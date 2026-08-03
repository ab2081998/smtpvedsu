import streamlit as st
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import re
import pandas as pd
from auth import require_login

# Security Check
require_login()

st.set_page_config(page_title="Important Mails Reader", page_icon="⭐", layout="wide")
st.title("⭐ Important Mails Reader (Inbox View)")
st.write("Aapke starred/flagged important emails ko Inbox ki tarah properly HTML preview ke saath dekhein.")

# --- INITIALIZE SESSION STATE FOR CREDENTIALS & EMAILS ---
if "imap_server" not in st.session_state:
    st.session_state["imap_server"] = st.secrets.get("IMAP_SERVER", "imap.gmail.com")
if "imap_port" not in st.session_state:
    st.session_state["imap_port"] = int(st.secrets.get("IMAP_PORT", 993))
if "email_user" not in st.session_state:
    st.session_state["email_user"] = st.secrets.get("IMAP_EMAIL", "")
if "email_pass" not in st.session_state:
    st.session_state["email_pass"] = ""

# --- SIDEBAR SETTINGS ---
st.sidebar.header("⚙️ IMAP Login Settings")

imap_server = st.sidebar.text_input("IMAP Server", value=st.session_state["imap_server"])
imap_port = st.sidebar.number_input("Port", value=st.session_state["imap_port"])
email_user = st.sidebar.text_input("Email Address", value=st.session_state["email_user"])
email_pass = st.sidebar.text_input("Password / App Password", type="password", value=st.session_state["email_pass"])

# Update session state whenever input changes
st.session_state["imap_server"] = imap_server
st.session_state["imap_port"] = imap_port
st.session_state["email_user"] = email_user
st.session_state["email_pass"] = email_pass

st.sidebar.divider()
st.sidebar.header("📅 Calendar & Filter Options")
today = datetime.now().date()
start_date = st.sidebar.date_input("Start Date:", today - timedelta(days=30))
end_date = st.sidebar.date_input("End Date:", today)
max_emails = st.sidebar.number_input(
    "Maximum emails display:", min_value=10, max_value=500, value=100, step=10
)

# Helper Functions
def parse_header(header_value):
    if not header_value:
        return ""
    decoded_list = decode_header(header_value)
    header_str = ""
    for decoded, encoding in decoded_list:
        if isinstance(decoded, bytes):
            header_str += decoded.decode(encoding or "utf-8", errors="ignore")
        else:
            header_str += str(decoded)
    return header_str

def parse_sender_info(from_addr):
    if not from_addr:
        return "", ""
    # Header format: "Display Name" <email@domain.com> ya simple email
    match = re.search(r'(?:"?([^"]*)"?\s*)?<([^>]+@[^>]+)>', from_addr)
    if match:
        name = match.group(1).strip() if match.group(1) else ""
        email_id = match.group(2).strip()
        if not name:
            name = email_id.split('@')[0]
        return name, email_id
    
    clean_addr = from_addr.strip()
    if "@" in clean_addr:
        return clean_addr.split('@')[0], clean_addr
    
    return clean_addr, clean_addr

def extract_email_body(msg):
    html_body, text_body = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition:
                if content_type == "text/html":
                    html_body = part.get_payload(decode=True).decode(errors="ignore")
                    break
                elif content_type == "text/plain" and not text_body:
                    text_body = part.get_payload(decode=True).decode(errors="ignore")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True).decode(errors="ignore")
        if content_type == "text/html":
            html_body = payload
        else:
            text_body = payload

    if html_body:
        return html_body
    else:
        return f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{text_body}</pre>"

# --- FETCH ACTION BUTTON ---
if st.sidebar.button("Fetch Important Emails", type="primary"):
    if not email_user or not email_pass:
        st.error("❌ Kripya Email Address aur Password enter karein.")
    else:
        try:
            with st.spinner("Connecting & Fetching Inbox-Style Emails..."):
                mail = imaplib.IMAP4_SSL(imap_server, port=imap_port)
                mail.login(email_user, email_pass)
                mail.select("inbox")

                since_str = start_date.strftime("%d-%b-%Y")
                before_str = (end_date + timedelta(days=1)).strftime("%d-%b-%Y")
                search_criterion = f'FLAGGED SINCE "{since_str}" BEFORE "{before_str}"'
                status, messages = mail.search(None, search_criterion)

                email_ids = messages[0].split()
                fetched_records = []

                if email_ids:
                    latest_ids = email_ids[::-1]
                    for idx, e_id in enumerate(latest_ids):
                        if idx >= max_emails:
                            break
                        res, msg_data = mail.fetch(e_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject = parse_header(msg.get("Subject")) or "(No Subject)"
                                from_addr = parse_header(msg.get("From"))
                                date_str = msg.get("Date")
                                body_content = extract_email_body(msg)

                                sender_name, sender_email = parse_sender_info(from_addr)

                                fetched_records.append({
                                    "subject": subject,
                                    "from_addr": from_addr,
                                    "sender_name": sender_name,
                                    "sender_email": sender_email,
                                    "date_str": date_str,
                                    "body_content": body_content
                                })

                mail.logout()
                st.session_state["fetched_important_emails"] = fetched_records
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error: {e}")

# --- MAIN DISPLAY AREA ---
if "fetched_important_emails" in st.session_state:
    all_emails = st.session_state["fetched_important_emails"]
    if not all_emails:
        st.info("ℹ️ Selected date range me koi important emails nahi mile.")
    else:
        st.success(f"✅ Total {len(all_emails)} Important emails loaded.")

        # Export CSV Button (Proper 3 Columns)
        csv_records = [
            {
                "Name": e["sender_name"],
                "Email": e["sender_email"],
                "Subject": e["subject"]
            }
            for e in all_emails
        ]
        df = pd.DataFrame(csv_records, columns=["Name", "Email", "Subject"])
        csv_data = df.to_csv(index=False).encode('utf-8-sig')

        st.download_button(
            label="📥 Export to CSV (Name, Email, Subject)",
            data=csv_data,
            file_name=f"important_emails_{today}.csv",
            mime="text/csv",
            type="primary"
        )

        st.divider()

        # Render All Emails Directly
        for item in all_emails:
            with st.expander(f"⭐ **{item['subject']}** — *From: {item['from_addr']}*"):
                st.markdown(f"**From:** `{item['from_addr']}`")
                st.markdown(f"**Date:** `{item['date_str']}`")
                st.divider()
                components.html(
                    f"""
                    <div style="background-color: #ffffff; padding: 15px; border-radius: 8px;">
                        {item['body_content']}
                    </div>
                    """,
                    height=400,
                    scrolling=True,
                )

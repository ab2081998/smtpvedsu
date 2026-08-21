from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import os
import re
import smtplib
import sys
import time
import pandas as pd
import streamlit as st
from streamlit_quill import st_quill

# --- 0. AUTHENTICATION & PATH SETUP ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

HISTORY_FILE = os.path.abspath(os.path.join(parent_dir, "email_history.csv"))

try:
    import auth
    if hasattr(auth, "require_auth"):
        auth.require_auth()
    elif hasattr(auth, "check_auth"):
        auth.check_auth()
    else:
        if not st.session_state["authenticated"]:
            st.warning("🔒 Access Restricted! Please enter password.")
            user_pass = st.text_input(
                "Please enter Password",
                type="password",
                key="p5_auth_pass_input",
            )
            CORRECT_PASSWORD = st.secrets.get("PASSWORD", "root")
            if st.button("Unlock Page"):
                if user_pass == CORRECT_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.success("✅ Password correct!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect password!")
                    st.stop()
except ImportError:
    if not st.session_state["authenticated"]:
        st.warning("🔒 Access Restricted! Please enter password.")
        user_pass = st.text_input(
            "Please enter Password",
            type="password",
            key="p5_auth_pass_input",
        )
        CORRECT_PASSWORD = st.secrets.get("PASSWORD", "root")
        if st.button("Unlock Page"):
            if user_pass == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.success("✅ Password correct!")
                st.rerun()
            else:
                st.error("❌ Incorrect password!")
                st.stop()

# --- 1. HISTORY & RETENTION HELPERS ---
def clean_and_load_history():
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        return pd.DataFrame()
    try:
        df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip", engine="python")
        if df.empty:
            return pd.DataFrame()
        df.columns = df.columns.str.strip()
        if "Timestamp" in df.columns:
            df["Parsed_Time"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            df = df.dropna(subset=["Parsed_Time"])
            cutoff_time = datetime.now() - timedelta(hours=48)
            recent_df = df[df["Parsed_Time"] >= cutoff_time].copy()
            if len(recent_df) < len(df):
                save_df = recent_df.drop(columns=["Parsed_Time"])
                save_df.to_csv(HISTORY_FILE, index=False, encoding="utf-8")
                return recent_df.drop(columns=["Parsed_Time"])
            return df
    except Exception:
        return pd.DataFrame()

def save_to_history(log_entry):
    try:
        log_df = pd.DataFrame([log_entry])
        file_exists = (
            os.path.exists(HISTORY_FILE) and os.path.getsize(HISTORY_FILE) > 0
        )
        log_df.to_csv(
            HISTORY_FILE,
            mode="a",
            header=not file_exists,
            index=False,
            encoding="utf-8",
        )
    except Exception as err:
        st.error(f"⚠️ History write error: {err}")

def get_dynamic_senders():
    senders = []
    if "smtp_accounts" in st.secrets:
        smtp_accs = st.secrets["smtp_accounts"]
        for acc_key in smtp_accs:
            acc = smtp_accs[acc_key]
            em = acc.get("email")
            pw = acc.get("pass") or acc.get("password")
            if em and pw:
                clean_pw = str(pw).strip().strip('"').strip("'").replace(" ", "")
                smtp_user = str(acc.get("user") or em).strip()
                
                senders.append({
                    "name": str(acc.get("name", acc_key)).strip(),
                    "email": str(em).strip(),
                    "user": smtp_user,
                    "password": clean_pw,
                    "server": str(acc.get("server", "smtp.resend.com")).strip(),
                    "port": int(acc.get("port", 587))
                })

    if not senders and "smtp" in st.secrets and "accounts" in st.secrets["smtp"]:
        for idx, acc in enumerate(st.secrets["smtp"]["accounts"]):
            if "email" in acc and "password" in acc:
                clean_pw = str(acc["password"]).strip().strip('"').strip("'").replace(" ", "")
                em = str(acc["email"]).strip()
                smtp_user = str(acc.get("user") or em).strip()
                senders.append({
                    "name": str(acc.get("name", f"Account {idx+1}")).strip(),
                    "email": em,
                    "user": smtp_user,
                    "password": clean_pw,
                    "server": str(acc.get("server", "smtp.resend.com")).strip(),
                    "port": int(acc.get("port", 587))
                })

    return senders

def make_links_clickable(text):
    """Auto-converts plain text URLs/emails into styled CRM hyperlinks."""
    if not text:
        return ""
    
    # 1. Convert plain email addresses to mailto:
    email_pattern = r'(?<!href="mailto:)(?<!href=")(?<!">)([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(?![^<]*>)'
    text = re.sub(email_pattern, r'<a href="mailto:\1" style="color: #0056b3; font-weight: 500; text-decoration: underline;">\1</a>', text)

    # 2. Convert raw https/http URLs
    url_pattern = r'(?<!href=")(?<!src=")(https?://[^\s<"]+)(?![^<]*>)'
    text = re.sub(url_pattern, r'<a href="\1" target="_blank" style="color: #0056b3; font-weight: 500; text-decoration: underline;">\1</a>', text)

    # 3. Convert raw www URLs
    www_pattern = r'(?<!href=")(?<!https://)(?<!http://)(www\.[^\s<"]+)(?![^<]*>)'
    text = re.sub(www_pattern, r'<a href="https://\1" target="_blank" style="color: #0056b3; font-weight: 500; text-decoration: underline;">\1</a>', text)

    return text

def strip_html_tags(html_content):
    """Creates a clean Plain Text version for MIME fallback."""
    if not html_content:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html_content)

def build_crm_html_template(body_content, is_rich_text=False):
    """Wraps campaign content into a high-deliverability CRM email layout."""
    if not body_content:
        return ""

    if is_rich_text:
        formatted_body = body_content
    else:
        # For Plain Text Editor Mode: process paragraphs & links
        clickable_text = make_links_clickable(body_content)
        paragraphs = clickable_text.split("\n\n")
        html_paragraphs = [
            f"<p style='margin: 0 0 16px 0; font-size: 15px; line-height: 1.6; color: #333333;'>{p.replace('\n', '<br>')}</p>" 
            for p in paragraphs if p.strip()
        ]
        formatted_body = "".join(html_paragraphs)

    # Professional CRM Email Envelope Layout
    crm_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Encoding" content="gzip, deflate">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4f6f9; padding: 25px 0;">
        <tr>
            <td align="center">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 620px; background-color: #ffffff; border-radius: 8px; border: 1px solid #e1e6eb; box-shadow: 0 2px 5px rgba(0,0,0,0.03); overflow: hidden;">
                    <tr>
                        <td style="padding: 30px 35px; color: #2d3748; font-size: 15px; line-height: 1.6;">
                            {formatted_body}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    return crm_template

# --- 2. MAIN APP UI ---
st.title("📧 Single Column Email Campaign Sender (CRM Engine)")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("1. SMTP Sender Selection")
    
    available_senders = get_dynamic_senders()
    selected_senders = []
    
    if available_senders:
        account_options = ["All Accounts (Round Robin)"] + [
            f"{acc['name']} ({acc['email']})" for acc in available_senders
        ]
        
        chosen_acc = st.selectbox(
            "Select Account from TOML",
            options=account_options,
            index=0
        )
        
        if chosen_acc == "All Accounts (Round Robin)":
            selected_senders = available_senders
            st.success(f"✅ Selected all {len(available_senders)} accounts for Round Robin")
        else:
            selected_acc_email = chosen_acc.split("(")[-1].replace(")", "").strip()
            selected_senders = [
                acc for acc in available_senders if acc["email"] == selected_acc_email
            ]
            st.success(f"✅ Selected: {selected_senders[0]['email']}")
    else:
        st.error("❌ No valid accounts found in secrets.toml!")

with col_right:
    st.subheader("2. Recipient Data (Single Column)")
    recipients_file = st.file_uploader(
        "Upload CSV/Excel (Single Column Email File)", type=["csv", "xlsx"]
    )

    recipient_emails = []
    list_name = "Single_Col_Campaign"
    
    if recipients_file:
        list_name = os.path.splitext(recipients_file.name)[0]
        try:
            if recipients_file.name.endswith(".csv"):
                df_raw = pd.read_csv(recipients_file, header=None)
            else:
                df_raw = pd.read_excel(recipients_file, header=None)
            
            first_col_vals = df_raw.iloc[:, 0].astype(str).tolist()
            for val in first_col_vals:
                cleaned_val = val.strip()
                if "@" in cleaned_val and "." in cleaned_val:
                    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", cleaned_val)
                    if match:
                        recipient_emails.append(match.group(0))
            
            st.success(f"✅ Loaded {len(recipient_emails)} emails from file '{list_name}'")
        except Exception as e:
            st.error(f"❌ File read error: {e}")

st.divider()

# --- Campaign Message Setup ---
st.subheader("3. Campaign Message Setup")

subject_template = st.text_input(
    "Subject Line", value="Important Update"
)

editor_mode = st.radio(
    "Select Editor Mode:",
    ["Plain / Standard Text Input", "Rich Text Editor (Quill)"],
    horizontal=True
)

if editor_mode == "Plain / Standard Text Input":
    email_body = st.text_area(
        "Email Body (CRM Auto-Formatter Enabled)",
        value="Managing employee performance is critical for leaders...\n\nRegister Now: https://www.webinarbrite.com\nNeed assistance? cs@webinarbrite.com",
        height=280
    )
else:
    email_body = st_quill(
        placeholder="Write your CRM campaign message here...",
        key="single_col_quill"
    )

with st.expander("⚙️ Advanced Settings & Resume Options"):
    delay_between_mails = st.number_input(
        "Delay Between Emails (seconds)", value=2, min_value=0
    )
    enable_auto_resume = st.checkbox(
        "Auto-Skip Emails Sent in Last 48 Hours", value=True
    )

st.divider()

if st.button("🚀 Start Campaign", type="primary", use_container_width=True):
    if not selected_senders:
        st.error("❌ Please setup valid accounts in secrets.toml!")
        st.stop()

    if not recipient_emails:
        st.error("❌ Please upload a valid CSV file containing email addresses!")
        st.stop()

    if not email_body or not email_body.strip():
        st.error("❌ Email Body khali nahi ho sakta!")
        st.stop()

    is_rich = (editor_mode == "Rich Text Editor (Quill)")
    
    # 1. Build High-converting CRM HTML template
    final_html_body = build_crm_html_template(email_body, is_rich_text=is_rich)
    
    # 2. Build Plain Text fallback for high inbox deliverability
    plain_text_fallback = strip_html_tags(email_body)

    already_sent_emails = set()
    if enable_auto_resume:
        history_df = clean_and_load_history()
        if not history_df.empty and "Recipient" in history_df.columns:
            if "Status" in history_df.columns:
                sent_mask = history_df["Status"].str.contains(
                    "Sent|✅", case=False, na=False
                )
                already_sent_emails = set(
                    history_df[sent_mask]["Recipient"]
                    .dropna()
                    .str.strip()
                    .str.lower()
                )
            else:
                already_sent_emails = set(
                    history_df["Recipient"].dropna().str.strip().str.lower()
                )

        if already_sent_emails:
            st.info(
                f"ℹ️ Auto-Resume Active: Pichle 48 hours me {len(already_sent_emails)} emails sent ho chuke hain. Unhe skip kiya jayega."
            )

    progress_bar = st.progress(0)
    logs_container = st.container()

    total_recipients = len(recipient_emails)
    sender_index = 0
    total_senders = len(selected_senders)

    for idx, email in enumerate(recipient_emails):

        if enable_auto_resume and email.lower() in already_sent_emails:
            with logs_container:
                st.write(f"⏭️ Skipped (Already sent in last 48h): {email}")
            progress_bar.progress((idx + 1) / total_recipients)
            continue

        curr_sender = selected_senders[sender_index % total_senders]
        sender_email = curr_sender["email"]
        smtp_login_user = curr_sender["user"]
        sender_pass = curr_sender["password"]
        active_host = curr_sender["server"]
        active_port = curr_sender["port"]
        active_sender_name = curr_sender["name"]

        sender_index += 1

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_success = False
        error_reason = "Success"

        try:
            # CRM Dual-part MIME Structure (Prevents Plain-text display/Spam flags)
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((active_sender_name, sender_email))
            msg["To"] = email
            msg["Subject"] = subject_template

            # Attach Plain Text first, then HTML (Standard CRM practice)
            msg.attach(MIMEText(plain_text_fallback, "plain", "utf-8"))
            msg.attach(MIMEText(final_html_body, "html", "utf-8"))

            server = smtplib.SMTP(active_host, active_port, timeout=15)
            server.starttls()
            server.login(smtp_login_user, sender_pass)
            server.sendmail(sender_email, email, msg.as_string())
            server.quit()

            is_success = True
            with logs_container:
                st.success(f"✅ Sent to: {email} via {sender_email}")
        except Exception as e:
            error_reason = str(e)
            with logs_container:
                st.error(f"❌ Failed for {email}: {error_reason}")

        log_entry = {
            "Timestamp": now_str,
            "List Name": list_name,
            "Sender": sender_email,
            "Recipient": email,
            "Subject": subject_template,
            "Status": "Sent ✅" if is_success else "Failed ❌",
            "Reason": error_reason,
        }
        save_to_history(log_entry)

        progress_bar.progress((idx + 1) / total_recipients)
        if delay_between_mails > 0:
            time.sleep(delay_between_mails)

    st.success("🎉 Campaign execution complete!")

st.divider()
st.subheader("📜 Recent Campaign History (Last 48 Hours)")

history_display_df = clean_and_load_history()
if not history_display_df.empty:
    st.dataframe(history_display_df, use_container_width=True, height=350)
    col_dl, col_clr = st.columns(2)
    col_dl.download_button(
        label="📥 Download History CSV",
        data=history_display_df.to_csv(index=False).encode("utf-8"),
        file_name=f"campaign_history_48h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if col_clr.button("🗑️ Clear History Data", use_container_width=True):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.success("History cleared!")
        st.rerun()
else:
    st.info("ℹ️ Abhi tak koi history record save nahi hua hai.")

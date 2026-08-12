from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import os
import smtplib
import sys
import time
import pandas as pd
import streamlit as st
from streamlit_quill import st_quill

# --- 0. AUTHENTICATION & SESSION CHECK ---
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
import auth

# Force Authentication Check via auth.py
if hasattr(auth, "require_auth"):
    auth.require_auth()
elif hasattr(auth, "check_auth"):
    auth.check_auth()

# Fallback session check with password unlock input
if not st.session_state.get("authenticated", False):
    st.subheader("🔒 Page Locked")
    password_input = st.text_input("Enter password to unlock page:", type="password")
    correct_password = st.secrets.get("APP_PASSWORD", "admin123")
    if st.button("Unlock"):
        if password_input == correct_password:
            st.session_state["authenticated"] = True
            st.success("Unlocked successfully!")
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()

# --- 1. SECRETS SE MULTI-SMTP ACCOUNTS FETCH KARNA ---
smtp_secrets = st.secrets.get("smtp_accounts", {})
if "smtp_profiles" not in st.session_state:
    st.session_state["smtp_profiles"] = {}

# secrets.toml mein [smtp_accounts.xxx] format load karein
if smtp_secrets:
    for acc_key, acc_data in smtp_secrets.items():
        profile_label = acc_data.get("name", acc_key.title())
        st.session_state["smtp_profiles"][profile_label] = {
            "email": str(acc_data.get("email", "")),
            "user": str(acc_data.get("user", "")),
            "pass": str(acc_data.get("pass", "")),
            "server": str(acc_data.get("server", "")),
            "port": int(acc_data.get("port", 587)),
            "name": str(acc_data.get("name", "")),
        }

# Fallback: Agar purani single DEFAULT_SMTP_ keys ho
if not st.session_state["smtp_profiles"]:
    DEF_EMAIL = st.secrets.get("DEFAULT_SMTP_EMAIL", "")
    DEF_USER = st.secrets.get("DEFAULT_SMTP_USER", "")
    DEF_PASS = st.secrets.get("DEFAULT_SMTP_PASS", "")
    DEF_SERVER = st.secrets.get("DEFAULT_SMTP_SERVER", "smtp.resend.com")
    DEF_PORT = st.secrets.get("DEFAULT_SMTP_PORT", 587)
    DEF_NAME = st.secrets.get("DEFAULT_SMTP_NAME", "Bulk Mailer")

    st.session_state["smtp_profiles"]["Default Profile"] = {
        "email": DEF_EMAIL,
        "user": DEF_USER,
        "pass": DEF_PASS,
        "server": DEF_SERVER,
        "port": DEF_PORT,
        "name": DEF_NAME,
    }

# Initial Session Credentials set karein
first_profile = list(st.session_state["smtp_profiles"].values())[0]
if "smtp_email" not in st.session_state:
    st.session_state["smtp_email"] = first_profile["email"]
if "smtp_user" not in st.session_state:
    st.session_state["smtp_user"] = first_profile["user"]
if "smtp_password" not in st.session_state:
    st.session_state["smtp_password"] = first_profile["pass"]
if "smtp_server" not in st.session_state:
    st.session_state["smtp_server"] = first_profile["server"]
if "smtp_port" not in st.session_state:
    st.session_state["smtp_port"] = first_profile["port"]
if "smtp_name" not in st.session_state:
    st.session_state["smtp_name"] = first_profile["name"]

DEFAULT_TEMPLATE = """<p>Hi {Name},</p>
<p>I hope this email finds you well.</p>
<p>Write your message here...</p>
<br>
<p data-path-to-node="12">WebinarBrite<br>2438 Industrial Blvd #1003, Abilene, TX 79605, United States<br>Need assistance? <a href="mailto:cs@webinarbrite.com ">cs@webinarbrite.com&nbsp;</a><br>If you do not wish to receive future webinar invites, please <a href="https://webinarbrite.com/unsubscribe">Unsubscribe Here</a></p>"""

if "editor_text" not in st.session_state:
    st.session_state["editor_text"] = DEFAULT_TEMPLATE

# --- 2. MULTI-SMTP SIDEBAR CONFIG ---
with st.sidebar:
    st.divider()
    st.markdown("**⚙️ SMTP Configurations**")

    profile_names = list(st.session_state["smtp_profiles"].keys())
    selected_profile_name = st.selectbox(
        "Select Active SMTP Profile:", options=profile_names
    )
    selected_profile = st.session_state["smtp_profiles"][selected_profile_name]

    profile_save_name = st.text_input(
        "Save As Profile Name:", value=selected_profile_name
    )

    button_container = st.container()

    st.markdown("---")
    s_email = st.text_input("Sender Email (From):", value=selected_profile["email"])
    s_user = st.text_input("SMTP Username:", value=selected_profile["user"])
    s_pass = st.text_input(
        "App Password / API Key:",
        value=selected_profile["pass"],
        type="password",
    )
    s_server = st.text_input("SMTP Server:", value=selected_profile["server"])
    s_port = st.number_input(
        "SMTP Port:", value=int(selected_profile["port"]), step=1
    )
    s_name = st.text_input("Sender Name:", value=selected_profile["name"])

    with button_container:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Profile", type="primary", use_container_width=True):
                p_name = profile_save_name.strip() or "Custom Profile"
                st.session_state["smtp_profiles"][p_name] = {
                    "email": s_email.strip(),
                    "user": s_user.strip(),
                    "pass": s_pass.strip(),
                    "server": s_server.strip(),
                    "port": s_port,
                    "name": s_name.strip(),
                }
                st.session_state["smtp_email"] = s_email.strip()
                st.session_state["smtp_user"] = s_user.strip()
                st.session_state["smtp_password"] = s_pass.strip()
                st.session_state["smtp_server"] = s_server.strip()
                st.session_state["smtp_port"] = s_port
                st.session_state["smtp_name"] = s_name.strip()
                st.success(f"✅ Profile '{p_name}' Saved!")
                st.rerun()
        with col2:
            if st.button("🔄 Reset Profile", use_container_width=True):
                st.session_state["smtp_email"] = selected_profile["email"]
                st.session_state["smtp_user"] = selected_profile["user"]
                st.session_state["smtp_password"] = selected_profile["pass"]
                st.session_state["smtp_server"] = selected_profile["server"]
                st.session_state["smtp_port"] = selected_profile["port"]
                st.session_state["smtp_name"] = selected_profile["name"]
                st.info("🔄 Restored Selected Profile Defaults!")
                st.rerun()

    st.divider()
    if st.button("🚪 Logout App"):
        st.session_state["authenticated"] = False
        st.success("👋 Logged out!")
        st.rerun()

# --- 3. MAIN UI ---
st.markdown("**📢 Single Column Mail Sender (Email Only)**")
st.caption("Send emails directly using a CSV containing only Email addresses.")

st.session_state["smtp_email"] = s_email.strip()
st.session_state["smtp_user"] = s_user.strip()
st.session_state["smtp_password"] = s_pass.strip()
st.session_state["smtp_server"] = s_server.strip()
st.session_state["smtp_port"] = s_port
st.session_state["smtp_name"] = s_name.strip()

if st.session_state["smtp_email"]:
    st.info(
        f"📧 **Active Profile ({selected_profile_name}):** `{st.session_state['smtp_name']} <{st.session_state['smtp_email']}>` "
        f"| Login User: `{st.session_state['smtp_user'] or st.session_state['smtp_email']}` "
        f"({st.session_state['smtp_server']}:{st.session_state['smtp_port']})"
    )
else:
    st.warning("⚠️ Pehle Sidebar me SMTP Details save karein ya secrets.toml setup karein!")
    st.stop()

# --- STEP A: CSV UPLOAD ---
st.markdown("**1. Upload CSV File**")
uploaded_file = st.file_uploader(
    "Upload CSV file (Containing Email column):",
    type=["csv"],
    key="single_col_csv_file_uploader",
)

df = None
email_col = None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()
        if len(df.columns) < 1:
            st.error("❌ CSV file khali lag rahi hai!")
            df = None
        else:
            email_col = df.columns[0]
            for col in df.columns:
                if col.lower() == "email":
                    email_col = col
                    break
            st.success(f"✅ CSV Loaded! Total Records: {len(df)}")
            st.info(f"📌 **Selected Email Column:** `{email_col}`")
            st.dataframe(df.head(5), use_container_width=True)
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")

st.divider()

# --- STEP B: EMAIL CONTENT ---
st.markdown("**2. Email Content**")

subject_input = st.text_input("Email Subject:", value="Important Announcement")

quill_res = st_quill(
    value=st.session_state["editor_text"], 
    html=True, 
    key="quill_editor_fixed"
)

# Editor me change hone par dynamic body fetch karne ka logic
active_body = quill_res if (quill_res and quill_res != "") else st.session_state["editor_text"]

# Save Template aur Test Mail Toolbar (Side-by-side Layout)
col_save, col_test_input, col_test_btn = st.columns([1.5, 2.5, 1])

with col_save:
    if st.button("💾 Save Template / Content", use_container_width=True):
        st.session_state["editor_text"] = active_body
        st.success("✅ Content Saved!")

with col_test_input:
    test_recipient = st.text_input(
        "Test Email To:", 
        placeholder="recipient@example.com", 
        label_visibility="collapsed"
    )

with col_test_btn:
    send_test_btn = st.button("🧪 Send Test Mail", type="primary", use_container_width=True)

# Test Email Execution Block
if send_test_btn:
    if not test_recipient or "@" not in test_recipient:
        st.error("❌ Valid recipient email address dalein!")
    else:
        sender_email = st.session_state["smtp_email"]
        smtp_username = st.session_state["smtp_user"] or sender_email
        sender_password = st.session_state["smtp_password"]
        smtp_server = st.session_state["smtp_server"]
        smtp_port = st.session_state["smtp_port"]
        sender_name = st.session_state["smtp_name"]
        
        test_subject = f"[TEST] {subject_input}"
        test_body = active_body.replace("{Name}", "Test User")

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((sender_name, sender_email))
            msg["To"] = test_recipient
            msg["Subject"] = test_subject

            clean_formatted_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
            p {{ margin: 0 0 6px 0 !important; padding: 0 !important; line-height: 1.4 !important; }}
            div {{ margin: 0 !important; padding: 0 !important; line-height: 1.4 !important; }}
            </style>
            </head>
            <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.4; margin: 0; padding: 10px;">
            {test_body}
            </body>
            </html>
            """
            msg.attach(MIMEText(clean_formatted_html, "html"))

            if int(smtp_port) == 465:
                with smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=15) as server:
                    server.login(smtp_username, sender_password)
                    server.sendmail(sender_email, test_recipient, msg.as_string())
            else:
                with smtplib.SMTP(smtp_server, int(smtp_port), timeout=15) as server:
                    server.starttls()
                    server.login(smtp_username, sender_password)
                    server.sendmail(sender_email, test_recipient, msg.as_string())

            st.success(f"✅ Test email successfully sent to `{test_recipient}`!")

        except Exception as e:
            st.error(f"❌ Failed to send Test Email: {str(e)}")

st.divider()

# --- STEP C: BULK SENDING LOGIC WITH AUTO-RESUME & RETRY ---
st.markdown("**3. Start Bulk Campaign**")

notification_box = st.container()
FALLBACK_NAME = "there"
HISTORY_FILE = "email_history.csv"

if st.button("🚀 Send Mails Now", type="primary", disabled=(df is None)):
    if df is None or len(df) == 0:
        st.error("❌ Valid CSV File upload karein!")
        st.stop()

    sender_email = st.session_state["smtp_email"]
    smtp_username = st.session_state["smtp_user"] or sender_email
    sender_password = st.session_state["smtp_password"]
    smtp_server = st.session_state["smtp_server"]
    smtp_port = st.session_state["smtp_port"]
    sender_name = st.session_state["smtp_name"]

    total_records = len(df)
    current_body = active_body

    # 1. PEHLE SE SENT EMAILS LOAD KAREIN (TO SKIP THEM AUTOMATICALLY)
    already_sent_emails = set()
    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(HISTORY_FILE)
            if "Recipient" in history_df.columns and "Status" in history_df.columns:
                already_sent_emails = set(
                    history_df[history_df["Status"] == "Sent ✅"]["Recipient"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )
        except Exception as e:
            st.warning(f"History load nahi ho saki: {e}")

    with notification_box:
        progress_bar = st.progress(0)
        status_text = st.empty()
        success_count = 0
        failed_count = 0
        skipped_count = 0
        logs = []

        for index, row in df.iterrows():
            recipient_email = (
                str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
            )
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # --- AUTO RESUME LOGIC: Skip already sent emails ---
            if recipient_email.lower() in already_sent_emails:
                skipped_count += 1
                current_progress = (index + 1) / total_records
                progress_bar.progress(current_progress)
                status_text.text(
                    f"⏩ Skipped {index + 1}/{total_records}: {recipient_email} (Already Sent)"
                )
                continue

            # Invalid Email Check
            if not recipient_email or "@" not in recipient_email:
                failed_count += 1
                log_data = {
                    "Timestamp": now_str,
                    "Sender": sender_email,
                    "Recipient": recipient_email,
                    "Subject": subject_input,
                    "Status": "Failed ❌",
                    "Reason": "Invalid Email",
                }
                logs.append(log_data)
                pd.DataFrame([log_data]).to_csv(
                    HISTORY_FILE,
                    mode="a",
                    header=not os.path.exists(HISTORY_FILE),
                    index=False,
                )
                continue

            custom_subject = subject_input.replace("{Name}", FALLBACK_NAME)
            custom_body = current_body.replace("{Name}", FALLBACK_NAME)

            # Retry mechanism agar connection drop/timeout ho jaye
            max_retries = 3
            email_sent = False

            for attempt in range(max_retries):
                try:
                    msg = MIMEMultipart("alternative")
                    msg["From"] = formataddr((sender_name, sender_email))
                    msg["To"] = recipient_email
                    msg["Subject"] = custom_subject

                    clean_formatted_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                    <style>
                    p {{ margin: 0 0 6px 0 !important; padding: 0 !important; line-height: 1.4 !important; }}
                    div {{ margin: 0 !important; padding: 0 !important; line-height: 1.4 !important; }}
                    </style>
                    </head>
                    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333333; line-height: 1.4; margin: 0; padding: 10px;">
                    {custom_body}
                    </body>
                    </html>
                    """
                    msg.attach(MIMEText(clean_formatted_html, "html"))

                    if int(smtp_port) == 465:
                        with smtplib.SMTP_SSL(
                            smtp_server, int(smtp_port), timeout=15
                        ) as server:
                            server.login(smtp_username, sender_password)
                            server.sendmail(
                                sender_email, recipient_email, msg.as_string()
                            )
                    else:
                        with smtplib.SMTP(
                            smtp_server, int(smtp_port), timeout=15
                        ) as server:
                            server.starttls()
                            server.login(smtp_username, sender_password)
                            server.sendmail(
                                sender_email, recipient_email, msg.as_string()
                            )

                    success_count += 1
                    email_sent = True
                    log_data = {
                        "Timestamp": now_str,
                        "Sender": sender_email,
                        "Recipient": recipient_email,
                        "Subject": custom_subject,
                        "Status": "Sent ✅",
                        "Reason": "Success",
                    }
                    logs.append(log_data)

                    # Instant history saving
                    pd.DataFrame([log_data]).to_csv(
                        HISTORY_FILE,
                        mode="a",
                        header=not os.path.exists(HISTORY_FILE),
                        index=False,
                    )
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        failed_count += 1
                        log_data = {
                            "Timestamp": now_str,
                            "Sender": sender_email,
                            "Recipient": recipient_email,
                            "Subject": custom_subject,
                            "Status": "Failed ❌",
                            "Reason": str(e),
                        }
                        logs.append(log_data)
                        pd.DataFrame([log_data]).to_csv(
                            HISTORY_FILE,
                            mode="a",
                            header=not os.path.exists(HISTORY_FILE),
                            index=False,
                        )

            current_progress = (index + 1) / total_records
            progress_bar.progress(current_progress)
            status_text.text(f"Sending {index + 1}/{total_records}: {recipient_email}")

            # Throttling & Delay Logic
            if (index + 1) % 50 == 0:
                time.sleep(10)  # Har 50 emails par 10s wait rate limits se bachne ke liye
            else:
                time.sleep(0.5)

        st.success(
            f"🎯 **Campaign Completed!** Mails Sent: **{success_count}** | Skipped (Already Sent): **{skipped_count}** | Failed: **{failed_count}**"
        )

        if logs:
            st.markdown("**Current Batch Summary Report**")
            log_df = pd.DataFrame(logs)
            st.dataframe(log_df, use_container_width=True)

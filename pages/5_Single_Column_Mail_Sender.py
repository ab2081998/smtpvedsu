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

# --- 0. AUTHENTICATION & SESSION CHECK ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    import auth

    if hasattr(auth, "require_auth"):
        auth.require_auth()
    elif hasattr(auth, "check_auth"):
        auth.check_auth()
    else:
        if not st.session_state["authenticated"]:
            st.warning("🔒 Access Restricted! Please enter root password.")
            user_pass = st.text_input(
                "Please enter Password",
                type="password",
                key="single_col_auth_pass_input",
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
        st.warning("🔒 Access Restricted! Please enter root password.")
        user_pass = st.text_input(
            "Please enter Password",
            type="password",
            key="single_col_auth_pass_input",
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

# --- 1. DEFAULT SECRETS FETCH & SESSION STATE SETUP ---
DEF_EMAIL = st.secrets.get("DEFAULT_SMTP_EMAIL", "")
DEF_USER = st.secrets.get("DEFAULT_SMTP_USER", "")
DEF_PASS = st.secrets.get("DEFAULT_SMTP_PASS", "")
DEF_SERVER = st.secrets.get("DEFAULT_SMTP_SERVER", "smtp.resend.com")
DEF_PORT = st.secrets.get("DEFAULT_SMTP_PORT", 587)
DEF_NAME = st.secrets.get("DEFAULT_SMTP_NAME", "Bulk Mailer")

if "smtp_email" not in st.session_state:
    st.session_state["smtp_email"] = DEF_EMAIL
if "smtp_user" not in st.session_state:
    st.session_state["smtp_user"] = DEF_USER
if "smtp_password" not in st.session_state:
    st.session_state["smtp_password"] = DEF_PASS
if "smtp_server" not in st.session_state:
    st.session_state["smtp_server"] = DEF_SERVER
if "smtp_port" not in st.session_state:
    st.session_state["smtp_port"] = DEF_PORT
if "smtp_name" not in st.session_state:
    st.session_state["smtp_name"] = DEF_NAME

# Default Template Text
DEFAULT_TEMPLATE = """<p>Hello {Name},</p>
<p>I hope this email finds you well.</p>
<p>Write your message here...</p>"""

# Persistent Session State for Quill content
if "editor_text" not in st.session_state:
    st.session_state["editor_text"] = DEFAULT_TEMPLATE


# --- 2. SIDEBAR CONFIG (DYNAMIC UPDATES & RESET) ---
with st.sidebar:
    st.divider()
    st.markdown("**⚙️ SMTP Config**")
    s_email = st.text_input(
        "Sender Email (From):",
        value=st.session_state["smtp_email"],
        placeholder="onboarding@resend.dev or verified domain",
    )
    s_user = st.text_input(
        "SMTP Username:",
        value=st.session_state["smtp_user"],
        placeholder="resend",
    )
    s_pass = st.text_input(
        "App Password / API Key:",
        value=st.session_state["smtp_password"],
        type="password",
    )
    s_server = st.text_input("SMTP Server:", value=st.session_state["smtp_server"])
    s_port = st.number_input(
        "SMTP Port:", value=int(st.session_state["smtp_port"]), step=1
    )
    s_name = st.text_input("Sender Name:", value=st.session_state["smtp_name"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Credentials", type="primary", use_container_width=True):
            st.session_state["smtp_email"] = s_email.strip()
            st.session_state["smtp_user"] = s_user.strip()
            st.session_state["smtp_password"] = s_pass.strip()
            st.session_state["smtp_server"] = s_server.strip()
            st.session_state["smtp_port"] = s_port
            st.session_state["smtp_name"] = s_name.strip()
            st.success("✅ Credentials Updated!")
            st.rerun()

    with col2:
        if st.button("🔄 Reset Default", use_container_width=True):
            st.session_state["smtp_email"] = DEF_EMAIL
            st.session_state["smtp_user"] = DEF_USER
            st.session_state["smtp_password"] = DEF_PASS
            st.session_state["smtp_server"] = DEF_SERVER
            st.session_state["smtp_port"] = DEF_PORT
            st.session_state["smtp_name"] = DEF_NAME
            st.info("🔄 Restored Default Secrets!")
            st.rerun()

    st.divider()
    if st.button("🚪 Logout App"):
        st.session_state["authenticated"] = False
        st.success("👋 Logged out!")
        st.rerun()


# --- 3. MAIN UI ---
st.markdown("**📢 Single Column Mail Sender (Email Only)**")
st.caption("Send emails directly using a CSV containing only Email addresses.")

# Active sender status indicator
if st.session_state["smtp_email"]:
    st.info(
        f"📧 **Active Sender:** `{st.session_state['smtp_name']} <{st.session_state['smtp_email']}>` "
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
            # First preference: Column named 'email'
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
subject_input = st.text_input(
    "Email Subject:", value="Important Announcement"
)

# Quill Text Editor with Session State
editor_content = st.st_quill(
    value=st.session_state["editor_text"],
    html=True,
    key="quill_single_col_custom",
)

if editor_content:
    st.session_state["editor_text"] = editor_content

st.divider()


# --- STEP C: BULK SENDING LOGIC ---
st.markdown("**3. Start Bulk Campaign**")
notification_box = st.container()
FALLBACK_NAME = "there"

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
    current_body = st.session_state["editor_text"]

    with notification_box:
        progress_bar = st.progress(0)
        status_text = st.empty()

        success_count = 0
        failed_count = 0
        logs = []

        for index, row in df.iterrows():
            recipient_email = (
                str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
            )

            if not recipient_email or "@" not in recipient_email:
                logs.append(
                    {
                        "Email": recipient_email,
                        "Status": "Failed ❌",
                        "Reason": "Invalid Email",
                    }
                )
                failed_count += 1
                continue

            custom_subject = subject_input.replace("{Name}", FALLBACK_NAME)
            custom_body = current_body.replace("{Name}", FALLBACK_NAME)

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
                    with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
                        server.login(smtp_username, sender_password)
                        server.sendmail(sender_email, recipient_email, msg.as_string())
                else:
                    with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                        server.starttls()
                        server.login(smtp_username, sender_password)
                        server.sendmail(sender_email, recipient_email, msg.as_string())

                success_count += 1
                logs.append(
                    {
                        "Email": recipient_email,
                        "Status": "Sent ✅",
                        "Reason": "Success",
                    }
                )
            except Exception as e:
                failed_count += 1
                logs.append(
                    {
                        "Email": recipient_email,
                        "Status": "Failed ❌",
                        "Reason": str(e),
                    }
                )

            current_progress = (index + 1) / total_records
            progress_bar.progress(current_progress)
            status_text.text(
                f"Sending {index + 1}/{total_records}: {recipient_email}"
            )
            time.sleep(0.2)

        st.success(
            f"🎯 **Campaign Finished!** Mails Sent: **{success_count}** | Failed: **{failed_count}**"
        )

        st.markdown("**Campaign Summary Report**")
        log_df = pd.DataFrame(logs)
        st.dataframe(log_df, use_container_width=True)

        # --- DOWNLOAD REPORT WITH SUBJECT & DATE IN FILENAME ---
        safe_subject = re.sub(r'[^\w\s-]', '', subject_input).strip().replace(' ', '_')
        if not safe_subject:
            safe_subject = "Campaign_Report"
        today_date = time.strftime("%Y-%m-%d")
        download_filename = f"{safe_subject}_{today_date}.csv"

        csv_data = log_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Campaign Report (CSV)",
            data=csv_data,
            file_name=download_filename,
            mime="text/csv",
            type="primary"
        )

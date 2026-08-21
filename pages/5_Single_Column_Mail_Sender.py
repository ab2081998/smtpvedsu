from datetime import datetime
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

# Absolute Path for email_history.csv to sync with History Page
HISTORY_FILE = os.path.abspath(os.path.join(parent_dir, "email_history.csv"))

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
                key="single_auth_pass_input",
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
            key="single_auth_pass_input",
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


# --- HELPER FUNCTION: SAFE CSV WRITE ---
def save_to_history(log_entry, filepath):
    """Guarantees absolute path resolution and appends record safely"""
    try:
        log_df = pd.DataFrame([log_entry])
        abs_path = os.path.abspath(filepath)
        file_exists = os.path.exists(abs_path) and os.path.getsize(abs_path) > 0

        log_df.to_csv(
            abs_path,
            mode="a",
            header=not file_exists,
            index=False,
            encoding="utf-8",
        )
    except Exception as err:
        st.error(f"⚠️ History write failed: {err}")


# --- 1. ADVANCED TOML & CSV SMTP LOADER ---
def load_smtp_accounts():
    accounts = []

    # A. Check secrets.toml for nested tables like [smtp_accounts.resend4]
    try:
        if "smtp_accounts" in st.secrets:
            smtp_sec = st.secrets["smtp_accounts"]

            if hasattr(smtp_sec, "items"):
                for acc_key, acc in smtp_sec.items():
                    if hasattr(acc, "get"):
                        accounts.append({
                            "name": acc.get("name", acc_key),
                            "email": str(acc.get("email", "")).strip(),
                            "user": str(
                                acc.get("user", acc.get("email", ""))
                            ).strip(),
                            "pass": str(
                                acc.get("pass", acc.get("password", ""))
                            ).strip(),
                            "server": str(
                                acc.get("server", "smtp.resend.com")
                            ).strip(),
                            "port": int(acc.get("port", 587)),
                        })
            elif isinstance(smtp_sec, list):
                for acc in smtp_sec:
                    accounts.append({
                        "name": acc.get("name", "SMTP Sender"),
                        "email": str(acc.get("email", "")).strip(),
                        "user": str(
                            acc.get("user", acc.get("email", ""))
                        ).strip(),
                        "pass": str(
                            acc.get("pass", acc.get("password", ""))
                        ).strip(),
                        "server": str(
                            acc.get("server", "smtp.resend.com")
                        ).strip(),
                        "port": int(acc.get("port", 587)),
                    })

        def_email = st.secrets.get("DEFAULT_SMTP_EMAIL", "")
        if def_email and not any(a["email"] == def_email for a in accounts):
            accounts.append({
                "name": st.secrets.get("DEFAULT_SMTP_NAME", "Default Sender"),
                "email": def_email.strip(),
                "user": st.secrets.get("DEFAULT_SMTP_USER", def_email).strip(),
                "pass": st.secrets.get("DEFAULT_SMTP_PASS", "").strip(),
                "server": st.secrets.get(
                    "DEFAULT_SMTP_SERVER", "smtp.resend.com"
                ).strip(),
                "port": int(st.secrets.get("DEFAULT_SMTP_PORT", 587)),
            })
    except Exception:
        pass

    # B. Check smtp_accounts.csv file
    csv_path = os.path.join(parent_dir, "smtp_accounts.csv")
    if os.path.exists(csv_path):
        try:
            acc_df = pd.read_csv(csv_path)
            acc_df.columns = acc_df.columns.str.strip().str.lower()
            for _, row in acc_df.iterrows():
                email_val = str(row.get("email", "")).strip()
                if email_val and not any(
                    a["email"] == email_val for a in accounts
                ):
                    accounts.append({
                        "name": str(row.get("name", "SMTP Sender")),
                        "email": email_val,
                        "user": str(row.get("user", email_val)).strip(),
                        "pass": str(
                            row.get("password", row.get("pass", ""))
                        ).strip(),
                        "server": str(
                            row.get("server", "smtp.resend.com")
                        ).strip(),
                        "port": int(row.get("port", 587)),
                    })
        except Exception:
            pass

    return accounts


smtp_list = load_smtp_accounts()

if "smtp_email" not in st.session_state and smtp_list:
    st.session_state["smtp_email"] = smtp_list[0]["email"]
    st.session_state["smtp_user"] = smtp_list[0]["user"]
    st.session_state["smtp_password"] = smtp_list[0]["pass"]
    st.session_state["smtp_server"] = smtp_list[0]["server"]
    st.session_state["smtp_port"] = smtp_list[0]["port"]
    st.session_state["smtp_name"] = smtp_list[0]["name"]

TEMPLATES = {
    "Custom (Blank)": """<p>Hello {Name},</p>
<p>I hope this email finds you well.</p>
<p>Write your message here...</p>""",
    "Quick Update": """
<div style="font-family: Arial, sans-serif; padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <p>Hi {Name},</p>
    <p>We wanted to send you a quick update regarding your account.</p>
    <p>Best regards,<br>Team</p>
</div>
""",
}


def extract_name_from_email(email_str):
    if not email_str or "@" not in str(email_str):
        return "there"
    local_part = str(email_str).split("@")[0]
    clean_part = re.sub(r"[0-9_\-\.]+", " ", local_part).strip()
    words = [w.capitalize() for w in clean_part.split() if w]
    return words[0] if words else "there"


# --- 2. SIDEBAR CONFIG ---
with st.sidebar:
    st.divider()
    st.markdown("**⚙️ Select SMTP Account**")

    if smtp_list:
        acc_labels = [f"{acc['name']} ({acc['email']})" for acc in smtp_list]
        selected_acc_idx = st.selectbox(
            "Available Accounts:",
            range(len(acc_labels)),
            format_func=lambda x: acc_labels[x],
        )
        selected_acc = smtp_list[selected_acc_idx]

        st.session_state["smtp_email"] = selected_acc["email"]
        st.session_state["smtp_user"] = selected_acc["user"]
        st.session_state["smtp_password"] = selected_acc["pass"]
        st.session_state["smtp_server"] = selected_acc["server"]
        st.session_state["smtp_port"] = selected_acc["port"]
        st.session_state["smtp_name"] = selected_acc["name"]
    else:
        st.warning("⚠️ No pre-saved accounts found in TOML/CSV")

    st.markdown("**Edit Current Credentials:**")
    s_email = st.text_input(
        "Sender Email (From):", value=st.session_state.get("smtp_email", "")
    )
    s_user = st.text_input(
        "SMTP Username:", value=st.session_state.get("smtp_user", "")
    )
    s_pass = st.text_input(
        "App Password / API Key:",
        value=st.session_state.get("smtp_password", ""),
        type="password",
    )
    s_server = st.text_input(
        "SMTP Server:",
        value=st.session_state.get("smtp_server", "smtp.resend.com"),
    )
    s_port = st.number_input(
        "SMTP Port:",
        value=int(st.session_state.get("smtp_port", 587)),
        step=1,
    )
    s_name = st.text_input(
        "Sender Name:", value=st.session_state.get("smtp_name", "Bulk Mailer")
    )

    if st.button(
        "💾 Save Active Credentials", type="primary", use_container_width=True
    ):
        st.session_state["smtp_email"] = s_email.strip()
        st.session_state["smtp_user"] = s_user.strip()
        st.session_state["smtp_password"] = s_pass.strip()
        st.session_state["smtp_server"] = s_server.strip()
        st.session_state["smtp_port"] = s_port
        st.session_state["smtp_name"] = s_name.strip()
        st.success("✅ Credentials Saved!")
        st.rerun()

    st.divider()
    if st.button("🚪 Logout App"):
        st.session_state["authenticated"] = False
        st.success("👋 Logged out!")
        st.rerun()

# --- 3. MAIN UI ---
st.markdown("**📧 Single Column Mail Sender**")
st.caption(
    "Send emails using CSV containing only Email IDs. Names will be"
    " auto-extracted if `{Name}` is used."
)

if st.session_state.get("smtp_email"):
    st.info(
        f"📧 **Active Sender:** `{st.session_state['smtp_name']} <{st.session_state['smtp_email']}>` ({st.session_state['smtp_server']}:{st.session_state['smtp_port']})"
    )
else:
    st.warning("⚠️ Pehle Sidebar me SMTP Details select ya enter karein!")
    st.stop()

# --- STEP A: SINGLE COLUMN CSV UPLOAD ---
st.markdown("**1. Upload Email CSV**")
uploaded_file = st.file_uploader(
    "Upload CSV containing Email list:", type=["csv"]
)

df = None
email_col = None
list_name = "Default_List"

if uploaded_file is not None:
    try:
        list_name = os.path.splitext(uploaded_file.name)[0]
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()
        if len(df.columns) == 0:
            st.error("❌ CSV file is empty!")
            df = None
        else:
            email_col = df.columns[0]
            for col in df.columns:
                if col.lower() == "email":
                    email_col = col
                    break

            df["Extracted_Name"] = (
                df[email_col].astype(str).apply(extract_name_from_email)
            )
            st.success(f"✅ CSV Loaded! Total Emails: {len(df)}")
            st.info(
                f"📌 **List Name:** `{list_name}` | **Targeted Email Column:**"
                f" `{email_col}`"
            )
            st.dataframe(df.head(5), use_container_width=True)
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")

st.divider()

# --- STEP B: TEMPLATE & EDITOR ---
st.markdown("**2. Email Content & Template**")
selected_template_name = st.selectbox(
    "Select Template:", list(TEMPLATES.keys())
)
template_content = TEMPLATES[selected_template_name]

subject_input = st.text_input("Email Subject:", value="Update for {Name}")

editor_content = st_quill(
    value=template_content,
    html=True,
    key=f"quill_single_{selected_template_name}",
)

st.divider()

# --- STEP C: BULK SENDING LOGIC ---
st.markdown("**3. Start Sending Campaign**")
notification_box = st.container()

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

    # Load history for Auto-Resume
    already_sent_emails = set()
    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(
                HISTORY_FILE, on_bad_lines="skip", engine="python"
            )
            target_col = (
                "Recipient"
                if "Recipient" in history_df.columns
                else ("Email" if "Email" in history_df.columns else None)
            )
            if target_col and "Status" in history_df.columns:
                already_sent_emails = set(
                    history_df[
                        history_df["Status"]
                        .astype(str)
                        .str.contains("Sent|✅", na=False, case=False)
                    ][target_col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )
        except Exception as e:
            st.warning(f"History load nahi ho saki: {e}")

    with notification_box:
        progress_bar = st.progress(0)
        status_text = st.empty()
        success_count, failed_count, skipped_count = 0, 0, 0
        logs = []

        for index, row in df.iterrows():
            recipient_email = (
                str(row[email_col]).strip() if pd.notna(row[email_col]) else ""
            )
            recipient_name = extract_name_from_email(recipient_email)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Auto-Resume Check
            if recipient_email.lower() in already_sent_emails:
                skipped_count += 1
                progress_bar.progress((index + 1) / total_records)
                status_text.text(
                    f"⏩ Skipped {index + 1}/{total_records}: {recipient_email}"
                    " (Already Sent)"
                )
                continue

            # Invalid Email Check
            if not recipient_email or "@" not in recipient_email:
                failed_count += 1
                log_data = {
                    "Timestamp": now_str,
                    "List Name": list_name,
                    "Sender": sender_email,
                    "Name": recipient_name,
                    "Recipient": recipient_email,
                    "Email": recipient_email,
                    "Subject": subject_input,
                    "Status": "Failed ❌",
                    "Reason": "Invalid Email",
                }
                logs.append(log_data)
                save_to_history(log_data, HISTORY_FILE)
                continue

            custom_subject = subject_input.replace("{Name}", recipient_name)
            custom_body = editor_content.replace("{Name}", recipient_name)

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    msg = MIMEMultipart("alternative")
                    msg["From"] = formataddr((sender_name, sender_email))
                    msg["To"] = recipient_email
                    msg["Subject"] = custom_subject

                    clean_formatted_html = f"""
                    <!DOCTYPE html>
                    <html>
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
                    log_data = {
                        "Timestamp": now_str,
                        "List Name": list_name,
                        "Sender": sender_email,
                        "Name": recipient_name,
                        "Recipient": recipient_email,
                        "Email": recipient_email,
                        "Subject": custom_subject,
                        "Status": "Sent ✅",
                        "Reason": "Success",
                    }
                    logs.append(log_data)
                    save_to_history(log_data, HISTORY_FILE)
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        failed_count += 1
                        log_data = {
                            "Timestamp": now_str,
                            "List Name": list_name,
                            "Sender": sender_email,
                            "Name": recipient_name,
                            "Recipient": recipient_email,
                            "Email": recipient_email,
                            "Subject": custom_subject,
                            "Status": "Failed ❌",
                            "Reason": str(e),
                        }
                        logs.append(log_data)
                        save_to_history(log_data, HISTORY_FILE)

            progress_bar.progress((index + 1) / total_records)
            status_text.text(
                f"Sending {index + 1}/{total_records}: {recipient_email}"
            )
            time.sleep(0.2)

        st.success(
            f"🎯 **Campaign Finished!** Sent: **{success_count}** | Skipped:"
            f" **{skipped_count}** | Failed: **{failed_count}**"
        )

        if logs:
            st.markdown("**Campaign Summary Report**")
            log_df = pd.DataFrame(logs)
            st.dataframe(log_df, use_container_width=True)

            safe_subject = (
                re.sub(r"[^\w\s-]", "", subject_input)
                .strip()
                .replace(" ", "_")
                or "Campaign_Report"
            )
            today_date = time.strftime("%Y-%m-%d")
            download_filename = f"{list_name}_{safe_subject}_{today_date}.csv"

            st.download_button(
                label="📥 Download Campaign Report (CSV)",
                data=log_df.to_csv(index=False).encode("utf-8"),
                file_name=download_filename,
                mime="text/csv",
                type="primary",
            )

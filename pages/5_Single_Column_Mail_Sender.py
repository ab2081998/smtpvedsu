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

def parse_multi_line_input(text):
    if not text:
        return []
    return [
        line.strip()
        for line in re.split(r"[\n,;]+", text)
        if line and line.strip()
    ]

def parse_credentials(text):
    creds = []
    lines = parse_multi_line_input(text)
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            creds.append(
                {"email": parts[0].strip(), "password": parts[1].strip()}
            )
        elif "," in line:
            parts = line.split(",", 1)
            creds.append(
                {"email": parts[0].strip(), "password": parts[1].strip()}
            )
    return creds

def get_dynamic_senders(manual_text=""):
    senders = []
    # Priority 1: Manual text input
    if manual_text.strip():
        senders = parse_credentials(manual_text)
        if senders:
            return senders, "Manual Text Area"

    # Priority 2: secrets.toml (SMTP_SENDERS string)
    if "SMTP_SENDERS" in st.secrets:
        senders = parse_credentials(st.secrets["SMTP_SENDERS"])
        if senders:
            return senders, "secrets.toml (SMTP_SENDERS)"

    # Priority 3: secrets.toml ([smtp_accounts.*] format)
    if "smtp_accounts" in st.secrets:
        smtp_accs = st.secrets["smtp_accounts"]
        for acc_key in smtp_accs:
            acc = smtp_accs[acc_key]
            em = acc.get("email")
            pw = acc.get("pass") or acc.get("password")
            if em and pw:
                senders.append({
                    "email": str(em).strip(),
                    "password": str(pw).strip(),
                    "server": acc.get("server"),
                    "port": acc.get("port")
                })
        if senders:
            return senders, "secrets.toml ([smtp_accounts])"

    # Priority 4: secrets.toml (smtp.accounts format)
    if "smtp" in st.secrets and "accounts" in st.secrets["smtp"]:
        for acc in st.secrets["smtp"]["accounts"]:
            if "email" in acc and "password" in acc:
                senders.append({"email": str(acc["email"]).strip(), "password": str(acc["password"]).strip()})
        if senders:
            return senders, "secrets.toml (smtp.accounts)"

    return [], "None"

st.title("📧 Single Column Campaign Sender (With Auto Resume)")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("1. SMTP Senders Setup")
    smtp_host = st.text_input("SMTP Server", value="smtp.gmail.com")
    smtp_port = st.number_input("SMTP Port", value=587, step=1)
    
    sender_text = st.text_area(
        "Sender Accounts (Optional: leave empty to auto-load from secrets.toml)",
        height=150,
        placeholder="email:password or email,password\n(If empty, system auto-fetches from TOML)"
    )
    
    senders, source_used = get_dynamic_senders(sender_text)
    if senders:
        st.success(f"✅ Loaded {len(senders)} senders automatically from: **{source_used}**")
    else:
        st.warning("⚠️ No senders found in Manual Input or secrets.toml!")

with col_right:
    st.subheader("2. Recipient Data Setup")
    recipients_file = st.file_uploader(
        "Upload Recipients CSV/Excel", type=["csv", "xlsx"]
    )
    list_name = st.text_input("Campaign List Name", value="Single_Col_Campaign")

    recipient_df = pd.DataFrame()
    if recipients_file:
        try:
            if recipients_file.name.endswith(".csv"):
                recipient_df = pd.read_csv(recipients_file)
            else:
                recipient_df = pd.read_excel(recipients_file)
            st.success(f"✅ Loaded {len(recipient_df)} recipients!")
        except Exception as e:
            st.error(f"❌ File read error: {e}")

st.divider()

st.subheader("3. Campaign Message Setup")
sender_name = st.text_input("Display Sender Name", value="Support Team")
subject_template = st.text_input(
    "Subject Line", value="Important Update for {Name}"
)

st.markdown("**Email Body (HTML/Text):**")
email_body = st_quill(
    placeholder="Write your email here...", key="single_col_quill"
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
    if not senders:
        st.error("❌ Sender accounts enter karein ya secrets.toml setup karein!")
        st.stop()

    if recipient_df.empty:
        st.error("❌ Valid Recipient file upload karein!")
        st.stop()

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
                f"ℹ️ Auto-Resume Active: Pichle 48 hours me {len(already_sent_emails)} emails already sent hain. Unhe skip kiya jayega."
            )

    progress_bar = st.progress(0)
    status_text = st.empty()
    logs_container = st.container()

    total_recipients = len(recipient_df)
    sender_index = 0
    total_senders = len(senders)

    for idx, row in recipient_df.iterrows():
        email = ""
        for col in recipient_df.columns:
            if "email" in col.lower() or "recipient" in col.lower():
                email = str(row[col]).strip()
                break
        if not email and len(recipient_df.columns) > 0:
            email = str(row.iloc[0]).strip()

        if enable_auto_resume and email.lower() in already_sent_emails:
            with logs_container:
                st.write(f"⏭️ Skipped (Already sent in last 48h): {email}")
            progress_bar.progress((idx + 1) / total_recipients)
            continue

        curr_sender = senders[sender_index % total_senders]
        sender_email = curr_sender["email"]
        sender_pass = curr_sender["password"]
        
        # TOML account config override if present
        active_host = curr_sender.get("server") or smtp_host
        active_port = int(curr_sender.get("port") or smtp_port)
        
        sender_index += 1

        rec_name = str(row.get("Name", row.get("name", "Customer")))

        custom_subject = subject_template.replace("{Name}", rec_name)
        custom_body = email_body.replace("{Name}", rec_name)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_success = False
        error_reason = "Success"

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((sender_name, sender_email))
            msg["To"] = email
            msg["Subject"] = custom_subject
            msg.attach(MIMEText(custom_body, "html"))

            server = smtplib.SMTP(active_host, active_port, timeout=15)
            server.starttls()
            server.login(sender_email, sender_pass)
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
            "Name": rec_name,
            "Recipient": email,
            "Subject": custom_subject,
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

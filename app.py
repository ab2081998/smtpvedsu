import hmac
import os
import time
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION (Navigation Bar Closed By Default) ---
st.set_page_config(
    page_title="CRM & Mail Portal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",  # Navigation bar closed by default
)

# --- PERSISTENT SESSION TIMEOUT (4-HOURS) ---
SESSION_TIMEOUT_SECONDS = 4 * 3600  # 4 Hours


def check_password():
    """Handles passcode authentication with persistent URL query parameters."""
    current_time = time.time()
    auth_param = st.query_params.get("session_auth", None)
    login_time_param = st.query_params.get("session_time", None)

    if auth_param == "true" and login_time_param:
        try:
            if current_time - float(login_time_param) < SESSION_TIMEOUT_SECONDS:
                st.session_state["authenticated"] = True
                return True
        except ValueError:
            pass

    if not st.session_state.get("authenticated", False):
        st.markdown(
            "<h2 style='text-align: center;'>🔒 CRM Portal Login</h2>",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info("Enter master passcode to unlock CRM tools.")
            entered_password = st.text_input(
                "Enter Passcode:", type="password", key="main_passcode_input"
            )
            if st.button("Unlock Dashboard", type="primary", use_container_width=True):
                correct_password = st.secrets.get("PASSWORD", "root")
                if hmac.compare_digest(entered_password, correct_password):
                    st.session_state["authenticated"] = True
                    st.query_params["session_auth"] = "true"
                    st.query_params["session_time"] = str(current_time)
                    st.success("✅ Access Granted!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect Passcode! Please try again.")
        return False
    return True


# Run Authentication Check
if not check_password():
    st.stop()

# --- MAIN CRM HOME DASHBOARD & HEADER ---
col_title, col_logout = st.columns([4, 1])

with col_title:
    st.title("🎯 Smart CRM & Bulk Outreach Suite")

with col_logout:
    st.write("")  # Margin adjustment
    if st.button("🚪 Logout App", use_container_width=True):
        st.session_state["authenticated"] = False
        if "session_auth" in st.query_params:
            del st.query_params["session_auth"]
        if "session_time" in st.query_params:
            del st.query_params["session_time"]
        st.rerun()

st.markdown(
    "Welcome to your **all-in-one Customer Relationship Management (CRM) & Automated Email Portal**."
)
st.divider()

# --- CRM HERO & FEATURES BANNER ---
col_left, col_right = st.columns([2, 1])
with col_left:
    st.subheader("💡 Why Use This CRM Suite?")
    st.markdown(
        """
    * 📬 **Automated Bulk Emailing:** Send personalized campaigns with simple CSV files.
    * 🎯 **Smart Personalization:** Auto-handles missing contact names with fallback greetings (*Hi there*).
    * 📊 **Live Campaign Tracking:** Real-time progress bars, success logs, and failure analytics.
    * 🔒 **Secure SMTP Credentials:** Safely store app credentials per session.
    """
    )

with col_right:
    st.info(
        "📌 **Quick Navigation**\n\nUse the sidebar menu at the **top-left (>` icon)** to access tools like **Bulk Mail Sender** and **Email Extractors**."
    )

st.divider()

# --- SAMPLE CSV DOWNLOAD SECTION ---
st.subheader("📁 Sample CSV Download (`testsmtp.csv`)")
st.caption(
    "Use this sample template for your bulk mail campaigns. Column 1 = Name | Column 2 = Email"
)

# Read 'testsmtp.csv' from main directory
csv_file_path = "testsmtp.csv"
sample_df = None

if os.path.exists(csv_file_path):
    try:
        sample_df = pd.read_csv(csv_file_path)
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")

# Fallback dataframe if file is missing
if sample_df is None:
    sample_df = pd.DataFrame(
        {
            "Name": ["Rahul Sharma", "", "Priya Verma"],
            "Email": [
                "rahul@example.com",
                "info@example.com",
                "priya@example.com",
            ],
        }
    )

csv_data = sample_df.to_csv(index=False).encode("utf-8")

# Direct Download Button in App for Logged-in user
st.download_button(
    label="📥 Download testsmtp.csv",
    data=csv_data,
    file_name="testsmtp.csv",
    mime="text/csv",
    type="primary",
)

# --- PREVIEW OF SAMPLE CSV ---
st.write("#### 📄 Sample Data Preview")
st.dataframe(sample_df, use_container_width=True)
st.divider()

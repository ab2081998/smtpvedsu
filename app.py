import os
import time
import pandas as pd
import streamlit as st
from auth import require_login

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CRM & Mail Portal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 🔒 Mandatory Security Check
require_login()

# --- HEADER & LOGOUT SECTION ---
col_title, col_logout = st.columns([4, 1])
with col_title:
    st.title("🎯 Smart CRM & Bulk Outreach Suite")
with col_logout:
    st.write("")  # Vertical alignment spacing
    if st.button("🚪 Logout App", use_container_width=True):
        st.session_state["authenticated"] = False
        if "session_auth" in st.query_params:
            del st.query_params["session_auth"]
        if "session_time" in st.query_params:
            del st.query_params["session_time"]
        st.rerun()

st.markdown(
    "Welcome to your **centralized CRM & Automation Hub**. Quick-launch your marketing and email extraction workflows below."
)
st.divider()

# --- QUICK ACCESS / PAGES HYPERLINKS NAVIGATION ---
st.subheader("⚡ Quick Navigation & Suite Tools")
st.caption(
    "Click on any tool below to open it directly or access them from the left sidebar."
)

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("### ⭐ Important Mails Reader")
        st.write(
            "Fetch and view important starred emails directly with HTML preview support."
        )
        st.page_link(
            "pages/2_Important_Mails.py", label="Open Reader", icon="⭐"
        )

    with st.container(border=True):
        st.markdown("### 📨 Bulk Mail Sender")
        st.write(
            "Send personalized email campaigns at scale using dynamic CSV list imports."
        )
        st.page_link(
            "pages/4_Bulk_Mail_Sender.py", label="Launch Bulk Sender", icon="📨"
        )

with col2:
    with st.container(border=True):
        st.markdown("### 📋 Single Column Mailer")
        st.write(
            "Simplified mail dispatcher for single-column contact lists without headers."
        )
        st.page_link(
            "pages/5_Single_Column_Mail_Sender.py",
            label="Open Single Column Mailer",
            icon="📋",
        )

    with st.container(border=True):
        st.markdown("### 🔍 Email Extractor Tool")
        st.write(
            "Extract clean email addresses automatically from raw unorganized text blocks."
        )
        st.page_link(
            "pages/6_Email_Extractor.py", label="Open Extractor", icon="🔍"
        )

st.divider()

# --- CRM METRICS & SUITE SUMMARY ---
st.subheader("📊 Outreach Metrics Overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric(label="Active SMTP Engine", value="Ready", delta="100% Operational")
m2.metric(label="Session Timeout", value="4 Hours", delta="Auto-renewed")
m3.metric(label="Recipient Fallback", value="Enabled", delta="Hi there")
m4.metric(label="Security Mode", value="Passcode Protected", delta="TOML Locked")

st.divider()

# --- SAMPLE CSV DOWNLOAD SECTION ---
st.subheader("📁 Campaign Template (`testsmtp.csv`)")
st.caption("Download the standardized template to prepare your email lists.")

csv_file_path = "testsmtp.csv"
sample_df = None

if os.path.exists(csv_file_path):
    try:
        sample_df = pd.read_csv(csv_file_path)
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")

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

col_btn, col_preview = st.columns([1, 2])
with col_btn:
    st.download_button(
        label="📥 Download Template CSV",
        data=csv_data,
        file_name="testsmtp.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

with col_preview:
    with st.expander("📄 Preview CSV Structure"):
        st.dataframe(sample_df, use_container_width=True)

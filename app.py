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
    st.write("")  # Alignment spacing
    if st.button("🚪 Logout App", use_container_width=True):
        st.session_state["authenticated"] = False
        if "session_auth" in st.query_params:
            del st.query_params["session_auth"]
        if "session_time" in st.query_params:
            del st.query_params["session_time"]
        st.rerun()

st.markdown(
    "Welcome to your **centralized CRM & Automation Hub**. Quick-launch your marketing workflows below."
)
st.divider()

# --- CSV PREPARATION LOGIC ---
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

# --- TOP SECTION: ⚡ QUICK NAVIGATION & CSV BUTTON ---
st.subheader("⚡ Quick Navigation")

nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)

with nav_col1:
    st.page_link(
        "pages/2_Important_Mails.py",
        label="⭐ Important Mails Reader",
        use_container_width=True,
    )

with nav_col2:
    st.page_link(
        "pages/4_Bulk_Mail_Sender.py",
        label="📨 Bulk Mail Sender",
        use_container_width=True,
    )

with nav_col3:
    st.page_link(
        "pages/5_Single_Column_Mail_Sender.py",
        label="📋 Single Column Mailer",
        use_container_width=True,
    )

with nav_col4:
    st.download_button(
        label="📥 Download Template CSV",
        data=csv_data,
        file_name="testsmtp.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

st.divider()

# --- BOTTOM SECTION: 💡 WHY USE THIS CRM SUITE ---
st.subheader("💡 Why Use This CRM Suite?")
st.markdown(
    """
* 📬 **Automated Bulk Emailing:** Send personalized campaigns with simple CSV files.
* 🎯 **Smart Personalization:** Auto-handles missing contact names with fallback greetings (*Hi there*).
* 📊 **Live Campaign Tracking:** Real-time progress bars, success logs, and failure analytics.
* 🔒 **Secure SMTP Credentials:** Safely store app credentials per session.
"""
)

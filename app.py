import os
import time
import pandas as pd
import streamlit as st
from auth import require_login

# Page Config
st.set_page_config(
    page_title="CRM & Mail Portal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 🔒 Mandatory Security Check
require_login()

# --- MAIN DASHBOARD CONTENT ---
col_title, col_logout = st.columns([4, 1])
with col_title:
    st.title("🎯 Smart CRM & Bulk Outreach Suite")
with col_logout:
    if st.button("🚪 Logout App", use_container_width=True):
        st.session_state["authenticated"] = False
        if "session_auth" in st.query_params:
            del st.query_params["session_auth"]
        if "session_time" in st.query_params:
            del st.query_params["session_time"]
        st.rerun()

st.write("Welcome to your CRM Dashboard!")

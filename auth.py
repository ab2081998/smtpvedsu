import hmac
import time
import streamlit as st

SESSION_TIMEOUT_SECONDS = 4 * 3600  # 4 Hours

def require_login():
    """Call this function at the top of every page to enforce authentication."""
    current_time = time.time()
    auth_param = st.query_params.get("session_auth", None)
    login_time_param = st.query_params.get("session_time", None)

    # 1. Check Query Parameters for persistent session
    if auth_param == "true" and login_time_param:
        try:
            saved_time = float(login_time_param)
            if current_time - saved_time < SESSION_TIMEOUT_SECONDS:
                st.session_state["authenticated"] = True
                st.session_state["login_time"] = saved_time
            else:
                st.query_params.clear()
                st.session_state["authenticated"] = False
        except ValueError:
            st.query_params.clear()

    # 2. Check Session State
    if st.session_state.get("authenticated", False):
        if current_time - st.session_state.get("login_time", 0) < SESSION_TIMEOUT_SECONDS:
            return True

    # 3. If Not Authenticated, Show Login UI & Stop execution
    st.title("🔒 Password Protected Page")
    password_input = st.text_input("Enter Passcode to Access:", type="password")

    if st.button("Login", type="primary"):
        app_password = st.secrets.get("APP_PASSWORD", "")
        if app_password and hmac.compare_digest(password_input, app_password):
            st.session_state["authenticated"] = True
            st.session_state["login_time"] = current_time
            st.query_params["session_auth"] = "true"
            st.query_params["session_time"] = str(current_time)
            st.rerun()
        else:
            st.error("❌ Incorrect Passcode!")
    
    st.stop()  # Age ka code run hone se rok dega

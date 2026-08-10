import hmac
import time
import streamlit as st

# Session Timeout (4 Hours)
SESSION_TIMEOUT_SECONDS = 4 * 3600

def require_login():
    """Handles passcode authentication using secrets.toml & URL query parameters."""
    current_time = time.time()
    auth_param = st.query_params.get("session_auth", None)
    login_time_param = st.query_params.get("session_time", None)

    # 1. Active Session Check
    if auth_param == "true" and login_time_param:
        try:
            if current_time - float(login_time_param) < SESSION_TIMEOUT_SECONDS:
                st.session_state["authenticated"] = True
                return True
        except ValueError:
            pass

    # 2. Not Authenticated -> Hide Sidebar & Navigation Controls
    if not st.session_state.get("authenticated", False):
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {display: none !important;}
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="collapsedControl"] {display: none !important;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        # --- 1. TOP MESSAGE ---
        st.title("🎯 Smart CRM & Bulk Outreach Suite")
        st.markdown(
            "Welcome to your **centralized CRM & Automation Hub**. Quick-launch your marketing workflows below."
        )

        st.divider()

        # --- 2. LOGIN FORM (IN MIDDLE) ---
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
                # Fetch password from secrets.toml (Fallback: 'root')
                correct_password = st.secrets.get("PASSWORD", "root")

                if hmac.compare_digest(entered_password, correct_password):
                    st.session_state["authenticated"] = True
                    st.query_params["session_auth"] = "true"
                    st.query_params["session_time"] = str(current_time)
                    st.success("✅ Access Granted!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect Passcode! Please try again.")

        st.divider()

        # --- 3. REST OF THE MESSAGE (AT BOTTOM) ---
        st.markdown(
            """
### 💡 Why Use This CRM Suite?
* 📬 **Automated Bulk Emailing:** Send personalized campaigns with simple CSV files.
* 🎯 **Smart Personalization:** Auto-handles missing contact names with fallback greetings (*Hi there*).
* 📊 **Live Campaign Tracking:** Real-time progress bars, success logs, and failure analytics.
* 🔒 **Secure SMTP Credentials:** Safely store app credentials per session.
"""
        )

        st.stop()

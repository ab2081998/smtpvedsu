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

    # 2. Not Authenticated -> Hide Sidebar & Styled Centered Layout
    if not st.session_state.get("authenticated", False):
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {display: none !important;}
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="collapsedControl"] {display: none !important;}
            
            /* Center Align Container Content */
            .main .block-container {
                max-width: 800px;
                padding-top: 2rem !important;
                padding-bottom: 2rem !important;
                margin: auto;
            }
            .centered-text {
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # --- 1. TOP HEADER (CENTERED) ---
        st.markdown(
            "<h1 style='text-align: center;'>🎯 Smart CRM & Bulk Outreach Suite</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; font-size: 1.1rem; color: #555;'>"
            "Welcome to your <b>centralized CRM & Automation Hub</b>. Quick-launch your marketing workflows below."
            "</p>",
            unsafe_allow_html=True,
        )

        st.divider()

        # --- 2. LOGIN CARD (CENTERED) ---
        st.markdown(
            "<h3 style='text-align: center;'><b>🔒 CRM Portal Login</b></h3>",
            unsafe_allow_html=True,
        )

        # Center Column for Login Inputs
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.info("Enter master passcode to unlock CRM tools.", icon="🔑")
            entered_password = st.text_input(
                "Enter Passcode:", type="password", key="main_passcode_input", placeholder="••••••••"
            )

            if st.button("Unlock Dashboard 🚀", type="primary", use_container_width=True):
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

        # --- 3. FEATURES LIST (CENTERED BOX) ---
        st.markdown(
            """
            <div style='text-align: center;'>
                <h3>💡 Why Use This CRM Suite?</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Centered Box for Bullets
        f_col1, f_col2, f_col3 = st.columns([0.15, 0.7, 0.15])
        with f_col2:
            st.markdown(
                """
* 📬 **Automated Bulk Emailing:** Send personalized campaigns with simple CSV files.
* 🎯 **Smart Personalization:** Auto-handles missing contact names with fallback greetings (*Hi there*).
* 📊 **Live Campaign Tracking:** Real-time progress bars, success logs, and failure analytics.
* 🔒 **Secure SMTP Credentials:** Safely store app credentials per session.
                """
            )

        st.stop()

import os
import sys
import pandas as pd
import streamlit as st

# --- AUTHENTICATION CHECK ---
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import auth

if hasattr(auth, "require_auth"):
    auth.require_auth()
elif hasattr(auth, "check_auth"):
    auth.check_auth()

if not st.session_state.get("authenticated", False):
    st.subheader("🔒 Page Locked")
    st.stop()

# --- PAGE CONFIG & TITLE ---
st.title("📊 Email Logs & History Dashboard")
st.caption("Yahan aap bheje gaye sabhi emails ka Date, Time, Subject, Recipient, aur Status real-time dekh sakte hain.")

HISTORY_FILE = "email_history.csv"

if os.path.exists(HISTORY_FILE):
    try:
        df = pd.read_csv(HISTORY_FILE)

        if df.empty:
            st.info("ℹ️ History file abhi khali hai.")
        else:
            # Stats Summary
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Executions", len(df))
            col2.metric("Successfully Sent", len(df[df["Status"].astype(str).str.contains("Sent", na=False)]))
            col3.metric("Failed Mails", len(df[df["Status"].astype(str).str.contains("Failed", na=False)]))

            st.divider()

            # Search Bar
            search_query = st.text_input("🔍 Search Logs (Subject, Email, Date):")
            if search_query:
                filtered_df = df[
                    df["Recipient"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["Subject"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["Timestamp"].astype(str).str.contains(search_query, case=False, na=False)
                ]
            else:
                filtered_df = df

            # Display Data Table
            st.dataframe(filtered_df, use_container_width=True)

            col_down, col_clear = st.columns([3, 1])

            with col_down:
                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Complete History (CSV)",
                    data=csv_data,
                    file_name="complete_email_history.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True,
                )

            with col_clear:
                if st.button("🗑️ Clear History", use_container_width=True):
                    os.remove(HISTORY_FILE)
                    st.success("History clear ho gayi!")
                    st.rerun()

    except Exception as e:
        st.error(f"Error reading history file: {e}")
else:
    st.info("ℹ️ Abhi tak koi Email History record nahi hui hai. Mail bhejne ke baad data yahan dikhega.")

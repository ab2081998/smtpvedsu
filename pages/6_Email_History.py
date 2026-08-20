from datetime import datetime
import os
import sys
import pandas as pd
import streamlit as st

# --- PAGE CONFIG (FULL PAGE / WIDE LAYOUT) ---
st.set_page_config(
    page_title="Email Logs & History Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- 0. AUTHENTICATION & SESSION CHECK ---
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
import auth

if hasattr(auth, "require_auth"):
    auth.require_auth()
elif hasattr(auth, "check_auth"):
    auth.check_auth()

# Fallback password unlock form
if not st.session_state.get("authenticated", False):
    st.subheader("🔒 Page Locked")
    password_input = st.text_input("Enter password to unlock page:", type="password")
    correct_password = st.secrets.get("APP_PASSWORD", "admin123")
    if st.button("Unlock"):
        if password_input == correct_password:
            st.session_state["authenticated"] = True
            st.success("Unlocked successfully!")
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
            st.stop()

# --- CLEAN & FULL PAGE CSS ---
st.markdown(
    """
<style>
/* Top padding reduce karne ke liye taaki full page utilize ho */
.block-container {padding-top: 2rem !important; padding-bottom: 2rem !important; max-width: 95% !important; }
/* Minimal & Sleek Metric Cards */
div[data-testid="stMetric"] {background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px 20px; transition: all 0.2s ease; }
div[data-testid="stMetric"]:hover {border-color: rgba(255, 255, 255, 0.2); background-color: rgba(255, 255, 255, 0.05); }
div[data-testid="stMetricLabel"] {font-size: 0.85rem !important; font-weight: 500 !important; opacity: 0.7; }
div[data-testid="stMetricValue"] {font-size: 1.7rem !important; font-weight: 600 !important; }
/* Clean Section Headers */
h3 {font-weight: 600 !important; font-size: 1.25rem !important; margin-top: 0.8rem !important; }
/* Soft Info Alert Box */
div[data-testid="stAlert"] {border-radius: 8px !important; border: 1px solid rgba(59, 130, 246, 0.2) !important; background-color: rgba(59, 130, 246, 0.04) !important; padding: 12px 16px !important; }
/* Buttons */
button[kind="primary"] {border-radius: 8px !important; font-weight: 500 !important; }
div.stButton > button {border-radius: 8px !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; font-weight: 500 !important; }
/* Full Width Dataframe Tables */
div[data-testid="stDataFrame"] {border-radius: 8px; overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# --- HEADER SECTION ---
st.title("📊 Email Logs & History Dashboard")
st.caption("Yahan aap list-wise bheje gaye sabhi emails ka Date, Time, Subject, Recipient, aur Status dekh sakte hain.")

HISTORY_FILE = "email_history.csv"

if os.path.exists(HISTORY_FILE):
    try:
        # Read CSV safely with on_bad_lines='skip'
        df = pd.read_csv(HISTORY_FILE, dtype=str, on_bad_lines="skip")

        if df.empty:
            st.info("ℹ️ History file abhi khali hai.")
        else:
            # Column fallback for older history logs
            if "List_Name" not in df.columns:
                df["List_Name"] = "Default List"

            # --- RECENT ON TOP (NEWEST FIRST SORTING) ---
            if "Timestamp" in df.columns:
                df["Timestamp_dt"] = pd.to_datetime(df["Timestamp"], errors="coerce")
                df = df.sort_values(by="Timestamp_dt", ascending=False)
            else:
                df = df.iloc[::-1]

            # Overall Top Stats Summary
            total_sent = len(df[df["Status"].astype(str).str.contains("Sent", na=False)])
            total_failed = len(df[df["Status"].astype(str).str.contains("Failed", na=False)])
            unique_lists = df["List_Name"].nunique()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Executions", len(df))
            col2.metric("Successfully Sent", total_sent)
            col3.metric("Failed Mails", total_failed)
            col4.metric("Total Lists Bheji Gayi", unique_lists)

            st.divider()

            # --- 1. LIST-WISE SUMMARY TABLE ---
            st.markdown("### 📋 List Wise Campaign Analytics")

            summary_records = []
            grouped = df.groupby(["List_Name", "Subject"], sort=False)

            for (l_name, subject_title), group in grouped:
                total_cnt = len(group)
                sent_cnt = len(group[group["Status"].astype(str).str.contains("Sent", na=False)])
                failed_cnt = len(group[group["Status"].astype(str).str.contains("Failed", na=False)])

                start_t = group["Timestamp_dt"].min()
                end_t = group["Timestamp_dt"].max()

                if pd.notnull(start_t) and pd.notnull(end_t):
                    duration_sec = (end_t - start_t).total_seconds()
                    mins = int(duration_sec // 60)
                    secs = int(duration_sec % 60)
                    time_duration = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                    time_range = f"{start_t.strftime('%I:%M %p')} - {end_t.strftime('%I:%M %p')}"
                else:
                    time_duration = "N/A"
                    time_range = "N/A"

                summary_records.append({
                    "List Name": str(l_name),
                    "Subject Title": str(subject_title),
                    "Total Emails": total_cnt,
                    "Sent ✅": sent_cnt,
                    "Failed ❌": failed_cnt,
                    "Time Interval": time_range,
                    "Duration": time_duration,
                })

            summary_df = pd.DataFrame(summary_records)
            st.dataframe(summary_df, use_container_width=True)

            # --- 2. DEEP-DIVE LIST CARDS (SHOW RECIPIENT EMAILS) ---
            st.markdown("### 📌 List Detail Cards (Recipient Emails)")
            
            for list_item in df["List_Name"].unique():
                sub_df = df[df["List_Name"] == list_item]
                total_list_mails = len(sub_df)
                sent_list_mails = len(sub_df[sub_df["Status"].astype(str).str.contains("Sent", na=False)])
                failed_list_mails = len(sub_df[sub_df["Status"].astype(str).str.contains("Failed", na=False)])

                expander_title = (
                    f"📂 List: **{list_item}** — Total: {total_list_mails} "
                    f"(✅ {sent_list_mails} Sent | ❌ {failed_list_mails} Failed)"
                )
                
                with st.expander(expander_title):
                    st.write(f"**Subject:** {sub_df['Subject'].iloc[0] if not sub_df.empty else 'N/A'}")
                    recipients_display = sub_df[["Timestamp", "Recipient", "Status", "Reason"]]
                    st.dataframe(recipients_display, use_container_width=True)

            st.divider()

            # --- 3. SEARCH & ALL LOGS TABLE ---
            st.markdown("### 🔍 All Executed Email Logs")
            search_query = st.text_input("Search Logs (List Name, Email, Subject, Date):")

            if search_query:
                filtered_df = df[
                    df["Recipient"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["Subject"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["List_Name"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["Timestamp"].astype(str).str.contains(search_query, case=False, na=False)
                ]
            else:
                filtered_df = df

            display_df = filtered_df.drop(columns=["Timestamp_dt"], errors="ignore")
            st.dataframe(display_df, use_container_width=True)

            col_down, col_clear = st.columns([3, 1])
            with col_down:
                csv_data = display_df.to_csv(index=False).encode("utf-8")
                current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dynamic_filename = f"email_history_{current_timestamp}.csv"
                st.download_button(
                    label="📥 Download CSV History",
                    data=csv_data,
                    file_name=dynamic_filename,
                    mime="text/csv",
                    type="primary",
                    use_container_width=True,
                )
            with col_clear:
                if st.button("🗑️ Clear History", use_container_width=True):
                    os.remove(HISTORY_FILE)
                    st.success("History successfully deleted!")
                    st.rerun()

    except Exception as e:
        st.error(f"Error reading history file: {e}")
else:
    st.info("ℹ️ Abhi tak koi Email History record nahi hui hai. Mail bhejne ke baad data yahan dikhega.")

import os
import sys
from datetime import datetime
import pandas as pd
import streamlit as st

# --- 0. AUTHENTICATION CHECK ---
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
st.caption("Yahan aap bheje gaye sabhi emails ka Date, Time, Subject, Recipient, aur Status dekh sakte hain.")

HISTORY_FILE = "email_history.csv"

if os.path.exists(HISTORY_FILE):
    try:
        # Special characters ko as-it-is exact format me load karne ke liye utf-8 encoding
        df = pd.read_csv(HISTORY_FILE, dtype=str)

        if df.empty:
            st.info("ℹ️ History file abhi khali hai.")
        else:
            # Stats Summary
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Executions", len(df))
            col2.metric("Successfully Sent", len(df[df["Status"].astype(str).str.contains("Sent", na=False)]))
            col3.metric("Failed Mails", len(df[df["Status"].astype(str).str.contains("Failed", na=False)]))

            st.divider()

            # --- CAMPAIGN WISE ANALYTICS / NOTES ---
            st.markdown("### 📋 Campaign Wise Summary Notes")
            
            # Datetime conversion for duration calculation
            df['Timestamp_dt'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            df['Date_Only'] = df['Timestamp_dt'].dt.strftime('%Y-%m-%d')

            summary_records = []
            
            # Subject (including special characters) aur Date wise Grouping
            grouped = df.groupby(['Subject', 'Date_Only'], sort=False)

            for (subject_title, date_val), group in grouped:
                total_cnt = len(group)
                sent_cnt = len(group[group['Status'].astype(str).str.contains('Sent', na=False)])
                failed_cnt = len(group[group['Status'].astype(str).str.contains('Failed', na=False)])

                start_t = group['Timestamp_dt'].min()
                end_t = group['Timestamp_dt'].max()

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
                    "Date": date_val if pd.notnull(date_val) else "N/A",
                    "Subject Title": str(subject_title),  # As-it-is special characters preserved
                    "Total Contacts": total_cnt,
                    "Sent ✅": sent_cnt,
                    "Failed ❌": failed_cnt,
                    "Time Interval": time_range,
                    "Duration": time_duration
                })

            summary_df = pd.DataFrame(summary_records)
            st.dataframe(summary_df, use_container_width=True)

            # Individual Clean Notes Cards
            st.markdown("**📌 Campaign Detail Cards**")
            for _, item in summary_df.iterrows():
                # Raw text/markdown escape to keep special characters as-is
                clean_title = item['Subject Title'].replace("*", "\\*").replace("_", "\\_")
                st.info(
                    f"📅 **Date:** `{item['Date']}` | ✉️ **Subject:** **{clean_title}**\n\n"
                    f"👉 **Total Contacts:** {item['Total Contacts']} ({item['Sent ✅']} Sent, {item['Failed ❌']} Failed) "
                    f"| ⏱️ **Time Taken:** `{item['Duration']}` ({item['Time Interval']})"
                )

            st.divider()

            # --- SEARCH & ALL LOGS TABLE ---
            st.markdown("### 🔍 All Executed Email Logs")
            search_query = st.text_input("Search Logs (Subject, Email, Date):")
            
            if search_query:
                filtered_df = df[
                    df["Recipient"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["Subject"].astype(str).str.contains(search_query, case=False, na=False)
                    | df["Timestamp"].astype(str).str.contains(search_query, case=False, na=False)
                ]
            else:
                filtered_df = df

            # Original Dataframe View (dropping temporary datetime helper columns)
            display_df = filtered_df.drop(columns=['Timestamp_dt', 'Date_Only'], errors='ignore')
            st.dataframe(display_df, use_container_width=True)

            col_down, col_clear = st.columns([3, 1])

            with col_down:
                csv_data = display_df.to_csv(index=False).encode("utf-8")
                
                # File name me dynamic Date aur Time mention karne ka logic
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

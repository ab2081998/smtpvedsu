from datetime import datetime
import os
import sys
import pandas as pd
import streamlit as st

# --- 0. AUTHENTICATION & PATH SETUP ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Path Resolution for History CSV File
possible_paths = [
    os.path.join(parent_dir, "email_history.csv"),
    os.path.join(os.path.dirname(__file__), "email_history.csv"),
    "email_history.csv"
]

HISTORY_FILE = None
for p in possible_paths:
    if os.path.exists(p):
        HISTORY_FILE = p
        break

if not HISTORY_FILE:
    HISTORY_FILE = os.path.join(parent_dir, "email_history.csv")

try:
    import auth
    if hasattr(auth, "require_auth"):
        auth.require_auth()
    elif hasattr(auth, "check_auth"):
        auth.check_auth()
    else:
        if not st.session_state["authenticated"]:
            st.warning("🔒 Access Restricted! Please enter root password.")
            user_pass = st.text_input("Please enter Password", type="password", key="hist_auth_pass_input")
            CORRECT_PASSWORD = st.secrets.get("PASSWORD", "root")
            if st.button("Unlock Page"):
                if user_pass == CORRECT_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.success("✅ Password correct!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect password!")
            st.stop()
except ImportError:
    if not st.session_state["authenticated"]:
        st.warning("🔒 Access Restricted! Please enter password.")
        user_pass = st.text_input("Please enter Password", type="password", key="hist_auth_pass_input")
        CORRECT_PASSWORD = st.secrets.get("PASSWORD", "root")
        if st.button("Unlock Page"):
            if user_pass == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.success("✅ Password correct!")
                st.rerun()
            else:
                st.error("❌ Incorrect password!")
        st.stop()

# --- 1. MAIN UI ---
st.markdown("## 📜 Email Campaign History & Analytics")
st.caption("View and manage all previously sent email logs across campaigns.")

if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
    st.info("ℹ️ Abhi tak koi history record nahi bana hai. Pehle koi email campaign run karein.")
    st.stop()

try:
    # Read history CSV with error tolerance
    df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip", engine="python")
    df.columns = df.columns.str.strip()
    
    if df.empty:
        st.info("ℹ️ History file khali hai.")
        st.stop()

    # Dynamic Column Mapping for missing/different header names
    col_map = {}
    for col in df.columns:
        c_low = col.lower()
        if c_low in ["timestamp", "time", "date", "sent_at"]:
            col_map["Timestamp"] = col
        elif c_low in ["recipient", "email", "to_email", "to"]:
            col_map["Recipient"] = col
        elif c_low in ["status", "sent_status"]:
            col_map["Status"] = col
        elif c_low in ["subject", "mail_subject"]:
            col_map["Subject"] = col
        elif c_low in ["sender", "from_email", "from"]:
            col_map["Sender"] = col

    # --- 2. SUMMARY METRICS ---
    status_col = col_map.get("Status", "Status" if "Status" in df.columns else None)
    
    col1, col2, col3, col4 = st.columns(4)
    total_logs = len(df)
    
    col1.metric("Total Logs", total_logs)
    
    if status_col and status_col in df.columns:
        sent_count = df[df[status_col].astype(str).str.contains("Sent|Success|✅", case=False, na=False)].shape[0]
        failed_count = df[df[status_col].astype(str).str.contains("Failed|Error|❌", case=False, na=False)].shape[0]
        
        col2.metric("Sent ✅", sent_count)
        col3.metric("Failed ❌", failed_count)
        success_rate = round((sent_count / total_logs) * 100, 1) if total_logs > 0 else 0
        col4.metric("Success Rate", f"{success_rate}%")

    st.divider()

    # --- 3. FILTERS & SEARCH ---
    st.markdown("**🔍 Filter Logs**")
    f_col1, f_col2 = st.columns([2, 1])
    
    search_query = f_col1.text_input("Search by Email, Subject, or List Name:")
    
    status_filter = "All"
    if status_col and status_col in df.columns:
        unique_statuses = ["All"] + list(df[status_col].dropna().unique())
        status_filter = f_col2.selectbox("Filter Status:", unique_statuses)

    # Filter Application
    filtered_df = df.copy()
    
    if search_query:
        search_mask = filtered_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[search_mask]
        
    if status_filter != "All" and status_col:
        filtered_df = filtered_df[filtered_df[status_col] == status_filter]

    # --- 4. DISPLAY TABLE ---
    st.dataframe(filtered_df, use_container_width=True, height=450)

    # --- 5. ACTION BUTTONS ---
    st.divider()
    b_col1, b_col2 = st.columns([1, 1])
    
    b_col1.download_button(
        label="📥 Download Full History CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"email_history_export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True
    )
    
    if b_col2.button("🗑️ Clear All History", type="secondary", use_container_width=True):
        try:
            os.remove(HISTORY_FILE)
            st.success("✅ History records deleted successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Could not delete history file: {e}")

except Exception as e:
    st.error(f"❌ History File load karte waqt error aaya: {e}")

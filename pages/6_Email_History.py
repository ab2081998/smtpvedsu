from datetime import datetime, timedelta
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

HISTORY_FILE = os.path.abspath(os.path.join(parent_dir, "email_history.csv"))

try:
    import auth

    if hasattr(auth, "require_auth"):
        auth.require_auth()
    elif hasattr(auth, "check_auth"):
        auth.check_auth()
    else:
        if not st.session_state["authenticated"]:
            st.warning("🔒 Access Restricted! Please enter root password.")
            user_pass = st.text_input(
                "Please enter Password", type="password", key="hist_auth_pass_input"
            )
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
        user_pass = st.text_input(
            "Please enter Password", type="password", key="hist_auth_pass_input"
        )
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
st.markdown("## 📜 Email Campaign History (Last 48 Hours)")
st.caption(
    "Automatic retention: Records older than 48 hours are automatically purged."
)

if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
    st.info(
        "ℹ️ Abhi tak koi history record nahi bana hai. Pehle koi email campaign run karein."
    )
    st.stop()

try:
    df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip", engine="python")
    df.columns = df.columns.str.strip()

    if df.empty:
        st.info("ℹ️ History file khali hai.")
        st.stop()

    # --- 2. 48-HOUR AUTO CLEANUP LOGIC ---
    time_col = None
    for col in df.columns:
        if col.lower() in ["timestamp", "time", "date", "sent_at"]:
            time_col = col
            break

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        cutoff_time = datetime.now() - timedelta(hours=48)

        # Filter recent records
        filtered_df = df[df[time_col] >= cutoff_time].copy()

        # Update CSV file to delete >48hr data permanently
        if len(filtered_df) < len(df):
            filtered_df_to_save = filtered_df.copy()
            filtered_df_to_save[time_col] = filtered_df_to_save[
                time_col
            ].dt.strftime("%Y-%m-%d %H:%M:%S")
            filtered_df_to_save.to_csv(HISTORY_FILE, index=False, encoding="utf-8")

        df = filtered_df

    if df.empty:
        st.info("ℹ️ Pichle 48 ghante me koi campaign run nahi hui hai.")
        st.stop()

    # --- 3. METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    total_logs = len(df)
    col1.metric("Total Logs (48h)", total_logs)

    status_col = "Status" if "Status" in df.columns else None
    if status_col:
        sent_count = df[
            df[status_col]
            .astype(str)
            .str.contains("Sent|Success|✅", case=False, na=False)
        ].shape[0]
        failed_count = df[
            df[status_col]
            .astype(str)
            .str.contains("Failed|Error|❌", case=False, na=False)
        ].shape[0]

        col2.metric("Sent ✅", sent_count)
        col3.metric("Failed ❌", failed_count)
        success_rate = (
            round((sent_count / total_logs) * 100, 1) if total_logs > 0 else 0
        )
        col4.metric("Success Rate", f"{success_rate}%")

    st.divider()

    # --- 4. SEARCH & FILTER ---
    st.markdown("**🔍 Filter Logs**")
    f_col1, f_col2 = st.columns([2, 1])

    search_query = f_col1.text_input("Search by Email, Subject, or List Name:")

    status_filter = "All"
    if status_col:
        unique_statuses = ["All"] + list(df[status_col].dropna().unique())
        status_filter = f_col2.selectbox("Filter Status:", unique_statuses)

    display_df = df.copy()

    if search_query:
        search_mask = (
            display_df.astype(str)
            .apply(lambda row: row.str.contains(search_query, case=False, na=False))
            .any(axis=1)
        )
        display_df = display_df[search_mask]

    if status_filter != "All" and status_col:
        display_df = display_df[display_df[status_col] == status_filter]

    st.dataframe(display_df, use_container_width=True, height=450)

    # --- 5. ACTIONS ---
    st.divider()
    b_col1, b_col2 = st.columns([1, 1])

    b_col1.download_button(
        label="📥 Download History CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"email_history_48h_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True,
    )

    if b_col2.button(
        "🗑️ Clear History Manually", type="secondary", use_container_width=True
    ):
        try:
            os.remove(HISTORY_FILE)
            st.success("✅ History file deleted!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Could not delete file: {e}")

except Exception as e:
    st.error(f"❌ History load karne me error: {e}")

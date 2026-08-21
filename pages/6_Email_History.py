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

# Page 5 waali exact same file path
HISTORY_FILE = os.path.abspath(os.path.join(parent_dir, "email_history.csv"))

# Auth Check (Page 5 identical)
try:
    import auth

    if hasattr(auth, "require_auth"):
        auth.require_auth()
    elif hasattr(auth, "check_auth"):
        auth.check_auth()
    else:
        if not st.session_state["authenticated"]:
            st.warning("🔒 Access Restricted! Please enter password.")
            user_pass = st.text_input(
                "Please enter Password",
                type="password",
                key="hist_auth_pass_input",
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


# --- HELPER: 48 HOURS CLEANUP & SYNC ---
def load_and_clean_history():
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip", engine="python")
        if df.empty:
            return pd.DataFrame()

        # Clean column spaces
        df.columns = df.columns.str.strip()

        # Page 5 Column verification
        if "Timestamp" in df.columns:
            df["Parsed_Time"] = pd.to_datetime(df["Timestamp"], errors="coerce")

            # Remove unparseable bad date rows
            df = df.dropna(subset=["Parsed_Time"])

            # Calculate 48 hours cutoff
            cutoff_time = datetime.now() - timedelta(hours=48)

            # Filter data within last 48 hours
            recent_df = df[df["Parsed_Time"] >= cutoff_time].copy()

            # If old records were removed, rewrite the CSV
            if len(recent_df) < len(df):
                save_df = recent_df.drop(columns=["Parsed_Time"])
                save_df.to_csv(HISTORY_FILE, index=False, encoding="utf-8")

            recent_df = recent_df.drop(columns=["Parsed_Time"])
            return recent_df

        return df
    except Exception as e:
        st.error(f"⚠️ CSV Read Error: {e}")
        return pd.DataFrame()


# --- 1. MAIN UI ---
st.markdown("## 📜 Email Campaign History (Last 48 Hours)")
st.caption(
    "Page 5 se live linked history. 48 hours se purana data automatically delete ho jata hai."
)

df = load_and_clean_history()

if df.empty:
    st.info("ℹ️ Abhi tak koi 48 hours ke andar ka history record nahi hai.")
    st.stop()

# --- 2. SUMMARY METRICS ---
col1, col2, col3, col4 = st.columns(4)
total_logs = len(df)
col1.metric("Total Sent/Attempted", total_logs)

if "Status" in df.columns:
    sent_count = df[
        df["Status"].astype(str).str.contains("Sent|✅", case=False, na=False)
    ].shape[0]
    failed_count = df[
        df["Status"]
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

# --- 3. FILTER & SEARCH ---
st.markdown("**🔍 Search & Filter Logs**")
f_col1, f_col2 = st.columns([2, 1])

search_query = f_col1.text_input("Search (Recipient, Subject, List Name, etc.):")

status_filter = "All"
if "Status" in df.columns:
    unique_statuses = ["All"] + list(df["Status"].dropna().unique())
    status_filter = f_col2.selectbox("Filter by Status:", unique_statuses)

display_df = df.copy()

if search_query:
    search_mask = (
        display_df.astype(str)
        .apply(
            lambda row: row.str.contains(search_query, case=False, na=False)
        )
        .any(axis=1)
    )
    display_df = display_df[search_mask]

if status_filter != "All" and "Status" in display_df.columns:
    display_df = display_df[display_df["Status"] == status_filter]

# Display data table as it is from Page 5
st.dataframe(display_df, use_container_width=True, height=450)

# --- 4. EXPORT & ACTIONS ---
st.divider()
b_col1, b_col2 = st.columns([1, 1])

b_col1.download_button(
    label="📥 Download 48h History (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"email_history_48h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
    type="primary",
    use_container_width=True,
)

if b_col2.button(
    "🗑️ Clear All History Now", type="secondary", use_container_width=True
):
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.success("✅ History completely cleared!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error clearing file: {e}")from datetime import datetime, timedelta
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

# Page 5 waali exact same file path
HISTORY_FILE = os.path.abspath(os.path.join(parent_dir, "email_history.csv"))

# Auth Check (Page 5 identical)
try:
    import auth

    if hasattr(auth, "require_auth"):
        auth.require_auth()
    elif hasattr(auth, "check_auth"):
        auth.check_auth()
    else:
        if not st.session_state["authenticated"]:
            st.warning("🔒 Access Restricted! Please enter password.")
            user_pass = st.text_input(
                "Please enter Password",
                type="password",
                key="hist_auth_pass_input",
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


# --- HELPER: 48 HOURS CLEANUP & SYNC ---
def load_and_clean_history():
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        return pd.DataFrame()

    try:
        df = pd.read_csv(HISTORY_FILE, on_bad_lines="skip", engine="python")
        if df.empty:
            return pd.DataFrame()

        # Clean column spaces
        df.columns = df.columns.str.strip()

        # Page 5 Column verification
        if "Timestamp" in df.columns:
            df["Parsed_Time"] = pd.to_datetime(df["Timestamp"], errors="coerce")

            # Remove unparseable bad date rows
            df = df.dropna(subset=["Parsed_Time"])

            # Calculate 48 hours cutoff
            cutoff_time = datetime.now() - timedelta(hours=48)

            # Filter data within last 48 hours
            recent_df = df[df["Parsed_Time"] >= cutoff_time].copy()

            # If old records were removed, rewrite the CSV
            if len(recent_df) < len(df):
                save_df = recent_df.drop(columns=["Parsed_Time"])
                save_df.to_csv(HISTORY_FILE, index=False, encoding="utf-8")

            recent_df = recent_df.drop(columns=["Parsed_Time"])
            return recent_df

        return df
    except Exception as e:
        st.error(f"⚠️ CSV Read Error: {e}")
        return pd.DataFrame()


# --- 1. MAIN UI ---
st.markdown("## 📜 Email Campaign History (Last 48 Hours)")
st.caption(
    "Page 5 se live linked history. 48 hours se purana data automatically delete ho jata hai."
)

df = load_and_clean_history()

if df.empty:
    st.info("ℹ️ Abhi tak koi 48 hours ke andar ka history record nahi hai.")
    st.stop()

# --- 2. SUMMARY METRICS ---
col1, col2, col3, col4 = st.columns(4)
total_logs = len(df)
col1.metric("Total Sent/Attempted", total_logs)

if "Status" in df.columns:
    sent_count = df[
        df["Status"].astype(str).str.contains("Sent|✅", case=False, na=False)
    ].shape[0]
    failed_count = df[
        df["Status"]
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

# --- 3. FILTER & SEARCH ---
st.markdown("**🔍 Search & Filter Logs**")
f_col1, f_col2 = st.columns([2, 1])

search_query = f_col1.text_input("Search (Recipient, Subject, List Name, etc.):")

status_filter = "All"
if "Status" in df.columns:
    unique_statuses = ["All"] + list(df["Status"].dropna().unique())
    status_filter = f_col2.selectbox("Filter by Status:", unique_statuses)

display_df = df.copy()

if search_query:
    search_mask = (
        display_df.astype(str)
        .apply(
            lambda row: row.str.contains(search_query, case=False, na=False)
        )
        .any(axis=1)
    )
    display_df = display_df[search_mask]

if status_filter != "All" and "Status" in display_df.columns:
    display_df = display_df[display_df["Status"] == status_filter]

# Display data table as it is from Page 5
st.dataframe(display_df, use_container_width=True, height=450)

# --- 4. EXPORT & ACTIONS ---
st.divider()
b_col1, b_col2 = st.columns([1, 1])

b_col1.download_button(
    label="📥 Download 48h History (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"email_history_48h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
    type="primary",
    use_container_width=True,
)

if b_col2.button(
    "🗑️ Clear All History Now", type="secondary", use_container_width=True
):
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        st.success("✅ History completely cleared!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error clearing file: {e}")

from datetime import datetime
import os
import sys
import pandas as pd
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Email Logs & History Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- 0. AUTHENTICATION & SESSION CHECK ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

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

# --- SIDEBAR LOGOUT ---
with st.sidebar:
    st.divider()
    if st.button("🚪 Logout App"):
        st.session_state["authenticated"] = False
        st.success("👋 Logged out!")
        st.rerun()

# --- MAIN DASHBOARD ---
st.title("📊 Email Logs & History Dashboard")
st.caption("View, search, filter, and export all email sending logs.")

HISTORY_FILE = "email_history.csv"

# --- SAFE CSV LOADING LOGIC ---
df = pd.DataFrame()

if os.path.exists(HISTORY_FILE):
    try:
        # Bad lines skip setting added to handle extra comma tokenizing errors
        df = pd.read_csv(
            HISTORY_FILE,
            on_bad_lines="skip",
            engine="python",
        )
        df.columns = df.columns.str.strip()
    except Exception as e:
        st.error(f"❌ Error loading history file: {e}")
        df = pd.DataFrame()

if df.empty:
    st.info("ℹ️ Koi history records nahi mile ya file empty hai.")
else:
    if "Status" not in df.columns:
        df["Status"] = "Unknown"
    
    # 1. OVERALL METRICS CARDS
    total_logs = len(df)
    sent_count = len(df[df["Status"].str.contains("Sent", case=False, na=False)])
    failed_count = len(df[df["Status"].str.contains("Failed", case=False, na=False)])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Processed", total_logs)
    col2.metric("Successfully Sent ✅", sent_count)
    col3.metric("Failed ❌", failed_count)

    st.divider()

    # 2. LIST NAME / CAMPAIGN CARDS (GROUP BY)
    list_col = None
    for possible_col in ["List Name", "Campaign", "Subject", "Sender"]:
        if possible_col in df.columns:
            list_col = possible_col
            break

    if list_col:
        st.markdown(f"**📁 Campaign / List-wise Summary (`{list_col}`)**")
        
        # Group data by List/Campaign/Subject
        grouped = df.groupby(list_col)
        
        # Grid Display for Cards
        cards_per_row = 3
        groups = list(grouped)
        
        for i in range(0, len(groups), cards_per_row):
            cols = st.columns(cards_per_row)
            for j, (group_name, group_df) in enumerate(groups[i : i + cards_per_row]):
                g_total = len(group_df)
                g_sent = len(group_df[group_df["Status"].str.contains("Sent", case=False, na=False)])
                g_failed = len(group_df[group_df["Status"].str.contains("Failed", case=False, na=False)])
                
                with cols[j]:
                    with st.container(border=True):
                        st.subheader(f"📌 {group_name}")
                        st.caption(f"Total Records: **{g_total}**")
                        st.write(f"✅ **Sent:** {g_sent} | ❌ **Failed:** {g_failed}")

        st.divider()

    # 3. FILTERS & SEARCH LOGS
    st.markdown("**🔎 Filter & Search Detailed Logs**")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        search_query = st.text_input("Search (Recipient / Name / Subject):", "")

    with f_col2:
        status_filter = st.selectbox(
            "Filter by Status:",
            ["All"] + list(df["Status"].unique())
        )

    with f_col3:
        sender_options = ["All"] + list(df["Sender"].unique()) if "Sender" in df.columns else ["All"]
        sender_filter = st.selectbox("Filter by Sender:", sender_options)

    # Apply Filters
    filtered_df = df.copy()

    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]

    if sender_filter != "All" and "Sender" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Sender"] == sender_filter]

    if search_query:
        search_pattern = search_query.lower()
        mask = filtered_df.astype(str).apply(
            lambda row: row.str.lower().str.contains(search_pattern).any(),
            axis=1
        )
        filtered_df = filtered_df[mask]

    st.dataframe(filtered_df, use_container_width=True)

    # 4. EXPORT & CLEAR HISTORY
    c_exp, c_clr = st.columns([2, 1])

    with c_exp:
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Current View (CSV)",
            data=csv_bytes,
            file_name=f"email_history_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary"
        )

    with c_clr:
        if st.button("🗑️ Clear History Logs", type="secondary"):
            try:
                os.remove(HISTORY_FILE)
                st.success("✅ History cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete history file: {e}")

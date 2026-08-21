from datetime import datetime
import os
import sys
import pandas as pd
import streamlit as st
from supabase import create_client, Client

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
except ImportError:
    pass

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

# --- 1. SUPABASE CLIENT INIT ---
@st.cache_resource
def get_supabase_client():
    if "supabase" in st.secrets:
        try:
            return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        except Exception as e:
            st.error(f"Supabase Connection Error: {e}")
            return None
    return None

supabase_client = get_supabase_client()

st.title("📊 Email History & Logs")

# --- 2. SYNC CSV DATA TO SUPABASE ---
if os.path.exists(HISTORY_FILE) and supabase_client:
    with st.expander("☁️ Sync / Push Local CSV Data to Supabase"):
        st.write("Local `email_history.csv` file se records Supabase database me sync karein:")
        if st.button("📤 Push CSV Data to Supabase Now"):
            try:
                csv_df = pd.read_csv(HISTORY_FILE)
                if not csv_df.empty:
                    records = []
                    for _, row in csv_df.iterrows():
                        record = {}
                        if "List Name" in row: record["list_name"] = str(row["List Name"])
                        if "Recipient" in row: record["recipient"] = str(row["Recipient"])
                        if "Reason" in row: record["reason"] = str(row["Reason"])
                        if "Subject" in row and pd.notna(row["Subject"]): record["subject"] = str(row["Subject"])
                        
                        records.append(record)

                    if records:
                        supabase_client.table("email_history").insert(records).execute()
                        st.success(f"✅ Successful! {len(records)} records Supabase par sync ho gaye.")
                        st.rerun()
                else:
                    st.warning("⚠️ CSV file khali hai!")
            except Exception as e:
                st.error(f"❌ Sync Error: {e}")

# --- 3. FETCH DATA FROM SUPABASE / LOCAL CSV ---
def load_history_data():
    # Primary: Try Supabase
    if supabase_client:
        try:
            res = supabase_client.table("email_history").select("*").order("id", desc=True).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                cols_rename = {
                    "list_name": "List Name",
                    "recipient": "Recipient",
                    "subject": "Subject",
                    "reason": "Reason",
                    "created_at": "Created At"
                }
                return df.rename(columns=cols_rename), "Supabase Cloud Database"
        except Exception as e:
            st.warning(f"Supabase fetch warning: {e}")

    # Fallback: Try Local CSV
    if os.path.exists(HISTORY_FILE):
        try:
            csv_data = pd.read_csv(HISTORY_FILE)
            if not csv_data.empty:
                return csv_data, "Local CSV File"
        except Exception as e:
            st.error(f"CSV read error: {e}")

    return pd.DataFrame(), "None"

df, data_source = load_history_data()

st.caption(f"📌 **Active Data Source:** `{data_source}`")

if df.empty:
    st.info("ℹ️ Koi history record nahi mila.")
else:
    # Filter Controls
    list_col = "List Name" if "List Name" in df.columns else ("list_name" if "list_name" in df.columns else None)
    
    if list_col:
        list_options = df[list_col].dropna().unique().tolist()
        list_filter = st.multiselect("Filter by List Name:", options=list_options, default=list_options)
        filtered_df = df[df[list_col].isin(list_filter)]
    else:
        filtered_df = df.copy()

    # Metrics
    m1, m2 = st.columns(2)
    m1.metric("Total Logs", len(df))
    m2.metric("Filtered Records", len(filtered_df))

    st.divider()

    # Display clean table
    ignore_cols = ["id"]
    display_df = filtered_df.drop(columns=[c for c in ignore_cols if c in filtered_df.columns])
    st.dataframe(display_df, use_container_width=True)

    # Danger Zone
    st.divider()
    with st.expander("⚠️ Danger Zone (Clear History)"):
        if st.button("🗑️ Clear History Data", type="primary"):
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            if supabase_client:
                try:
                    supabase_client.table("email_history").delete().gt("id", 0).execute()
                except Exception:
                    pass
            st.success("✅ History Database & CSV clear ho gaya!")
            st.rerun()

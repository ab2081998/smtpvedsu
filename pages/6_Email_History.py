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

# --- 2. SYNC CSV DATA TO SUPABASE (WITH DEDUPLICATION) ---
if os.path.exists(HISTORY_FILE) and supabase_client:
    with st.expander("☁️ Sync / Push Local CSV Data to Supabase"):
        st.write("Local `email_history.csv` file se naye records Supabase database me sync karein:")
        if st.button("📤 Push CSV Data to Supabase Now"):
            try:
                csv_df = pd.read_csv(HISTORY_FILE)
                if not csv_df.empty:
                    # 1. Fetch existing timestamps & recipients from Supabase to prevent duplicates
                    existing_data = supabase_client.table("email_history").select("timestamp, recipient").execute()
                    existing_keys = set()
                    if existing_data.data:
                        for item in existing_data.data:
                            existing_keys.add(f"{item.get('timestamp')}_{item.get('recipient')}")

                    records = []
                    skipped_count = 0

                    for _, row in csv_df.iterrows():
                        ts = str(row.get("Timestamp", "")).strip()
                        rec = str(row.get("Recipient", "")).strip()
                        key = f"{ts}_{rec}"

                        # Skip if record already exists in Supabase
                        if key in existing_keys:
                            skipped_count += 1
                            continue

                        records.append({
                            "timestamp": ts,
                            "list_name": str(row.get("List Name", "")),
                            "sender": str(row.get("Sender", "")),
                            "recipient": rec,
                            "subject": str(row.get("Subject", "")),
                            "status": str(row.get("Status", "")),
                            "reason": str(row.get("Reason", ""))
                        })

                    if records:
                        supabase_client.table("email_history").insert(records).execute()
                        st.success(f"✅ Successful! {len(records)} naye records upload hue. ({skipped_count} duplicate records skip hue)")
                        st.rerun()
                    else:
                        st.info(f"ℹ️ Saare records pehle se Supabase me maujood hain. ({skipped_count} records skipped)")
                else:
                    st.warning("⚠️ CSV file khali hai!")
            except Exception as e:
                st.error(f"❌ Upload Error: {e}")

# --- 3. FETCH DATA FROM SUPABASE / CSV ---
def load_history_data():
    if supabase_client:
        try:
            res = supabase_client.table("email_history").select("*").order("id", desc=True).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                cols_rename = {
                    "timestamp": "Timestamp",
                    "list_name": "List Name",
                    "sender": "Sender",
                    "recipient": "Recipient",
                    "subject": "Subject",
                    "status": "Status",
                    "reason": "Reason"
                }
                return df.rename(columns=cols_rename), "Supabase Cloud Database"
        except Exception as e:
            st.warning(f"Supabase connection warning: {e}")

    # Fallback to local CSV
    if os.path.exists(HISTORY_FILE):
        try:
            return pd.read_csv(HISTORY_FILE), "Local CSV File"
        except Exception as e:
            st.error(f"CSV read error: {e}")

    return pd.DataFrame(), "None"

df, data_source = load_history_data()

st.caption(f"📌 **Active Data Source:** `{data_source}`")

if df.empty:
    st.info("ℹ️ Koi history record nahi mila.")
else:
    # Filter Controls
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.multiselect(
            "Filter by Status:",
            options=df["Status"].unique().tolist() if "Status" in df.columns else [],
            default=df["Status"].unique().tolist() if "Status" in df.columns else []
        )
    with col_f2:
        list_filter = st.multiselect(
            "Filter by List Name:",
            options=df["List Name"].unique().tolist() if "List Name" in df.columns else [],
            default=df["List Name"].unique().tolist() if "List Name" in df.columns else []
        )

    filtered_df = df.copy()
    if status_filter and "Status" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]
    if list_filter and "List Name" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["List Name"].isin(list_filter)]

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Logs", len(df))
    m2.metric("Filtered Records", len(filtered_df))
    sent_count = len(df[df["Status"].str.contains("Sent|✅", na=False, case=False)]) if "Status" in df.columns else 0
    m3.metric("Successful Mails", sent_count)

    st.divider()

    # Hide internal database columns like id/created_at if present
    display_cols = [col for col in ["Timestamp", "List Name", "Sender", "Recipient", "Subject", "Status", "Reason"] if col in filtered_df.columns]
    st.dataframe(filtered_df[display_cols], use_container_width=True)

    # Danger Zone
    st.divider()
    with st.expander("⚠️ Danger Zone (Clear History)"):
        if st.button("🗑️ Clear History Data", type="primary"):
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
            if supabase_client:
                try:
                    supabase_client.table("email_history").delete().gt("id", 0).execute()
                except Exception as e:
                    pass
            st.success("✅ History Database & CSV clear ho gaya!")
            st.rerun()

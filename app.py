import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- 1. CONFIG & DATE ---
today = datetime.now().date()
today_str = str(today)
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION (Fixed Syntax & PEM Error) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    try:
        # Streamlit Secrets theke data neya
        creds_info = st.secrets["gcp_service_account"]
        
        # AttrDict ke normal dict e convert kora
        info = dict(creds_info)
        
        # Private key formatting fix (InvalidPadding/PEM error dur korar jonno)
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Configuration Error: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_worksheet(name):
    if client is None:
        return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except Exception as e:
        st.error(f"Sheet Tab Error: '{name}' tab ti khuje pawa jachche na.")
        return None

# --- 3. LOGIN LOGIC ---
USER_CREDENTIALS = {"azman@pathao.com": "pathao123", "asikul.islam@pathao.com": "pathao456"}
if 'logged_in' not in st.session_state: 
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access Control")
    with st.form("login"):
        u_email = st.text_input("Email").lower().strip()
        u_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u_email in USER_CREDENTIALS and USER_CREDENTIALS[u_email] == u_pass:
                st.session_state['logged_in'] = True
                st.rerun()
            else: 
                st.error("Wrong Email/Password")
    st.stop()

# --- 4. NAVIGATION ---
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])

# --- 5. DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    ws = get_worksheet("tasks")
    if ws:
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            p_h = pd.to_numeric(df['Planned Hours'], errors='coerce').sum()
            a_h = pd.to_numeric(df['Actual Hours'], errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Planned", f"{p_h}h")
            c2.metric("Actual", f"{a_h}h")
            c3.metric("Efficiency", f"{(a_h/p_h*100):.1f}%" if p_h > 0 else "0%")
            st.table(df.groupby('Task Name')[['Planned Hours', 'Actual Hours']].sum())
        else: 
            st.info("No data yet.")

# --- 6. PLAN TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    with st.form("p_f", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver", "Training", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Save"):
            ws = get_worksheet("tasks")
            if ws:
                ws.append_row([today_str, cat, name, ph, 0, "Planned", ""])
                st.success("Saved to Google Sheet!")

# --- 7. UPDATE STATUS ---
elif page == "Update Status (EOD)":
    st.header("✅ End of Day Update")
    ws = get_worksheet("tasks")
    if ws:
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            pending = df[(df['Date'] == today_str) & (df['Status'] == "Planned")]
            if not pending.empty:
                for idx, row in pending.iterrows():
                    with st.expander(f"Task: {row['Task Name']}"):
                        ah = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"h{idx}")
                        stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                        if st.button("Update", key=f"b{idx}"):
                            ws.update_cell(idx + 2, 5, ah)
                            ws.update_cell(idx + 2, 6, stat)
                            st.success("Updated!"); st.rerun()
            else: 
                st.info("Nothing to update for today.")

# --- 8. QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_f", clear_on_submit=True):
        ch = st.selectbox("Channel", ["Email", "Chat", "Call"])
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log QA"):
            ws = get_worksheet("qa")
            if ws:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                hrs = (cnt*15)/60
                ws.append_row([today_str, ch, cnt, err, acc, hrs])
                st.success("QA Data Logged!")

# --- 9. DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding")
    with st.form("dr_f", clear_on_submit=True):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        stat = st.selectbox("Status", ["pending", "active"])
        if st.form_submit_button("Save Driver"):
            ws = get_worksheet("drivers")
            if ws:
                ws.append_row([today_str, name, phone, "Dhaka", "Yes", "submitted", stat, "Call received", "No"])
                st.success("Driver Data Saved!")

# --- 10. SUSPENSION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Bulk Re-Validation")
    up = st.file_uploader("Upload File", type=["xlsx", "csv"])
    if up:
        df_up = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        if st.button("Push to Sheet"):
            ws = get_worksheet("revalidation")
            if ws:
                # Insert Date as first column
                data_to_save = df_up.values.tolist()
                for row in data_to_save:
                    row.insert(0, today_str)
                ws.append_rows(data_to_save)
                st.success("Bulk Data Pushed Successfully!")

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- 1. CONFIG & DATE ---
today = datetime.now().date()
today_str = str(today)
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Global client initialize kora jate NameError na hoy
client = None 

try:
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        # PEM format fix
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
    else:
        st.error("Secrets not found! Please add 'gcp_service_account' in Streamlit Cloud.")
except Exception as e:
    st.error(f"Authentication Error: {e}")

SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_worksheet(name):
    if client is None:
        st.error("Google Sheets client is not initialized.")
        return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except Exception as e:
        st.error(f"Worksheet '{name}' error: {e}")
        return None

# --- 3. LOGIN LOGIC ---
USER_CREDENTIALS = {"asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}
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
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            # Simple Summary Metrics
            p_h = pd.to_numeric(df['Planned Hours'], errors='coerce').sum()
            a_h = pd.to_numeric(df['Actual Hours'], errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Planned Total", f"{p_h}h")
            c2.metric("Actual Total", f"{a_h}h")
            c3.metric("Efficiency", f"{(a_h/p_h*100):.1f}%" if p_h > 0 else "0%")
            
            st.subheader("Task Details")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No data found in 'tasks' sheet.")

# --- 6. PLAN DAILY TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    with st.form("p_f", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver", "Training", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Save Plan"):
            ws = get_worksheet("tasks")
            if ws:
                ws.append_row([today_str, cat, name, ph, 0, "Planned", ""])
                st.success("Plan saved to Google Sheet!")

# --- 7. UPDATE STATUS (EOD) ---
elif page == "Update Status (EOD)":
    st.header("✅ End of Day Update")
    ws = get_worksheet("tasks")
    if ws:
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            # Today's planned tasks
            pending = df[(df['Date'].astype(str) == today_str) & (df['Status'] == "Planned")]
            
            if not pending.empty:
                for idx, row in pending.iterrows():
                    with st.expander(f"Task: {row['Task Name']}"):
                        actual = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"up_{idx}")
                        status = st.selectbox("Status", ["Completed", "Incompleted"], key=f"st_{idx}")
                        if st.button("Submit Update", key=f"btn_{idx}"):
                            # Update Google Sheet (Row index is idx + 2 because of header)
                            ws.update_cell(idx + 2, 5, actual) # Col E
                            ws.update_cell(idx + 2, 6, status) # Col F
                            st.success("Updated successfully!")
                            st.rerun()
            else:
                st.info("No pending tasks to update for today.")

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
                ws.append_row([today_str, ch, cnt, err, f"{((cnt-err)/cnt)*100:.1f}%", (cnt*15)/60])
                st.success("QA Logged!")

# --- 9. DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding")
    with st.form("dr_f", clear_on_submit=True):
        name = st.text_input("Driver Name")
        phone = st.text_input("Phone")
        if st.form_submit_button("Save"):
            ws = get_worksheet("drivers")
            if ws:
                ws.append_row([today_str, name, phone, "Dhaka", "Active"])
                st.success("Driver saved!")

# --- 10. SUSPENSION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Bulk Re-Validation")
    up = st.file_uploader("Upload File", type=["xlsx", "csv"])
    if up:
        df_up = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        if st.button("Push to Sheet"):
            ws = get_worksheet("revalidation")
            if ws:
                data = df_up.values.tolist()
                ws.append_rows(data)
                st.success("Bulk data pushed!")

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- 1. CONFIG & DATE ---
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")
today = datetime.now().date()
today_str = str(today)

# --- 2. GOOGLE SHEETS CONNECTION (Enhanced for PEM Error Fix) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            # Secrets theke data neya
            info = dict(st.secrets["gcp_service_account"])
            # CRITICAL: Fix for "Unable to load PEM file" / InvalidPadding
            # Eiti multiline key-r literal \n ke real newline e convert kore
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            
            creds = Credentials.from_service_account_info(info, scopes=scope)
            return gspread.authorize(creds)
        else:
            st.error("Secrets not found! Please check Streamlit Cloud Settings.")
            return None
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_ws(name):
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except:
        st.error(f"Tab '{name}' not found in Google Sheet!")
        return None

# --- 3. LOGIN LOGIC ---
USER_CREDENTIALS = {"asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access Control")
    with st.form("login_form"):
        u_email = st.text_input("Email").lower().strip()
        u_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u_email in USER_CREDENTIALS and USER_CREDENTIALS[u_email] == u_pass:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u_email
                st.rerun()
            else: st.error("Wrong Email or Password!")
    st.stop()

# --- 4. SIDEBAR NAVIGATION ---
page = st.sidebar.selectbox("Navigation", [
    "📊 Dashboard", 
    "📝 Plan Daily Tasks", 
    "✅ Update Status (EOD)", 
    "🔍 QA Details", 
    "🚗 Driver Onboarding", 
    "⚠️ Suspension Re-Validation"
])

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 5. DASHBOARD ---
if page == "📊 Dashboard":
    st.header("Performance Overview")
    ws = get_ws("tasks")
    if ws:
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            # Metrics calculation
            p_h = pd.to_numeric(df['Planned Hours'], errors='coerce').sum()
            a_h = pd.to_numeric(df['Actual Hours'], errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Planned", f"{p_h}h")
            c2.metric("Total Actual", f"{a_h}h")
            c3.metric("Efficiency", f"{(a_h/p_h*100 if p_h > 0 else 0):.1f}%")
            st.divider()
            st.subheader("Task Log")
            st.dataframe(df, use_container_width=True)
        else: st.info("No data available.")

# --- 6. PLAN DAILY TASKS ---
elif page == "📝 Plan Daily Tasks":
    st.header("Morning Planning")
    with st.form("plan_f", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver", "Training", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Save Plan"):
            ws = get_ws("tasks")
            if ws:
                ws.append_row([today_str, cat, name, ph, 0, "Planned", ""])
                st.success("Task Planned Successfully!")

# --- 7. UPDATE STATUS (EOD) ---
elif page == "✅ Update Status (EOD)":
    st.header("End of Day Update")
    ws = get_ws("tasks")
    if ws:
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            pending = df[(df['Date'].astype(str) == today_str) & (df['Status'] == "Planned")]
            if not pending.empty:
                for idx, row in pending.iterrows():
                    with st.expander(f"Task: {row['Task Name']}"):
                        act = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"a_{idx}")
                        stt = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s_{idx}")
                        if st.button("Update", key=f"b_{idx}"):
                            ws.update_cell(idx + 2, 5, act) # Col E
                            ws.update_cell(idx + 2, 6, stt) # Col F
                            st.success("Updated!"); st.rerun()
            else: st.info("No pending tasks for today.")

# --- 8. QA DETAILS ---
elif page == "🔍 QA Details":
    st.header("Audit Tracking")
    with st.form("qa_f", clear_on_submit=True):
        ch = st.selectbox("Channel", ["Email", "Chat", "Call"])
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Critical Errors", 0)
        if st.form_submit_button("Log QA"):
            ws = get_ws("qa")
            if ws:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                hrs = (cnt * 15) / 60 # Assuming 15 mins per audit
                ws.append_row([today_str, ch, cnt, err, acc, hrs])
                st.success("QA Recorded!")

# --- 9. DRIVER ONBOARDING ---
elif page == "🚗 Driver Onboarding":
    st.header("Rental Driver Tracker")
    with st.form("dr_f", clear_on_submit=True):
        d_name = st.text_input("Driver Name")
        d_phone = st.text_input("Phone Number")
        d_stat = st.selectbox("Account Status", ["pending", "active"])
        if st.form_submit_button("Submit"):
            ws = get_ws("drivers")
            if ws:
                ws.append_row([today_str, d_name, d_phone, "Dhaka", "Yes", "submitted", d_stat])
                st.success("Driver Onboarding Logged!")

# --- 10. SUSPENSION RE-VALIDATION ---
elif page == "⚠️ Suspension Re-Validation":
    st.header("Bulk Re-Validation Upload")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up:
        df_up = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        st.write("Preview:", df_up.head())
        if st.button("Push to Google Sheet"):
            ws = get_ws("revalidation")
            if ws:
                data = df_up.values.tolist()
                # Adding today's date to each row
                for r in data: r.insert(0, today_str)
                ws.append_rows(data)
                st.success(f"Successfully pushed {len(data)} rows!")

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json

# --- 1. CONFIG ---
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")
today = datetime.now().date()
today_str = str(today)

# --- 2. GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gspread_client():
    try:
        json_creds_str = st.secrets["gcp_service_account"]["json_creds"]
        creds_dict = json.loads(json_creds_str)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_ws(name):
    if not client: return None
    try:
        return client.open_by_key(SHEET_ID).worksheet(name)
    except Exception as e:
        st.error(f"Sheet '{name}' Error: {e}")
        return None

# --- 3. LOGIN & NAVIGATION ---
USER_CREDENTIALS = {"asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access")
    with st.form("login"):
        u = st.text_input("Email").lower().strip()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u in USER_CREDENTIALS and USER_CREDENTIALS[u] == p:
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("Wrong info!")
    st.stop()

# --- 4. NAVIGATION ---
page = st.sidebar.selectbox("Navigation", 
    ["Dashboard", "Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 5. PAGE: DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    
    ws_tasks = get_ws("tasks")
    ws_qa = get_ws("qa")
    ws_drivers = get_ws("drivers")

    # Load Data
    t_df = pd.DataFrame(ws_tasks.get_all_records()) if ws_tasks else pd.DataFrame()
    q_df = pd.DataFrame(ws_qa.get_all_records()) if ws_qa else pd.DataFrame()
    d_df = pd.DataFrame(ws_drivers.get_all_records()) if ws_drivers else pd.DataFrame()

    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    # Filter Logic
    for df in [t_df, q_df, d_df]:
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date

    if view == "Daily":
        t_f = t_df[t_df['Date'] == today]
        q_f = q_df[q_df['Date'] == today]
        d_f = d_df[d_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_f, q_f, d_f = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw], d_df[d_df['Date'] >= sw]
    else:
        t_f, q_f, d_f = t_df, q_df, d_df

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    audits = q_f['Audit Count'].sum() if not q_f.empty else 0
    drivers = len(d_f[d_f['Acc Status'] == 'active']) if not d_f.empty else 0
    plan_h = t_f['Planned Hours'].sum() if not t_f.empty else 0
    act_h = t_f['Actual Hours'].sum() if not t_f.empty else 0
    
    m1.metric("Audits Done", int(audits))
    m2.metric("Drivers Active", int(drivers))
    m3.metric("Actual Hours", f"{act_h:.1f}h")
    m4.metric("Efficiency %", f"{(act_h/plan_h*100):.1f}%" if plan_h > 0 else "0%")

    st.subheader("📋 Task Breakdown")
    st.dataframe(t_f, use_container_width=True)

# --- 6. PAGE: PLAN DAILY TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    with st.form("plan", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "Suspension", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add to Plan"):
            ws = get_ws("tasks")
            if ws:
                ws.append_row([today_str, cat, name, ph, 0.0, "Planned", ""])
                st.success("Task added to Google Sheet!")

# --- 7. PAGE: UPDATE STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Update")
    ws = get_ws("tasks")
    if ws:
        df = pd.DataFrame(ws.get_all_records())
        # Filter for today's planned tasks
        mask = (df['Date'] == today_str) & (df['Status'] == "Planned")
        pending = df[mask]
        
        if not pending.empty:
            for idx, row in pending.iterrows():
                with st.expander(f"Update: {row['Task Name']}"):
                    # Google Sheet is 1-indexed, and header is row 1, so row idx is idx+2
                    row_num = idx + 2 
                    ah = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"h{idx}")
                    stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                    if st.button("Confirm Update", key=f"b{idx}"):
                        ws.update_cell(row_num, 5, ah) # Col 5 is Actual Hours
                        ws.update_cell(row_num, 6, stat) # Col 6 is Status
                        st.success("Updated!")
                        st.rerun()
        else:
            st.info("No pending tasks for today.")

# --- 8. PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_log", clear_on_submit=True):
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log QA"):
            ws = get_ws("qa")
            if ws and cnt > 0:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                hrs = (cnt * 15) / 60 # Assume 15 min per audit
                ws.append_row([today_str, "General", cnt, err, acc, hrs])
                st.success("QA Saved!")

# --- 9. PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Management")
    with st.form("dr", clear_on_submit=True):
        n = st.text_input("Driver Name")
        p = st.text_input("Phone")
        city = st.selectbox("City", ["Dhaka", "Chittagong", "Sylhet"])
        as_stat = st.selectbox("Account Status", ["pending", "active"])
        if st.form_submit_button("Save Driver"):
            ws = get_ws("drivers")
            if ws:
                ws.append_row([today_str, n, p, city, "Yes", "submitted", as_stat, "Call done", "No"])
                st.success("Driver Logged!")

# --- 10. PAGE: SUSPENSION ---
elif page == "Suspension Re-Validation":
    st.header("⚠️ Suspension Re-Validation")
    up = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    if up:
        raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        st.write("Preview:", raw.head(3))
        if st.button("Push All to Google Sheet"):
            ws = get_ws("revalidation")
            if ws:
                # Convert dataframe to list of lists for gspread
                data_to_push = raw.values.tolist()
                ws.append_rows(data_to_push)
                st.success(f"Successfully pushed {len(data_to_push)} rows!")

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

# --- 2. HELPER FUNCTIONS ---
def get_working_days(start_date, end_date):
    """শুক্রবার, শনিবার এবং সরকারি ছুটি বাদ দিয়ে কার্যদিবস গণনা করে"""
    govt_holidays = [
        datetime(2026, 2, 21).date(), # শহীদ দিবস
        datetime(2026, 3, 26).date(), # স্বাধীনতা দিবস
        datetime(2026, 4, 14).date(), # পহেলা বৈশাখ
    ]
    all_days = pd.date_range(start=start_date, end=end_date)
    working_days = [d for d in all_days if d.weekday() not in [4, 5] and d.date() not in govt_holidays]
    return len(working_days)

# --- 3. GOOGLE SHEETS CONNECTION ---
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

# --- 4. LOGIN & NAVIGATION ---
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

page = st.sidebar.selectbox("Navigation", 
    ["Dashboard", "Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 5. PAGE: DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard & Targets")
    
    start_of_week = today - timedelta(days=(today.weekday() + 2) % 7) 
    start_of_month = today.replace(day=1)
    
    # লোড ডাটা
    ws_tasks = get_ws("tasks")
    ws_drivers = get_ws("drivers")
    ws_qa = get_ws("qa")
    
    t_df = pd.DataFrame(ws_tasks.get_all_records()) if ws_tasks else pd.DataFrame()
    d_df = pd.DataFrame(ws_drivers.get_all_records()) if ws_drivers else pd.DataFrame()
    q_df = pd.DataFrame(ws_qa.get_all_records()) if ws_qa else pd.DataFrame()

    # ডাটা প্রেপারেশন (স্পেস ক্লিন করা ও ডেট ফরম্যাট)
    for df in [t_df, d_df, q_df]:
        if not df.empty:
            df.columns = df.columns.str.strip()
            df['Date'] = pd.to_datetime(df['Date']).dt.date

    # --- মেট্রিক্স ক্যালকুলেশন ---
    st.subheader("🎯 Progress vs Targets")
    m1, m2, m3, m4 = st.columns(4)

    # ১. QA Audit (Daily Target: 12) - qa শিট থেকে Audit Count এর যোগফল
    today_audits = q_df[q_df['Date'] == today]['Audit Count'].sum() if not q_df.empty else 0
    m1.metric("Today's QA Audits", f"{int(today_audits)}/12", delta=int(today_audits) - 12)

    # ২. Weekly Driver Onboarding (Target: 10/week) - drivers শিট থেকে Acc Status 'Active'
    week_drivers = len(d_df[(d_df['Date'] >= start_of_week) & (d_df['Acc Status'] == 'Active')]) if not d_df.empty else 0
    m2.metric("Weekly Onboarding", f"{week_drivers}/10", delta=week_drivers - 10)

    # ৩. Weekly Training (Target: 5/week) - tasks শিট থেকে Category 'Agent Training'
    week_trainings = len(t_df[(t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Agent Training')]) if not t_df.empty else 0
    m3.metric("Weekly Training", f"{week_trainings}/5", delta=week_trainings - 5)

    # ৪. কাজের দিন (মাসিক)
    monthly_working_days = get_working_days(start_of_month, today)
    m4.metric("Working Days (Month)", f"{monthly_working_days} Days")

    st.divider()

    # --- সাপ্তাহিক চেকলিস্ট ---
    st.subheader("🗓️ Weekly Deliverables Checklist")
    c1, c2 = st.columns(2)
    with c1:
        susp_status = any((t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Suspension') & (t_df['Status'] == 'Completed')) if not t_df.empty else False
        st.checkbox("Suspension Re-validation Report Sharing", value=susp_status, disabled=True)
        
        init_status = any((t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Initiatives') & (t_df['Status'] == 'Completed')) if not t_df.empty else False
        st.checkbox("Weekly Performance Initiative", value=init_status, disabled=True)
    with c2:
        st.info("**QA Insight:** Identify & report top recurring issues based on weekly audits.")
        if not q_df.empty:
            st.write(f"Audits logged this week: {int(q_df[q_df['Date'] >= start_of_week]['Audit Count'].sum())}")

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
                st.success("Task added!")
                st.rerun()

# --- 7. PAGE: UPDATE TASK STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Update")
    ws = get_ws("tasks")
    if ws:
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip()
            mask = (df['Date'].astype(str) == today_str) & (df['Status'] == "Planned")
            pending = df[mask]
            if not pending.empty:
                for idx, row in pending.iterrows():
                    with st.expander(f"Update: {row['Task Name']}"):
                        row_num = idx + 2
                        ah = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"h{idx}")
                        stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                        if st.button("Save Update", key=f"b{idx}"):
                            ws.update_cell(row_num, 5, ah)
                            ws.update_cell(row_num, 6, stat)
                            st.success("Updated!")
                            st.rerun()
            else: st.info("No pending tasks today.")

# --- 8. PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_log", clear_on_submit=True):
        channel = st.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue & Email", "Complaint Management"])
        cnt = st.number_input("Audit Count", min_value=1, step=1)
        err = st.number_input("Critical Errors", min_value=0, step=1)
        if st.form_submit_button("Log QA Data"):
            ws = get_ws("qa")
            if ws:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                hrs = round((cnt * 15) / 60, 2)
                ws.append_row([today_str, channel, cnt, err, acc, hrs])
                st.success(f"QA Saved for {channel}!")

# --- 9. PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding & Management")
    ws = get_ws("drivers")
    
    st.subheader("Step 1: New Driver Entry")
    with st.form("dr_new", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Name")
        p = c2.text_input("Phone")
        city = c3.selectbox("City", ["Dhaka", "Chittagong", "Sylhet"])
        c4, c5, c6 = st.columns(3)
        interested = c4.selectbox("Interested?", ["Yes", "No"])
        doc_stat = c5.selectbox("Doc Status", ["Pending", "Partially Submitted", "Submitted"])
        acc_stat = c6.selectbox("Acc Status", ["Inactive", "Active"])
        if st.form_submit_button("Submit"):
            if ws and n and p:
                ws.append_row([today_str, n, p, city, interested, doc_stat, acc_stat, "No"])
                st.success("New driver entry saved!")
                st.rerun()

    st.divider()
    st.subheader("Step 2: Update Existing Status")
    if ws:
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip()
            # শুধু যাদের প্রথম ট্রিপ হয়নি তাদের দেখাবে
            pending = df[df['First Trip'] != "Yes"]
            for idx, row in pending.iterrows():
                row_num = idx + 2
                with st.expander(f"Update: {row['Name']} ({row['Phone']})"):
                    u1, u2, u3 = st.columns(3)
                    new_doc = u1.selectbox("Doc Status", ["Pending", "Partially Submitted", "Submitted"], key=f"d{idx}")
                    new_acc = u2.selectbox("Acc Status", ["Inactive", "Active"], key=f"a{idx}")
                    trip = u3.checkbox("First Trip Completed?", key=f"t{idx}")
                    if st.button("Confirm Update", key=f"btn{idx}"):
                        ws.update_cell(row_num, 6, new_doc)
                        ws.update_cell(row_num, 7, new_acc)
                        if trip: ws.update_cell(row_num, 8, "Yes")
                        st.success("Updated!")
                        st.rerun()

# --- 10. PAGE: SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("⚠️ Suspension Re-Validation")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up:
        raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        if st.button("Push Data to Sheet"):
            ws = get_ws("revalidation")
            if ws:
                ws.append_rows(raw.fillna("").values.tolist())
                st.success("Suspension data updated!")

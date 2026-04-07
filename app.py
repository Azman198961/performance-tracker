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

# --- 2. HELPER FUNCTIONS (এটি সবার আগে থাকতে হবে) ---
def get_working_days(start_date, end_date):
    """শুক্রবার, শনিবার এবং সরকারি ছুটি বাদ দিয়ে কার্যদিবস গণনা করে"""
    # সরকারি ছুটির লিস্ট (প্রয়োজন অনুযায়ী এখানে তারিখ যোগ করুন)
    govt_holidays = [
        datetime(2026, 2, 21).date(), # শহীদ দিবস
        datetime(2026, 3, 26).date(), # স্বাধীনতা দিবস
        datetime(2026, 4, 14).date(), # পহেলা বৈশাখ
    ]
    
    all_days = pd.date_range(start=start_date, end=end_date)
    # Friday=4, Saturday=5
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
    
    # সময়সীমা নির্ধারণ
    start_of_week = today - timedelta(days=(today.weekday() + 2) % 7) # Sunday শুরু ধরলে
    start_of_month = today.replace(day=1)
    
    weekly_working_days = get_working_days(start_of_week, today)
    monthly_working_days = get_working_days(start_of_month, today)

    # ডাটা লোড
    ws_tasks = get_ws("tasks")
    ws_drivers = get_ws("drivers")
    
    t_df = pd.DataFrame(ws_tasks.get_all_records()) if ws_tasks else pd.DataFrame()
    d_df = pd.DataFrame(ws_drivers.get_all_records()) if ws_drivers else pd.DataFrame()

    if not t_df.empty:
        t_df.columns = t_df.columns.str.strip()
        t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not d_df.empty:
        d_df.columns = d_df.columns.str.strip()
        d_df['Date'] = pd.to_datetime(d_df['Date']).dt.date

    # --- মেট্রিক্স ডিসপ্লে ---
    st.subheader("🎯 Real-time Progress")
    m1, m2, m3, m4 = st.columns(4)

    # ১. ডেইলি টাস্ক (Target: 12)
    today_tasks_count = len(t_df[t_df['Date'] == today]) if not t_df.empty else 0
    m1.metric("Today's Tasks", f"{today_tasks_count}/12", delta=today_tasks_count - 12)

    # ২. ড্রাইভার অনবোর্ডিং (Target: 10/week)
    week_drivers = len(d_df[(d_df['Date'] >= start_of_week) & (d_df['Acc Status'] == 'active')]) if not d_df.empty else 0
    m2.metric("Weekly Onboarding", f"{week_drivers}/10", delta=week_drivers - 10)

    # ৩. ট্রেনিং সেশন (Target: 5/week)
    week_trainings = len(t_df[(t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Agent Training')]) if not t_df.empty else 0
    m3.metric("Weekly Training", f"{week_trainings}/5", delta=week_trainings - 5)

    # ৪. কাজের দিন
    m4.metric("Working Days (Month)", f"{monthly_working_days} Days")

    st.divider()

    # --- সাপ্তাহিক চেকলিস্ট ---
    st.subheader("🗓️ Weekly Deliverables Checklist")
    c1, c2 = st.columns(2)
    
    with c1:
        # সাসপেনশন রিপোর্ট চেক
        susp_status = any((t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Suspension') & (t_df['Status'] == 'Completed')) if not t_df.empty else False
        st.checkbox("Suspension Re-validation Report Sharing", value=susp_status, disabled=True)
        
        # ইনিশিয়েটিভ চেক
        init_status = any((t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Initiatives') & (t_df['Status'] == 'Completed')) if not t_df.empty else False
        st.checkbox("Weekly Performance Initiative", value=init_status, disabled=True)

    with c2:
        st.info("**QA Insight:** Identify & report top recurring issues weekly.")
        st.write("Current QA entries logged for this week are being analyzed.")

    st.divider()
    st.subheader("📋 Today's Task List")
    st.dataframe(t_df[t_df['Date'] == today], use_container_width=True)

# --- বাকি পেজগুলো (Plan Tasks, Update EOD, QA, etc.) আগের মতোই থাকবে ---
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
                        if st.button("Save", key=f"b{idx}"):
                            ws.update_cell(row_num, 5, ah)
                            ws.update_cell(row_num, 6, stat)
                            st.success("Updated!")
                            st.rerun()
            else: st.info("No pending tasks today.")

elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_log", clear_on_submit=True):
        channel = st.selectbox("Channel", ["Inbound", "Live Chat", "Report Issue & Email", "Complaint Management"])
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log QA"):
            ws = get_ws("qa")
            if ws:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                hrs = (cnt * 15) / 60
                ws.append_row([today_str, channel, cnt, err, acc, hrs])
                st.success("QA Logged!")

elif page == "Driver Onboarding":
    st.header("🚗 Driver Management")
    with st.form("dr", clear_on_submit=True):
        n = st.text_input("Name")
        p = st.text_input("Phone")
        as_stat = st.selectbox("Status", ["pending", "active"])
        if st.form_submit_button("Save"):
            ws = get_ws("drivers")
            if ws:
                ws.append_row([today_str, n, p, "Dhaka", "Yes", "submitted", as_stat, "Done", "No"])
                st.success("Saved!")

elif page == "Suspension Re-Validation":
    st.header("⚠️ Suspension Re-Validation")
    up = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if up:
        raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        if st.button("Push to Sheet"):
            ws = get_ws("revalidation")
            if ws:
                ws.append_rows(raw.fillna("").values.tolist())
                st.success("Data Pushed!")

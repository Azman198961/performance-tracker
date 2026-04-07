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
elif page == "Dashboard":
    st.header("📊 Performance Dashboard & Targets")
    
    # --- ক্যালকুলেশন পার্ট ---
    # বর্তমান সপ্তাহের শুরু (Sunday থেকে শুরু ধরলে)
    start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)
    # বর্তমান মাসের শুরু
    start_of_month = today.replace(day=1)
    
    # ওয়ার্কিং ডে বের করা
    weekly_working_days = get_working_days(start_of_week, today)
    monthly_working_days = get_working_days(start_of_month, today)

    # --- টার্গেট সেট করা ---
    targets = {
        "Daily Tasks": {"target": 12, "unit": "tasks/day"},
        "Driver Onboarding": {"target": 10, "unit": "drivers/week"},
        "Training Sessions": {"target": 5, "unit": "sessions/week"},
        "Suspension Report": {"target": 1, "unit": "report/week"},
        "Improvement Initiative": {"target": 1, "unit": "initiative/week"}
    }

    # --- ডাটা লোড করা ---
    ws_tasks = get_ws("tasks")
    ws_drivers = get_ws("drivers")
    
    t_df = pd.DataFrame(ws_tasks.get_all_records()) if ws_tasks else pd.DataFrame()
    d_df = pd.DataFrame(ws_drivers.get_all_records()) if ws_drivers else pd.DataFrame()

    # ডাটা ফরম্যাটিং
    for df in [t_df, d_df]:
        if not df.empty: 
            df['Date'] = pd.to_datetime(df['Date']).dt.date

    # --- ডিসপ্লে মেট্রিক্স ---
    st.subheader("🎯 Key Performance Targets (This Week)")
    m1, m2, m3, m4 = st.columns(4)

    # ১. টাস্ক কাউন্ট (আজকের)
    today_tasks = len(t_df[t_df['Date'] == today]) if not t_df.empty else 0
    m1.metric("Today's Tasks", f"{today_tasks}/12", delta=f"{today_tasks - 12}")

    # ২. ড্রাইভার অনবোর্ডিং (সাপ্তাহিক)
    week_drivers = len(d_df[d_df['Date'] >= start_of_week]) if not d_df.empty else 0
    m2.metric("Weekly Onboarding", f"{week_drivers}/10", delta=f"{week_drivers - 10}")

    # ৩. ট্রেনিং সেশন (সাপ্তাহিক)
    # ধরে নিচ্ছি Task Category 'Agent Training' এ সেভ হয়
    week_trainings = len(t_df[(t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Agent Training')]) if not t_df.empty else 0
    m3.metric("Weekly Training", f"{week_trainings}/5", delta=f"{week_trainings - 5}")

    # ৪. ওয়ার্কিং ডেস রিমেইনিং
    m4.metric("Days Worked (Month)", f"{monthly_working_days} Days")

    st.divider()

    # --- স্পেশাল রিপোর্ট চেকলিস্ট ---
    st.subheader("🗓️ Weekly Deliverables Status")
    c1, c2 = st.columns(2)
    
    with c1:
        st.info("**Checklist (Weekly):**")
        # এই লজিকগুলো আপনার টাস্ক লিস্টের স্ট্যাটাস থেকে আসবে
        suspension_done = any(t_df[(t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Suspension')]['Status'] == 'Completed')
        st.checkbox("Suspension Re-validation Report Sharing", value=suspension_done, disabled=True)
        
        initiative_done = any(t_df[(t_df['Date'] >= start_of_week) & (t_df['Task Category'] == 'Initiatives')]['Status'] == 'Completed')
        st.checkbox("Performance Improvement Initiative", value=initiative_done, disabled=True)

    with c2:
        st.warning("**QA Insight:**")
        st.write("Top recurring issues are identified based on QA logs.")
        # এখানে QA থেকে ডাইনামিক ডেটা দেখাতে পারেন
        st.button("Review QA Findings for Top Issues")

    st.divider()
    st.subheader("📋 All Task History")
    st.dataframe(t_df.sort_values(by='Date', ascending=False), use_container_width=True)

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
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df.columns = df.columns.str.strip() # KeyError থেকে বাঁচতে কলাম ক্লিন করা
            
            if 'Date' in df.columns and 'Status' in df.columns:
                # আজকের 'Planned' টাস্কগুলো খুঁজে বের করা
                mask = (df['Date'].astype(str) == today_str) & (df['Status'] == "Planned")
                pending = df[mask]
                
                if not pending.empty:
                    for idx, row in pending.iterrows():
                        with st.expander(f"Update: {row['Task Name']}"):
                            row_num = idx + 2 
                            ah = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"h{idx}")
                            stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                            if st.button("Confirm Update", key=f"b{idx}"):
                                ws.update_cell(row_num, 5, ah) # Col 5 = Actual Hours
                                ws.update_cell(row_num, 6, stat) # Col 6 = Status
                                st.success("Updated Successfully!")
                                st.rerun()
                else:
                    st.info("আজকের জন্য কোনো পেন্ডিং টাস্ক নেই।")
            else:
                st.error("Sheet-এ 'Date' অথবা 'Status' কলাম পাওয়া যায়নি।")

# --- 8. PAGE: QA DETAILS (MODIFIED) ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    
    # QA শিট থেকে আগের ডেটা দেখানোর জন্য
    ws = get_ws("qa")
    
    with st.form("qa_log", clear_on_submit=True):
        # ১. চ্যানেল ড্রপডাউন
        channel = st.selectbox("Channel Name", [
            "Inbound", 
            "Live Chat", 
            "Report Issue & Email", 
            "Complaint Management"
        ])
        
        col1, col2 = st.columns(2)
        # ২. অডিট কাউন্ট
        cnt = col1.number_input("Audit Count", min_value=1, step=1)
        # ৩. ক্রিটিক্যাল এরর কাউন্ট
        err = col2.number_input("Critical Errors", min_value=0, step=1)
        
        if st.form_submit_button("Log QA"):
            if ws:
                # ক্যালকুলেশন
                accuracy = f"{((cnt - err) / cnt) * 100:.1f}%" if cnt > 0 else "0%"
                # অডিট প্রতি ১৫ মিনিট ধরে টাইম ক্যালকুলেশন (আপনার আগের লজিক অনুযায়ী)
                hrs = round((cnt * 15) / 60, 2)
                
                # শিটে ডেটা পুশ (Date, Channel, Audit Count, Errors, Accuracy, Hours)
                try:
                    ws.append_row([today_str, channel, cnt, err, accuracy, hrs])
                    st.success(f"✅ QA Logged for {channel}!")
                except Exception as e:
                    st.error(f"Error saving to sheet: {e}")

    # হিস্ট্রি দেখার জন্য ছোট একটি টেবিল (অপশনাল কিন্তু হেল্পফুল)
    st.divider()
    st.subheader("Recent QA Entries")
    if ws:
        qa_data = ws.get_all_records()
        if qa_data:
            q_df = pd.DataFrame(qa_data)
            q_df.columns = q_df.columns.str.strip()
            # শুধু আজকের এন্ট্রিগুলো দেখাবে
            st.dataframe(q_df[q_df['Date'].astype(str) == today_str], use_container_width=True)

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

# --- 10. PAGE: SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("⚠️ Suspension Re-Validation")
    up = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    if up:
        try:
            raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.write("Preview:", raw.head(3))
            if st.button("Push All to Google Sheet"):
                ws = get_ws("revalidation")
                if ws:
                    data_to_push = raw.fillna("").values.tolist() # NaN হ্যান্ডেল করা
                    ws.append_rows(data_to_push)
                    st.success(f"Successfully pushed {len(data_to_push)} rows!")
        except Exception as e:
            st.error(f"File Error: {e}")

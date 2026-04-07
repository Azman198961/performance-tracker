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
    
    if ws_tasks:
        data = ws_tasks.get_all_records()
        if data:
            t_df = pd.DataFrame(data)
            t_df.columns = t_df.columns.str.strip() # কলামের নামের স্পেস ক্লিন করা
            
            if 'Date' in t_df.columns:
                t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
                view = st.radio("Timeframe:", ["Daily", "Weekly", "All Time"], horizontal=True)
                
                if view == "Daily":
                    t_f = t_df[t_df['Date'] == today]
                elif view == "Weekly":
                    sw = today - timedelta(days=today.weekday())
                    t_f = t_df[t_df['Date'] >= sw]
                else:
                    t_f = t_df

                # Metrics
                plan_h = pd.to_numeric(t_f['Planned Hours'], errors='coerce').sum()
                act_h = pd.to_numeric(t_f['Actual Hours'], errors='coerce').sum()
                
                m1, m2 = st.columns(2)
                m1.metric("Total Planned Hours", f"{plan_h:.1f}h")
                m2.metric("Efficiency %", f"{(act_h/plan_h*100):.1f}%" if plan_h > 0 else "0%")
                
                st.subheader("📋 Task Records")
                st.dataframe(t_f, use_container_width=True)
            else:
                st.error("Sheet-এ 'Date' কলাম পাওয়া যায়নি।")
        else:
            st.info("ড্যাশবোর্ডে দেখানোর মতো কোনো ডেটা নেই।")

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
                hrs = (cnt * 15) / 60 
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

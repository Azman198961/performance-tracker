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

def get_gspread_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        # app.py te ei line-ti khuje modify korun:
creds_dict = st.secrets["gcp_service_account"].to_dict() # to_dict() add korun
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n") # Fixes the slash issue
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Configuration Error: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_worksheet(name):
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except Exception as e:
        st.error(f"Sheet Error: Make sure tab '{name}' exists and Email is shared as Editor.")
        return None

# --- 3. AUTHENTICATION ---
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
                st.session_state['user'] = u_email
                st.rerun()
            else:
                st.error("Invalid credentials!")
    st.stop()

# --- 4. NAVIGATION ---
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 5. PAGE: DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    
    t_ws = get_worksheet("tasks")
    q_ws = get_worksheet("qa")
    d_ws = get_worksheet("drivers")
    
    if t_ws:
        t_df = pd.DataFrame(t_ws.get_all_records())
        q_df = pd.DataFrame(q_ws.get_all_records()) if q_ws else pd.DataFrame()
        d_df = pd.DataFrame(d_ws.get_all_records()) if d_ws else pd.DataFrame()
        
        if not t_df.empty:
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
            p_h = pd.to_numeric(t_f['Planned Hours'], errors='coerce').sum()
            a_h = pd.to_numeric(t_f['Actual Hours'], errors='coerce').sum()
            qa_count = pd.to_numeric(q_df['Audit Count'], errors='coerce').sum() if not q_df.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Planned Hours", f"{p_h}h")
            c2.metric("Actual Hours", f"{a_h}h")
            c3.metric("Total Audits", int(qa_count))
            
            st.divider()
            st.subheader("📋 Task Efficiency Breakdown")
            breakdown = t_f.groupby('Task Name').agg({'Planned Hours': 'sum', 'Actual Hours': 'sum'})
            st.table(breakdown)
            st.bar_chart(t_f.groupby('Task Category')[['Planned Hours', 'Actual Hours']].sum())
        else:
            st.info("No task data found.")

# --- 6. PAGE: PLAN DAILY TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    with st.form("p_form", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "Suspension", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Save Plan"):
            ws = get_worksheet("tasks")
            if ws:
                ws.append_row([today_str, cat, name, ph, 0, "Planned", ""])
                st.success("Planned Successfully!")

# --- 7. PAGE: UPDATE STATUS ---
elif page == "Update Status (EOD)":
    st.header("✅ End of Day Update")
    ws = get_worksheet("tasks")
    if ws:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        pending = df[(df['Date'] == today_str) & (df['Status'] == "Planned")]
        
        if not pending.empty:
            for idx, row in pending.iterrows():
                with st.expander(f"Task: {row['Task Name']}"):
                    ah = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"h{idx}")
                    stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                    rem = st.text_input("Remarks", key=f"r{idx}")
                    if st.button("Update", key=f"b{idx}"):
                        ws.update_cell(idx + 2, 5, ah) # Col E
                        ws.update_cell(idx + 2, 6, stat) # Col F
                        ws.update_cell(idx + 2, 7, rem) # Col G
                        st.success("Updated!")
                        st.rerun()
        else:
            st.info("No pending tasks for today.")

# --- 8. PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_form", clear_on_submit=True):
        ch = st.selectbox("Channel", ["Email", "Chat", "Call"])
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Critical Errors", 0)
        if st.form_submit_button("Log QA"):
            ws = get_worksheet("qa")
            if ws:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                hrs = (cnt * 15) / 60
                ws.append_row([today_str, ch, cnt, err, acc, hrs])
                st.success("QA Logged Successfully!")

# --- 9. PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding Tracker")
    with st.form("dr_form", clear_on_submit=True):
        name = st.text_input("Driver Name")
        phone = st.text_input("Phone Number")
        city = st.text_input("City", "Dhaka")
        status = st.selectbox("Acc Status", ["pending", "active"])
        if st.form_submit_button("Save Driver"):
            ws = get_worksheet("drivers")
            if ws:
                ws.append_row([today_str, name, phone, city, "Yes", "submitted", status, "Call received", "No"])
                st.success("Driver Data Saved!")

# --- 10. PAGE: SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Bulk Suspension Re-Validation")
    up = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    if up:
        df_up = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        st.write("Preview Uploaded Data:")
        st.dataframe(df_up.head())
        
        if st.button("Push All to Google Sheet"):
            ws = get_worksheet("revalidation")
            if ws:
                # Add Date column
                df_up.insert(0, 'Re-validation Date', today_str)
                ws.append_rows(df_up.values.tolist())
                st.success("Bulk Data Pushed Successfully!")

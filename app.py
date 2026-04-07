import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import os

# --- 1. GLOBAL CONFIG & DATE ---
today = datetime.now().date()
today_str = str(today)

# --- 2. GOOGLE SHEETS SETUP ---
# Authenticate using Streamlit Secrets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open the Sheet by ID
    SHEET_ID = "1WM3ezVX9Sq9e7kxyxs7aV0vKQFcd_wxWCRuUOOtZbeU"
    sh = client.open_by_key(SHEET_ID)
except Exception as e:
    st.error("Google Sheets Connection Error. Please check Secrets and Share Settings.")
    st.stop()

# Helper function to load data from a specific worksheet
def load_gsheet_data(sheet_name):
    try:
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# Helper function to append data to a worksheet
def save_to_gsheet(sheet_name, row_data):
    try:
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

# --- 3. PAGE CONFIG & AUTH ---
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")
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
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 5. DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    
    t_df = load_gsheet_data("tasks")
    q_df = load_gsheet_data("qa")
    d_df = load_gsheet_data("drivers")

    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    # Fix Data Types and Filtering
    for df in [t_df, q_df, d_df]:
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            for col in df.columns:
                if any(x in col for x in ["Hours", "Count", "Errors"]):
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Filtering Logic
    if view == "Daily":
        t_f, q_f, d_f = t_df[t_df['Date'] == today], q_df[q_df['Date'] == today], d_df[d_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_f, q_f, d_f = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw], d_df[d_df['Date'] >= sw]
    else:
        t_f, q_f, d_f = t_df, q_df, d_df

    # Metrics
    audits = q_f['Audit Count'].sum() if not q_f.empty else 0
    drivers = len(d_f[d_f['Acc Status'] == 'active']) if not d_f.empty else 0
    plan_h = t_f['Planned Hours'].sum() if not t_f.empty else 0
    act_h = t_f['Actual Hours'].sum() if not t_f.empty else 0
    eff = (act_h / plan_h * 100) if plan_h > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Audits Done", int(audits))
    m2.metric("Drivers Onboarded", int(drivers))
    m3.metric("Actual Hours", f"{act_h:.1f}h")
    m4.metric("Efficiency %", f"{eff:.1f}%")

    st.divider()
    st.subheader("📋 Task Breakdown & Efficiency")
    if not t_f.empty:
        breakdown = t_f.groupby('Task Name').agg({'Task Category':'first', 'Planned Hours':'sum', 'Actual Hours':'sum'})
        breakdown['Efficiency %'] = (breakdown['Actual Hours'] / breakdown['Planned Hours'] * 100).round(1)
        st.table(breakdown)
        st.bar_chart(t_f.groupby('Task Category')[['Planned Hours', 'Actual Hours']].sum())
    else:
        st.info("No data found for this timeframe.")

# --- 6. PLAN DAILY TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    with st.form("plan_form", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "Suspension Re-Validation", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add to Plan"):
            if save_to_gsheet("tasks", [today_str, cat, name, ph, 0.0, "Planned", ""]):
                st.success("Planned in Google Sheet!")
                st.rerun()

# --- 7. UPDATE STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Update")
    df = load_gsheet_data("tasks")
    # Finding planned tasks for today
    pending = df[(df['Date'] == today_str) & (df['Status'] == "Planned")]
    
    if not pending.empty:
        for idx, row in pending.iterrows():
            with st.expander(f"Task: {row['Task Name']}"):
                ah = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"h{idx}")
                stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                if st.button("Update Status", key=f"b{idx}"):
                    # Logic to update specific row in GSheet
                    worksheet = sh.worksheet("tasks")
                    # GSheet index starts at 1, and header is row 1
                    worksheet.update_cell(idx + 2, 5, ah) # Actual Hours Column
                    worksheet.update_cell(idx + 2, 6, stat) # Status Column
                    st.success("Updated!")
                    st.rerun()
    else:
        st.info("No pending tasks for today.")

# --- 8. QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_form"):
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Critical Errors", 0)
        if st.form_submit_button("Submit QA"):
            hrs = (cnt * 15) / 60
            acc = f"{((cnt-err)/cnt)*100:.1f}%"
            if save_to_gsheet("qa", [today_str, "General", cnt, err, acc, hrs]):
                st.success("QA Logged!")

# --- 9. DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding")
    with st.form("dr_form"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Driver Name")
        p = c2.text_input("Phone Number")
        as_stat = c1.selectbox("Acc Status", ["pending", "active"])
        if st.form_submit_button("Save"):
            if save_to_gsheet("drivers", [today_str, n, p, "Dhaka", "Yes", "submitted", as_stat, "Call received", False]):
                st.success("Driver Saved!")

# --- 10. SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Bulk Suspension Re-Validation")
    up = st.file_uploader("Upload Excel", type=["xlsx", "csv"])
    if up:
        raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        
        # Mapping and showing in data editor
        st.subheader("Verify Data")
        edited = st.data_editor(raw, use_container_width=True)
        
        if st.button("Final Submission to GSheet"):
            worksheet = sh.worksheet("revalidation")
            # Convert DF to list of lists for bulk upload
            worksheet.append_rows(edited.values.tolist())
            st.success("All data pushed to Google Sheet!")

import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. ACCESS CONTROL ---
USER_CREDENTIALS = {
    "asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"

}

st.set_page_config(page_title="Performance Tracker Pro", layout="wide")

# --- 2. LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Login")
    with st.form("login_form"):
        u_email = st.text_input("Email").lower().strip()
        u_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u_email in USER_CREDENTIALS and USER_CREDENTIALS[u_email] == u_pass:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u_email
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# --- 3. DATA & COLUMNS ---
COLS = {
    "tasks": ["Date", "Task Category", "Task Name", "Planned Hours", "Status", "Remarks"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "Call Status", "First Trip"],
    "revalidation": ["Date", "User/Driver ID", "Category", "Re-validation Status", "Remarks"]
}

def save_data(df, name):
    df.to_csv(f"data_{name}.csv", index=False)

def load_data(name):
    if os.path.exists(f"data_{name}.csv"):
        df = pd.read_csv(f"data_{name}.csv")
        for col in COLS.get(name, []):
            if col not in df.columns: df[col] = ""
        return df
    return pd.DataFrame(columns=COLS.get(name, []))

# --- 4. NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state['user']}")
page = st.sidebar.radio("Navigation", ["Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation", "Dashboard"])
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- PAGE: PLAN DAILY TASKS ---
if page == "Plan Daily Tasks":
    st.header("📝 Morning Task Planning")
    df = load_data("tasks")
    with st.form("plan_form", clear_on_submit=True):
        cat = st.selectbox("Task Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "User & Driver Suspension Re-Validation"])
        name = st.text_input("Task Description/Name")
        hrs = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add to Today's Plan"):
            new_task = pd.DataFrame([[datetime.now().date(), cat, name, hrs, "Planned", ""]], columns=COLS["tasks"])
            df = pd.concat([df, new_task], ignore_index=True)
            save_data(df, "tasks")
            st.success("Task added to plan!")
    st.subheader("Today's Plan")
    st.write(df[df['Date'] == str(datetime.now().date())])

# --- PAGE: UPDATE TASK STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Task Update")
    df = load_data("tasks")
    today = str(datetime.now().date())
    pending_tasks = df[(df['Date'] == today) & (df['Status'] == "Planned")]
    
    if not pending_tasks.empty:
        for idx, row in pending_tasks.iterrows():
            with st.expander(f"Task: {row['Task Name']} ({row['Task Category']})"):
                new_status = st.selectbox(f"Status for {idx}", ["Completed", "Incompleted"], key=f"stat_{idx}")
                rem = ""
                if new_status == "Incompleted":
                    rem = st.text_input("Reason for being Incomplete", key=f"rem_{idx}")
                
                if st.button("Update This Task", key=f"btn_{idx}"):
                    df.at[idx, 'Status'] = new_status
                    df.at[idx, 'Remarks'] = rem
                    save_data(df, "tasks")
                    st.success("Updated!")
                    st.rerun()
    else:
        st.info("No planned tasks left to update for today.")
    st.subheader("Status Summary")
    st.dataframe(df[df['Date'] == today])

# --- PAGE: SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 User & Driver Suspension Re-Validation")
    rv_df = load_data("revalidation")
    
    uploaded_file = st.file_uploader("Upload Excel/CSV File", type=["xlsx", "csv"])
    if uploaded_file:
        data = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        st.write("### File Data")
        
        # Row by row validation
        for idx, row in data.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
            c1.write(f"ID: {row.iloc[0]}") # Assuming 1st col is ID
            val_stat = c2.selectbox("Status", ["Valid", "Invalid"], key=f"rv_s_{idx}")
            v_rem = ""
            if val_stat == "Invalid":
                v_rem = c3.text_input("Reason", key=f"rv_r_{idx}")
            
            if c4.button("Confirm", key=f"rv_b_{idx}"):
                new_rv = pd.DataFrame([[datetime.now().date(), row.iloc[0], "Suspension", val_stat, v_rem]], columns=COLS["revalidation"])
                rv_df = pd.concat([rv_df, new_rv], ignore_index=True)
                save_data(rv_df, "revalidation")
                st.toast(f"Validated ID {row.iloc[0]}")
    st.subheader("Validation History")
    st.dataframe(rv_df)

# --- PAGE: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Performance Dashboard")
    t_df = load_data("tasks")
    rv_df = load_data("revalidation")
    
    # Weekly Re-validation Report
    st.subheader("📥 Export Weekly Reports")
    if not rv_df.empty:
        # Filter for last 7 days
        rv_df['Date'] = pd.to_datetime(rv_df['Date'])
        weekly_rv = rv_df[rv_df['Date'] > (datetime.now() - pd.Timedelta(days=7))]
        
        csv = weekly_rv.to_csv(index=False).encode('utf-8')
        st.download_button("Download Weekly Re-Validation Report (CSV)", csv, "Weekly_Suspension_Report.csv", "text/csv")
    else:
        st.info("No re-validation data to export.")

    # Task Breakdown
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Task Completion Rate")
        if not t_df.empty:
            st.bar_chart(t_df['Status'].value_counts())
    with c2:
        st.write("#### Re-validation Status")
        if not rv_df.empty:
            st.pie_chart(rv_df['Re-validation Status'].value_counts())

# (Baki QA Details ebong Driver Onboarding page logic gulo ager motoi thakbe)

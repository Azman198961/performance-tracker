import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. ACCESS CONTROL ---
USER_CREDENTIALS = {
   "asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}

st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# --- 2. LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
            else:
                st.error("Invalid credentials!")
    st.stop()

# --- 3. DATA PERSISTENCE ---
COLS = {
    "tasks": ["Date", "Task Category", "Task Name", "Planned Hours", "Actual Hours", "Status", "Remarks"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "Call Status", "First Trip"],
    "revalidation": ["Date", "ID", "Category", "Re-validation Status", "Remarks"]
}

def save_data(df, name):
    df.to_csv(f"data_{name}.csv", index=False)

def load_data(name):
    if os.path.exists(f"data_{name}.csv"):
        df = pd.read_csv(f"data_{name}.csv")
        for col in COLS.get(name, []):
            if col not in df.columns: df[col] = 0 if "Hours" in col else ""
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
        name = st.text_input("Task Description")
        p_hrs = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add to Today's Plan"):
            new_task = pd.DataFrame([[datetime.now().date(), cat, name, p_hrs, 0.0, "Planned", ""]], columns=COLS["tasks"])
            df = pd.concat([df, new_task], ignore_index=True)
            save_data(df, "tasks")
            st.success("Task Planned!")
    st.dataframe(df[df['Date'] == str(datetime.now().date())])

# --- PAGE: UPDATE TASK STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Task Update")
    df = load_data("tasks")
    today = str(datetime.now().date())
    pending = df[(df['Date'] == today) & (df['Status'] == "Planned")]
    
    if not pending.empty:
        for idx, row in pending.iterrows():
            with st.expander(f"Update: {row['Task Name']}"):
                a_hrs = st.number_input(f"Actual Hours for {idx}", 0.0, 15.0, row['Planned Hours'], key=f"hrs_{idx}")
                new_stat = st.selectbox(f"Status {idx}", ["Completed", "Incompleted"], key=f"st_{idx}")
                rem = st.text_input(f"Remarks/Reason {idx}", key=f"rem_{idx}") if new_stat == "Incompleted" else ""
                
                if st.button("Update Task", key=f"btn_{idx}"):
                    df.at[idx, 'Actual Hours'], df.at[idx, 'Status'], df.at[idx, 'Remarks'] = a_hrs, new_stat, rem
                    save_data(df, "tasks")
                    st.rerun()
    else:
        st.info("No tasks pending for update today.")
    st.dataframe(df[df['Date'] == today])

# --- PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    df = load_data("qa")
    with st.form("qa_form"):
        count = st.number_input("Audit Count", min_value=1)
        err = st.number_input("Critical Errors", 0)
        hrs = (count * 15) / 60 
        acc = f"{((count - err) / count) * 100:.2f}%"
        if st.form_submit_button("Log QA"):
            new_row = pd.DataFrame([[datetime.now().date(), "General", count, err, acc, hrs]], columns=COLS["qa"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "qa")
            st.success("QA Logged!")
    st.dataframe(df)

# --- PAGE: SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 User & Driver Suspension Re-Validation")
    rv_df = load_data("revalidation")
    uploaded = st.file_uploader("Upload Excel", type=["xlsx", "csv"])
    if uploaded:
        data = pd.read_excel(uploaded) if uploaded.name.endswith('xlsx') else pd.read_csv(uploaded)
        for idx, row in data.iterrows():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            c1.write(f"ID: {row.iloc[0]}")
            status = c2.selectbox("Status", ["Valid", "Invalid"], key=f"rv_{idx}")
            rem = c3.text_input("Remarks", key=f"rvr_{idx}") if status == "Invalid" else ""
            if c4.button("Confirm", key=f"rvb_{idx}"):
                new_rv = pd.DataFrame([[datetime.now().date(), row.iloc[0], "Suspension", status, rem]], columns=COLS["revalidation"])
                rv_df = pd.concat([rv_df, new_rv], ignore_index=True)
                save_data(rv_df, "revalidation")
                st.toast("Updated!")
    st.dataframe(rv_df)

# --- PAGE: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Final Performance Dashboard")
    t_df, q_df, rv_df = load_data("tasks"), load_data("qa"), load_data("revalidation")
    
    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    today = datetime.now().date()
    
    # Filtering Logic
    if not t_df.empty: t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not q_df.empty: q_df['Date'] = pd.to_datetime(q_df['Date']).dt.date
    
    if view == "Daily":
        t_df, q_df = t_df[t_df['Date'] == today], q_df[q_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_df, q_df = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw]
    elif view == "Monthly":
        t_df = t_df[pd.to_datetime(t_df['Date']).dt.month == today.month]
        q_df = q_df[pd.to_datetime(q_df['Date']).dt.month == today.month]

    # Metrics Calculation
    p_hrs_total = t_df['Planned Hours'].sum() if not t_df.empty else 0
    a_hrs_total = t_df['Actual Hours'].sum() if not t_df.empty else 0
    qa_hrs_total = q_df['Hours Spent'].sum() if not q_df.empty else 0
    total_actual = a_hrs_total + qa_hrs_total
    efficiency = (total_actual / p_hrs_total * 100) if p_hrs_total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned Hours", f"{p_hrs_total}h")
    c2.metric("Actual Hours (Task+QA)", f"{total_actual}h")
    c3.metric("Efficiency %", f"{efficiency:.1f}%")
    c4.metric("Suspension Validated", len(rv_df))

    st.divider()
    st.subheader("✅ Tasks Breakdown")
    if not t_df.empty:
        done_df = t_df[t_df['Status'] == 'Completed']
        for _, r in done_df.iterrows():
            st.write(f"✔️ **{r['Task Name']}** ({r['Task Category']}) | Planned: {r['Planned Hours']}h | Actual: {r['Actual Hours']}h")
    
    st.divider()
    st.subheader("📥 Export Weekly Suspension Report")
    if not rv_df.empty:
        csv = rv_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Report", csv, "Weekly_Suspension.csv", "text/csv")

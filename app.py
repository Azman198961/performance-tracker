import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. GLOBAL CONFIG & DATE (Fixes NameError) ---
today = datetime.now().date()
today_str = str(today)

# --- 2. DATA LOADING (Fixes ValueError by ensuring numeric defaults) ---
@st.cache_data(ttl=60)
def load_data_cached(name, expected_cols):
    if os.path.exists(f"data_{name}.csv"):
        try:
            df = pd.read_csv(f"data_{name}.csv")
            for col in expected_cols:
                if col not in df.columns:
                    # Fix: Ensure numeric columns default to 0.0, not "pending"
                    df[col] = 0.0 if any(x in col for x in ["Hours", "Count", "Errors"]) else "pending"
            return df[expected_cols]
        except:
            return pd.DataFrame(columns=expected_cols)
    return pd.DataFrame(columns=expected_cols)

def save_data(df, name):
    df.to_csv(f"data_{name}.csv", index=False)
    st.cache_data.clear()

# --- 3. ACCESS CONTROL ---
USER_CREDENTIALS = {"asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

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

# --- 4. COLUMNS ---
COLS = {
    "tasks": ["Date", "Task Category", "Task Name", "Planned Hours", "Actual Hours", "Status", "Remarks"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Date", "Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "Call Status", "First Trip"],
    "revalidation": ["Re-validation Date", "Execution Date", "Trip ID", "User/Driver Number", "User/Driver ID", "Suspension Reason", "Executed By", "Re-validation Status", "Remarks"]
}

# --- 5. SIDEBAR ---
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 6. PAGE: DASHBOARD (DYNAMIC & FIXED) ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    t_df = load_data_cached("tasks", COLS["tasks"])
    q_df = load_data_cached("qa", COLS["qa"])
    d_df = load_data_cached("drivers", COLS["drivers"])

    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    # Ensure Dates are datetime objects for filtering
    for df in [t_df, q_f := q_df, d_f := d_df]:
        if not df.empty: df['Date'] = pd.to_datetime(df['Date']).dt.date

    # Filter Logic
    if view == "Daily":
        t_f, q_f, d_f = t_df[t_df['Date'] == today], q_df[q_df['Date'] == today], d_df[d_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_f, q_f, d_f = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw], d_df[d_df['Date'] >= sw]
    elif view == "Monthly":
        sm = today.replace(day=1)
        t_f, q_f, d_f = t_df[t_df['Date'] >= sm], q_df[q_df['Date'] >= sm], d_df[d_df['Date'] >= sm]
    else:
        t_f, q_f, d_f = t_df, q_df, d_df

    # Summary Metrics (Fixes ValueError with pd.to_numeric)
    audits = pd.to_numeric(q_f['Audit Count'], errors='coerce').sum() if not q_f.empty else 0
    drivers = len(d_f[d_f['Acc Status'] == 'active']) if not d_f.empty else 0
    plan_h = pd.to_numeric(t_f['Planned Hours'], errors='coerce').sum() if not t_f.empty else 0
    act_h = pd.to_numeric(t_f['Actual Hours'], errors='coerce').sum() if not t_f.empty else 0
    qa_h = pd.to_numeric(q_f['Hours Spent'], errors='coerce').sum() if not q_f.empty else 0
    
    total_actual = act_h + qa_h
    eff = (total_actual / plan_h * 100) if plan_h > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Audits Done", int(audits))
    m2.metric("Drivers Onboarded", int(drivers))
    m3.metric("Total Actual Hours", f"{total_actual:.1f}h")
    m4.metric("Efficiency %", f"{eff:.1f}%")

    st.divider()
    
    # Detailed Task Table
    st.subheader("📋 Task Performance Breakdown")
    if not t_f.empty:
        breakdown = t_f.groupby('Task Name').agg({
            'Task Category': 'first',
            'Planned Hours': 'sum',
            'Actual Hours': 'sum'
        })
        breakdown['Efficiency %'] = (breakdown['Actual Hours'] / breakdown['Planned Hours'] * 100).round(1)
        st.table(breakdown)
        
        st.subheader("📈 Planned vs Actual Hours by Category")
        st.bar_chart(t_f.groupby('Task Category')[['Planned Hours', 'Actual Hours']].sum())
    else:
        st.info("No data available for selected timeframe.")

# --- 7. PAGE: PLAN DAILY TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    df = load_data_cached("tasks", COLS["tasks"])
    with st.form("plan", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "Suspension Re-Validation", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add to Plan"):
            new = pd.DataFrame([[today_str, cat, name, ph, 0.0, "Planned", ""]], columns=COLS["tasks"])
            save_data(pd.concat([df, new]), "tasks")
            st.success("Added!")
            st.rerun()
    st.subheader("Today's Schedule")
    st.dataframe(df[df['Date'] == today_str])

# --- 8. PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Management")
    df = load_data_cached("drivers", COLS["drivers"])
    with st.form("dr", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Name")
        p = c2.text_input("Phone")
        city = c1.text_input("City")
        ds = c1.selectbox("Doc Status", ["pending", "submitted"])
        as_stat = c2.selectbox("Acc Status", ["pending", "active"])
        if st.form_submit_button("Save Driver"):
            new = pd.DataFrame([[today_str, n, p, city, "Yes", ds, as_stat, "Call received", False]], columns=COLS["drivers"])
            save_data(pd.concat([df, new]), "drivers")
            st.rerun()
    st.dataframe(df)

# --- 9. PAGE: UPDATE STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Update")
    df = load_data_cached("tasks", COLS["tasks"])
    pending = df[(df['Date'] == today_str) & (df['Status'] == "Planned")]
    if not pending.empty:
        for idx, row in pending.iterrows():
            with st.expander(f"Update: {row['Task Name']}"):
                ah = st.number_input("Actual Hours", 0.0, 15.0, row['Planned Hours'], key=f"h{idx}")
                stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                if st.button("Update", key=f"b{idx}"):
                    df.at[idx, 'Actual Hours'], df.at[idx, 'Status'] = ah, stat
                    save_data(df, "tasks")
                    st.rerun()
    st.dataframe(df[df['Date'] == today_str])

# --- 10. PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    df = load_data_cached("qa", COLS["qa"])
    with st.form("qa_log"):
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log"):
            hrs = (cnt * 15) / 60
            new = pd.DataFrame([[today_str, "General", cnt, err, f"{((cnt-err)/cnt)*100:.1f}%", hrs]], columns=COLS["qa"])
            save_data(pd.concat([df, new]), "qa")
            st.rerun()
    st.dataframe(df)

# --- 11. PAGE: SUSPENSION RE-VALIDATION (Fixed Excel Import) ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Suspension Re-Validation")
    RV_COLS = ["Re-validation Date", "Execution Date", "Trip ID", "User/Driver Number", "User/Driver ID", "Suspension Reason", "Executed By", "Re-validation Status", "Remarks"]
    rv_df = load_data_cached("revalidation", RV_COLS)
    up = st.file_uploader("Upload Excel", type=["xlsx", "csv"])
    if up:
        if 'temp_rv' not in st.session_state:
            # Fix: Case-insensitive column matching
            raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            raw.columns = [str(c).strip().lower() for c in raw.columns]
            temp = pd.DataFrame(columns=RV_COLS)
            mapping = {"Execution Date": "execution date", "Trip ID": "trip id", "User/Driver Number": "user/driver number", "User/Driver ID": "user/driver id", "Suspension Reason": "suspension reason", "Executed By": "executed by"}
            for target, excel in mapping.items():
                if excel in raw.columns: temp[target] = raw[excel]
            temp["Re-validation Date"] = today_str
            temp["Re-validation Status"] = "Valid"
            st.session_state['temp_rv'] = temp
        
        edited = st.data_editor(st.session_state['temp_rv'], use_container_width=True, hide_index=True)
        if st.button("Final Submission ✅"):
            save_data(pd.concat([rv_df, edited], ignore_index=True), "revalidation")
            del st.session_state['temp_rv']
            st.rerun()
    st.divider()
    st.subheader("History")
    st.dataframe(rv_df[rv_df["Trip ID"] != "pending"] if not rv_df.empty else rv_df, use_container_width=True, hide_index=True)

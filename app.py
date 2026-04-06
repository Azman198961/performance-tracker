import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. GLOBAL CONFIG & DATE (FIXED NameError) ---
today = datetime.now().date()
today_str = str(today)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60)
def load_data_cached(name, expected_cols):
    if os.path.exists(f"data_{name}.csv"):
        try:
            df = pd.read_csv(f"data_{name}.csv")
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = 0.0 if "Hours" in col else "pending"
            return df[expected_cols]
        except:
            return pd.DataFrame(columns=expected_cols)
    return pd.DataFrame(columns=expected_cols)

def save_data(df, name):
    df.to_csv(f"data_{name}.csv", index=False)
    st.cache_data.clear()

# --- 3. ACCESS CONTROL ---
USER_CREDENTIALS = {
    "asikul.islam@pathao.com": "Win@1234",
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

# --- 6. PAGE: DASHBOARD (DYNAMIC UPDATED) ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    t_df = load_data_cached("tasks", COLS["tasks"])
    q_df = load_data_cached("qa", COLS["qa"])
    d_df = load_data_cached("drivers", COLS["drivers"])

    # Timeframe Filter
    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    if not t_df.empty: t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not q_df.empty: q_df['Date'] = pd.to_datetime(q_df['Date']).dt.date
    if not d_df.empty: d_df['Date'] = pd.to_datetime(d_df['Date']).dt.date

    if view == "Daily":
        t_f = t_df[t_df['Date'] == today]
        q_f = q_df[q_df['Date'] == today]
        d_f = d_df[d_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_f, q_f, d_f = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw], d_df[d_df['Date'] >= sw]
    elif view == "Monthly":
        sm = today.replace(day=1)
        t_f, q_f, d_f = t_df[t_df['Date'] >= sm], q_df[q_df['Date'] >= sm], d_df[d_df['Date'] >= sm]
    else:
        t_f, q_f, d_f = t_df, q_df, d_df

    # Metrics
    c1, c2, c3 = st.columns(3)
    audits = q_f['Audit Count'].sum() if not q_f.empty else 0
    drivers = len(d_f[d_f['Acc Status'] == 'active']) if not d_f.empty else 0
    total_p = t_f['Planned Hours'].sum() if not t_f.empty else 0
    total_a = t_f['Actual Hours'].sum() + (q_f['Hours Spent'].sum() if not q_f.empty else 0)
    overall_eff = (total_a / total_p * 100) if total_p > 0 else 0

    c1.metric("Total Audits", int(audits))
    c2.metric("Drivers Onboarded", int(drivers))
    c3.metric("Overall Efficiency", f"{overall_eff:.1f}%")

    st.divider()

    # Task Breakdown Table
    st.subheader("📋 Task Performance Breakdown")
    if not t_f.empty:
        # Grouping data to show count and hours
        breakdown = t_f.groupby('Task Name').agg({
            'Task Category': 'count',
            'Planned Hours': 'sum',
            'Actual Hours': 'sum'
        }).rename(columns={'Task Category': 'Count'})
        
        breakdown['Efficiency %'] = (breakdown['Actual Hours'] / breakdown['Planned Hours'] * 100).round(1)
        st.table(breakdown)
        
        # Performance Graph
        st.subheader("📈 Category Productivity (Planned vs Actual)")
        chart_data = t_f.groupby('Task Category')[['Planned Hours', 'Actual Hours']].sum()
        st.bar_chart(chart_data)
    else:
        st.info("No tasks logged for this timeframe.")

# --- 7. PAGE: PLAN DAILY TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    df = load_data_cached("tasks", COLS["tasks"])
    with st.form("p_form", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "User & Driver Suspension Re-Validation", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add to Plan"):
            new = pd.DataFrame([[today_str, cat, name, ph, 0.0, "Planned", ""]], columns=COLS["tasks"])
            save_data(pd.concat([df, new]), "tasks")
            st.success("Task Added!")
            st.rerun()
    st.subheader("Today's Plan")
    st.dataframe(df[df['Date'] == today_str])

# --- 8. PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Management")
    df = load_data_cached("drivers", COLS["drivers"])
    with st.form("add_dr", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Full Name")
        p = c2.text_input("Phone Number")
        city = c1.text_input("City")
        intst = c2.selectbox("Interested?", ["Yes", "No", "Pending"])
        ds = c1.selectbox("Doc Status", ["pending", "partially pending", "submitted"])
        as_stat = c2.selectbox("Acc Status", ["pending", "active"])
        cs = c1.selectbox("Call Status", ["Call received", "DNP"])
        trip = c2.checkbox("First Trip Completed?")
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[today_str, n, p, city, intst, ds, as_stat, cs, trip]], columns=COLS["drivers"])
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
                ah = st.number_input(f"Actual Hours", 0.0, 15.0, row['Planned Hours'], key=f"h{idx}")
                stat = st.selectbox(f"Status", ["Completed", "Incompleted"], key=f"s{idx}")
                rem = st.text_input(f"Remarks", key=f"r{idx}")
                if st.button(f"Update", key=f"b{idx}"):
                    df.at[idx, 'Actual Hours'], df.at[idx, 'Status'], df.at[idx, 'Remarks'] = ah, stat, rem
                    save_data(df, "tasks")
                    st.rerun()
    st.dataframe(df[df['Date'] == today_str])

# --- 10. PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    df = load_data_cached("qa", COLS["qa"])
    with st.form("q_f"):
        cnt = st.number_input("Audit Count", min_value=1)
        err = st.number_input("Critical Errors", 0)
        if st.form_submit_button("Log QA"):
            hrs = (cnt * 15) / 60
            acc = f"{((cnt-err)/cnt)*100:.2f}%"
            new = pd.DataFrame([[today_str, "General", cnt, err, acc, hrs]], columns=COLS["qa"])
            save_data(pd.concat([df, new]), "qa")
            st.rerun()
    st.dataframe(df)

# --- 11. PAGE: SUSPENSION RE-VALIDATION (BULK) ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Suspension Re-Validation")
    RV_COLS = ["Re-validation Date", "Execution Date", "Trip ID", "User/Driver Number", "User/Driver ID", "Suspension Reason", "Executed By", "Re-validation Status", "Remarks"]
    rv_df = load_data_cached("revalidation", RV_COLS)
    up = st.file_uploader("Upload Excel", type=["xlsx", "csv"])
    if up:
        if 'temp_rv_data' not in st.session_state:
            raw = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            raw.columns = [str(c).strip().lower() for c in raw.columns]
            temp_rows = []
            for _, row in raw.iterrows():
                new_row = {col: "" for col in RV_COLS}
                new_row["Re-validation Date"] = today_str
                new_row["Re-validation Status"] = "Valid"
                mapping = {"Execution Date": "execution date", "Trip ID": "trip id", "User/Driver Number": "user/driver number", "User/Driver ID": "user/driver id", "Suspension Reason": "suspension reason", "Executed By": "executed by"}
                for target, excel in mapping.items():
                    if excel in raw.columns: new_row[target] = row[excel]
                temp_rows.append(new_row)
            st.session_state['temp_rv_data'] = pd.DataFrame(temp_rows)
        
        if 'temp_rv_data' in st.session_state:
            edited = st.data_editor(st.session_state['temp_rv_data'], use_container_width=True, hide_index=True)
            if st.button("Final Submission ✅"):
                save_data(pd.concat([rv_df, edited], ignore_index=True), "revalidation")
                del st.session_state['temp_rv_data']
                st.rerun()
    st.divider()
    st.subheader("Validation History")
    st.dataframe(rv_df[rv_df["Trip ID"] != "pending"] if not rv_df.empty else rv_df, use_container_width=True, hide_index=True)

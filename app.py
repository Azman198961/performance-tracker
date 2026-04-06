import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. SECURE ACCESS CONTROL ---
# Change these emails and passwords as per your need
USER_CREDENTIALS = {
   "asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}

# Page Configuration
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# --- 2. LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access - Performance Tracker")
    with st.container():
        st.write("Please log in with your authorized credentials.")
        with st.form("login_form"):
            user_email = st.text_input("Email Address")
            user_password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                email_lower = user_email.lower().strip()
                if email_lower in USER_CREDENTIALS and USER_CREDENTIALS[email_lower] == user_password:
                    st.session_state['logged_in'] = True
                    st.session_state['current_user'] = email_lower
                    st.success("Access Granted!")
                    st.rerun()
                else:
                    st.error("Invalid Email or Password!")
    st.stop()

# --- 3. DATA STORAGE LOGIC ---
COLS = {
    "tasks": ["Date", "Task Name", "Description", "Planned Hours", "Actual Hours", "Manager Approved", "Status"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "Call Status", "First Trip"],
    "train": ["Date", "Agent", "Topic", "Pre", "Post"],
    "init": ["Project", "Desc", "Purpose", "Blocker", "Outcome", "Approval"]
}

def save_data(df, filename):
    df.to_csv(f"data_{filename}.csv", index=False)

def load_data(filename):
    expected_cols = COLS.get(filename, [])
    if os.path.exists(f"data_{filename}.csv"):
        df = pd.read_csv(f"data_{filename}.csv")
        # Syncing columns to avoid errors
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0 if "Hours" in col or "Count" in col else "pending"
        return df[expected_cols]
    return pd.DataFrame(columns=expected_cols)

# --- 4. NAVIGATION & SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state['current_user']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

page = st.sidebar.radio("Go to:", ["Daily Tasks", "QA Details", "Driver Onboarding", "Training", "Initiatives", "Dashboard"])

# --- PAGE: DAILY TASKS ---
if page == "Daily Tasks":
    st.header("📋 Daily Task Tracker")
    df = load_data("tasks")
    with st.form("task_form", clear_on_submit=True):
        t_name = st.text_input("Task Name")
        desc = st.text_area("Description")
        p_hrs = st.number_input("Planned Hours", 0.5)
        a_hrs = st.number_input("Actual Hours", 0.0)
        appr = st.checkbox("Manager Aligned?")
        stat = st.selectbox("Status", ["Planned", "Completed"])
        if st.form_submit_button("Save Task"):
            new_row = pd.DataFrame([[datetime.now().date(), t_name, desc, p_hrs, a_hrs, appr, stat]], columns=COLS["tasks"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "tasks")
            st.success("Task Saved Successfully!")
    st.dataframe(df)

# --- PAGE: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    df = load_data("qa")
    with st.form("qa_form"):
        ch = st.selectbox("Channel", ["Email", "Chat", "Call", "Social Media"])
        count = st.number_input("Audit Count", min_value=1)
        err = st.number_input("Critical Errors", min_value=0)
        # 15 mins per audit logic
        hrs = (count * 15) / 60 
        acc = f"{((count - err) / count) * 100:.2f}%"
        if st.form_submit_button("Log QA"):
            new_row = pd.DataFrame([[datetime.now().date(), ch, count, err, acc, hrs]], columns=COLS["qa"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "qa")
            st.success(f"Logged! Total Time: {hrs} hrs")
    st.dataframe(df)

# --- PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Management")
    df = load_data("drivers")
    t1, t2 = st.tabs(["Add New Driver", "Update Existing Status"])
    
    with t1:
        with st.form("add_dr", clear_on_submit=True):
            n = st.text_input("Name"); p = st.text_input("Phone"); c = st.text_input("City")
            i = st.selectbox("Interested?", ["Yes", "No", "Pending"])
            ds = st.selectbox("Doc Status", ["pending", "partially pending", "submitted"])
            as_stat = st.selectbox("Acc Status", ["pending", "active"])
            cs = st.selectbox("Call Status", ["Call received", "DNP"])
            f = st.checkbox("First Trip?")
            if st.form_submit_button("Submit"):
                new_row = pd.DataFrame([[n, p, c, i, ds, as_stat, cs, f]], columns=COLS["drivers"])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, "drivers")
                st.success("New Driver Added!")
                st.rerun()

    with t2:
        if not df.empty:
            name_select = st.selectbox("Select Driver to Update", df['Name'].tolist())
            idx = df[df['Name'] == name_select].index[0]
            with st.form("update_dr"):
                u_ds = st.selectbox("Update Doc Status", ["pending", "partially pending", "submitted"], index=["pending", "partially pending", "submitted"].index(df.at[idx, 'Doc Status']))
                u_as = st.selectbox("Update Acc Status", ["pending", "active"], index=["pending", "active"].index(df.at[idx, 'Acc Status']))
                u_cs = st.selectbox("Update Call Status", ["Call received", "DNP"], index=["Call received", "DNP"].index(df.at[idx, 'Call Status']))
                u_f = st.checkbox("First Trip Completed?", value=df.at[idx, 'First Trip'])
                if st.form_submit_button("Update Details"):
                    df.at[idx, 'Doc Status'], df.at[idx, 'Acc Status'] = u_ds, u_as
                    df.at[idx, 'Call Status'], df.at[idx, 'First Trip'] = u_cs, u_f
                    save_data(df, "drivers"); st.success("Updated!"); st.rerun()
    st.dataframe(df)

# --- PAGE: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Performance Dashboard")
    t_df, q_df, d_df = load_data("tasks"), load_data("qa"), load_data("drivers")
    
    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    today = datetime.now().date()
    
    # Date Filtering Logic
    if not t_df.empty: t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not q_df.empty: q_df['Date'] = pd.to_datetime(q_df['Date']).dt.date

    if view == "Daily":
        t_df = t_df[t_df['Date'] == today]; q_df = q_df[q_df['Date'] == today]
    elif view == "Weekly":
        sw = today - pd.Timedelta(days=today.weekday())
        t_df = t_df[t_df['Date'] >= sw]; q_df = q_df[q_df['Date'] >= sw]

    # Metrics
    done = len(t_df[t_df['Status']=='Completed']) if not t_df.empty else 0
    planned = len(t_df[t_df['Status']=='Planned']) if not t_df.empty else 0
    audits = q_df['Audit Count'].sum() if not q_df.empty else 0
    qa_hrs = q_df['Hours Spent'].sum() if not q_df.empty else 0
    # Onboarded = Only Active status drivers
    onboarded = len(d_df[d_df['Acc Status'] == 'active']) if not d_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Tasks Done", done)
        st.caption(f"Planned: {planned}")
    c2.metric("Audits Done", int(audits))
    c3.metric("QA Hours", f"{qa_hrs} hrs")
    c4.metric("Driver Onboarded", onboarded)

    st.divider()
    # Task List Breakdown
    st.write("### ✅ Tasks Completed List")
    if not t_df.empty:
        c_list = t_df[t_df['Status'] == 'Completed']['Task Name'].tolist()
        if c_list:
            for i, name in enumerate(c_list, 1): st.write(f"{i}. {name}")
        else: st.info("No tasks completed yet.")
    
    st.divider()
    if st.button("Generate Final Report"):
        st.write("Excel generation logic active.")

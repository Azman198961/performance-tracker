import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Page Config
st.set_page_config(page_title="Performance Tracker", layout="wide")

# Data Loading Logic
def save_data(df, filename):
    df.to_csv(f"data_{filename}.csv", index=False)

def load_data(filename, columns):
    if os.path.exists(f"data_{filename}.csv"):
        return pd.read_csv(f"data_{filename}.csv")
    return pd.DataFrame(columns=columns)

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Daily Tasks", "QA Details", "Driver Onboarding", "Training", "Initiatives", "Dashboard"])

# --- PAGE 1: DAILY TASKS ---
if page == "Daily Tasks":
    st.header("📋 Daily Task Tracker")
    cols = ["Date", "Task Name", "Description", "Planned Hours", "Actual Hours", "Approved", "Status"]
    df = load_data("tasks", cols)
    with st.form("task_form", clear_on_submit=True):
        t_name = st.text_input("Task Name")
        desc = st.text_area("Description")
        p_hrs = st.number_input("Planned Hours", 0.5)
        a_hrs = st.number_input("Actual Hours", 0.0)
        appr = st.checkbox("Manager Aligned?")
        stat = st.selectbox("Status", ["Planned", "Completed"])
        if st.form_submit_button("Save"):
            new_row = pd.DataFrame([[datetime.now().date(), t_name, desc, p_hrs, a_hrs, appr, stat]], columns=cols)
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "tasks")
            st.success("Saved!")
    st.dataframe(df)

# --- PAGE 2: QA DETAILS (Updated) ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    cols = ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"]
    df = load_data("qa", cols)
    
    with st.form("qa_form"):
        channel = st.selectbox("Channel", ["Email", "Chat", "Call", "Social Media"])
        count = st.number_input("Audit Count", min_value=1)
        errors = st.number_input("Critical Errors", min_value=0)
        
        # Calculation: 15 mins per audit
        hours_spent = (count * 15) / 60 
        accuracy = ((count - errors) / count) * 100
        
        if st.form_submit_button("Log QA"):
            new_data = pd.DataFrame([[datetime.now().date(), channel, count, errors, f"{accuracy}%", hours_spent]], columns=cols)
            df = pd.concat([df, new_data], ignore_index=True)
            save_data(df, "qa")
    st.dataframe(df)

# --- PAGE 3: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding")
    cols = ["Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "First Trip"]
    df = load_data("drivers", cols)
    with st.form("dr_form"):
        n = st.text_input("Name"); p = st.text_input("Phone"); c = st.text_input("City")
        i = st.selectbox("Interested?", ["Yes", "No"]); d = st.text_input("Doc Status")
        a = st.text_input("Acc Status"); f = st.checkbox("First Trip?")
        if st.form_submit_button("Save"):
            new_row = pd.DataFrame([[n, p, c, i, d, a, f]], columns=cols)
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "drivers")
    st.dataframe(df)

# --- PAGE 4: TRAINING ---
elif page == "Training":
    st.header("🎓 Training Effectiveness")
    cols = ["Date", "Agent", "Topic", "Pre", "Post"]
    df = load_data("train", cols)
    with st.form("tr_form"):
        ag = st.text_input("Agent Name"); top = st.text_input("Topic")
        pre = st.number_input("Pre-Score", 0); post = st.number_input("Post-Score", 0)
        if st.form_submit_button("Log"):
            new_row = pd.DataFrame([[datetime.now().date(), ag, top, pre, post]], columns=cols)
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "train")
    st.dataframe(df)

# --- PAGE 5: INITIATIVES ---
elif page == "Initiatives":
    st.header("💡 New Initiatives")
    cols = ["Project", "Desc", "Purpose", "Blocker", "Outcome", "Approval"]
    df = load_data("init", cols)
    with st.form("in_form"):
        prj = st.text_input("Project Name"); dsc = st.text_area("Desc")
        pur = st.text_input("Purpose"); blk = st.text_input("Blocker")
        out = st.text_input("Outcome"); ap = st.checkbox("Manager Approval")
        if st.form_submit_button("Submit"):
            new_row = pd.DataFrame([[prj, dsc, pur, blk, out, ap]], columns=cols)
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "init")
    st.dataframe(df)

# --- PAGE 6: DASHBOARD & EXPORT (Full Update) ---
elif page == "Dashboard":
    st.header("📊 Performance Analytics Dashboard")
    
    # Load all data
    tasks_df = load_data("tasks", ["Date", "Task Name", "Description", "Planned Hours", "Actual Hours", "Manager Approved", "Status"])
    qa_df = load_data("qa", ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"])
    drivers_df = load_data("drivers", ["Name", "Number", "City", "Interested?", "Docs Status", "Account Status", "First Trip"])
    training_df = load_data("train", ["Date", "Agent", "Topic", "Pre", "Post"])

    # Date Filter Logic
    st.subheader("📅 Filter Report")
    filter_type = st.radio("Select View:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    # Convert Date column to datetime for filtering
    if not tasks_df.empty:
        tasks_df['Date'] = pd.to_datetime(tasks_df['Date']).dt.date
    if not qa_df.empty:
        qa_df['Date'] = pd.to_datetime(qa_df['Date']).dt.date

    today = datetime.now().date()
    
    # Filtering Data
    if filter_type == "Daily":
        tasks_df = tasks_df[tasks_df['Date'] == today]
        qa_df = qa_df[qa_df['Date'] == today]
    elif filter_type == "Weekly":
        start_of_week = today - pd.Timedelta(days=today.weekday())
        tasks_df = tasks_df[tasks_df['Date'] >= start_of_week]
        qa_df = qa_df[qa_df['Date'] >= start_of_week]
    elif filter_type == "Monthly":
        tasks_df = tasks_df[pd.to_datetime(tasks_df['Date']).dt.month == today.month]
        qa_df = qa_df[pd.to_datetime(qa_df['Date']).dt.month == today.month]

    # Metrics Row 1
    c1, c2, c3, c4 = st.columns(4)
    
    total_tasks = len(tasks_df[tasks_df['Status'] == 'Completed']) if not tasks_df.empty else 0
    total_audits = int(qa_df['Audit Count'].sum()) if not qa_df.empty else 0
    # QA Hours calculation (15 mins per audit)
    total_qa_hours = qa_df['Hours Spent'].sum() if not qa_df.empty else 0
    total_task_hours = tasks_df['Actual Hours'].sum() if not tasks_df.empty else 0

    c1.metric("Tasks Completed", total_tasks)
    c2.metric("Total Audits Done", total_audits)
    c3.metric("QA Hours (15m/ea)", f"{total_qa_hours} hrs")
    c4.metric("Onboarded Drivers", len(drivers_df) if not drivers_df.empty else 0)

    # Metrics Row 2
    st.divider()
    c5, c6 = st.columns(2)
    with c5:
        st.write("### 🕒 Total Productivity")
        st.info(f"Total Combined Work Hours: **{total_qa_hours + total_task_hours} hrs**")
    
    with c6:
        st.write("### 📈 Training Effectiveness")
        if not training_df.empty:
            avg_improvement = (pd.to_numeric(training_df['Post']) - pd.to_numeric(training_df['Pre'])).mean()
            st.success(f"Average Performance Jump: **{avg_improvement:.2f}%**")
        else:
            st.write("No training data available.")

    # Export Section
    st.divider()
    st.subheader("📥 Download Performance Report")
    
    if st.button("Generate Excel Report"):
        report_name = f"PIP_Report_{filter_type}_{today}.xlsx"
        with pd.ExcelWriter(report_name) as writer:
            tasks_df.to_excel(writer, sheet_name="Tasks", index=False)
            qa_df.to_excel(writer, sheet_name="QA_Audits", index=False)
            drivers_df.to_excel(writer, sheet_name="Drivers", index=False)
            training_df.to_excel(writer, sheet_name="Training", index=False)
        
        with open(report_name, "rb") as f:
            st.download_button("Click here to Download", f, file_name=report_name)

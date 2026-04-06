import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Page Configuration
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# Columns definition to keep everything synced
COLS = {
    "tasks": ["Date", "Task Name", "Description", "Planned Hours", "Actual Hours", "Manager Approved", "Status"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Name", "Number", "City", "Interested?", "Docs Status", "Account Status", "First Trip"],
    "train": ["Date", "Agent", "Topic", "Pre", "Post"],
    "init": ["Project", "Desc", "Purpose", "Blocker", "Outcome", "Approval"]
}

def save_data(df, filename):
    df.to_csv(f"data_{filename}.csv", index=False)

def load_data(filename):
    expected_cols = COLS.get(filename, [])
    if os.path.exists(f"data_{filename}.csv"):
        df = pd.read_csv(f"data_{filename}.csv")
        # Add missing columns if any (to prevent KeyError)
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0 if "Hours" in col or "Count" in col else ""
        return df[expected_cols] # Ensure column order
    return pd.DataFrame(columns=expected_cols)

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Daily Tasks", "QA Details", "Driver Onboarding", "Training", "Initiatives", "Dashboard"])

# --- PAGE 1: DAILY TASKS ---
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
        if st.form_submit_button("Save"):
            new_row = pd.DataFrame([[datetime.now().date(), t_name, desc, p_hrs, a_hrs, appr, stat]], columns=COLS["tasks"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "tasks")
            st.success("Saved!")
    st.dataframe(df)

# --- PAGE 2: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    df = load_data("qa")
    with st.form("qa_form"):
        ch = st.selectbox("Channel", ["Email", "Chat", "Call", "Social Media"])
        count = st.number_input("Audit Count", min_value=1)
        err = st.number_input("Critical Errors", min_value=0)
        hrs = (count * 15) / 60 
        acc = f"{((count - err) / count) * 100:.2f}%"
        if st.form_submit_button("Log QA"):
            new_row = pd.DataFrame([[datetime.now().date(), ch, count, err, acc, hrs]], columns=COLS["qa"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "qa")
            st.success("Logged!")
    st.dataframe(df)

# --- PAGE 3: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding")
    df = load_data("drivers")
    with st.form("dr_form"):
        n = st.text_input("Name"); p = st.text_input("Phone"); c = st.text_input("City")
        i = st.selectbox("Interested?", ["Yes", "No"]); d = st.text_input("Doc Status")
        a = st.text_input("Acc Status"); f = st.checkbox("First Trip?")
        if st.form_submit_button("Save Driver"):
            new_row = pd.DataFrame([[n, p, c, i, d, a, f]], columns=COLS["drivers"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "drivers")
    st.dataframe(df)

# --- PAGE 4: TRAINING ---
elif page == "Training":
    st.header("🎓 Training Effectiveness")
    df = load_data("train")
    with st.form("tr_form"):
        ag = st.text_input("Agent Name"); top = st.text_input("Topic")
        pre = st.number_input("Pre-Score", 0); post = st.number_input("Post-Score", 0)
        if st.form_submit_button("Log"):
            new_row = pd.DataFrame([[datetime.now().date(), ag, top, pre, post]], columns=COLS["train"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "train")
    st.dataframe(df)

# --- PAGE 5: INITIATIVES ---
elif page == "Initiatives":
    st.header("💡 New Initiatives")
    df = load_data("init")
    with st.form("in_form"):
        prj = st.text_input("Project Name"); dsc = st.text_area("Desc")
        pur = st.text_input("Purpose"); blk = st.text_input("Blocker")
        out = st.text_input("Outcome"); ap = st.checkbox("Manager Approval")
        if st.form_submit_button("Submit"):
            new_row = pd.DataFrame([[prj, dsc, pur, blk, out, ap]], columns=COLS["init"])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, "init")
    st.dataframe(df)

# --- PAGE 6: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Dashboard")
    t_df = load_data("tasks"); q_df = load_data("qa")
    d_df = load_data("drivers"); tr_df = load_data("train")

    st.subheader("📅 Date Filters")
    f_type = st.radio("View:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    today = datetime.now().date()
    if not t_df.empty: t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not q_df.empty: q_df['Date'] = pd.to_datetime(q_df['Date']).dt.date

    if f_type == "Daily":
        t_df = t_df[t_df['Date'] == today]; q_df = q_df[q_df['Date'] == today]
    elif f_type == "Weekly":
        sw = today - pd.Timedelta(days=today.weekday())
        t_df = t_df[t_df['Date'] >= sw]; q_df = q_df[q_df['Date'] >= sw]

    c1, c2, c3, c4 = st.columns(4)
    t_done = len(t_df[t_df['Status']=='Completed']) if not t_df.empty else 0
    q_count = q_df['Audit Count'].sum() if not q_df.empty else 0
    q_hrs = q_df['Hours Spent'].sum() if not q_df.empty else 0
    d_count = len(d_df) if not d_df.empty else 0

    c1.metric("Tasks Done", t_done)
    c2.metric("Audits Done", int(q_count))
    c3.metric("QA Hours", f"{q_hrs} hrs")
    c4.metric("Drivers", d_count)

    st.divider()
    if st.button("Download Final Excel Report"):
        with pd.ExcelWriter("PIP_Report.xlsx") as writer:
            t_df.to_excel(writer, sheet_name="Tasks")
            q_df.to_excel(writer, sheet_name="QA")
        with open("PIP_Report.xlsx", "rb") as f:
            st.download_button("Click to Download", f, file_name="PIP_Report.xlsx")

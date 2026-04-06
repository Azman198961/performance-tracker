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
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0 if "Hours" in col or "Count" in col else "Pending"
        return df[expected_cols]
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

# --- PAGE 3: DRIVER ONBOARDING (Update & Edit Enabled) ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding & Management")
    df = load_data("drivers")
    
    tab1, tab2 = st.tabs(["Add New Driver", "Update Existing Driver"])
    
    with tab1:
        with st.form("dr_form", clear_on_submit=True):
            n = st.text_input("Name"); p = st.text_input("Phone"); c = st.text_input("City")
            i = st.selectbox("Interested?", ["Yes", "No", "Pending"])
            ds = st.selectbox("Doc Status", ["pending", "partially pending", "submitted"])
            as_stat = st.selectbox("Acc Status", ["pending", "active"])
            cs = st.selectbox("Call Status", ["Call received", "DNP"])
            f = st.checkbox("First Trip Completed?")
            if st.form_submit_button("Add Driver"):
                new_row = pd.DataFrame([[n, p, c, i, ds, as_stat, cs, f]], columns=COLS["drivers"])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df, "drivers")
                st.success("Driver Added!")
                st.rerun()

    with tab2:
        if not df.empty:
            driver_to_edit = st.selectbox("Select Driver to Update", df['Name'].tolist())
            idx = df[df['Name'] == driver_to_edit].index[0]
            
            with st.form("edit_form"):
                e_p = st.text_input("Phone", value=df.at[idx, 'Phone'])
                e_ds = st.selectbox("Doc Status", ["pending", "partially pending", "submitted"], 
                                   index=["pending", "partially pending", "submitted"].index(df.at[idx, 'Doc Status']))
                e_as = st.selectbox("Acc Status", ["pending", "active"], 
                                   index=["pending", "active"].index(df.at[idx, 'Acc Status']))
                e_cs = st.selectbox("Call Status", ["Call received", "DNP"],
                                   index=["Call received", "DNP"].index(df.at[idx, 'Call Status']))
                e_f = st.checkbox("First Trip?", value=df.at[idx, 'First Trip'])
                
                if st.form_submit_button("Update Details"):
                    df.at[idx, 'Phone'] = e_p
                    df.at[idx, 'Doc Status'] = e_ds
                    df.at[idx, 'Acc Status'] = e_as
                    df.at[idx, 'Call Status'] = e_cs
                    df.at[idx, 'First Trip'] = e_f
                    save_data(df, "drivers")
                    st.success("Updated Successfully!")
                    st.rerun()
    st.dataframe(df)

# --- PAGE 6: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Performance Dashboard")
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

    # Metrics Calculations
    t_completed = len(t_df[t_df['Status']=='Completed']) if not t_df.empty else 0
    t_planned = len(t_df[t_df['Status']=='Planned']) if not t_df.empty else 0
    q_count = q_df['Audit Count'].sum() if not q_df.empty else 0
    q_hrs = q_df['Hours Spent'].sum() if not q_df.empty else 0
    
    # Driver logic: Only count Active ones
    d_onboarded = len(d_df[d_df['Acc Status'] == 'active']) if not d_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Tasks Done", t_completed)
        st.caption(f"Planned: {t_planned}") # Breakdown
    c2.metric("Audits Done", int(q_count))
    c3.metric("QA Hours", f"{q_hrs} hrs")
    c4.metric("Driver Onboarded", d_onboarded)
# --- Task List Breakdown (New Update) ---
    st.write("### ✅ Tasks Completed List")
    if not t_df.empty:
        # Shudhu Completed task gulo filter kore nam gulo nibe
        completed_tasks_list = t_df[t_df['Status'] == 'Completed']['Task Name'].tolist()
        
        if completed_tasks_list:
            for i, task in enumerate(completed_tasks_list, 1):
                st.write(f"{i}. {task}")
        else:
            st.info("No tasks completed yet for this period.")
    else:
        st.info("No task data found.")
    st.divider()
    # Excel Download logic
    if st.button("Generate Excel Report"):
        st.write("File ready for download (Logic simulated)")

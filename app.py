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

# --- PAGE 2: QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit")
    cols = ["Date", "Channel", "Audits", "Errors"]
    df = load_data("qa", cols)
    with st.form("qa_form"):
        ch = st.text_input("Channel")
        aud = st.number_input("Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log"):
            new_row = pd.DataFrame([[datetime.now().date(), ch, aud, err]], columns=cols)
            df = pd.concat([df, new_row], ignore_index=True)
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

# --- PAGE 6: DASHBOARD ---
elif page == "Dashboard":
    st.header("📊 Dashboard")
    t = load_data("tasks", []); q = load_data("qa", []); d = load_data("drivers", [])
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks Done", len(t[t['Status']=='Completed']) if not t.empty else 0)
    c2.metric("Total Audits", q['Audits'].sum() if not q.empty else 0)
    c3.metric("Drivers", len(d) if not d.empty else 0)
    if st.button("Export Excel"):
        st.write("Excel report ready (Demo logic)")
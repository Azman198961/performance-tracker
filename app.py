import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. OPTIMIZED DATA LOADING (CACHING) ---
@st.cache_data(ttl=60)  # 60 second por por cache refresh hobe
def load_data_cached(name, expected_cols):
    if os.path.exists(f"data_{name}.csv"):
        try:
            df = pd.read_csv(f"data_{name}.csv")
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = 0.0 if "Hours" in col else ""
            return df[expected_cols]
        except:
            return pd.DataFrame(columns=expected_cols)
    return pd.DataFrame(columns=expected_cols)

def save_data(df, name):
    df.to_csv(f"data_{name}.csv", index=False)
    st.cache_data.clear() # Data save hole cache clear hobe jate updated data dekhay

# --- 2. ACCESS CONTROL ---
USER_CREDENTIALS = {
   "asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}

st.set_page_config(page_title="Performance Tracker Pro", layout="wide")

# --- 3. LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access")
    with st.container():
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

# --- 4. CONFIGURATION ---
COLS = {
    "tasks": ["Date", "Task Category", "Task Name", "Planned Hours", "Actual Hours", "Status", "Remarks"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "Call Status", "First Trip"],
    "revalidation": ["Date", "ID", "Category", "Re-validation Status", "Remarks"]
}

# --- 5. SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state['user']}")
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 6. PAGE LOGIC (FASTER NAVIGATION) ---

# --- DASHBOARD (Optimized) ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    t_df = load_data_cached("tasks", COLS["tasks"])
    q_df = load_data_cached("qa", COLS["qa"])
    rv_df = load_data_cached("revalidation", COLS["revalidation"])

    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    today = datetime.now().date()
    
    if not t_df.empty: t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not q_df.empty: q_df['Date'] = pd.to_datetime(q_df['Date']).dt.date

    # Filtering
    if view == "Daily":
        t_f, q_f = t_df[t_df['Date'] == today], q_df[q_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_f, q_f = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw]
    else:
        t_f, q_f = t_df, q_df

    # Metrics
    p_hrs = t_f['Planned Hours'].sum() if not t_f.empty else 0
    a_hrs = t_f['Actual Hours'].sum() if not t_f.empty else 0
    qa_hrs = q_f['Hours Spent'].sum() if not q_f.empty else 0
    total_actual = a_hrs + qa_hrs
    eff = (total_actual / p_hrs * 100) if p_hrs > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned", f"{p_hrs}h")
    c2.metric("Actual (Task+QA)", f"{total_actual}h")
    c3.metric("Efficiency %", f"{eff:.1f}%")
    c4.metric("Validated", len(rv_df))

    st.divider()
    st.subheader("✅ Completed Tasks")
    if not t_f.empty:
        done = t_f[t_f['Status'] == 'Completed']
        for _, r in done.iterrows():
            st.write(f"✔️ **{r['Task Name']}** | {r['Actual Hours']}h / {r['Planned Hours']}h")

# --- PLAN TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    df = load_data_cached("tasks", COLS["tasks"])
    with st.form("p_form", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver Onboarding", "Agent Training", "Initiatives", "Suspension"])
        name = st.text_input("Task Name")
        ph = st.number_input("Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Add"):
            new = pd.DataFrame([[str(datetime.now().date()), cat, name, ph, 0.0, "Planned", ""]], columns=COLS["tasks"])
            save_data(pd.concat([df, new]), "tasks")
            st.success("Planned!")
    st.dataframe(df[df['Date'] == str(datetime.now().date())])

# --- UPDATE STATUS ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Update")
    df = load_data_cached("tasks", COLS["tasks"])
    today = str(datetime.now().date())
    pending = df[(df['Date'] == today) & (df['Status'] == "Planned")]
    
    for idx, row in pending.iterrows():
        with st.expander(f"Task: {row['Task Name']}"):
            ah = st.number_input("Actual Hours", 0.0, 15.0, row['Planned Hours'], key=f"h{idx}")
            stat = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
            rem = st.text_input("Remarks", key=f"r{idx}") if stat == "Incompleted" else ""
            if st.button("Update", key=f"b{idx}"):
                df.at[idx, 'Actual Hours'], df.at[idx, 'Status'], df.at[idx, 'Remarks'] = ah, stat, rem
                save_data(df, "tasks")
                st.rerun()

# --- SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 Re-Validation")
    rv_df = load_data_cached("revalidation", COLS["revalidation"])
    up = st.file_uploader("Upload Excel")
    if up:
        data = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
        for idx, row in data.head(10).iterrows(): # Speed up by limiting view
            c1, c2, c3 = st.columns([3,3,2])
            c1.write(f"ID: {row.iloc[0]}")
            val = c2.selectbox("Status", ["Valid", "Invalid"], key=f"v{idx}")
            if c3.button("Confirm", key=f"cb{idx}"):
                new_rv = pd.DataFrame([[str(datetime.now().date()), row.iloc[0], "Suspension", val, ""]], columns=COLS["revalidation"])
                save_data(pd.concat([rv_df, new_rv]), "revalidation")
                st.toast("Saved")

# --- QA & DRIVER PAGES (Minimized for speed) ---
elif page == "QA Details":
    st.header("🔍 QA Audit")
    df = load_data_cached("qa", COLS["qa"])
    with st.form("q"):
        cnt = st.number_input("Audits", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log"):
            hrs = (cnt * 15) / 60
            acc = f"{((cnt-err)/cnt)*100:.2f}%"
            new = pd.DataFrame([[str(datetime.now().date()), "General", cnt, err, acc, hrs]], columns=COLS["qa"])
            save_data(pd.concat([df, new]), "qa")
    st.dataframe(df)

elif page == "Driver Onboarding":
    st.header("🚗 Drivers")
    df = load_data_cached("drivers", COLS["drivers"])
    # simplified entry for speed
    with st.form("d"):
        n = st.text_input("Name")
        st_ac = st.selectbox("Status", ["pending", "active"])
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[n, "", "", "", "", st_ac, "", ""]], columns=COLS["drivers"])
            save_data(pd.concat([df, new]), "drivers")
    st.dataframe(df)

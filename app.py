import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. GLOBAL CONFIG & DATE ---
today = datetime.now().date()
today_str = str(today)

# --- 2. OPTIMIZED DATA LOADING ---
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

# --- 4. COLUMNS CONFIGURATION ---
COLS = {
    "tasks": ["Date", "Task Category", "Task Name", "Planned Hours", "Actual Hours", "Status", "Remarks"],
    "qa": ["Date", "Channel", "Audit Count", "Critical Errors", "Accuracy %", "Hours Spent"],
    "drivers": ["Name", "Phone", "City", "Interested", "Doc Status", "Acc Status", "Call Status", "First Trip"],
    "revalidation": ["Date", "ID", "Category", "Re-validation Status", "Remarks"]
}

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title(f"👤 {st.session_state['user']}")
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Task Status (EOD)", "QA Details", "Driver Onboarding", "Suspension Re-Validation"])

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 6. PAGE: DASHBOARD ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    t_df = load_data_cached("tasks", COLS["tasks"])
    q_df = load_data_cached("qa", COLS["qa"])
    d_df = load_data_cached("drivers", COLS["drivers"])
    rv_df = load_data_cached("revalidation", COLS["revalidation"])

    view = st.radio("Timeframe:", ["Daily", "Weekly", "Monthly", "All Time"], horizontal=True)
    
    if not t_df.empty: t_df['Date'] = pd.to_datetime(t_df['Date']).dt.date
    if not q_df.empty: q_df['Date'] = pd.to_datetime(q_df['Date']).dt.date

    if view == "Daily":
        t_f, q_f = t_df[t_df['Date'] == today], q_df[q_df['Date'] == today]
    elif view == "Weekly":
        sw = today - timedelta(days=today.weekday())
        t_f, q_f = t_df[t_df['Date'] >= sw], q_df[q_df['Date'] >= sw]
    else:
        t_f, q_f = t_df, q_df

    p_hrs = t_f['Planned Hours'].sum() if not t_f.empty else 0
    a_hrs = t_f['Actual Hours'].sum() if not t_f.empty else 0
    qa_hrs = q_f['Hours Spent'].sum() if not q_f.empty else 0
    total_actual = a_hrs + qa_hrs
    eff = (total_actual / p_hrs * 100) if p_hrs > 0 else 0
    onboarded = len(d_df[d_df['Acc Status'] == 'active']) if not d_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned Hours", f"{p_hrs}h")
    c2.metric("Actual (Task+QA)", f"{total_actual}h")
    c3.metric("Efficiency %", f"{eff:.1f}%")
    c4.metric("Driver Onboarded", onboarded)

    st.divider()
    st.subheader("✅ Completed Tasks")
    if not t_f.empty:
        done = t_f[t_f['Status'] == 'Completed']
        for _, r in done.iterrows():
            st.write(f"✔️ **{r['Task Name']}** ({r['Task Category']}) | {r['Actual Hours']}h / {r['Planned Hours']}h")
    
    st.divider()
    if not rv_df.empty:
        st.subheader("📥 Export Suspension Report")
        csv = rv_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Report", csv, "Suspension_Report.csv", "text/csv")

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
            st.success(f"Task added under {cat}!")
            st.rerun()
    
    st.subheader("Today's Plan")
    st.dataframe(df[df['Date'] == today_str])

# --- 8. PAGE: DRIVER ONBOARDING ---
elif page == "Driver Onboarding":
    st.header("🚗 Driver Management")
    df = load_data_cached("drivers", COLS["drivers"])
    t1, t2 = st.tabs(["Add New Driver", "Update Existing Status"])
    
    with t1:
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
            if st.form_submit_button("Add Driver"):
                new_dr = pd.DataFrame([[n, p, city, intst, ds, as_stat, cs, trip]], columns=COLS["drivers"])
                save_data(pd.concat([df, new_dr]), "drivers")
                st.success("Driver Added!")
                st.rerun()

    with t2:
        if not df.empty:
            name_select = st.selectbox("Select Driver to Update", df['Name'].unique())
            idx = df[df['Name'] == name_select].index[0]
            with st.form("up_dr"):
                u_ds = st.selectbox("Doc Status", ["pending", "partially pending", "submitted"], index=["pending", "partially pending", "submitted"].index(df.at[idx, 'Doc Status']))
                u_as = st.selectbox("Acc Status", ["pending", "active"], index=["pending", "active"].index(df.at[idx, 'Acc Status']))
                u_cs = st.selectbox("Call Status", ["Call received", "DNP"], index=["Call received", "DNP"].index(df.at[idx, 'Call Status']))
                u_f = st.checkbox("First Trip?", value=df.at[idx, 'First Trip'])
                if st.form_submit_button("Update"):
                    df.at[idx, 'Doc Status'], df.at[idx, 'Acc Status'], df.at[idx, 'Call Status'], df.at[idx, 'First Trip'] = u_ds, u_as, u_cs, u_f
                    save_data(df, "drivers")
                    st.success("Updated!")
                    st.rerun()
    st.dataframe(df)

# --- 9. PAGE: UPDATE STATUS (EOD) ---
elif page == "Update Task Status (EOD)":
    st.header("✅ End of Day Task Update")
    df = load_data_cached("tasks", COLS["tasks"])
    pending = df[(df['Date'] == today_str) & (df['Status'] == "Planned")]
    
    if not pending.empty:
        for idx, row in pending.iterrows():
            with st.expander(f"Update: {row['Task Name']} ({row['Task Category']})"):
                ah = st.number_input(f"Actual Hours", 0.0, 15.0, row['Planned Hours'], key=f"h{idx}")
                stat = st.selectbox(f"Status", ["Completed", "Incompleted"], key=f"s{idx}")
                rem = st.text_input(f"Remarks", key=f"r{idx}") if stat == "Incompleted" else ""
                if st.button(f"Update Task", key=f"b{idx}"):
                    df.at[idx, 'Actual Hours'], df.at[idx, 'Status'], df.at[idx, 'Remarks'] = ah, stat, rem
                    save_data(df, "tasks")
                    st.rerun()
    else:
        st.info("No pending tasks for today.")
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
            st.success("QA Logged!")
            st.rerun()
    st.dataframe(df)

# --- PAGE: SUSPENSION RE-VALIDATION ---
elif page == "Suspension Re-Validation":
    st.header("🔍 User & Driver Suspension Re-Validation")
    
    # Required Internal Columns
    RV_COLS = ["Re-validation Date", "Execution Date", "Trip ID", "User/Driver Number", "User/Driver ID", "Suspension Reason", "Executed By", "Re-validation Status", "Remarks"]
    rv_df = load_data_cached("revalidation", RV_COLS)
    
    up = st.file_uploader("Upload Excel File", type=["xlsx", "csv"])
    
    if up:
        if 'temp_rv_data' not in st.session_state:
            try:
                # Load Excel
                raw_data = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
                
                # Case-Insensitive & Space-striping mapping
                raw_data.columns = [str(c).strip().lower() for c in raw_data.columns]
                
                mapping = {
                    "Execution Date": "execution date",
                    "Trip ID": "trip id",
                    "User/Driver Number": "user/driver number",
                    "User/Driver ID": "user/driver id",
                    "Suspension Reason": "suspension reason",
                    "Executed By": "executed by"
                }

                temp_rows = []
                for _, row in raw_data.iterrows():
                    new_row = {col: "" for col in RV_COLS}
                    new_row["Re-validation Date"] = today_str 
                    new_row["Re-validation Status"] = "Valid"
                    
                    for target_col, excel_col in mapping.items():
                        if excel_col in raw_data.columns:
                            new_row[target_col] = row[excel_col]
                    
                    temp_rows.append(new_row)
                
                st.session_state['temp_rv_data'] = pd.DataFrame(temp_rows)
                
            except Exception as e:
                st.error(f"Error processing Excel: {e}")

        if 'temp_rv_data' in st.session_state:
            temp_df = st.session_state['temp_rv_data']
            st.subheader("📝 Edit Uploaded Data")
            
            edited_df = st.data_editor(
                temp_df,
                column_config={
                    "Re-validation Status": st.column_config.SelectboxColumn("Status", options=["Valid", "Invalid"], required=True),
                    "Remarks": st.column_config.TextColumn("Remarks")
                },
                disabled=["Re-validation Date", "Execution Date", "Trip ID", "User/Driver Number", "User/Driver ID", "Suspension Reason", "Executed By"],
                hide_index=True,
                use_container_width=True
            )

            if st.button("Final Submission ✅", type="primary"):
                final_save = pd.concat([rv_df, edited_df], ignore_index=True)
                save_data(final_save, "revalidation")
                del st.session_state['temp_rv_data']
                st.success("Successfully Validated!")
                st.rerun()

    # --- SINGLE CLEAN HISTORY TABLE ---
    st.divider()
    st.subheader("Validation History")
    
    if not rv_df.empty:
        # Filter out 'pending' or 'None' rows to show only actual data
        clean_history = rv_df[
            (rv_df["Trip ID"].notna()) & 
            (rv_df["Trip ID"] != "pending") & 
            (rv_df["Trip ID"] != "None") &
            (rv_df["Trip ID"] != "")
        ]
        st.dataframe(clean_history, use_container_width=True, hide_index=True)
    else:
        st.info("No validation history found.")

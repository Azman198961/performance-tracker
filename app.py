import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- 1. CONFIG & DATE ---
today = datetime.now().date()
today_str = str(today)
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
client = None 

try:
    if "gcp_service_account" in st.secrets:
        # AttrDict ke dict e convert kore private_key fix kora
        info = dict(st.secrets["gcp_service_account"])
        # CRITICAL: PEM formatting fix
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
    else:
        st.error("Secrets setup kora hoyni!")
except Exception as e:
    st.error(f"Authentication Error: {e}")

SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_worksheet(name):
    if client is None: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except:
        return None

# --- 3. LOGIN ---
USER_CREDENTIALS = {"asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access Control")
    with st.form("login"):
        u_email = st.text_input("Email").lower().strip()
        u_pass = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u_email in USER_CREDENTIALS and USER_CREDENTIALS[u_email] == u_pass:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = u_email
                st.rerun()
            else: st.error("Invalid credentials!")
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.write(f"👤 {st.session_state['user_email']}")
page = st.sidebar.selectbox("Navigation", ["Dashboard", "Plan Daily Tasks", "Update Status (EOD)", "QA Details", "Driver Onboarding"])
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 5. DASHBOARD (Fixed ValueError) ---
if page == "Dashboard":
    st.header("📊 Performance Dashboard")
    ws = get_worksheet("tasks")
    q_ws = get_worksheet("qa")
    
    # Safe metrics calculation to avoid ValueError
    p_h, a_h, audits = 0.0, 0.0, 0
    
    if ws:
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            # Filtering for today
            df_today = df[df['Date'] == today]
            p_h = pd.to_numeric(df_today['Planned Hours'], errors='coerce').sum()
            a_h = pd.to_numeric(df_today['Actual Hours'], errors='coerce').sum()
    
    if q_ws:
        q_data = q_ws.get_all_records()
        if q_data:
            q_df = pd.DataFrame(q_data)
            audits = pd.to_numeric(q_df['Audit Count'], errors='coerce').sum()

    # Layout
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Planned Hours", f"{p_h}h")
    c2.metric("Actual Hours", f"{a_h}h")
    c3.metric("Efficiency %", f"{(a_h/p_h*100):.1f}%" if p_h > 0 else "0%")
    c4.metric("Total Audits", int(audits) if not pd.isna(audits) else 0) # Fix for image_a9568d

# --- 6. PLAN TASKS ---
elif page == "Plan Daily Tasks":
    st.header("📝 Morning Planning")
    with st.form("p_f", clear_on_submit=True):
        cat = st.selectbox("Category", ["QA Audit", "Rental Driver", "Adhoc"])
        name = st.text_input("Task Name")
        ph = st.number_input("Planned Hours", 0.5, 12.0, 1.0)
        if st.form_submit_button("Save"):
            ws = get_worksheet("tasks")
            if ws:
                ws.append_row([today_str, cat, name, ph, 0, "Planned", ""])
                st.success("Planned in GSheet!")

# --- 7. UPDATE STATUS ---
elif page == "Update Status (EOD)":
    st.header("✅ End of Day Update")
    ws = get_worksheet("tasks")
    if ws:
        df = pd.DataFrame(ws.get_all_records())
        pending = df[(df['Date'].astype(str) == today_str) & (df['Status'] == "Planned")]
        if not pending.empty:
            for idx, row in pending.iterrows():
                with st.expander(f"Update: {row['Task Name']}"):
                    act = st.number_input("Actual Hours", 0.0, 15.0, float(row['Planned Hours']), key=f"a{idx}")
                    stt = st.selectbox("Status", ["Completed", "Incompleted"], key=f"s{idx}")
                    if st.button("Submit", key=f"b{idx}"):
                        ws.update_cell(idx + 2, 5, act)
                        ws.update_cell(idx + 2, 6, stt)
                        st.success("Updated!"); st.rerun()
        else: st.info("No tasks to update today.")

# --- 8. QA DETAILS ---
elif page == "QA Details":
    st.header("🔍 QA Audit Logs")
    with st.form("qa_f", clear_on_submit=True):
        cnt = st.number_input("Audit Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log"):
            ws = get_worksheet("qa")
            if ws:
                acc = f"{((cnt-err)/cnt)*100:.1f}%"
                ws.append_row([today_str, "General", cnt, err, acc, (cnt*15)/60])
                st.success("Logged!")

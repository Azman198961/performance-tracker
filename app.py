import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# --- 1. CONFIG ---
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")
today_str = str(datetime.now().date())

# --- 2. GOOGLE SHEETS CONNECTION (Safe Method) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_gspread_client():
    try:
        # Secrets থেকে সরাসরি JSON স্ট্রিং নেওয়া
        json_creds_str = st.secrets["gcp_service_account"]["json_creds"]
        creds_dict = json.loads(json_creds_str)
        
        # Newline fix just in case
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

client = get_gspread_client()
SHEET_ID = "1nWFF1uLd-Nwsxw7cXIeBDaVxLiC5360dvtHWrSyuoSM"

def get_ws(name):
    if not client: return None
    try:
        return client.open_by_key(SHEET_ID).worksheet(name)
    except Exception as e:
        st.error(f"Sheet Error: {e}")
        return None

# --- 3. LOGIN & NAVIGATION ---
USER_CREDENTIALS = {"asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access")
    with st.form("login"):
        u = st.text_input("Email").lower().strip()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u in USER_CREDENTIALS and USER_CREDENTIALS[u] == p:
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("Wrong info!")
    st.stop()

# --- 4. APP PAGES ---
page = st.sidebar.selectbox("Pages", ["Dashboard", "Plan Tasks", "QA Details", "Driver Onboarding", "Suspension"])

if page == "Dashboard":
    st.header("📊 Dashboard")
    ws = get_ws("tasks")
    if ws:
        df = pd.DataFrame(ws.get_all_records())
        st.dataframe(df)

elif page == "Plan Tasks":
    st.header("📝 Plan Daily Tasks")
    with st.form("p_f"):
        cat = st.selectbox("Cat", ["QA", "Training", "Onboarding"])
        task = st.text_input("Task")
        hrs = st.number_input("Hrs", 0.5, 12.0)
        if st.form_submit_button("Submit"):
            ws = get_ws("tasks")
            if ws:
                ws.append_row([today_str, cat, task, hrs, 0, "Planned"])
                st.success("Saved!")

elif page == "QA Details":
    st.header("🔍 QA Details")
    with st.form("qa_f"):
        cnt = st.number_input("Count", 1)
        err = st.number_input("Errors", 0)
        if st.form_submit_button("Log"):
            ws = get_ws("qa")
            if ws:
                ws.append_row([today_str, "Call", cnt, err, f"{((cnt-err)/cnt)*100:.1f}%"])
                st.success("QA Saved!")

elif page == "Driver Onboarding":
    st.header("🚗 Driver Onboarding")
    with st.form("dr_f"):
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        if st.form_submit_button("Save"):
            ws = get_ws("drivers")
            if ws:
                ws.append_row([today_str, name, phone, "Active"])
                st.success("Driver Saved!")

elif page == "Suspension":
    st.header("⚠️ Suspension Re-validation")
    up = st.file_uploader("Upload CSV", type=["csv"])
    if up:
        df_up = pd.read_csv(up)
        if st.button("Push to Sheet"):
            ws = get_ws("revalidation")
            if ws:
                ws.append_rows(df_up.values.tolist())
                st.success("Pushed!")

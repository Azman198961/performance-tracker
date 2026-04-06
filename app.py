import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- SECURE ACCESS CONTROL ---
# Eikhane Email ebong Password set korun
USER_CREDENTIALS = {
    "asikul.islam@pathao.com": "Win@1234",
    "jahidul.saimon@pathao.com": "saimon9090",
    "lira@pathao.com": "lira1234"
}

# Page Configuration
st.set_page_config(page_title="Performance Pulse Tracker", layout="wide")

# --- LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Secure Access")
    
    with st.form("login_form"):
        user_email = st.text_input("Email Address")
        user_password = st.text_input("Password", type="password") # Asterisk (*) hoye thakbe
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            # Check if email exists and password matches
            if user_email.lower() in USER_CREDENTIALS and USER_CREDENTIALS[user_email.lower()] == user_password:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = user_email
                st.success(f"Welcome {user_email}!")
                st.rerun()
            else:
                st.error("Invalid Email or Password!")
    st.stop()

# --- SIDEBAR & LOGOUT ---
st.sidebar.title(f"👤 {st.session_state['current_user']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- REST OF THE CODE (Baki shob code ager moto thakbe) ---
# (Eikhane apnar load_data, save_data, ebong shob Page logic gulo thakbe)

import streamlit as st
import pandas as pd
import datetime
import numpy as np
import io

# --- Webpage & Brand Setup ---
st.set_page_config(page_title="The AccounTech | FAR Tool", layout="wide", page_icon="🏢")

# --- Session State Management (Remembers User Inputs) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Initialize empty tables in session memory so data survives tab-switching
if 'rules_data' not in st.session_state:
    st.session_state.rules_data = pd.DataFrame(columns=["Asset Category", "Depreciation Method", "Useful Life"])

if 'add_data' not in st.session_state:
    st.session_state.add_data = pd.DataFrame(columns=["Control No.", "Asset Category", "Vendor Name", "Invoice No.", "Date of Purchase", "Put to use date", "FA Qty", "Original Cost (Rs)", "Salvage Value"])

if 'wo_data' not in st.session_state:
    st.session_state.wo_data = pd.DataFrame(columns=["Control No.", "Date of Write Off", "FA Write off Qty", "Reason"])

# --- 1. LOGIN PAGE ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🏢 The AccounTech</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: gray;'>Enterprise Fixed Asset Management</h4>", unsafe_allow_html=True)
    
    st.write("")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.info("ℹ️ **Account Status:** Trial license active. Credit days expiring in **7 days**.")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Secure Login", use_container_width=True)
            
            if submit:
                # Default credentials for your testing
                if username == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try admin / admin123")

# --- 2. MAIN APP ARCHITECTURE ---
def main_app():
    # Sidebar Navigation & Branding
    st.sidebar.markdown("<h2>🏢 The AccounTech</h2>", unsafe_allow_html=True)
    st.sidebar.warning("⏳ **Trial ending in 7 days.** Please renew your credits.")
    st.sidebar.divider()
    
    page = st.sidebar.radio("Navigation Menu", ["🏠 Main Dashboard", "📉 Depreciation Tool"])
    
    st.sidebar.divider()
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

    # --- PAGE: MAIN DASHBOARD ---
    if page == "🏠 Main Dashboard":
        st.title("Welcome to The AccounTech Workspace")
        st.markdown("Your connection is secure. All inputs in the Depreciation Tool are automatically saved to your current browser session. You can safely switch between tabs without losing your progress.")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Active License", value="Enterprise Trial")
        with col2:
            st.metric(label="Days Remaining", value="7 Days", delta="-1 day")

    # --- PAGE: DEPRECIATION TOOL ---
    elif page == "📉 Depreciation Tool":
        st.title("Enterprise FAR Calculator")
        st.markdown("Generates exact days-used depreciation with advanced deletion math.")

        st.subheader("Step 1: Financial Year Setup")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            fy_start

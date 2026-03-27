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
            fy_start = st.date_input("Financial Year Start:", datetime.date(2022, 4, 1))
        with col_d2:
            fy_end = st.date_input("Financial Year End:", datetime.date(2023, 3, 31))

        fy_start_dt = pd.to_datetime(fy_start)
        fy_end_dt = pd.to_datetime(fy_end)

        # Interactive Data Grids
        st.subheader("Step 2: Master Dep Approach")
        st.session_state.rules_data = st.data_editor(st.session_state.rules_data, num_rows="dynamic", use_container_width=True)

        st.divider()
        st.subheader("Step 3: Fixed Asset Additions")
        
        # --- THE FIX: Force Datetime conversion immediately before rendering ---
        st.session_state.add_data["Date of Purchase"] = pd.to_datetime(st.session_state.add_data["Date of Purchase"], errors='coerce')
        st.session_state.add_data["Put to use date"] = pd.to_datetime(st.session_state.add_data["Put to use date"], errors='coerce')
        
        st.session_state.add_data = st.data_editor(
            st.session_state.add_data, num_rows="dynamic", use_container_width=True,
            column_config={
                "Date of Purchase": st.column_config.DateColumn("Date of Purchase"), 
                "Put to use date": st.column_config.DateColumn("Put to use date")
            }
        )

        st.divider()
        st.subheader("Step 4: Fixed Asset Write-Offs")
        
        # --- THE FIX: Force Datetime conversion immediately before rendering ---
        st.session_state.wo_data["Date of Write Off"] = pd.to_datetime(st.session_state.wo_data["Date of Write Off"], errors='coerce')
        
        st.session_state.wo_data = st.data_editor(
            st.session_state.wo_data, num_rows="dynamic", use_container_width=True,
            column_config={"Date of Write Off": st.column_config.DateColumn("Date of Write Off")}
        )

        # CORE MATH ENGINE
        st.divider()
        if st.button("⚙️ Generate Enterprise FAR", type="primary"):
            with st.spinner("Processing advanced pro-rata math & deletions..."):
                try:
                    if st.session_state.rules_data.empty or st.session_state.add_data.empty:
                        st.warning("⚠️ Please enter Rules and Additions data.")
                    else:
                        df = st.session_state.add_data.copy()
                        df["Original Cost (Rs)"] = pd.to_numeric(df["Original Cost (Rs)"], errors='coerce').fillna(0)
                        df["Salvage Value"] = pd.to_numeric(df["Salvage Value"], errors='coerce').fillna(0)
                        df["FA Qty"] = pd.to_numeric(df["FA Qty"], errors='coerce').fillna(1)
                        
                        df["Max Acc Dep"] = np.maximum(df["Original Cost (Rs)"] - df["Salvage Value"], 0)
                        df["Date of Purchase"] = pd.to_datetime(df["Date of Purchase"])
                        df["Put to use date"] = pd.to_datetime(df["Put to use date"])

                        df = pd.merge(df, st.session_state.rules_data, on="Asset Category", how="left")
                        df["Useful Life"] = pd.to_numeric(df["Useful Life"], errors='coerce').fillna(1)
                        
                        safe_cost = np.where(df["Original Cost (Rs)"] == 0, 1, df["Original Cost (Rs)"])
                        wdv_rate = 1 - (df["Salvage Value"] / safe_cost) ** (1 / df["Useful Life"])
                        slm_rate = 1 / df["Useful Life"]
                        
                        df["Effective Rate"] = np.where(df["Depreciation Method"] == "WDV", wdv_rate, slm_rate)
                        df["Effective Rate"] = df["Effective Rate"].fillna(0)

                        if not st.session_state.wo_data.empty:
                            wo = st.session_state.wo_data.copy()
                            wo["Date of Write Off"] = pd.to_datetime(wo["Date of Write Off"])
                            wo["FA Write off Qty"] = pd.to_numeric(wo["FA Write off Qty"], errors='coerce').fillna(0)

                            wo_opening = wo[wo["Date of Write Off"] < fy_start_dt]
                            op_agg = wo_opening.groupby("Control No.")["FA Write off Qty"].sum().reset_index(name="FA Write off Qty Opening")
                            
                            wo_during = wo[(wo["Date of Write Off"] >= fy_start_dt) & (wo["Date of Write Off"] <= fy_end_dt)]
                            dur_agg = wo_during.groupby("Control No.")["FA Write off Qty"].sum().reset_index(name="FA Write off Qty During the year")

                            latest_wo_date = wo.groupby("Control No.")["Date of Write Off"].max().reset_index(name="Latest Date of Write Off")

                            df = pd.merge(df, op_agg, on="Control No.", how="left")
                            df = pd.merge(df, dur_agg, on="Control No.", how="left")
                            df = pd.merge(df, latest_wo_date, on="Control No.", how="left")
                        else:
                            df["FA Write off Qty Opening"] = 0
                            df["FA Write off Qty During the year"] = 0
                            df["Latest Date of Write Off"] = pd.NaT

                        df["FA Write off Qty Opening"] = df["FA Write off Qty Opening"].fillna(0)
                        df["FA Write off Qty During the year"] = df["FA Write off Qty During the year"].fillna(0)

                        safe_qty = np.where(df["FA Qty"] == 0, 1, df["FA Qty"])

                        df["FA Write off(Rs) Opening"] = (df["FA Write off Qty Opening"] / safe_qty) * df["Original Cost (Rs)"]
                        df["FA Write off(Rs) During the year"] = (df["FA Write off Qty During the year"] / safe_qty) * df["Original Cost (Rs)"]

                        df["Calc End Date"] = df["Latest Date of Write Off"].fillna(fy_end_dt)
                        df["Calc End Date"] = pd.to_datetime(df["Calc End Date"])

                        df["Days Used Opening"] = np.clip((fy_start_dt - df["Put to use date"]).dt.days, 0, 36500)
                        df["Days Used Closing"] = np.clip((df["Calc End Date"] - df["Put to use date"]).dt.days + 1, 0, 36500)

                        df["Gross Block Opening"] = np.where(df["Date of Purchase"] < fy_start_dt, df["Original Cost (Rs)"] - df["FA Write off(Rs) Opening"], 0)
                        df["Gross Block Additions"] = np.where((df["Date of Purchase"] >= fy_start_dt) & (df["Date of Purchase"] <= fy_end_dt), df["Original Cost (Rs)"], 0)
                        df["Gross Block Deletions"] = df["FA Write off(Rs) During the year"]
                        df["Gross Block Closing"] = df["Gross Block Opening"] + df["Gross Block Additions"] - df["Gross Block Deletions"]

                        # Accumulated Depreciation Calculations
                        days_op_frac = df["Days Used Opening"] / 365
                        op_slm = df["Max Acc Dep"] * df["Effective Rate"] * days_op_frac
                        op_wdv = df["Original Cost (Rs)"] * (1 - (1 - df["Effective Rate"]) ** days_op_frac)
                        
                        calc_op = np.where(df["Days Used Opening"] > 0, np.where(df["Depreciation Method"] == "SLM", op_slm, op_wdv), 0)
                        df["Acc Dep Opening"] = np.minimum(calc_op, df["Max Acc Dep"]).fillna(0)

                        days_cl_frac = df["Days Used Closing"] / 365
                        cl_slm = df["Max Acc Dep"] * df["Effective Rate"] * days_cl_frac
                        cl_wdv = df["Original Cost (Rs)"] * (1 - (1 - df["Effective Rate"]) ** days_cl_frac)
                        
                        calc_cl = np.where(df["Days Used Closing"] > 0, np.where(df["Depreciation Method"] == "SLM", cl_slm, cl_wdv), 0)
                        df["Acc Dep Closing"] = np.minimum(calc_cl, df["Max Acc Dep"]).fillna(0)

                        df["Dep During Year"] = np.maximum(df["Acc Dep Closing"] - df["Acc Dep Opening"], 0).fillna(0)

                        # Depreciation on Deletions Logic
                        calc_start_date = np.maximum(fy_start_dt, df["Put to use date"])
                        df["Days Used on Deletions"] = np.where(
                            (df["Latest Date of Write Off"] >= fy_start_dt) & (df["Latest Date of Write Off"] <= fy_end_dt),
                            (pd.to_datetime(df["Latest Date of Write Off"]) - calc_start_date).dt.days + 1,
                            0
                        )
                        df["Days Used on Deletions"] = np.clip(df["Days Used on Deletions"], 0, 365)
                        
                        del_days_frac = df["Days Used on Deletions"] / 365
                        base_del = df["Gross Block Deletions"] - df["Salvage Value"]
                        
                        del_slm = base_del * df["Effective Rate"] * del_days_frac
                        del_wdv = base_del * (1 - (1 - df["Effective Rate"]) ** del_days_frac)
                        
                        df["Depreciation on Deletions"] = np.where(
                            df["Gross Block Deletions"] > 0,
                            np.maximum(np.where(df["Depreciation Method"] == "SLM", del_slm, del_wdv), 0),
                            0
                        ).fillna(0)

                        # Net Block Logic
                        df["Net Block Opening"] = (df["Gross Block Opening"] - df["Acc Dep Opening"]).fillna(0)
                        df["Net Block Closing"] = (df["Gross Block Closing"] - df["Acc Dep Closing"]).fillna(0)

                        # Formatted Output
                        final_cols = [
                            "Control No.", "Date of Purchase", "Put to use date", "Asset Category", 
                            "Gross Block Opening", "Gross Block Additions", "Gross Block Deletions", "Gross Block Closing",
                            "Acc Dep Opening", "Depreciation on Deletions", "Dep During Year", "Acc Dep Closing", 
                            "Net Block Opening", "Net Block Closing"
                        ]
                        final_far = df[final_cols]

                        st.success("Calculations complete! Deletion depreciation math applied successfully.")
                        st.dataframe(final_far.style.format({col: "{:,.2f}" for col in final_far.select_dtypes(include=['float64','int64']).columns}), use_container_width=True, hide_index=True)

                        # Excel Download
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            final_far.to_excel(writer, index=False, sheet_name='Detailed FAR')
                        
                        st.download_button(
                            label="📥 Download Exact FAR (Excel)",
                            data=output.getvalue(),
                            file_name=f"The_AccounTech_FAR_{fy_end_dt.strftime('%Y')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"Calculation Error: {e}")

# --- Render Application State ---
if st.session_state.logged_in:
    main_app()
else:
    login_page()

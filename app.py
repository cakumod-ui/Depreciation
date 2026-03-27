import streamlit as st
import pandas as pd
import datetime
import numpy as np
import io

# --- Webpage & Brand Setup ---
st.set_page_config(page_title="The AccounTech | FAR Tool", layout="wide", page_icon="🏢")

# --- Session State Management ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'rules_data' not in st.session_state:
    st.session_state.rules_data = pd.DataFrame(columns=["Asset Category", "Depreciation Method", "Useful Life"])

if 'add_data' not in st.session_state:
    st.session_state.add_data = pd.DataFrame(columns=["Control No.", "Asset Category", "Vendor Name", "Invoice No.", "Date of Purchase", "Put to use date", "FA Qty", "Original Cost (Rs)", "Salvage Value"])

if 'wo_data' not in st.session_state:
    st.session_state.wo_data = pd.DataFrame(columns=["Control No.", "Date of Write Off", "FA Write off Qty", "Reason"])

# --- Helper Function ---
def safe_numeric(col, default_val=0):
    """Safely converts Excel comma-formatted strings into pure Python numbers."""
    cleaned = col.astype(str).str.replace(r'[^\d.-]', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce').fillna(default_val)

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
                if username == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try admin / admin123")

# --- 2. MAIN APP ARCHITECTURE ---
def main_app():
    st.sidebar.markdown("<h2>🏢 The AccounTech</h2>", unsafe_allow_html=True)
    st.sidebar.warning("⏳ **Trial ending in 7 days.** Please renew your credits.")
    st.sidebar.divider()
    
    page = st.sidebar.radio("Navigation Menu", ["🏠 Main Dashboard", "📉 Depreciation Tool"])
    
    st.sidebar.divider()
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

    if page == "🏠 Main Dashboard":
        st.title("Welcome to The AccounTech Workspace")
        st.markdown("Your connection is secure. All inputs in the Depreciation Tool are automatically saved to your current browser session.")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Active License", value="Enterprise Trial")
        with col2:
            st.metric(label="Days Remaining", value="7 Days", delta="-1 day")

    elif page == "📉 Depreciation Tool":
        st.title("Enterprise FAR Calculator")
        st.markdown("Generates exact days-used depreciation with advanced proportional logic.")

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
        st.session_state.add_data["Date of Purchase"] = pd.to_datetime(st.session_state.add_data["Date of Purchase"], errors='coerce')
        st.session_state.add_data["Put to use date"] = pd.to_datetime(st.session_state.add_data["Put to use date"], errors='coerce')
        st.session_state.add_data = st.data_editor(
            st.session_state.add_data, num_rows="dynamic", use_container_width=True,
            column_config={"Date of Purchase": st.column_config.DateColumn("Date of Purchase"), "Put to use date": st.column_config.DateColumn("Put to use date")}
        )

        st.divider()
        st.subheader("Step 4: Fixed Asset Write-Offs")
        st.session_state.wo_data["Date of Write Off"] = pd.to_datetime(st.session_state.wo_data["Date of Write Off"], errors='coerce')
        st.session_state.wo_data = st.data_editor(
            st.session_state.wo_data, num_rows="dynamic", use_container_width=True,
            column_config={"Date of Write Off": st.column_config.DateColumn("Date of Write Off")}
        )

        # CORE MATH ENGINE
        st.divider()
        if st.button("⚙️ Generate Enterprise FAR", type="primary"):
            with st.spinner("Processing exact proportional pro-rata math..."):
                try:
                    if st.session_state.rules_data.empty or st.session_state.add_data.empty:
                        st.warning("⚠️ Please enter Rules and Additions data.")
                    else:
                        df = st.session_state.add_data.copy()
                        
                        df["Original Cost (Rs)"] = safe_numeric(df["Original Cost (Rs)"], 0)
                        df["Salvage Value"] = safe_numeric(df["Salvage Value"], 0)
                        df["FA Qty"] = safe_numeric(df["FA Qty"], 1)

                        df["Asset Category"] = df["Asset Category"].astype(str).str.strip()
                        rules_clean = st.session_state.rules_data.copy()
                        rules_clean["Asset Category"] = rules_clean["Asset Category"].astype(str).str.strip()
                        
                        df["Date of Purchase"] = pd.to_datetime(df["Date of Purchase"], errors='coerce')
                        df["Put to use date"] = pd.to_datetime(df["Put to use date"], errors='coerce')
                        df["Date of Purchase"] = df["Date of Purchase"].fillna(df["Put to use date"])
                        df["Put to use date"] = df["Put to use date"].fillna(df["Date of Purchase"])

                        df = pd.merge(df, rules_clean, on="Asset Category", how="left")
                        df["Useful Life"] = safe_numeric(df["Useful Life"], 1)
                        
                        safe_qty = np.where(df["FA Qty"] == 0, 1, df["FA Qty"])
                        total_cost = df["Original Cost (Rs)"]
                        total_salvage = df["Salvage Value"]
                        max_acc_dep = np.maximum(total_cost - total_salvage, 0)
                        
                        safe_cost = np.where(total_cost == 0, 1, total_cost)
                        wdv_rate = 1 - (total_salvage / safe_cost) ** (1 / df["Useful Life"])
                        slm_rate = 1 / df["Useful Life"]
                        
                        df["Effective Rate"] = np.where(df["Depreciation Method"] == "WDV", wdv_rate, slm_rate)
                        df["Effective Rate"] = df["Effective Rate"].fillna(0)

                        if not st.session_state.wo_data.empty:
                            wo = st.session_state.wo_data.copy()
                            wo["Date of Write Off"] = pd.to_datetime(wo["Date of Write Off"], errors='coerce')
                            wo["FA Write off Qty"] = safe_numeric(wo["FA Write off Qty"], 0)

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

                        # --- THE FIX: Mathematical "Proportional" Depreciation Logic ---
                        days_opening = np.clip((fy_start_dt - df["Put to use date"]).dt.days, 0, 36500)
                        days_closing = np.clip((fy_end_dt - df["Put to use date"]).dt.days + 1, 0, 36500)
                        
                        latest_wo = pd.to_datetime(df["Latest Date of Write Off"], errors='coerce')
                        days_deletion = (latest_wo - df["Put to use date"]).dt.days + 1
                        days_deletion = np.clip(days_deletion.fillna(0), 0, 36500)
                        
                        # Calculate full theoretical depreciation first
                        def calc_full_acc_dep(days):
                            days_frac = days / 365.0
                            slm = max_acc_dep * df["Effective Rate"] * days_frac
                            wdv = total_cost * (1 - (1 - df["Effective Rate"]) ** days_frac)
                            calc = np.where(df["Depreciation Method"] == "SLM", slm, wdv)
                            return np.where(days > 0, np.clip(calc, 0, max_acc_dep), 0)

                        full_acc_dep_opening = calc_full_acc_dep(days_opening)
                        full_acc_dep_closing = calc_full_acc_dep(days_closing)
                        full_acc_dep_deletion = calc_full_acc_dep(days_deletion)

                        # Calculate Proportions based on QTY remaining
                        qty_op_deleted = df["FA Write off Qty Opening"]
                        qty_dur_deleted = df["FA Write off Qty During the year"]
                        
                        prop_opening_deleted = np.clip(qty_op_deleted / safe_qty, 0, 1)
                        prop_during_deleted = np.clip(qty_dur_deleted / safe_qty, 0, 1)
                        
                        prop_opening_active = np.clip(1 - prop_opening_deleted, 0, 1)
                        prop_closing_active = np.clip(1 - (prop_opening_deleted + prop_during_deleted), 0, 1)

                        # Scale Gross Block Perfectly
                        df["Gross Block Opening"] = np.where(df["Date of Purchase"] < fy_start_dt, total_cost * prop_opening_active, 0)
                        df["Gross Block Additions"] = np.where((df["Date of Purchase"] >= fy_start_dt) & (df["Date of Purchase"] <= fy_end_dt), total_cost, 0)
                        df["Gross Block Deletions"] = total_cost * prop_during_deleted
                        df["Gross Block Closing"] = df["Gross Block Opening"] + df["Gross Block Additions"] - df["Gross Block Deletions"]

                        # Scale Acc Dep Perfectly
                        df["Acc Dep Opening"] = full_acc_dep_opening * prop_opening_active
                        df["Acc Dep Closing"] = full_acc_dep_closing * prop_closing_active
                        
                        # Derive Expenses using algebraic plug formulas to guarantee balance
                        acc_dep_withdrawn = full_acc_dep_deletion * prop_during_deleted
                        total_dep_expense = df["Acc Dep Closing"] - df["Acc Dep Opening"] + acc_dep_withdrawn
                        opening_acc_dep_of_sold_items = full_acc_dep_opening * prop_during_deleted
                        
                        df["Depreciation on Deletions"] = np.maximum(acc_dep_withdrawn - opening_acc_dep_of_sold_items, 0)
                        df["Dep During Year"] = np.maximum(total_dep_expense - df["Depreciation on Deletions"], 0)

                        # Final Net Block Calculation
                        df["Net Block Opening"] = np.maximum(df["Gross Block Opening"] - df["Acc Dep Opening"], 0)
                        df["Net Block Closing"] = np.maximum(df["Gross Block Closing"] - df["Acc Dep Closing"], 0)

                        # Formatting Output
                        final_cols = [
                            "Control No.", "Date of Purchase", "Put to use date", "Asset Category", 
                            "Original Cost (Rs)", "Salvage Value", "Effective Rate",
                            "Gross Block Opening", "Gross Block Additions", "Gross Block Deletions", "Gross Block Closing",
                            "Acc Dep Opening", "Depreciation on Deletions", "Dep During Year", "Acc Dep Closing", 
                            "Net Block Opening", "Net Block Closing"
                        ]
                        
                        for c in final_cols:
                            if c not in df.columns:
                                df[c] = 0
                                
                        final_far = df[final_cols]

                        st.success("Calculations complete! Data sanitized and FAR generated successfully.")
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

if st.session_state.logged_in:
    main_app()
else:
    login_page()

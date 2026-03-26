import streamlit as st
import pandas as pd
import datetime
import numpy as np
import io

# --- Webpage Setup ---
st.set_page_config(page_title="Enterprise FAR Calculator", layout="wide")

st.title("🏢 Enterprise FAR Calculator")
st.markdown("Generates exact days-used depreciation matching professional Excel `VDB`/fractional-power logic.")

# --- 1. Reporting Period ---
st.subheader("Step 1: Financial Year Setup")
col_d1, col_d2 = st.columns(2)
with col_d1:
    fy_start = st.date_input("Financial Year Start:", datetime.date(2025, 4, 1))
with col_d2:
    fy_end = st.date_input("Financial Year End:", datetime.date(2026, 3, 31))

fy_start_dt = pd.to_datetime(fy_start)
fy_end_dt = pd.to_datetime(fy_end)

# --- 2. Asset Rules ---
st.subheader("Step 2: Master Dep Approach")
rule_columns = ["Asset Category", "Depreciation Method", "Useful Life"]
rule_df = pd.DataFrame(columns=rule_columns)
edited_rules = st.data_editor(rule_df, num_rows="dynamic", use_container_width=True, key="rules")

# --- 3. FA Additions ---
st.divider()
st.subheader("Step 3: Fixed Asset Additions")
add_columns = ["Control No.", "Asset Category", "Vendor Name", "Invoice No.", "Date of Purchase", "Put to use date", "FA Qty", "Original Cost (Rs)", "Salvage Value"]
add_df = pd.DataFrame(columns=add_columns)
edited_additions = st.data_editor(
    add_df, num_rows="dynamic", use_container_width=True, key="additions",
    column_config={"Date of Purchase": st.column_config.DateColumn(), "Put to use date": st.column_config.DateColumn()}
)

# --- 4. FA Write Offs ---
st.divider()
st.subheader("Step 4: Fixed Asset Write-Offs")
wo_columns = ["Control No.", "Date of Write Off", "FA Write off Qty", "FA Write off(Rs)", "Reason"]
wo_df = pd.DataFrame(columns=wo_columns)
edited_writeoffs = st.data_editor(
    wo_df, num_rows="dynamic", use_container_width=True, key="writeoffs",
    column_config={"Date of Write Off": st.column_config.DateColumn()}
)

# --- 5. CORE MATH ENGINE ---
st.divider()
if st.button("⚙️ Generate Enterprise FAR", type="primary"):
    with st.spinner("Processing advanced pro-rata math..."):
        try:
            if edited_rules.empty or edited_additions.empty:
                st.warning("⚠️ Please enter Rules and Additions data.")
            else:
                # 1. Clean & Prepare Data
                df = edited_additions.copy()
                df["Original Cost (Rs)"] = pd.to_numeric(df["Original Cost (Rs)"], errors='coerce').fillna(0)
                df["Salvage Value"] = pd.to_numeric(df["Salvage Value"], errors='coerce')
                
                # Auto-calculate 5% Salvage Value if left blank (matching your Excel =ROUND(Cost*5%))
                df["Salvage Value"] = np.where(df["Salvage Value"].isna(), np.round(df["Original Cost (Rs)"] * 0.05, 1), df["Salvage Value"])
                
                df["Date of Purchase"] = pd.to_datetime(df["Date of Purchase"])
                df["Put to use date"] = pd.to_datetime(df["Put to use date"])

                # 2. Merge Rules (XLOOKUP equivalent)
                df = pd.merge(df, edited_rules, on="Asset Category", how="left")
                df["Useful Life"] = pd.to_numeric(df["Useful Life"], errors='coerce').fillna(1)
                
                # 3. Calculate Effective Rate (Matching your WDV / SLM fractional math)
                # WDV: 1 - (Salvage/Cost)^(1/Life) | SLM: 1/Life
                wdv_rate = 1 - (df["Salvage Value"] / df["Original Cost (Rs)"]) ** (1 / df["Useful Life"])
                slm_rate = 1 / df["Useful Life"]
                df["Effective Rate"] = np.where(df["Depreciation Method"] == "WDV", wdv_rate, slm_rate)

                # 4. Handle Deletions/Write-offs
                if not edited_writeoffs.empty:
                    wo = edited_writeoffs.copy()
                    wo["Date of Write Off"] = pd.to_datetime(wo["Date of Write Off"])
                    wo["FA Write off(Rs)"] = pd.to_numeric(wo["FA Write off(Rs)"], errors='coerce').fillna(0)
                    df = pd.merge(df, wo[["Control No.", "Date of Write Off", "FA Write off(Rs)"]], on="Control No.", how="left")
                else:
                    df["Date of Write Off"] = pd.NaT
                    df["FA Write off(Rs)"] = 0

                # Determine the end date for calculation (Write-off date OR Financial Year End)
                df["Calc End Date"] = df["Date of Write Off"].fillna(fy_end_dt)
                df["Calc End Date"] = pd.to_datetime(df["Calc End Date"])

                # 5. Exact Days Used Logic (Matching your MIN/MAX formulas)
                # Opening Days:

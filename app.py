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
                
                # Auto-calculate 5% Salvage Value if left blank
                df["Salvage Value"] = np.where(df["Salvage Value"].isna(), np.round(df["Original Cost (Rs)"] * 0.05, 1), df["Salvage Value"])
                
                df["Date of Purchase"] = pd.to_datetime(df["Date of Purchase"])
                df["Put to use date"] = pd.to_datetime(df["Put to use date"])

                # 2. Merge Rules
                df = pd.merge(df, edited_rules, on="Asset Category", how="left")
                df["Useful Life"] = pd.to_numeric(df["Useful Life"], errors='coerce').fillna(1)
                
                # 3. Calculate Effective Rate
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

                df["Calc End Date"] = df["Date of Write Off"].fillna(fy_end_dt)
                df["Calc End Date"] = pd.to_datetime(df["Calc End Date"])

                # 5. Exact Days Used Logic
                df["Days Used Opening"] = np.clip((fy_start_dt - df["Put to use date"]).dt.days, 0, 365 * df["Useful Life"])
                df["Days Used Closing"] = np.clip((df["Calc End Date"] - df["Put to use date"]).dt.days + 1, 0, 365 * df["Useful Life"])

                # 6. Gross Block Logic
                df["Gross Block Opening"] = np.where(df["Date of Purchase"] < fy_start_dt, df["Original Cost (Rs)"], 0)
                df["Gross Block Additions"] = np.where((df["Date of Purchase"] >= fy_start_dt) & (df["Date of Purchase"] <= fy_end_dt), df["Original Cost (Rs)"], 0)
                df["Gross Block Deletions"] = df["FA Write off(Rs)"]
                df["Gross Block Closing"] = df["Gross Block Opening"] + df["Gross Block Additions"] - df["Gross Block Deletions"]

                # 7. Accumulated Depreciation Logic
                dep_base = df["Original Cost (Rs)"] - df["Salvage Value"]
                
                op_slm = dep_base * df["Effective Rate"] * (df["Days Used Opening"] / 365)
                op_wdv = dep_base * (1 - (1 - df["Effective Rate"]) ** (df["Days Used Opening"] / 365))
                df["Acc Dep Opening"] = np.where(df["Days Used Opening"] > 0, np.where(df["Depreciation Method"] == "SLM", op_slm, op_wdv), 0)

                cl_slm = dep_base * df["Effective Rate"] * (df["Days Used Closing"] / 365)
                cl_wdv = dep_base * (1 - (1 - df["Effective Rate"]) ** (df["Days Used Closing"] / 365))
                df["Acc Dep Closing"] = np.where(df["Days Used Closing"] > 0, np.where(df["Depreciation Method"] == "SLM", cl_slm, cl_wdv), 0)

                df["Dep During Year"] = df["Acc Dep Closing"] - df["Acc Dep Opening"]

                # 8. Net Block Logic
                df["Net Block Opening"] = df["Gross Block Opening"] - df["Acc Dep Opening"]
                df["Net Block Closing"] = df["Gross Block Closing"] - df["Acc Dep Closing"]

                # --- FORMATTING THE FINAL OUTPUT ---
                final_cols = [
                    "Control No.", "Date of Purchase", "Put to use date", "Asset Category", "Vendor Name", "Invoice No.", 
                    "FA Qty", "Original Cost (Rs)", "Salvage Value", "Depreciation Method", "Useful Life", "Effective Rate",
                    "Gross Block Opening", "Gross Block Additions", "Gross Block Deletions", "Gross Block Closing",
                    "Days Used Opening", "Days Used Closing", 
                    "Acc Dep Opening", "Dep During Year", "Acc Dep Closing", 
                    "Net Block Opening", "Net Block Closing"
                ]
                final_far = df[final_cols]

                # --- UI DISPLAY ---
                st.success("Calculations complete! Pro-rata math applied successfully.")
                st.dataframe(final_far.style.format({col: "{:,.2f}" for col in final_far.select_dtypes(include=['float64','int64']).columns}), use_container_width=True, hide_index=True)

                # --- EXCEL DOWNLOAD ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_far.to_excel(writer, index=False, sheet_name='Detailed FAR')
                
                st.download_button(
                    label="📥 Download Exact FAR (Excel)",
                    data=output.getvalue(),
                    file_name=f"FAR_Register_{fy_end_dt.strftime('%Y')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
        except Exception as e:
            st.error(f"Calculation Error: {e}")

import streamlit as st
import pandas as pd
import datetime
import numpy as np
import io

# --- Webpage Setup ---
st.set_page_config(page_title="Enterprise FAR Calculator", layout="wide")

st.title("🏢 Enterprise FAR Calculator")
st.markdown("Generates exact days-used depreciation with multiple partial write-offs support.")

# --- 1. Reporting Period ---
st.subheader("Step 1: Financial Year Setup")
col_d1, col_d2 = st.columns(2)
with col_d1:
    fy_start = st.date_input("Financial Year Start:", datetime.date(2022, 4, 1))
with col_d2:
    fy_end = st.date_input("Financial Year End:", datetime.date(2023, 3, 31))

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
wo_columns = ["Control No.", "Date of Write Off", "FA Write off Qty", "Reason"]
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
                df["Salvage Value"] = pd.to_numeric(df["Salvage Value"], errors='coerce').fillna(0)
                df["FA Qty"] = pd.to_numeric(df["FA Qty"], errors='coerce').fillna(1) # Default to 1 to prevent division by zero
                
                df["Max Acc Dep"] = np.maximum(df["Original Cost (Rs)"] - df["Salvage Value"], 0)
                df["Date of Purchase"] = pd.to_datetime(df["Date of Purchase"])
                df["Put to use date"] = pd.to_datetime(df["Put to use date"])

                # 2. Merge Rules
                df = pd.merge(df, edited_rules, on="Asset Category", how="left")
                df["Useful Life"] = pd.to_numeric(df["Useful Life"], errors='coerce').fillna(1)
                
                # 3. Calculate Effective Rate
                safe_cost = np.where(df["Original Cost (Rs)"] == 0, 1, df["Original Cost (Rs)"])
                wdv_rate = 1 - (df["Salvage Value"] / safe_cost) ** (1 / df["Useful Life"])
                slm_rate = 1 / df["Useful Life"]
                
                df["Effective Rate"] = np.where(df["Depreciation Method"] == "WDV", wdv_rate, slm_rate)
                df["Effective Rate"] = df["Effective Rate"].fillna(0)

                # ---------------------------------------------------------
                # 4. MULTIPLE WRITE-OFFS LOGIC (Replicating SUMIFS)
                # ---------------------------------------------------------
                if not edited_writeoffs.empty:
                    wo = edited_writeoffs.copy()
                    wo["Date of Write Off"] = pd.to_datetime(wo["Date of Write Off"])
                    wo["FA Write off Qty"] = pd.to_numeric(wo["FA Write off Qty"], errors='coerce').fillna(0)

                    # A. Filter and Sum for "Opening" (Before FY Start)
                    wo_opening = wo[wo["Date of Write Off"] < fy_start_dt]
                    op_agg = wo_opening.groupby("Control No.")["FA Write off Qty"].sum().reset_index(name="FA Write off Qty Opening")
                    
                    # B. Filter and Sum for "During the Year" (Within FY Dates)
                    wo_during = wo[(wo["Date of Write Off"] >= fy_start_dt) & (wo["Date of Write Off"] <= fy_end_dt)]
                    dur_agg = wo_during.groupby("Control No.")["FA Write off Qty"].sum().reset_index(name="FA Write off Qty During the year")

                    # Get the latest write off date for calculation cutoffs
                    latest_wo_date = wo.groupby("Control No.")["Date of Write Off"].max().reset_index(name="Latest Date of Write Off")

                    # Merge the aggregations back into the main DataFrame
                    df = pd.merge(df, op_agg, on="Control No.", how="left")
                    df = pd.merge(df, dur_agg, on="Control No.", how="left")
                    df = pd.merge(df, latest_wo_date, on="Control No.", how="left")
                else:
                    df["FA Write off Qty Opening"] = 0
                    df["FA Write off Qty During the year"] = 0
                    df["Latest Date of Write Off"] = pd.NaT

                # Fill any NaN values with 0
                df["FA Write off Qty Opening"] = df["FA Write off Qty Opening"].fillna(0)
                df["FA Write off Qty During the year"] = df["FA Write off Qty During the year"].fillna(0)

                # Prevent division by zero if FA Qty was left blank
                safe_qty = np.where(df["FA Qty"] == 0, 1, df["FA Qty"])

                # C. Calculate proportional Rupee (Rs) values
                df["FA Write off(Rs) Opening"] = (df["FA Write off Qty Opening"] / safe_qty) * df["Original Cost (Rs)"]
                df["FA Write off(Rs) During the year"] = (df["FA Write off Qty During the year"] / safe_qty) * df["Original Cost (Rs)"]

                # ---------------------------------------------------------
                # 5. Adjusted Gross Block Logic
                # ---------------------------------------------------------
                df["Calc End Date"] = df["Latest Date of Write Off"].fillna(fy_end_dt)
                df["Calc End Date"] = pd.to_datetime(df["Calc End Date"])

                df["Days Used Opening"] = np.clip((fy_start_dt - df["Put to use date"]).dt.days, 0, 36500)
                df["Days Used Closing"] = np.clip((df["Calc End Date"] - df["Put to use date"]).dt.days + 1, 0, 36500)

                # Gross Block Opening now deducts Opening Write Offs
                df["Gross Block Opening"] = np.where(
                    df["Date of Purchase"] < fy_start_dt, 
                    df["Original Cost (Rs)"] - df["FA Write off(Rs) Opening"], 
                    0
                )
                df["Gross Block Additions"] = np.where((df["Date of Purchase"] >= fy_start_dt) & (df["Date of Purchase"] <= fy_end_dt), df["Original Cost (Rs)"], 0)
                
                # Gross Block Deletions is explicitly the write offs strictly during the year
                df["Gross Block Deletions"] = df["FA Write off(Rs) During the year"]
                
                df["Gross Block Closing"] = df["Gross Block Opening"] + df["Gross Block Additions"] - df["Gross Block Deletions"]

                # 6. Accumulated Depreciation Logic
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

                # 7. Net Block Logic
                df["Net Block Opening"] = (df["Gross Block Opening"] - df["Acc Dep Opening"]).fillna(0)
                df["Net Block Closing"] = (df["Gross Block Closing"] - df["Acc Dep Closing"]).fillna(0)

                # --- FORMATTING THE FINAL OUTPUT ---
                final_cols = [
                    "Control No.", "Date of Purchase", "Put to use date", "Asset Category", "FA Qty", "Original Cost (Rs)", 
                    "FA Write off Qty Opening", "FA Write off(Rs) Opening", 
                    "FA Write off Qty During the year", "FA Write off(Rs) During the year",
                    "Gross Block Opening", "Gross Block Additions", "Gross Block Deletions", "Gross Block Closing",
                    "Acc Dep Opening", "Dep During Year", "Acc Dep Closing", 
                    "Net Block Opening", "Net Block Closing"
                ]
                final_far = df[final_cols]

                # --- UI DISPLAY ---
                st.success("Calculations complete! Pro-rata math applied successfully with multiple write-off support.")
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

import streamlit as st
import pandas as pd
import datetime
import io
import numpy as np

# --- Webpage Setup ---
st.set_page_config(page_title="Pro Depreciation Tool", layout="wide")

st.title("🚀 Pro Depreciation Calculator & FAR Generator")
st.markdown("Enter your asset details below. The system will calculate exact days used, generate a summary schedule, and build a detailed Fixed Asset Register (FAR).")

# --- 1. Reporting Date ---
st.subheader("Step 1: Reporting Period")
reporting_date = st.date_input("Select Reporting Date (Year End):", datetime.date(2026, 3, 31))
# Convert reporting_date to pandas datetime for math later
report_dt = pd.to_datetime(reporting_date)

# --- 2. Asset Categories & Rules ---
st.subheader("Step 2: Asset Category Rules")
rule_columns = ["Asset Category", "Depreciation Method", "Useful Life (Years)", "Depreciation Rate %"]
rule_df = pd.DataFrame(columns=rule_columns)
edited_rules = st.data_editor(rule_df, num_rows="dynamic", use_container_width=True, key="rules")

# --- 3. FA Additions Input ---
st.divider()
st.subheader("Step 3: Fixed Asset Additions")
add_columns = ["Asset ID", "Asset Category", "Date of Purchase", "Put to use date", "Purchase Value", "Vendor Name", "Invoice No.", "Invoice Qty", "Salvage Value"]
add_df = pd.DataFrame(columns=add_columns)

# We use column config to ensure dates are treated as dates in the grid
edited_additions = st.data_editor(
    add_df, 
    num_rows="dynamic", 
    use_container_width=True, 
    key="additions",
    column_config={
        "Date of Purchase": st.column_config.DateColumn("Date of Purchase"),
        "Put to use date": st.column_config.DateColumn("Put to use date")
    }
)

# --- 4. FA Write Offs Input ---
st.divider()
st.subheader("Step 4: Fixed Asset Write-Offs (Optional)")
wo_columns = ["Asset ID", "Date of Write Off", "Write Off Value", "Reason"]
wo_df = pd.DataFrame(columns=wo_columns)
edited_writeoffs = st.data_editor(
    wo_df, 
    num_rows="dynamic", 
    use_container_width=True, 
    key="writeoffs",
    column_config={
        "Date of Write Off": st.column_config.DateColumn("Date of Write Off")
    }
)

# --- 5. Generate FAR & Schedule ---
st.divider()
if st.button("🧾 Generate FAR & Schedule", type="primary"):
    with st.spinner("Calculating exact days and building reports..."):
        try:
            if edited_rules.empty or edited_additions.empty:
                st.warning("⚠️ Please enter at least one Asset Rule and one Addition to calculate.")
            else:
                # --- PREPARE DATA ---
                far_df = edited_additions.copy()
                far_df["Purchase Value"] = pd.to_numeric(far_df["Purchase Value"], errors='coerce').fillna(0)
                far_df["Salvage Value"] = pd.to_numeric(far_df["Salvage Value"], errors='coerce').fillna(0)
                far_df["Put to use date"] = pd.to_datetime(far_df["Put to use date"])
                
                # Merge Rules to get Rate and Method
                far_df = pd.merge(far_df, edited_rules, on="Asset Category", how="left")
                far_df["Depreciation Rate %"] = pd.to_numeric(far_df["Depreciation Rate %"], errors='coerce').fillna(0)
                
                # Merge Write-offs to see if any assets were deleted
                if not edited_writeoffs.empty:
                    wo_clean = edited_writeoffs.copy()
                    wo_clean["Date of Write Off"] = pd.to_datetime(wo_clean["Date of Write Off"])
                    wo_clean["Write Off Value"] = pd.to_numeric(wo_clean["Write Off Value"], errors='coerce').fillna(0)
                    far_df = pd.merge(far_df, wo_clean[["Asset ID", "Date of Write Off", "Write Off Value"]], on="Asset ID", how="left")
                else:
                    far_df["Date of Write Off"] = pd.NaT
                    far_df["Write Off Value"] = 0

                # --- PRO-RATA MATH (The core engine!) ---
                # Calculate the end date for depreciation (either reporting date OR write-off date)
                far_df["Depreciation End Date"] = far_df["Date of Write Off"].fillna(report_dt)
                far_df["Depreciation End Date"] = pd.to_datetime(far_df["Depreciation End Date"])
                
                # Calculate Exact Days Used
                far_df["Days Used"] = (far_df["Depreciation End Date"] - far_df["Put to use date"]).dt.days + 1
                far_df["Days Used"] = far_df["Days Used"].apply(lambda x: max(0, min(x, 365))) # Cap at 365 for a standard year
                
                # Calculate Depreciation Amount: (Purchase Value * Rate) * (Days Used / 365)
                far_df["Depreciation for the year"] = (far_df["Purchase Value"] * (far_df["Depreciation Rate %"] / 100)) * (far_df["Days Used"] / 365)
                
                # Calculate Net Block
                far_df["Closing Acc Dep"] = far_df["Depreciation for the year"] # Assuming new assets. For older assets, add Opening Acc Dep here.
                far_df["Net Block"] = far_df["Purchase Value"] - far_df["Write Off Value"] - far_df["Closing Acc Dep"]
                
                # Format the Final FAR DataFrame exactly like the screenshots
                final_far = far_df[[
                    "Asset ID", "Asset Category", "Vendor Name", "Invoice No.", "Invoice Qty", 
                    "Date of Purchase", "Put to use date", "Purchase Value", "Salvage Value", 
                    "Depreciation Method", "Useful Life (Years)", "Depreciation Rate %", 
                    "Date of Write Off", "Write Off Value", "Days Used", "Depreciation for the year", "Net Block"
                ]]
                
                # --- GENERATE SUMMARY SCHEDULE ---
                schedule = []
                for cat in far_df["Asset Category"].unique():
                    cat_data = far_df[far_df["Asset Category"] == cat]
                    
                    schedule.append({
                        "Block of Assets": cat,
                        "Gross Block - Opening": 0,
                        "Gross Block - Additions": cat_data["Purchase Value"].sum(),
                        "Gross Block - Deletions": cat_data["Write Off Value"].sum(),
                        "Gross Block - Closing": cat_data["Purchase Value"].sum() - cat_data["Write Off Value"].sum(),
                        "Acc Dep - Opening": 0,
                        "Acc Dep - For the year": cat_data["Depreciation for the year"].sum(),
                        "Acc Dep - Closing": cat_data["Depreciation for the year"].sum(),
                        f"Net Block As at {reporting_date.strftime('%d-%b-%Y')}": cat_data["Net Block"].sum()
                    })
                final_schedule = pd.DataFrame(schedule)

                # --- DISPLAY TABS ---
                tab1, tab2 = st.tabs(["📋 Detailed FAR (Register)", "📊 Summary Schedule"])
                
                with tab1:
                    st.dataframe(final_far.style.format(precision=2, thousands=","), use_container_width=True, hide_index=True)
                with tab2:
                    st.dataframe(final_schedule.style.format(precision=2, thousands=","), use_container_width=True, hide_index=True)

                # --- EXPORT TO EXCEL ---
                st.divider()
                st.markdown("### Export Reports")
                
                # Create a single Excel file with two sheets
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_far.to_excel(writer, index=False, sheet_name='Detailed FAR')
                    final_schedule.to_excel(writer, index=False, sheet_name='Summary Schedule')
                
                st.download_button(
                    label="📥 Download Complete Excel Report",
                    data=output.getvalue(),
                    file_name=f"Depreciation_Report_{reporting_date.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

        except Exception as e:
            st.error(f"Error calculating reports. Please check your date formats. Details: {e}")

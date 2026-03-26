import streamlit as st
import pandas as pd
import datetime

# --- Webpage Setup ---
st.set_page_config(page_title="Pro Depreciation Tool", layout="wide")

st.title("🚀 Pro Depreciation Calculator")
st.markdown("Enter your asset rules, additions, and write-offs directly below to generate your schedule.")

# --- 1. Reporting Date ---
st.subheader("Step 1: Reporting Period")
reporting_date = st.date_input("Select Reporting Date (Year End):", datetime.date.today())

# --- 2. Asset Categories & Rules ---
st.subheader("Step 2: Asset Category Rules")
st.markdown("Add your asset classes and how they should depreciate.")
# We create an empty table with your exact column names
rule_columns = ["Asset Category", "Depreciation Method", "Useful Life (Years)", "Depreciation Rate %"]
rule_df = pd.DataFrame(columns=rule_columns)

# num_rows="dynamic" lets the user add as many rows as they want!
edited_rules = st.data_editor(rule_df, num_rows="dynamic", use_container_width=True, key="rules")

# --- 3. FA Additions Input ---
st.divider()
st.subheader("Step 3: Fixed Asset Additions")
add_columns = ["Asset ID", "Asset Category", "Date of Purchase", "Put to use date", "Purchase Value", "Vendor Name", "Invoice No.", "Invoice Qty", "Salvage Value"]
add_df = pd.DataFrame(columns=add_columns)

edited_additions = st.data_editor(add_df, num_rows="dynamic", use_container_width=True, key="additions")

# --- 4. FA Write Offs Input ---
st.divider()
st.subheader("Step 4: Fixed Asset Write-Offs / Deletions")
wo_columns = ["Asset ID", "Date of Write Off", "Write Off Qty", "Reason"]
wo_df = pd.DataFrame(columns=wo_columns)

edited_writeoffs = st.data_editor(wo_df, num_rows="dynamic", use_container_width=True, key="writeoffs")

# --- 5. Generate Schedule Button ---
st.divider()
if st.button("🧾 Generate Depreciation Schedule", type="primary"):
    with st.spinner("Building your schedule..."):
        try:
            # First, we check if they actually entered data
            if edited_rules.empty or edited_additions.empty:
                st.warning("⚠️ Please enter at least one Asset Rule and one Addition to calculate.")
            else:
                # ---------------------------------------------------------
                # MATH & AGGREGATION ENGINE
                # ---------------------------------------------------------
                
                # Make sure numbers are treated as math numbers, not text
                edited_additions["Purchase Value"] = pd.to_numeric(edited_additions["Purchase Value"], errors='coerce').fillna(0)
                
                # Join the Rules to the Additions so the app knows the rate for each item
                merged_data = pd.merge(edited_additions, edited_rules, on="Asset Category", how="left")
                merged_data["Depreciation Rate %"] = pd.to_numeric(merged_data["Depreciation Rate %"], errors='coerce').fillna(0)
                
                # Calculate Basic Depreciation for the year (Purchase Value * Rate / 100)
                # *Note: For a full pro-rata calculation, you would use 'Put to use date' and 'reporting_date' to find exact days.*
                merged_data["Depreciation For Year"] = merged_data["Purchase Value"] * (merged_data["Depreciation Rate %"] / 100)
                
                # Group everything together by "Asset Category" to match your Annexure image format
                schedule = []
                categories = merged_data["Asset Category"].unique()
                
                for cat in categories:
                    cat_data = merged_data[merged_data["Asset Category"] == cat]
                    
                    # Calculate totals for this specific category block
                    additions_total = cat_data["Purchase Value"].sum()
                    dep_for_year_total = cat_data["Depreciation For Year"].sum()
                    
                    # Create the row matching your image's column headers
                    schedule_row = {
                        "Block of Assets": cat,
                        "Gross Block - Opening Balance": 0, # Assumed 0 for new additions
                        "Gross Block - Additions": additions_total,
                        "Gross Block - Deletions": 0, # You can link the write-off table math here later
                        "Gross Block - Closing Balance": additions_total, # Opening + Additions - Deletions
                        "Acc Dep - Opening Balance": 0,
                        "Acc Dep - For the year": dep_for_year_total,
                        "Acc Dep - Deletions": 0,
                        "Acc Dep - Closing Balance": dep_for_year_total,
                        f"Net Block As at {reporting_date.strftime('%d-%b-%Y')}": additions_total - dep_for_year_total
                    }
                    schedule.append(schedule_row)
                
                # Convert the list of rows into a final DataFrame table
                final_schedule_df = pd.DataFrame(schedule)
                
                # ---------------------------------------------------------
                # DISPLAY THE FINAL SCHEDULE
                # ---------------------------------------------------------
                st.success("Schedule Generated Successfully!")
                st.markdown("### Fixed Asset Schedule")
                
                # Display beautifully formatted table
                st.dataframe(
                    final_schedule_df.style.format(precision=2, thousands=","),
                    use_container_width=True,
                    hide_index=True
                )
                
        except Exception as e:
            st.error(f"Error calculating schedule: {e}")

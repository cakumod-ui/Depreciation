import streamlit as st
import pandas as pd
import io

# 1. Setup the Webpage
st.set_page_config(page_title="Depreciation Calculator", layout="wide")

st.title("📊 Depreciation Calculator Web Tool")
st.markdown("Download the templates, fill in your asset details, upload them below, and calculate!")

# --- 2. Function to create blank templates ---
def create_template(sheet_type):
    # We create a blank table with standard column names
    if sheet_type == "Addition":
        df = pd.DataFrame(columns=["Asset ID", "Asset Category", "Date of Purchase", "Purchase Value", "Depreciation Rate %"])
    else:
        df = pd.DataFrame(columns=["Asset ID", "Date of Write Off", "Write Off Value", "Reason"])
    
    # Save the blank table as an Excel file in the website's memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_type)
    return output.getvalue()

# --- 3. Download Buttons for Templates ---
st.subheader("Step 1: Download Templates")
col1, col2 = st.columns(2)

with col1:
    st.download_button(
        label="⬇️ Download 'FA Addition' Template",
        data=create_template("Addition"),
        file_name="FA_Addition_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    st.download_button(
        label="⬇️ Download 'FA Write Off' Template",
        data=create_template("Write Off"),
        file_name="FA_Write_Off_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- 4. File Uploaders ---
st.divider()
st.subheader("Step 2: Upload Your Filled Data")

col3, col4 = st.columns(2)
with col3:
    addition_file = st.file_uploader("Upload filled FA Addition File", type=["xlsx"])
with col4:
    write_off_file = st.file_uploader("Upload filled FA Write Off File (Optional)", type=["xlsx"])

# --- 5. Calculation Logic ---
st.divider()
st.subheader("Step 3: Calculate")
selected_method = st.selectbox("Select Calculation Method:", ["Straight Line Method (SLM)", "Written Down Value (WDV)"])

if st.button("Calculate Depreciation", type="primary"):
    
    # Check if the user actually uploaded the required Addition file
    if addition_file is not None:
        with st.spinner("Crunching the numbers..."):
            try:
                # Read the Excel files the user just uploaded
                df_add = pd.read_excel(addition_file)
                
                # If they also uploaded a write-off file, read it too
                if write_off_file is not None:
                    df_write_off = pd.read_excel(write_off_file)
                
                # --- CALCULATION MATH GOES HERE ---
                # Since we are no longer using Excel's formulas, we do the math in Python!
                # Here is a basic example calculating a simple percentage:
                
                # Ensure the columns are numeric before calculating
                df_add["Purchase Value"] = pd.to_numeric(df_add["Purchase Value"], errors='coerce').fillna(0)
                df_add["Depreciation Rate %"] = pd.to_numeric(df_add["Depreciation Rate %"], errors='coerce').fillna(0)
                
                # Calculate Depreciation (Purchase Value * Rate / 100)
                df_add["Calculated Depreciation"] = df_add["Purchase Value"] * (df_add["Depreciation Rate %"] / 100)
                
                # Calculate Net Block (Purchase Value - Depreciation)
                df_add["Net Block Value"] = df_add["Purchase Value"] - df_add["Calculated Depreciation"]
                
                st.success("Calculation Complete!")
                
                # Display the final formatted data table
                st.dataframe(
                    df_add.style.format({"Purchase Value": "{:,.2f}", "Calculated Depreciation": "{:,.2f}", "Net Block Value": "{:,.2f}"}), 
                    use_container_width=True, 
                    hide_index=True
                )
                
            except Exception as e:
                st.error(f"Oops! Something went wrong reading the file. Make sure you didn't change the column names in the template. Details: {e}")
    else:
        st.warning("⚠️ Please upload the FA Addition file first!")

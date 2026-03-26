import streamlit as st
import pandas as pd

# Configure the software UI
st.set_page_config(page_title="Depreciation Calculator 3.0", layout="wide")

# Custom CSS for a smoother UI
st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Depreciation Calculator Tool")
st.markdown("Select your parameters below to generate the Fixed Asset addition schedule.")

# File path to the backend Excel calculator (keep this in the same directory)
excel_file = "Depreciation Calculator tool 3.0 - WIOM (2).xlsm"

# Create layout columns
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Configuration")
    # Simulate reading the J1 dropdown options (you can hardcode or read dynamically)
    j1_options = ["Method A (SLM)", "Method B (WDV)", "Method C"] 
    selected_method = st.selectbox("Select FA Schedule Criteria (Cell J1 Input):", [""] + j1_options)
    
    calculate_btn = st.button("Calculate Depreciation")

with col2:
    st.subheader("FA Addition Output")
    
    if calculate_btn:
        if selected_method != "":
            with st.spinner("Calculating depreciation..."):
                try:
                    # In a fully integrated version, you would use xlwings here to 
                    # inject the selected_method into J1, trigger the Excel calculation, 
                    # and then read the results. 
                    
                    # Read the output columns P to AR from the FA addition sheet
                    df_output = pd.read_excel(excel_file, sheet_name="FA addition", usecols="P:AR", engine='openpyxl')
                    
                    st.success("Calculation Complete!")
                    st.dataframe(df_output, use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading backend data: {e}")
        else:
            st.warning("⚠️ Please select a valid criteria from the drop-down menu first.")
    else:
        st.info("Output will appear here after calculation.")
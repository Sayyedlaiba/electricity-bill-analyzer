import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import re

# =====================================================================
# 1. CORE FUNCTIONS (Must be defined first)
# =====================================================================
def extract_bill_details(uploaded_file):
    """Uses Gemini to extract details using native byte arrays for stability."""
    prompt = """
    Analyze this electricity bill image. Identify the billing month/period and the final total amount due.
    
    Respond ONLY with a valid JSON object matching this structure:
    {
        "billing_month": "Month Year",
        "amount_due": 1234.56
    }
    
    Rules:
    - If the month isn't explicitly clear, look for the 'Bill Date' or 'Due Date' and use that month.
    - The amount_due must be a raw number (no currency symbols, no commas).
    - Do not include markdown formatting like ```json.
    """
    try:
        # Read file as raw bytes natively for the API
        image_bytes = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": image_bytes
            }
        ]
        
        # Pass the formatted byte structure to the model
        response = model.generate_content([prompt, image_parts[0]])
        
        if not response or not response.text:
            return {"billing_month": None, "amount_due": None, "error": "Empty response from Gemini API"}
            
        raw_text = response.text.strip()
        
        # Clean any accidental markdown code blocks
        clean_text = re.sub(r"```json\s*|\s*```", "", raw_text)
        
        data = json.loads(clean_text)
        return data
        
    except Exception as e:
        # Detailed UI fallback error printed to the screen
        st.error(f"⚠️ API Error on file {uploaded_file.name}: {str(e)}")
        return {"billing_month": None, "amount_due": None, "error": str(e)}


# =====================================================================
# 2. PAGE INITIALIZATION & CONFIGURATION
# =====================================================================
st.set_page_config(page_title="Annual Electricity Bill Analyzer", page_icon="⚡", layout="wide")

st.title("⚡ Annual Electricity Bill Analyzer")
st.write("Upload your electricity bills for the past year to analyze your consumption trends, peaks, and lows.")

# Sidebar API Key Setup
api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if not api_key:
    st.info("Please enter your Gemini API Key in the sidebar or set it up in Streamlit Secrets to proceed.", icon="🔑")
    st.stop()

# Initialize Gemini Client
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')


# =====================================================================
# 3. USER INTERFACE: FILE UPLOADER
# =====================================================================
uploaded_files = st.file_uploader(
    "Upload Bill Images (JPEG/PNG) - You can select multiple files", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)


# =====================================================================
# 4. PROCESSING LOGIC
# =====================================================================
if uploaded_files:
    if st.button("Analyze Uploaded Bills", type="primary"):
        bill_data = []
        
        # Progress UI setup
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, file in enumerate(uploaded_files):
            status_text.text(f"Processing image {index + 1} of {len(uploaded_files)}: {file.name}...")
            
            # Send file structure directly to the core function
            extracted = extract_bill_details(file) 
            
            if extracted.get("billing_month") and extracted.get("amount_due"):
                bill_data.append({
                    "Filename": file.name,
                    "Billing Month": extracted["billing_month"],
                    "Amount Due": float(extracted["amount_due"])
                })
            else:
                st.warning(f"Could not reliably read data from {file.name}. Skipped.")
                
            progress_bar.progress((index + 1) / len(uploaded_files))
            
        status_text.empty()
        progress_bar.empty()
        
        if bill_data:
            df = pd.DataFrame(bill_data)
            # Save to session state so it doesn't disappear on user interactions
            st.session_state['bill_df'] = df
        else:
            st.error("No valid data could be extracted from the uploaded images.")


# =====================================================================
# 5. DATA VISUALIZATION AND INSIGHTS GENERATION
# =====================================================================
if 'bill_df' in st.session_state:
    df = st.session_state['bill_df']
    
    st.success("Analysis Complete!")
    
    # UI Layout: Chart on left, Raw data on right
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📊 Consumption Trend Over Time")
        fig = px.bar(df, x="Billing Month", y="Amount Due", text="Amount Due",
                     labels={"Amount Due": "Amount Due"},
                     color="Amount Due", color_continuous_scale="RdYlGn_r")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("📋 Extracted Data")
        st.dataframe(df[["Billing Month", "Amount Due"]], use_container_width=True, hide_index=True)

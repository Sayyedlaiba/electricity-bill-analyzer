import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from PIL import Image
import json
import re

# Page Configuration
st.set_page_config(page_title="Annual Electricity Bill Analyzer", page_icon="⚡", layout="wide")

st.title("⚡ Annual Electricity Bill Analyzer")
st.write("Upload your electricity bills for the past year to analyze your consumption trends, peaks, and lows.")

# 1. Setup API Key Securely
# In Streamlit Cloud, you set this up in Settings -> Secrets as GEMINI_API_KEY
api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if not api_key:
    st.info("Please enter your Gemini API Key in the sidebar or set it up in Streamlit Secrets to proceed.", icon="🔑")
    st.stop()

# Initialize Gemini Client
genai.configure(api_key=api_key)
# Using gemini-2.5-flash as it is fast, multimodal, and ideal for structured data extraction
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. File Uploader
uploaded_files = st.file_uploader(
    "Upload Bill Images (JPEG/PNG) - You can select multiple files", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

def extract_bill_details(image):
    """Uses Gemini to extract billing month and total amount from the image."""
    prompt = """
    Analyze this electricity bill image. Extract the billing month (or billing period) and the total amount due/payable.
    Respond ONLY with a valid JSON object matching this structure. Do not include markdown formatting like ```json.
    If you cannot confidently find a value, use null.
    
    {
        "billing_month": "Month Year (e.g., January 2026)",
        "amount_due": 1250.50
    }
    """
    try:
        response = model.generate_content([prompt, image])
        # Clean response string just in case it returns markdown blocks
        clean_text = re.sub(r"```json\s*|\s*```", "", response.text.strip())
        data = json.loads(clean_text)
        return data
    except Exception as e:
        return {"billing_month": None, "amount_due": None, "error": str(e)}

# 3. Processing the Bills
if uploaded_files:
    if st.button("Analyze Uploaded Bills", type="primary"):
        bill_data = []
        
        # Progress bar for visual feedback
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, file in enumerate(uploaded_files):
            status_text.text(f"Processing image {index + 1} of {len(uploaded_files)}: {file.name}...")
            
            image = Image.open(file)
            extracted = extract_bill_details(image)
            
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
            
            # Save to session state so it doesn't disappear on rerun
            st.session_state['bill_df'] = df
        else:
            st.error("No valid data could be extracted from the uploaded images.")

# 4. Data Visualization and Insights
if 'bill_df' in st.session_state:
    df = st.session_state['bill_df']
    
    st.success("Analysis Complete!")
    
    # Layout splits: Insights on left, Data table on right
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Consumption Trend Over Time")
        # Creating a bar chart for clear comparison
        fig = px.bar(df, x="Billing Month", y="Amount Due", text="Amount Due",
                     labels={"Amount Due": "Amount (₹/$)"},
                     color="Amount Due", color_continuous_scale="RdYlGn_r")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("📋 Extracted Data")
        st.dataframe(df[["Billing Month", "Amount Due"]], use_container_width=True, hide_index=True)

    # Key Performance Metrics / Anomalies
    st.markdown("---")
    st.subheader("💡 Key Insights")
    
    max_bill = df.loc[df['Amount Due'].idxmax()]
    min_bill = df.loc[df['Amount Due'].idxmin()]
    avg_bill = df['Amount Due'].mean()
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric(
            label="🔴 Highest Bill Month", 
            value=f"{max_bill['Billing Month']}", 
            delta=f"{max_bill['Amount Due']:.2f} (Peak)"
        )
        st.caption(f"Your highest expenditure happened in {max_bill['Billing Month']}.")
        
    with metric_col2:
        st.metric(
            label="🟢 Lowest Bill Month", 
            value=f"{min_bill['Billing Month']}", 
            delta=f"{min_bill['Amount Due']:.2f} (Dip)",
            delta_color="inverse"
        )
        st.caption(f"Your lowest expenditure happened in {min_bill['Billing Month']}.")

    with metric_col3:
        st.metric(
            label="🔵 Average Monthly Bill", 
            value=f"{avg_bill:.2f}"
        )
        st.caption("This is your baseline monthly power cost.")
        
    # Smart Explanations
    st.markdown("### 🔍 Summary Analysis")
    st.write(
        f"Your power bills peaked significantly during **{max_bill['Billing Month']}**, "
        f"costing you **{max_bill['Amount Due']:.2f}**, which is "
        f"**{(max_bill['Amount Due'] - avg_bill):.2f} higher** than your yearly average. "
        f"Conversely, you managed your consumption best during **{min_bill['Billing Month']}**."
    )

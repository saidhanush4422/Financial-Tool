import streamlit as st
import pdfplumber
import pandas as pd
import google.generativeai as genai
import json

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="FinSync", page_icon="💸", layout="centered")

# --- SIDEBAR: SECRETS & SETTINGS ---
with st.sidebar:
    st.header("⚙️ Setup")
    api_key = st.text_input("Enter Google Gemini API Key", type="password")
    st.markdown("[Get a Free Key Here](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.info("FinSync uses AI to categorize your statement without connecting to your bank.")

# --- MAIN INTERFACE ---
st.title("💸 FinSync")
st.caption("The AI-Powered CFO for Couples")

# --- STEP 1: UPLOAD ---
st.subheader("1. Upload Bank Statement")
uploaded_file = st.file_uploader("Upload PDF (Bank Statement)", type="pdf")

# --- LOGIC FUNCTIONS ---
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def analyze_with_ai(text_chunk, api_key):
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # The Prompt (The "Brain")
    prompt = f"""
    You are a financial analyst. Analyze the following bank statement text.
    Extract the top 10 largest transactions.
    For each transaction, determine if it is likely "Private" (individual) or "Shared" (couple) based on typical spending habits.
    
    Return ONLY a JSON list with this format:
    [
        {{"date": "YYYY-MM-DD", "description": "Transaction Name", "amount": 0.00, "category": "Food/Rent/Utility", "type": "Shared/Private"}}
    ]

    Bank Text Data:
    {text_chunk[:10000]} 
    """
    # Limit text to 10k chars for free tier safety
    
    try:
        response = model.generate_content(prompt)
        # Clean up code blocks if the AI adds them
        clean_json = response.text.replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        return []

# --- EXECUTION ---
if uploaded_file and api_key:
    with st.spinner("🤖 AI is reading your statement..."):
        # 1. Extract Text
        raw_text = extract_text_from_pdf(uploaded_file)
        
        # 2. AI Analysis
        data = analyze_with_ai(raw_text, api_key)
        
        if data:
            df = pd.DataFrame(data)
            
            # --- STEP 2: VERIFICATION ---
            st.subheader("2. Review Transactions")
            edited_df = st.data_editor(df, num_rows="dynamic")
            
            # Calculate Totals
            total_spend = edited_df['amount'].sum()
            shared_spend = edited_df[edited_df['type'] == 'Shared']['amount'].sum()
            
            # --- STEP 3: THE EQUITY SLIDER ---
            st.divider()
            st.subheader("3. Settle Up (The Equity Slider)")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Spending", f"${total_spend:.2f}")
            with col2:
                st.metric("Shared Spending", f"${shared_spend:.2f}")
            
            income_split = st.slider("Income Split (You / Partner)", 0, 100, 50)
            
            your_share = (income_split / 100) * shared_spend
            partner_share = shared_spend - your_share
            
            st.success(f"Based on a {income_split}/{100-income_split} split:")
            st.write(f"🧑‍🦰 **You Pay:** ${your_share:.2f}")
            st.write(f"👱‍♂️ **Partner Pays:** ${partner_share:.2f}")
            
            # --- STEP 4: WHATSAPP INTEGRATION ---
            whatsapp_msg = f"Hey! FinSync calculated our shared expenses. Total is ${shared_spend}. Based on our split, you owe ${partner_share:.2f}."
            whatsapp_url = f"https://wa.me/?text={whatsapp_msg.replace(' ', '%20')}"
            
            st.markdown(f"""
                <a href="{whatsapp_url}" target="_blank">
                    <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; font-weight:bold;">
                        Send via WhatsApp 💬
                    </button>
                </a>
            """, unsafe_allow_html=True)
            
        else:
            st.error("Could not extract data. Try a cleaner PDF or check API Key.")

elif uploaded_file and not api_key:
    st.warning("Please enter your API Key in the sidebar to process the file.")

import streamlit as st
import pdfplumber
import pandas as pd
import google.generativeai as genai
import json
import plotly.express as px

# --- 1. CONFIGURATION & CUSTOM CSS (The "Astonishing" Look) ---
st.set_page_config(page_title="FinSync Pro", page_icon="💳", layout="wide")

# Custom CSS for "Glassmorphism" and clean UI
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stApp {
        background: linear-gradient(to right, #ece9e6, #ffffff); 
    }
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    /* Custom Button */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        background-color: #4CAF50;
        color: white;
        border: none;
        height: 50px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    /* Headers */
    h1, h2, h3 {
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETTINGS & DEBUG ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2953/2953363.png", width=80)
    st.title("FinSync Settings")
    api_key = st.text_input("🔑 Google Gemini API Key", type="password", help="Get this from Google AI Studio")
    
    st.divider()
    
    st.caption("Debugging Tools")
    show_debug = st.toggle("Show Raw AI Response", value=False)
    
    st.info("💡 Tip: Use a PDF with clear text. Scanned images won't work without OCR.")

# --- LOGIC FUNCTIONS ---
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def analyze_with_ai(text_chunk, api_key):
    if not api_key:
        return None, "Missing API Key"
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Refined Prompt for JSON reliability
        prompt = f"""
        Act as a strict financial data parser. Analyze this bank statement text and extract the transactions.
        
        Rules:
        1. Ignore headers, footers, and legal text.
        2. Identify the transaction Date, Description, Amount, and Category.
        3. Guess if the type is "Shared" (Groceries, Rent, Utilities, Dining) or "Private" (Personal shopping, Subscriptions).
        4. Return ONLY valid JSON array. No Markdown. No ```json tags.
        
        JSON Format:
        [
            {{"date": "YYYY-MM-DD", "description": "Short Name", "amount": 10.50, "category": "Food", "type": "Shared"}}
        ]

        Data:
        {text_chunk[:10000]}
        """
        
        response = model.generate_content(prompt)
        raw_text = response.text
        
        # Cleaning the response just in case
        clean_json = raw_text.strip().replace("```json", "").replace("```", "")
        
        return json.loads(clean_json), raw_text
        
    except Exception as e:
        return None, str(e)

# --- MAIN DASHBOARD INTERFACE ---

# Hero Section
col1, col2 = st.columns([3, 1])
with col1:
    st.title("💸 FinSync Pro")
    st.markdown("### The AI-Powered CFO for Modern Couples")
with col2:
    st.empty() # Spacer

st.divider()

# 1. Upload Section
if not uploaded_file := st.file_uploader("📂 Drop your Bank Statement PDF here", type="pdf"):
    st.info("👆 Upload a file to get started.")

# 2. Processing
if uploaded_file and api_key:
    with st.spinner("🤖 analyzing finances..."):
        # Extract
        raw_text = extract_text_from_pdf(uploaded_file)
        
        if len(raw_text) < 50:
            st.error("⚠️ The PDF seems empty. Is it a scanned image? This tool requires text-based PDFs.")
        else:
            # AI Analyze
            data, debug_log = analyze_with_ai(raw_text, api_key)
            
            # --- DEBUGGER (Visible if Toggle is On or Error Occurs) ---
            if show_debug or data is None:
                with st.expander("🛠️ Debugger / Raw Error Log"):
                    st.text("Extracted Text Preview:")
                    st.text(raw_text[:500])
                    st.divider()
                    st.text("AI Response / Error:")
                    st.code(debug_log)

            if data:
                df = pd.DataFrame(data)
                
                # --- DASHBOARD VIEW ---
                
                # Metrics Row
                m1, m2, m3 = st.columns(3)
                total_spend = df['amount'].sum()
                shared_spend = df[df['type'] == 'Shared']['amount'].sum()
                private_spend = total_spend - shared_spend
                
                m1.metric("Total Spending", f"${total_spend:,.2f}")
                m2.metric("🏠 Shared Pot", f"${shared_spend:,.2f}", delta="To be split")
                m3.metric("👤 Personal", f"${private_spend:,.2f}")
                
                st.markdown("### 📊 Spending Breakdown")
                
                # Layout: Table on Left, Chart on Right
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.caption("Edit categories below if the AI guessed wrong.")
                    edited_df = st.data_editor(
                        df, 
                        column_config={
                            "amount": st.column_config.NumberColumn(format="$%.2f"),
                            "type": st.column_config.SelectboxColumn(options=["Shared", "Private"])
                        },
                        num_rows="dynamic",
                        use_container_width=True
                    )
                
                with c2:
                    # Pie Chart
                    fig = px.pie(edited_df, values='amount', names='category', title='Expenses by Category', hole=0.4)
                    fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=300)
                    st.plotly_chart(fig, use_container_width=True)

                # --- SETTLEMENT SECTION ---
                st.markdown("---")
                st.subheader("🤝 Settlement Center")
                
                with st.container():
                    col_slider, col_result = st.columns([2, 1])
                    
                    with col_slider:
                        st.markdown("**Income Equity Slider**")
                        split = st.slider("Your Contribution %", 0, 100, 50, help="Slide to adjust based on income disparity")
                        
                    with col_result:
                        # Recalculate based on edited DF
                        final_shared = edited_df[edited_df['type'] == 'Shared']['amount'].sum()
                        you_pay = (split / 100) * final_shared
                        partner_pay = final_shared - you_pay
                        
                        st.markdown(f"""
                        <div style="background-color:#d4edda; padding:15px; border-radius:10px; border:1px solid #c3e6cb; text-align:center;">
                            <h3 style="color:#155724; margin:0;">You Owe: ${you_pay:,.2f}</h3>
                            <p style="margin:0; color:#155724;">Partner Owes: ${partner_pay:,.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)

                # WhatsApp Button
                msg = f"Hey! FinSync Report: Total Shared is ${final_shared:.2f}. Based on a {split}/{100-split} split, please send ${partner_pay:.2f}."
                link = f"[https://wa.me/?text=](https://wa.me/?text=){msg.replace(' ', '%20')}"
                
                st.link_button("📲 Send Report via WhatsApp", link, type="primary")

            else:
                st.error("Could not extract transaction data. Check the Debugger in the sidebar for details.")

elif not api_key:
    st.warning("👈 Please enter your Google Gemini API Key in the sidebar to begin.")

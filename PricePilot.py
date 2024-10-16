import streamlit as st
import os
import pandas as pd
from PIL import Image
import pytesseract
from openai import OpenAI

# Set up OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable in Streamlit Cloud settings.")
else:
    client = OpenAI(api_key=api_key)

    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Load data tables (only accessible to the admin)
    if "article_table" not in st.session_state or "synonym_table" not in st.session_state or "customer_size_table" not in st.session_state or "customer_prices_table" not in st.session_state or "sharpness_matrix" not in st.session_state or "customer_sales_table" not in st.session_state or "offer_size_table" not in st.session_state:
        st.session_state.article_table = None
        st.session_state.synonym_table = None
        st.session_state.customer_size_table = None
        st.session_state.customer_prices_table = None
        st.session_state.sharpness_matrix = None
        st.session_state.customer_sales_table = None
        st.session_state.offer_size_table = None

    st.sidebar.title("Admin Settings")
    if st.sidebar.checkbox("Upload Data Tables (Admin Only)"):
        article_file = st.sidebar.file_uploader("Upload Article Table (CSV or Excel)", type=["csv", "xlsx"], key="article")
        synonym_file = st.sidebar.file_uploader("Upload Synonym Table (CSV or Excel)", type=["csv", "xlsx"], key="synonym")
        customer_size_file = st.sidebar.file_uploader("Upload Customer Size Table (CSV or Excel)", type=["csv", "xlsx"], key="customer_size")
        customer_prices_file = st.sidebar.file_uploader("Upload Customer Prices Table (CSV or Excel)", type=["csv", "xlsx"], key="customer_prices")
        sharpness_matrix_file = st.sidebar.file_uploader("Upload Sharpness Matrix (CSV or Excel)", type=["csv", "xlsx"], key="sharpness_matrix")
        customer_sales_file = st.sidebar.file_uploader("Upload Customer Sales Table (CSV or Excel)", type=["csv", "xlsx"], key="customer_sales")
        offer_size_file = st.sidebar.file_uploader("Upload Offer Size Table (CSV or Excel)", type=["csv", "xlsx"], key="offer_size")

        if article_file is not None:
            try:
                if article_file.name.endswith('.csv'):
                    st.session_state.article_table = pd.read_csv(article_file)
                elif article_file.name.endswith('.xlsx'):
                    st.session_state.article_table = pd.read_excel(article_file, engine='openpyxl')
                st.sidebar.success("Article Table uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Article Table: {e}")

        if synonym_file is not None:
            try:
                if synonym_file.name.endswith('.csv'):
                    st.session_state.synonym_table = pd.read_csv(synonym_file)
                elif synonym_file.name.endswith('.xlsx'):
                    st.session_state.synonym_table = pd.read_excel(synonym_file, engine='openpyxl')
                st.sidebar.success("Synonym Table uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Synonym Table: {e}")

        if customer_size_file is not None:
            try:
                if customer_size_file.name.endswith('.csv'):
                    st.session_state.customer_size_table = pd.read_csv(customer_size_file)
                elif customer_size_file.name.endswith('.xlsx'):
                    st.session_state.customer_size_table = pd.read_excel(customer_size_file, engine='openpyxl')
                st.sidebar.success("Customer Size Table uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Customer Size Table: {e}")

        if customer_prices_file is not None:
            try:
                if customer_prices_file.name.endswith('.csv'):
                    st.session_state.customer_prices_table = pd.read_csv(customer_prices_file)
                elif customer_prices_file.name.endswith('.xlsx'):
                    st.session_state.customer_prices_table = pd.read_excel(customer_prices_file, engine='openpyxl')
                st.sidebar.success("Customer Prices Table uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Customer Prices Table: {e}")

        if sharpness_matrix_file is not None:
            try:
                if sharpness_matrix_file.name.endswith('.csv'):
                    st.session_state.sharpness_matrix = pd.read_csv(sharpness_matrix_file)
                elif sharpness_matrix_file.name.endswith('.xlsx'):
                    st.session_state.sharpness_matrix = pd.read_excel(sharpness_matrix_file, engine='openpyxl')
                st.sidebar.success("Sharpness Matrix uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Sharpness Matrix: {e}")

        if customer_sales_file is not None:
            try:
                if customer_sales_file.name.endswith('.csv'):
                    st.session_state.customer_sales_table = pd.read_csv(customer_sales_file)
                elif customer_sales_file.name.endswith('.xlsx'):
                    st.session_state.customer_sales_table = pd.read_excel(customer_sales_file, engine='openpyxl')
                st.sidebar.success("Customer Sales Table uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Customer Sales Table: {e}")

        if offer_size_file is not None:
            try:
                if offer_size_file.name.endswith('.csv'):
                    st.session_state.offer_size_table = pd.read_csv(offer_size_file)
                elif offer_size_file.name.endswith('.xlsx'):
                    st.session_state.offer_size_table = pd.read_excel(offer_size_file, engine='openpyxl')
                st.sidebar.success("Offer Size Table uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load Offer Size Table: {e}")

    # Streamlit UI setup
    st.title("PricePilot - Customer Pricing Assistant")
    st.write("This is a tool for generating customer-specific pricing, based on provided inputs.")

    # User input area
    customer_input = st.text_area("Enter customer request here (email, text, etc.)")
    customer_file = st.file_uploader("Or upload a file (e.g., screenshot or document)", type=["png", "jpg", "jpeg", "pdf"])

    # Handle GPT Chat functionality
    if st.button("Start Chat with GPT"):
        try:
            if customer_input:
                st.session_state.chat_history.append({"role": "user", "content": customer_input})
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history,
                    max_tokens=150
                )
                assistant_message = response.choices[0].message.content.strip()
                st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
            elif customer_file:
                if customer_file.type.startswith("image"):
                    image = Image.open(customer_file)
                    st.image(image, caption='Uploaded image', use_column_width=True)
                    # Use pytesseract to extract text
                    extracted_text = pytesseract.image_to_string(image)
                    st.session_state.chat_history.append({"role": "user", "content": extracted_text})
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=st.session_state.chat_history,
                        max_tokens=150
                    )
                    assistant_message = response.choices[0].message.content.strip()
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                else:
                    st.error("File type not supported for processing.")
            else:
                st.warning("Please enter some text or upload a file.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

    # Display chat history as it evolves
    if st.session_state.chat_history:
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                st.write(f"You: {chat['content']}")
            else:
                st.write(f"GPT: {chat['content']}")

    # Parameters for pricing logic (optional)
    if st.checkbox("Show advanced pricing parameters"):
        discount_rate = st.slider("Discount Rate (%)", 0, 100, 10)
        quantity = st.number_input("Quantity", value=1)
        price_sensitivity = st.selectbox("Price Sensitivity Level", ["Low", "Medium", "High"])
        st.write("These parameters can be used to customize the pricing recommendation.")

import streamlit as st
import os
import pandas as pd
import openpyxl
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
    if "data_tables" not in st.session_state:
        st.session_state.data_tables = {
            "article_table": None,
            "synonym_table": None,
            "customer_size_table": None,
            "customer_prices_table": None,
            "sharpness_matrix": None,
            "customer_sales_table": None,
            "offer_size_table": None
        }

    # Load synonyms into a dictionary
    def load_synonyms():
        synonym_dict = {}
        if st.session_state.data_tables["synonym_table"] is not None:
            synonym_table = st.session_state.data_tables["synonym_table"]
            if "Synoniemenlijst" in synonym_table.columns and "Artikelnummer" in synonym_table.columns:
                for _, row in synonym_table.iterrows():
                    synonym_dict[row["Synoniemenlijst"]] = row["Artikelnummer"]
            else:
                st.error("Synonym table is missing required columns 'Synoniemenlijst' and 'Artikelnummer'.")
        return synonym_dict

    synonym_dict = load_synonyms()

    st.sidebar.title("Admin Settings")
    if st.sidebar.checkbox("Upload Data Tables (Admin Only)"):
        article_file = st.sidebar.file_uploader("Upload Article Table (CSV or Excel)", type=["csv", "xlsx"], key="article")
        synonym_file = st.sidebar.file_uploader("Upload Synonym Table (CSV or Excel)", type=["csv", "xlsx"], key="synonym")
        customer_size_file = st.sidebar.file_uploader("Upload Customer Size Table (CSV or Excel)", type=["csv", "xlsx"], key="customer_size")
        customer_prices_file = st.sidebar.file_uploader("Upload Customer Prices Table (CSV or Excel)", type=["csv", "xlsx"], key="customer_prices")
        sharpness_matrix_file = st.sidebar.file_uploader("Upload Sharpness Matrix (CSV or Excel)", type=["csv", "xlsx"], key="sharpness_matrix")
        customer_sales_file = st.sidebar.file_uploader("Upload Customer Sales Table (CSV or Excel)", type=["csv", "xlsx"], key="customer_sales")
        offer_size_file = st.sidebar.file_uploader("Upload Offer Size Table (CSV or Excel)", type=["csv", "xlsx"], key="offer_size")

        def load_table(file, table_name):
            try:
                if file.name.endswith('.csv'):
                    st.session_state.data_tables[table_name] = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    st.session_state.data_tables[table_name] = pd.read_excel(file, engine='openpyxl')
                st.sidebar.success(f"{table_name.replace('_', ' ').title()} uploaded successfully!")
            except Exception as e:
                st.sidebar.error(f"Failed to load {table_name.replace('_', ' ').title()}: {e}")

        if article_file is not None:
            load_table(article_file, "article_table")

        if synonym_file is not None:
            load_table(synonym_file, "synonym_table")

        if customer_size_file is not None:
            load_table(customer_size_file, "customer_size_table")

        if customer_prices_file is not None:
            load_table(customer_prices_file, "customer_prices_table")

        if sharpness_matrix_file is not None:
            load_table(sharpness_matrix_file, "sharpness_matrix")

        if customer_sales_file is not None:
            load_table(customer_sales_file, "customer_sales_table")

        if offer_size_file is not None:
            load_table(offer_size_file, "offer_size_table")

    # Streamlit UI setup
    st.title("PricePilot - Customer Pricing Assistant")
    st.write("This is a tool for generating customer-specific pricing, based on provided inputs.")

    # User input area
    customer_input = st.text_area("Enter customer request here (email, text, etc.)")
    customer_file = st.file_uploader("Or upload a file (e.g., screenshot or document)", type=["png", "jpg", "jpeg", "pdf"])

    # Function to replace synonyms in input text
    def replace_synonyms(input_text, synonyms):
        for term, synonym in synonyms.items():
            input_text = input_text.replace(term, synonym)
        return input_text

    # Function to find article details from the article table
    def find_article_details(article_number):
        if st.session_state.data_tables["article_table"] is not None:
            article_table = st.session_state.data_tables["article_table"]
            filtered_articles = article_table[article_table['Material'] == article_number]
            if not filtered_articles.empty:
                description = filtered_articles.iloc[0]['Description']
                return article_number, description
        return None, None

    # Handle GPT Chat functionality
    if st.button("Start Chat with GPT"):
        try:
            if customer_input:
                # Replace synonyms in customer input
                processed_input = replace_synonyms(customer_input, synonym_dict)
                st.session_state.chat_history.append({"role": "user", "content": processed_input})
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history,
                    max_tokens=150
                )
                assistant_message = response.choices[0].message.content.strip()

                # Check for synonyms and provide article details if applicable
                for term, article_number in synonym_dict.items():
                    if term in customer_input:
                        article_number, description = find_article_details(article_number)
                        if article_number and description:
                            assistant_message += f"\n\nBedoelt u artikelnummer {article_number}, {description}?"

                st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
            elif customer_file:
                if customer_file.type.startswith("image"):
                    image = Image.open(customer_file)
                    st.image(image, caption='Uploaded image', use_column_width=True)
                    # Use pytesseract to extract text
                    extracted_text = pytesseract.image_to_string(image)
                    # Replace synonyms in extracted text
                    processed_input = replace_synonyms(extracted_text, synonym_dict)
                    st.session_state.chat_history.append({"role": "user", "content": processed_input})
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=st.session_state.chat_history,
                        max_tokens=150
                    )
                    assistant_message = response.choices[0].message.content.strip()

                    # Check for synonyms and provide article details if applicable
                    for term, article_number in synonym_dict.items():
                        if term in extracted_text:
                            article_number, description = find_article_details(article_number)
                            if article_number and description:
                                assistant_message += f"\n\nBedoelt u artikelnummer {article_number}, {description}?"

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

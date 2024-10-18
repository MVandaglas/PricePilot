import streamlit as st
import os
import pandas as pd
import openpyxl
from PIL import Image
import pytesseract
from openai import OpenAI
from fuzzywuzzy import process

# Set up OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable in Streamlit Cloud settings.")
else:
    client = OpenAI(api_key=api_key)

    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Load synonyms into a dictionary (from Synonyms.py)
    from Synonyms import synonym_dict

    # Load article table from Articles.py
    from Articles import article_table

    # Convert article_table from dictionary to DataFrame
    article_table = pd.DataFrame.from_dict(article_table)

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
        filtered_articles = article_table[article_table['Material'] == int(article_number)]
        if not filtered_articles.empty:
            description = filtered_articles.iloc[0]['Description']
            return article_number, description
        return None, None

    # Function to perform fuzzy matching on customer input
    def fuzzy_match_synonyms(input_text, synonyms, threshold=80):
        matched_term, score = process.extractOne(input_text, synonyms.keys())
        if score >= threshold:
            return synonyms[matched_term]
        return None

    # Handle GPT Chat functionality
    if st.button("Start Chat with GPT"):
        try:
            if customer_input:
                # Perform fuzzy matching to find potential articles
                matched_article_number = fuzzy_match_synonyms(customer_input, synonym_dict)
                if matched_article_number:
                    article_number, description = find_article_details(matched_article_number)
                    if article_number and description:
                        st.write(f"Bedoelt u artikelnummer {article_number}, {description}?")
                        verification = st.radio("Klopt dit artikelnummer?", ("Ja", "Nee"))
                        if verification == "Nee":
                            st.write("Gelieve meer informatie te geven om het juiste artikelnummer te vinden.")
                        else:
                            st.session_state.chat_history.append({"role": "user", "content": customer_input})
                            response = client.chat_completions.create(
                                model="gpt-3.5-turbo",
                                messages=st.session_state.chat_history,
                                max_tokens=150
                            )
                            assistant_message = response.choices[0].message.content.strip()
                            st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                else:
                    st.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
            elif customer_file:
                if customer_file.type.startswith("image"):
                    image = Image.open(customer_file)
                    st.image(image, caption='Uploaded image', use_column_width=True)
                    # Use pytesseract to extract text
                    extracted_text = pytesseract.image_to_string(image)
                    # Perform fuzzy matching to find potential articles
                    matched_article_number = fuzzy_match_synonyms(extracted_text, synonym_dict)
                    if matched_article_number:
                        article_number, description = find_article_details(matched_article_number)
                        if article_number and description:
                            st.write(f"Bedoelt u artikelnummer {article_number}, {description}?")
                            verification = st.radio("Klopt dit artikelnummer?", ("Ja", "Nee"))
                            if verification == "Nee":
                                st.write("Gelieve meer informatie te geven om het juiste artikelnummer te vinden.")
                            else:
                                st.session_state.chat_history.append({"role": "user", "content": extracted_text})
                                response = client.chat_completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=st.session_state.chat_history,
                                    max_tokens=150
                                )
                                assistant_message = response.choices[0].message.content.strip()
                                st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                    else:
                        st.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
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

import streamlit as st
import os
import pandas as pd
from PIL import Image
import pytesseract
import openai

# OpenAI API-sleutel instellen
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API-sleutel ontbreekt. Stel de OPENAI_API_KEY omgevingsvariabele in de Streamlit Cloud-instellingen in.")
else:
    openai.api_key = api_key

customer_number = st.sidebar.text_input("Klantnummer (6 karakters)", max_chars=6)

if customer_number in customer_data:
    st.sidebar.write(f"Omzet klant: {customer_data[customer_number]['revenue']}")
    st.sidebar.write(f"Klantgrootte: {customer_data[customer_number]['size']}" )

customer_data = {
    "111111": {"revenue": "40.000 euro", "size": "D"},
    "222222": {"revenue": "140.000 euro", "size": "B"},
    "333333": {"revenue": "600.000 euro", "size": "A"}
}


# Functie om synoniemen te vervangen in invoertekst
def replace_synonyms(input_text, synonyms):
    for term, synonym in synonyms.items():
        input_text = input_text.replace(term, synonym)
    return input_text

# Functie om artikelgegevens te vinden
def find_article_details(article_number):
    filtered_articles = article_table[article_table['Material'] == int(article_number)]
    if not filtered_articles.empty:
        return filtered_articles.iloc[0]['Description']
    return None

# Functie om synoniemen te matchen in invoertekst
def match_synonyms(input_text, synonyms):
    for term in synonyms:
        if term in input_text:
            return synonyms.get(term)
    return None

# GPT Chat functionaliteit
def handle_gpt_chat():
    if customer_input:
        matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in customer_input]

        if matched_articles:
            response_text = "Bedoelt u de volgende samenstellingen:"
            data = []
            for term, article_number in matched_articles:
                description = find_article_details(article_number)
                if description:
                    quantity, width, height = extract_dimensions(customer_input, term)
                    if quantity.endswith('x'):
                        quantity = quantity[:-1].strip()
                    data.append([description, article_number, width, height, quantity])

            new_df = pd.DataFrame(data, columns=["Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal"])
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)


import streamlit as st
import os
import pandas as pd
from PIL import Image
import pytesseract
import openai
import re

# OpenAI API-sleutel instellen
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API-sleutel ontbreekt. Stel de OPENAI_API_KEY omgevingsvariabele in de Streamlit Cloud-instellingen in.")
else:
    openai.api_key = api_key

# Hard gecodeerde klantgegevens
customer_data = {
    "111111": {"revenue": "40.000 euro", "size": "D"},
    "222222": {"revenue": "140.000 euro", "size": "B"},
    "333333": {"revenue": "600.000 euro", "size": "A"}
}

# Initialiseer offerte DataFrame en klantnummer in sessiestatus
if "offer_df" not in st.session_state:
    st.session_state.offer_df = pd.DataFrame(columns=["Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal"])
if "customer_number" not in st.session_state:
    st.session_state.customer_number = ""

# Laad synoniemen en artikelentabel
from Synonyms import synonym_dict
from Articles import article_table

# Converteer article_table naar DataFrame
article_table = pd.DataFrame(article_table)

# Streamlit UI-instellingen
st.sidebar.title("PricePilot - Klantprijsassistent")
st.sidebar.write("Dit is een tool voor het genereren van klant specifieke prijzen op basis van ingevoerde gegevens.")

# Gebruikersinvoer
customer_input = st.sidebar.text_area("Voer hier het klantverzoek in (e-mail, tekst, etc.)")
customer_file = st.sidebar.file_uploader("Of upload een bestand (bijv. screenshot of document)", type=["png", "jpg", "jpeg", "pdf"])
customer_number = st.sidebar.text_input("Klantnummer (6 karakters)", max_chars=6)
offer_amount = st.sidebar.number_input("Offertebedrag in euro", min_value=0, step=1000)

if customer_number in customer_data:
    st.sidebar.write(f"Omzet klant: {customer_data[customer_number]['revenue']}")
    st.sidebar.write(f"Klantgrootte: {customer_data[customer_number]['size']}")

    # Bepaal prijsscherpte op basis van klantgrootte en offertebedrag
    klantgrootte = customer_data[customer_number]['size']
    prijsscherpte = ""
    if klantgrootte == "A":
        if offer_amount > 50000:
            prijsscherpte = 90
        elif offer_amount > 25000:
            prijsscherpte = 80
        elif offer_amount > 10000:
            prijsscherpte = 70
        elif offer_amount > 5000:
            prijsscherpte = 60
        else:
            prijsscherpte = 50
    st.sidebar.write(f"Prijsscherpte: {prijsscherpte}")

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
        else:
            st.sidebar.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
    elif customer_file:
        handle_file_upload(customer_file)
    else:
        st.sidebar.warning("Voer alstublieft tekst in of upload een bestand.")

# Functie om bestand te verwerken
def handle_file_upload(file):
    if file.type.startswith("image"):
        image = Image.open(file)
        st.sidebar.image(image, caption='Geüploade afbeelding', use_column_width=True)
        extracted_text = pytesseract.image_to_string(image)
        handle_text_input(extracted_text)
    else:
        st.sidebar.error("Bestandstype wordt niet ondersteund voor verwerking.")

# Functie om afmetingen uit tekst te halen
def extract_dimensions(text, term):
    quantity, width, height = "", "", ""
    # Zoek naar het aantal
    quantity_match = re.search(r'(\d+)\s*(stuks|ruiten|aantal)', text, re.IGNORECASE)
    if quantity_match:
        quantity = quantity_match.group(1)
    # Zoek naar de afmetingen ná het artikelnummer
    term_index = text.find(term)
    if term_index != -1:
        text_after_term = text[term_index + len(term):]
        dimension_match = re.search(r'(\d+)\s*(bij|x|b|B|breedte)\s*(\d+)', text_after_term, re.IGNORECASE)
        if dimension_match:
            width = dimension_match.group(1)
            height = dimension_match.group(3)
        else:
            dimension_match_alt = re.search(r'(h|H|hoogte)\s*:?\s*(\d+)\s*(b|B|breedte)\s*:?\s*(\d+)', text_after_term, re.IGNORECASE)
            if dimension_match_alt:
                height = dimension_match_alt.group(2)
                width = dimension_match_alt.group(4)
    return quantity, width, height

# Functie om tekstinvoer te verwerken
def handle_text_input(input_text):
    matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in input_text]

    if matched_articles:
        response_text = "Bedoelt u de volgende samenstellingen:"
        for term, article_number in matched_articles:
            description = find_article_details(article_number)
            if description:
                response_text += f"- {description} met artikelnummer {article_number}\n"

        response_text += "?"
        st.sidebar.write(response_text)
    else:
        st.sidebar.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")

# Verwerk chat met GPT
if st.sidebar.button("Verstuur chat met GPT"):
    try:
        handle_gpt_chat()
    except Exception as e:
        st.sidebar.error(f"Er is een fout opgetreden: {e}")

# Toon bewaarde offerte DataFrame in het middenscherm en maak het aanpasbaar
if st.session_state.offer_df is not None:
    st.title("Offerteoverzicht")
    st.session_state.offer_df = st.data_editor(st.session_state.offer_df, num_rows="dynamic")
    if st.button("Sla artikelen op in geheugen"):
        st.session_state.saved_offer_df = st.session_state.offer_df.copy()
        st.success("Artikelen succesvol opgeslagen in het geheugen.")

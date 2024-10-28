import streamlit as st
from streamlit_option_menu import option_menu
import os
import pandas as pd
from PIL import Image
import pytesseract
import openai
import re
from datetime import datetime

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
    st.session_state.offer_df = pd.DataFrame(columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"])
if "customer_number" not in st.session_state:
    st.session_state.customer_number = ""
if "loaded_offer_df" not in st.session_state:
    st.session_state.loaded_offer_df = pd.DataFrame(columns=["Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"])
if "saved_offers" not in st.session_state:
    st.session_state.saved_offers = pd.DataFrame(columns=["Offertenummer", "Klantnummer", "Eindbedrag", "Datum"])

# Laad synoniemen en artikelentabel
from Synonyms import synonym_dict
from Articles import article_table

# Converteer article_table naar DataFrame
article_table = pd.DataFrame(article_table)

# Streamlit UI-instellingen
# Meerdere tabbladen maken in Streamlit
selected_tab = option_menu(
    menu_title=None,  # required
    options=["Offerte Genereren", "Opgeslagen Offertes"],  # required
    icons=["file-earmark-plus", "folder"],  # optional
    menu_icon="cast",  # optional
    default_index=0,
    orientation="horizontal",
)
st.sidebar.title("PricePilot - Klantprijsassistent")
st.sidebar.write("Dit is een tool voor het genereren van klant specifieke prijzen op basis van ingevoerde gegevens.")

# Gebruikersinvoer
customer_input = st.sidebar.text_area("Voer hier het klantverzoek in (e-mail, tekst, etc.)")
customer_file = st.sidebar.file_uploader("Of upload een bestand (bijv. screenshot of document)", type=["png", "jpg", "jpeg", "pdf"])
customer_number = st.sidebar.text_input("Klantnummer (6 karakters)", max_chars=6)
st.session_state.customer_number = str(customer_number) if customer_number else ''
offer_amount = st.sidebar.number_input("Offertebedrag in euro", min_value=0, step=1000)

if customer_number in customer_data:
    st.sidebar.write(f"Omzet klant: {customer_data[customer_number]['revenue']}")
    st.sidebar.write(f"Klantgrootte: {customer_data[customer_number]['size']}")

    # Bepaal prijsscherpte op basis van klantgrootte en offertebedrag
    klantgrootte = customer_data[customer_number]['size']
    prijsscherpte = ""
    if klantgrootte == "A":
        if offer_amount > 50000:
            prijsscherpte = 100
        elif offer_amount > 25000:
            prijsscherpte = 90
        elif offer_amount > 10000:
            prijsscherpte = 80
        elif offer_amount > 5000:
            prijsscherpte = 70
        else:
            prijsscherpte = 60
    elif klantgrootte == "B":
        if offer_amount > 50000:
            prijsscherpte = 80
        elif offer_amount > 25000:
            prijsscherpte = 70
        elif offer_amount > 10000:
            prijsscherpte = 60
        elif offer_amount > 5000:
            prijsscherpte = 50
        else:
            prijsscherpte = 40
    elif klantgrootte == "C":
        if offer_amount > 50000:
            prijsscherpte = 75
        elif offer_amount > 25000:
            prijsscherpte = 65
        elif offer_amount > 10000:
            prijsscherpte = 50
        elif offer_amount > 5000:
            prijsscherpte = 40
        else:
            prijsscherpte = 30
    elif klantgrootte == "D":
        if offer_amount > 50000:
            prijsscherpte = 70
        elif offer_amount > 25000:
            prijsscherpte = 60
        elif offer_amount > 10000:
            prijsscherpte = 45
        elif offer_amount > 5000:
            prijsscherpte = 25
        else:
            prijsscherpte = 10
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
        return filtered_articles.iloc[0]['Description'], filtered_articles.iloc[0]['Min_prijs'], filtered_articles.iloc[0]['Max_prijs']
    return None, None, None

# Functie om synoniemen te matchen in invoertekst
def match_synonyms(input_text, synonyms):
    for term in synonyms:
        if term in input_text:
            return synonyms.get(term)
    return None

# Functie om aanbevolen prijs te berekenen
def calculate_recommended_price(min_price, max_price, prijsscherpte):
    if min_price is not None and max_price is not None and prijsscherpte != "":
        return min_price + ((max_price - min_price) * (100 - prijsscherpte) / 100)
    return None

# Functie om m2 per stuk te berekenen
def calculate_m2_per_piece(width, height):
    if width and height:
        width_m = int(width) / 1000
        height_m = int(height) / 1000
        m2 = max(width_m * height_m, 0.65)
        return m2
    return None

# GPT Chat functionaliteit
def handle_gpt_chat():
    if customer_input:
        matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in customer_input]

        if matched_articles:
            data = []
            for term, article_number in matched_articles:
                description, min_price, max_price = find_article_details(article_number)
                if description:
                    quantity, width, height = extract_dimensions(customer

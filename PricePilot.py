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
    st.session_state.offer_df = pd.DataFrame(columns=["Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP"])
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
                    quantity, width, height = extract_dimensions(customer_input, term)
                    if quantity.endswith('x'):
                        quantity = quantity[:-1].strip()
                    recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                    m2_per_piece = calculate_m2_per_piece(width, height)
                    m2_total = float(quantity) * m2_per_piece if m2_per_piece and quantity else None
                    m2_per_piece = calculate_m2_per_piece(width, height)
m2_total = float(quantity) * m2_per_piece if m2_per_piece and quantity else None
data.append([description, article_number, width, height, quantity, f"€ {recommended_price:.2f}" if recommended_price is not None else None, f"{m2_per_piece:.2f} m²" if m2_per_piece is not None else None, f"{m2_total:.2f} m²" if m2_total is not None else None])

            new_df = pd.DataFrame(data, columns=["Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"])
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
    st.markdown("<style>.main .block-container { width: 300%; }</style>", unsafe_allow_html=True)
    edited_df = st.data_editor(st.session_state.offer_df, num_rows="dynamic")

    # Herbereken M2 p/s en M2 totaal bij wijzigingen
    if not edited_df.equals(st.session_state.offer_df):
        edited_df["M2 p/s"] = edited_df.apply(lambda row: calculate_m2_per_piece(row["Breedte"], row["Hoogte"]) if pd.notna(row["Breedte"]) and pd.notna(row["Hoogte"]) else None, axis=1)
        edited_df["M2 totaal"] = edited_df.apply(lambda row: float(row["Aantal"]) * row["M2 p/s"] if pd.notna(row["Aantal"]) and pd.notna(row["M2 p/s"]) else None, axis=1)
        st.session_state.offer_df = edited_df
    if st.button("Sla artikelen op in geheugen"):
        st.session_state.saved_offer_df = st.session_state.offer_df.copy()
        st.success("Artikelen succesvol opgeslagen in het geheugen.")

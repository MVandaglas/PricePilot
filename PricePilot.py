import streamlit as st
import os
import pandas as pd
import openpyxl
from PIL import Image
import pytesseract
import openai

# Stel de OpenAI API-sleutel in
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API-sleutel ontbreekt. Stel de OPENAI_API_KEY omgevingsvariabele in de Streamlit Cloud-instellingen in.")
else:
    openai.api_key = api_key

# Initialiseer chatgeschiedenis in sessiestatus
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Laad synoniemen in een woordenboek (van Synonyms.py)
from Synonyms import synonym_dict

# Laad artikelentabel van Articles.py
from Articles import article_table

# Converteer article_table van lijst van woordenboeken naar DataFrame
article_table = pd.DataFrame(article_table)

# Streamlit UI-instelling
st.title("PricePilot - Klantprijsassistent")
st.write("Dit is een tool voor het genereren van klant specifieke prijzen op basis van ingevoerde gegevens.")

# Gebruikersinvoerveld
customer_input = st.text_area("Voer hier het klantverzoek in (e-mail, tekst, etc.)")
customer_file = st.file_uploader("Of upload een bestand (bijv. screenshot of document)", type=["png", "jpg", "jpeg", "pdf"])

# Functie om synoniemen te vervangen in invoertekst
def replace_synonyms(input_text, synonyms):
    for term, synonym in synonyms.items():
        input_text = input_text.replace(term, synonym)
    return input_text

# Functie om artikelgegevens te vinden uit de artikelentabel
def find_article_details(article_number):
    filtered_articles = article_table[article_table['Material'] == int(article_number)]
    if not filtered_articles.empty:
        description = filtered_articles.iloc[0]['Description']
        return article_number, description
    return None, None

# Functie om exacte matching uit te voeren op klantinvoer
def match_synonyms(input_text, synonyms):
    for term in synonyms:
        if term in input_text:
            return synonyms.get(term)
    return None

# GPT Chat functionaliteit afhandelen
if st.button("Verstuur chat met GPT"):
    try:
        if customer_input:
            # Voer exacte matching uit om mogelijke artikelen te vinden
            matched_articles = []
            for term in synonym_dict:
                if term in customer_input:
                    matched_articles.append((term, synonym_dict[term]))

            if matched_articles:
                response_text = "Bedoelt u de volgende samenstellingen:\n"
                response_text += "| Artikelnaam | Artikelnummer | Breedte | Hoogte | Aantal |\n"
                response_text += "| --- | --- | --- | --- | --- |\n"
                for term, article_number in matched_articles:
                    _, description = find_article_details(article_number)
                    if description:
                        # Extract quantity, width, and height from customer input
                        quantity = ""
                        width = ""
                        height = ""
                        if f"{term}" in customer_input:
                            parts = customer_input.split(term)
                            if len(parts) > 0:
                                quantity_part = parts[0].strip().split()[-1]
                                if quantity_part.isdigit():
                                    quantity = quantity_part
                            if len(parts) > 1:
                                size_part = parts[1].strip().split()[0]
                                if "x" in size_part:
                                    width, height = size_part.split("x")
                                    width = width.strip()
                                    height = height.strip()
                        response_text += f"| {description} | {article_number} | {width} | {height} | {quantity} |\n"

                response_text += "?"
                st.session_state.chat_history.append({"role": "user", "content": customer_input})
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

                # Verificatie stap
                verification = st.radio("Klopt dit artikelnummer?", ("Ja", "Nee"), index=-1)
                if verification == "Ja":
                    st.write("Bedankt voor uw bevestiging. We gaan verder met het opstellen van de offerte.")
                elif verification == "Nee":
                    st.write("Gelieve meer informatie te geven om het juiste artikelnummer te vinden.")
            else:
                st.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
        elif customer_file:
            if customer_file.type.startswith("image"):
                image = Image.open(customer_file)
                st.image(image, caption='Geüploade afbeelding', use_column_width=True)
                # Gebruik pytesseract om tekst te extraheren
                extracted_text = pytesseract.image_to_string(image)
                # Voer exacte matching uit om mogelijke artikelen te vinden
                matched_articles = []
                for term in synonym_dict:
                    if term in extracted_text:
                        matched_articles.append((term, synonym_dict[term]))

                if matched_articles:
                    response_text = "Bedoelt u de volgende samenstellingen:\n"
                    response_text += "| Artikelnaam | Artikelnummer | Breedte | Hoogte | Aantal |\n"
                    response_text += "| --- | --- | --- | --- | --- |\n"
                    for term, article_number in matched_articles:
                        _, description = find_article_details(article_number)
                        if description:
                            response_text += f"| {description} | {article_number} | | | |\n"

                    response_text += "?"
                    st.session_state.chat_history.append({"role": "user", "content": extracted_text})
                    st.write(response_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})

                    # Verificatie stap
                    verification = st.radio("Klopt dit artikelnummer?", ("Ja", "Nee"), index=-1)
                    if verification == "Ja":
                        st.write("Bedankt voor uw bevestiging. We gaan verder met het opstellen van de offerte.")
                    elif verification == "Nee":
                        st.write("Gelieve meer informatie te geven om het juiste artikelnummer te vinden.")
                else:
                    st.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
            else:
                st.error("Bestandstype wordt niet ondersteund voor verwerking.")
        else:
            st.warning("Voer alstublieft tekst in of upload een bestand.")
    except Exception as e:
        st.error(f"Er is een fout opgetreden: {e}")

# Toon chatgeschiedenis zoals deze zich ontwikkelt
if st.session_state.chat_history:
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.write(f"U: {chat['content']}")
        else:
            st.write(f"GPT: {chat['content']}")

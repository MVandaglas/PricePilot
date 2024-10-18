import streamlit as st
import os
import pandas as pd
import openpyxl
from PIL import Image
import pytesseract
import openai
from fuzzywuzzy import process

# Stel de OpenAI API-sleutel in
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API-sleutel ontbreekt. Stel de OPENAI_API_KEY omgevingsvariabele in de Streamlit Cloud-instellingen in.")

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

# Functie om fuzzy matching uit te voeren op klantinvoer
def fuzzy_match_synonyms(input_text, synonyms, threshold=80):
    matched_term, score = process.extractOne(input_text, synonyms.keys())
    if score >= threshold:
        return synonyms[matched_term]
    return None

# GPT Chat functionaliteit afhandelen
if st.button("Start chat met GPT"):
    try:
        if customer_input:
            # Voer fuzzy matching uit om mogelijke artikelen te vinden
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
                        response = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=st.session_state.chat_history,
                            max_tokens=150
                        )
                        assistant_message = response['choices'][0]['message']['content'].strip()
                        st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                        st.write(f"GPT: {assistant_message}")
            else:
                st.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
        elif customer_file:
            if customer_file.type.startswith("image"):
                image = Image.open(customer_file)
                st.image(image, caption='Geüploade afbeelding', use_column_width=True)
                # Gebruik pytesseract om tekst te extraheren
                extracted_text = pytesseract.image_to_string(image)
                # Voer fuzzy matching uit om mogelijke artikelen te vinden
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
                            response = openai.ChatCompletion.create(
                                model="gpt-3.5-turbo",
                                messages=st.session_state.chat_history,
                                max_tokens=150
                            )
                            assistant_message = response['choices'][0]['message']['content'].strip()
                            st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
                            st.write(f"GPT: {assistant_message}")
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

# Parameters voor prijslogica (optioneel)
if st.checkbox("Toon geavanceerde prijsparameters"):
    discount_rate = st.slider("Kortingstarief (%)", 0, 100, 10)
    quantity = st.number_input("Hoeveelheid", value=1)
    price_sensitivity = st.selectbox("Prijselasticiteitniveau", ["Laag", "Gemiddeld", "Hoog"])
    st.write("Deze parameters kunnen worden gebruikt om de prijsaanbeveling aan te passen.")

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
    st.session_state.offer_df = pd.DataFrame(columns=["Offertenummer", "Klantnummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Datum"])
if "customer_number" not in st.session_state:
    st.session_state.customer_number = ""

# Laad synoniemen en artikelentabel
from Synonyms import synonym_dict
from Articles import article_table

# Laad opgeslagen offertes CSV
csv_path = r'saved_offers.csv'
if os.path.exists(csv_path):
    try:
        saved_offers_df = pd.read_csv(csv_path)
        st.session_state.saved_offers = saved_offers_df
    except Exception as e:
        st.warning(f"Kon CSV niet laden: {e}")
else:
    st.session_state.saved_offers = pd.DataFrame(columns=["Offertenummer", "Klantnummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Datum"])

# Converteer article_table naar DataFrame
article_table = pd.DataFrame(article_table)

# Streamlit UI-instellingen
# Meerdere tabbladen maken in Streamlit
selected_tab = option_menu(
    menu_title=None,
    options=["Offerte Genereren", "Opgeslagen Offertes"],
    icons=["file-earmark-plus", "folder"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
)
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
        prijsscherpte = 100 if offer_amount > 50000 else 90 if offer_amount > 25000 else 80 if offer_amount > 10000 else 70 if offer_amount > 5000 else 60
    elif klantgrootte == "B":
        prijsscherpte = 80 if offer_amount > 50000 else 70 if offer_amount > 25000 else 60 if offer_amount > 10000 else 50 if offer_amount > 5000 else 40
    elif klantgrootte == "C":
        prijsscherpte = 75 if offer_amount > 50000 else 65 if offer_amount > 25000 else 50 if offer_amount > 10000 else 40 if offer_amount > 5000 else 30
    elif klantgrootte == "D":
        prijsscherpte = 70 if offer_amount > 50000 else 60 if offer_amount > 25000 else 45 if offer_amount > 10000 else 25 if offer_amount > 5000 else 10
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

# Functie om aanbevolen prijs te berekenen
def calculate_recommended_price(min_price, max_price, prijsscherpte):
    if min_price is not None and max_price is not None and prijsscherpte != "":
        return min_price + ((max_price - min_price) * (100 - prijsscherpte) / 100)
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
                    recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                    data.append([None, customer_number, description, article_number, "Breedte", "Hoogte", "Aantal", f"€ {recommended_price:.2f}" if recommended_price is not None else None, "M2 p/s", "M2 totaal", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

            new_df = pd.DataFrame(data, columns=["Offertenummer", "Klantnummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Datum"])
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

# Functie om tekstinvoer te verwerken
def handle_text_input(input_text):
    matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in input_text]

    if matched_articles:
        response_text = "Bedoelt u de volgende samenstellingen:"
        for term, article_number in matched_articles:
            description, _, _ = find_article_details(article_number)
            if description:
                response_text += f"- {description} met artikelnummer {article_number}\n"

        response_text += "?"
        st.sidebar.write(response_text)
    else:
        st.sidebar.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")

# Offerte Genereren tab
if selected_tab == "Offerte Genereren":
    if st.sidebar.button("Verstuur chat met GPT"):
        try:
            handle_gpt_chat()
        except Exception as e:
            st.sidebar.error(f"Er is een fout opgetreden: {e}")

# Opgeslagen Offertes tab
elif selected_tab == "Opgeslagen Offertes":
    st.title("Opgeslagen Offertes")
    if not st.session_state.saved_offers.empty:
        offers_summary = st.session_state.saved_offers.groupby("Offertenummer").agg({
            "Klantnummer": "first",
            "Datum": "first",
            "RSP": lambda x: (x.str.replace('€', '').str.strip().astype(float) * st.session_state.saved_offers["M2 totaal"].str.split().str[0].astype(float)).sum()
        }).reset_index()
        offers_summary.rename(columns={"RSP": "Eindbedrag"}, inplace=True)
        offers_summary["Selectie"] = offers_summary.apply(lambda x: f"Offertenummer: {x['Offertenummer']} | Klantnummer: {x['Klantnummer']} | Eindtotaal: € {x['Eindbedrag']:.2f} | Datum: {x['Datum']}", axis=1)
        selected_offer = st.selectbox("Selecteer een offerte om in te laden", offers_summary['Selectie'], key='select_offerte')
        if st.button("Laad offerte", key='load_offerte_button'):
            selected_offertenummer = int(selected_offer.split('|')[0].split(':')[1].strip())
            offer_rows = st.session_state.saved_offers[st.session_state.saved_offers['Offertenummer'] == selected_offertenummer]
            if not offer_rows.empty:
                st.session_state.offer_df = offer_rows.copy()
                st.success(f"Offerte {selected_offertenummer} succesvol ingeladen.")
    else:
        st.warning("Er zijn nog geen offertes opgeslagen.")

# Toon bewaarde offerte DataFrame in het middenscherm en maak het aanpasbaar
if not st.session_state.offer_df.empty:
    # Voeg een knop toe om de offerte als PDF te downloaden
    if st.button("Download offerte als PDF", key='download_pdf_button'):
        # Functie voor PDF generatie (kan worden toegevoegd)
        pass
    st.title("Offerteoverzicht")
    edited_df = st.data_editor(st.session_state.offer_df, num_rows="dynamic", key='offer_editor')

    # Voeg een knop toe om de artikelen op te slaan in het geheugen
    if st.button("Sla offerte op", key='save_offerte_button'):
        # Genereer een uniek offertenummer
        if 'next_offer_number' not in st.session_state:
            st.session_state.next_offer_number = 1
        offer_number = st.session_state.next_offer_number
        st.session_state.next_offer_number += 1

        # Voeg offerte-informatie toe aan een nieuwe DataFrame
        offer_summary = edited_df.copy()
        offer_summary['Offertenummer'] = offer_number
        offer_summary['Klantnummer'] = customer_number
        offer_summary['Datum'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Voeg offerte-informatie toe aan opgeslagen offertes
        st.session_state.saved_offers = pd.concat([st.session_state.saved_offers, offer_summary], ignore_index=True)

        # Sla op naar CSV-bestand
        try:
            st.session_state.saved_offers.to_csv(csv_path, index=False)
            st.success(f"Offerte {offer_number} succesvol opgeslagen in het geheugen en in CSV-bestand.")
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het opslaan naar CSV: {e}")

    # Herbereken M2 totaal bij wijzigingen in de tabel
    if not edited_df.equals(st.session_state.offer_df):
        edited_df["M2 totaal"] = edited_df.apply(lambda row: float(row["Aantal"]) * float(row["M2 p/s"].split()[0]) if pd.notna(row["Aantal"]) and pd.notna(row["M2 p/s"]) else None, axis=1)
        st.session_state.offer_df = edited_df

import streamlit as st
st.set_page_config(layout="wide")
from streamlit_option_menu import option_menu
import os
import pandas as pd
from PIL import Image
import pytesseract
import re
from num2words import num2words
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode, GridUpdateMode, DataReturnMode
import openai


# OpenAI API-sleutel instellen
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API-sleutel ontbreekt. Stel de OPENAI_API_KEY omgevingsvariabele in de Streamlit Cloud-instellingen in.")
else:
    openai.api_key = api_key  # Initialize OpenAI ChatCompletion client
    print("API-sleutel is ingesteld.")  # Bevestiging dat de sleutel is ingesteld

# Hard gecodeerde klantgegevens
customer_data = {
    "111111": {"revenue": "50.000 euro", "size": "D"},
    "222222": {"revenue": "140.000 euro", "size": "B"},
    "333333": {"revenue": "600.000 euro", "size": "A"}
}

# Initialiseer offerte DataFrame en klantnummer in sessiestatus
if "offer_df" not in st.session_state:
    st.session_state.offer_df = pd.DataFrame(columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Min_prijs", "Max_prijs"])
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
selected_tab = st.radio(
    "Selecteer een optie:",
    ["Offerte Genereren", "Opgeslagen Offertes"],
    index=0,
    horizontal=True,
)


# Omzetting naar numerieke waarden en lege waarden vervangen door 0
st.session_state.offer_df["M2 totaal"] = pd.to_numeric(st.session_state.offer_df["M2 totaal"], errors='coerce').fillna(0)
st.session_state.offer_df["RSP"] = pd.to_numeric(st.session_state.offer_df["RSP"], errors='coerce').fillna(0)

# Berekeningen uitvoeren
totaal_m2 = st.session_state.offer_df["M2 totaal"].sum()
totaal_bedrag = (st.session_state.offer_df["M2 totaal"] * st.session_state.offer_df["RSP"]).sum()

# Resultaten weergeven
st.sidebar.title("PricePilot")
st.sidebar.markdown("---")  # Scheidingslijn voor duidelijkheid
st.sidebar.metric("Totaal m2", f"{totaal_m2:.2f}")
st.sidebar.metric("Totaal Bedrag", f"€ {totaal_bedrag:.2f}")

# Voeg totaal m2 en totaal bedrag toe aan de sidebar onderaan
st.sidebar.markdown("---")  # Scheidingslijn voor duidelijkheid

# Gebruikersinvoer

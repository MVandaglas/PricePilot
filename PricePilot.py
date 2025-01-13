import streamlit as st
st.set_page_config(layout="wide")
from streamlit_option_menu import option_menu
import os
import pandas as pd
from PIL import Image
import re
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode, GridUpdateMode, DataReturnMode
import openai
from SAPprijs import sap_prices
from Synonyms import synonym_dict
from Articles import article_table
import difflib
from rapidfuzz import process, fuzz
from io import BytesIO
from PyPDF2 import PdfReader
import extract_msg



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
    st.session_state.offer_df = pd.DataFrame(columns=["Rijnummer", "Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "RSP", "SAP Prijs", "Handmatige Prijs", "Min_prijs", "M2 p/s", "M2 totaal", "Max_prijs", "Verkoopprijs", "Prijs_backend", "Source"])
if "customer_number" not in st.session_state:
    st.session_state.customer_number = ""
if "loaded_offer_df" not in st.session_state:
    st.session_state.loaded_offer_df = pd.DataFrame(columns=["Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Verkoopprijs"])
if "saved_offers" not in st.session_state:
    st.session_state.saved_offers = pd.DataFrame(columns=["Offertenummer", "Klantnummer", "Eindbedrag", "Datum"])
if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = []


# Converteer article_table naar DataFrame
article_table = pd.DataFrame(article_table)

# Streamlit UI-instellingen
# Maak de tabs aan
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Offerte Genereren", "💾 Opgeslagen Offertes", "✨ Beoordeel AI", "🤖 Glasbot", "⚙️ Instellingen"])

# Tab 1: Offerte Genereren
with tab1:
    st.subheader("Offerte Genereren")
    
    if st.session_state.offer_df is not None and not st.session_state.offer_df.empty:
        st.title("Offerteoverzicht")


if st.session_state.offer_df is None or st.session_state.offer_df.empty:
    st.session_state.offer_df = pd.DataFrame(columns=["Rijnummer", "Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "M2 p/s", "M2 totaal", "RSP", "SAP Prijs", "Handmatige Prijs", "Min_prijs", "Max_prijs", "Verkoopprijs", "Prijs_backend", "Source"])


# Omzetting naar numerieke waarden en lege waarden vervangen door 0
st.session_state.offer_df["M2 totaal"] = pd.to_numeric(st.session_state.offer_df["M2 totaal"], errors='coerce').fillna(0)
st.session_state.offer_df["RSP"] = pd.to_numeric(st.session_state.offer_df["RSP"], errors='coerce').fillna(0)
st.session_state.offer_df["Verkoopprijs"] = pd.to_numeric(st.session_state.offer_df["Verkoopprijs"], errors='coerce')

# Offerte Genereren tab
with tab1:
    
    # Voeg een dropdown toe voor prijsbepaling met een breedte-instelling
    col1, _ = st.columns([1, 7])  # Maak kolommen om breedte te beperken
    with col1:
        prijsbepaling_optie = st.selectbox("Prijsbepaling", ["PricePilot logica", "SAP prijs", "RSP"], key="prijsbepaling", help="Selecteer een methode voor prijsbepaling.")

# Offerte Genereren tab
with tab1:
    def bereken_prijs_backend(df):
        if df is None or not isinstance(df, pd.DataFrame):
            st.warning("De DataFrame is leeg of ongeldig. Prijs_backend kan niet worden berekend.")
            return pd.DataFrame()  # Retourneer een lege DataFrame als fallback

        try:
            # Controleer of de DataFrame geldig is
            if not isinstance(df, pd.DataFrame):
                raise ValueError("De input is geen geldige DataFrame.")

            # Zorg ervoor dat kolommen numeriek zijn of bestaan
            for col in ["SAP Prijs", "RSP", "Handmatige Prijs", "Prijskwaliteit"]:
                if col not in df.columns:
                    df[col] = 0  # Voeg de kolom toe als deze niet bestaat

            df["SAP Prijs"] = pd.to_numeric(df["SAP Prijs"], errors="coerce").fillna(0)
            df["RSP"] = pd.to_numeric(df["RSP"], errors="coerce").fillna(0)
            df["Handmatige Prijs"] = pd.to_numeric(df["Handmatige Prijs"], errors="coerce").fillna(0)
            df["Prijskwaliteit"] = pd.to_numeric(df["Prijskwaliteit"], errors="coerce").fillna(100)

            # Functie om Prijs_backend te bepalen op basis van logica
            def bepaal_prijs_backend(row):
                # Controleer of Handmatige Prijs is ingevuld
                if row["Handmatige Prijs"] > 0:
                    return row["Handmatige Prijs"]
                
                # Logica voor SAP Prijs
                elif prijsbepaling_optie == "SAP prijs":
                    return row["SAP Prijs"]
                
                # Logica voor RSP
                elif prijsbepaling_optie == "RSP":
                    rsp_met_kwaliteit = row["RSP"] * (row["Prijskwaliteit"] / 100)
                    return (rsp_met_kwaliteit * 20 // 1 + (1 if (rsp_met_kwaliteit * 20 % 1) > 0 else 0)) / 20
                
                # Logica voor PricePilot
                elif prijsbepaling_optie == "PricePilot logica":
                    return min(row["SAP Prijs"], row["RSP"])
                
                # Default naar 0 als niets anders van toepassing is
                return 0

            # Pas de prijsbepaling logica toe op de DataFrame
            df["Prijs_backend"] = df.apply(bepaal_prijs_backend, axis=1)

            # Verkoopprijs is gelijk aan Prijs_backend
            df["Verkoopprijs"] = df["Prijs_backend"]

        except Exception as e:
            st.error(f"Fout bij het berekenen van Prijs_backend: {e}")

        return df






# Controleer en zet kolommen om
for col in ["M2 totaal", "RSP", "Verkoopprijs"]:
    if col not in st.session_state.offer_df.columns:
        st.session_state.offer_df[col] = 0
    st.session_state.offer_df[col] = pd.to_numeric(st.session_state.offer_df[col], errors='coerce').fillna(0)

# Berekeningen uitvoeren
totaal_m2 = st.session_state.offer_df["M2 totaal"].sum()
totaal_bedrag = (st.session_state.offer_df["M2 totaal"] * st.session_state.offer_df["Prijs_backend"]).sum()


# Resultaten weergeven
st.sidebar.title("PricePilot")
st.sidebar.markdown("---")  # Scheidingslijn voor duidelijkheid
st.sidebar.metric("Totaal m2", f"{totaal_m2:.2f}")
st.sidebar.metric("Totaal Bedrag", f"€ {totaal_bedrag:.2f}")

# Voeg totaal m2 en totaal bedrag toe aan de sidebar onderaan
st.sidebar.markdown("---")  # Scheidingslijn voor duidelijkheid

cutoff_value = st.sidebar.slider(
    "Matchwaarde AI",
    min_value=0.1,
    max_value=1.0,
    value=0.6,  # Standaardwaarde
    step=0.1,  # Stappen in float
    help="Stel matchwaarde in. Hogere waarde betekent strengere matching, 0.6 aanbevolen."
)

# Bijlagen in mail definiëren
def detect_relevant_columns(df):
    """
    Detecteert de relevante kolommen (Artikelnaam, Hoogte, Breedte, Aantal) in een DataFrame.
    """
    column_mapping = {
        "Artikelnaam": ["artikelnaam", "artikel", "product", "samenstelling", "Artikel", "Artikelnaam", "Product", "Samenstelling", "Article", "article"],
        "Hoogte": ["hoogte", "h", "height", "lengte", "Lengte", "Height", "H", "Hoogte"],
        "Breedte": ["breedte", "b", "width", "Breedte", "B", "Width"],
        "Aantal": ["aantal", "quantity", "qty", "stuks", "Aantal", "Quantity", "QTY", "Stuks", "Qty"]
    }
    detected_columns = {}

    for key, patterns in column_mapping.items():
        for pattern in patterns:
            for col in df.columns:
                if re.search(pattern, col, re.IGNORECASE):
                    detected_columns[key] = col
                    break
            if key in detected_columns:
                break

    return detected_columns



# Gebruikersinvoer
customer_input = st.sidebar.text_area("Voer hier het klantverzoek in (e-mail, tekst, etc.)")
customer_number = st.sidebar.text_input("Klantnummer (6 karakters)", max_chars=6)
st.session_state.customer_number = str(customer_number) if customer_number else ''
offer_amount = totaal_bedrag



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
    # Sla het originele artikelnummer op
    original_article_number = article_number  

        
    # 1. Controleer of artikelnummer een exacte match is in synonym_dict.values()
    if article_number in synonym_dict.values():
        filtered_articles = article_table[article_table['Material'].astype(str) == str(article_number)]
        if not filtered_articles.empty:
            return (
                filtered_articles.iloc[0]['Description'],
                filtered_articles.iloc[0]['Min_prijs'],
                filtered_articles.iloc[0]['Max_prijs'],
                article_number,
                "synoniem",  # Bron: exacte match in synonym_dict.values()
                article_number,  # Original article number
                None  # Fuzzy match remains empty
            )

    # 2. Controleer of artikelnummer een exacte match is in synonym_dict.keys()
    if article_number in synonym_dict.keys():
        matched_article_number = synonym_dict[article_number]  # Haal het bijbehorende artikelnummer op
        filtered_articles = article_table[article_table['Material'].astype(str) == str(matched_article_number)]
        if not filtered_articles.empty:
            return (
                filtered_articles.iloc[0]['Description'],
                filtered_articles.iloc[0]['Min_prijs'],
                filtered_articles.iloc[0]['Max_prijs'],
                matched_article_number,
                "synoniem",  # Bron: exacte match in synonym_dict.keys()
                article_number,  # Original article number
                None  # Fuzzy match remains empty
            )

    # 3. Zoek naar een bijna-match met RapidFuzz
    closest_match = process.extractOne(article_number, synonym_dict.keys(), scorer=fuzz.ratio, score_cutoff=cutoff_value * 100)
    if closest_match:
        best_match = closest_match[0]
        matched_article_number = synonym_dict[best_match]
        filtered_articles = article_table[article_table['Material'].astype(str) == str(matched_article_number)]
        if not filtered_articles.empty:
            return (
                filtered_articles.iloc[0]['Description'],
                filtered_articles.iloc[0]['Min_prijs'],
                filtered_articles.iloc[0]['Max_prijs'],
                matched_article_number,
                "interpretatie",  # Bron: RapidFuzz match
                article_number,  # Original article number
                best_match  # Fuzzy match found
            )
    
    # 4. Zoek naar een bijna-match met difflib
    closest_matches = difflib.get_close_matches(article_number, synonym_dict.keys(), n=1, cutoff=cutoff_value)
    if closest_matches:
        best_match = closest_matches[0]
        matched_article_number = synonym_dict[best_match]
        filtered_articles = article_table[article_table['Material'].astype(str) == str(matched_article_number)]
        if not filtered_articles.empty:
            return (
                filtered_articles.iloc[0]['Description'],
                filtered_articles.iloc[0]['Min_prijs'],
                filtered_articles.iloc[0]['Max_prijs'],
                matched_article_number,
                "interpretatie",  # Bron: difflib match
                article_number,  # Original article number
                best_match  # Fuzzy match found
            )

     # 5. Zoek alternatieven via GPT
    synonym_list_str = "\n".join([f"{k}: {v}" for k, v in synonym_dict.items()])
    prompt = f"""
    Op basis van voorgaande regex is de input '{original_article_number}' niet toegewezen aan een synoniem. Hier is een lijst van beschikbare synoniemen:
    {synonym_list_str}
    Kun je één synoniem voorstellen die het dichtst in de buurt komt bij '{original_article_number}'? Onthoud, het is enorm belangrijk dat je slechts het synoniem retourneert, geen begeleidend schrijven.
    """
    try:
        # Debug: Toon de gegenereerde prompt
        st.write("### Debug: Prompt naar GPT")
        st.write(prompt)
    
        # Correcte API-aanroep
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Je bent een behulpzame assistent die een synoniem zoekt dat het dichtst in de buurt komt van het gegeven artikelnummer. Het is enorm belangrijk dat je slechts het synoniem retourneert, geen begeleidend schrijven."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=20, 
            temperature=0.5,
        )
    
        # Debug: Toon de volledige API-response
        st.write("### Debug: API Response")
        st.write(response)
    
        # Verwerk de response
        response_text = response.choices[0].message.content.strip()
    
        # Debug: Toon de verwerkte respons
        st.write("### Debug: Verwerkte Respons")
        st.write(response_text)
    
        # Controleer op meerdere regels
        if "\n" in response_text:
            suggestions = response_text.split("\n")
            first_suggestion = suggestions[0]
        else:
            first_suggestion = response_text  # Hele respons gebruiken als suggestie
    
        # Debug: Toon de geselecteerde suggestie
        st.write("### Debug: Geselecteerde Suggestie")
        st.write(first_suggestion)
    
        # Resultaat retourneren
        return (first_suggestion, None, None, original_article_number, "GPT", original_article_number, None)  # Bron: GPT suggestie

    except Exception as e:
        # Debug: Toon foutmelding
        st.write("### Debug: Foutmelding")
        st.write(f"Fout bij het raadplegen van OpenAI API: {e}")


    # 6. Als alles niet matcht
    return (None, None, None, original_article_number, "niet gevonden", original_article_number, None)


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

# Functie om determine_spacer waarde te bepalen uit samenstellingstekst
def determine_spacer(term, default_value="15 - alu"):
    if term and isinstance(term, str):
        parts = term.split("-")
        if len(parts) >= 2:
            try:
                values = [int(part) for part in parts if part.isdigit()]
                if len(values) > 1:
                    spacer_value = values[1]
                    if 3 < spacer_value < 30:
                        if any(keyword in term.lower() for keyword in ["we", "warmedge", "warm edge"]):
                            return f"{spacer_value} - warm edge"
                        else:
                            return f"{spacer_value} - alu"
            except ValueError:
                pass
    return default_value

# Voorbeeld van hoe de waarde wordt opgeslagen in de state
def update_spacer_state(user_input, app_state):
    selected_spacer = determine_spacer(user_input)
    app_state["spacer"] = selected_spacer


# Functie om bestaande spacers niet te overschrijven bij updates
def preserve_existing_spacers(df):
    for index, row in df.iterrows():
        if pd.notna(row.get("Spacer")):
            print(f"Spacer behouden op rij {index}: {row['Spacer']}")  # Debugging
            continue  # Behoud bestaande waarde
        # Alleen waarden aanpassen als deze niet bestaan of leeg zijn
        df.at[index, "Spacer"] = determine_spacer(row.get("Spacer", "15 - alu"))
        print(f"Spacer bijgewerkt op rij {index}: {df.at[index, 'Spacer']}")  # Debugging
    return df


def update_offer_data(df):
    for index, row in df.iterrows():
        if pd.notna(row['Breedte']) and pd.notna(row['Hoogte']):
            df.at[index, 'M2 p/s'] = calculate_m2_per_piece(row['Breedte'], row['Hoogte'])
        if pd.notna(row['Aantal']) and pd.notna(df.at[index, 'M2 p/s']):
            df.at[index, 'M2 totaal'] = float(row['Aantal']) * float(str(df.at[index, 'M2 p/s']).split()[0].replace(',', '.'))
        if pd.notna(row['Artikelnummer']):
            # Controleer of Source al is gevuld
            if pd.isna(row.get('Source')) or row['Source'] in ['niet gevonden', 'GPT']:
                description, min_price, max_price, article_number, source, original_article_number, fuzzy_match = find_article_details(row['Artikelnummer'])
                if description:
                    df.at[index, 'Artikelnaam'] = description
                if min_price is not None and max_price is not None:
                    df.at[index, 'Min_prijs'] = min_price
                    df.at[index, 'Max_prijs'] = max_price
                if source:  # Alleen Source bijwerken als deze leeg is
                    df.at[index, 'Source'] = source
                if original_article_number:
                    df.at[index, 'original_article_number'] = original_article_number
                if fuzzy_match:
                    df.at[index, 'fuzzy_match'] = fuzzy_match
            
            # Update SAP Prijs
            if st.session_state.customer_number in sap_prices:
                sap_prijs = sap_prices[st.session_state.customer_number].get(row['Artikelnummer'], None)
                df.at[index, 'SAP Prijs'] = sap_prijs if sap_prijs else "Geen prijs"
            else:
                df.at[index, 'SAP Prijs'] = "Geen prijs"
    df = bereken_prijs_backend(df)
    return df


# Functie om de RSP voor alle regels te updaten
def update_rsp_for_all_rows(df, prijsscherpte):
    # Controleer of prijsscherpte geldig is
    if prijsscherpte:
        for index, row in df.iterrows():
            min_price, max_price = row.get('Min_prijs', None), row.get('Max_prijs', None)
            if pd.notna(min_price) and pd.notna(max_price):
                rsp_value = calculate_recommended_price(min_price, max_price, prijsscherpte)
                # Rond RSP af naar de dichtstbijzijnde 5 cent en zorg voor 2 decimalen
                df.at[index, 'RSP'] = round(rsp_value * 20) / 20
        df = bereken_prijs_backend(df)
    return df





# Functie om Prijs_backend te updaten na wijzigingen
def update_prijs_backend():
    st.session_state.offer_df = bereken_prijs_backend(st.session_state.offer_df)

def reset_rijnummers(df):
    if not df.empty:
        df['Rijnummer'] = range(1, len(df) + 1)
    return df

# JavaScript-code voor conditionele opmaak
cell_style_js = JsCode("""
function(params) {
    if (params.colDef.field === "RSP" && params.data.Prijs_backend === params.data.RSP) {
        return {'backgroundColor': '#DFFFD6', 'fontWeight': 'bold'};  // Lichtgroen met vetgedrukte letters
    } else if (params.colDef.field === "SAP Prijs" && params.data.Prijs_backend === params.data["SAP Prijs"]) {
        return {'backgroundColor': '#DFFFD6', 'fontWeight': 'bold'};  // Lichtgroen met vetgedrukte letters
    } else if (params.colDef.field === "Verkoopprijs" && params.data.Prijs_backend === params.data.Verkoopprijs) {
        return {'backgroundColor': '#DFFFD6', 'fontWeight': 'bold'};  // Lichtgroen met vetgedrukte letters
    } else if (params.colDef.field !== "Verkoopprijs") {
        return {'backgroundColor': '#e0e0e0'};  // Grijs voor alle andere cellen
    }
    return null;
}
""")

# Voeg een cell renderer toe om de stericoon weer te geven
cell_renderer_js = JsCode("""
function(params) {
    if (params.data.Source === "interpretatie" || params.data.Source === "GPT") {
        return `✨ ${params.value}`;  // Voeg stericoon toe vóór de waarde
    }
    return params.value;  // Toon de originele waarde
}
""")


def save_changes(df):
    st.session_state.offer_df = df
    st.session_state.offer_df = update_offer_data(st.session_state.offer_df)
    st.session_state.offer_df = bereken_prijs_backend(st.session_state.offer_df)
    st.session_state.offer_df = update_rsp_for_all_rows(st.session_state.offer_df, st.session_state.get('prijsscherpte', ''))

# Offerte Genereren tab
with tab1:
    # Voeg een veld toe voor prijskwaliteit als RSP wordt gekozen met beperkte breedte
    if prijsbepaling_optie == "RSP":
        col1, _ = st.columns([1, 10])
        with col1:
            prijskwaliteit = st.number_input("Prijskwaliteit (%)", min_value=0, max_value=200, value=100, key="prijskwaliteit")
        st.session_state.offer_df["Prijskwaliteit"] = prijskwaliteit

    # Altijd de logica via de functie bereken_prijs_backend toepassen
    st.session_state.offer_df = bereken_prijs_backend(st.session_state.offer_df)

# JavaScript code voor het opslaan van wijzigingen
js_update_code = JsCode('''
function onCellEditingStopped(params) {
    // Opslaan van gewijzigde data na het bewerken van een cel
    let updatedRow = params.node.data;

    // Zorg ervoor dat wijzigingen worden doorgevoerd in de grid
    params.api.applyTransaction({ update: [updatedRow] });
}
''')


# Maak grid-opties aan voor AgGrid met gebruik van een "select all" checkbox in de header
gb = GridOptionsBuilder.from_dataframe(st.session_state.offer_df)
gb.configure_default_column(flex=1, minWidth=50, editable=True)
gb.configure_column("Spacer", editable=True, cellEditor='agSelectCellEditor', cellEditorParams={"values": ["4 - alu", "6 - alu", "7 - alu", "8 - alu", "9 - alu", "10 - alu", "12 - alu", "13 - alu", "14 - alu", "15 - alu", "16 - alu", "18 - alu", "20 - alu", "24 - alu", "10 - warm edge", "12 - warm edge", "14 - warm edge", "15 - warm edge", "16 - warm edge", "18 - warm edge", "20 - warm edge", "24 - warm edge"]})
gb.configure_column("Rijnummer", type=["numericColumn"], editable=False, cellStyle={"backgroundColor": "#e0e0e0"}, cellRenderer=cell_renderer_js)
gb.configure_column("Artikelnaam", width=600)
gb.configure_column("Offertenummer", hide=True)
gb.configure_column("Prijs_backend", hide=False)
gb.configure_column("Min_prijs", hide=True)
gb.configure_column("Artikelnummer", hide=False)
gb.configure_column("Prijskwaliteit", hide=True)
gb.configure_column("Max_prijs", hide=True)
gb.configure_column("Handmatige Prijs", editable=True, type=["numericColumn"])
gb.configure_column("Breedte", editable=True, type=["numericColumn"])
gb.configure_column("Hoogte", editable=True, type=["numericColumn"])
gb.configure_column("Aantal", editable=True, type=["numericColumn"])
gb.configure_column("RSP", editable=False, type=["numericColumn"], valueFormatter="x.toFixed(2)", cellStyle=cell_style_js)
gb.configure_column("Verkoopprijs", editable=True, type=["numericColumn"], cellStyle=cell_style_js, valueFormatter="x.toFixed(2)")
gb.configure_column("M2 p/s", editable=False, type=["numericColumn"], cellStyle={"backgroundColor": "#e0e0e0"}, valueFormatter="x.toFixed(2)")
gb.configure_column("M2 totaal", editable=False, type=["numericColumn"], cellStyle={"backgroundColor": "#e0e0e0"}, valueFormatter="x.toFixed(2)")
gb.configure_column("SAP Prijs", editable=False, type=["numericColumn"], valueFormatter="x.toFixed(2)", cellStyle=cell_style_js)
gb.configure_column("Source", hide=False)


# Configuratie voor selectie, inclusief checkbox in de header voor "select all"
gb.configure_selection(
    selection_mode='multiple',
    use_checkbox=True,
    header_checkbox=True  # Voeg een selectievakje in de header toe
)

# Voeg de JavaScript code toe aan de grid-opties
gb.configure_grid_options(onCellEditingStopped=js_update_code)

# Overige configuratie van de grid
gb.configure_grid_options(domLayout='normal', rowHeight=23)  # Dit zorgt ervoor dat scrollen mogelijk is

# Voeg een JavaScript event listener toe voor updates bij het indrukken van Enter
js_update_code = JsCode('''
function onCellValueChanged(params) {
    let rowNode = params.node;
    let data = rowNode.data;

    // Zorg ervoor dat wijzigingen direct worden toegepast
    params.api.applyTransaction({ update: [data] });

    // Forceer visuele update
    params.api.refreshCells({ force: true });

    // Luister naar de Enter-toets
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            // Ververs de grid wanneer Enter wordt ingedrukt
            params.api.redrawRows();
        }
    });
}
''')
gb.configure_grid_options(onCellValueChanged=js_update_code)

# Bouw grid-opties
grid_options = gb.build()

# Offerte Genereren tab
with tab1:

    # Toon de AG Grid met het material-thema
    edited_df_response = AgGrid(
        st.session_state.offer_df,
        gridOptions=grid_options,
        theme='material',
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        allow_unsafe_jscode=True
    )

    # Update de DataFrame na elke wijziging
    if "data" in edited_df_response:
        updated_df = pd.DataFrame(edited_df_response['data'])
        # Werk de sessiestatus bij met de nieuwe data
        st.session_state.offer_df = updated_df
        # Voer alle benodigde berekeningen uit
        st.session_state.offer_df = update_offer_data(st.session_state.offer_df)
        st.session_state.offer_df = bereken_prijs_backend(st.session_state.offer_df)

 
   

# Verbeterde update_tabel functie
def update_tabel():
    updated_df = pd.DataFrame(edited_df_response['data'])
    st.session_state.offer_df = updated_df
    st.session_state.offer_df = update_offer_data(st.session_state.offer_df)
    st.session_state.offer_df = bereken_prijs_backend(st.session_state.offer_df)

# Offerte Genereren tab
with tab1:
    
    # Knop om de tabel bij te werken
    if st.button("Update tabel"):
        update_tabel()
        update_tabel()
 
    # Update de DataFrame na elke wijziging
    updated_df = edited_df_response['data']
    save_changes(pd.DataFrame(updated_df))
    
    # Sla de geselecteerde rijen op in sessie status
    selected_rows = edited_df_response.get('selected_rows_id', edited_df_response.get('selected_rows', edited_df_response.get('selected_data', [])))


    # Zorg dat selected_rows geen None of DataFrame is, maar altijd een lijst
    if selected_rows is None or not isinstance(selected_rows, list):
        selected_rows = []
    
    # Als er rijen zijn geselecteerd, zet deze in de sessie state
    if isinstance(selected_rows, list) and len(selected_rows) > 0:
        try:
            st.session_state.selected_rows = [int(r) for r in selected_rows]
        except ValueError:
            st.write("Waarschuwing: Fout bij het converteren van geselecteerde rijen naar indices.")
    else:
        st.session_state.selected_rows = []
    
    def delete_selected_rows(df, selected):
        if selected_rows is not None and len(selected_rows) > 0:
            # Zorg ervoor dat de indices integers zijn
            selected = [int(i) for i in selected]
            st.write("Geselecteerde indices na conversie:", selected)  # Debugging statement
    
            # Verwijder de geselecteerde rijen en reset de index
            new_df = df.drop(index=selected_rows, errors='ignore').reset_index(drop=True)
            return new_df
           
        else:
            return df

   
    # Knoppen toevoegen aan de GUI
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        if st.button("Voeg rij toe"):
            # Voeg een lege rij toe aan het DataFrame
            new_row = pd.DataFrame({
                "Offertenummer": [None], "Artikelnaam": [""], "Artikelnummer": [""], "Spacer": ["15 - alu"], "Breedte": [0], "Hoogte": [0],
                "Aantal": [0], "RSP": [0], "M2 p/s": [0], "M2 totaal": [0], "Min_prijs": [0], "Max_prijs": [0], "Verkoopprijs": [0]
            })
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_row], ignore_index=True)
            st.session_state.offer_df = bereken_prijs_backend(st.session_state.offer_df)
            # Werk de Rijnummer-kolom bij zodat deze overeenkomt met de index + 1
            st.session_state.offer_df = reset_rijnummers(st.session_state.offer_df)
            # Vernieuw de AgGrid
            st.rerun()
    
    with col2:
        if st.button("Verwijder rijen (2x klikken)", key='delete_rows_button'):
            # Haal de geselecteerde rijen op in de juiste vorm
            selected = st.session_state.selected_rows
            st.write("Geselecteerde rijen voor verwijdering:", selected)  # Debugging statement
    
            # Verwijder rijen op basis van index
            if len(selected) > 0:
                # Verwijder de rijen uit de DataFrame op basis van de geselecteerde indices
                st.session_state.offer_df = delete_selected_rows(st.session_state.offer_df, selected)
                st.session_state.selected_rows = []  # Reset de geselecteerde rijen na verwijderen
                # Reset de Rijnummer-kolom na verwijderen
                st.session_state.offer_df = reset_rijnummers(st.session_state.offer_df)
                st.rerun
            else:
                st.warning("Selecteer eerst rijen om te verwijderen.")
    
        # Zorg dat de update wordt getriggerd na verwijdering
        st.session_state['trigger_update'] = True

  
# Functie om getallen van 1 tot 100 te herkennen
def extract_numbers(text):
    pattern = r'\b(1|[1-9]|[1-9][0-9]|100)\b'
    matches = re.findall(pattern, text)
    return [int(match) for match in matches]

# Functie om woorden naar getallen om te zetten
def word_to_number(word):
    mapping = {
        "een": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10, "elf": 11, "twaalf": 12, "dertien": 13, "veertien": 14, "vijftien": 15, "zestien": 16, "zeventien": 17, "achttien": 18, 
        "negentien": 19, "twintig": 20, "eenentwintig": 21, "tweeëntwintig": 22, "drieëntwintig": 23, "vierentwintig": 24, "vijfentwintig": 25, "zesentwintig": 26, "zevenentwintig": 27, "achtentwintig": 28, 
        "negenentwintig": 29, "dertig": 30, "eenendertig": 31, "tweeëndertig": 32, "drieënendertig": 33, "vierendertig": 34, "vijfendertig": 35, "zesendertig": 36, "zevenendertig": 37, "achtendertig": 38, 
        "negenendertig": 39, "veertig": 40, "eenenveertig": 41, "tweeënveertig": 42, "drieënveertig": 43, "vierenveertig": 44, "vijfenveertig": 45, "zesenveertig": 46, "zevenenveertig": 47, "achtenveertig": 48, 
        "negenenveertig": 49, "vijftig": 50, "eenenvijftig": 51, "tweeënvijftig": 52, "drieënvijftig": 53, "vierenvijftig": 54, "vijfenvijftig": 55, "zesenvijftig": 56, "zevenenvijftig": 57, "achtenvijftig": 58, 
        "negenenvijftig": 59, "zestig": 60, "eenenzestig": 61, "tweeënzestig": 62, "drieënzestig": 63, "vierenzestig": 64, "vijfenzestig": 65, "zesenzestig": 66, "zevenenzestig": 67, "achtenzestig": 68, 
        "negenenzestig": 69, "zeventig": 70, "eenenzeventig": 71, "tweeënzeventig": 72, "drieënzeventig": 73, "vierenzeventig": 74, "vijfenzeventig": 75, "zesenzeventig": 76, "zevenenzeventig": 77, "achtenzeventig": 78, 
        "negenenzeventig": 79, "tachtig": 80, "eenentachtig": 81, "tweeëntachtig": 82, "drieëntachtig": 83, "vierentachtig": 84, "vijfentachtig": 85, "zesentachtig": 86, "zevenentachtig": 87, "achtentachtig": 88, 
        "negenentachtig": 89, "negentig": 90, "eenennegentig": 91, "tweeënnegentig": 92, "drieënnegentig": 93, "vierennegentig": 94, "vijfennegentig": 95, "zesennegentig": 96, "zevenennegentig": 97, "achtennegentig": 98, 
        "negenennegentig": 99, "honderd": 100
    }
    return mapping.get(word, None)

# Callback functie voor het verwijderen van geselecteerde rijen
@st.cache_data
def update_dash_table(n_dlt, n_add, data):
    if ctx.triggered_id == "add-row-btn":
        new_row = pd.DataFrame({
            "Offertenummer": [None],
            "Artikelnaam": [""],
            "Artikelnummer": [""],
            "Spacer": [st.session_state.get("last_selected_spacer", "15 - alu")],  # Gebruik de laatst geselecteerde waarde
            "Breedte": [0],
            "Hoogte": [0],
            "Aantal": [0],
            "RSP": [0],
            "M2 p/s": [0],
            "M2 totaal": [0],
            "Min_prijs": [0],
            "Max_prijs": [0],
            "Verkoopprijs": [0]
        })
        df_new_row = pd.DataFrame(new_row)
        updated_table = pd.concat([pd.DataFrame(data), df_new_row])
        return False, updated_table.to_dict("records")

    elif ctx.triggered_id == "delete-row-btn":
        return True, no_update


  
# Functie om het aantal uit tekst te extraheren
def extract_quantity(text):
    # Zoek naar een getal of woord dat voor 'stuks', 'aantal', 'ruiten', 'st', 'keer', of 'x' staat
    unit_matches = re.findall(r'(\d+|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|elf|twaalf|dertien|veertien|vijftien|zestien|zeventien|achttien|negentien|twintig|eenentwintig|tweeëntwintig|drieëntwintig|vierentwintig|vijfentwintig|zesentwintig|zevenentwintig|achtentwintig|negenentwintig|dertig|eenendertig|tweeëndertig|drieëndertig|vierendertig|vijfendertig|zesendertig|zevenendertig|achtendertig|negenendertig|veertig|eenenveertig|tweeënveertig|drieënveertig|vierenveertig|vijfenveertig|zesenveertig|zevenenveertig|achtenveertig|negenenveertig|vijftig|eenenvijftig|tweeënvijftig|drieënvijftig|vierenvijftig|vijfenvijftig|zesenvijftig|zevenenvijftig|achtenvijftig|negenenvijftig|zestig|eenenzestig|tweeënzestig|drieënzestig|vierenzestig|vijfenzestig|zesenzestig|zevenenzestig|achtenzestig|negenenzestig|zeventig|eenenzeventig|tweeënzeventig|drieënzeventig|vierenzeventig|vijfenzeventig|zesenzeventig|zevenenzeventig|achtenzeventig|negenenzeventig|tachtig|eenentachtig|tweeëntachtig|drieëntachtig|vierentachtig|vijfentachtig|zesentachtig|zevenentachtig|achtentachtig|negenentachtig|negentig|eenennegentig|tweeënnegentig|drieënnegentig|vierennegentig|vijfennegentig|zesennegentig|zevenennegentig|achtennegentig|negenennegentig|honderd)\s*(stuks|aantal|ruiten|st|keer|x)\b', text, re.IGNORECASE)

    
    if unit_matches:
        # Als een match gevonden is, zet het om naar een getal
        return word_to_number(unit_matches[0][0]) if unit_matches[0][0].isalpha() else int(unit_matches[0][0])
    
    # Anders zoek naar een getal alleen
    quantity_matches = extract_numbers(text)
    word_matches = re.findall(r'\b(twee|drie|vier|vijf|zes|zeven|acht|negen|tien|elf|twaalf|dertien|veertien|vijftien|zestien|zeventien|achttien|negentien|twintig|eenentwintig|tweeëntwintig|drieëntwintig|vierentwintig|vijfentwintig|zesentwintig|zevenentwintig|achtentwintig|negenentwintig|dertig|eenendertig|tweeëndertig|drieëndertig|vierendertig|vijfendertig|zesendertig|zevenendertig|achtendertig|negenendertig|veertig|eenenveertig|tweeënveertig|drieënveertig|vierenveertig|vijfenveertig|zesenveertig|zevenenveertig|achtenveertig|negenenveertig|vijftig|eenenvijftig|tweeënvijftig|drieënvijftig|vierenvijftig|vijfenvijftig|zesenvijftig|zevenenvijftig|achtenvijftig|negenenvijftig|zestig|eenenzestig|tweeënzestig|drieënzestig|vierenzestig|vijfenzestig|zesenzestig|zevenenzestig|achtenzestig|negenenzestig|zeventig|eenenzeventig|tweeënzeventig|drieënzeventig|vierenzeventig|vijfenzeventig|zesenzeventig|zevenenzeventig|achtenzeventig|negenenzeventig|tachtig|eenentachtig|tweeëntachtig|drieëntachtig|vierentachtig|vijfentachtig|zesentachtig|zevenentachtig|achtentachtig|negenentachtig|negentig|eenennegentig|tweeënnegentig|drieënnegentig|vierennegentig|vijfennegentig|zesennegentig|zevenennegentig|achtennegentig|negenennegentig|honderd)\b', text)

    if word_matches:
        return word_to_number(word_matches[0])  # Neem het eerste gevonden aantal in woorden
    if quantity_matches:
        return quantity_matches[0]  # Neem het eerste gevonden aantal in cijfers
    return None


# Functie om afmetingen (breedte en hoogte) uit tekst te extraheren
def extract_dimensions(text):
    # Zoek naar een patroon zoals '800 bij 900' of '800x900', waarbij we waarden > 99 voor breedte en hoogte willen
    matches = re.findall(r'(\d+)\s*(bij|X|x)\s*(\d+)', text)
    dimensions = []
    for match in matches:
        width, _, height = match
        width = int(width)
        height = int(height)
        if width > 99 and height > 99:
            dimensions.append((width, height))
    
    if dimensions:
        return dimensions[0]  # Geef de eerste geldige set van afmetingen terug
    return None, None

# Functie om alle gegevens (aantal, afmetingen, artikelnummer) te extraheren
def extract_all_details(line):
    # Extract quantity
    quantity = extract_quantity(line)
    # Extract dimensions
    width, height = extract_dimensions(line)
    # Extract article number
    article_number_match = re.search(r'(\d+[./-]?\d*[-*#]\d+[./-]?\d*)', line)
    article_number = article_number_match.group(0) if article_number_match else None
    return quantity, width, height, article_number

def handle_gpt_chat():
    if customer_input:
        lines = customer_input.splitlines()
        data = []
        for line in lines:
            # Nieuwe regex voor herkenning van patronen zoals "400m2 van 4-4" of "4-4 400m2"
            m2_match = re.search(r'(\d+)\s*m2.*?(\d+-\d+)|^(\d+-\d+).*?(\d+)\s*m2', line, re.IGNORECASE)
            if m2_match:
                # Afhankelijk van de volgorde in de match, haal het artikelnummer en m2 op
                if m2_match.group(1):
                    m2_total = int(m2_match.group(1))
                    article_number = m2_match.group(2)
                else:
                    article_number = m2_match.group(3)
                    m2_total = int(m2_match.group(4))

                # Zoek artikelnummer op in synoniemenlijst
                article_number = synonym_dict.get(article_number, article_number)

                description, min_price, max_price, article_number, source, original_article_number, fuzzy_match = find_article_details(article_number)
                if description:
                    # Bereken de aanbevolen prijs (RSP)
                    recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)

                    # Voeg een regel toe aan de data met Verkoopprijs en Prijs_backend
                    verkoopprijs = None  
                    prijs_backend = verkoopprijs if verkoopprijs is not None else recommended_price

                    data.append([
                        None,  # Placeholder voor Offertenummer
                        description,
                        article_number,
                        None,  # Spacer blijft leeg
                        None,  # Breedte blijft leeg
                        None,  # Hoogte blijft leeg
                        None,  # Aantal blijft leeg
                        f"{recommended_price:.2f}" if recommended_price is not None else 0,  # RSP gevuld
                        None,  # M2 p/s blijft leeg
                        f"{m2_total:.2f}",  # M2 totaal
                        None, # Handmatige prijs blijft leeg
                        None, # SAP Prijs wordt gevuld
                        min_price,
                        max_price,
                        verkoopprijs,
                        prijs_backend,
                        source,
                        fuzzy_match,  # Vul fuzzy_match kolom
                        original_article_number  # Vul original_article_number kolom
                        
                    ])
                else:
                    st.sidebar.warning(f"Artikelnummer '{article_number}' niet gevonden in de artikelentabel.")
            else:
                # Bestaande logica voor het extraheren van aantal, breedte, hoogte, etc.
                quantity, width, height, article_number = extract_all_details(line)
                if article_number:
                    # Zoek artikelnummer op in synoniemenlijst
                    article_number = synonym_dict.get(article_number, article_number)
                    description, min_price, max_price, article_number, source, original_article_number, fuzzy_match = find_article_details(article_number)
                    if description:
                        # Bepaal de spacer waarde
                        spacer = determine_spacer(line)
                        # Rest van de bestaande verwerking voor als er geen specifieke m2 is
                        recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                        m2_per_piece = round(calculate_m2_per_piece(width, height), 2) if width and height else None
                        m2_total = round(float(quantity) * m2_per_piece, 2) if m2_per_piece and quantity else None

                        verkoopprijs = None
                        prijs_backend = verkoopprijs if verkoopprijs is not None else recommended_price

                        data.append([
                            None,  # Placeholder voor Offertenummer
                            description,
                            article_number,
                            spacer,
                            width,
                            height,
                            quantity,
                            f"{m2_per_piece:.2f}" if m2_per_piece is not None else None,
                            f"{m2_total:.2f}" if m2_total is not None else None,
                            f"{recommended_price:.2f}" if recommended_price is not None else 0,
                            min_price,
                            None, # Handmatige prijs is leeg
                            max_price,
                            None, # SAP Prijs wordt gevuld
                            verkoopprijs,
                            prijs_backend,
                            source,
                            fuzzy_match,  # Vul fuzzy_match kolom
                            original_article_number  # Vul original_article_number kolom
                        ])
                    else:
                        st.sidebar.warning(f"Artikelnummer '{article_number}' niet gevonden in de artikelentabel.")
                else:
                    st.sidebar.warning("Geen artikelen gevonden in de invoer.")

        if data:
            new_df = pd.DataFrame(data, columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "M2 p/s", "M2 totaal", "RSP", "SAP Prijs", "Handmatige Prijs", "Min_prijs", "Max_prijs", "Verkoopprijs", "Prijs_backend", "Source", "fuzzy_match", "original_article_number"])
            
            # Voeg regelnummers toe
            new_df.insert(0, 'Rijnummer', new_df.index + 1)

            # Update de sessie state met de nieuwe gegevens
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)
            
            # Update de waarden direct om de RSP en andere kolommen te berekenen
            st.session_state.offer_df = update_offer_data(st.session_state.offer_df)  # Update de tabel na toevoegen van nieuwe data
            
            # Update de RSP voor alle regels op basis van de nieuwe prijsscherpte
            st.session_state.offer_df = update_rsp_for_all_rows(st.session_state.offer_df, prijsscherpte)

            # Trigger update via een verborgen knop of simulatie
            st.session_state["trigger_update"] = True

            # Reset de Rijnummer-kolom na verwijderen
            st.session_state.offer_df = reset_rijnummers(st.session_state.offer_df)

            # Vernieuw de AgGrid
            st.rerun()

        else:
            st.sidebar.warning("Geen gegevens gevonden om toe te voegen.")
    elif customer_file:
        handle_file_upload(customer_file)
    else:
        st.sidebar.warning("Voer alstublieft tekst in of upload een bestand.")


# Functie voor het verwerken van e-mailinhoud naar offerte
def handle_email_to_offer(email_body):
    if email_body:
        lines = email_body.splitlines()
        data = []
        for line in lines:
            # Verwerking voor specifieke m2-patronen
            m2_match = re.search(r'(\d+)\s*m2.*?(\d+-\d+)|^(\d+-\d+).*?(\d+)\s*m2', line, re.IGNORECASE)
            if m2_match:
                if m2_match.group(1):
                    m2_total = int(m2_match.group(1))
                    article_number = m2_match.group(2)
                else:
                    article_number = m2_match.group(3)
                    m2_total = int(m2_match.group(4))
                
                # Synoniem lookup en artikelgegevens ophalen
                article_number = synonym_dict.get(article_number, article_number)
                description, min_price, max_price, article_number, source, original_article_number, fuzzy_match = find_article_details(article_number)
                
                if description:
                    recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                    verkoopprijs = None
                    prijs_backend = verkoopprijs if verkoopprijs is not None else recommended_price

                    data.append([
                        None, description, article_number, None, None, None, None,
                        f"{recommended_price:.2f}" if recommended_price is not None else 0,
                        None, f"{m2_total:.2f}", None, None, min_price, max_price, verkoopprijs, prijs_backend,
                        source, fuzzy_match, original_article_number
                    ])
                else:
                    st.sidebar.warning(f"Artikelnummer '{article_number}' niet gevonden in de artikelentabel.")
            else:
                # Alternatieve verwerking van regels
                quantity, width, height, article_number = extract_all_details(line)
                if article_number:
                    article_number = synonym_dict.get(article_number, article_number)
                    description, min_price, max_price, article_number, source, original_article_number, fuzzy_match = find_article_details(article_number)
                    
                    if description:
                        spacer = determine_spacer(line)
                        recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                        m2_per_piece = round(calculate_m2_per_piece(width, height), 2) if width and height else None
                        m2_total = round(float(quantity) * m2_per_piece, 2) if m2_per_piece and quantity else None

                        verkoopprijs = None
                        prijs_backend = verkoopprijs if verkoopprijs is not None else recommended_price

                        data.append([
                            None, description, article_number, spacer, width, height, quantity,
                            f"{m2_per_piece:.2f}" if m2_per_piece is not None else None,
                            f"{m2_total:.2f}" if m2_total is not None else None,
                            f"{recommended_price:.2f}" if recommended_price is not None else 0,
                            min_price, None, max_price, None, verkoopprijs, prijs_backend,
                            source, fuzzy_match, original_article_number
                        ])
                    else:
                        st.sidebar.warning(f"Artikelnummer '{article_number}' niet gevonden in de artikelentabel.")

        if data:
            new_df = pd.DataFrame(data, columns=[
                "Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", 
                "Aantal", "M2 p/s", "M2 totaal", "RSP", "SAP Prijs", "Handmatige Prijs", 
                "Min_prijs", "Max_prijs", "Verkoopprijs", "Prijs_backend", "Source", "fuzzy_match", "original_article_number"
            ])
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)
            st.session_state.offer_df = update_rsp_for_all_rows(st.session_state.offer_df, prijsscherpte)
            st.session_state.offer_df = reset_rijnummers(st.session_state.offer_df)
            st.rerun()
        else:
            st.sidebar.warning("Geen gegevens gevonden om toe te voegen.")

def handle_mapped_data_to_offer(df):
    """
    Verwerkt de gemapte data en vertaalt deze naar de tabelstructuur voor offertes.
    """
    data = []
    for _, row in df.iterrows():
        description = row["Artikelnaam"]
        height = row["Hoogte"]
        width = row["Breedte"]
        quantity = row["Aantal"]

        # Synoniem lookup en artikelgegevens ophalen
        article_number = synonym_dict.get(description, description)
        description, min_price, max_price, article_number, source, original_article_number, fuzzy_match = find_article_details(article_number)

        if description:
            recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
            verkoopprijs = None
            prijs_backend = verkoopprijs if verkoopprijs is not None else recommended_price

            m2_per_piece = round(calculate_m2_per_piece(width, height), 2) if width and height else None
            m2_total = round(float(quantity) * m2_per_piece, 2) if m2_per_piece and quantity else None

            data.append([
                None, description, article_number, None, width, height, quantity,
                f"{m2_per_piece:.2f}" if m2_per_piece is not None else None,
                f"{m2_total:.2f}" if m2_total is not None else None,
                f"{recommended_price:.2f}" if recommended_price is not None else 0,
                min_price, None, max_price, None, verkoopprijs, prijs_backend,
                source, fuzzy_match, original_article_number
            ])
        else:
            st.sidebar.warning(f"Artikelnaam '{description}' niet gevonden in de artikelentabel.")

    if data:
        new_df = pd.DataFrame(data, columns=[
            "Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", 
            "Aantal", "M2 p/s", "M2 totaal", "RSP", "SAP Prijs", "Handmatige Prijs", 
            "Min_prijs", "Max_prijs", "Verkoopprijs", "Prijs_backend", "Source", "fuzzy_match", "original_article_number"
        ])
        st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)
        st.session_state.offer_df = update_rsp_for_all_rows(st.session_state.offer_df, prijsscherpte)
        st.session_state.offer_df = reset_rijnummers(st.session_state.offer_df)
        st.rerun()
    else:
        st.sidebar.warning("Geen gegevens gevonden om toe te voegen.")

def manual_column_mapping(df, detected_columns):
    """
    Biedt de gebruiker een interface om ontbrekende kolommen handmatig te mappen.
    """
    all_columns = list(df.columns)
    mapped_columns = detected_columns.copy()

    st.write("Controleer of de kolommen correct zijn gedetecteerd. Indien niet, selecteer de juiste kolom.")

    for key in ["Artikelnaam", "Hoogte", "Breedte", "Aantal"]:
        if key not in detected_columns:
            st.warning(f"Kolom voor '{key}' niet automatisch gevonden.")
        mapped_columns[key] = st.selectbox(
            f"Selecteer kolom voor '{key}'", 
            options=["Geen"] + all_columns,
            index=all_columns.index(detected_columns[key]) if key in detected_columns else 0
        )

    # Filter de mapping om alleen daadwerkelijke selecties te behouden
    mapped_columns = {k: v for k, v in mapped_columns.items() if v != "Geen"}

    return mapped_columns               

# PDF uitlezen
def extract_table_from_pdf(pdf_reader):
    """
    Extracteert tabellen uit een PDF en converteert deze naar een Pandas DataFrame.
    """
    table_data = []
    headers = []

    for page in pdf_reader.pages:
        text = page.extract_text()
        lines = text.splitlines()

        for line in lines:
            # Zoek naar een rij met de headers
            if re.search(r'Artikelnaam.*?Breedte.*?Hoogte.*?Aantal', line, re.IGNORECASE):
                headers = re.split(r'\s{2,}', line.strip())
            elif headers and len(line.split()) >= len(headers):
                # Splits de gegevens als er headers zijn gedetecteerd
                table_data.append(re.split(r'\s{2,}', line.strip()))

    if headers and table_data:
        df = pd.DataFrame(table_data, columns=headers)
        return df
    else:
        st.warning("Geen tabel gevonden in de PDF.")
        return pd.DataFrame()            


# Bepaal de laatste email van een mailboom
def extract_latest_email(body):
    """
    Extraheert alleen de laatste e-mail uit een e-mailthread.
    Het detecteert het begin van een nieuwe e-mail met behulp van het patroon 'Van:' gevolgd door 'Verzonden:'.
    """
    # Split de e-mailthread op basis van het patroon
    email_parts = re.split(r'Van:.*?Verzonden:.*?Aan:.*?Onderwerp:', body, flags=re.DOTALL)
    
    # De eerste sectie is de laatste e-mail in de thread
    if email_parts:
        latest_email = email_parts[0].strip()
        return latest_email
    else:
        return body.strip()  # Als er niets gesplitst wordt, geef de volledige body teru

def process_attachment(attachment, attachment_name):
    """
    Analyseert en verwerkt een bijlage op basis van het type bestand (PDF of Excel).
    """
    if attachment_name.endswith(".xlsx"):
        try:
            # Lees Excel-bestand
            df = pd.read_excel(BytesIO(attachment))
            st.write("Bijlage ingelezen als DataFrame:")
            st.dataframe(df)

            # Detecteer relevante kolommen
            detected_columns = detect_relevant_columns(df)

            # Handmatig mappen indien nodig
            mapped_columns = manual_column_mapping(df, detected_columns)

            if mapped_columns:
                st.write("Definitieve kolommapping:", mapped_columns)

                # Filter de DataFrame op relevante kolommen
                relevant_data = df[[mapped_columns[key] for key in mapped_columns]]
                relevant_data.columns = mapped_columns.keys()  # Hernoem kolommen naar standaardnamen

                st.write("Relevante data:")
                st.dataframe(relevant_data)
              
                # Verwerk de relevante data naar offerte
                if st.sidebar.button("Verwerk gegevens naar offerte"):
                    handle_mapped_data_to_offer(relevant_data)
                
            else:
                st.warning("Geen relevante kolommen gevonden of gemapped.")
                return None
        except Exception as e:
            st.error(f"Fout bij het verwerken van de Excel-bijlage: {e}")
            return None
        

    elif attachment_name.endswith(".pdf"):
        try:
            # Lees PDF-bestand
            pdf_reader = PdfReader(BytesIO(attachment))
            st.write(f"PDF-bestand '{attachment_name}' ingelezen:")

            # Extracteer tabel uit PDF
            pdf_df = extract_table_from_pdf(pdf_reader)

            if not pdf_df.empty:
                st.write("PDF-gegevens als DataFrame:")
                st.dataframe(pdf_df)

                # Detecteer relevante kolommen
                detected_columns = detect_relevant_columns(pdf_df)

                # Handmatig mappen indien nodig
                mapped_columns = manual_column_mapping(pdf_df, detected_columns)

                if mapped_columns:
                    relevant_data = pdf_df[[mapped_columns[key] for key in mapped_columns]]
                    relevant_data.columns = mapped_columns.keys()  # Hernoem kolommen naar standaardnamen

                    st.write("Relevante data:")
                    st.dataframe(relevant_data)

                    # Verwerk de relevante data naar offerte
                    if not relevant_data.empty:
                        if st.button("Verwerk gegevens naar offerte"):
                            handle_mapped_data_to_offer(relevant_data)
                    else:
                        st.warning("Relevante data is leeg. Controleer de kolommapping en inhoud van de PDF.")
                else:
                    st.warning("Geen relevante kolommen gevonden of gemapped.")
            else:
                st.warning("Geen tabelgegevens gevonden in de PDF.")
        except Exception as e:
            st.error(f"Fout bij het verwerken van de PDF-bijlage: {e}")
    else:
        st.warning(f"Bijlage '{attachment_name}' wordt niet ondersteund.")

# File uploader alleen beschikbaar in de uitklapbare invoeropties
with st.sidebar.expander("Upload document", expanded=False):
    # Bestand uploaden
    uploaded_file = st.file_uploader("Upload een Outlook .msg bestand", type=["msg"])
    
    # Controleren of er een bestand is geüpload
    if uploaded_file:
        # Bestand tijdelijk opslaan
        with open("uploaded_email.msg", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Open het .msg-bestand met extract-msg
        try:
            msg = extract_msg.Message("uploaded_email.msg")
            msg_subject = msg.subject
            msg_sender = msg.sender
            full_email_body = msg.body  # De volledige e-mailthread
            latest_email = extract_latest_email(full_email_body)  # Bepaal alleen de laatste e-mail
            msg_body = latest_email
            email_body = msg_body
            
            # Resultaten weergeven
            st.subheader("Berichtinformatie")
            st.write(f"**Onderwerp:** {msg_subject}")
            st.write(f"**Afzender:** {msg_sender}")
            st.write("**Inhoud van het bericht:**")
            st.text(msg_body)
            
            # Verwerk bijlagen
            st.subheader("Bijlagen:")
            if msg.attachments:
                for attachment in msg.attachments:
                    attachment_name = attachment.longFilename or attachment.shortFilename
                    attachment_data = attachment.data
    
                    # Toon naam van de bijlage
                    st.write(f"Bijlage: {attachment_name}")
    
                    # Verwerk de bijlage
                    process_attachment(attachment_data, attachment_name)
            else:
                st.write("Geen bijlagen gevonden.")
        
        except Exception as e:
            st.error(f"Fout bij het verwerken van het bestand: {e}")
    else:
        st.info("Upload een .msg-bestand om verder te gaan.")    





# Functie om tekstinvoer te verwerken
def handle_text_input(input_text):
    matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in input_text]

    if matched_articles:
        response_text = "Bedoelt u de volgende samenstellingen:"
        for term, article_number in matched_articles:
            description, _, _, _, _ = find_article_details(article_number)
            if description:
                response_text += f"- {description} met artikelnummer {article_number}\n"

        response_text += "?"
        st.sidebar.write(response_text)
    else:
        st.sidebar.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")

# Functie om offerte als PDF te genereren
def generate_pdf(df):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'HeaderStyle', parent=styles['Heading1'], fontSize=17, alignment=TA_CENTER, textColor=colors.black
    )
    normal_style = ParagraphStyle(
        'NormalStyle', parent=styles['Normal'], fontSize=11, alignment=TA_LEFT, textColor=colors.black
    )
    right_aligned_style = ParagraphStyle(
        'RightAlignedStyle', parent=styles['Normal'], fontSize=11, alignment=TA_LEFT, textColor=colors.black
    )

    # Header
    elements.append(Paragraph("Vandaglas - Offerte", header_style))
    elements.append(Spacer(1, 12))

    # Introductietekst
    elements.append(Paragraph(
        "Beste klant,<br/><br/>"
        "Hartelijk dank voor uw prijsaanvraag. Hieronder vindt u onze offerte. Wij hopen u een passend aanbod te hebben gedaan. "
        "Uw contactpersoon, Job, geeft graag nog een toelichting en beantwoordt eventuele vragen.<br/><br/>"
        "Met vriendelijke groet,<br/>"
        "Vandaglas",
        normal_style
    ))
    elements.append(Spacer(1, 24))

    # Tabel header
    data = [["Artikelnaam", "Breedte", "Hoogte", "Aantal", "Prijs p/s", "M2 p/s", "Totaal M2", "Totaal"]]

    # Voeg gegevens uit df toe aan tabel
    for index, row in df.iterrows():
        if all(col in row for col in ['Artikelnaam', 'Breedte', 'Hoogte', 'Aantal', 'RSP', 'M2 p/s', 'M2 totaal']):
            data.append([
    row['Artikelnaam'],
    row['Breedte'],
    row['Hoogte'],
    row['Aantal'],
    row['Prijs_backend'],
    f"{float(str(row['M2 p/s']).replace('m²', '').replace(',', '.').strip()):.2f} m2" if pd.notna(row['M2 p/s']) else None,
    f"{float(str(row['M2 totaal']).replace('m²', '').replace(',', '.').strip()):.2f} m2" if pd.notna(row['M2 totaal']) else None,
    f"{round(float(str(row['Prijs_backend']).replace('€', '').replace(',', '.').strip()) * float(row['Aantal']) * float(str(row['M2 p/s']).replace('m²', '').replace(',', '.').strip()), 2):,.2f}" if pd.notna(row['Prijs_backend']) and pd.notna(row['Aantal']) else None
])


    # Maak de tabel
    table = Table(data, repeatRows=1, colWidths=[150, 45, 45, 45, 45, 45, 45, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 24))

    # Eindtotaal, BTW, Te betalen
    total_price = df.apply(lambda row: round(float(str(row['Prijs_backend']).replace('€', '').replace(',', '.').strip()) * float(str(row['M2 totaal']).replace('m²', '').replace(',', '.').strip()), 2) if pd.notna(row['Prijs_backend']) and pd.notna(row['M2 totaal']) else 0, axis=1).sum()
    btw = total_price * 0.21
    te_betalen = total_price + btw

    # Maak klein tabelletje voor totalen
    totals_data = [
        ["Eindtotaal:", f"€ {total_price:.2f}"],
        ["BTW (21%):", f"€ {btw:.2f}"],
        ["Te betalen:", f"€ {te_betalen:.2f}"]
    ]
    totals_table = Table(totals_data, colWidths=[100, 100])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    from reportlab.lib.units import inch
    elements.append(Spacer(1, 0.5 * inch))
    totals_table = Table(totals_data, colWidths=[100, 100], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(Spacer(1, 3 * inch))
    elements.append(totals_table)
  

    # Bouwelementen aan document
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Offerte Genereren tab
with tab1:
    # Knop om GPT-chat te versturen
    if st.sidebar.button("Vertaal chat naar offerte"):
        try:
            handle_gpt_chat()
        except Exception as e:
            st.sidebar.error(f"Er is een fout opgetreden: {e}")

    # Knop om de e-mail te vertalen naar een offerte
    if st.sidebar.button("Vertaal mail naar offerte"):
        try:
            handle_email_to_offer(email_body)
        except Exception as e:
            st.error(f"Fout bij het verwerken van de e-mail: {e}")

# Voeg rijnummers toe aan de offerte DataFrame als deze nog niet bestaat
if 'Rijnummer' not in st.session_state.offer_df.columns:
    st.session_state.offer_df.insert(0, 'Rijnummer', range(1, len(st.session_state.offer_df) + 1))

    


# Offerte Genereren tab
with tab1:    

    with col6:
        # Voeg een knop toe om de offerte als PDF te downloaden
        if totaal_bedrag > 25000:
            st.button("Download offerte als PDF", key='download_pdf_button', disabled=True)
            st.button("Autoriseer offerte", key='authorize_offer_button')
        else:
            if st.button("Download offerte als PDF", key='download_pdf_button'):
                pdf_buffer = generate_pdf(st.session_state.offer_df)
                st.download_button(label="Download PDF", data=pdf_buffer, file_name="offerte.pdf", mime="application/pdf")
    
        if st.button("Sla offerte op", key='save_offerte_button'):
            # Zoek het hoogste offertenummer
            if not st.session_state.saved_offers.empty:
                max_offer_number = st.session_state.saved_offers['Offertenummer'].max()
                offer_number = max_offer_number + 1
            else:
                offer_number = 1
    
            # Bereken eindtotaal
            if all(col in edited_df_response.data.columns for col in ['RSP', 'M2 totaal']):
                eindtotaal = edited_df_response.data.apply(lambda row: float(str(row['RSP']).replace('€', '').replace(',', '.').strip()) * float(str(row['M2 totaal']).split()[0].replace(',', '.')) if pd.notna(row['RSP']) and pd.notna(row['M2 totaal']) else 0, axis=1).sum()
            else:
                eindtotaal = 0
    
            # Voeg offerte-informatie toe aan een nieuwe DataFrame
            offer_summary = pd.DataFrame({
                'Offertenummer': [offer_number],
                'Klantnummer': [str(st.session_state.customer_number)],
                'Eindbedrag': [eindtotaal],
                'Datum': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            })
    
            # Voeg offerte-informatie toe aan opgeslagen offertes
            st.session_state.saved_offers = pd.concat([st.session_state.saved_offers, offer_summary], ignore_index=True)
    
            # Voeg offertenummer toe aan elke regel in de offerte
            st.session_state.offer_df.loc[st.session_state.offer_df['Offertenummer'].isna(), 'Offertenummer'] = offer_number
    
            # Toon succesbericht
            st.success(f"Offerte is opgeslagen onder offertenummer {offer_number}")


if 'edited_df' in locals() and not edited_df.equals(st.session_state.offer_df):
    edited_df = edited_df.copy()
    edited_df = update_offer_data(edited_df)
    st.session_state.offer_df = edited_df

# Opgeslagen Offertes tab
with tab2:
    st.subheader("Opgeslagen Offertes")
    if 'saved_offers' in st.session_state and not st.session_state.saved_offers.empty:
        offers_summary = st.session_state.saved_offers
        offers_summary['Selectie'] = offers_summary.apply(lambda x: f"Offertenummer: {x['Offertenummer']} | Klantnummer: {x['Klantnummer']} | Eindtotaal: € {x['Eindbedrag']:.2f} | Datum: {x['Datum']}", axis=1)
        selected_offer = st.selectbox("Selecteer een offerte om in te laden", offers_summary['Selectie'], key='select_offerte')
        if st.button("Laad offerte", key='load_offerte_button'):
            selected_offertenummer = int(selected_offer.split('|')[0].split(':')[1].strip())
            offer_rows = st.session_state.saved_offers[st.session_state.saved_offers['Offertenummer'] == selected_offertenummer]
            if not offer_rows.empty:
                st.session_state.loaded_offer_df = st.session_state.offer_df[st.session_state.offer_df['Offertenummer'] == selected_offertenummer].copy()
                st.success(f"Offerte {selected_offertenummer} succesvol ingeladen.")
            else:
                st.warning("Geen gedetailleerde gegevens gevonden voor de geselecteerde offerte.")
        if st.button("Vergeet alle offertes", key='forget_offers_button'):
            st.session_state.saved_offers = pd.DataFrame(columns=["Offertenummer", "Klantnummer", "Eindbedrag", "Datum"])
            st.session_state.offer_df = pd.DataFrame(columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"])
            st.success("Alle opgeslagen offertes zijn vergeten.")
    else:
        st.warning("Er zijn nog geen offertes opgeslagen.")




# Toon geladen offerte in de tab "Opgeslagen Offertes"
with tab2:
    if "loaded_offer_df" in st.session_state and not st.session_state.loaded_offer_df.empty:
        st.title("Geladen Offerte")
        required_columns = [
            "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", 
            "Aantal", "RSP", "M2 p/s", "M2 totaal"
        ]
        # Controleer of alle vereiste kolommen aanwezig zijn
        if all(col in st.session_state.loaded_offer_df.columns for col in required_columns):
            st.dataframe(st.session_state.loaded_offer_df[required_columns])
        else:
            st.warning("De geladen offerte bevat niet alle verwachte kolommen.")
    else:
        st.info("Er is nog geen offerte geladen om weer te geven.")


with tab3:
    st.markdown("### Beoordeel output AI ✨")

    # Controleer of offer_df beschikbaar is in sessiestatus
    if "offer_df" in st.session_state and not st.session_state.offer_df.empty:
        # Filter regels met "Source" = "interpretatie"
        interpretatie_rows = st.session_state.offer_df[st.session_state.offer_df["Source"] == "interpretatie"]
        
        # Houd alleen unieke rijen op basis van combinatie van kolommen
        interpretatie_rows = interpretatie_rows.drop_duplicates(subset=["Artikelnaam", "Artikelnummer", "fuzzy_match", "original_article_number"])
    else:
        interpretatie_rows = pd.DataFrame()  # Lege DataFrame als fallback

    if interpretatie_rows.empty:
        st.info("Er zijn geen regels met 'interpretatie' om te beoordelen.")
    else:
        # Maak een tabel met de correcte input en gematchte waarden
        beoordeling_tabel = interpretatie_rows.copy()
        beoordeling_tabel = beoordeling_tabel[["Artikelnaam", "Artikelnummer", "fuzzy_match", "original_article_number"]].fillna("")
        beoordeling_tabel.rename(columns={
            "Artikelnaam": "Artikelnaam",
            "Artikelnummer": "Artikelnummer",
            "fuzzy_match": "Gematcht op",
            "original_article_number": "Input"
        }, inplace=True)

        gb = GridOptionsBuilder.from_dataframe(beoordeling_tabel)
        gb.configure_selection(selection_mode="multiple", use_checkbox=True)
        gb.configure_default_column(editable=True)
        grid_options = gb.build()

        response = AgGrid(
            beoordeling_tabel,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            theme="material"
        )

        # Knop voor accordering
        if st.button("Accordeer synoniem"):
            geselecteerde_rijen = response["selected_rows"]
            if geselecteerde_rijen:
                for rij in geselecteerde_rijen:
                    input_waarde = rij["Input"]
                    artikelnummer = rij["Artikelnummer"]
                    if input_waarde and artikelnummer:
                        Suggested_synonyms_dict[input_waarde] = artikelnummer
                        st.success(f"Synoniem '{input_waarde}' -> '{artikelnummer}' is opgeslagen!")
            else:
                st.warning("Selecteer minimaal één rij om te accorderen.")

with tab4:
    st.subheader("💬 Glasadvies Chatbot")
    st.info("Stel je vraag over glas en krijg advies van AI op basis van beschikbare bronnen.")

    # # Functie om website content en subpagina's op te halen
    # def fetch_website_and_subpages(base_url, max_depth=0):
    #     visited_urls = set()
    #     content_list = []

    #     def crawl(url, depth):
    #         if url in visited_urls or depth > max_depth:
    #             return
    #         try:
    #             visited_urls.add(url)
    #             response = requests.get(url)
    #             if response.status_code == 200:
    #                 soup = BeautifulSoup(response.text, "html.parser")
    #                 content_list.append(soup.get_text())  # Voeg de tekst van de pagina toe
                    
    #                 # Zoek naar onderliggende links
    #                 for link in soup.find_all("a", href=True):
    #                     next_url = link["href"]
    #                     if next_url.startswith("/") or next_url.startswith(base_url):
    #                         full_url = next_url if next_url.startswith("http") else f"{base_url.rstrip('/')}/{next_url.lstrip('/')}"
    #                         crawl(full_url, depth + 1)
    #         except Exception as e:
    #             st.error(f"Fout bij ophalen van {url}: {e}")
    
    #     crawl(base_url, 0)
    #     return "\n".join(content_list)

    # # Functie om PDF-inhoud op te halen
    # def fetch_pdf_content(url):
    #     try:
    #         response = requests.get(url)
    #         pdf_file = io.BytesIO(response.content)
    #         pdf_reader = PdfReader(pdf_file)
    #         text = ""
    #         for page in pdf_reader.pages:
    #             text += page.extract_text()
    #         return text
    #     except Exception as e:
    #         st.error(f"Kon de PDF {url} niet verwerken: {e}")
    #         return ""
    
    # # Bronnen ophalen (websites + PDF)
    # sources = [
    #     fetch_website_and_subpages("https://www.onderhoudnl.nl/glasvraagbaak", max_depth=0),
    #     fetch_website_and_subpages("https://www.glasdiscount.nl/kennisbank/begrippen", max_depth=0),
    #     fetch_pdf_content("https://www.kenniscentrumglas.nl/wp-content/uploads/Infosheet-NEN-2608-1.pdf"),
    #     fetch_pdf_content("https://www.kenniscentrumglas.nl/wp-content/uploads/KCG-infosheet-Letselveiligheid-glas-NEN-3569-1.pdf"),
    # ]
    # combined_source_text = "\n".join(sources)
    
    # Initialiseer chatgeschiedenis in sessiestatus
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [{"role": "assistant", "content": "Hoe kan ik je helpen met glasadvies?"}]
    
    st.title("💬 Glasadvies Chatbot")
    
    # Toon chatgeschiedenis
    for msg in st.session_state["chat_history"]:
        st.chat_message(msg["role"]).write(msg["content"])
    
    # Inputveld voor gebruikersvraag
    user_query = st.chat_input("Stel je vraag hier:")
    
    if user_query:
        st.chat_message("user").write(user_query)  # Toon de gebruikersvraag
        st.session_state["chat_history"].append({"role": "user", "content": user_query})
    
        try:
            # # Verstuur de vraag naar OpenAI met de opgehaalde documentatie
            # response = openai.chat.completions.create(
            #     model="gpt-4",
            #     messages=[
            #         {"role": "system", "content": "Je bent een glasadvies assistent die technisch advies geeft op basis van de gegeven documentatie. Geef kort en helder advies."},
            #         {"role": "user", "content": f"Documentatie:\n{combined_source_text}\n\nVraag: {user_query}"}
            #     ],
            #     max_tokens=300,
            #     temperature=0.7
            # )

            # # Toon het antwoord van OpenAI
            # ai_response = response.choices[0].message.content
            # st.chat_message("assistant").write(ai_response)
            # st.session_state["chat_history"].append({"role": "assistant", "content": ai_response})
            pass  # Deze logica wordt niet uitgevoerd
        except Exception as e:
            st.error(f"Er is een fout opgetreden bij het raadplegen van OpenAI: {e}")

            
with tab5:
    st.subheader("Jouw instellingen")

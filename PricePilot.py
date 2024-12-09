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
import dash_bootstrap_components as dbc


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
    st.session_state.offer_df = pd.DataFrame(columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Min_prijs", "Max_prijs", "Verkoopprijs", "Prijs_backend"])
if "customer_number" not in st.session_state:
    st.session_state.customer_number = ""
if "loaded_offer_df" not in st.session_state:
    st.session_state.loaded_offer_df = pd.DataFrame(columns=["Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Verkoopprijs"])
if "saved_offers" not in st.session_state:
    st.session_state.saved_offers = pd.DataFrame(columns=["Offertenummer", "Klantnummer", "Eindbedrag", "Datum"])
if "selected_rows" not in st.session_state:
    st.session_state.selected_rows = []

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
st.session_state.offer_df["Verkoopprijs"] = pd.to_numeric(st.session_state.offer_df["Verkoopprijs"], errors='coerce')

# Functie om Prijs_backend te berekenen
def bereken_prijs_backend(df):
    df["Prijs_backend"] = df.apply(
    lambda row: row["Verkoopprijs"] if pd.notna(row.get("Verkoopprijs")) and isinstance(row["Verkoopprijs"], (int, float)) and row["Verkoopprijs"] > 0
    else row.get("RSP", 0),
    axis=1
)
    return df


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

# Gebruikersinvoer
customer_input = st.sidebar.text_area("Voer hier het klantverzoek in (e-mail, tekst, etc.)")
customer_number = st.sidebar.text_input("Klantnummer (6 karakters)", max_chars=6)
st.session_state.customer_number = str(customer_number) if customer_number else ''
offer_amount = totaal_bedrag

# File uploader alleen beschikbaar in de uitklapbare invoeropties
with st.sidebar.expander("Upload document", expanded=False):
    customer_file = st.file_uploader("Upload een bestand (bijv. screenshot of document)", type=["png", "jpg", "jpeg", "pdf"])


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


if "offer_df" in st.session_state and not st.session_state.offer_df.empty:
    if "M2 totaal" in st.session_state.offer_df.columns:
        st.session_state.offer_df["M2 totaal"] = pd.to_numeric(st.session_state.offer_df["M2 totaal"], errors='coerce').fillna(0)
    else:
        st.warning("Kolom 'M2 totaal' ontbreekt in het DataFrame.")
else:
    st.warning("Het DataFrame 'offer_df' is niet geïnitialiseerd of leeg.")




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
if selected_tab == "Offerte Genereren":
    
  if st.sidebar.button("Verstuur chat met GPT"):
    try:
       handle_gpt_chat()
    except Exception as e:
        st.sidebar.error(f"Er is een fout opgetreden: {e}")



# Toon bewaarde offerte DataFrame in het middenscherm en maak het aanpasbaar
if st.session_state.offer_df is not None and not st.session_state.offer_df.empty:
    st.title("Offerteoverzicht")

# Voeg rijnummers toe aan de offerte DataFrame als deze nog niet bestaat
if 'Rijnummer' not in st.session_state.offer_df.columns:
    st.session_state.offer_df.insert(0, 'Rijnummer', range(1, len(st.session_state.offer_df) + 1))
    


      
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
elif selected_tab == "Opgeslagen Offertes":
    st.title("Opgeslagen Offertes")
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
if selected_tab == "Opgeslagen Offertes" and st.session_state.loaded_offer_df is not None and not st.session_state.loaded_offer_df.empty:
    st.title("Geladen Offerte")
    required_columns = ["Artikelnaam", "Artikelnummer", "Spacer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"]
    if all(col in st.session_state.loaded_offer_df.columns for col in required_columns):
        st.dataframe(st.session_state.loaded_offer_df[required_columns])
    else:
        st.warning("De geladen offerte bevat niet alle verwachte kolommen.")

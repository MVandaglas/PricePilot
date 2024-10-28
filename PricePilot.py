def handle_gpt_chat():
    if customer_input:
        matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in customer_input]

        if matched_articles:
            data = []
            for term, article_number in matched_articles:
                description, min_price, max_price = find_article_details(article_number)
                if description:
                    quantity, width, height = extract_dimensions(customer_input, term)
                    gpt_interpreted = False  # Indicator voor GPT-interpretatie

                    # Als hoeveelheid niet gevonden wordt, gebruik GPT om een schatting te maken
                    if not quantity:
                        try:
                            response = openai.Completion.create(
                                engine="text-davinci-003",
                                prompt=f"Interpreteer het volgende klantverzoek en geef de hoeveelheid in numerieke vorm: \"{customer_input}\"",
                                max_tokens=10
                            )
                            quantity_match = re.search(r'\d+', response.choices[0].text)
                            quantity = quantity_match.group() if quantity_match else ""
                            gpt_interpreted = True if quantity else False
                        except Exception as e:
                            st.sidebar.error(f"Fout bij GPT-interpretatie: {e}")

                    if quantity.endswith('x'):
                        quantity = quantity[:-1].strip()

                    recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                    m2_per_piece = calculate_m2_per_piece(width, height)
                    m2_total = float(quantity) * m2_per_piece if m2_per_piece and quantity else None
                    data.append([
                        None,  # Placeholder for Offertenummer, to be added later
                        description,
                        article_number,
                        width,
                        height,
                        quantity,
                        f"€ {recommended_price:.2f}" if recommended_price is not None else None,
                        f"{m2_per_piece:.2f} m²" if m2_per_piece is not None else None,
                        f"{m2_total:.2f} m²" if m2_total is not None else None,
                        gpt_interpreted  # Marker voor GPT-interpretatie
                    ])

            new_df = pd.DataFrame(data, columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "GPT"])
            
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)
        else:
            st.sidebar.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
    elif customer_file:
        handle_file_upload(customer_file)
    else:
        st.sidebar.warning("Voer alstublieft tekst in of upload een bestand.")

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
        
        # Pas het dataframe aan om door GPT geïnterpreteerde waarden rood weer te geven
        offer_df_display = st.session_state.offer_df.copy()
        offer_df_display['Aantal'] = offer_df_display.apply(lambda row: f"**:red[{row['Aantal']}]**" if row['GPT'] else row['Aantal'], axis=1)

        st.data_editor(offer_df_display[["Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal", "Offertenummer"]], num_rows="dynamic", key='offer_editor')

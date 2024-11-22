def handle_gpt_chat():
    if customer_input:
        lines = customer_input.splitlines()
        data = []
        for line in lines:
            # Nieuwe regex voor herkenning van patronen zoals "400m2 van 4-4" of "4-4 400m2"
            m2_match = re.search(r'(\d+)\s*m2.*?(\d+-\d+)|(\d+-\d+).*?(\d+)\s*m2', line, re.IGNORECASE)
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

                description, min_price, max_price = find_article_details(article_number)
                if description:
                    # Bereken de aanbevolen prijs (RSP)
                    recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)

                    # Voeg een regel toe aan de data met m² en artikelnummer
                    data.append([
                        None,  # Placeholder voor Offertenummer
                        description,
                        article_number,
                        None,  # Breedte blijft leeg
                        None,  # Hoogte blijft leeg
                        None,  # Aantal blijft leeg
                        f"{recommended_price:.2f}" if recommended_price is not None else 0,  # RSP gevuld
                        None,  # M2 p/s blijft leeg
                        f"{m2_total:.2f}"  # M2 totaal
                    ])
                else:
                    st.sidebar.warning(f"Artikelnummer '{article_number}' niet gevonden in de artikelentabel.")
            else:
                # Bestaande logica voor het extraheren van aantal, breedte, hoogte, etc.
                quantity, width, height, article_number = extract_all_details(line)
                if article_number:
                    # Zoek artikelnummer op in synoniemenlijst
                    article_number = synonym_dict.get(article_number, article_number)
                    description, min_price, max_price = find_article_details(article_number)
                    if description:
                        # Rest van de bestaande verwerking voor als er geen specifieke m2 is
                        recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                        m2_per_piece = round(calculate_m2_per_piece(width, height), 2) if width and height else None
                        m2_total = round(float(quantity) * m2_per_piece, 2) if m2_per_piece and quantity else None

                        data.append([
                            None,  # Placeholder voor Offertenummer
                            description,
                            article_number,
                            width,
                            height,
                            quantity,
                            f"{recommended_price:.2f}" if recommended_price is not None else 0,
                            f"{m2_per_piece:.2f}" if m2_per_piece is not None else None,
                            f"{m2_total:.2f}" if m2_total is not None else None
                        ])
                    else:
                        st.sidebar.warning(f"Artikelnummer '{article_number}' niet gevonden in de artikelentabel.")
                else:
                    st.sidebar.warning("Geen artikelen gevonden in de invoer.")

        if data:
            new_df = pd.DataFrame(data, columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"])
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)
            st.session_state.offer_df = update_offer_data(st.session_state.offer_df)  # Update de tabel na toevoegen van nieuwe data
            st.experimental_rerun()  # Hiermee vernieuw je de Streamlit app, zodat de AgGrid bijgewerkt wordt met de nieuwe data
        
        else:
            st.sidebar.warning("Geen gegevens gevonden om toe te voegen.")
    elif customer_file:
        handle_file_upload(customer_file)
    else:
        st.sidebar.warning("Voer alstublieft tekst in of upload een bestand.")

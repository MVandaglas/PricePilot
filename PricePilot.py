# GPT Chat functionaliteit

def handle_gpt_chat():
    if customer_input:
        # Verwerk de invoer regel voor regel
        lines = customer_input.splitlines()

        data = []
        for line in lines:
            matched_articles = [(term, synonym_dict[term]) for term in synonym_dict if term in line]

            if matched_articles:
                for term, article_number in matched_articles:
                    description, min_price, max_price = find_article_details(article_number)
                    if description:
                        quantity, width, height = extract_dimensions(line, term)
                        if not quantity:
                            # Gebruik GPT om het ontbrekende aantal te vinden als het niet is herkend
                            try:
                                response = openai.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "Je bent een glas offerte assistent. Analyseer de volgende tekst en geef specifiek het gevraagde aantal terug."},
                                        {"role": "user", "content": line}
                                    ],
                                    max_tokens=50,
                                    temperature=0.9
                                )
                                gpt_output = response['choices'][0]['message']['content'].strip()
                                quantity_match = re.search(r'\d+', gpt_output)
                                if quantity_match:
                                    quantity = quantity_match.group(0)
                                    # Voeg de waarde met een rode kleur toe aan het overzicht
                                    st.sidebar.markdown(f"<span style='color: red;'>GPT vond aantal: {quantity}</span>", unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"Er is een fout opgetreden bij het gebruik van GPT: {str(e)}")

                        if quantity and isinstance(quantity, str) and quantity.endswith('x'):
                            quantity = quantity[:-1].strip()

                        recommended_price = calculate_recommended_price(min_price, max_price, prijsscherpte)
                        m2_per_piece = round(calculate_m2_per_piece(width, height), 2) if calculate_m2_per_piece(width, height) else None
                        m2_total = round(float(quantity) * m2_per_piece, 2) if m2_per_piece and quantity else None
                        data.append([
                            None,  # Placeholder for Offertenummer, to be added later
                            description,
                            article_number,
                            width,
                            height,
                            quantity,
                            f"€ {recommended_price:.2f}" if recommended_price is not None else None,
                            f"{m2_per_piece:.2f} m²" if m2_per_piece is not None else None,
                            f"{m2_total:.2f} m²" if m2_total is not None else None
                        ])
            else:
                try:
                    # Gebruik GPT om te proberen ontbrekende details te vinden
                    line = re.sub(r'(?i)\b(tien|twintig|dertig|veertig|vijftig|zestig|zeventig|tachtig|negentig|honderd) keer\b', lambda x: str(text2num(x.group(1))), line)
                    response = openai.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "Je bent een glas offerte assistent. Analyseer de volgende tekst en geef specifiek het gevraagde aantal terug."},
                                        {"role": "user", "content": line}
                                    ],
                                    max_tokens=50,
                                    temperature=0.9
                                )
                    gpt_output = response['choices'][0]['message']['content'].strip()
                    st.sidebar.markdown(f"<span style='color: red;'>GPT Suggestie: {gpt_output}</span>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Fout bij het aanroepen van de OpenAI API: {str(e)}")

        if data:
            new_df = pd.DataFrame(data, columns=["Offertenummer", "Artikelnaam", "Artikelnummer", "Breedte", "Hoogte", "Aantal", "RSP", "M2 p/s", "M2 totaal"])
            st.session_state.offer_df = pd.concat([st.session_state.offer_df, new_df], ignore_index=True)
        else:
            st.sidebar.warning("Geen gerelateerde artikelen gevonden. Gelieve meer details te geven.")
    elif customer_file:
        handle_file_upload(customer_file)
    else:
        st.sidebar.warning("Voer alstublieft tekst in of upload een bestand.")

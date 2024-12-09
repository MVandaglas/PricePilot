import streamlit as st
import pandas as pd

def delete_selected_rows(df, selected):
    if selected is not None and len(selected) > 0:
        try:
            selected_indices = [int(i) for i in selected if str(i).isdigit()]
            st.write("Geselecteerde indices (na conversie):", selected_indices)

            valid_indices = [i for i in selected_indices if i in df.index]
            st.write("Valide indices voor verwijdering:", valid_indices)

            if valid_indices:
                st.write("DataFrame vóór verwijdering:", df)
                new_df = df.drop(index=valid_indices, errors='ignore').reset_index(drop=True)
                st.write("DataFrame na verwijdering:", new_df)
                return new_df
            else:
                st.warning("Geen valide indices gevonden in geselecteerde rijen.")
                return df
        except Exception as e:
            st.error(f"Fout bij het verwerken van geselecteerde indices: {e}")
            return df
    else:
        st.warning("Geen rijen geselecteerd om te verwijderen.")
        return df

# Voorbeeld DataFrame
df = pd.DataFrame({
    'A': [1, 2, 3, 4],
    'B': [5, 6, 7, 8]
})

st.session_state.offer_df = df
st.session_state.selected_rows = ['0', '2']  # Voorbeeld geselecteerde rijen

if st.button("Verwijder rijen", key='delete_rows_button'):
    st.write("Geselecteerde rijen vóór verwerking (ruwe data):", st.session_state.selected_rows)

    selected = st.session_state.selected_rows
    if selected:
        try:
            selected_indices = [int(r) for r in selected if str(r).isdigit()]
            st.write("Geselecteerde indices (als integers):", selected_indices)
        except ValueError as ve:
            st.error(f"Fout bij converteren van geselecteerde rijen: {ve}")
            selected_indices = []

        st.session_state.offer_df = delete_selected_rows(st.session_state.offer_df, selected_indices)

        if not st.session_state.offer_df.empty:
            st.session_state.offer_df = st.session_state.offer_df.reset_index(drop=True)
        else:
            st.write("DataFrame is nu leeg na verwijdering.")

        st.write("DataFrame na verwerking:", st.session_state.offer_df)
    else:
        st.warning("Geen rijen geselecteerd voor verwijdering.")

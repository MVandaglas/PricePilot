import streamlit as st
import openai
import os
from PIL import Image
import pytesseract

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Streamlit UI setup
st.title("PricePilot - Customer Pricing Assistant")
st.write("This is a tool for generating customer-specific pricing, based on provided inputs.")

# User input area
customer_input = st.text_area("Enter customer request here (email, text, etc.)")
customer_file = st.file_uploader("Or upload a file (e.g., screenshot or document)", type=["png", "jpg", "jpeg", "pdf"])

# Handle GPT Chat functionality
if st.button("Start Chat with GPT"):
    try:
        if customer_input:
            st.session_state.chat_history.append({"role": "user", "content": customer_input})
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.chat_history
            )
            assistant_message = response.choices[0].message['content'].strip()
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
        elif customer_file:
            if customer_file.type.startswith("image"):
                image = Image.open(customer_file)
                st.image(image, caption='Uploaded image', use_column_width=True)
                # Use pytesseract to extract text
                extracted_text = pytesseract.image_to_string(image)
                st.session_state.chat_history.append({"role": "user", "content": extracted_text})
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.chat_history
                )
                assistant_message = response.choices[0].message['content'].strip()
                st.session_state.chat_history.append({"role": "assistant", "content": assistant_message})
            else:
                st.error("File type not supported for processing.")
        else:
            st.warning("Please enter some text or upload a file.")
    except openai.OpenAIError as e:
        st.error(f"An error occurred: {e}")

# Display chat history as it evolves
if st.session_state.chat_history:
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.write(f"You: {chat['content']}")
        else:
            st.write(f"GPT: {chat['content']}")

# Parameters for pricing logic (optional)
if st.checkbox("Show advanced pricing parameters"):
    discount_rate = st.slider("Discount Rate (%)", 0, 100, 10)
    quantity = st.number_input("Quantity", value=1)
    price_sensitivity = st.selectbox("Price Sensitivity Level", ["Low", "Medium", "High"])
    st.write("These parameters can be used to customize the pricing recommendation.")

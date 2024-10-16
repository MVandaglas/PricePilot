import streamlit as st
import openai
import os
from PIL import Image

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Streamlit UI setup
st.title("PricePilot - Customer Pricing Assistant")
st.write("This is a tool for generating customer-specific pricing, based on provided inputs.")

# Chat Functionality with GPT
chat_history = []

# User input area
customer_input = st.text_area("Enter customer request here (email, text, etc.)")
customer_file = st.file_uploader("Or upload a file (e.g., screenshot or document)", type=["png", "jpg", "jpeg", "pdf"])

# Add chat history UI
if st.button("Start Chat with GPT"):
    if customer_input:
        # Use GPT to interpret the customer request
        chat_history.append({"role": "user", "content": customer_input})
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=chat_history
        )
        assistant_message = response['choices'][0]['message']['content']
        chat_history.append({"role": "assistant", "content": assistant_message})
        st.text_area("Chat History", value=assistant_message, height=200)
    elif customer_file:
        if customer_file.type.startswith("image"):
            image = Image.open(customer_file)
            st.image(image, caption='Uploaded image', use_column_width=True)
            # You would need OCR to extract text from the image (e.g., using pytesseract)
            # Here we simulate the extracted text
            extracted_text = "Simulated text extracted from image."
            chat_history.append({"role": "user", "content": extracted_text})
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=chat_history
            )
            assistant_message = response['choices'][0]['message']['content']
            chat_history.append({"role": "assistant", "content": assistant_message})
            st.text_area("Chat History", value=assistant_message, height=200)
        else:
            st.error("File type not supported for processing.")
    else:
        st.warning("Please enter some text or upload a file.")

# Display chat history as it evolves
if chat_history:
    for chat in chat_history:
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
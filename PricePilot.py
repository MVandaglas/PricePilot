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
            model="gpt-3.5-turbo",
            messages=chat_history
        )
        assistant_message = response['choices'][0]['message']['content'].strip()
        chat_history.append({"role": "assistant", "content": assistant_message})
        st.text_area("Chat History", value="\n".join([f"GPT: {assistant_message}" for assistant_message in [m['content'] for m in chat_history if m['role']=='assistant']]), height=200)
    elif customer_file:
        if customer_file.type.startswith("image"):
            image = Image.open(customer

<<<<<<< HEAD
import streamlit as st
from chat_engine import get_ai_response

st.title("🩺 AI Hasta - Doktor Simülasyonu")
st.write("Sorular sorarak hastayı teşhis etmeye çalış.")

# Geçmiş konuşmaları tutmak için
if "chat" not in st.session_state:
    st.session_state.chat = []

# Kullanıcıdan giriş al
user_input = st.text_input("Doktor:", "")

# Gönder butonuna basıldığında
if st.button("Gönder") and user_input:
    ai_response = get_ai_response(user_input)
    st.session_state.chat.append(("👨‍⚕️ Doktor", user_input))
    st.session_state.chat.append(("🧑‍🦰 Hasta", ai_response))

# Sohbet geçmişini yazdır
for role, msg in st.session_state.chat:
    st.write(f"**{role}**: {msg}")
=======
import streamlit as st
from chat_engine import get_ai_response

st.title("🩺 AI Hasta - Doktor Simülasyonu")
st.write("Sorular sorarak hastayı teşhis etmeye çalış.")

if "chat" not in st.session_state:
    st.session_state.chat = []


user_input = st.text_input("Doktor:", "")


if st.button("Gönder") and user_input:
    ai_response = get_ai_response(user_input)
    st.session_state.chat.append(("👨‍⚕️ Doktor", user_input))
    st.session_state.chat.append(("🧑‍🦰 Hasta", ai_response))

for role, msg in st.session_state.chat:
    st.write(f"**{role}**: {msg}")
>>>>>>> 8993cc9e3c664893f4682b73ca8595a122adade4

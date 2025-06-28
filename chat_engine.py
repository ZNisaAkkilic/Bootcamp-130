import streamlit as st
import google.generativeai as genai

# API key yapılandırması
genai.configure(api_key="AIzaSyAnHlwv3Erz5KgbC6gj0kHUENum57a_VRg")  # <== buraya kendi key'ini yaz

# Modeli başlat (beklemeyi tercih ediyorsan bu satır çalışmaz hâlde kalabilir)
model = genai.GenerativeModel("models/gemini-1.5-pro")  # veya hangi modeli istiyorsan

# Başlangıç prompt'u
base_prompt = """
Sen AI destekli bir hasta simülasyonusun.

Kurallar:
- Kendi içinde gizli bir hastalık ve semptom listesi oluştur.
- Bunları baştan söyleme.
- Doktor sana sorular soracak.
- Her cevabında sadece hasta gibi davran.
- "Tanım: ..." yazıldığında doktorun teşhis denemesi başlar.
- O zaman doğru tanıyı açıkla ve eksik soruları geri bildir.

Cevaplarında sadece hasta gibi konuş. Teşhis koyma, açıklama yapma.
"""

# Oturum durumu için başlatıcılar
if "conversation" not in st.session_state:
    st.session_state.conversation = [{"role": "user", "parts": [base_prompt]}]

# Sayfa başlığı
st.markdown("## 🧠 AI Hasta - Doktor Simülasyonu")
st.markdown("Sorular sorarak hastayı teşhis etmeye çalış.")

# Giriş alanı
st.markdown("#### 🩺 Doktor:")
user_input = st.text_input("", placeholder="örnek: miden bulanıyor mu?")

# Gönder butonu
if st.button("Gönder") and user_input.strip() != "":
    # Sohbeti güncelle
    st.session_state.conversation.append({"role": "user", "parts": [user_input]})
    
    try:
        # AI'dan yanıt al
        chat = model.start_chat(history=st.session_state.conversation)
        response = chat.send_message(user_input)
        reply = response.text
    except Exception as e:
        reply = f"⚠️ Hata oluştu: {e}"

    # Yanıtı kaydet
    st.session_state.conversation.append({"role": "model", "parts": [reply]})

# Sohbet geçmişini göster
for msg in st.session_state.conversation:
    if msg["parts"][0] == base_prompt:
        continue
    if msg["role"] == "user":
        st.markdown(f"👨‍⚕️ **Doktor:** {msg['parts'][0]}")
    else:
        st.markdown(f"🧑‍🦰 **Hasta:** {msg['parts'][0]}")

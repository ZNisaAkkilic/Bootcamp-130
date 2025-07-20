import google.generativeai as genai
import streamlit as st
import speech_recognition as sr
import random
import datetime
import json
import os
from PIL import Image

# API Key buraya
genai.configure(api_key="AIzaSyCoGAEwMMsVoSZ2MlQ4qzqLQd3OuHCgKD4") # BURAYI KENDİ API ANAHTARINIZLA DEĞİŞTİRİN

# --- Session State Başlangıç Değerleri (Uygulama Çalışırken Her Zaman Tanımlı Olmalı) ---
if "page" not in st.session_state:
    st.session_state.page = "home"
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "selected_branch_display_name" not in st.session_state:
    st.session_state.selected_branch_display_name = ""
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "tahmin_hakki" not in st.session_state:
    st.session_state.tahmin_hakki = 2
if "system_message" not in st.session_state:
    st.session_state.system_message = ""
if "logs" not in st.session_state:
    st.session_state.logs = []
if "last_branch" not in st.session_state:
    st.session_state.last_branch = st.session_state.selected_branch_display_name

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="AI Doktor Simülatörü",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Model Tanımı ---
try:
    model = genai.GenerativeModel("models/gemini-1.5-flash")
except Exception as e:
    st.error(f"Model yüklenirken bir hata oluştu: {e}")
    st.warning("Lütfen genai.GenerativeModel() içinde doğru model adını kullandığınızdan emin olun.")
    st.stop()

# --- Yardımcı Fonksiyonlar ---
def sesli_komut_al():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Dinleniyor...")
        audio = r.listen(source)
        try:
            text = r.recognize_google(audio, language="tr-TR")
            st.success(f"Tanınan metin: {text}")
            return text
        except sr.UnknownValueError:
            st.error("Ne dediğinizi anlayamadım.")
        except sr.RequestError:
            st.error("Konuşma tanıma servisine ulaşılamadı. İnternet bağlantınızı kontrol edin.")
    return ""

# --- Ana Sayfa (HOME PAGE) Fonksiyonu ---
def home_page():
    st.title("AI Doktor Simülatörü")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        try:
            image_path = "assets/welcome_image.png"
            if os.path.exists(image_path):
                image = Image.open(image_path)
                st.image(image, use_column_width=True)
            else:
                st.markdown("<h1>🩺</h1>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Görsel yüklenirken hata oluştu: {e}. 'assets/welcome_image.png' dosyasının varlığını ve formatını kontrol edin.")
            st.markdown("<h1>🩺</h1>", unsafe_allow_html=True)

    with col2:
        st.subheader("Merhaba!")
        st.markdown("Bu simülatör, tıp öğrencilerinin ve sağlık alanına ilgi duyanların teşhis koyma becerilerini geliştirmeleri için yapay zeka destekli bir sanal hasta sunar. Yapay zeka ile konuşarak semptomları ve hastanın hikayesini öğrenmeli, ardından doğru tanıyı koymalısınız.")

    st.markdown("---")
    st.header("Nasıl Çalışır?")
    st.markdown("""
    1.  *Uzmanlık Alanı Seçin:* Simülasyonun zorluk seviyesini ve konusunu belirlemek için bir uzmanlık alanı seçin.
    2.  *Soru Sorun:* Hastaya semptomları, tıbbi geçmişi ve yaşam tarzı hakkında sorular sorun.
    3.  *Tanı Koyun:* Yeterli bilgi topladığınızı düşündüğünüzde, teşhisinizi "Tanım: [Hastalık Adı]" şeklinde girin.
    4.  *Geribildirim Alın:* Simülatör, tanınızın doğru olup olmadığını size söyleyecektir.
    """)

    st.markdown("---")
    st.warning("Bu simülatör yalnızca eğitim amaçlıdır ve profesyonel tıbbi tavsiye yerine geçmez.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Başlamaya Hazır mısınız?")
    if st.button("🚀 Simülasyonu Başlat", key="home_start_sim_btn"):
        st.session_state.page = "simulation"
        st.rerun()

# --- Simülasyon Sayfası (CHAT PAGE) Fonksiyonu ---
def simulation_page():
    st.markdown("## 👨‍⚕ Doktor Simülasyonu Başladı")
    st.info("🧑‍🔬 *AI Hasta:* Yapay zeka destekli sanal bir hasta sizi bekliyor.\n🎯 *Görev:* Sorular sorarak doğru tanıya ulaşın.\n💡 Not: Hasta doğrudan hastalığını söylemez, siz ipuçlarından tanıyı tahmin etmelisiniz.")
    st.warning("📌 *İpuçları:*\n- Tanı için Tanım: X şeklinde yazın.\n- Sadece *2 tahmin hakkınız* vardır. İyi düşünün!")

    st.markdown("---")
    st.sidebar.markdown("---")
    st.sidebar.header("⚕ Uzmanlık Alanı Seçimi")
    branch_options = [
        "Genel Hekimlik", "Dahiliye", "Kardiyoloji",
        "Nöroloji", "Üroloji", "Kadın Hastalıkları ve Doğum",
        "Ortopedi", "Kulak Burun Boğaz", "Pediatri",
        "Göğüs Hastalıkları", "Dermatoloji"
    ]
    if "selected_branch_display_name" not in st.session_state:
        st.session_state.selected_branch_display_name = branch_options[0]

    try:
        current_branch_index = branch_options.index(st.session_state.selected_branch_display_name)
    except ValueError:
        st.session_state.selected_branch_display_name = branch_options[0]
        current_branch_index = 0

    selected_branch_display_name_new = st.sidebar.selectbox(
        "Lütfen bir uzmanlık alanı seçin",
        branch_options,
        key="branch_select_box",
        index=current_branch_index
    )
    st.sidebar.markdown("---")
    st.sidebar.header("Navigasyon")
    if st.sidebar.button("🏠 Ana Sayfa", key="sidebar_home_btn"):
        st.session_state.page = "home"
        st.rerun()
    if st.sidebar.button("💬 Yeni Simülasyon", key="sidebar_sim_btn"):
        st.session_state.page = "simulation"
        st.rerun()

    if st.session_state.selected_branch_display_name != selected_branch_display_name_new:
        st.session_state.selected_branch_display_name = selected_branch_display_name_new
        
        simulation_rules = (
            "Simülasyon gereği, kan tahlili, röntgen, MR veya diğer fiziksel muayene sonuçları elimizde yok. "
            "Sadece bana verdiğin bilgilere ve benim sana sözlü olarak sunduğum şikayetlere odaklan. "
            "Bu simülasyon, doktor adayının teşhis yeteneğini ve sorgulama becerisini test etmek içindir, "
            "bu yüzden bana somut test sonuçları isteme ve bu yönde konuşma."
        )

        if st.session_state.selected_branch_display_name == "Genel Hekimlik":
            st.session_state.base_prompt = (
                "Merhaba, ben bir hasta simülatörüyüm. Lütfen bana Türkçe olarak sorular sorarak hastalığımı teşhis etmeye çalış. "
                "Simülasyonda tek amacın hastalığı teşhis etmek. Sadece sorularıma yanıt vererek ve benim sana verdiğim "
                "bilgilere göre teşhis koy. Simülasyon kuralları: "
                f"{simulation_rules} "
                "Hazır olduğunda, bana 'Merhaba' de. Sadece hasta rolü oyna ve sana sorulan sorulara kısa ve öz yanıt ver. "
                "İlgili hastalığı söylemekten kaçın, ipuçları ver."
            )
        else:
            st.session_state.base_prompt = (
                f"Merhaba, ben bir hasta simülatörüyüm. {st.session_state.selected_branch_display_name} alanında uzman bir "
                "doktor rolü oynayan birine sorular soracağım. Simülasyonda tek amacın hastalığı teşhis etmek. Sadece sorularıma "
                "yanıt vererek ve benim sana verdiğim bilgilere göre teşhis koy. Simülasyon kuralları: "
                f"{simulation_rules} "
                "Hazır olduğunda, bana 'Merhaba' de. Sadece hasta rolü oyna ve sana sorulan sorulara kısa ve öz yanıt ver. "
                "İlgili hastalığı söylemekten kaçın, ipuçları ver."
            )

        st.session_state.conversation = [{"role": "user", "parts": [st.session_state.base_prompt]}]
        st.session_state.tahmin_hakki = 2
        st.session_state.system_message = ""
        st.session_state.logs = []
        st.session_state.input_text = ""
        st.rerun()

    def handle_send_message():
        """Sohbet gönderme işlemini yürüten yardımcı fonksiyon"""
        if st.session_state.input_text.strip():
            input_to_process = st.session_state.input_text
            st.session_state.input_text = ""

            if input_to_process.lower().startswith("tanım:"):
                tahmin = input_to_process[len("tanım:"):].strip()
                st.session_state.conversation.append({"role": "user", "parts": [f"Tanım: {tahmin}"]})

                with st.spinner("Tanı değerlendiriliyor..."):
                    chat_for_diagnosis = model.start_chat(history=st.session_state.conversation)

                    if st.session_state.tahmin_hakki > 0:
                        st.session_state.tahmin_hakki -= 1

                        if st.session_state.tahmin_hakki == 0:
                            diagnosis_prompt = f"Benim koyduğum teşhis şudur: '{tahmin}'. Bu teşhis doğru mu? Hastalığımın tanısı neydi? Yanıtın 'Doğru teşhis' ile başlamalı veya hastanın gerçek tanısını vermelisin. Tüm detayları ve doğru tanıyı açıklayarak süreci tamamla. Ayrıca, bana yanlış teşhislerimi ve doğru teşhise nasıl ulaşabileceğimi gösterir misin?"
                        else:
                            diagnosis_prompt = f"Benim koyduğum teşhis şudur: '{tahmin}'. Bu teşhis doğru mu? Yanıtın 'Doğru teşhis' veya 'Yanlış teşhis' ile başlamalı. Eğer yanlışsa, bana doğru teşhise yaklaşmam için ipuçları ver."

                        try:
                            diagnosis_response_raw = chat_for_diagnosis.send_message(diagnosis_prompt).text

                            is_correct_diagnosis = diagnosis_response_raw.lower().startswith("doğru teşhis")

                            if "logs" not in st.session_state:
                                st.session_state.logs = []

                            st.session_state.logs.append({
                                "timestamp": str(datetime.datetime.now()),
                                "guess": tahmin,
                                "actual_ai_response": diagnosis_response_raw,
                                "result": "Doğru Teşhis" if is_correct_diagnosis else "Yanlış Teşhis",
                                "branch": st.session_state.selected_branch_display_name,
                                "language": "tr"
                            })

                            if is_correct_diagnosis:
                                st.session_state.system_message = f"*Tebrikler! Doğru Teşhis!*\n\n{diagnosis_response_raw}"
                                st.session_state.tahmin_hakki = 0
                            else:
                                st.session_state.system_message = f"*Yanlış teşhis. Kalan tahmin hakkınız: {st.session_state.tahmin_hakki}*\n\n{diagnosis_response_raw}"
                                if st.session_state.tahmin_hakki == 0:
                                    st.session_state.system_message = f"*Yanlış teşhis. Tahmin hakkınız kalmadı.*\n\n{diagnosis_response_raw}"

                        except Exception as e:
                            st.error(f"Modelden cevap alınırken hata oluştu: {e}")
                            st.session_state.system_message = "Sistem Mesajı: Tanı değerlendirmesi sırasında bir hata oluştu."

                        st.rerun()

                    else:
                        st.session_state.system_message = "Tahmin hakkınız kalmadı."
                        st.rerun()
            else:
                # Normal sohbet işlemi
                st.session_state.conversation.append({"role": "user", "parts": [input_to_process]})

                with st.spinner("Hastanın yanıtı bekleniyor..."):
                    chat = model.start_chat(history=st.session_state.conversation)
                    reply = chat.send_message(input_to_process).text

                st.session_state.conversation.append({"role": "model", "parts": [reply]})
                st.rerun()

    # Sohbet arayüzü
    st.markdown("---")
    chat_display_area = st.container()
    with chat_display_area:
        for message in st.session_state.conversation[1:]:
            if message["role"] == "user":
                st.chat_message("user").write(message["parts"][0])
            elif message["role"] == "model":
                st.chat_message("assistant").write(message["parts"][0])

    if "system_message" in st.session_state and st.session_state.system_message:
        st.info(f"*Sistem Mesajı:*\n\n{st.session_state.system_message}")

    # BUTONLARI VE TEXT_INPUT'I YAN YANA KOYMAK İÇİN YENİ DÜZENLEME
    col_mic, col_input, col_send = st.columns([1, 6, 2])
    
    with col_mic:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎤", help="Sesli komut ile konuş", key="mic_btn"):
            st.session_state.input_text = sesli_komut_al()
            if st.session_state.input_text:
                st.experimental_rerun()
    
    with col_input:
        user_input = st.text_input(
            "Lütfen buraya yazın...",
            value=st.session_state.input_text,
            key="chat_input",
            label_visibility="collapsed"
        )
    
    with col_send:
        with st.form(key="send_form", clear_on_submit=True):
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 Gönder")
            if submitted and user_input.strip():
                st.session_state.input_text = user_input
                handle_send_message()

    st.markdown("---")
    col_buttons = st.columns(3)
    with col_buttons[0]:
        if st.button("Performans Raporu", key="perf_report_btn"):
            if "logs" in st.session_state and st.session_state.logs:
                total = len(st.session_state.logs)
                correct_count = sum(1 for log in st.session_state.logs if log["result"] == "Doğru Teşhis")

                st.info(f"Toplam Tahmin Sayısı: {total}")
                st.info(f"Doğru Tahmin Sayısı: {correct_count} ✅")

                if total > 0:
                    st.success(f"Başarı Oranı: %{100 * correct_count / total:.2f}")
                    st.markdown("### Branşa Göre İstatistikler")
                    branch_stats = {}
                    for log in st.session_state.logs:
                        b = log["branch"]
                        if b not in branch_stats:
                            branch_stats[b] = {"total": 0, "correct": 0}
                        branch_stats[b]["total"] += 1
                        if log["result"] == "Doğru Teşhis":
                            branch_stats[b]["correct"] += 1
                    for b, stat in branch_stats.items():
                        oran = 100 * stat["correct"] / stat["total"] if stat["total"] > 0 else 0
                        st.markdown(f"- *{b}*: {stat['correct']}/{stat['total']} (%{oran:.1f})")
                else:
                    st.warning("Henüz veri yok.")
            else:
                st.warning("Henüz veri yok.")
    with col_buttons[1]:
        if st.button("Logları Kaydet", key="log_save_btn"):
            if "logs" in st.session_state and st.session_state.logs:
                with open("teşhis_loglari.json", "w", encoding="utf-8") as f:
                    json.dump(st.session_state.logs, f, ensure_ascii=False, indent=4)
                st.success("Loglar 'teşhis_loglari.json' dosyasına kaydedildi.")
            else:
                st.warning("Kaydedilecek log bulunamadı.")
    with col_buttons[2]:
        if st.button("Yeni Simülasyon", key="new_sim_btn"):
            st.session_state.clear()
            st.session_state.page = "simulation"
            st.rerun()

# --- Sayfa Yönlendirici ---
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "simulation":
    simulation_page()

# --- FOOTER (Alt Bilgi) ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #6c757d; font-size: 0.85rem;'>AI Doktor Simülatörü - Eğitim Amaçlı Bir Uygulamadır</p>", unsafe_allow_html=True)

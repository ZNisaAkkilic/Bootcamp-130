import google.generativeai as genai
from groq import Groq
import streamlit as st
import speech_recognition as sr
import random
import datetime
import json
import os
from PIL import Image

try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"Groq istemcisi başlatılırken hata oluştu: {e}")
    st.stop()

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
    st.session_state.last_branch = "" # Başlangıçta boş olmalı ki ilk branş seçiminde prompt oluşsun
if "current_language" not in st.session_state:
    st.session_state.current_language = "tr" # Varsayılan dil Türkçe
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False # Varsayılan olarak karanlık mod kapalı
if "is_new_simulation" not in st.session_state:
    st.session_state.is_new_simulation = True # Yeni simülasyonu tetiklemek için flag

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="AI Doktor Simülatörü",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Dil Dosyalarını Yükleme Fonksiyonu ---
@st.cache_data(show_spinner=False)
def load_locales(lang_code):
    try:
        with open(f"locales/{lang_code}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Dil dosyası bulunamadı: locales/{lang_code}.json")
        return {}
    except json.JSONDecodeError:
        st.error(f"Dil dosyası hatalı: locales/{lang_code}.json. Lütfen JSON formatını kontrol edin.")
        return {}

# Mevcut dili yükle
loc = load_locales(st.session_state.current_language)

try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"Groq istemcisi başlatılırken hata oluştu: {e}. Lütfen Streamlit Secrets ayarlarınızı kontrol edin.")
    st.stop()

# --- Yardımcı Fonksiyonlar ---
def sesli_komut_al():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info(loc.get('voice_input_listening', 'Dinleniyor...'))
        audio = r.listen(source)
        try:
            # Ses tanıma için doğru dil kodunu seç
            lang_code = ""
            if st.session_state.current_language == "tr":
                lang_code = "tr-TR"
            elif st.session_state.current_language == "en":
                lang_code = "en-US"
            elif st.session_state.current_language == "ar":
                lang_code = "ar-SA" # Arapça için genel bir kod, bölgeye göre değişebilir
            
            text = r.recognize_google(audio, language=lang_code)
            st.success(f"{loc.get('voice_input_recognized', 'Tanınan metin:')} {text}")
            return text
        except sr.UnknownValueError:
            st.error(loc.get('voice_input_unknown', 'Ne dediğinizi anlayamadım.'))
        except sr.RequestError:
            st.error(loc.get('voice_input_api_error', 'Konuşma tanıma servisine ulaşılamadı. İnternet bağlantınızı kontrol edin.'))
    return ""

# --- Tema (Dark Mode) Ayarları ---
def apply_theme():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {'#1E1E1E' if st.session_state.dark_mode else '#F0F2F6'};
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'};
        }}
        .st-emotion-cache-nahz7x {{ /* Header/Title color */
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'};
        }}
        /* Specific adjustments for chat messages */
        .stChatMessage.st-chat-message-user {{
            background-color: {'#4A4A4A' if st.session_state.dark_mode else '#E6F3FF'}; /* Example user message background */
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'};
        }}
        .stChatMessage.st-chat-message-assistant {{
            background-color: {'#3A3A3A' if st.session_state.dark_mode else '#F0F0F0'}; /* Example assistant message background */
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'};
        }}
        .stAlert {{
            background-color: {'#333333' if st.session_state.dark_mode else '#e7f3ff'};
            color: {'#FFFFFF' if st.session_state.dark_mode else '#0c5460'};
        }}
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown p, .stMarkdown li {{
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'};
        }}
        /* Adjustments for info/warning boxes if needed */
        .st-emotion-cache-1fzhx90.e1f1d6gn4 {{ /* st.info box */
            background-color: {'#333333' if st.session_state.dark_mode else '#e7f3ff'};
            color: {'#FFFFFF' if st.session_state.dark_mode else '#0c5460'};
        }}
        .st-emotion-cache-16p7f6y.e1f1d6gn4 {{ /* st.warning box */
            background-color: {'#333333' if st.session_state.dark_mode else '#fff3cd'};
            color: {'#FFFFFF' if st.session_state.dark_mode else '#856404'};
        }}
        /* Style for the text input in dark mode */
        .stTextInput > div > div > input {{
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'}; /* Text color */
            background-color: {'#444444' if st.session_state.dark_mode else '#FFFFFF'}; /* Background color */
            border: 1px solid {'#666666' if st.session_state.dark_mode else '#CCCCCC'}; /* Border color */
        }}
        /* Style for the send button in dark mode */
        .stButton > button {{
            color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'};
            background-color: {'#555555' if st.session_state.dark_mode else '#E1E1E1'};
            border-color: {'#777777' if st.session_state.dark_mode else '#CCCCCC'};
        }}
        .stButton > button:hover {{
            background-color: {'#777777' if st.session_state.dark_mode else '#D1D1D1'};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Sidebar Ortak Bölüm (Dil ve Tema Seçimi) ---
def render_sidebar_common_sections():
    st.sidebar.markdown("---")
    
    # Dil Seçimi
    st.sidebar.header(loc.get('sidebar_language_selection_title', "Dil Seçimi"))
    language_options = {
        "tr": loc.get('language_turkish', "Türkçe"),
        "en": loc.get('language_english', "İngilizce"),
        "ar": loc.get('language_arabic', "Arapça")
    }
    
    display_languages = list(language_options.values())
    current_lang_display_name = language_options.get(st.session_state.current_language, "Türkçe")
    
    try:
        current_lang_index = display_languages.index(current_lang_display_name)
    except ValueError:
        current_lang_index = 0

    selected_language_display_name = st.sidebar.selectbox(
        loc.get('select_language_label', "Dil Seçimi"),
        options=display_languages,
        index=current_lang_index,
        key="sidebar_language_select_box"
    )

    if selected_language_display_name != current_lang_display_name:
        for code, name in language_options.items():
            if name == selected_language_display_name:
                st.session_state.current_language = code
                st.rerun()
                break
    
    st.sidebar.markdown("---")

    # Tema Seçimi (Karanlık Mod)
    st.sidebar.header(loc.get("home_page_dark_mode_toggle", "Tema Seçimi") if st.session_state.page == "home" else loc.get("chat_page_dark_mode_toggle", "Tema Seçimi"))
    dark_mode_on = st.sidebar.checkbox(
        loc.get('dark_mode_toggle', '🌙 Karanlık Mod'),
        value=st.session_state.dark_mode,
        key="sidebar_dark_mode_checkbox"
    )
    if dark_mode_on != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_on
        st.rerun()

    apply_theme() # Tema ayarlarını uygula
    
# --- Ana Sayfa (HOME PAGE) Fonksiyonu ---
def home_page():
    render_sidebar_common_sections() # Ortak sidebar öğelerini render et
    
    st.title(loc.get("app_title", "AI Doktor Simülatörü"))
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        try:
            image_path = "assets/welcome_image.png.avif"
            if os.path.exists(image_path):
                image = Image.open(image_path)
                st.image(image, use_column_width=True)
            else:
                st.markdown("<h1>🩺</h1>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Görsel yüklenirken hata oluştu: {e}. 'assets/welcome_image.png' dosyasının varlığını ve formatını kontrol edin.")
            st.markdown("<h1>🩺</h1>", unsafe_allow_html=True)

    with col2:
        st.subheader(loc.get("welcome_header", "Merhaba!"))
        st.markdown(loc.get("welcome_text", "Bu simülatör, tıp öğrencilerinin ve sağlık alanına ilgi duyanların teşhis koyma becerilerini geliştirmeleri için yapay zeka destekli bir sanal hasta sunar. Yapay zeka ile konuşarak semptomları ve hastanın hikayesini öğrenmeli, ardından doğru tanıyı koymalısınız."))

    st.markdown("---")
    st.header(loc.get("how_it_works_header", "Nasıl Çalışır?"))
    st.markdown(loc.get("how_it_works_text_1", "1. *Uzmanlık Alanı Seçin:* Simülasyonun zorluk seviyesini ve konusunu belirlemek için bir uzmanlık alanı seçin."))
    st.markdown(loc.get("how_it_works_text_2", "2. *Soru Sorun:* Hastaya semptomları, tıbbi geçmişi ve yaşam tarzı hakkında sorular sorun."))
    st.markdown(loc.get("how_it_works_text_3", "3. *Tanı Koyun:* Yeterli bilgi topladığınızı düşündüğünüzde, teşhisinizi \"Tanım: [Hastalık Adı]\" şeklinde girin."))
    st.markdown(loc.get("how_it_works_text_4", "4. *Geribildirim Alın:* Simülatör, tanınızın doğru olup olmadığını size söyleyecektir."))

    st.markdown("---")
    st.warning(loc.get("disclaimer_text", "Bu simülatör yalnızca eğitim amaçlıdır ve profesyonel tıbbi tavsiye yerine geçmez."))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(loc.get("ready_to_start_header", "### Başlamaya Hazır mısınız?"))
    if st.button(loc.get("start_simulation_button_label_large", "🚀 Simülasyonu Başlat"), key="home_start_sim_btn"):
        st.session_state.page = "simulation"
        st.session_state.is_new_simulation = True # Simülasyon başlarken prompt'u tetikle
        st.rerun()

# --- Simülasyon Sayfası (CHAT PAGE) Fonksiyonu ---
def simulation_page():
    render_sidebar_common_sections() # Ortak sidebar öğelerini render et

    st.sidebar.markdown("---")
    st.sidebar.header(loc.get('sidebar_branch_selection_title', "Uzmanlık Alanı Seçimi"))
    
    branch_keys = [
        "branch_general", "branch_internal_medicine", "branch_cardiology",
        "branch_neurology", "branch_urology", "branch_obgyn",
        "branch_orthopedics", "branch_ent", "branch_pediatrics",
        "branch_pulmonology", "branch_dermatology"
    ]
    branch_options_display = [loc.get(key, key) for key in branch_keys]

    if not st.session_state.selected_branch_display_name or st.session_state.selected_branch_display_name not in branch_options_display:
        st.session_state.selected_branch_display_name = branch_options_display[0]

    try:
        current_branch_index = branch_options_display.index(st.session_state.selected_branch_display_name)
    except ValueError:
        st.session_state.selected_branch_display_name = branch_options_display[0]
        current_branch_index = 0

    selected_branch_display_name_new = st.sidebar.selectbox(
        loc.get('select_branch_placeholder', "Uzmanlık Alanı Seçin"),
        branch_options_display,
        key="branch_select_box",
        index=current_branch_index
    )
    st.sidebar.markdown("---")
    st.sidebar.header(loc.get('sidebar_navigation_header', "Navigasyon"))
    if st.sidebar.button(loc.get('home_button_label', "🏠 Ana Sayfa"), key="sidebar_home_btn"):
        st.session_state.page = "home"
        st.rerun()
    if st.sidebar.button(loc.get('start_simulation_button_label', "💬 Yeni Simülasyon"), key="sidebar_sim_btn"):
        st.session_state.clear() # Tüm session state'i temizle
        st.session_state.page = "simulation"
        st.session_state.is_new_simulation = True # Yeni simülasyonu tetiklemek için flag
        st.rerun()

    # Eğer branş değiştiyse veya yeni simülasyon başlatıldıysa prompt'u sıfırla
    if st.session_state.get("last_branch") != selected_branch_display_name_new or st.session_state.is_new_simulation:
        st.session_state.last_branch = selected_branch_display_name_new
        st.session_state.is_new_simulation = False # Sıfırlama sonrası flag'i resetle
        
        ai_lang_code_for_prompt = ""
        if st.session_state.current_language == "tr":
            ai_lang_code_for_prompt = "Türkçe"
        elif st.session_state.current_language == "en":
            ai_lang_code_for_prompt = "English"
        elif st.session_state.current_language == "ar":
            ai_lang_code_for_prompt = "العربية"
            
        simulation_rules = (
            f"Simülasyon gereği, kan tahlili, röntgen, MR veya diğer fiziksel muayene sonuçları elimizde yok. "
            f"Sadece bana verdiğin bilgilere ve benim sana sözlü olarak sunduğum şikayetlere odaklan. "
            f"Bu simülasyon, doktor adayının teşhis yeteneğini ve sorgulama becerisini test etmek içindir, "
            f"bu yüzden bana somut test sonuçları isteme ve bu yönde konuşma. "
            f"Tüm cevaplarını kesinlikle {ai_lang_code_for_prompt} olarak ver. "
        )

        base_prompt_part1 = loc.get("base_prompt_part1", "Sen AI destekli bir hasta simülasyonusun.")
        base_prompt_part2 = loc.get("base_prompt_part2", "Doktorun dili {AI_LANG}. Tüm cevaplarını **{AI_LANG}** olarak ver.").format(AI_LANG=ai_lang_code_for_prompt)
        base_prompt_part4 = loc.get("base_prompt_part4", "Cevapların kısa ve sade olsun.")
        base_prompt_part5 = loc.get("base_prompt_part5", "Doktor 'Tanım:' veya 'tanım:' ile başlayan bir mesaj gönderirse, bu bir teşhis denemesidir. Bu mesaja **KESİNLİKLE DOĞRUDAN YANIT VERME.** Senin yanıtın, sistem tarafından işlenecek özel bir prompt'a yanıt olarak verilecek ve sistem mesajı olarak gösterilecektir.")
        base_prompt_part6 = loc.get("base_prompt_part6", "Doktor \"Merhaba, şikayetiniz nedir?\" gibi bir soruyla sana başladığında, kendi seçtiğin birincil semptomunu ve şikayetini **{AI_LANG}** olarak açıklayarak sohbeti başlat.").format(AI_LANG=ai_lang_code_for_prompt)
        base_prompt_part7 = loc.get("base_prompt_part7", "Doktor senden tıbbi bir bulgu (röntgen, kan sonuçları, mr, cilt fotoğrafı vb.) isterse, kısaca 'Evet, elimde mevcut.' gibi bir ifadeyle **{AI_LANG}** olarak onay ver ve ek bilgi isteme.").format(AI_LANG=ai_lang_code_for_prompt)

        if selected_branch_display_name_new == loc.get("branch_general", "Genel Hekimlik"):
            base_prompt_part3 = loc.get("base_prompt_part3_general", "Sen herhangi bir branşa ait olabilecek bir hastasın. Kafanda bir hastalık belirle. Bu hastalığı ve semptomlarını doğrudan söyleme. Doktorun sorularına göre cevap ver.")
        else:
            base_prompt_part3 = loc.get("base_prompt_part3_branch", "Sen {branch_name} branşında bir hastasın. Kafanda bu branşa ait bir hastalık belirle. Bu hastalığı ve semptomlarını doğrudan söyleme. Doktorun sorularına göre cevap ver.").format(branch_name=selected_branch_display_name_new)

        st.session_state.base_prompt = "\n".join([
            base_prompt_part1,
            base_prompt_part2,
            base_prompt_part3,
            base_prompt_part4,
            base_prompt_part5,
            base_prompt_part6,
            base_prompt_part7,
            simulation_rules # Sabit kuralları da prompt'a ekle
        ])
        
        st.session_state.conversation = [{"role": "user", "parts": [st.session_state.base_prompt]}]
        st.session_state.tahmin_hakki = 2
        st.session_state.system_message = ""
        st.session_state.logs = []
        st.session_state.input_text = ""
        st.session_state.selected_branch_display_name = selected_branch_display_name_new # Branşı güncelle
        st.rerun()


    st.markdown(f"## {loc.get('app_title', 'AI Doktor Simülatörü')}")
    st.info(f"{loc.get('patient_info', '🧑‍🔬 AI Hasta: Yapay zeka destekli sanal bir hasta sizi bekliyor.')}\n{loc.get('task_info', '🎯 Görev: Sorular sorarak doğru tanıya ulaşın.')}\n{loc.get('hint_info', '💡 Not: Hasta doğrudan hastalığını söylemez, siz ipuçlarından tanıyı tahmin etmelisiniz.')}")
    st.warning(f"{loc.get('tips_title', '📌 İpuçları:')}\n{loc.get('tip_diagnosis_format', '- Tanı için Tanım: X şeklinde yazın.')}\n{loc.get('tip_guess_limit', '- Sadece *2 tahmin hakkınız* vardır. İyi düşünün!')}")

    st.markdown("---")

    def handle_send_message():
        """Sohbet gönderme işlemini yürüten yardımcı fonksiyon (Groq için güncellendi)"""
        if st.session_state.input_text.strip():
            input_to_process = st.session_state.input_text
            st.session_state.input_text = ""

            # Groq'un beklediği {"role": ..., "content": ...} formatına dönüştür.
            def convert_history_for_api(conversation_history):
                messages = []
                for msg in conversation_history:
                    content = msg["parts"][0]
                    role = "assistant" if msg["role"] == "model" else msg["role"]
                    messages.append({"role": role, "content": content})
                return messages

            # Teşhis anahtar kelimelerini kontrol et
            diagnosis_keywords = ["tanım:", "diagnosis:", "تشخيص:"]
            is_diagnosis_attempt = False
            tahmin = ""
            for keyword in diagnosis_keywords:
                if input_to_process.lower().startswith(keyword):
                    tahmin = input_to_process[len(keyword):].strip()
                    is_diagnosis_attempt = True
                    break

            # --- TEŞHİS GİRİŞİMİ MANTIĞI (GROQ İÇİN GÜNCELLENDİ) ---
            if is_diagnosis_attempt:
                st.session_state.conversation.append(
                    {"role": "user", "parts": [f"**{loc.get('doctor_label', 'Doktor')}:** {input_to_process}"]})

                with st.spinner(loc.get('processing_diagnosis', "Tanı değerlendiriliyor...")):
                    if st.session_state.tahmin_hakki > 0:
                        st.session_state.tahmin_hakki -= 1

                        ai_lang_code_for_prompt = st.session_state.current_language
                        prompt_key = "diagnosis_prompt_final" if st.session_state.tahmin_hakki == 0 else "diagnosis_prompt_initial"
                        diagnosis_prompt_text = loc.get(prompt_key, "").format(guess=tahmin,
                                                                               AI_LANG=ai_lang_code_for_prompt)

                        # Mevcut sohbeti ve özel teşhis sorusunu API'ye gönder
                        messages_for_api = convert_history_for_api(st.session_state.conversation)
                        messages_for_api.append({"role": "user", "content": diagnosis_prompt_text})

                        try:
                            chat_completion = groq_client.chat.completions.create(
                                messages=messages_for_api,
                                model="llama3-8b-8192"
                            )
                            diagnosis_response_raw = chat_completion.choices[0].message.content

                            # ... (Loglama ve mesaj gösterme mantığı aynı kalıyor) ...
                            correct_diagnosis_phrase_lower = loc.get("diagnosis_prompt_correct",
                                                                     "Doğru Teşhis!").lower()
                            is_correct_diagnosis = diagnosis_response_raw.lower().startswith(
                                correct_diagnosis_phrase_lower)

                            if "logs" not in st.session_state: st.session_state.logs = []
                            st.session_state.logs.append({
                                "timestamp": str(datetime.datetime.now()), "guess": tahmin,
                                "actual_ai_response": diagnosis_response_raw,
                                "result": "Doğru Teşhis" if is_correct_diagnosis else "Yanlış Teşhis",
                                "branch": st.session_state.selected_branch_display_name,
                                "language": st.session_state.current_language
                            })

                            if is_correct_diagnosis:
                                st.session_state.system_message = f"*{loc.get('diagnosis_correct_congrats', 'Tebrikler! Doğru Teşhis!')}*\n\n{diagnosis_response_raw}"
                                st.session_state.tahmin_hakki = 0
                            else:
                                if st.session_state.tahmin_hakki == 0:
                                    st.session_state.system_message = f"*{loc.get('diagnosis_wrong_no_attempts', 'Yanlış teşhis. Tahmin hakkınız kalmadı.')}*\n\n{diagnosis_response_raw}"
                                else:
                                    st.session_state.system_message = f"*{loc.get('diagnosis_wrong_remaining', 'Yanlış teşhis. Kalan tahmin hakkınız:')} {st.session_state.tahmin_hakki}*\n\n{diagnosis_response_raw}"

                        except Exception as e:
                            st.error(f"Groq API ile tanı değerlendirilirken hata oluştu: {e}")
                            st.session_state.system_message = "Sistem Mesajı: Tanı değerlendirmesi sırasında bir hata oluştu."
                        st.rerun()
                    else:
                        st.session_state.system_message = loc.get('no_more_guesses', "Tahmin hakkınız kalmadı.")
                        st.rerun()

            # --- NORMAL SOHBET MANTIĞI (GROQ İÇİN GÜNCELLENDİ) ---
            else:
                st.session_state.conversation.append(
                    {"role": "user", "parts": [f"**{loc.get('doctor_label', 'Doktor')}:** {input_to_process}"]})

                with st.spinner(loc.get('waiting_for_patient_response', "Hastanın yanıtı bekleniyor...")):
                    messages_for_api = convert_history_for_api(st.session_state.conversation)
                    try:
                        chat_completion = groq_client.chat.completions.create(
                            messages=messages_for_api,
                            model="llama3-70b-8192"
                        )
                        reply = chat_completion.choices[0].message.content
                        st.session_state.conversation.append(
                            {"role": "model", "parts": [f"**{loc.get('patient_label', 'Hasta')}:** {reply}"]})
                    except Exception as e:
                        st.error(f"Groq API'den yanıt alınırken bir hata oluştu: {e}")
                st.rerun()

    st.markdown("---")
    chat_display_area = st.container()
    with chat_display_area:
        for message in st.session_state.conversation[1:]:
            if "user" in message["role"]:
                with st.chat_message("user"):
                    st.write(message["parts"][0])
            elif "model" in message["role"]:
                with st.chat_message("assistant"):
                    st.write(message["parts"][0])

    if "system_message" in st.session_state and st.session_state.system_message:
        st.info(f"*{loc.get('system_message_prefix', 'Sistem Mesajı:')}*\n\n{st.session_state.system_message}")

    col_mic, col_input, col_send = st.columns([1, 6, 2])
    
    with col_mic:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎤", help=loc.get('mic_button_help', "Sesli komut ile konuş"), key="mic_btn"):
            st.session_state.input_text = sesli_komut_al()
            st.rerun()

    with col_input:
        user_input = st.text_input(
            loc.get('user_input_placeholder', "Lütfen buraya yazın..."),
            value=st.session_state.input_text,
            key="chat_input",
            label_visibility="collapsed",
            on_change=lambda: setattr(st.session_state, 'input_text', st.session_state.chat_input)
        )
    
    with col_send:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(loc.get('send_button', "🚀 Gönder"), key="send_message_button"):
            handle_send_message()


    st.markdown("---")
    col_buttons = st.columns(3)
    with col_buttons[0]:
        if st.button(loc.get('performance_report_button', "Performans Raporu"), key="perf_report_btn"):
            if "logs" in st.session_state and st.session_state.logs:
                total = len(st.session_state.logs)
                correct_count = sum(1 for log in st.session_state.logs if log["result"] == "Doğru Teşhis")

                st.info(f"{loc.get('total_guesses', 'Toplam Tahmin Sayısı:')} {total}")
                st.info(f"{loc.get('correct_guesses', 'Doğru Tahmin Sayısı:')} {correct_count} ✅")

                if total > 0:
                    st.success(f"{loc.get('success_rate', 'Başarı Oranı:')} %{100 * correct_count / total:.2f}")
                    st.markdown(f"### {loc.get('branch_statistics', 'Branşa Göre İstatistikler')}")
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
                    st.warning(loc.get('no_data_yet', "Henüz veri yok."))
            else:
                st.warning(loc.get('no_data_yet', "Henüz veri yok."))
    with col_buttons[1]:
        if st.button(loc.get('log_save_button', "Logları Kaydet"), key="log_save_btn"):
            if "logs" in st.session_state and st.session_state.logs:
                try:
                    with open("teşhis_loglari.json", "w", encoding="utf-8") as f:
                        json.dump(st.session_state.logs, f, ensure_ascii=False, indent=4)
                    st.success(loc.get('logs_saved_success', "Loglar 'teşhis_loglari.json' dosyasına kaydedildi."))
                except Exception as e:
                    st.error(f"Log kaydedilirken hata oluştu: {e}")
            else:
                st.warning(loc.get('no_logs_to_save', "Kaydedilecek log bulunamadı."))
    with col_buttons[2]:
        if st.button(loc.get('new_simulation_button_main', "Yeni Simülasyon"), key="new_sim_btn"):
            st.session_state.clear()
            st.session_state.page = "simulation"
            st.session_state.is_new_simulation = True
            st.rerun()

# --- Sayfa Yönlendirici ---
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "simulation":
    simulation_page()

# --- FOOTER (Alt Bilgi) ---
st.markdown("---")
st.markdown(f"<p style='text-align: center; color: #6c757d; font-size: 0.85rem;'>{loc.get('footer_text', 'AI Doktor Simülatörü - Eğitim Amaçlı Bir Uygulamadır')}</p>", unsafe_allow_html=True)

import google.generativeai as genai
import streamlit as st
import speech_recognition as sr
import random
import datetime
import json
import os
from PIL import Image
from groq import Groq

# ==============================================================================
# BÖLÜM 1: API İSTEMCİLERİ VE BAŞLANGIÇ AYARLARI
# ==============================================================================

# Groq istemcisini başlat
try:
    groq_client = Groq(api_key=st.secrets.get("GROQ_API_KEY"))
    GROQ_MODEL_NAME = "llama3-8b-8192"
except Exception as e:
    st.error(f"Groq istemcisi başlatılırken hata oluştu: {e}. Lütfen GROQ_API_KEY'i kontrol edin.")
    st.stop()

# Gemini istemcisini başlat (Yedek olarak hazırda tutuluyor)
try:
    genai.configure(api_key=st.secrets.get("GOOGLE_API_KEY"))
except Exception as e:
    st.warning(f"Gemini istemcisi başlatılırken hata oluştu: {e}. İstemci kullanıma hazır değil.")

# Sayfa yapılandırması
st.set_page_config(
    page_title="AI Hasta Simülatörü/CaseZero",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="expanded"
)


# Session State başlangıç değerlerini tek bir fonksiyonda ayarla
def initialize_session_state():
    """Uygulamanın session state değişkenlerini başlatır."""
    defaults = {
        "page": "home",
        "input_text": "",
        "selected_branch_display_name": "",
        "conversation": [],
        "tahmin_hakki": 2,
        "system_message": "",
        "logs": [],
        "last_branch": "",
        "current_language": "tr",
        "dark_mode": False,
        "is_new_simulation": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()


# Dil dosyalarını yükle
@st.cache_data(show_spinner=False)
def load_locales(lang_code):
    """Dil dosyasını yükler ve önbelleğe alır."""
    try:
        with open(f"locales/{lang_code}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Dil dosyası bulunamadı: locales/{lang_code}.json")
        return {}
    except json.JSONDecodeError:
        st.error(f"Dil dosyası hatalı: locales/{lang_code}.json. Lütfen JSON formatını kontrol edin.")
        return {}


loc = load_locales(st.session_state.current_language)


# ==============================================================================
# BÖLÜM 2: YARDIMCI FONKSİYONLAR
# ==============================================================================

def get_speech_input():
    """Sesli komut ile kullanıcıdan metin alır."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info(loc.get('voice_input_listening', 'Dinleniyor...'))
        audio = r.listen(source)
        try:
            lang_codes = {"tr": "tr-TR", "en": "en-US", "ar": "ar-SA"}
            lang_code = lang_codes.get(st.session_state.current_language, "tr-TR")
            text = r.recognize_google(audio, language=lang_code)
            st.success(f"{loc.get('voice_input_recognized', 'Tanınan metin:')} {text}")
            return text
        except sr.UnknownValueError:
            st.error(loc.get('voice_input_unknown', 'Ne dediğinizi anlayamadım.'))
        except sr.RequestError:
            st.error(loc.get('voice_input_api_error',
                             'Konuşma tanıma servisine ulaşılamadı. İnternet bağlantınızı kontrol edin.'))
    return ""


def render_custom_css():
    """Uygulamaya özel CSS stillerini uygular (dark/light mode)."""
    # Uzun CSS kodunu fonksiyon içine taşıyarak ana kodu temiz tuttuk.
    css_code = f"""
        <style>
        .stApp {{ background-color: {'#121212' if st.session_state.dark_mode else '#F0F2F6'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#333333'}; }}
        h1, h2, h3, h4, h5, h6, .st-emotion-cache-nahz7x {{ color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'}; }}
        .stMarkdown p, .stMarkdown li {{ color: {'#E0E0E0' if st.session_state.dark_mode else '#333333'}; }}
        [data-testid="stSidebarV1"] {{ background-color: {'#1E1E1E !important' if st.session_state.dark_mode else '#FFFFFF !important'}; color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarContent"] {{ background-color: {'#1E1E1E !important' if st.session_state.dark_mode else '#FFFFFF !important'}; color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarV1"] *, [data-testid="stSidebarContent"] * {{ color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarV1"] h1, [data-testid="stSidebarV1"] h2, [data-testid="stSidebarV1"] h3, [data-testid="stSidebarV1"] h4, [data-testid="stSidebarV1"] h5, [data-testid="stSidebarV1"] h6 {{ color: {'#FFFFFF !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarV1"] .stMarkdown label p, [data-testid="stSidebarV1"] label span {{ color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarV1"] .stRadio > label {{ color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarV1"] .stRadio > div[role="radiogroup"] > label > div[data-testid="stConfiguredRFE"] {{ background-color: {'#3A3A3A !important' if st.session_state.dark_mode else 'inherit'}; border-color: {'#555555 !important' if st.session_state.dark_mode else 'inherit'}; }}
        [data-testid="stSidebarV1"] .stRadio > div[role="radiogroup"] > label > div[data-testid="stConfiguredRFE"] > div {{ background-color: {'#66BB6A !important' if st.session_state.dark_mode else 'inherit'}; }}
        [data-testid="stSidebarV1"] .stSelectbox > label {{ color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        [data-testid="stSidebarV1"] .stSelectbox > div > div[data-testid="stSelectbox"] {{ background-color: {'#2A2A2A !important' if st.session_state.dark_mode else '#FFFFFF !important'}; color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; border: 1px solid {'#444444' if st.session_state.dark_mode else '#CCCCCC'}; }}
        .st-emotion-cache-cnbvte {{ background-color: {'#1E1E1E !important' if st.session_state.dark_mode else '#FFFFFF !important'}; }}
        .st-emotion-cache-cnbvte li {{ color: {'#E0E0E0 !important' if st.session_state.dark_mode else '#000000 !important'}; }}
        .st-emotion-cache-cnbvte li:hover {{ background-color: {'#3A3A3A !important' if st.session_state.dark_mode else '#F0F0F0 !important'}; }}
        [data-testid="stSidebarV1"] .st-emotion-cache-gq0y6b {{ background-color: {'#4CAF50 !important' if st.session_state.dark_mode else '#CCCCCC !important'}; }}
        [data-testid="stSidebarV1"] .st-emotion-cache-gq0y6b[data-checked="true"] {{ background-color: {'#66BB6A !important' if st.session_state.dark_mode else '#007bff !important'}; }}
        [data-testid="stSidebarV1"] .stButton > button {{ color: {'#FFFFFF !important' if st.session_state.dark_mode else '#333333 !important'}; background-color: {'#4CAF50 !important' if st.session_state.dark_mode else '#E1E1E1 !important'}; border-color: {'#4CAF50 !important' if st.session_state.dark_mode else '#CCCCCC !important'}; }}
        [data-testid="stSidebarV1"] .stButton > button:hover {{ background-color: {'#66BB6A !important' if st.session_state.dark_mode else '#D1D1D1 !important'}; border-color: {'#66BB6A !important' if st.session_state.dark_mode else '#BBBBBB !important'}; }}
        [data-testid="stSidebarV1"] hr {{ border-top: 1px solid {'#3A3A3A !important' if st.session_state.dark_mode else '#CCCCCC !important'}; }}
        .stChatMessage.st-chat-message-user {{ background-color: {'#2A2A2A' if st.session_state.dark_mode else '#E6F3FF'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#333333'}; }}
        .stChatMessage.st-chat-message-assistant {{ background-color: {'#3A3A3A' if st.session_state.dark_mode else '#F0F0F0'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#333333'}; }}
        .stAlert {{ background-color: {'#1F2937' if st.session_state.dark_mode else '#e7f3ff'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#0c5460'}; border-left: 5px solid {'#4CAF50' if st.session_state.dark_mode else '#28a745'}; }}
        .stAlert.info-alert, .st-emotion-cache-1fzhx90.e1f1d6gn4 {{ background-color: {'#1F2937' if st.session_state.dark_mode else '#e7f3ff'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#0c5460'}; border-left: 5px solid {'#3498DB' if st.session_state.dark_mode else '#007bff'}; }}
        .stAlert.warning-alert, .st-emotion-cache-16p7f6y.e1f1d6gn4 {{ background-color: {'#1F2937' if st.session_state.dark_mode else '#fff3cd'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#856404'}; border-left: 5px solid {'#FFC107' if st.session_state.dark_mode else '#ffc107'}; }}
        .stAlert.error-alert, .st-emotion-cache-10kls2b.e1f1d6gn4 {{ background-color: {'#1F2937' if st.session_state.dark_mode else '#f8d7da'}; color: {'#E0E0E0' if st.session_state.dark_mode else '#721c24'}; border-left: 5px solid {'#E74C3C' if st.session_state.dark_mode else '#dc3545'}; }}
        .stAlert p, .stAlert span, .st-emotion-cache-1fzhx90.e1f1d6gn4 p, .st-emotion-cache-1fzhx90.e1f1d6gn4 span, .st-emotion-cache-16p7f6y.e1f1d6gn4 p, .st-emotion-cache-16p7f6y.e1f1d6gn4 span, .st-emotion-cache-10kls2b.e1f1d6gn4 p, .st-emotion-cache-10kls2b.e1f1d6gn4 span {{ color: {'#E0E0E0 !important' if st.session_state.dark_mode else 'inherit'}; }}
        .stTextInput > div > div > input {{ color: {'#E0E0E0' if st.session_state.dark_mode else '#333333'}; background-color: {'#2A2A2A' if st.session_state.dark_mode else '#FFFFFF'}; border: 1px solid {'#444444' if st.session_state.dark_mode else '#CCCCCC'}; }}
        .stTextInput > div > div > input:focus {{ border-color: {'#66BB6A' if st.session_state.dark_mode else '#66BB6A'}; box-shadow: 0 0 0 0.2rem {'rgba(102, 187, 106, 0.25)' if st.session_state.dark_mode else 'rgba(102, 187, 106, 0.25)'}; }}
        .stButton > button, .stDownloadButton > button {{ color: {'#FFFFFF' if st.session_state.dark_mode else '#333333'}; background-color: {'#4CAF50' if st.session_state.dark_mode else '#E1E1E1'}; border-color: {'#4CAF50' if st.session_state.dark_mode else '#CCCCCC'}; }}
        .stButton > button:hover {{ background-color: {'#66BB6A' if st.session_state.dark_mode else '#D1D1D1'}; border-color: {'#66BB6A' if st.session_state.dark_mode else '#BBBBBB'}; }}
        hr {{ border-top: 1px solid {'#3A3A3A' if st.session_state.dark_mode else '#CCCCCC'}; }}
        </style>
    """
    st.markdown(css_code, unsafe_allow_html=True)


def render_sidebar_common_sections():
    """Sidebar'ın dil ve tema seçimi gibi ortak bölümlerini çizer."""
    st.sidebar.markdown("---")
    st.sidebar.header(loc.get('sidebar_language_selection_title', "Dil Seçimi"))

    language_options = {
        "tr": loc.get('language_turkish', "Türkçe"),
        "en": loc.get('language_english', "İngilizce"),
        "ar": loc.get('language_arabic', "Arapça")
    }
    display_languages = list(language_options.values())
    current_lang_display_name = language_options.get(st.session_state.current_language, "Türkçe")

    current_lang_index = display_languages.index(
        current_lang_display_name) if current_lang_display_name in display_languages else 0
    selected_lang_display_name = st.sidebar.selectbox(
        loc.get('select_language_label', "Dil Seçimi"),
        options=display_languages,
        index=current_lang_index,
        key="sidebar_language_select_box"
    )

    if selected_lang_display_name != current_lang_display_name:
        for code, name in language_options.items():
            if name == selected_lang_display_name:
                st.session_state.current_language = code
                st.rerun()
                break

    st.sidebar.markdown("---")
    st.sidebar.header(loc.get("home_page_dark_mode_toggle", "Tema Seçimi"))
    dark_mode_on = st.sidebar.checkbox(
        loc.get('dark_mode_toggle', '🌙 Karanlık Mod'),
        value=st.session_state.dark_mode,
        key="sidebar_dark_mode_checkbox"
    )
    if dark_mode_on != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode_on
        st.rerun()


def get_base_prompt_for_simulation():
    """Simülasyon için temel prompt metnini oluşturur ve döndürür."""
    ai_lang_code_for_prompt = {"tr": "Türkçe", "en": "English", "ar": "العربية"}.get(
        st.session_state.current_language, "Türkçe")

    simulation_rules = (
        f"Simülasyon gereği, kan tahlili, röntgen, MR veya diğer fiziksel muayene sonuçları elimizde yok. "
        f"Sadece bana verdiğin bilgilere ve benim sana sözlü olarak sunduğum şikayetlere odaklan. "
        f"Bu simülasyon, doktor adayının teşhis yeteneğini ve sorgulama becerisini test etmek içindir, "
        f"bu yüzden bana somut test sonuçları isteme ve bu yönde konuşma. "
        f"Tüm cevaplarını kesinlikle {ai_lang_code_for_prompt} olarak ver. "
    )

    base_prompt_part1 = loc.get("base_prompt_part1", "Sen AI destekli bir hasta simülasyonusun.")
    base_prompt_part2 = loc.get("base_prompt_part2",
                                "Doktorun dili {AI_LANG}. Tüm cevaplarını **{AI_LANG}** olarak ver.").format(
        AI_LANG=ai_lang_code_for_prompt)
    base_prompt_part4 = loc.get("base_prompt_part4", "Cevapların kısa ve sade olsun.")
    base_prompt_part5 = loc.get("base_prompt_part5",
                                "Doktor 'Tanım:' veya 'tanım:' ile başlayan bir mesaj gönderirse, bu bir teşhis denemesidir. Bu mesaja **KESİNLİKLE DOĞRUDAN YANIT VERME.** Senin yanıtın, sistem tarafından işlenecek özel bir prompt'a yanıt olarak verilecek ve sistem mesajı olarak gösterilecektir.")
    base_prompt_part6 = loc.get("base_prompt_part6",
                                "Doktor \"Merhaba, şikayetiniz nedir?\" gibi bir soruyla sana başladığında, kendi seçtiğin birincil semptomunu ve şikayetini **{AI_LANG}** olarak açıklayarak sohbeti başlat.").format(
        AI_LANG=ai_lang_code_for_prompt)
    base_prompt_part7 = loc.get("base_prompt_part7",
                                "Doktor senden tıbbi bir bulgu (röntgen, kan sonuçları, mr, cilt fotoğrafı vb.) isterse, kısaca 'Evet, elimde mevcut.' gibi bir ifadeyle **{AI_LANG}** olarak onay ver ve ek bilgi isteme.").format(
        AI_LANG=ai_lang_code_for_prompt)

    if st.session_state.selected_branch_display_name == loc.get("branch_general", "Genel Hekimlik"):
        base_prompt_part3 = loc.get("base_prompt_part3_general",
                                    "Sen herhangi bir branşa ait olabilecek bir hastasın. Kafanda bir hastalık belirle. Bu hastalığı ve semptomlarını doğrudan söyleme. Doktorun sorularına göre cevap ver.")
    else:
        base_prompt_part3 = loc.get("base_prompt_part3_branch",
                                    "Sen {branch_name} branşında bir hastasın. Kafanda bu branşa ait bir hastalık belirle. Bu hastalığı ve semptomlarını doğrudan söyleme. Doktorun sorularına göre cevap ver.").format(
            branch_name=st.session_state.selected_branch_display_name)

    return "\n".join([
        base_prompt_part1,
        base_prompt_part2,
        base_prompt_part3,
        base_prompt_part4,
        base_prompt_part5,
        base_prompt_part6,
        base_prompt_part7,
        simulation_rules
    ])


def handle_diagnosis_attempt(input_text):
    """Teşhis girişimini yönetir ve Groq API'sini kullanarak yanıt oluşturur."""
    st.session_state.conversation.append({"role": "user", "parts": [input_text]})
    with st.spinner(loc.get('processing_diagnosis', "Tanı değerlendiriliyor...")):
        if st.session_state.tahmin_hakki > 0:
            st.session_state.tahmin_hakki -= 1
            ai_lang_code_for_prompt = st.session_state.current_language

            tahmin = input_text.split(":", 1)[-1].strip()
            prompt_key = "diagnosis_prompt_final" if st.session_state.tahmin_hakki == 0 else "diagnosis_prompt_initial"
            diagnosis_prompt_text = loc.get(prompt_key, "").format(guess=tahmin, AI_LANG=ai_lang_code_for_prompt)

            chat_history_for_groq = [{"role": "user", "content": msg["parts"][0]} for msg in
                                     st.session_state.conversation[1:]]

            try:
                response = groq_client.chat.completions.create(
                    messages=chat_history_for_groq + [{"role": "user", "content": diagnosis_prompt_text}],
                    model=GROQ_MODEL_NAME,
                    temperature=0.5
                )
                diagnosis_response_raw = response.choices[0].message.content
                correct_phrase = loc.get("diagnosis_correct_congrats", "Tebrikler! Doğru Teşhis!").lower()
                is_correct = diagnosis_response_raw.lower().startswith(correct_phrase)

                if is_correct:
                    st.session_state.system_message = f"*{loc.get('diagnosis_correct_congrats', 'Tebrikler! Doğru Teşhis!')}*\n\n{diagnosis_response_raw}"
                    st.session_state.tahmin_hakki = 0
                else:
                    if st.session_state.tahmin_hakki == 0:
                        st.session_state.system_message = f"*{loc.get('diagnosis_wrong_no_attempts', 'Yanlış teşhis. Tahmin hakkınız kalmadı.')}*\n\n{diagnosis_response_raw}"
                    else:
                        st.session_state.system_message = f"*{loc.get('diagnosis_wrong_remaining', 'Yanlış teşhis. Kalan tahmin hakkınız:')} {st.session_state.tahmin_hakki}*"

            except Exception as e:
                st.error(f"Groq API ile tanı değerlendirilirken hata oluştu: {e}")
                st.session_state.system_message = loc.get('system_message_diagnosis_error',
                                                          "Sistem Mesajı: Tanı değerlendirmesi sırasında bir hata oluştu.")
            st.rerun()
        else:
            st.session_state.system_message = loc.get('no_more_guesses', "Tahmin hakkınız kalmadı.")
            st.rerun()


def handle_chat_message(input_text):
    """Normal sohbet mesajını yönetir ve Groq API'sinden yanıt alır."""
    st.session_state.conversation.append({"role": "user", "parts": [input_text]})
    with st.spinner(loc.get('waiting_for_patient_response', "Hastanın yanıtı bekleniyor...")):
        chat_history_for_groq = [{"role": "user", "content": msg["parts"][0]} for msg in st.session_state.conversation]

        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": st.session_state.base_prompt}] + chat_history_for_groq,
                model=GROQ_MODEL_NAME,
                temperature=0.5
            )
            reply = response.choices[0].message.content
            st.session_state.conversation.append({"role": "model", "parts": [reply]})
        except Exception as e:
            st.error(f"Groq API'den yanıt alınırken bir hata oluştu: {e}")
    st.rerun()


def save_logs():
    """Teşhis loglarını JSON dosyasına kaydeder."""
    if "logs" in st.session_state and st.session_state.logs:
        try:
            with open("teşhis_loglari.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state.logs, f, ensure_ascii=False, indent=4)
            st.success(loc.get('logs_saved_success', "Loglar 'teşhis_loglari.json' dosyasına kaydedildi."))
        except Exception as e:
            st.error(f"Log kaydedilirken hata oluştu: {e}")
    else:
        st.warning(loc.get('no_logs_to_save', "Kaydedilecek log bulunamadı."))


def show_performance_report():
    """Kullanıcının performans raporunu gösterir."""
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
                branch_stats.setdefault(b, {"total": 0, "correct": 0})
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


# ==============================================================================
# BÖLÜM 3: SAYFA RENDERLAMA FONKSİYONLARI
# ==============================================================================

def handle_submit():
    """Form gönderimini yönetir ve doğru işleme fonksiyonunu çağırır."""
    user_input = st.session_state.chat_input_key_form
    if user_input.strip():
        # Teşhis anahtar kelimelerini kontrol et
        diagnosis_keywords = ["tanım:", "diagnosis:", "تشخيص:"]
        is_diagnosis_attempt = False
        for keyword in diagnosis_keywords:
            if user_input.lower().startswith(keyword):
                is_diagnosis_attempt = True
                break

        if is_diagnosis_attempt:
            handle_diagnosis_attempt(user_input)
        else:
            handle_chat_message(user_input)


def home_page():
    """Uygulamanın ana sayfasını oluşturur."""
    render_sidebar_common_sections()
    st.title(loc.get("app_title", "AI Hasta Simülatörü/CaseZero"))
    st.markdown("---")

    col1, col2 = st.columns([1, 2])
    with col1:
        try:
            image = Image.open("assets/steteskop.jpg") if os.path.exists("assets/steteskop.jpg") else None
            if image:
                st.image(image, use_container_width=True)
            else:
                st.markdown("<h1>🩺</h1>", unsafe_allow_html=True)
                st.warning(loc.get("image_load_error", "Görsel yüklenirken hata oluştu."))
        except Exception as e:
            st.markdown("<h1>🩺</h1>", unsafe_allow_html=True)
            st.warning(loc.get("image_load_error", f"Görsel yüklenirken hata oluştu: {e}."))

    with col2:
        st.subheader(loc.get("welcome_header", "Merhaba!"))
        st.markdown(loc.get("welcome_text",
                            "Bu simülatör, tıp öğrencilerinin ve sağlık alanına ilgi duyanların teşhis koyma becerilerini geliştirmeleri için yapay zeka destekli bir sanal hasta sunar. Yapay zeka ile konuşarak semptomları ve hastanın hikayesini öğrenmeli, ardından doğru tanıyı koymalısınız."))

    st.markdown("---")
    st.header(loc.get("how_it_works_header", "Nasıl Çalışır?"))
    st.markdown(loc.get("how_it_works_text_1",
                        "1. *Uzmanlık Alanı Seçin:* Simülasyonun zorluk seviyesini ve konusunu belirlemek için bir uzmanlık alanı seçin."))
    st.markdown(loc.get("how_it_works_text_2",
                        "2. *Soru Sorun:* Hastaya semptomları, tıbbi geçmişi ve yaşam tarzı hakkında sorular sorun."))
    st.markdown(loc.get("how_it_works_text_3",
                        "3. *Tanı Koyun:* Yeterli bilgi topladığınızı düşündüğünüzde, teşhisinizi \"Tanım: [Hastalık Adı]\" şeklinde girin."))
    st.markdown(loc.get("how_it_works_text_4",
                        "4. *Geribildirim Alın:* Simülatör, tanınızın doğru olup olmadığını size söyleyecektir."))
    st.markdown("---")
    st.warning(loc.get("disclaimer_text",
                       "Bu simülatör yalnızca eğitim amaçlıdır ve profesyonel tıbbi tavsiye yerine geçmez."))
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(loc.get("ready_to_start_header", "### Başlamaya Hazır mısınız?"))
    if st.button(loc.get("start_simulation_button_label_large", "🚀 Simülasyonu Başlat"), key="home_start_sim_btn"):
        st.session_state.page = "simulation"
        st.session_state.is_new_simulation = True
        st.rerun()


def simulation_page():
    """Uygulamanın sohbet ve simülasyon sayfasını oluşturur."""
    render_sidebar_common_sections()
    st.sidebar.markdown("---")
    st.sidebar.header(loc.get('sidebar_branch_selection_title', "Uzmanlık Alanı Seçimi"))

    branch_keys = ["branch_general", "branch_internal_medicine", "branch_cardiology", "branch_neurology",
                   "branch_urology", "branch_obgyn", "branch_orthopedics", "branch_ent", "branch_pediatrics",
                   "branch_pulmonology", "branch_dermatology"]
    branch_options_display = [loc.get(key, key) for key in branch_keys]

    if st.session_state.selected_branch_display_name not in branch_options_display:
        st.session_state.selected_branch_display_name = branch_options_display[0]

    current_branch_index = branch_options_display.index(
        st.session_state.selected_branch_display_name) if st.session_state.selected_branch_display_name in branch_options_display else 0
    selected_branch_display_name_new = st.sidebar.selectbox(
        loc.get('select_branch_placeholder', "Uzmanlık Alanı Seçin"),
        branch_options_display,
        key="branch_select_box",
        index=current_branch_index
    )

    st.sidebar.markdown("---")
    st.sidebar.header(loc.get('sidebar_navigation_header', "Navigasyon"))
    if st.sidebar.button(loc.get('home_button_label', "🏠 Ana Sayfa"), key="sidebar_home_btn"):
        st.session_state.clear()
        st.session_state.page = "home"
        st.rerun()
    if st.sidebar.button(loc.get('start_simulation_button_label', "💬 Yeni Simülasyon"), key="sidebar_sim_btn"):
        st.session_state.clear()
        st.session_state.page = "simulation"
        st.session_state.is_new_simulation = True
        st.rerun()

    if st.session_state.get("last_branch") != selected_branch_display_name_new or st.session_state.is_new_simulation:
        st.session_state.last_branch = selected_branch_display_name_new
        st.session_state.is_new_simulation = False
        st.session_state.selected_branch_display_name = selected_branch_display_name_new
        st.session_state.base_prompt = get_base_prompt_for_simulation()
        st.session_state.conversation = [{"role": "user", "parts": [st.session_state.base_prompt]}]
        st.session_state.tahmin_hakki = 2
        st.session_state.system_message = ""
        st.session_state.logs = []
        st.session_state.input_text = ""
        st.rerun()

    st.markdown(f"## {loc.get('app_title', 'AI Hasta Simülatörü/CaseZero')}")
    st.info(
        f"{loc.get('patient_info', '🧑‍🔬 AI Hasta: Yapay zeka destekli sanal bir hasta sizi bekliyor.')}\n{loc.get('task_info', '🎯 Görev: Sorular sorarak doğru tanıya ulaşın.')}\n{loc.get('hint_info', '💡 Not: Hasta doğrudan hastalığını söylemez, siz ipuçlarından tanıyı tahmin etmelisiniz.')}")
    st.warning(
        f"{loc.get('tips_title', '📌 İpuçları:')}\n{loc.get('tip_diagnosis_format', '- Tanı için Tanım: X şeklinde yazın.')}\n{loc.get('tip_guess_limit', '- Sadece *2 tahmin hakkınız* vardır. İyi düşünün!')}")
    st.markdown("---")

    for message in st.session_state.conversation[1:]:
        with st.chat_message(message["role"]):
            st.write(message["parts"][0])

    if "system_message" in st.session_state and st.session_state.system_message:
        st.info(f"*{loc.get('system_message_prefix', 'Sistem Mesajı:')}*\n\n{st.session_state.system_message}")

    col_mic, col_form = st.columns([1, 8])
    with col_mic:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎤", help=loc.get('mic_button_help', "Sesli komut ile konuş")):
            st.session_state.input_text = get_speech_input()
            if st.session_state.input_text:
                st.session_state.chat_input_key_form = st.session_state.input_text
                handle_submit()

    with col_form:
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input(loc.get('user_input_placeholder', "Lütfen buraya yazın..."),
                                       value=st.session_state.input_text, key="chat_input_key_form",
                                       label_visibility="collapsed")
            submitted = st.form_submit_button(loc.get('send_button', "🚀 Gönder"))

            if submitted:
                handle_submit()

    st.markdown("---")
    col_buttons = st.columns(3)
    with col_buttons[0]:
        if st.button(loc.get('performance_report_button', "Performans Raporu")):
            show_performance_report()
    with col_buttons[1]:
        if st.button(loc.get('log_save_button', "Logları Kaydet")):
            save_logs()
    with col_buttons[2]:
        if st.button(loc.get('new_simulation_button_main', "Yeni Simülasyon")):
            st.session_state.clear()
            st.session_state.page = "simulation"
            st.session_state.is_new_simulation = True
            st.rerun()
# ==============================================================================
# BÖLÜM 4: ANA YÖNLENDİRİCİ
# ==============================================================================

# Tema ve CSS'i uygula
render_custom_css()

# Sayfa yönlendiricisi
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "simulation":
    simulation_page()

# Footer
st.markdown("---")
st.markdown(
    f"<p style='text-align: center; color: #6c757d; font-size: 0.85rem;'>{loc.get('footer_text', 'AI Doktor Simülatörü - Eğitim Amaçlı Bir Uygulamadır')}</p>",
    unsafe_allow_html=True)
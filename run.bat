@echo off
REM Script bulunduğu klasöre gider
cd /d %~dp0

REM Sanal ortamı etkinleştir
call .venv\Scripts\activate.bat

REM Streamlit uygulamasını çalıştır
streamlit run chat_engine.py

REM İsteğe bağlı olarak komut satırını açık tutmak için pause ekleyebilirsin
pause
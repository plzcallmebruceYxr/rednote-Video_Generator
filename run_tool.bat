@echo off
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install streamlit pillow moviepy edge-tts google-genai numpy --quiet

streamlit run app.py
pause
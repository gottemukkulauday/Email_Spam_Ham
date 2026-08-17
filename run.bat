@echo off
python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r backend\requirements.txt
python backend\app.py

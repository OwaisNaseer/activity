@echo off
echo Starting FastAPI backend server...
cd /d %~dp0
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000


@echo off
REM One-click setup and launch for Brain Gym
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Installing dependencies...
call ".venv\Scripts\activate.bat"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo Starting Brain Gym at http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.
python app.py

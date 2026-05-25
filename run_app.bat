@echo off
setlocal

cd /d "%~dp0"

if not exist app.py (
    echo app.py not found. Please keep this BAT file in the project folder.
    pause
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo Python was not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

python -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Streamlit is not installed. Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies. Please run: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo Starting opinion material classifier...
python -m streamlit run app.py

if errorlevel 1 (
    echo Application exited with an error.
    pause
)

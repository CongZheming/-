@echo off
setlocal

cd /d "%~dp0"

if not exist app.py (
    echo app.py not found. Please keep this BAT file in the project folder.
    pause
    exit /b 1
)

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 was not found. Please install Python 3.12 or update this script.
    pause
    exit /b 1
)

set "PYTHON_CMD=py -3.12"

%PYTHON_CMD% -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Streamlit is not installed. Installing dependencies from requirements.txt...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies. Please run: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo Starting opinion material classifier...
%PYTHON_CMD% -m streamlit run app.py

if errorlevel 1 (
    echo Application exited with an error.
    pause
)

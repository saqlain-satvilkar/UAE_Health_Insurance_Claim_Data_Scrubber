@echo off
TITLE UAE Claim Scrubber Launcher
echo ====================================================
echo   UAE Health Insurance Claim Data Scrubber Launcher
echo   Developer: Saqlain Satvilkar
echo ====================================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or added to PATH.
    pause
    exit /b 1
)
echo [INFO] Installing required libraries...
python -m pip install --upgrade pip
python -m pip install streamlit pandas openpyxl
echo.
echo [INFO] Launching app...
python -m streamlit run app.py
pause
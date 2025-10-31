@echo off
echo ====================================
echo Email Follow-Up Audit Tool
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install -q -r requirements.txt
echo.

REM Check if admin exists
if not exist "data\main.db" (
    echo First time setup detected!
    echo Please create an admin account:
    echo.
    python create_admin.py
    echo.
)

REM Start Streamlit
echo Starting application...
echo.
streamlit run main.py

pause

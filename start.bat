@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.11+ is not installed or not on PATH. Get it from https://www.python.org/downloads/ & pause & exit /b 1)
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv || (echo Could not create venv & pause & exit /b 1)
)
call venv\Scripts\activate.bat
echo Installing requirements (first run takes a few minutes)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q || (echo pip install failed & pause & exit /b 1)
if not exist .env (
  copy .env.example .env >nul
  echo Created .env from .env.example. Paste your API keys into .env, then close this window and run start.bat again. It runs in demo (mock) mode until then.
)
echo.
echo  RRR AI Help Desk is starting at  http://localhost:8000
echo  Press Ctrl+C to stop.
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause

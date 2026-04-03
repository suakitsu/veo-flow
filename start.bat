@echo off
chcp 65001 >nul
echo ========================================
echo Google Veo Video Generator
echo ========================================
echo.

cd /d "%~dp0"

set GCP_PROJECT_ID=YOUR-GCP-PROJECT-ID
set GOOGLE_APPLICATION_CREDENTIALS=%~dp0vertex.json

:: Uncomment and edit the lines below if you need a proxy
:: set HTTP_PROXY=http://127.0.0.1:7897
:: set HTTPS_PROXY=http://127.0.0.1:7897
:: set http_proxy=http://127.0.0.1:7897
:: set https_proxy=http://127.0.0.1:7897

echo Starting server...
echo http://localhost:5000
echo.

python app.py
pause

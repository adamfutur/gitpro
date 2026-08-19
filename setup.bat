@echo off
REM Quick setup script for GitPro

echo ========================================
echo GitPro Setup Wizard
echo ========================================
echo.

REM Check if .env exists
if exist .env (
    echo .env file already exists!
    echo.
    choice /C YN /M "Do you want to recreate it"
    if errorlevel 2 goto :skip_env
)

echo Creating .env file from template...
copy .env.example .env
echo.
echo ========================================
echo IMPORTANT: Edit .env file and add:
echo ========================================
echo 1. GITHUB_CLIENT_ID     - From https://github.com/settings/developers
echo 2. GITHUB_CLIENT_SECRET - From your GitHub OAuth App
echo 3. GEMINI_API_KEY       - From https://makersuite.google.com/app/apikey
echo.
echo See TESTING.md for detailed instructions.
echo.
pause

:skip_env

echo.
echo ========================================
echo Starting Docker Services
echo ========================================
echo.
echo This will take a few minutes on first run...
echo.

docker-compose up --build

echo.
echo Services stopped.
echo.
pause

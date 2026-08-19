@echo off
REM GitPro Backend Test Script for Windows

echo ========================================
echo GitPro Backend Health Check
echo ========================================
echo.

echo Testing API Gateway (Port 8000)...
curl -s http://localhost:8000/health
echo.
echo.

echo Testing Auth Service (Port 8001)...
curl -s http://localhost:8001/health
echo.
echo.

echo Testing Repository Service (Port 8002)...
curl -s http://localhost:8002/health
echo.
echo.

echo Testing AI Service (Port 8003)...
curl -s http://localhost:8003/health
echo.
echo.

echo Testing Chat Service (Port 8004)...
curl -s http://localhost:8004/health
echo.
echo.

echo Testing Webhook Service (Port 8005)...
curl -s http://localhost:8005/health
echo.
echo.

echo ========================================
echo Test Complete!
echo ========================================
echo.
echo If all services returned "healthy", you're good to go!
echo.
echo Next steps:
echo 1. Test OAuth: Open http://localhost:8001/github in your browser
echo 2. See TESTING.md for more detailed tests
echo.
pause

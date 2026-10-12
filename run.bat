@echo off
echo ============================================
echo   Daily Coloring Book Agent - Local Runner
echo ============================================
echo.
cd /d "%~dp0"
python main.py %*
echo.
pause

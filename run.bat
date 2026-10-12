@echo off
echo ============================================
echo   Daily Coloring Book Agent - Local Runner
echo ============================================
echo.
cd /d "%~dp0"
python run_local.py %*
echo.
pause

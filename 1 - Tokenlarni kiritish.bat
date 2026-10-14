@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python topilmadi. Python 3.12 o'rnatilganini tekshiring.
  pause
  exit /b 1
)
python server\tokenlar.py
pause

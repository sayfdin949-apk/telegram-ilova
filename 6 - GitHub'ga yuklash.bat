@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Telegram ilovani GitHub ga yuklash (yopiq repo: sayfdin949-apk/telegram-ilova)
echo  ==========================================================================
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo.
  echo  1. Brauzerda GitHub ochiladi. Nomi va "Private" tayyor turadi -
  echo     pastdagi yashil "Create repository" tugmasini bosing.
  start "" "https://github.com/new?name=telegram-ilova&visibility=private"
  echo  2. Repo yaratilgach shu oynaga qaytib, istalgan tugmani bosing.
  pause >nul
  git remote add origin https://github.com/sayfdin949-apk/telegram-ilova.git
)
echo.
echo  Yuklanmoqda (~200 MB, bir necha daqiqa). GitHub kirish oynasi chiqsa - kiring.
git add -A
git commit -q -m "Yangilash" >nul 2>&1
git push -u origin main
echo.
if errorlevel 1 (echo  XATO: yuqoridagi yozuvni Claude ga korsating.) else (echo  TAYYOR: https://github.com/sayfdin949-apk/telegram-ilova)
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Bu fayl yangi serverga (VPS) shu kompyuterning SSH kalitini qo'shadi.
echo Shundan keyin serverga parolsiz ulaniladi. Parol faqat shu oynada, bir marta kiritiladi.
echo.
if not exist "%USERPROFILE%\.ssh\noon_vps.pub" python tools\deploy.py kalit
set /p IP=Serverning IP manzili (masalan 185.12.34.56):
set USR=root
set /p USR=Foydalanuvchi nomi [root] - shunchaki Enter bosing:
echo.
echo Endi provayder emailga yuborgan parolni kiriting (yozganda ko'rinmaydi, bu normal):
type "%USERPROFILE%\.ssh\noon_vps.pub" | ssh -o StrictHostKeyChecking=accept-new %USR%@%IP% "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo OK"
if errorlevel 1 (
  echo.
  echo Ulanib bo'lmadi. IP va parolni tekshirib, qaytadan urinib ko'ring.
) else (
  echo.
  echo Tayyor: kalit qo'shildi. Endi Claude ga IP manzil va domen nomini yozing. Parolni hech kimga yubormang.
)
pause

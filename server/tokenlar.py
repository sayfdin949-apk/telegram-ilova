"""Bot tokenlarini kiritish: server/.env faylini yozadi. Buni faqat ilova egasi o'zi ishga tushiradi.

Tokenlar ekranda ko'rinmaydi, hech qayerga chiqarilmaydi va logga yozilmaydi.
Har bir token Telegramda tekshiriladi (getMe) va bot nomi (@username) ko'rsatiladi.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402

YES = ("ha", "h", "xa", "yes", "y")


def get_me(token: str):
    """dict - bot topildi; None - Telegram tokenni rad etdi; "tarmoq" - ulanib bo'lmadi."""
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/getMe", headers={"User-Agent": "noon-tokenlar"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d.get("result") if d.get("ok") and isinstance(d.get("result"), dict) else None
    except urllib.error.HTTPError as e:
        return None if e.code in (401, 403, 404) else "tarmoq"
    except Exception:
        return "tarmoq"


def ask_token(label: str):
    for _ in range(3):
        try:
            t = getpass.getpass(f"{label} tokenini qo'ying va Enter bosing (token ekranda ko'rinmaydi): ").strip().strip("\"'").strip()
        except EOFError:
            return None
        if not t:
            print("Hech narsa kiritilmadi.")
            continue
        if not config.TOKEN_RE.match(t):
            print("Token ko'rinishi noto'g'ri. U shunday bo'ladi: 1234567890:AAH...  (raqamlar, ikki nuqta, harflar).")
            continue
        me = get_me(t)
        if me == "tarmoq":
            print("Telegramga ulanib bo'lmadi. Internetni tekshirib, qayta urinib ko'ring.")
            continue
        if not me:
            print("Telegram bu tokenni qabul qilmadi. @BotFather dagi tokenni qaytadan nusxalab qo'ying.")
            continue
        print(f"   Topildi: @{me.get('username')} ({me.get('first_name')})")
        return t, me
    return None


def main() -> int:
    print("Muhammadamin - bot tokenlarini kiritish")
    print("=" * 44)
    print("Kerak bo'ladi: @BotFather da yaratilgan ikki bot tokeni.")
    print("  1) Talabalar boti   (masalan: Muhammadamin darslar)")
    print("  2) Xodimlar boti    (masalan: Muhammadamin boshqaruv)")
    print("Tokenni hech kimga yubormang va hech qayerga yozmang.\n")
    if config.ENV_FILE.exists():
        try:
            ans = input("server\\.env allaqachon bor. Tokenlarni almashtirasizmi? (ha/yo'q): ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in YES:
            print("Hech narsa o'zgarmadi.")
            return 0
    a = ask_token("1) Talabalar boti")
    if not a:
        print("Bekor qilindi. Hech narsa yozilmadi.")
        return 1
    b = ask_token("2) Xodimlar boti")
    if not b:
        print("Bekor qilindi. Hech narsa yozilmadi.")
        return 1
    (t1, me1), (t2, me2) = a, b
    if me1.get("id") == me2.get("id"):
        print("Ikkala token bitta botga tegishli. @BotFather da ikki xil bot yarating. Hech narsa yozilmadi.")
        return 1
    text = ("# Noon Telegram ilova - bot tokenlari. MAXFIY: hech kimga yubormang.\n"
            f"TALABA_BOT_TOKEN={t1}\nXODIM_BOT_TOKEN={t2}\n")
    tmp = config.ENV_FILE.with_name(".env.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, config.ENV_FILE)
    except OSError as e:
        try:
            tmp.unlink()
        except OSError:
            pass
        print(f"server\\.env yozilmadi ({e.__class__.__name__}). Papkaga yozish ruxsatini tekshiring. Hech narsa o'zgarmadi.")
        return 1
    print("\nSaqlandi: server\\.env")
    print(f"  Talabalar boti: @{me1.get('username')}  ->  https://t.me/{me1.get('username')}")
    print(f"  Xodimlar boti:  @{me2.get('username')}  ->  https://t.me/{me2.get('username')}")
    print("\nKeyingi qadam: \"2 - Botlarni ishga tushirish.bat\".")
    print("Agar server hozir ishlab turgan bo'lsa: avval \"3 - Botlarni to'xtatish.bat\", keyin \"2 - ...\".")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nBekor qilindi. Hech narsa yozilmadi.")
        sys.exit(1)

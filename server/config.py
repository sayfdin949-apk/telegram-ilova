"""Noon Telegram ilova - umumiy sozlamalar: yo'llar, port, vaqt mintaqasi, o'yin qoidalari, sinov tokenlari.

Haqiqiy bot tokenlari faqat server/.env da turadi (uni faqat server/tokenlar.py yozadi).
Bu fayldagi SINOV_* tokenlari soxta - faqat sinov rejimi uchun.
"""
from __future__ import annotations

import re
from datetime import time as dtime
from datetime import timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------- yo'llar
ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT / "server"
WEB_DIR = ROOT / "web"
APP_DIR = WEB_DIR / "app"
STAFF_DIR = WEB_DIR / "staff"
ADMIN_DIR = WEB_DIR / "admin"
PANEL_DIR = STAFF_DIR / "p"
SHARED_DIR = WEB_DIR / "shared"
CONTENT_DIR = WEB_DIR / "content"
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "log"
BIN_DIR = SERVER_DIR / "bin"
CLOUDFLARED = BIN_DIR / "cloudflared.exe"
ENV_FILE = SERVER_DIR / ".env"
VIDEOLAR_FILE = SERVER_DIR / "videolar.json"
DB_FILE = DATA_DIR / "noon.db"
HOLAT_FILE = DATA_DIR / "holat.json"
PID_FILE = DATA_DIR / "main.pid"
SECRET_FILE = DATA_DIR / "secret.key"
LOG_FILE = LOG_DIR / "server.log"
PDF_DIR = Path(r"C:\Users\N.M\Desktop\taqdimot\Fonetika kursi (36 dars)\PDF")

# ---------------------------------------------------------------- server
HOST = "127.0.0.1"
PORT = 8790
BREND = "Muhammadamin"
TZ = timezone(timedelta(hours=5))  # Asia/Tashkent = doimiy UTC+05:00 (tzdata kerak emas)
CREATE_NO_WINDOW = 0x08000000

# ---------------------------------------------------------------- tokenlar
SINOV_TALABA_TOKEN = "1111111111:SINOVtalabaAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
SINOV_XODIM_TOKEN = "2222222222:SINOVxodimBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
SINOV_TALABA_USERNAME = "noon_talaba_sinov_bot"
SINOV_XODIM_USERNAME = "noon_xodim_sinov_bot"
TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,60}$")
TOKEN_ANY_RE = re.compile(r"\d{6,12}:[A-Za-z0-9_-]{30,60}")  # loglarda yashirish uchun

# ---------------------------------------------------------------- o'yin qoidalari
KUNLIK_MAQSAD = 30          # ball
XP_SLAYD = 1                # har yangi ko'rilgan slayd
XP_DARS = 20                # dars tugatilganda (bir marta)
XP_VIDEO = 30               # video oxirigacha ko'rilganda (bir marta)
XP_TEST_HAR_BIR = 4         # testdagi har yangi eng yaxshi to'g'ri javob
XP_MUKAMMAL = 10            # birinchi marta hammasi to'g'ri
DARS_TUGATISH_FOIZ = 80     # dars tugatish uchun ko'rilgan slaydlar ulushi (%)
JAMI_DARS_STANDART = 36

# ---------------------------------------------------------------- duellar va do'st taklifi (SPEC 11)
DUEL_SAVOLLAR = 5           # bitta dueldagi savollar
DUEL_MIN_SAVOL = 3          # umumiy savollar shundan kam bo'lsa - "umumiy dars yo'q"
DUEL_SONIYA = 15            # har savolga soniya
DUEL_KECHIKISH = 30         # soniya: 5 x 15 s dan keyin tarmoq uchun qo'shimcha
DUEL_OYNA = DUEL_SAVOLLAR * DUEL_SONIYA + DUEL_KECHIKISH  # start -> finish uchun eng ko'p vaqt (105 s)
DUEL_MS_MAX = 60000         # javobdagi ms qiymatining yuqori chegarasi (validatsiya)
DUEL_MUDDAT = 24 * 3600     # duel yaratilgandan keyin shuncha vaqtda tugamasa - muddati o'tadi
DUEL_TAKLIF_MUDDAT = 24 * 3600   # do'stga yuborilgan duel havolasi (bir martalik)
DUEL_KUNLIK = 10            # har o'quvchi kuniga ko'pi bilan yangi duel (tasodifiy + do'st havolasi)
DUEL_OCHIQ = 3              # tugallanmagan chiquvchi duellar (+ ishlatilmagan havolalar) chegarasi
DUEL_TAKROR = 24 * 3600     # tasodifiy raqib: bir juftlik shuncha vaqtda qayta tanlanmaydi
DUEL_FAOL_KUN = 7           # tasodifiy raqib: oxirgi shuncha kunda kirgan o'quvchilar
DUEL_NOMZOD = 30            # tasodifiy raqib: eng yaqinda faol nomzodlar soni (ko'rib chiqiladi)
DUEL_TANLOV = 5             # ...ulardan eng kam band 5 tasi orasidan tasodifiy tanlanadi
DUEL_MUDDAT_TEKSHIRUV = 3600     # soniya: muddati o'tgan duellarni belgilash vazifasi
XP_DUEL_YUTUQ = 15          # g'olibga
XP_DUEL_DURRANG = 5         # durrangda har ikkalasiga
XP_TAKLIF = 50              # do'st 1-darsni tugatsa - ikkalasiga (bir marta)

# ---------------------------------------------------------------- xavfsizlik va cheklovlar
TALABA_INITDATA_MUDDAT = 7 * 24 * 3600
XODIM_INITDATA_MUDDAT = 24 * 3600
PANEL_TOKEN_MUDDAT = 12 * 3600
TAKLIF_MUDDAT = 48 * 3600
API_BODY_LIMIT = 64 * 1024
EVENT_LIMIT_MIN = 120       # har foydalanuvchiga daqiqasiga voqealar
API_LIMIT_MIN = 300         # har foydalanuvchiga daqiqasiga umumiy so'rovlar
PDF_ORALIQ = 20             # soniya
PDF_KUNLIK = 15
TAKLIF_SOATIGA = 30
TRACK_LIMIT_MIN = 30        # /api/s/track: har foydalanuvchiga daqiqasiga so'rovlar
TRACK_MAX_EVENTS = 100      # /api/s/track: bitta so'rovda ko'pi bilan voqealar
TRACK_SOAT_FARQI = 600      # soniya: mijoz vaqti server vaqtidan shuncha farq qilsa - server vaqti olinadi
FAOL_HOZIR = 300            # soniya: "hozir faol" seans (oxirgi signal shuncha vaqt ichida)
KIRISH_MUDDAT = 600         # /kirish havolasi (soniya), bir martalik
KIRISH_SOATIGA = 20         # /kirish: har xodimga soatiga ko'pi bilan havolalar
COOKIE_NOMI = "noon_admin"
COOKIE_MUDDAT = 12 * 3600   # = PANEL_TOKEN_MUDDAT
CSRF_SARLAVHA = "X-Requested-With"
CSRF_QIYMAT = "noon"

# ---------------------------------------------------------------- bot vazifalari
ESLATMA_VAQTI = dtime(19, 0, tzinfo=TZ)
HISOBOT_VAQTI = dtime(21, 0, tzinfo=TZ)
ESLATMA_FAOL_KUN = 14       # oxirgi marta shuncha kun ichida kirganlarga eslatiladi
XABAR_ORALIQ = 0.05         # ~20 xabar/soniya

# ---------------------------------------------------------------- rollar va panellar
ROLLAR = ("ceo", "admin", "ustoz", "assistent")
TAKLIF_ROLLARI = ("admin", "ustoz", "assistent")
ROL_NOMI = {"ceo": "CEO", "admin": "Admin", "ustoz": "Ustoz", "assistent": "Assistent"}
OCHISH_ROLLARI = ("ceo", "admin")            # 03.10: ustoz ochiq darslarni endi o'zgartira olmaydi
KORISH_ROLLARI = ("ceo", "admin", "ustoz")   # /ochiq (faqat ko'rish), /kirish, admin panel
ADMIN_ROLLARI = ("ceo", "admin", "ustoz")    # admin panelga kira oladiganlar (assistent - yo'q)

# ---------------------------------------------------------------- admin panel bo'limlari (SPEC 10.1)
# kalit -> (nomi, guruh, {rol: "edit" | "read"})
BOLIMLAR = {
    "bosh": ("Bosh sahifa", "Boshqaruv", {"ceo": "edit", "admin": "edit"}),
    "oquvchilar": ("O'quvchilar", "Boshqaruv", {"ceo": "edit", "admin": "edit", "ustoz": "read"}),
    "voronka": ("Voronka", "Boshqaruv", {"ceo": "edit", "admin": "edit"}),
    "tugmalar": ("Tugmalar va ekranlar", "Boshqaruv", {"ceo": "edit", "admin": "edit"}),
    "qurilmalar": ("Qurilmalar", "Boshqaruv", {"ceo": "edit", "admin": "edit"}),
    "kurs": ("Kurs", "O'quv jarayoni", {"ceo": "edit", "admin": "edit", "ustoz": "read"}),
    "testlar": ("Testlar", "O'quv jarayoni", {"ceo": "edit", "admin": "edit", "ustoz": "read"}),
    # 2-bosqich (SPEC 11.5): faqat ko'rish
    "duellar": ("Duellar", "Faollik", {"ceo": "read", "admin": "read"}),
    "takliflar": ("Do'st takliflari", "Faollik", {"ceo": "read", "admin": "read"}),
    "xodimlar": ("Xodimlar", "Tizim", {"ceo": "edit"}),
    "funksiyalar": ("Funksiyalar", "Tizim", {"ceo": "edit"}),
    "jurnal": ("Amallar jurnali", "Tizim", {"ceo": "edit", "admin": "edit"}),
}

# ---------------------------------------------------------------- funksiyalar (SPEC 10.3; tartibli, standart - yoqilgan)
# (kalit, nomi, tavsif, bosqich)
FUNKSIYALAR = (
    ("reyting", "Reyting", "O'quvchilar reytingi (bo'lim va kartalar). O'chirilsa reyting ilovada ko'rinmaydi.", 1),
    ("video", "Video darslar", "Video bo'limi va darslardagi videolar. O'chirilsa videolar ochilmaydi.", 1),
    ("test", "Mini testlar", "Darslardagi \"Mashq\" (mini test). O'chirilsa mashqlar yashiriladi.", 1),
    ("ball", "Ball, seriya va kunlik maqsad", "Ball, seriya va kunlik maqsad ko'rinishi (server baribir hisoblaydi). "
                                              "O'chirilsa Reyting ham yashiriladi.", 1),
    ("uslub", "Manzara tanlash", "O'quvchi Profil bo'limida manzarani (Sahro, Voha, Shahar, Qahva, Xattot, Shom) o'zi "
     "tanlaydi. O'chirilsa tanlash yashiriladi va manzara har ochilganda o'zi almashadi; kunduzgi/tungi rejim qoladi.", 1),
    ("eslatma", "Kunlik eslatma (19:00)", "Talabalar boti har kuni 19:00 da eslatma yuboradi. O'chirilsa ilovaning "
                                          "Profil bo'limidagi eslatma tugmasi ham yashiriladi.", 1),
    ("hisobot", "Kunlik hisobot (21:00)", "Xodimlar boti har kuni 21:00 da CEO larga qisqa hisobot yuboradi.", 1),
    ("duel", "Duellar", "O'quvchilar o'rtasida duel: 5 savol, har biriga 15 soniya; savollar faqat ikkalasi tugatgan "
                        "darslardan. O'chirilsa duel bo'limi yashiriladi va yangi duel boshlanmaydi.", 2),
    ("taklif", "Do'st taklif qilish", "Shaxsiy taklif havolasi: do'st 1-darsni tugatsa ikkalasiga +50 ball. O'chirilsa "
                                      "taklif bo'limi yashiriladi, yangi taklif bog'lanmaydi va bonus berilmaydi.", 2),
    ("qollanma", "Qo'llanma", "Profildagi to'liq qo'llanma va birinchi kirishdagi 2 ta tanishtiruv ekrani. "
     "O'chirilsa ikkalasi ham yashiriladi.", 3),
)
FUNKSIYA_KALITLARI = tuple(k for k, _, _, _ in FUNKSIYALAR)

# ---------------------------------------------------------------- NUQTA ko'rinishi (SPEC 12; kuzatuv - SPEC 10.4)
# talaba ilovasidagi manzaralar (kalit, nomi) - ilova tartibida; mavzu - amalda qo'llangan kunduzgi/tungi
MANZARALAR = (("sahro", "Sahro"), ("voha", "Voha"), ("shahar", "Shahar"), ("qahva", "Qahva"), ("xattot", "Xattot"),
              ("shom", "Shom"))
MANZARA_KALITLARI = tuple(k for k, _ in MANZARALAR)
MAVZULAR = ("kun", "tun")

# kalit -> (fayl, rejim, nomi)
PANELLAR = {
    "ceo": ("CEO_paneli.html", None, "CEO paneli"),
    "admin": ("Admin_paneli.html", None, "Admin paneli"),
    "lms": ("Admin_paneli.html", "lms", "LMS paneli"),
    "ustoz": ("Ustoz_paneli.html", None, "Ustoz paneli"),
    "assistent": ("Ustoz_paneli.html", "assistent", "Assistent paneli"),
}
ROL_PANELLARI = {
    "ceo": ("ceo", "admin", "lms", "ustoz"),
    "admin": ("admin", "lms"),
    "ustoz": ("ustoz", "lms"),
    "assistent": ("assistent",),
}
PANEL_FAYLLARI = frozenset(f for f, _, _ in PANELLAR.values())


def load_env(path: Path = ENV_FILE) -> dict:
    """server/.env ni o'qiydi (KEY=VALUE). Qiymatlar hech qayerga yozilmaydi va chiqarilmaydi."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

"""Admin panel uchun o'zbekcha yorliqlar: talaba ilovasining ekranlari va tugmalari (web/app/app.js).

EKRAN_NOMI - har ekran kaliti (track "screen" voqeasining `n` qiymati);
TUGMA_NOMI - har `data-act` qiymati (track "click" voqeasining `n` qiymati).
Noma'lum kalit -> kalitning o'zi qaytariladi. Yangi tugma/ekran qo'shilsa - shu yerga ham qo'shing
(tools/test_admin_api.py app.js dagi barcha data-act larni tekshiradi).
"""
from __future__ import annotations

EKRAN_NOMI = {
    # pastki menyu
    "bosh": "Bosh sahifa",
    "darslar": "Darslar",
    "video": "Video darslar",
    "reyting": "Reyting",
    "profil": "Profil",
    # ichki ekranlar
    "dars": "Dars (taqdimot)",
    "kitob": "Kitob betlari",
    "player": "Video pleyer",
    "mashq": "Mashq",
    "natija": "Mashq natijasi",
    # oynalar (sheet-<nom>)
    "sheet-vids": "Dars videolari oynasi",
    "sheet-videolar": "Dars videolari oynasi",
    "sheet-done": "Dars tugadi oynasi",
    "sheet-tugadi": "Dars tugadi oynasi",
    "sheet-dars-tugadi": "Dars tugadi oynasi",
    "sheet-lesson-done": "Dars tugadi oynasi",
    "sheet-zoom": "Kattalashtirish oynasi",
    "sheet-hint": "Maslahat oynasi",
    "sheet-lock": "Yopiq dars oynasi",
    # duellar va do'st taklifi (SPEC 11.4)
    "duellar": "Duellar",
    "duel": "Duel (o'yin)",
    "duel-natija": "Duel natijasi",
    "taklif": "Do'stlarni taklif qilish",
    "sheet-duel-yangi": "Yangi duel oynasi",
    "sheet-duel-chiqish": "Dueldan chiqish oynasi",
    # tanishuv (ob-<qadam>)
    "ob-1": "Tanishuv: salomlashish",
    "ob-2": "Tanishuv: uslub tanlash",
    "ob-3": "Tanishuv: rejim tanlash",
    "ob-salom": "Tanishuv: salomlashish",
    "ob-xush": "Tanishuv: salomlashish",
    "ob-uslub": "Tanishuv: uslub tanlash",
    "ob-rejim": "Tanishuv: rejim tanlash",
    "ob-korinish": "Tanishuv: manzara tanlash",        # 05.10 egasi: "Tanishuv: manzara tanlash"
    "ob-qanday": "Tanishuv: qanday o'qiladi",
    "ob-ball": "Tanishuv: ball, duel va do'stlar",
    # qo'llanma (3-bosqich)
    "qollanma": "Qo'llanma",
    # holatlar
    "xato": "Xato ekrani",
    "yuklanmoqda": "Yuklanmoqda",
}

TUGMA_NOMI = {
    "tab": "Bo'lim almashtirish",
    "back": "Orqaga",
    "tg-back": "Orqaga (Telegram tugmasi)",
    "lesson": "Darsni ochish",
    "video": "Videoni ochish",
    "vids": "Dars videolari ro'yxati",
    "sheet-close": "Oynani yopish",
    "sheet-bg": "Oyna tashqarisini bosish",
    "quiz": "Mashqni boshlash",
    "pick": "Javob tanlash",
    "qz-check": "Javobni tekshirish",
    "qz-next": "Keyingi savol",
    "qz-restart": "Mashqni qayta boshlash",
    "qz-retry": "Mashqqa qayta urinish",
    "test-retry": "Mashqni qayta yuklash",
    "vw-prev": "Oldingi slayd",
    "vw-next": "Keyingi slayd",
    "vw-go": "Slaydga o'tish",
    "vw-finish": "Darsni tugatish",
    "vw-zoom": "Kattalashtirish",
    "zm-s": "Kattalashtirish darajasi",
    "zm-close": "Kattalashtirishni yopish",
    "hint-ok": "Maslahatni yopish",
    "dk-prev": "Oldingi slayd",
    "dk-next": "Keyingi slayd",
    "dk-finish": "Darsni tugatish",
    "dk-fs": "To'liq ekran",
    "dk-reload": "Taqdimotni qayta yuklash",
    "kitob": "Kitob betlarini ochish",
    "davr": "Reyting davrini almashtirish",
    "rating-retry": "Reytingni qayta yuklash",
    "set-uslub": "Uslubni o'zgartirish",
    "set-rejim": "Rejimni o'zgartirish",
    "set-arab": "Arabcha matn o'lchami",
    "set-esl": "Kunlik eslatmani yoqish/o'chirish",
    "ob-style": "Uslub tanlash (tanishuv)",
    "ob-mode": "Rejim tanlash (tanishuv)",
    "ob-next": "Keyingi qadam (tanishuv)",
    "ob-done": "Boshlash (tanishuv)",
    "retry": "Qayta urinish",
    # duellar va do'st taklifi (SPEC 11.4)
    "duel-new": "Yangi duel",
    "duel-random": "Tasodifiy raqib bilan duel",
    "duel-friend": "Do'stni duelga chaqirish",
    "duel-open": "Duelni ochish",
    "duel-start": "Duelni boshlash",
    "duel-pick": "Duelda javob tanlash",
    "duel-share": "Duel havolasini ulashish",
    "duel-copy": "Duel havolasini nusxalash",
    "duel-quit": "Dueldan chiqish",
    "duel-retry": "Duelni qayta yuklash",
    "taklif-open": "Do'st taklif qilish bo'limini ochish",
    "taklif-share": "Taklif havolasini ulashish",
    "taklif-copy": "Taklif havolasini nusxalash",
    "taklif-retry": "Taklif bo'limini qayta yuklash",
    # qo'llanma (3-bosqich)
    "qollanma-open": "Qo'llanmani ochish",
    "qollanma-bolim": "Qo'llanma bo'limini ochish/yopish",
    "ob-skip": "Tanishuvni o'tkazib yuborish",
    # NUQTA ko'rinishi (04.10)
    "set-manzara": "Manzarani tanlash",
    "set-aylanish": "Manzara almashinuvini yoqish/o'chirish",
    "qism": "Darslar qismini ochish/yopish",   # Darslar ro'yxatidagi qism (data-n = qism raqami)
}

VOQEA_NOMI = {
    "screen": "Ekran ochildi",
    "click": "Tugma bosildi",
    "end": "Ilovadan chiqdi (fonga o'tdi)",
    "resume": "Ilovaga qaytdi",
}

# tugma qiymatlari (ref) uchun qo'shimcha yorliqlar
QIYMAT_NOMI = {
    "set-rejim": {"light": "Kunduzgi", "dark": "Tungi", "auto": "Avto"},
    "ob-mode": {"light": "Kunduzgi", "dark": "Tungi", "auto": "Avto"},
    "set-uslub": {"game": "O'yinli", "glass": "Shisha"},
    "ob-style": {"game": "O'yinli", "glass": "Shisha"},
    "set-arab": {"m": "O'rta", "l": "Katta"},
    "davr": {"hafta": "Bu hafta", "umumiy": "Umumiy"},
    "set-manzara": {"sahro": "Sahro", "voha": "Voha", "shahar": "Shahar", "qahva": "Qahva", "xattot": "Xattot", "shom": "Shom"},
    "set-aylanish": {"on": "yoqildi", "off": "o'chirildi"},
}

# ref = dars raqami bo'lgan tugmalar (admin panelda "7-dars" deb ko'rsatiladi)
DARS_REF_TUGMALAR = ("lesson", "quiz", "kitob", "vids", "qz-retry")

# Amallar jurnali (audit)
AMAL_NOMI = {
    "open": "Ochiq darslar soni o'zgardi",
    "feature": "Funksiya almashtirildi",
    "invite": "Taklif havolasi yaratildi",
    "staff_remove": "Xodim chiqarildi",
    "kirish": "Admin panelga kirish (brauzer)",
}


def ekran_nomi(key: str | None) -> str:
    if not key:
        return ""
    if key in EKRAN_NOMI:
        return EKRAN_NOMI[key]
    if key.startswith("sheet-"):
        return "Oyna: " + key[6:]
    if key.startswith("ob-"):
        return "Tanishuv: " + key[3:]
    return key


def tugma_nomi(key: str | None, ref: str | None = None) -> str:
    """Tugma yorlig'i; `ref` berilsa - ma'nosi qo'shiladi (masalan "Bo'lim almashtirish: Darslar")."""
    if not key:
        return ""
    base = TUGMA_NOMI.get(key, key)
    if not ref:
        return base
    if key == "tab":
        return f"{base}: {ekran_nomi(ref)}"
    q = QIYMAT_NOMI.get(key, {}).get(ref)
    if q:
        return f"{base}: {q}"
    if key in DARS_REF_TUGMALAR and ref.isdigit():
        return f"{base}: {ref}-dars"
    return base


def qiymat_nomi(key: str | None, ref: str | None) -> str | None:
    """Tugma qiymatining o'zi (masalan set-manzara + sahro -> "Sahro", tab + darslar -> "Darslar"); bo'lmasa None."""
    if not key or not ref:
        return None
    if key == "tab":
        return ekran_nomi(ref)
    q = QIYMAT_NOMI.get(key, {}).get(ref)
    if q:
        return q
    if key in DARS_REF_TUGMALAR and ref.isdigit():
        return f"{ref}-dars"
    return None


def voqea_nomi(kind: str, name: str | None, ref: str | None = None) -> str:
    if kind == "screen":
        return ekran_nomi(name)
    if kind == "click":
        return tugma_nomi(name, ref)
    return VOQEA_NOMI.get(kind, kind)


def amal_matni(action: str, d: dict | None) -> str:
    """Amallar jurnali qatori uchun to'liq o'zbekcha matn."""
    import config
    d = d or {}
    rol = config.ROL_NOMI.get(d.get("role") or "", d.get("role") or "")
    if action == "open":
        if d.get("from") is not None:
            return f"Ochiq darslar soni o'zgardi: {d.get('from')} -> {d.get('to')}"
        return f"Ochiq darslar soni: {d.get('to')}"
    if action == "feature":
        nomi = next((n for k, n, _, _ in config.FUNKSIYALAR if k == d.get("key")), d.get("key") or "")
        holat = "yoqildi" if d.get("on") else "o'chirildi"
        return f"Funksiya {holat}: {nomi}"
    if action == "invite":
        return f"Taklif havolasi yaratildi: {rol}" if rol else "Taklif havolasi yaratildi"
    if action == "staff_remove":
        return f"Xodim chiqarildi: {d.get('name') or d.get('id')}" + (f" ({rol})" if rol else "")
    if action == "kirish":
        return "Admin panelga brauzer orqali kirdi"
    return AMAL_NOMI.get(action, action)

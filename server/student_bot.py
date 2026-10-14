"""Talabalar boti (python-telegram-bot 22.8): /start, /darslar, /video, /yordam, kunlik eslatma, PDF yuborish.

Matnlar va tugma manzillari oddiy funksiyalarda (sinash oson); Telegram bilan ishlash - handlerlarda.
"""
from __future__ import annotations

import asyncio
import logging
import re
import warnings

from telegram import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Update, User,
                      WebAppInfo)
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config
from db import Xato, iso, short_name

log = logging.getLogger("noon.talaba")

TUGMA_OCHISH = "Darslarni ochish"
TUGMA_DAVOM = "Darsni davom ettirish"
TUGMA_VIDEO = "Video darslar"
TUGMA_DUEL = "Duelni ochish"
TUGMA_NATIJA = "Natijani ko'rish"
TUGMA_ILOVA = "Ilovani ochish"
DUEL_KOD_RE = re.compile(r"^[a-z0-9]{10}$")
MENU_MATN = "Darslar"
TABLAR = ("darslar", "video", "reyting", "profil")
XATO_YUBORISH = "Bot sizga xabar yubora olmadi. Botda /start bosing va qayta urinib ko'ring."


# ---------------------------------------------------------------- matnlar va manzillar
def app_url(base: str | None, payload: str = "") -> str | None:
    """{base}/app/ ; payload 'dars8' -> ?dars=8 ; 'video'|'darslar'|'reyting'|'profil' -> ?tab=..."""
    if not base:
        return None
    url = base.rstrip("/") + "/app/"
    p = (payload or "").strip().lower()
    m = re.fullmatch(r"dars(\d{1,3})", p)
    if m and int(m.group(1)) >= 1:
        return f"{url}?dars={int(m.group(1))}"
    if p in TABLAR:
        return f"{url}?tab={p}"
    return url


def start_text(first_name: str | None, brend: str, jami: int) -> str:
    ism = (first_name or "").strip()
    salom = f"Salom, {ism}!" if ism else "Salom!"
    return (f"{salom}\n\n{brend} fonetika kursiga xush kelibsiz. Bu yerda {jami} ta dars slaydlari, "
            f"video darslar va mashqlar bor.\n\nPastdagi tugma orqali darslarni oching.")


def yordam_text(jami: int) -> str:
    return ("Buyruqlar:\n"
            "/darslar - darslar ro'yxati\n"
            "/video - video darslar\n"
            "/yordam - shu yordam\n\n"
            f"Ilovada {jami} ta dars slaydlari, video darslar va mashqlar bor. Ilovani pastdagi \"Darslar\" "
            "tugmasi orqali ham ochish mumkin.\n\n"
            "Darslar ketma-ket ochiladi: avvalgi darsni tugatsangiz, keyingisi ochiladi. "
            "Kunlik eslatmani ilovaning Profil bo'limida yoqish yoki o'chirish mumkin.")


def eslatma_text(streak: int) -> str:
    if streak >= 1:
        return f"Bugungi darsni davom ettiramizmi? Seriyangiz: {streak} kun."
    return "Bugungi darsni davom ettiramizmi? Bugun yangi seriya boshlang."


# --- duellar va do'st taklifi (SPEC 11): tranzaksion xabarlar (eslatma sozlamasidan qat'i nazar yuboriladi)
def duel_url(base: str | None, did: str) -> str | None:
    return f"{base.rstrip('/')}/app/?duel={did}" if base else None


def duel_kod_url(base: str | None, code: str) -> str | None:
    return f"{base.rstrip('/')}/app/?duel_kod={code}" if base else None


def duel_chaqiruv_text(ism: str) -> str:
    return f"{ism} sizni duelga chaqirdi. 24 soat ichida javob bering."


def duel_qabul_text(ism: str) -> str:
    return f"{ism} duelni qabul qildi."


def duel_natija_text(natija: str, my: int | None, their: int | None, raqib: str, xp: int) -> str:
    """natija: 'yutdi' | 'yutqazdi' | 'durrang' (xabar oluvchi nuqtai nazaridan)."""
    hisob = f"{my or 0}:{their or 0}"
    if natija == "yutdi":
        bosh = f"Duel natijasi: siz yutdingiz {hisob}"
    elif natija == "yutqazdi":
        bosh = f"Duel natijasi: siz yutqazdingiz {hisob}"
    else:
        bosh = f"Duel natijasi: durrang {hisob}"
    lines = [bosh, f"Raqib: {raqib}"]
    if xp:
        lines.append(f"Sizga +{xp} ball.")
    return "\n".join(lines)


def duel_taklif_text(ism: str) -> str:
    return (f"Duelga taklif\n\n{ism} sizni fonetika bo'yicha duelga chaqirdi: 5 savol, har biriga 15 soniya. Savollar "
            "ikkalangiz ham tugatgan darslardan olinadi.\n\nQabul qilish uchun pastdagi tugmani bosing.")


DUEL_ESKI_TEXT = "Bu duel taklifi eskirgan yoki allaqachon ishlatilgan. Do'stingizdan yangi havola so'rang."
DUEL_OZI_TEXT = "Bu sizning duel havolangiz. Uni do'stingizga yuboring - u qabul qilganda bot sizga xabar beradi."


def taklif_bonus_text(ism: str, xp: int = config.XP_TAKLIF) -> str:
    return f"Do'stingiz {ism} 1-darsni tugatdi: sizga va unga +{xp} ball."


def description_text(brend: str, jami: int) -> str:
    return (f"{brend} fonetika kursi: {jami} ta dars slaydlari, video darslar, mashqlar, kunlik maqsad va reyting. "
            "Hammasi bitta ilovada.")


def short_description_text(brend: str) -> str:
    return f"{brend} fonetika kursi: darslar, video va mashqlar."


COMMANDS = [("darslar", "Darslar ro'yxati"), ("video", "Video darslar"), ("yordam", "Yordam")]


def markup(label: str, url: str | None) -> InlineKeyboardMarkup | None:
    if not url:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, web_app=WebAppInfo(url=url))]])


def retry_seconds(e: RetryAfter) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ra = e.retry_after
    return float(ra.total_seconds()) if hasattr(ra, "total_seconds") else float(ra)


# ---------------------------------------------------------------- handlerlar
def _svc(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["svc"]


def _user_dict(u: User) -> dict:
    return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "username": u.username,
            "language_code": u.language_code}


def handle_start_payload(svc, uid: int, payload: str, is_new: bool, now) -> tuple[str, str, str | None] | None:
    """/start duel_<kod> va ref_<kod> (SPEC 11.3). (matn, tugma yozuvi, url) - alohida javob kerak bo'lsa; None - oddiy
    salomlashish. Funksiya o'chirilgan bo'lsa parametrlar e'tiborsiz (oddiy salomlashish)."""
    p = (payload or "").strip()
    if p.startswith("ref_"):
        if is_new and svc.store.feature_on("taklif"):
            inviter = svc.store.ref_link(uid, p[4:], now)
            if inviter:
                log.info("taklif: yangi o'quvchi %s -> taklif qilgan %s", uid, inviter)
        return None
    if p.startswith("duel_") and svc.store.feature_on("duel"):
        code = p[5:]
        r = svc.store.duel_invite_get(code) if DUEL_KOD_RE.fullmatch(code) else None
        if r is None or r["used_by"] not in (None, uid) or (r["used_by"] is None and r["expires_at"] <= iso(now)):
            return DUEL_ESKI_TEXT, TUGMA_OCHISH, app_url(svc.base_url)
        if r["from_id"] == uid:
            return DUEL_OZI_TEXT, TUGMA_OCHISH, app_url(svc.base_url)
        ism = short_name(r["first_name"], r["last_name"], r["username"])
        return duel_taklif_text(ism), TUGMA_DUEL, duel_kod_url(svc.base_url, code)
    return None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    u, msg = update.effective_user, update.effective_message
    if not u or not msg:
        return
    now = svc.now()
    is_new = svc.store.upsert_user(_user_dict(u), now, "bot")
    payload = context.args[0] if context.args else ""
    special = handle_start_payload(svc, u.id, payload, is_new, now)
    if special:
        text, label, url = special
        if not url:
            text += "\n\nIlova manzili hozir tayyorlanmoqda. Birozdan keyin /darslar buyrug'ini yuboring."
        await msg.reply_text(text, reply_markup=markup(label, url))
        return
    url = app_url(svc.base_url, payload)
    text = start_text(u.first_name, svc.brend, svc.kurs.jami())
    if not url:
        text += "\n\nIlova manzili hozir tayyorlanmoqda. Birozdan keyin /darslar buyrug'ini yuboring."
    await msg.reply_text(text, reply_markup=markup(TUGMA_OCHISH, url))


async def cmd_darslar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    if update.effective_user:
        svc.store.upsert_user(_user_dict(update.effective_user), svc.now(), "bot")
    url = app_url(svc.base_url, "darslar")
    text = "Darslar ro'yxatini ochish uchun tugmani bosing." if url else "Ilova hozircha ishlamayapti. Birozdan keyin qayta urinib ko'ring."
    await update.effective_message.reply_text(text, reply_markup=markup(TUGMA_OCHISH, url))


async def cmd_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    if update.effective_user:
        svc.store.upsert_user(_user_dict(update.effective_user), svc.now(), "bot")
    url = app_url(svc.base_url, "video")
    text = "Video darslarni ko'rish uchun tugmani bosing." if url else "Ilova hozircha ishlamayapti. Birozdan keyin qayta urinib ko'ring."
    await update.effective_message.reply_text(text, reply_markup=markup(TUGMA_VIDEO, url))


async def cmd_yordam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    await update.effective_message.reply_text(yordam_text(svc.kurs.jami()),
                                              reply_markup=markup(TUGMA_OCHISH, app_url(svc.base_url)))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    url = app_url(svc.base_url)
    text = "Darslarni ochish uchun pastdagi tugmani bosing. Buyruqlar ro'yxati: /yordam"
    await update.effective_message.reply_text(text, reply_markup=markup(TUGMA_OCHISH, url))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, Forbidden):
        return
    log.warning("talaba boti xatosi: %s: %s", err.__class__.__name__, err)


def build(token: str, svc, base_api: str | None = None, base_file: str | None = None) -> Application:
    b = (Application.builder().token(token)
         .connect_timeout(20).read_timeout(30).write_timeout(30).pool_timeout(15).media_write_timeout(300))
    if base_api:
        b = b.base_url(base_api).base_file_url(base_file or base_api)
    app = b.build()
    app.bot_data["svc"] = svc
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", cmd_start, filters=private))
    app.add_handler(CommandHandler("darslar", cmd_darslar, filters=private))
    app.add_handler(CommandHandler("video", cmd_video, filters=private))
    app.add_handler(CommandHandler(["yordam", "help"], cmd_yordam, filters=private))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    return app


# ---------------------------------------------------------------- ishga tushganda
async def set_menu(app: Application, svc) -> bool:
    """"Darslar" menyu tugmasini joriy manzilga ulaydi. True - muvaffaqiyatli."""
    url = app_url(svc.base_url)
    if not url:
        return False
    try:
        await app.bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text=MENU_MATN, web_app=WebAppInfo(url=url)))
        return True
    except TelegramError as e:
        log.warning("talaba boti menyu tugmasi o'rnatilmadi: %s", e.__class__.__name__)
        return False


async def setup_ui(app: Application, svc) -> None:
    bot = app.bot
    jami = svc.kurs.jami()
    steps = [
        ("buyruqlar", lambda: bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])),
        ("tavsif", lambda: bot.set_my_description(description=description_text(svc.brend, jami))),
        ("qisqa tavsif", lambda: bot.set_my_short_description(short_description=short_description_text(svc.brend))),
    ]
    for name, call in steps:
        try:
            await call()
        except TelegramError as e:
            log.warning("talaba boti %s o'rnatilmadi: %s", name, e.__class__.__name__)
    # menyu tugmasini main.sync_menus o'rnatadi (muvaffaqiyatsiz bo'lsa qayta urinadi)


# ---------------------------------------------------------------- PDF
_pdf_locks: dict[int, asyncio.Lock] = {}


async def send_pdf(bot, svc, uid: int, dars: int) -> None:
    """Dars PDF ini o'quvchi chatiga yuboradi. Birinchi yuklashdan keyin file_id bazada saqlanadi."""
    path = svc.kurs.pdf_path(dars)
    if path is None:
        raise Xato(404, "Bu dars uchun PDF topilmadi")
    ls = svc.kurs.lesson(dars) or {}
    caption = f"{dars}-dars. {ls.get('nomi') or ''}".strip()[:1000]
    st = path.stat()
    lock = _pdf_locks.setdefault(dars, asyncio.Lock())
    async with lock:
        row = svc.store.pdf_cache_get(bot.id, dars)
        if row and row["size"] == st.st_size and abs((row["mtime"] or 0) - st.st_mtime) < 1:
            try:
                await bot.send_document(chat_id=uid, document=row["file_id"], caption=caption)
                return
            except Forbidden:
                raise Xato(409, XATO_YUBORISH)
            except BadRequest as e:
                if "chat not found" in str(e).lower():
                    raise Xato(409, XATO_YUBORISH)
                log.warning("PDF kesh yaroqsiz (dars %s): %s", dars, e.__class__.__name__)
                svc.store.pdf_cache_drop(bot.id, dars)
        try:
            with open(path, "rb") as f:
                msg = await bot.send_document(chat_id=uid, document=f, filename=path.name, caption=caption,
                                              write_timeout=300, read_timeout=120)
        except Forbidden:
            raise Xato(409, XATO_YUBORISH)
        except BadRequest as e:
            if "chat not found" in str(e).lower():  # botda hech qachon /start bosmagan
                raise Xato(409, XATO_YUBORISH)
            raise
        if msg and msg.document:
            svc.store.pdf_cache_set(bot.id, dars, msg.document.file_id, st.st_size, st.st_mtime, svc.now())


# ---------------------------------------------------------------- tranzaksion xabarlar (duel, taklif bonusi)
async def notify(bot, svc, uid: int, text: str, label: str | None = None, url: str | None = None) -> bool:
    """Bitta o'quvchiga xabar (web.py fondagi vazifadan chaqiradi). Bloklagan / botni ochmagan o'quvchi - belgilanadi,
    xato chiqarilmaydi. True - yuborildi."""
    for _ in range(2):
        try:
            await bot.send_message(chat_id=uid, text=text, reply_markup=markup(label, url) if label else None)
            return True
        except Forbidden:
            svc.store.mark_blocked(uid)
            return False
        except RetryAfter as e:
            await asyncio.sleep(min(retry_seconds(e) + 1, 30))
        except BadRequest as e:
            if "chat not found" in str(e).lower():
                svc.store.mark_blocked(uid)
            else:
                log.warning("xabar yuborilmadi: %s", e.__class__.__name__)
            return False
        except TelegramError as e:
            log.warning("xabar yuborilmadi: %s", e.__class__.__name__)
            return False
    return False


# ---------------------------------------------------------------- muddati o'tgan duellar (har soat)
async def job_duel_muddat(context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    n = svc.store.duels_expire(svc.now())
    if n:
        log.info("muddati o'tgan duellar belgilandi: %s", n)


# ---------------------------------------------------------------- kunlik eslatma (19:00)
async def job_eslatma(context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    if not svc.store.feature_on("eslatma"):
        log.info("kunlik eslatma o'chirilgan (Funksiyalar)")
        return
    targets = svc.store.reminder_targets(svc.now())
    url = app_url(svc.base_url)
    sent = 0
    for t in targets:
        for _ in range(2):
            try:
                await context.bot.send_message(chat_id=t["id"], text=eslatma_text(t["streak"]),
                                               reply_markup=markup(TUGMA_DAVOM, url))
                sent += 1
                break
            except Forbidden:
                svc.store.mark_blocked(t["id"])
                break
            except RetryAfter as e:
                await asyncio.sleep(retry_seconds(e) + 1)
            except BadRequest as e:
                if "chat not found" in str(e).lower():  # botni hech qachon ishga tushirmagan - xabar yuborib bo'lmaydi
                    svc.store.mark_blocked(t["id"])
                else:
                    log.warning("eslatma yuborilmadi: %s", e.__class__.__name__)
                break
            except TelegramError as e:
                log.warning("eslatma yuborilmadi: %s", e.__class__.__name__)
                break
        await asyncio.sleep(config.XABAR_ORALIQ)
    log.info("kunlik eslatma: %s / %s", sent, len(targets))

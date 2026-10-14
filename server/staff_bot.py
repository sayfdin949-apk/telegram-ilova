"""Xodimlar boti (python-telegram-bot 22.8): ulash kodi, taklif havolalari, /taklif, /xodimlar, /ochiq,
/statistika, /kirish (admin panelga brauzerdan kirish), /yordam, "Boshqaruv" menyu tugmasi (-> /admin/),
har kuni 21:00 da CEO larga qisqa hisobot.

Biznes mantiq handle_* funksiyalarida (Reply qaytaradi) - Telegramsiz sinash mumkin.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

from telegram import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Update, User,
                      WebAppInfo)
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config
from config import ROL_NOMI
from db import full_name

log = logging.getLogger("noon.xodim")

TUGMA = "Boshqaruvni ochish"
TUGMA_KIRISH = "Admin panelni ochish"
MENU_MATN = "Boshqaruv"
COMMANDS = [("start", "Boshqaruvni ochish"), ("statistika", "Qisqa statistika"), ("ochiq", "Ochiq darslar soni"),
            ("kirish", "Admin panelga brauzer orqali kirish"),
            ("taklif", "Xodim taklif qilish (CEO)"), ("xodimlar", "Xodimlar ro'yxati (CEO)"), ("yordam", "Yordam")]
PAIR_LIMIT_USER = 5          # noto'g'ri kod - foydalanuvchiga soatiga
PAIR_LIMIT_ALL = 50          # noto'g'ri kod - hammaga soatiga
ULASH_YORIQ = ("Bot egasi bo'lsangiz: kompyuterdagi \"4 - Holat.bat\" oynasida ko'rsatilgan 6 xonali kodni "
               "shu yerga oddiy xabar qilib yuboring.")


@dataclass
class Reply:
    text: str
    button: tuple[str, str] | None = None       # (yozuv, web_app manzil)
    notify: list[tuple[int, str]] = field(default_factory=list)
    paired: bool = False
    link: tuple[str, str] | None = None         # (yozuv, oddiy URL) - brauzerda ochiladigan tugma (/kirish)


def staff_url(base: str | None) -> str | None:
    """Eski xodimlar Mini App (/staff/) - fayllari saqlanadi, bot endi /admin/ ni ochadi."""
    return base.rstrip("/") + "/staff/" if base else None


def admin_url(base: str | None) -> str | None:
    return base.rstrip("/") + "/admin/" if base else None


def fmt_dt(s: str | None) -> str:
    try:
        d = datetime.fromisoformat(s).astimezone(config.TZ)
    except (TypeError, ValueError):
        return s or ""
    return d.strftime("%d.%m.%Y %H:%M")


def _name(u: dict) -> str:
    return (u.get("first_name") or "").strip() or (u.get("username") or "") or "xodim"


def _begona(svc) -> Reply:
    return Reply(f"Bu bot faqat {svc.brend} xodimlari uchun.")


def _btn(svc) -> tuple[str, str] | None:
    url = admin_url(svc.base_url)
    return (TUGMA, url) if url else None


def _audit(svc, staff_id: int, action: str, detail: dict, now: datetime) -> None:
    try:
        svc.store.audit_add(staff_id, action, detail, now)
    except Exception:
        log.exception("amallar jurnaliga yozilmadi")


def _pair_limited(svc, uid: int) -> bool:
    now = time.monotonic()
    fails = getattr(svc, "_pair_fails", None)
    if fails is None:
        fails = svc._pair_fails = {}
    for k in list(fails):
        fails[k] = [t for t in fails[k] if now - t < 3600]
        if not fails[k]:
            del fails[k]
    total = sum(len(v) for v in fails.values())
    return len(fails.get(uid, [])) >= PAIR_LIMIT_USER or total >= PAIR_LIMIT_ALL


def _pair_fail(svc, uid: int) -> None:
    fails = getattr(svc, "_pair_fails", None)
    if fails is None:
        fails = svc._pair_fails = {}
    fails.setdefault(uid, []).append(time.monotonic())


# ---------------------------------------------------------------- mantiq
def handle_pair(svc, u: dict, code: str, now: datetime) -> Reply:
    if _pair_limited(svc, u["id"]):
        return Reply("Urinishlar juda ko'p. Bir soatdan keyin qayta urinib ko'ring.")
    res = svc.store.pair_ceo(u, code, now)
    if res == "ok":
        log.info("CEO ulandi: %s", u["id"])
        return Reply(f"Salom, {_name(u)}! Siz CEO sifatida ulandingiz.\n\n"
                     "Xodimlarni taklif qilish: /taklif admin, /taklif ustoz yoki /taklif assistent.\n"
                     "Boshqa buyruqlar: /yordam", button=_btn(svc), paired=True)
    if res == "band":
        return _begona(svc)
    _pair_fail(svc, u["id"])
    return Reply("Kod noto'g'ri. Kompyuterdagi \"4 - Holat.bat\" oynasida ko'rsatilgan 6 xonali kodni yuboring.")


def handle_redeem(svc, u: dict, code: str, now: datetime) -> Reply:
    role, err = svc.store.invite_redeem(code, u, now)
    if err == "ceo":
        return Reply("Siz allaqachon CEO siz. Taklif havolasi ishlatilmadi.", button=_btn(svc))
    if err:
        return Reply("Taklif havolasi yaroqsiz yoki muddati tugagan. CEO dan yangi havola so'rang.")
    log.info("taklif ishlatildi: %s -> %s", u["id"], role)
    who = full_name(u.get("first_name"), u.get("last_name"), u.get("username"))
    if u.get("username"):
        who += f" (@{u['username']})"
    notify = [(r["id"], f"Yangi xodim qo'shildi: {who} - {ROL_NOMI[role]}.")
              for r in svc.store.staff_by_role("ceo") if r["id"] != u["id"]]
    return Reply(f"Salom, {_name(u)}! Siz {svc.brend} jamoasiga qo'shildingiz. Rolingiz: {ROL_NOMI[role]}.\n\n"
                 "Boshqaruvni pastdagi tugma yoki \"Boshqaruv\" menyusi orqali oching. Buyruqlar: /yordam",
                 button=_btn(svc), notify=notify)


def handle_start(svc, u: dict, arg: str, now: datetime) -> Reply:
    arg = (arg or "").strip()
    if arg.startswith("t_"):
        return handle_redeem(svc, u, arg[2:], now)
    row = svc.store.staff_get(u["id"])
    if row is None and re.fullmatch(r"\d{6}", arg) and svc.store.get_setting("ulash_kodi"):
        return handle_pair(svc, u, arg, now)
    if row is None:
        if svc.store.get_setting("ulash_kodi") and svc.store.staff_count() == 0:
            # hali hech kim ulanmagan: egasiga keyingi qadamni aytamiz (kodning o'zi bu yerda ko'rsatilmaydi)
            return Reply(f"Bu bot faqat {svc.brend} xodimlari uchun.\n\n" + ULASH_YORIQ)
        return _begona(svc)
    text = f"Salom, {_name(u)}! Rolingiz: {ROL_NOMI[row['role']]}."
    if not svc.base_url:
        text += "\n\nBoshqaruv manzili hozir tayyorlanmoqda. Birozdan keyin /start yuboring."
    return Reply(text, button=_btn(svc))


def handle_text(svc, u: dict, text: str, now: datetime) -> Reply:
    t = (text or "").strip()
    row = svc.store.staff_get(u["id"])
    if row is None:
        if re.fullmatch(r"\d{6}", t) and svc.store.get_setting("ulash_kodi"):
            return handle_pair(svc, u, t, now)
        if svc.store.get_setting("ulash_kodi") and svc.store.staff_count() == 0:
            return Reply(f"Bu bot faqat {svc.brend} xodimlari uchun.\n\n" + ULASH_YORIQ)
        return _begona(svc)
    return Reply("Buyruqlar ro'yxati: /yordam", button=_btn(svc))


def handle_taklif(svc, u: dict, args: list[str], now: datetime) -> Reply:
    row = svc.store.staff_get(u["id"])
    if row is None:
        return _begona(svc)
    if row["role"] != "ceo":
        return Reply("Bu buyruq faqat CEO uchun.")
    role = (args[0] if args else "").strip().lower()
    if role not in config.TAKLIF_ROLLARI:
        return Reply("Foydalanish: /taklif admin, /taklif ustoz yoki /taklif assistent")
    if not svc.xodim_username:
        return Reply("Bot hali to'liq ishga tushmagan. Birozdan keyin qayta urinib ko'ring.")
    if svc.store.invites_recent(u["id"], now) >= config.TAKLIF_SOATIGA:
        return Reply("Juda ko'p taklif yaratildi. Birozdan keyin qayta urinib ko'ring.")
    code, exp = svc.store.invite_create(role, u["id"], now)
    _audit(svc, u["id"], "invite", {"role": role, "expires": exp, "via": "bot"}, now)
    link = f"https://t.me/{svc.xodim_username}?start=t_{code}"
    return Reply(f"{ROL_NOMI[role]} uchun taklif havolasi:\n{link}\n\n"
                 f"Havola bir marta ishlaydi va {fmt_dt(exp)} gacha amal qiladi. "
                 "Uni faqat taklif qilinayotgan odamga yuboring.")


def handle_xodimlar(svc, u: dict) -> Reply:
    row = svc.store.staff_get(u["id"])
    if row is None:
        return _begona(svc)
    if row["role"] != "ceo":
        return Reply("Bu buyruq faqat CEO uchun.")
    rows = svc.store.staff_list()
    lines = []
    for i, r in enumerate(rows, 1):
        s = f"{i}. {full_name(r['first_name'], r['last_name'], r['username'])}"
        if r["username"]:
            s += f" (@{r['username']})"
        lines.append(f"{s} - {ROL_NOMI[r['role']]}")
    return Reply(f"Xodimlar ({len(rows)}):\n" + "\n".join(lines) +
                 "\n\nXodimni o'chirish: Boshqaruv ilovasidagi \"Xodimlar\" bo'limi.", button=_btn(svc))


def handle_ochiq(svc, u: dict, args: list[str], now: datetime | None = None) -> Reply:
    row = svc.store.staff_get(u["id"])
    if row is None:
        return _begona(svc)
    if row["role"] not in config.KORISH_ROLLARI:
        return Reply("Bu buyruq siz uchun emas.")
    jami = svc.kurs.jami()
    cur = svc.store.course_open(jami)
    can_set = row["role"] in config.OCHISH_ROLLARI
    if not args:
        if can_set:
            return Reply(f"Ochiq darslar: {cur} / {jami}.\nO'zgartirish: /ochiq 12 (1 dan {jami} gacha)")
        return Reply(f"Ochiq darslar: {cur} / {jami}.")
    if not can_set:
        return Reply("Ochiq darslar sonini faqat CEO yoki admin o'zgartira oladi.")
    a = args[0].strip()
    if not a.isdigit() or not 1 <= int(a) <= jami:
        return Reply(f"Foydalanish: /ochiq 12 (1 dan {jami} gacha)")
    n = int(a)
    svc.store.set_course_open(n)
    if n != cur:
        _audit(svc, u["id"], "open", {"from": cur, "to": n, "via": "bot"}, now or svc.now())
    log.info("ochiq darslar: %s (xodim %s, bot)", n, u["id"])
    return Reply(f"Saqlandi. Ochiq darslar: {n} / {jami}. O'quvchilar 1-{n}-darslarni ko'ra oladi.")


def handle_kirish(svc, u: dict, now: datetime) -> Reply:
    """Admin panelga brauzer orqali kirish: bir martalik, 10 daqiqalik havola (tugmada; matnda havola yo'q -
    Telegram havola ko'rinishini oldindan ochib, kodni "ishlatib qo'ymasin")."""
    row = svc.store.staff_get(u["id"])
    if row is None:
        return _begona(svc)
    if row["role"] not in config.ADMIN_ROLLARI:
        return Reply("Admin panel hozircha CEO, admin va ustoz uchun ochiq.")
    base = (svc.base_url or "").rstrip("/")
    if not base:
        return Reply("Admin panel manzili hozir tayyorlanmoqda. Birozdan keyin /kirish yuboring.")
    if svc.store.login_recent(u["id"], now) >= config.KIRISH_SOATIGA:
        return Reply("Juda ko'p kirish havolasi so'raldi. Birozdan keyin qayta urinib ko'ring.")
    code, _ = svc.store.login_create(u["id"], now)
    mins = config.KIRISH_MUDDAT // 60
    return Reply("Admin panelga kirish havolasi tayyor. Pastdagi tugmani bosing - panel brauzerda ochiladi.\n\n"
                 f"Tugma {mins} daqiqa ichida faqat bir marta ishlaydi. Uni boshqalarga yubormang.",
                 link=(TUGMA_KIRISH, f"{base}/admin/kirish?k={code}"))


def stats_text(svc, now: datetime) -> str:
    s = svc.store.staff_stats(now, svc.kurs.lesson_of_video)
    jami = svc.kurs.jami()
    return (f"Statistika ({now.astimezone(config.TZ).strftime('%d.%m.%Y %H:%M')}):\n"
            f"O'quvchilar: {s['students']}\n"
            f"Bugun faol: {s['active_today']}\n"
            f"7 kunda faol: {s['active_7d']}\n"
            f"Yangi (7 kun): {s['new_7d']}\n"
            f"Tugatilgan darslar: {s['lessons_done']}\n"
            f"Ko'rilgan videolar: {s['videos_done']}\n"
            f"Topshirilgan testlar: {s['tests_done']}\n"
            f"O'rtacha ball: {s['avg_xp']}\n"
            f"Ochiq darslar: {svc.store.course_open(jami)} / {jami}")


def handle_statistika(svc, u: dict, now: datetime) -> Reply:
    if svc.store.staff_get(u["id"]) is None:
        return _begona(svc)
    return Reply(stats_text(svc, now), button=_btn(svc))


def handle_yordam(svc, u: dict) -> Reply:
    row = svc.store.staff_get(u["id"])
    if row is None:
        return _begona(svc)
    lines = ["Buyruqlar:", "/start - boshqaruvni ochish", "/statistika - qisqa statistika"]
    if row["role"] in config.OCHISH_ROLLARI:
        lines.append("/ochiq - ochiq darslar soni (o'zgartirish: /ochiq 12)")
    elif row["role"] in config.KORISH_ROLLARI:
        lines.append("/ochiq - ochiq darslar soni")
    if row["role"] in config.ADMIN_ROLLARI:
        lines.append("/kirish - admin panelni kompyuter brauzerida ochish (bir martalik havola)")
    if row["role"] == "ceo":
        lines.append("/taklif admin | ustoz | assistent - xodim uchun taklif havolasi")
        lines.append("/xodimlar - xodimlar ro'yxati")
    lines.append("/yordam - shu yordam")
    return Reply("\n".join(lines), button=_btn(svc))


def summary_text(svc, now: datetime) -> str:
    s = svc.store.daily_summary(now)
    return (f"Kunlik hisobot ({now.astimezone(config.TZ).strftime('%d.%m.%Y')}):\n"
            f"Yangi o'quvchilar: {s['new']}\n"
            f"Bugun faol: {s['active']}\n"
            f"Bugun tugatilgan darslar: {s['lessons_done']}\n"
            f"Jami o'quvchilar: {s['students']}")


# ---------------------------------------------------------------- Telegram handlerlari
def _svc(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data["svc"]


def _user_dict(u: User) -> dict:
    return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "username": u.username}


def markup(button: tuple[str, str] | None, link: tuple[str, str] | None = None) -> InlineKeyboardMarkup | None:
    if link:
        return InlineKeyboardMarkup([[InlineKeyboardButton(link[0], url=link[1])]])
    if not button:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(button[0], web_app=WebAppInfo(url=button[1]))]])


async def _answer(update: Update, context: ContextTypes.DEFAULT_TYPE, reply: Reply) -> None:
    svc = _svc(context)
    await update.effective_message.reply_text(reply.text, reply_markup=markup(reply.button, reply.link))
    for chat_id, text in reply.notify:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except TelegramError as e:
            log.warning("xabarnoma yuborilmadi: %s", e.__class__.__name__)
    if reply.paired and getattr(svc, "on_paired", None):
        try:
            svc.on_paired()
        except Exception:
            log.exception("on_paired")


def _touch(svc, u: dict) -> None:
    row = svc.store.staff_get(u["id"])
    if row and ((u.get("first_name") or "") != row["first_name"] or (u.get("last_name") or "") != row["last_name"]
                or (u.get("username") or None) != row["username"]):
        svc.store.staff_update_names(u)


def _wrap(fn):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user or not update.effective_message:
            return
        svc = _svc(context)
        u = _user_dict(update.effective_user)
        _touch(svc, u)
        reply = fn(svc, u, update, context)
        if reply is not None:
            await _answer(update, context, reply)
    return handler


cmd_start = _wrap(lambda svc, u, up, ctx: handle_start(svc, u, ctx.args[0] if ctx.args else "", svc.now()))
cmd_taklif = _wrap(lambda svc, u, up, ctx: handle_taklif(svc, u, ctx.args or [], svc.now()))
cmd_xodimlar = _wrap(lambda svc, u, up, ctx: handle_xodimlar(svc, u))
cmd_ochiq = _wrap(lambda svc, u, up, ctx: handle_ochiq(svc, u, ctx.args or [], svc.now()))
cmd_kirish = _wrap(lambda svc, u, up, ctx: handle_kirish(svc, u, svc.now()))
cmd_statistika = _wrap(lambda svc, u, up, ctx: handle_statistika(svc, u, svc.now()))
cmd_yordam = _wrap(lambda svc, u, up, ctx: handle_yordam(svc, u))
on_text = _wrap(lambda svc, u, up, ctx: handle_text(svc, u, up.effective_message.text or "", svc.now()))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if isinstance(err, Forbidden):
        return
    log.warning("xodim boti xatosi: %s: %s", err.__class__.__name__, err)


def build(token: str, svc, base_api: str | None = None, base_file: str | None = None) -> Application:
    b = Application.builder().token(token).connect_timeout(20).read_timeout(30).write_timeout(30).pool_timeout(15)
    if base_api:
        b = b.base_url(base_api).base_file_url(base_file or base_api)
    app = b.build()
    app.bot_data["svc"] = svc
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", cmd_start, filters=private))
    app.add_handler(CommandHandler("taklif", cmd_taklif, filters=private))
    app.add_handler(CommandHandler("xodimlar", cmd_xodimlar, filters=private))
    app.add_handler(CommandHandler("ochiq", cmd_ochiq, filters=private))
    app.add_handler(CommandHandler("kirish", cmd_kirish, filters=private))
    app.add_handler(CommandHandler("statistika", cmd_statistika, filters=private))
    app.add_handler(CommandHandler(["yordam", "help"], cmd_yordam, filters=private))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    return app


async def set_menu(app: Application, svc) -> bool:
    """"Boshqaruv" menyu tugmasini joriy manzildagi admin panelga (/admin/) ulaydi. True - muvaffaqiyatli."""
    url = admin_url(svc.base_url)
    if not url:
        return False
    try:
        await app.bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text=MENU_MATN, web_app=WebAppInfo(url=url)))
        return True
    except TelegramError as e:
        log.warning("xodim boti menyu tugmasi o'rnatilmadi: %s", e.__class__.__name__)
        return False


async def setup_ui(app: Application, svc) -> None:
    bot = app.bot
    steps = [
        ("buyruqlar", lambda: bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])),
        ("tavsif", lambda: bot.set_my_description(
            description=f"{svc.brend} xodimlari uchun boshqaruv boti: o'quvchilar statistikasi, kurs nazorati va admin panel.")),
        ("qisqa tavsif", lambda: bot.set_my_short_description(short_description=f"{svc.brend} xodimlari uchun boshqaruv.")),
    ]
    for name, call in steps:
        try:
            await call()
        except TelegramError as e:
            log.warning("xodim boti %s o'rnatilmadi: %s", name, e.__class__.__name__)
    # menyu tugmasini main.sync_menus o'rnatadi (muvaffaqiyatsiz bo'lsa qayta urinadi)


async def job_hisobot(context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = _svc(context)
    if not svc.store.feature_on("hisobot"):
        log.info("kunlik hisobot o'chirilgan (Funksiyalar)")
        return
    text = summary_text(svc, svc.now())
    url = admin_url(svc.base_url)
    for r in svc.store.staff_by_role("ceo"):
        for _ in range(2):
            try:
                await context.bot.send_message(chat_id=r["id"], text=text, reply_markup=markup((TUGMA, url) if url else None))
                break
            except Forbidden:
                break
            except RetryAfter as e:
                from student_bot import retry_seconds
                await asyncio.sleep(retry_seconds(e) + 1)
            except TelegramError as e:
                log.warning("kunlik hisobot yuborilmadi: %s", e.__class__.__name__)
                break
        await asyncio.sleep(config.XABAR_ORALIQ)

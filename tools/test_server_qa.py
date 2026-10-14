"""Mustaqil QA sinovlari (qa-server agenti): test_server.py dagi asosiy sinovlarni to'ldiradi.

    python tools/test_server.py --faqat qa        (o'z sinov serverini 8796-portda ishga tushiradi va to'xtatadi)

Tekshiriladi:
  - initData tafsilotlari (kelajakdagi auth_date, takroriy kalit, signature maydoni, user turi, buzuq qiymatlar)
  - har bir xodim API marshrutida rol tekshiruvi (rol x marshrut jadvali), X-Staff-Token, o'chirilgan xodim,
    xodim API tezlik cheklovi, 64 KB chegara xodim API da ham
  - kunlik vazifalar (19:00 eslatma, 21:00 hisobot) - callback lar soxta bot/soat/baza bilan to'g'ridan-to'g'ri
  - send_pdf: kesh, "chat not found" -> 409, Forbidden -> 409
  - tokenlar.py: tarmoq xatosi, EOF, qo'shtirnoqli token, .env.tmp qolmasligi
  - main.py .env siz: stderr da tushunarli o'zbekcha xabar; ikkinchi nusxa log fayliga tegmaydi
  - jarayon: ishchi server to'xtatilganda sinov serverlariga tegilmaydi
  - tunnel.stop: tashqi bekor qilish yutib yuborilmaydi; 409 ogohlantirishi o'z-o'zidan o'chadi
"""
from __future__ import annotations

import asyncio
import builtins
import contextlib
import getpass
import io
import json
import subprocess
import sys
import tempfile
import time
import types
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import auth  # noqa: E402
import config  # noqa: E402
import db as dbm  # noqa: E402
from sinov_initdata import SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN, TALABA, make  # noqa: E402

TZ = config.TZ


# ---------------------------------------------------------------- initData
def initdata_tests(check, log) -> None:
    log("\n== QA: initData tafsilotlari ==")
    import hashlib
    import hmac
    import urllib.parse
    u = TALABA["aziza"]
    now = int(time.time())
    T = SINOV_TALABA_TOKEN
    W = 7 * 86400
    check(auth.check_init_data(make(T, u, auth_date=now + 3600), T, W) == u, "initData: soat farqi (+1 soat) qabul qilinadi")
    check(auth.check_init_data(make(T, u, auth_date=now + 25 * 3600), T, W) is None, "initData: 25 soat kelajakda -> rad")
    check(auth.check_init_data(make(T, u, auth_date=0), T, W) is None, "initData: auth_date=0 -> rad")
    good = make(T, u)
    check(auth.check_init_data(good + "&user=" + urllib.parse.quote(json.dumps({"id": 1})), T, W) is None,
          "initData: takroriy 'user' kaliti qo'shilsa -> rad")
    check(auth.check_init_data(good + "&extra=1", T, W) is None, "initData: imzosiz qo'shimcha maydon -> rad")
    sig = make(T, u, extra={"signature": "abcDEF_-123"})
    check(auth.check_init_data(sig, T, W) == u, "initData: 'signature' maydoni (Bot API 8.0) imzoga kiradi -> qabul")
    check(auth.check_init_data(sig.replace("abcDEF_-123", "abcDEF_-124"), T, W) is None, "initData: signature o'zgartirilsa -> rad")

    def raw_make(pairs: dict) -> str:
        dcs = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", T.encode(), hashlib.sha256).digest()
        return urllib.parse.urlencode(dict(pairs, hash=hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()))
    for name, pairs in (
        ("user yo'q", {"auth_date": str(now)}),
        ("user id matn", {"auth_date": str(now), "user": '{"id":"5"}'}),
        ("user id bool", {"auth_date": str(now), "user": '{"id":true}'}),
        ("user id manfiy", {"auth_date": str(now), "user": '{"id":-5}'}),
        ("user ro'yxat", {"auth_date": str(now), "user": "[1]"}),
        ("user buzuq JSON", {"auth_date": str(now), "user": "{id:1"}),
        ("auth_date matn", {"auth_date": "kecha", "user": '{"id":5}'}),
    ):
        try:
            res = auth.check_init_data(raw_make(pairs), T, W)
        except Exception as e:  # istisno chiqmasligi kerak
            res = e
        check(res is None, f"initData: {name} -> rad (istisnosiz)", res)
    ok = raw_make({"auth_date": str(now), "user": '{"id":5,"first_name":"A"}'})
    check(auth.check_init_data(ok, T, W) == {"id": 5, "first_name": "A"}, "initData: minimal to'g'ri")
    check(auth.check_init_data("x" * 9000, T, W) is None, "initData: 8 KB dan uzun -> rad")
    # log: tokenlar yashiriladi (xabar va traceback ichida ham)
    import logging

    import main as mainmod
    real_like = "8123456789:AAH" + "x" * 32
    fmt = mainmod.RedactFormatter("%(message)s", [real_like])
    try:
        raise RuntimeError(f"POST https://api.telegram.org/bot{real_like}/getUpdates failed")
    except RuntimeError:
        rec = logging.LogRecord("httpx", logging.WARNING, __file__, 1, "so'rov: %s", (f"/bot{real_like}/getMe",), sys.exc_info())
    s = fmt.format(rec)
    other = "7000001:" + "Q" * 40  # ro'yxatda yo'q, lekin token ko'rinishida
    s2 = mainmod.RedactFormatter("%(message)s", []).format(logging.LogRecord("x", 20, __file__, 1, other, (), None))
    check(real_like not in s and "***" in s and "Traceback" in s and other not in s2,
          "log: token xabarda ham, tracebackda ham yashirildi", s[-160:])
    # panel token: rol o'zgartirilgan / exp matn
    key = b"k" * 32
    payload = auth._b64e(json.dumps({"id": 1, "role": "xakker", "exp": now + 99}).encode())
    tok = payload + "." + hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    check(auth.read_panel_token(key, tok) is None, "panel token: noma'lum rol -> rad")
    payload = auth._b64e(json.dumps({"id": 1, "role": "ceo", "exp": str(now + 99)}).encode())
    tok = payload + "." + hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    check(auth.read_panel_token(key, tok) is None, "panel token: exp matn -> rad")
    check(auth.read_panel_token(key, "a.b.c") is None and auth.read_panel_token(key, None) is None, "panel token: buzuq shakl -> rad")


# ---------------------------------------------------------------- server: rollar
def role_tests(check, log, ts) -> None:
    """ts - test_server moduli (http/jhttp/S/X yordamchilari va start/stop)."""
    log("\n== QA: xodim API - har marshrutda rol tekshiruvi (port %d) ==" % ts.PORT)
    for suf in ("", "-wal", "-shm"):
        try:
            Path(str(ts.DB) + suf).unlink()
        except OSError:
            pass
    p = ts.start_server(["--sinov", "--port", str(ts.PORT), "--db", str(ts.DB.relative_to(ROOT)), "--seed"])
    try:
        _role_body(check, log, ts)
    except Exception:
        import traceback
        check(False, "QA rol sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        check(ts.stop_server(p, config.DATA_DIR / f"sinov_{ts.PORT}.stop"), "QA server yumshoq to'xtadi")
    logtxt = (config.LOG_DIR / f"sinov_{ts.PORT}.log").read_text(encoding="utf-8", errors="ignore")
    check(SINOV_TALABA_TOKEN not in logtxt and SINOV_XODIM_TOKEN not in logtxt and not config.TOKEN_ANY_RE.search(logtxt),
          "sinov logida token ko'rinishidagi satr yo'q")


def _role_body(check, log, ts) -> None:
    jh = ts.jhttp
    # (usul, yo'l, tana, ruxsat etilgan rollar)
    routes = [
        ("POST", "/api/x/auth", {}, {"ceo", "admin", "ustoz", "assistent"}),
        ("GET", "/api/x/stats", None, {"ceo", "admin", "ustoz", "assistent"}),
        ("GET", "/api/x/students", None, {"ceo", "admin", "ustoz", "assistent"}),
        ("GET", "/api/x/course", None, {"ceo", "admin", "ustoz", "assistent"}),
        ("POST", "/api/x/open", {"n": 36}, {"ceo", "admin"}),  # 03.10: ustoz endi o'zgartira olmaydi
        ("POST", "/api/x/invite", {"role": "assistent"}, {"ceo"}),
        ("GET", "/api/x/staff", None, {"ceo"}),
        ("POST", "/api/x/staff/remove", {"id": 424242}, {"ceo"}),  # yo'q xodim: ceo -> 400, boshqalar -> 403
    ]
    toks = {r: jh("POST", "/api/x/auth", {}, ts.X(r))[2]["token"] for r in ("ceo", "admin", "ustoz", "assistent")}
    for method, path, body, allowed in routes:
        for role in ("ceo", "admin", "ustoz", "assistent"):
            for how, hdr in (("initData", ts.X(role)), ("X-Staff-Token", {"X-Staff-Token": toks[role]})):
                s, _, b = jh(method, path, body, hdr)
                exp_ok = role in allowed
                good = (s in (200, 400) and (s == 200 or path.endswith("/remove"))) if exp_ok else (s == 403 and isinstance(b, dict) and "xato" in b)
                check(good, f"rol: {role:9s} {method} {path} ({how}) -> {'ruxsat' if exp_ok else '403'}", (s, b))
        for name, hdr in (("headersiz", {}), ("talaba imzosi", ts.S("aziza")), ("begona", ts.X("begona"))):
            s, _, b = jh(method, path, body, hdr)
            check(s in (401, 403) and isinstance(b, dict) and "xato" in b, f"rol: {name} {method} {path} -> 401/403", (s, b))
    # tokendagi rol emas, bazadagi rol: assistent tokeni rolini "ceo" deb soxtalashtirib bo'lmaydi (imzo), lekin
    # rol bazada o'zgarsa - eski token ham yangi rol bilan ishlaydi
    import sqlite3
    c = sqlite3.connect(ts.DB, timeout=20)
    try:
        with c:
            c.execute("UPDATE staff SET role='ceo' WHERE id=900004")
        check(jh("GET", "/api/x/staff", None, {"X-Staff-Token": toks["assistent"]})[0] == 200, "rol bazadan: assistent CEO qilinsa - eski token CEO huquqi bilan")
        with c:
            c.execute("UPDATE staff SET role='assistent' WHERE id=900004")
        check(jh("GET", "/api/x/staff", None, {"X-Staff-Token": toks["assistent"]})[0] == 403, "rol bazadan: qaytarilganda yana 403")
    finally:
        c.close()
    # initData ustun: noto'g'ri initData + to'g'ri token -> 401 (aralashtirib bo'lmaydi)
    s = jh("GET", "/api/x/stats", None, {"X-Init-Data": "auth_date=1&hash=" + "0" * 64, "X-Staff-Token": toks["ceo"]})[0]
    check(s == 401, "xodim: buzuq initData + to'g'ri token -> 401", s)
    # 64 KB xodim API da ham
    big = json.dumps({"n": 5, "pad": "x" * 70000}).encode()
    s, _, _ = ts.http("POST", "/api/x/open", raw_body=big, headers=ts.X("ceo"))
    check(s == 413, "xodim API: 64 KB dan katta -> 413", s)
    # GET API ga POST -> 405 JSON
    s, _, b = jh("POST", "/api/x/stats", {}, ts.X("ceo"))
    check(s in (404, 405) and isinstance(b, dict) and "xato" in b, "xodim API: noto'g'ri usul -> 404/405 JSON", (s, b))
    # tezlik cheklovi: 300/daqiqa (admin)
    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(lambda _: jh("GET", "/api/x/course", None, ts.X("admin"))[0], range(310)))
    n200, n429 = codes.count(200), codes.count(429)
    check(n429 >= 1 and n200 <= config.API_LIMIT_MIN, "xodim API: daqiqasiga 300 dan keyin 429", (n200, n429))
    # talaba: test natijasi serverda hisoblanadi - javoblar ro'yxati qisqa bo'lsa qolganlari xato
    t8 = json.loads((config.CONTENT_DIR / "test" / "08.json").read_text(encoding="utf-8"))
    key8 = [q["ok"] for q in t8["savollar"]]
    s, _, b = jh("POST", "/api/s/event", {"type": "test_done", "dars": 8, "answers": key8[:2]}, ts.S("jahongir"))
    check(s == 200 and b["correct"] == 2 and b["total"] == len(key8), "test: 2 ta javob yuborilsa - 2/5 (qolganlari javobsiz)", (s, b))
    s, _, b = jh("POST", "/api/s/event", {"type": "test_done", "dars": 8, "answers": [None] * len(key8)}, ts.S("jahongir"))
    check(s == 200 and b["correct"] == 0, "test: hammasi javobsiz (null) -> 0", (s, b))
    s, _, b = jh("POST", "/api/s/event", {"type": "test_done", "dars": 8, "answers": [99, -1, 5, 7, 1000]}, ts.S("jahongir"))
    check(s == 200 and b["correct"] == 0, "test: chegaradan tashqari indekslar -> 0 (xatosiz)", (s, b))
    # video_done pos chegarasi
    s, _, b = jh("POST", "/api/s/event", {"type": "video_pos", "vid": "d02", "pos": 1e12}, ts.S("jahongir"))
    check(s == 200 and b["item"]["pos"] <= 1934.2, "video_pos: juda katta pozitsiya davomiylik bilan cheklanadi", (s, b and b.get("item")))
    s, _, b = jh("POST", "/api/s/event", {"type": "video_pos", "vid": "d02", "pos": "12"}, ts.S("jahongir"))
    check(s == 400, "video_pos: pos matn -> 400", s)
    s, _, _ = ts.http("POST", "/api/s/event", raw_body=b'{"type":"video_pos","vid":"d02","pos":NaN}', headers=ts.S("jahongir"))
    check(s == 400, "video_pos: NaN -> 400", s)
    # HEAD va OPTIONS
    s, h, _ = ts.http("HEAD", "/content/kurs.json")
    check(s == 200 and h.get("Cache-Control") == "no-cache", "HEAD /content/kurs.json -> 200", s)
    s, _, b = jh("OPTIONS", "/api/s/me")
    check(s in (404, 405), "OPTIONS API -> CORS yo'q (404/405)", s)


# ---------------------------------------------------------------- kunlik vazifalar
class FakeBot:
    def __init__(self, behaviour: dict | None = None):
        self.sent: list[dict] = []
        self.behaviour = behaviour or {}   # chat_id -> list of exceptions (navbat bilan)
        self.id = 4242

    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        q = self.behaviour.get(chat_id)
        if q:
            exc = q.pop(0)
            if exc is not None:
                raise exc
        self.sent.append({"chat_id": chat_id, "text": text, "markup": reply_markup})
        return types.SimpleNamespace(message_id=len(self.sent))


def _ctx(svc, bot):
    return types.SimpleNamespace(application=types.SimpleNamespace(bot_data={"svc": svc}), bot=bot)


def jobs_tests(check, log) -> None:
    log("\n== QA: kunlik vazifalar (callback to'g'ridan-to'g'ri, soxta soat) ==")
    import staff_bot
    import student_bot
    from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter
    from kurs import Kurs
    config.XABAR_ORALIQ = 0.0
    st = dbm.Store(Path(tempfile.mkdtemp()) / "jobs.db")
    # soat: 2026-10-05 19:00 Toshkent (dushanba)
    t19 = datetime(2026, 10, 5, 19, 0, tzinfo=TZ)
    kecha = t19 - timedelta(days=1)
    users = {
        1: dict(first_name="Ali"),                  # kecha ball bor -> seriya 1 bilan eslatma
        2: dict(first_name="Vali"),                 # bugun 00:30 da ball oldi -> eslatma yo'q
        3: dict(first_name="Gani", eslatma=0),      # eslatma o'chiq
        4: dict(first_name="Bloklagan"),            # Forbidden -> blocked=1
        5: dict(first_name="Eski"),                 # 15 kun oldin kirgan -> yo'q
        6: dict(first_name="Kutgan"),               # RetryAfter -> qayta urinib yuboriladi
        7: dict(first_name="Topilmagan"),           # chat not found -> blocked
        8: dict(first_name="Tarmoq"),               # NetworkError -> o'tkazib yuboriladi (keyingilarga to'sqinlik yo'q)
        9: dict(first_name="Nol"),                  # bugun ilovani ochgan, 0 ball -> eslatma (seriya 0 matni)
    }
    for uid, kw in users.items():
        last = t19 - timedelta(days=15) if uid == 5 else t19 - timedelta(hours=3)
        st.upsert_user({"id": uid, "first_name": kw["first_name"]}, kecha - timedelta(days=2), "bot")
        with st._c(True) as c:
            c.execute("UPDATE users SET last_seen=?, eslatma=? WHERE id=?", (dbm.iso(last), kw.get("eslatma", 1), uid))
    for d in range(3):  # Ali: 3 kunlik seriya kechagacha
        st.ev_slide(1, 1, d + 1, kecha - timedelta(days=d))
    st.ev_slide(2, 1, 1, datetime(2026, 10, 5, 0, 30, tzinfo=TZ))  # UTC bo'yicha hali 4-oktabr
    st.upsert_user({"id": 9, "first_name": "Nol"}, t19 - timedelta(hours=1), "app")
    targets = [t["id"] for t in st.reminder_targets(t19)]
    check(targets == [1, 4, 6, 7, 8, 9], "eslatma nishonlari (eslatma, blok, 14 kun, bugungi ball - Toshkent sanasi bilan)", targets)
    bot = FakeBot({4: [Forbidden("Forbidden: bot was blocked by the user")],
                   6: [RetryAfter(1)],
                   7: [BadRequest("Chat not found")],
                   8: [NetworkError("x")]})
    svc = types.SimpleNamespace(store=st, kurs=Kurs(), base_url="https://a-b.trycloudflare.com", brend="Muhammadamin", now=lambda: t19)
    t0 = time.time()
    asyncio.run(student_bot.job_eslatma(_ctx(svc, bot)))
    took = time.time() - t0
    sent = {m["chat_id"]: m for m in bot.sent}
    check(set(sent) == {1, 6, 9}, "eslatma yuborildi: Ali, RetryAfter dan keyin Kutgan, Nol", sorted(sent))
    check(sent.get(1, {}).get("text") == "Bugungi darsni davom ettiramizmi? Seriyangiz: 3 kun.", "eslatma matni (seriya 3)", sent.get(1))
    check(sent.get(9, {}).get("text") == "Bugungi darsni davom ettiramizmi? Bugun yangi seriya boshlang.", "eslatma matni (seriya 0)", sent.get(9))
    mk = sent.get(1, {}).get("markup")
    btn = mk.inline_keyboard[0][0] if mk else None
    check(btn is not None and btn.text == "Darsni davom ettirish" and btn.web_app.url == "https://a-b.trycloudflare.com/app/",
          "eslatma tugmasi web_app /app/", btn)
    check(1.0 <= took < 10, "RetryAfter: kutib qayta urindi", f"{took:.1f} s")
    bl = {r["id"]: r["blocked"] for r in [st.get_user(i) for i in (4, 7, 8)]}
    check(bl == {4: 1, 7: 1, 8: 0}, "Forbidden va 'chat not found' -> blocked=1; tarmoq xatosi -> o'zgarmaydi", bl)
    check([t["id"] for t in st.reminder_targets(t19)] == [1, 6, 8, 9], "bloklanganlarga keyingi kuni eslatma yo'q")
    st.upsert_user({"id": 4, "first_name": "Bloklagan"}, t19, "bot")
    check(st.get_user(4)["blocked"] == 0, "bloklagan /start bossa - blok olib tashlanadi")
    # manzil yo'q (tunnel hali tayyor emas) - tugmasiz yuboriladi
    bot2 = FakeBot()
    svc.base_url = None
    asyncio.run(student_bot.job_eslatma(_ctx(svc, bot2)))
    check(bot2.sent and all(m["markup"] is None for m in bot2.sent), "manzil yo'q: eslatma tugmasiz")

    # 21:00 hisobot
    t21 = datetime(2026, 10, 5, 21, 0, tzinfo=TZ)
    st.staff_set({"id": 501, "first_name": "Bosh"}, "ceo", None, t21 - timedelta(days=3))
    st.staff_set({"id": 502, "first_name": "Ikkinchi"}, "ceo", None, t21 - timedelta(days=3))
    st.staff_set({"id": 503, "first_name": "Ustoz"}, "ustoz", 501, t21 - timedelta(days=3))
    st.upsert_user({"id": 20, "first_name": "Yangi"}, datetime(2026, 10, 5, 10, 0, tzinfo=TZ), "bot")
    st.upsert_user({"id": 21, "first_name": "Kechagi"}, datetime(2026, 10, 4, 23, 59, tzinfo=TZ), "bot")
    for i in range(1, 13):
        st.ev_slide(20, 3, i, datetime(2026, 10, 5, 11, 0, tzinfo=TZ))
    st.ev_lesson_done(20, 3, 12, datetime(2026, 10, 5, 11, 5, tzinfo=TZ))
    s = st.daily_summary(t21)
    exp_active = len({r[0] for r in st._conn().execute("SELECT user_id FROM days WHERE day='2026-10-05'")})
    check(s["new"] == 1 and s["lessons_done"] == 1 and s["active"] == exp_active, "hisobot: yangi 1 (kechagi emas), tugatilgan 1, faol", (s, exp_active))
    bot3 = FakeBot({502: [Forbidden("blocked")]})
    svc.base_url = "https://a-b.trycloudflare.com"
    svc.now = lambda: t21
    asyncio.run(staff_bot.job_hisobot(_ctx(svc, bot3)))
    check([m["chat_id"] for m in bot3.sent] == [501], "hisobot faqat CEO larga (bloklagan CEO o'tkazildi, ustozga yo'q)", [m["chat_id"] for m in bot3.sent])
    txt = bot3.sent[0]["text"] if bot3.sent else ""
    check(txt.startswith("Kunlik hisobot (05.10.2026):\nYangi o'quvchilar: 1\n") and "Bugun tugatilgan darslar: 1" in txt,
          "hisobot matni", txt)
    btn = bot3.sent[0]["markup"].inline_keyboard[0][0] if bot3.sent and bot3.sent[0]["markup"] else None
    check(btn is not None and btn.web_app.url == "https://a-b.trycloudflare.com/admin/", "hisobot tugmasi /admin/ (03.10 dan)", btn)

    # vazifalar jadvali: PTB JobQueue 19:00 / 21:00 Toshkent vaqti (UTC 14:00 / 16:00)
    from telegram.ext import Application
    app = Application.builder().token(SINOV_TALABA_TOKEN).build()

    async def sched():
        await app.job_queue.start()
        j1 = app.job_queue.run_daily(student_bot.job_eslatma, time=config.ESLATMA_VAQTI, name="eslatma")
        j2 = app.job_queue.run_daily(staff_bot.job_hisobot, time=config.HISOBOT_VAQTI, name="hisobot")
        r = (j1.next_t, j2.next_t)
        await app.job_queue.stop()
        return r
    n1, n2 = asyncio.run(sched())
    from datetime import timezone
    check(n1 is not None and n1.astimezone(TZ).strftime("%H:%M") == "19:00" and n1.astimezone(timezone.utc).hour == 14,
          "JobQueue: eslatma 19:00 Toshkent (14:00 UTC)", n1)
    check(n2 is not None and n2.astimezone(TZ).strftime("%H:%M") == "21:00", "JobQueue: hisobot 21:00 Toshkent", n2)


# ---------------------------------------------------------------- PDF yuborish
def pdf_tests(check, log) -> None:
    log("\n== QA: send_pdf (soxta bot) ==")
    import student_bot
    from db import Xato
    from kurs import Kurs
    from telegram.error import BadRequest, Forbidden
    st = dbm.Store(Path(tempfile.mkdtemp()) / "pdf.db")
    kurs = Kurs()
    if kurs.pdf_path(1) is None:
        log("  (o'tkazildi: PDF papkasi topilmadi)")
        return

    class Bot:
        id = 777

        def __init__(self, fail=None):
            self.calls = []
            self.fail = fail or []

        async def send_document(self, chat_id, document, **kw):
            self.calls.append((chat_id, "file" if hasattr(document, "read") else document))
            if self.fail:
                raise self.fail.pop(0)
            return types.SimpleNamespace(document=types.SimpleNamespace(file_id=f"FID{len(self.calls)}"))

    svc = types.SimpleNamespace(store=st, kurs=kurs, now=dbm.now_tz)

    async def go():
        b = Bot()
        await student_bot.send_pdf(b, svc, 1, 1)
        await student_bot.send_pdf(b, svc, 2, 1)
        check([c[1] for c in b.calls] == ["file", "FID1"], "send_pdf: birinchi yuklash, keyin file_id", b.calls)
        b = Bot([BadRequest("Chat not found")])
        try:
            await student_bot.send_pdf(b, svc, 3, 1)
            check(False, "send_pdf: chat not found -> Xato(409)")
        except Xato as e:
            check(e.status == 409 and "/start" in e.xato, "send_pdf: kesh + 'chat not found' -> 409", e.xato)
        check(st.pdf_cache_get(777, 1) is not None, "send_pdf: 'chat not found' keshni o'chirmaydi")
        b = Bot([BadRequest("Wrong file identifier/http url specified")])
        await student_bot.send_pdf(b, svc, 4, 1)
        check([c[1] for c in b.calls] == ["FID1", "file"], "send_pdf: kesh yaroqsiz -> qayta yuklaydi", b.calls)
        b = Bot([Forbidden("blocked")])
        try:
            await student_bot.send_pdf(b, svc, 5, 2)
            check(False, "send_pdf: Forbidden -> 409")
        except Xato as e:
            check(e.status == 409, "send_pdf: Forbidden (yangi fayl) -> 409")
    asyncio.run(go())


# ---------------------------------------------------------------- tokenlar.py
def tokenlar_tests(check, log) -> None:
    log("\n== QA: tokenlar.py (soxta getpass/input/tarmoq) ==")
    import tokenlar
    d = Path(tempfile.mkdtemp())
    tmp_env = d / ".env"
    t1, t2 = "1234567:" + "A" * 35, "7654321:" + "B" * 35
    saved = (config.ENV_FILE, tokenlar.get_me, getpass.getpass, builtins.input)
    try:
        config.ENV_FILE = tmp_env
        tokenlar.get_me = lambda t: "tarmoq"
        seq = iter([t1, t1, t1])
        getpass.getpass = lambda prompt="": next(seq)
        with contextlib.redirect_stdout(io.StringIO()) as b:
            rc = tokenlar.main()
        check(rc == 1 and b.getvalue().count("Telegramga ulanib bo'lmadi") == 3 and not tmp_env.exists(),
              "tokenlar: tarmoq yo'q -> 3 marta xabar, hech narsa yozilmadi", rc)
        tokenlar.get_me = lambda t: {"id": int(t.split(":")[0]), "username": f"b{t[:3]}_bot", "first_name": "S"}
        seq = iter([f'"{t1}"', f" '{t2}' "])
        getpass.getpass = lambda prompt="": next(seq)
        with contextlib.redirect_stdout(io.StringIO()) as b:
            rc = tokenlar.main()
        txt = tmp_env.read_text(encoding="utf-8") if tmp_env.exists() else ""
        check(rc == 0 and f"TALABA_BOT_TOKEN={t1}\n" in txt and f"XODIM_BOT_TOKEN={t2}\n" in txt, "tokenlar: qo'shtirnoqli token tozalandi", txt[:0])
        check(t1 not in b.getvalue() and t2 not in b.getvalue() and "AAAAAAAAAA" not in b.getvalue(), "tokenlar: ekranda token yo'q")
        check(not (d / ".env.tmp").exists(), "tokenlar: .env.tmp qolmadi")
        check(config.load_env(tmp_env) == {"TALABA_BOT_TOKEN": t1, "XODIM_BOT_TOKEN": t2}, "config.load_env .env ni o'qiydi")

        def eof(prompt=""):
            raise EOFError
        builtins.input = eof
        with contextlib.redirect_stdout(io.StringIO()) as b:
            try:
                rc = tokenlar.main()
            except EOFError:
                rc = "EOFError"
        check(rc == 0 and "Hech narsa o'zgarmadi" in b.getvalue() and tmp_env.read_text(encoding="utf-8") == txt,
              "tokenlar: mavjud .env + kiritish yopiq (EOF) -> o'zgarmaydi, xatosiz", rc)
        builtins.input = lambda prompt="": "ha"
        getpass.getpass = eof
        with contextlib.redirect_stdout(io.StringIO()) as b:
            rc = tokenlar.main()
        check(rc == 1 and "Bekor qilindi" in b.getvalue() and tmp_env.read_text(encoding="utf-8") == txt, "tokenlar: getpass EOF -> bekor, .env o'zgarmaydi")
        seq = iter(["", "123:abc", t1, t2])
        getpass.getpass = lambda prompt="": next(seq)
        with contextlib.redirect_stdout(io.StringIO()) as b:
            rc = tokenlar.main()
        check(rc == 0 and "Hech narsa kiritilmadi" in b.getvalue() and "Token ko'rinishi noto'g'ri" in b.getvalue(),
              "tokenlar: bo'sh va qisqa token -> qayta so'raladi")
        # haqiqiy get_me: Telegram 401 -> None; ulanish xatosi -> "tarmoq" (tarmoqqa chiqmasdan)
        import urllib.error
        import urllib.request
        real = saved[1]
        orig = urllib.request.urlopen

        def u401(req, timeout=0):
            check("/bot" in req.full_url, "get_me: api.telegram.org/bot<token>/getMe")
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        try:
            urllib.request.urlopen = u401
            r401 = real(t1)
            urllib.request.urlopen = lambda req, timeout=0: (_ for _ in ()).throw(urllib.error.URLError("no net"))
            rnet = real(t1)
        finally:
            urllib.request.urlopen = orig
        check(r401 is None and rnet == "tarmoq", "get_me: 401 -> None, tarmoq xatosi -> 'tarmoq'", (r401, rnet))
    finally:
        config.ENV_FILE, tokenlar.get_me, getpass.getpass, builtins.input = saved


# ---------------------------------------------------------------- main.py / boshqar / jarayon
def process_tests(check, log, out: Path) -> None:
    log("\n== QA: main.py .env siz, ikkinchi nusxa, jarayon filtri ==")
    import jarayon
    if not config.ENV_FILE.exists():
        hp, pp, lp = out / "qa_prod_holat.json", out / "qa_prod.pid", out / "qa_prod.log"
        for f in (hp, pp, lp):
            try:
                f.unlink()
            except OSError:
                pass
        r = subprocess.run([sys.executable, str(ROOT / "server" / "main.py"), "--port", "8796", "--holat", str(hp), "--pid", str(pp),
                            "--log", str(lp)], cwd=str(ROOT), capture_output=True, timeout=60, creationflags=config.CREATE_NO_WINDOW)
        err = r.stderr.decode("utf-8", "replace")
        check(r.returncode == 2 and "server\\.env topilmadi" in err and "1 - Tokenlarni kiritish.bat" in err,
              "main.py .env siz: stderr da o'zbekcha yo'riq", err.strip()[-200:])
    # jarayon filtri
    root = str(config.ROOT)
    prod = f'"C:\\Python\\pythonw.exe" "{root}\\server\\main.py"'
    sinov = f'python.exe "{root}\\server\\main.py" --sinov --port 8794 --db data\\x.db'
    fake = f'pythonw.exe "{root}\\server\\main.py" --fake-tg http://127.0.0.1:5 --port 8796'
    other = 'python.exe "C:\\Users\\N.M\\.claude\\telegram-bot\\bot.py"'
    check(jarayon.is_main_cmdline(prod) and not jarayon.is_test_cmdline(prod), "jarayon: ishchi server tanildi")
    check(jarayon.is_test_cmdline(sinov) and jarayon.is_test_cmdline(fake), "jarayon: sinov/fake serverlar tanildi")
    check(not jarayon.is_main_cmdline(other), "jarayon: boshqa bot (telegram-bot) tegilmaydi")
    saved = jarayon.processes
    try:
        jarayon.processes = lambda names: [{"pid": 11, "name": "pythonw.exe", "exe": "", "cmdline": prod},
                                           {"pid": 12, "name": "python.exe", "exe": "", "cmdline": sinov},
                                           {"pid": 13, "name": "pythonw.exe", "exe": "", "cmdline": fake},
                                           {"pid": 14, "name": "python.exe", "exe": "", "cmdline": other}]
        check([p["pid"] for p in jarayon.main_processes()] == [11], "jarayon.main_processes: faqat ishchi server (sinovlarga tegilmaydi)")
        check([p["pid"] for p in jarayon.main_processes(include_tests=True)] == [11, 12, 13], "jarayon.main_processes(include_tests)")
        jarayon.processes = lambda names: [{"pid": 21, "name": "cloudflared.exe", "exe": "C:\\Users\\N.M\\.claude\\telegram-bot\\cloudflared.exe", "cmdline": ""},
                                           {"pid": 22, "name": "cloudflared.exe", "exe": str(config.CLOUDFLARED), "cmdline": ""},
                                           {"pid": 23, "name": "cloudflared.exe", "exe": root + "x\\cloudflared.exe", "cmdline": ""}]
        check([p["pid"] for p in jarayon.cloudflared_under_root()] == [22], "jarayon: faqat ROOT ichidagi cloudflared (boshqa bot va o'xshash nomli papka emas)")
    finally:
        jarayon.processes = saved
    # boshqar.stop (sinov PID lari bilan) - begona jarayon PID i berilmasa hech narsa o'ldirilmaydi
    import boshqar
    lines: list[str] = []
    rc = boshqar.stop(holat_path=out / "yoq_holat.json", pid_path=out / "yoq.pid", only_pids={999999}, out=lines.append, wait=1)
    check(rc == 0 and lines == ["Server ishlamayotgan edi."], "boshqar.stop: ishlamayotgan server -> tushunarli xabar", lines)
    # main.py yagona nusxa: ikkinchi nusxa log fayliga yozmaydi
    pp = out / "qa_lock.pid"
    lp = out / "qa_lock.log"
    for f in (lp,):
        try:
            f.unlink()
        except OSError:
            pass
    sys.path.insert(0, str(ROOT / "server"))
    import main as mainmod
    lock = mainmod.PidLock(pp)
    check(lock.acquire(), "PidLock: birinchi nusxa qulfni oldi")
    try:
        r = subprocess.run([sys.executable, str(ROOT / "server" / "main.py"), "--sinov", "--port", "8796", "--pid", str(pp), "--log", str(lp)],
                           cwd=str(ROOT), capture_output=True, timeout=60, creationflags=config.CREATE_NO_WINDOW)
        check(r.returncode == 3 and not lp.exists() and "allaqachon ishlayapti" in r.stderr.decode("utf-8", "replace"),
              "ikkinchi nusxa: chiqish 3, log fayliga tegmaydi, stderr da xabar", (r.returncode, lp.exists()))
    finally:
        lock.release()
    check(not pp.exists(), "PidLock: release faylni o'chiradi")


def async_tests(check, log, out: Path) -> None:
    log("\n== QA: tunnel.stop bekor qilish, 409 ogohlantirishi ==")
    import main as mainmod
    import tunnel as tn

    async def go():
        t = tn.Tunnel(1, exe=Path(sys.executable), args=["-c", "import time; time.sleep(60)"])
        # manzil chiqmaydigan jarayon: start() kutadi; tashqaridan bekor qilinsa - CancelledError tarqalishi kerak
        task = asyncio.create_task(t.start(timeout=30))
        await asyncio.sleep(1.0)
        task.cancel()
        try:
            await asyncio.wait_for(task, 15)
            res = "tugadi"
        except asyncio.CancelledError:
            res = "bekor"
        except asyncio.TimeoutError:
            res = "osildi"
        check(res == "bekor", "tunnel.start: tashqi bekor qilish yutilmaydi", res)
        await t.stop()
        check(not t.alive(), "tunnel: bekor qilingandan keyin jarayon to'xtatildi")
        # 409 ogohlantirishi
        h = mainmod.Holat(out / "qa_konflikt_holat.json", 1)
        h.update(xato="Talabalar boti tokeni bilan " + mainmod.KONFLIKT_MATN)
        h.conflict_last = time.monotonic() - mainmod.KONFLIKT_TOZALASH - 1
        old = mainmod.MENYU_TEKSHIRUV
        mainmod.MENYU_TEKSHIRUV = 0.2
        stop = asyncio.Event()
        task = asyncio.create_task(mainmod.conflict_clear(h, stop))
        await asyncio.sleep(0.8)
        check(h.data["xato"] is None, "409 ogohlantirishi: Conflict to'xtagach o'chdi")
        h.update(xato="Talabalar boti tokeni bilan " + mainmod.KONFLIKT_MATN)
        h.conflict_last = time.monotonic()
        await asyncio.sleep(0.6)
        check(h.data["xato"] is not None, "409 ogohlantirishi: Conflict davom etsa saqlanadi")
        h.update(xato="Tunnel manzili olinmadi")
        h.conflict_last = 0.0
        await asyncio.sleep(0.6)
        check(h.data["xato"] == "Tunnel manzili olinmadi", "boshqa xatolarga tegilmaydi")
        stop.set()
        await asyncio.wait_for(task, 5)
        mainmod.MENYU_TEKSHIRUV = old
    asyncio.run(go())


def bot_text_tests(check, log) -> None:
    log("\n== QA: xodim boti (ulanmagan holat) ==")
    import staff_bot
    st = dbm.Store(Path(tempfile.mkdtemp()) / "sb.db")
    kod = st.ensure_pair_code()
    svc = types.SimpleNamespace(store=st, brend="Muhammadamin", base_url=None, xodim_username="b_bot")
    now = dbm.now_tz()
    r = staff_bot.handle_start(svc, {"id": 1, "first_name": "Ega"}, "", now)
    check("4 - Holat.bat" in r.text and kod not in r.text and r.button is None, "ulanmagan: /start -> kod yo'rig'i (kodning o'zi yo'q)", r.text)
    r = staff_bot.handle_text(svc, {"id": 1, "first_name": "Ega"}, "salom", now)
    check("4 - Holat.bat" in r.text, "ulanmagan: oddiy matn -> kod yo'rig'i")
    for i in range(5):
        staff_bot.handle_text(svc, {"id": 2}, str(100000 + (int(kod) - 100000 + 1 + i) % 900000), now)
    r = staff_bot.handle_text(svc, {"id": 2}, kod, now)
    check("juda ko'p" in r.text.lower() and st.staff_count() == 0, "ulash: 5 xato urinishdan keyin to'g'ri kod ham qabul qilinmaydi (1 soat)", r.text)
    r = staff_bot.handle_text(svc, {"id": 1, "first_name": "Ega"}, kod, now)
    check(r.paired and st.staff_get(1)["role"] == "ceo", "ulash: boshqa foydalanuvchi (ega) to'g'ri kod bilan CEO bo'ldi")
    r = staff_bot.handle_start(svc, {"id": 3, "first_name": "Begona"}, "", now)
    check(r.text == "Bu bot faqat Muhammadamin xodimlari uchun.", "ulangandan keyin: begona -> faqat rad (yo'riqsiz)", r.text)
    r = staff_bot.handle_start(svc, {"id": 1, "first_name": "Ega"}, "", now)
    check("tayyorlanmoqda" in r.text and r.button is None, "manzil yo'q: CEO /start -> kuting, tugmasiz", r.text)


def run(check, log, ts) -> None:
    out = ts.OUT
    out.mkdir(parents=True, exist_ok=True)
    for fn in (lambda: initdata_tests(check, log), lambda: jobs_tests(check, log), lambda: pdf_tests(check, log),
               lambda: tokenlar_tests(check, log), lambda: bot_text_tests(check, log),
               lambda: process_tests(check, log, out), lambda: async_tests(check, log, out),
               lambda: role_tests(check, log, ts)):
        try:
            fn()
        except Exception:
            import traceback
            check(False, "QA bo'limi kutilmaganda to'xtadi", traceback.format_exc())

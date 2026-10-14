"""Server sinovlari (server agenti).

    python tools/test_server.py              # hammasi: unit + API + soxta Telegram (e2e)
    python tools/test_server.py --faqat unit|api|tg

API sinovi:  python server/main.py --sinov --port 8793 --db data/sinov_server.db --seed  (o'zi ishga tushiradi va to'xtatadi)
E2E sinovi:  tools/test_server_tg.py (soxta Telegram + boshqar.start/stop + --fake-tg)
Natija: _sinov/server/natija.txt
"""
from __future__ import annotations

import argparse
import http.client as httpclient
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import auth  # noqa: E402
import config  # noqa: E402
import db as dbm  # noqa: E402
from sinov_initdata import SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN, TALABA, XODIM, make  # noqa: E402

PORT = 8796
DB = ROOT / "data" / "sinov_qa_server.db"
OUT = ROOT / "_sinov" / "qa-server"
BASE = f"http://127.0.0.1:{PORT}"


def configure(port: int, db: Path, out: Path) -> None:
    """Port/baza/natija papkasini o'zgartirish (har agent o'z porti va bazasi bilan)."""
    global PORT, DB, OUT, BASE
    PORT, DB, OUT = port, db, out
    BASE = f"http://127.0.0.1:{PORT}"
    import test_server_tg as tg
    tg.PORT, tg.OUT, tg.BASE = port, out, BASE
    tg.DB = db.with_name(db.stem + "_tg.db")
    tg.HOLAT, tg.PID = out / "tg_holat.json", out / "tg_main.pid"
TZ = config.TZ


# ---------------------------------------------------------------- natijalar
class R:
    ok = 0
    fails: list[str] = []
    lines: list[str] = []


def log(s: str) -> None:
    R.lines.append(s)
    print(s, flush=True)


def check(cond, name: str, detail="") -> bool:
    if cond:
        R.ok += 1
        log(f"  OK   {name}")
    else:
        R.fails.append(f"{name} :: {detail}")
        log(f"  XATO {name} :: {detail}")
    return bool(cond)


# ---------------------------------------------------------------- HTTP
def http(method: str, path: str, body=None, headers: dict | None = None, raw_body: bytes | None = None):
    data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, r.headers, r.read()  # HTTPMessage: sarlavha nomlari katta-kichik harfga sezgir emas
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def jhttp(method, path, body=None, headers=None):
    s, h, b = http(method, path, body, headers)
    try:
        return s, h, json.loads(b) if b else None
    except ValueError:
        return s, h, None


def raw(path: str, headers: dict | None = None):
    """So'rov yo'lini o'zgartirmasdan yuborish (traversal sinovi uchun)."""
    c = httpclient.HTTPConnection("127.0.0.1", PORT, timeout=15)
    c.putrequest("GET", path, skip_accept_encoding=True)
    for k, v in (headers or {}).items():
        c.putheader(k, v)
    c.endheaders()
    r = c.getresponse()
    body = r.read()
    st, hd = r.status, r.msg
    c.close()
    return st, hd, body


def S(name="aziza", **kw):
    return {"X-Init-Data": make(SINOV_TALABA_TOKEN, TALABA[name] if isinstance(name, str) else name, **kw)}


def X(name="ceo", **kw):
    return {"X-Init-Data": make(SINOV_XODIM_TOKEN, XODIM[name] if isinstance(name, str) else name, **kw)}


# ---------------------------------------------------------------- server jarayoni
def start_server(extra: list[str]) -> subprocess.Popen:
    OUT.mkdir(parents=True, exist_ok=True)
    out = open(OUT / "server_stdout.txt", "w", encoding="utf-8")
    p = subprocess.Popen([sys.executable, str(ROOT / "server" / "main.py"), *extra], cwd=str(ROOT),
                         stdout=out, stderr=subprocess.STDOUT, creationflags=config.CREATE_NO_WINDOW)
    t0 = time.time()
    while time.time() - t0 < 30:
        if p.poll() is not None:
            raise RuntimeError("server to'xtab qoldi: " + (OUT / "server_stdout.txt").read_text(encoding="utf-8"))
        try:
            s, _, _ = http("GET", "/")
            if s in (301, 302):
                return p
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.3)
    p.kill()
    raise RuntimeError("server 30 s da javob bermadi")


def stop_server(p: subprocess.Popen, stop_file: Path) -> bool:
    """Yumshoq to'xtatish (stop fayli); bo'lmasa - majburan (faqat o'zimiz ishga tushirgan jarayon)."""
    stop_file.write_text("stop", encoding="ascii")
    try:
        p.wait(15)
        return True
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(5)
        return False


# ---------------------------------------------------------------- UNIT
def unit_tests() -> None:
    log("\n== UNIT ==")
    # streak
    t = date(2026, 10, 2)
    d = lambda n: (t - timedelta(days=n)).isoformat()  # noqa: E731
    check(dbm.streak_from_days([], t) == (0, 0), "streak: bo'sh")
    check(dbm.streak_from_days([d(0), d(1), d(2)], t) == (3, 3), "streak: bugun bilan 3")
    check(dbm.streak_from_days([d(1), d(2)], t) == (2, 2), "streak: bugun yo'q, kecha bor -> 2")
    check(dbm.streak_from_days([d(2), d(3)], t) == (0, 2), "streak: kecha ham yo'q -> 0")
    check(dbm.streak_from_days([d(0), d(2), d(3), d(4), d(5)], t) == (1, 4), "streak: uzilish -> 1, eng uzun 4")
    check(dbm.short_name("Aziza", "Karimova") == "Aziza K.", "ism: Aziza K.")
    check(dbm.short_name("Jasur", "") == "Jasur", "ism: familiyasiz")

    # initData
    now = time.time()
    u = TALABA["aziza"]
    good = make(SINOV_TALABA_TOKEN, u)
    check(auth.check_init_data(good, SINOV_TALABA_TOKEN, 7 * 86400) == u, "initData: to'g'ri -> user")
    check(auth.check_init_data(good, SINOV_XODIM_TOKEN, 7 * 86400) is None, "initData: boshqa bot tokeni -> None")
    check(auth.check_init_data(good.replace("Aziza", "Azizb"), SINOV_TALABA_TOKEN, 7 * 86400) is None, "initData: o'zgartirilgan -> None")
    old = make(SINOV_TALABA_TOKEN, u, auth_date=int(now) - 8 * 86400)
    check(auth.check_init_data(old, SINOV_TALABA_TOKEN, 7 * 86400) is None, "initData: 8 kunlik -> None")
    check(auth.check_init_data("", SINOV_TALABA_TOKEN, 100) is None, "initData: bo'sh -> None")
    check(auth.check_init_data("hash=" + chr(0xE9) * 64, SINOV_TALABA_TOKEN, 100) is None, "initData: ASCII bo'lmagan hash -> None")
    check(auth.check_init_data("a=1&&b", SINOV_TALABA_TOKEN, 100) is None, "initData: buzuq -> None")

    # panel token
    key = os.urandom(32)
    tok = auth.make_panel_token(key, 900001, "ceo")
    check(auth.read_panel_token(key, tok)["id"] == 900001, "panel token: to'g'ri")
    check(auth.read_panel_token(os.urandom(32), tok) is None, "panel token: boshqa kalit -> None")
    check(auth.read_panel_token(key, auth.make_panel_token(key, 900001, "ceo", ttl=-5)) is None, "panel token: muddati o'tgan")
    p, s = tok.split(".")
    forged = auth._b64e(json.dumps({"id": 900003, "role": "ceo", "exp": int(now) + 999}).encode()) + "." + s
    check(auth.read_panel_token(key, forged) is None, "panel token: o'zgartirilgan payload")
    check(auth.read_panel_token(key, p + ".zz") is None, "panel token: buzuq imzo")
    check(auth.panel_allowed("ustoz", "Admin_paneli.html", "lms") and not auth.panel_allowed("ustoz", "Admin_paneli.html", None),
          "panel_allowed: ustoz faqat LMS")
    check(not auth.panel_allowed("ustoz", "CEO_paneli.html", None), "panel_allowed: ustoz CEO panelga yo'q")
    check(auth.panel_allowed("assistent", "Ustoz_paneli.html", "assistent") and not auth.panel_allowed("assistent", "Ustoz_paneli.html", None),
          "panel_allowed: assistent faqat assistent rejimi")

    # safe_path
    import web
    root = config.CONTENT_DIR
    check(web.safe_path(root, "kurs.json") is not None, "safe_path: oddiy fayl")
    for bad in ("../server/.env", "..", "dars/../../x", "a\\b", "C:/Windows/win.ini", ".env", "kurs.json\x00.png", "NUL",
                "dars/con.txt", "kurs.json.", "x/./y", ""):
        check(web.safe_path(root, bad) is None, f"safe_path rad etadi: {bad!r}")

    # Store: vaqtinchalik bazada
    tmp = Path(tempfile.mkdtemp()) / "unit.db"
    st = dbm.Store(tmp)
    now_dt = dbm.now_tz()
    st.upsert_user({"id": 1, "first_name": "A"}, now_dt)
    x1, _ = st.ev_slide(1, 8, 1, now_dt)
    x2, _ = st.ev_slide(1, 8, 1, now_dt)
    check((x1, x2) == (1, 0), "XP: slayd bir marta", (x1, x2))
    try:
        st.ev_lesson_done(1, 8, 15, now_dt)
        check(False, "dars tugatish: 1/15 da rad etilishi kerak")
    except dbm.Xato as e:
        check(e.status == 400, "dars tugatish: 1/15 -> 400")
    for i in range(2, 12):
        st.ev_slide(1, 8, i, now_dt)
    try:
        st.ev_lesson_done(1, 8, 15, now_dt)
        check(False, "dars tugatish: 11/15 (<80%) rad etilishi kerak")
    except dbm.Xato:
        check(True, "dars tugatish: 11/15 -> rad")
    st.ev_slide(1, 8, 12, now_dt)
    a, _ = st.ev_lesson_done(1, 8, 15, now_dt)
    b, _ = st.ev_lesson_done(1, 8, 15, now_dt)
    check((a, b) == (20, 0), "dars tugatish: 12/15 (=80%) -> +20, qayta 0", (a, b))
    # 8 slaydli dars: ceil(6.4) = 7
    for i in range(1, 7):
        st.ev_slide(1, 18, i, now_dt)
    try:
        st.ev_lesson_done(1, 18, 8, now_dt)
        check(False, "dars 18: 6/8 rad etilishi kerak")
    except dbm.Xato:
        check(True, "dars 18: 6/8 -> rad (ceil(6.4)=7)")
    st.ev_slide(1, 18, 7, now_dt)
    check(st.ev_lesson_done(1, 18, 8, now_dt)[0] == 20, "dars 18: 7/8 -> +20")
    v1, _ = st.ev_video_done(1, "d02", now_dt)
    v2, _ = st.ev_video_done(1, "d02", now_dt)
    check((v1, v2) == (30, 0), "XP: video bir marta +30", (v1, v2))
    t1 = st.ev_test_done(1, 8, 2, 5, now_dt)[0]
    t2 = st.ev_test_done(1, 8, 1, 5, now_dt)[0]
    t3 = st.ev_test_done(1, 8, 5, 5, now_dt)[0]
    t4 = st.ev_test_done(1, 8, 5, 5, now_dt)[0]
    check((t1, t2, t3, t4) == (8, 0, 22, 0), "XP test: 4*(yangi-eski) + birinchi mukammal +10", (t1, t2, t3, t4))
    # takliflar
    st.staff_set({"id": 10, "first_name": "Bosh"}, "ceo", None, now_dt)
    code, exp = st.invite_create("ustoz", 10, now_dt)
    check(st.invite_redeem(code, {"id": 11, "first_name": "U"}, now_dt) == ("ustoz", None), "taklif: birinchi marta -> ustoz")
    check(st.invite_redeem(code, {"id": 12, "first_name": "V"}, now_dt)[1] == "yaroqsiz", "taklif: ikkinchi marta -> yaroqsiz")
    code2, _ = st.invite_create("admin", 10, now_dt)
    check(st.invite_redeem(code2, {"id": 13}, now_dt + timedelta(hours=49))[1] == "yaroqsiz", "taklif: 49 soatdan keyin -> yaroqsiz")
    check(st.invite_redeem(code2, {"id": 13}, now_dt + timedelta(hours=47))[0] == "admin", "taklif: 47 soatda -> admin")
    code3, _ = st.invite_create("assistent", 10, now_dt)
    check(st.invite_redeem(code3, {"id": 10}, now_dt)[1] == "ceo", "taklif: CEO o'z rolini yo'qotmaydi")
    check(st.staff_get(10)["role"] == "ceo", "taklif: CEO hali ham ceo")
    # oxirgi CEO
    check(st.staff_remove(11, 10) == "Oxirgi CEO ni o'chirib bo'lmaydi.", "oxirgi CEO ni o'chirib bo'lmaydi")
    check(st.staff_remove(10, 10) == "O'zingizni o'chira olmaysiz.", "o'zini o'chira olmaydi")
    st.staff_set({"id": 14, "first_name": "Ikkinchi"}, "ceo", None, now_dt)
    check(st.staff_remove(10, 14) is None, "ikkita CEO bo'lsa - birini o'chirish mumkin")
    # ulash kodi
    tmp2 = Path(tempfile.mkdtemp()) / "pair.db"
    st2 = dbm.Store(tmp2)
    kod = st2.ensure_pair_code()
    check(kod and len(kod) == 6 and kod.isdigit(), "ulash kodi: 6 xonali", kod)
    check(st2.ensure_pair_code() == kod, "ulash kodi: qayta ishga tushganda o'sha kod")
    wrong = "100000" if kod != "100000" else "100001"
    check(st2.pair_ceo({"id": 5, "first_name": "Q"}, wrong, now_dt) == "xato", "ulash: noto'g'ri kod")
    check(st2.pair_ceo({"id": 6, "first_name": "Ega"}, kod, now_dt) == "ok", "ulash: to'g'ri kod -> CEO")
    check(st2.get_setting("ulash_kodi") is None and st2.ensure_pair_code() is None, "ulash: kod o'chirildi")
    check(st2.pair_ceo({"id": 7}, kod, now_dt) == "band", "ulash: ikkinchi marta -> band")

    # bot mantiqi (Telegramsiz)
    import staff_bot
    import student_bot
    check(student_bot.app_url("https://a.trycloudflare.com", "dars8") == "https://a.trycloudflare.com/app/?dars=8", "app_url dars8")
    check(student_bot.app_url("https://a.trycloudflare.com", "video") == "https://a.trycloudflare.com/app/?tab=video", "app_url video")
    check(student_bot.app_url("https://a.trycloudflare.com", "x<y") == "https://a.trycloudflare.com/app/", "app_url noma'lum")
    check(student_bot.app_url(None) is None, "app_url: manzil yo'q")
    check(student_bot.start_text("Ali", "Muhammadamin", 36).startswith("Salom, Ali!\n\nMuhammadamin fonetika kursiga xush kelibsiz."),
          "start matni")
    check(student_bot.eslatma_text(4) == "Bugungi darsni davom ettiramizmi? Seriyangiz: 4 kun.", "eslatma matni (seriya bilan)")
    check(staff_bot.fmt_dt("2026-10-04T15:48:00+05:00") == "04.10.2026 15:48", "xodim boti: sana formati")
    check(staff_bot.staff_url("https://a.trycloudflare.com") == "https://a.trycloudflare.com/staff/", "xodim boti: /staff/ manzili")
    # 03.10 (SPEC 10.5): xodimlar boti tugmalari endi admin panelni (/admin/) ochadi
    check(staff_bot.admin_url("https://a.trycloudflare.com") == "https://a.trycloudflare.com/admin/", "xodim boti: /admin/ manzili")
    import types
    st3 = dbm.Store(Path(tempfile.mkdtemp()) / "bot.db")
    kod3 = st3.ensure_pair_code()
    svc = types.SimpleNamespace(store=st3, brend="Muhammadamin", base_url="https://x-y.trycloudflare.com", xodim_username="b_bot")
    r = staff_bot.handle_start(svc, {"id": 77, "first_name": "Ega"}, kod3, now_dt)
    check(r.paired and st3.staff_get(77)["role"] == "ceo" and r.button == ("Boshqaruvni ochish", "https://x-y.trycloudflare.com/admin/"),
          "xodim boti: /start KOD -> CEO (tugma -> /admin/)", r)
    r = staff_bot.handle_start(svc, {"id": 78, "first_name": "Boshqa"}, kod3, now_dt)
    check(r.text == "Bu bot faqat Muhammadamin xodimlari uchun." and not r.paired, "xodim boti: kod ishlatilgandan keyin -> begona")
    # 19:00 eslatma kimga boradi
    for uid_, kw in ((1, {}), (2, {"eslatma": 0}), (3, {"blocked": 1}), (4, {}), (5, {})):
        st3.upsert_user({"id": 100 + uid_, "first_name": f"T{uid_}"}, now_dt, "bot")
        if kw:
            with st3._c(True) as c:
                c.execute(f"UPDATE users SET {', '.join(k + '=?' for k in kw)} WHERE id=?", (*kw.values(), 100 + uid_))
    st3.ev_slide(104, 1, 1, now_dt)  # bugun ball bor
    with st3._c(True) as c:
        c.execute("UPDATE users SET last_seen=? WHERE id=105", (dbm.iso(now_dt - timedelta(days=15)),))
    ids = [t["id"] for t in st3.reminder_targets(now_dt)]
    check(ids == [101], "eslatma: faqat eslatma yoqilgan, bloklamagan, bugun balli yo'q, 14 kun ichida kirgan", ids)
    tunnel_tests()
    tokenlar_tests()
    prod_tests()


def tokenlar_tests() -> None:
    """tokenlar.py: getpass, format tekshiruvi, getMe (soxta), ikki xil bot, .env yozish - tokenlar chiqarilmaydi."""
    import builtins
    import contextlib
    import getpass
    import io

    import tokenlar
    tmp_env = Path(tempfile.mkdtemp()) / ".env"
    t1, t2 = "1234567:" + "A" * 35, "7654321:" + "B" * 35
    saved = (config.ENV_FILE, tokenlar.get_me, getpass.getpass, builtins.input)
    try:
        config.ENV_FILE = tmp_env
        tokenlar.get_me = lambda t: {"id": int(t.split(":")[0]), "username": f"bot_{t[:3]}", "first_name": "Sinov"}
        seq = iter(["noto'g'ri", t1, t2])
        getpass.getpass = lambda prompt="": next(seq)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = tokenlar.main()
        txt = tmp_env.read_text(encoding="utf-8") if tmp_env.exists() else ""
        check(rc == 0 and f"TALABA_BOT_TOKEN={t1}" in txt and f"XODIM_BOT_TOKEN={t2}" in txt, "tokenlar: .env yozildi", rc)
        check(t1 not in buf.getvalue() and t2 not in buf.getvalue() and "@bot_123" in buf.getvalue(), "tokenlar: tokenlar ekranga chiqmadi")
        check("Token ko'rinishi noto'g'ri" in buf.getvalue(), "tokenlar: noto'g'ri format rad etildi")
        builtins.input = lambda prompt="": "yo'q"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = tokenlar.main()
        check(rc == 0 and tmp_env.read_text(encoding="utf-8") == txt, "tokenlar: mavjud .env - rozilik bo'lmasa o'zgarmaydi")
        builtins.input = lambda prompt="": "ha"
        seq = iter([t1, t1])
        getpass.getpass = lambda prompt="": next(seq)
        with contextlib.redirect_stdout(io.StringIO()) as b2:
            rc = tokenlar.main()
        check(rc == 1 and "bitta botga" in b2.getvalue() and tmp_env.read_text(encoding="utf-8") == txt, "tokenlar: bitta bot ikki marta -> rad")
        tokenlar.get_me = lambda t: None
        seq = iter([t1, t1, t1])
        with contextlib.redirect_stdout(io.StringIO()) as b3:
            rc = tokenlar.main()
        check(rc == 1 and "qabul qilmadi" in b3.getvalue(), "tokenlar: Telegram rad etgan token -> qayta so'raydi, keyin bekor")
    finally:
        config.ENV_FILE, tokenlar.get_me, getpass.getpass, builtins.input = saved


def prod_tests() -> None:
    """Ishchi rejim .env siz: main.py tushunarli xato bilan chiqadi; boshqar start .env ni so'raydi; holat o'qiladi."""
    import boshqar
    if config.ENV_FILE.exists():
        log("  (o'tkazildi: server/.env bor - ishchi rejim sinovi .env siz qilinadi)")
        return
    hp, pp, lp = OUT / "prod_holat.json", OUT / "prod.pid", OUT / "prod.log"
    for p in (hp, pp):
        try:
            p.unlink()
        except OSError:
            pass
    r = subprocess.run([sys.executable, str(ROOT / "server" / "main.py"), "--port", str(PORT), "--holat", str(hp), "--pid", str(pp),
                        "--log", str(lp)], cwd=str(ROOT), capture_output=True, text=True, timeout=60,
                       creationflags=config.CREATE_NO_WINDOW)
    h = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else {}
    check(r.returncode == 2 and h.get("holat") == "xato" and "1 - Tokenlarni kiritish.bat" in (h.get("xato") or "") and not pp.exists(),
          "ishchi rejim .env siz: chiqish 2, holat.json da tushunarli xato", (r.returncode, h))
    lines: list[str] = []
    check(boshqar.start(out=lines.append) == 1 and "Tokenlarni kiritish" in " ".join(lines), "boshqar start .env siz -> yo'riq", lines)
    lines = []
    boshqar.holat(out=lines.append)
    check(lines and lines[0].startswith("Holat:"), "boshqar holat ishlaydi", lines[:1])


FAKE_CF = r'''
import sys, time
name, life = sys.argv[1], float(sys.argv[2])
e = sys.stderr
print("2026-10-02T10:00:00Z INF Requesting new quick Tunnel on trycloudflare.com...", file=e, flush=True)
print('2026-10-02T10:00:00Z ERR retry error="Post \"https://api.trycloudflare.com/tunnel\": EOF"', file=e, flush=True)
print("2026-10-02T10:00:01Z INF |  Your quick Tunnel has been created! Visit it at:  |", file=e, flush=True)
print(f"2026-10-02T10:00:01Z INF |  https://{name}-beta-gamma-delta.trycloudflare.com  |", file=e, flush=True)
print("2026-10-02T10:00:02Z INF Registered tunnel connection connIndex=0 location=fra", file=e, flush=True)
t0 = time.time()
while time.time() - t0 < life:
    time.sleep(0.1)
'''


def tunnel_tests() -> None:
    """tunnel.py: manzilni ajratish (api.trycloudflare.com e'tiborsiz) va main.tunnel_watch qayta ulanishi."""
    import asyncio
    import types

    import main as mainmod
    import tunnel as tn
    from telegram import MenuButtonWebApp
    check(tn.parse_url("ERR Post \"https://api.trycloudflare.com/tunnel\": EOF") is None, "tunnel: api.trycloudflare.com e'tiborsiz")
    check(tn.parse_url("INF |  https://abc-def-ghi.trycloudflare.com  |") == "https://abc-def-ghi.trycloudflare.com", "tunnel: manzil ajratildi")
    OUT.mkdir(parents=True, exist_ok=True)
    script = OUT / "fake_cloudflared.py"
    script.write_text(FAKE_CF, encoding="utf-8")

    class Bot:
        def __init__(self):
            self.calls = []

        async def set_chat_menu_button(self, menu_button=None, **kw):
            self.calls.append(menu_button)

    async def go():
        t = tn.Tunnel(PORT, exe=Path(sys.executable), args=[str(script), "alpha", "1.5"])
        url = await t.start(timeout=20)
        check(url == "https://alpha-beta-gamma-delta.trycloudflare.com" and t.ready and t.alive(), "tunnel: soxta cloudflared -> manzil", url)
        t.args = [str(script), "omega", "60"]
        apps = [types.SimpleNamespace(bot=Bot()), types.SimpleNamespace(bot=Bot())]
        svc = types.SimpleNamespace(base_url=url)
        hp = OUT / "tunnel_holat.json"
        holat = mainmod.Holat(hp, PORT)
        stop = asyncio.Event()
        mainmod.TUNNEL_TEKSHIRUV = 0.5
        task = asyncio.create_task(mainmod.tunnel_watch(t, svc, apps, holat, stop))
        omega = "https://omega-beta-gamma-delta.trycloudflare.com"
        for _ in range(100):
            if svc.base_url == omega:
                break
            await asyncio.sleep(0.2)
        check(svc.base_url == omega, "tunnel_watch: cloudflared to'xtadi -> qayta ishga tushdi, yangi manzil", svc.base_url)
        m0, m1 = (apps[0].bot.calls or [None])[-1], (apps[1].bot.calls or [None])[-1]
        check(isinstance(m0, MenuButtonWebApp) and m0.web_app.url == omega + "/app/" and m0.text == "Darslar"
              and isinstance(m1, MenuButtonWebApp) and m1.web_app.url == omega + "/admin/" and m1.text == "Boshqaruv",
              "tunnel_watch: ikkala bot menyu tugmasi yangi manzilga", (m0, m1))
        check(json.loads(hp.read_text(encoding="utf-8"))["url"] == omega, "tunnel_watch: holat.json yangilandi")
        stop.set()
        await asyncio.wait_for(task, 5)
        await t.stop()
        check(not t.alive(), "tunnel: to'xtatildi")
    asyncio.run(go())


# ---------------------------------------------------------------- API
def api_tests() -> None:
    log("\n== API (sinov server, port %d) ==" % PORT)
    for suf in ("", "-wal", "-shm"):
        try:
            Path(str(DB) + suf).unlink()
        except OSError:
            pass
    p = start_server(["--sinov", "--port", str(PORT), "--db", str(DB.relative_to(ROOT)), "--seed"])
    try:
        _api_body()
    except Exception:
        check(False, "API sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        graceful = stop_server(p, config.DATA_DIR / f"sinov_{PORT}.stop")
        check(graceful, "server stop fayli bilan yumshoq to'xtadi")


def _api_body() -> None:
    kurs = json.loads((config.CONTENT_DIR / "kurs.json").read_text(encoding="utf-8"))
    lessons = {x["n"]: x for x in kurs["darslar"]}
    test8 = json.loads((config.CONTENT_DIR / "test" / "08.json").read_text(encoding="utf-8"))
    key8 = [q["ok"] for q in test8["savollar"]]

    @contextmanager
    def con():
        c = sqlite3.connect(DB, timeout=20)
        try:
            with c:
                yield c
        finally:
            c.close()

    log("-- autentifikatsiya")
    s, h, b = jhttp("POST", "/api/s/me", {})
    check(s == 401 and b and "xato" in b, "talaba: initData yo'q -> 401", s)
    forged = make(SINOV_TALABA_TOKEN, TALABA["aziza"]).replace("aziza_k", "aziza_x")
    check(jhttp("POST", "/api/s/me", {}, {"X-Init-Data": forged})[0] == 401, "talaba: soxta hash -> 401")
    check(jhttp("POST", "/api/s/me", {}, {"X-Init-Data": make(SINOV_XODIM_TOKEN, TALABA["aziza"])})[0] == 401,
          "talaba: boshqa bot tokeni -> 401")
    check(jhttp("POST", "/api/s/me", {}, S(auth_date=int(time.time()) - 8 * 86400))[0] == 401, "talaba: muddati o'tgan (8 kun) -> 401")
    check(jhttp("POST", "/api/s/me", {}, S(auth_date=int(time.time()) - 6 * 86400))[0] == 200, "talaba: 6 kunlik -> 200")
    check(jhttp("GET", "/api/x/stats")[0] == 401, "xodim: initData yo'q -> 401")
    check(jhttp("GET", "/api/x/stats", None, S("aziza"))[0] == 401, "xodim: talaba boti imzosi -> 401")
    s, _, b = jhttp("GET", "/api/x/stats", None, X("begona"))
    check(s == 403 and b == {"xato": "Bu bo'lim faqat xodimlar uchun"}, "xodim API da talaba (xodim boti imzosi) -> 403", (s, b))
    s, _, b = jhttp("POST", "/api/x/auth", {}, X({"id": 123456, "first_name": "Begona"}))
    check(s == 403, "xodim emas -> 403", s)
    check(jhttp("GET", "/api/x/stats", None, X("ceo", auth_date=int(time.time()) - 25 * 3600))[0] == 401, "xodim: 25 soatlik initData -> 401")
    check(jhttp("GET", "/api/x/stats", None, {"X-Staff-Token": "abc.def"})[0] == 401, "xodim: buzuq X-Staff-Token -> 401")

    log("-- /api/s/me")
    s, h, me = jhttp("POST", "/api/s/me", {}, S("aziza"))
    check(s == 200 and me["user"]["id"] == 800001 and me["prefs"]["uslub"] is None, "me: Aziza, uslub null", me and me.get("prefs"))
    check(set(me["stats"]) >= {"xp", "streak", "best_streak", "today_xp", "goal", "week"} and me["stats"]["goal"] == 30, "me: stats maydonlari")
    wk = me["stats"]["week"]
    today = datetime.now(TZ).date()
    check(len(wk) == 7 and wk[-1]["day"] == today.isoformat() and wk[0]["day"] == (today - timedelta(days=6)).isoformat(),
          "me: week 7 kun, oxirgisi bugun")
    check(me["stats"]["streak"] == 3 and me["stats"]["best_streak"] == 5, "me: seed seriyasi 3, eng uzun 5", me["stats"])
    check(me["progress"]["lessons"]["8"]["seen"] == [1, 2, 3] and me["progress"]["tests"]["8"]["tries"] == 2,
          "me: progress (8-dars 1-3 slayd, test 2 urinish)")
    check(me["progress"]["videos"]["d02"]["pos"] == 312.5, "me: video pozitsiyasi")
    check(me["course"]["open"] == 36, "me: course.open = 36")
    check(h.get("Cache-Control") == "no-store", "API: Cache-Control no-store", h.get("Cache-Control"))
    s, _, me2 = jhttp("POST", "/api/s/me", {}, S("yangi"))
    check(s == 200 and me2["stats"]["xp"] == 0 and me2["user"]["username"] in ("", None), "me: yangi o'quvchi yaratildi")

    log("-- /api/s/prefs")
    s, _, b = jhttp("POST", "/api/s/prefs", {"uslub": "glass", "rejim": "dark", "arab": "l", "eslatma": False}, S("yangi"))
    check(s == 200 and b == {"ok": True}, "prefs: saqlandi")
    pr = jhttp("POST", "/api/s/me", {}, S("yangi"))[2]["prefs"]
    check(pr == {"uslub": "glass", "rejim": "dark", "arab": "l", "eslatma": False}, "prefs: me da ko'rinadi", pr)
    check(jhttp("POST", "/api/s/prefs", {"uslub": "neon"}, S("yangi"))[0] == 400, "prefs: noto'g'ri uslub -> 400")
    check(jhttp("POST", "/api/s/prefs", {"eslatma": "ha"}, S("yangi"))[0] == 400, "prefs: eslatma bool emas -> 400")
    check(jhttp("POST", "/api/s/prefs", {"rejim": "light"}, S("yangi"))[0] == 200, "prefs: qisman yangilash")

    log("-- ketma-ket ochilish (dars faqat oldingisi tugagach)")
    ev = lambda body, who="yangi": jhttp("POST", "/api/s/event", body, S(who))  # noqa: E731
    me_y = jhttp("POST", "/api/s/me", {}, S("yangi"))[2]
    check(me_y["course"]["available"] == [1], "yangi o'quvchi: faqat 1-dars ochiq (course.available)", me_y["course"])
    s, _, b = ev({"type": "slide", "dars": 2, "idx": 1})
    check(s == 403 and b == {"xato": "Avval 1-darsni tugating"}, "2-dars slayd (1-dars tugamagan) -> 403 'Avval 1-darsni tugating'", (s, b))
    s, _, b = ev({"type": "lesson_done", "dars": 9})
    check(s == 403 and b["xato"] == "Avval 8-darsni tugating", "lesson_done 9 (8 tugamagan) -> 403", (s, b))
    s, _, b = ev({"type": "test_done", "dars": 8, "answers": key8})
    check(s == 403 and b["xato"] == "Avval 7-darsni tugating", "test_done 8 (7 tugamagan) -> 403", (s, b))
    s, _, b = ev({"type": "video_pos", "vid": "d02", "pos": 5})
    check(s == 403 and b["xato"] == "Avval 1-darsni tugating", "video 2-dars (1 tugamagan) -> 403", (s, b))
    # 1-dars: 80% slayd + lesson_done -> javobda 2-dars darhol ochiladi
    n1 = lessons[1]["slaydlar"]
    for i in range(1, math.ceil(0.8 * n1) + 1):
        ev({"type": "slide", "dars": 1, "idx": i})
    s, _, b = ev({"type": "lesson_done", "dars": 1})
    check(s == 200 and b["course"]["available"] == [1, 2], "1-dars tugadi -> javobda available [1, 2]", (s, b and b.get("course")))
    check(ev({"type": "slide", "dars": 2, "idx": 1})[0] == 200, "2-dars endi ochiq -> 200")
    # 2..8 darslar tugatilgan deb bazaga yoziladi (keyingi sinovlar uchun)
    uid_y = TALABA["yangi"]["id"]
    with con() as c:
        for n in range(2, 9):
            c.execute("INSERT OR REPLACE INTO lessons(user_id, dars, started_at, done_at) VALUES (?,?,?,?)",
                      (uid_y, n, "2026-10-01T10:00:00+05:00", "2026-10-01T10:05:00+05:00"))
    me_y = jhttp("POST", "/api/s/me", {}, S("yangi"))[2]
    check(me_y["course"]["available"] == list(range(1, 10)), "1-8 tugagan -> available 1..9", me_y["course"]["available"])

    log("-- voqealar va XP")
    s, _, b = ev({"type": "slide", "dars": 9, "idx": 1})
    check(s == 200 and b["xp_added"] == 1 and b["item"]["seen"] == [1], "slayd: +1 XP", b)
    s, _, b = ev({"type": "slide", "dars": 9, "idx": 1})
    check(s == 200 and b["xp_added"] == 0, "slayd: qayta -> 0 XP (idempotent)")
    check(ev({"type": "slide", "dars": 9, "idx": lessons[9]["slaydlar"] + 1})[0] == 400, "slayd: raqam chegaradan tashqari -> 400")
    check(ev({"type": "slide", "dars": 99, "idx": 1})[0] == 400, "slayd: noma'lum dars -> 400")
    check(ev({"type": "slide", "dars": True, "idx": 1})[0] == 400, "slayd: dars bool -> 400")
    check(ev({"type": "nimadir"})[0] == 400, "voqea: noma'lum tur -> 400")
    n9 = lessons[9]["slaydlar"]
    need = math.ceil(0.8 * n9)
    for i in range(2, need):
        ev({"type": "slide", "dars": 9, "idx": i})
    s, _, b = ev({"type": "lesson_done", "dars": 9})
    check(s == 400 and "xato" in b, f"lesson_done: {need - 1}/{n9} -> 400 (80% qoidasi)", (s, b))
    ev({"type": "slide", "dars": 9, "idx": need})
    s, _, b = ev({"type": "lesson_done", "dars": 9})
    check(s == 200 and b["xp_added"] == 20 and b["item"]["done_at"], f"lesson_done: {need}/{n9} -> +20", b)
    check(ev({"type": "lesson_done", "dars": 9})[2]["xp_added"] == 0, "lesson_done: qayta -> 0")
    check(10 in jhttp("POST", "/api/s/me", {}, S("yangi"))[2]["course"]["available"], "9-dars tugadi -> 10-dars ochildi")
    s, _, b = ev({"type": "slide", "dars": 11, "idx": 1})
    check(s == 403 and b["xato"] == "Avval 10-darsni tugating", "11-dars (10 tugamagan) -> 403", (s, b))

    log("-- bir darsda bir nechta video")
    multi = {x["n"]: x.get("videolar") or [] for x in kurs["darslar"]}
    vids = [(n, v["id"]) for n, vs in multi.items() for v in vs]
    check(all(x.get("video") == ((x.get("videolar") or [None])[0]) for x in kurs["darslar"]),
          "kurs.json: 'video' = videolar[0] (moslik)")
    check(len({v for _, v in vids}) == len(vids) and ("d02" in {v for _, v in vids}), "kurs.json: video id lar noyob, d02 bor", vids)
    for n, vid in vids:
        if n <= 9:
            s, _, b = ev({"type": "video_pos", "vid": vid, "pos": 3})
            check(s == 200 and b["item"]["pos"] == 3, f"video_pos {vid} ({n}-dars) -> 200, alohida progress", (s, b))
            s, h, body = http("GET", f"/media/video/{vid}", headers={"Range": "bytes=0-99"})
            check(s == 206 and len(body) == 100 and h.get("Content-Type") == "video/mp4", f"/media/video/{vid} Range -> 206", s)
        s, _, b = jhttp("POST", "/api/s/event", {"type": "video_pos", "vid": vid, "pos": 1}, S({"id": 800090, "first_name": "Yangi2"}))
        exp = 200 if n == 1 else 403
        check(s == exp and (exp == 200 or b["xato"] == f"Avval {n - 1}-darsni tugating"), f"yangi o'quvchi: {vid} ({n}-dars) -> {exp}", (s, b))
    s, _, crs = jhttp("GET", "/api/x/course", None, X("ceo"))
    check(all(x["videolar"] == len(multi[x["n"]]) and x["video"] == bool(multi[x["n"]]) for x in crs["lessons"]),
          "x/course: har dars videolar soni")
    s, _, b = ev({"type": "video_pos", "vid": "d02", "pos": 312.5})
    check(s == 200 and b["xp_added"] == 0 and b["item"]["pos"] == 312.5, "video_pos: XP yo'q, pozitsiya saqlandi", b)
    check(ev({"type": "video_pos", "vid": "d02", "pos": -1})[0] == 400, "video_pos: manfiy -> 400")
    check(ev({"type": "video_pos", "vid": "yoq", "pos": 1})[0] == 400, "video_pos: noma'lum video -> 400")
    s, _, b = ev({"type": "video_done", "vid": "d02"})
    check(s == 200 and b["xp_added"] == 30, "video_done: +30")
    check(ev({"type": "video_done", "vid": "d02"})[2]["xp_added"] == 0, "video_done: qayta -> 0")

    log("-- test (serverda baholash)")
    wrong = [(k + 1) % 4 for k in key8]
    s, _, b = ev({"type": "test_done", "dars": 8, "answers": wrong})
    check(s == 200 and b["correct"] == 0 and b["total"] == len(key8) and b["xp_added"] == 0, "test: hammasi xato -> 0", b)
    three = list(key8[:3]) + wrong[3:]
    b = ev({"type": "test_done", "dars": 8, "answers": three})[2]
    check(b["correct"] == 3 and b["xp_added"] == 12, "test: 3 to'g'ri -> +12", b)
    b = ev({"type": "test_done", "dars": 8, "answers": key8})[2]
    check(b["correct"] == len(key8) and b["xp_added"] == 4 * (len(key8) - 3) + 10 and b["bonus"] == 10 and b["perfect"],
          "test: hammasi to'g'ri -> 4*(5-3)+10", b)
    b = ev({"type": "test_done", "dars": 8, "answers": key8})[2]
    check(b["xp_added"] == 0 and b["item"]["tries"] == 4 and b["item"]["best"] == len(key8), "test: qayta mukammal -> 0, tries 4", b)
    check(ev({"type": "test_done", "dars": 8, "answers": ["1"] * 5})[0] == 400, "test: javoblar matn -> 400")
    check(ev({"type": "test_done", "dars": 8, "answers": [True] * 5})[0] == 400, "test: javoblar bool -> 400")
    check(ev({"type": "test_done", "dars": 8, "answers": [1] * 6})[0] == 400, "test: javoblar ko'p -> 400")
    s9, _, b9 = ev({"type": "test_done", "dars": 9, "answers": [0] * 5})
    check(s9 == 200 and b9["total"] == 5, "test: 9-dars mini testi baholanadi", (s9, b9))
    check(ev({"type": "test_done", "dars": 9, "answers": [0] * 6})[0] == 400, "test: 9-dars ortiqcha javob -> 400")

    log("-- ochiq darslar (403)")
    # 03.10 (SPEC 10.1): ustoz ochiq darslarni endi o'zgartira olmaydi (OCHISH_ROLLARI = ceo, admin)
    s, _, b = jhttp("POST", "/api/x/open", {"n": 5}, X("ustoz"))
    check(s == 403 and "xato" in b, "open: ustoz -> 403 (03.10 dan)", (s, b))
    s, _, b = jhttp("POST", "/api/x/open", {"n": 5}, X("admin"))
    check(s == 200 and b == {"ok": True, "open": 5}, "open: admin 5 ga o'rnatdi", (s, b))
    check(ev({"type": "slide", "dars": 6, "idx": 1})[0] == 403, "voqea: 6-dars (ochiq 5) -> 403")
    check(ev({"type": "test_done", "dars": 8, "answers": key8})[0] == 403, "test: 8-dars yopiq -> 403")
    check(ev({"type": "video_pos", "vid": "d02", "pos": 1})[0] == 200, "video: 2-dars ochiq -> 200")
    check(jhttp("POST", "/api/s/me", {}, S("yangi"))[2]["course"]["open"] == 5, "me: course.open = 5")
    check(jhttp("POST", "/api/x/open", {"n": 6}, X("assistent"))[0] == 403, "open: assistent -> 403")
    check(jhttp("POST", "/api/x/open", {"n": 0}, X("admin"))[0] == 400, "open: 0 -> 400")
    check(jhttp("POST", "/api/x/open", {"n": 37}, X("admin"))[0] == 400, "open: 37 -> 400")
    check(jhttp("POST", "/api/x/open", {"n": 36}, X("ceo"))[2] == {"ok": True, "open": 36}, "open: ceo 36 ga qaytardi")

    log("-- tezlik cheklovi (120 voqea/daqiqa)")
    t_rl = time.time()
    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(lambda _: ev({"type": "slide", "dars": 1, "idx": 1}, "jahongir")[0], range(130)))
    took = time.time() - t_rl
    check(codes.count(200) == 120 and codes.count(429) == 10, "voqealar: 120/daqiqadan keyin 429",
          (codes.count(200), codes.count(429), f"{took:.1f} s"))

    log("-- seriya va haftalik reyting (kun qatorlari to'g'ridan-to'g'ri)")
    uid = 800050
    usr = {"id": uid, "first_name": "Seriya", "last_name": "Sinov", "username": "seriya_s"}
    jhttp("POST", "/api/s/me", {}, S(usr))
    monday = today - timedelta(days=today.weekday())
    rows = [((today - timedelta(days=1)).isoformat(), 5), ((today - timedelta(days=2)).isoformat(), 6),
            ((today - timedelta(days=3)).isoformat(), 7), ((today - timedelta(days=5)).isoformat(), 4),
            ((today - timedelta(days=6)).isoformat(), 4), ((today - timedelta(days=7)).isoformat(), 4),
            ((today - timedelta(days=8)).isoformat(), 4), ((monday - timedelta(days=10)).isoformat(), 9000)]
    # 9000 - bu haftadan oldin; monday-10 (monday-9 emas): dushanba kuni monday-9 = today-9 seriyaga ulanib qolardi
    with con() as c:
        c.execute("DELETE FROM days WHERE user_id=?", (uid,))
        c.executemany("INSERT OR REPLACE INTO days(user_id, day, xp) VALUES (?,?,?)", [(uid, d, x) for d, x in rows])
    st = jhttp("POST", "/api/s/me", {}, S(usr))[2]["stats"]
    check(st["streak"] == 3 and st["best_streak"] == 4 and st["today_xp"] == 0, "seriya: 3 (bugun yo'q), eng uzun 4", st)
    jhttp("POST", "/api/s/event", {"type": "slide", "dars": 1, "idx": 2}, S(usr))
    st = jhttp("POST", "/api/s/me", {}, S(usr))[2]["stats"]
    check(st["streak"] == 4 and st["today_xp"] == 1, "seriya: bugun ball -> 4", st)
    week_xp = sum(x for d, x in rows if d >= monday.isoformat()) + 1
    s, _, rt = jhttp("GET", "/api/s/rating?davr=hafta", None, S(usr))
    check(s == 200 and rt["me"]["xp"] == week_xp, f"reyting hafta: faqat dushanbadan beri ({week_xp})", rt["me"])
    check(rt["top"][0]["rank"] == 1 and len(rt["top"]) <= 20 and all(set(t) >= {"rank", "name", "xp", "streak", "me"} for t in rt["top"]),
          "reyting: maydonlar")
    xs = [t["xp"] for t in rt["top"]]
    check(xs == sorted(xs, reverse=True), "reyting: kamayish tartibida")
    s, _, ru = jhttp("GET", "/api/s/rating?davr=umumiy", None, S(usr))
    check(ru["me"]["rank"] == 1 and ru["me"]["xp"] == sum(x for _, x in rows) + 1 and ru["top"][0]["me"] is True,
          "reyting umumiy: 9000+ ball bilan 1-o'rin, me=true", ru["me"])
    check(ru["top"][0]["name"] == "Seriya S.", "reyting: ism + familiya harfi", ru["top"][0]["name"])
    check(jhttp("GET", "/api/s/rating?davr=yil", None, S(usr))[0] == 400, "reyting: noto'g'ri davr -> 400")
    s, _, rn = jhttp("GET", "/api/s/rating?davr=hafta", None, S({"id": 800077, "first_name": "Nol"}))
    check(s == 200 and rn["me"]["xp"] == 0 and isinstance(rn["me"]["rank"], int), "reyting: balli yo'q -> rank butun son", rn["me"])

    log("-- xodim: statistika")
    s, _, stt = jhttp("GET", "/api/x/stats", None, X("assistent"))
    with con() as c:
        n_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        n_ld = c.execute("SELECT COUNT(*) FROM lessons WHERE done_at IS NOT NULL").fetchone()[0]
        n_vd = c.execute("SELECT COUNT(*) FROM videos WHERE done_at IS NOT NULL").fetchone()[0]
        n_td = c.execute("SELECT COUNT(*) FROM tests WHERE tries>0").fetchone()[0]
        n_act = c.execute("SELECT COUNT(DISTINCT user_id) FROM days WHERE day=?", (today.isoformat(),)).fetchone()[0]
        tot = c.execute("SELECT SUM(xp) FROM days").fetchone()[0]
        xp_today = c.execute("SELECT COALESCE(SUM(xp),0) FROM days WHERE day=?", (today.isoformat(),)).fetchone()[0]
    check(s == 200 and stt["students"] == n_users and stt["lessons_done"] == n_ld and stt["videos_done"] == n_vd
          and stt["tests_done"] == n_td and stt["active_today"] == n_act, "stats: sonlar bazaga mos",
          (stt.get("students"), n_users, stt.get("lessons_done"), n_ld, stt.get("active_today"), n_act))
    check(stt["avg_xp"] == round(tot / n_users), "stats: o'rtacha ball", (stt["avg_xp"], tot, n_users))
    check(sum(stt["styles"].values()) == n_users and sum(stt["modes"].values()) == n_users, "stats: uslub va rejim yig'indisi")
    kk = stt.get("korinish") or {}
    check(kk.get("days") == 14 and len(kk.get("manzara", [])) == 6 and len(kk.get("soat", [])) == 24
          and {"since", "users", "tanlov", "mavzu"} <= set(kk), "stats: korinish (06.10; assistent ham ko'radi)", sorted(kk))
    check(len(stt["daily"]) == 14 and stt["daily"][-1]["day"] == today.isoformat() and stt["daily"][-1]["xp"] == xp_today,
          "stats: daily 14 kun, oxirgisi bugun")
    rc = stt["recent"]
    check(0 < len(rc) <= 20 and [r["at"] for r in rc] == sorted([r["at"] for r in rc], reverse=True)
          and all(r["kind"] in ("lesson_done", "video_done", "test_done") and r["ref"].endswith("-dars") for r in rc),
          "stats: recent <=20, yangisi birinchi, ref 'N-dars'")

    log("-- xodim: o'quvchilar va kurs")
    s, _, sl = jhttp("GET", "/api/x/students?q=aziza", None, X("ustoz"))
    check(s == 200 and any(x["id"] == 800001 for x in sl["students"]) and all("aziza" in (x["name"] + (x["username"] or "")).lower() for x in sl["students"]),
          "students: q=aziza")
    s, _, sl = jhttp("GET", "/api/x/students", None, X("ustoz"))
    keys = {"id", "name", "username", "joined_at", "last_seen", "xp", "streak", "lessons_done", "videos_done", "uslub", "rejim",
            "device_label", "sessions", "last_session_at",  # 03.10 (SPEC 10.6) dan
            "manzara", "mavzu"}  # 06.10: oxirgi ko'rinish (manzarasi bor oxirgi seansdan, yo'q bo'lsa null)
    ls_ = [x["last_seen"] for x in sl["students"]]
    check(len(sl["students"]) == n_users and set(sl["students"][0]) == keys and ls_ == sorted(ls_, reverse=True),
          "students: hammasi, maydonlar, oxirgi faollik bo'yicha")
    s, _, cs = jhttp("GET", "/api/x/course", None, X("assistent"))
    l8 = next(x for x in cs["lessons"] if x["n"] == 8)
    l2 = next(x for x in cs["lessons"] if x["n"] == 2)
    with con() as c:
        d8 = c.execute("SELECT COUNT(*) FROM lessons WHERE dars=8 AND done_at IS NOT NULL").fetchone()[0]
        s8 = c.execute("SELECT COUNT(*) FROM lessons WHERE dars=8").fetchone()[0]
        a8 = c.execute("SELECT AVG(best) FROM tests WHERE dars=8").fetchone()[0]
    check(cs["open"] == 36 and len(cs["lessons"]) == 36 and l8["test"] is True and l2["video"] is True and l8["video"] is False,
          "course: 36 dars, test/video belgilari")
    check(l8["done"] == d8 and l8["started"] == s8 and l8["test_avg"] == round(a8, 1) and l8["slaydlar"] == lessons[8]["slaydlar"],
          "course: 8-dars sonlari bazaga mos", (l8, d8, s8, a8))

    log("-- xodim: auth, panellar, takliflar")
    s, _, au = jhttp("POST", "/api/x/auth", {}, X("ceo"))
    check(s == 200 and au["role"] == "ceo" and au["brend"] == "Muhammadamin" and [p["key"] for p in au["panels"]] == ["ceo", "admin", "lms", "ustoz"],
          "auth: ceo panellari", au and [p["key"] for p in au.get("panels", [])])
    exp_panels = {"admin": ["admin", "lms"], "ustoz": ["ustoz", "lms"], "assistent": ["assistent"]}
    toks = {"ceo": au["token"]}
    for role, keys_ in exp_panels.items():
        a = jhttp("POST", "/api/x/auth", {}, X(role))[2]
        toks[role] = a["token"]
        check([p["key"] for p in a["panels"]] == keys_, f"auth: {role} panellari {keys_}")
    lms = next(p for p in au["panels"] if p["key"] == "lms")
    check(lms["url"].startswith("/staff/p/Admin_paneli.html?rejim=lms&t="), "auth: lms URL", lms["url"])
    check(jhttp("GET", "/api/x/stats", None, {"X-Staff-Token": au["token"]})[0] == 200, "X-Staff-Token bilan API -> 200")
    for p in au["panels"]:
        s, h, body = http("GET", p["url"])
        check(s == 200 and b'<meta name="referrer" content="no-referrer">' in body[:3000]
              and b'telegram-web-app.js?59' in body[:3000] and body.rstrip().endswith(b'<script src="/staff/adapter.js"></script></body></html>'),
              f"panel {p['key']}: 200 + inyeksiya", (s, body[:120]))
    s, h, body = http("GET", au["panels"][0]["url"])
    check(h.get("Cache-Control") == "private, no-cache" and h.get("ETag"), "panel: no-cache + ETag", h.get("Cache-Control"))
    check(http("GET", au["panels"][0]["url"], headers={"If-None-Match": h.get("ETag", "")})[0] == 304, "panel: If-None-Match -> 304")
    tampered = au["token"][:-2] + ("00" if not au["token"].endswith("00") else "11")
    s, h, _ = http("GET", "/staff/p/CEO_paneli.html?t=" + tampered)
    check(s == 302 and h.get("Location") == "/staff/", "panel: buzilgan token -> 302 /staff/", (s, h.get("Location")))
    secret = auth.load_secret()
    expired = auth.make_panel_token(secret, 900001, "ceo", ttl=-10)
    check(http("GET", "/staff/p/CEO_paneli.html?t=" + expired)[0] == 302, "panel: muddati o'tgan token -> 302")
    check(http("GET", "/staff/p/CEO_paneli.html")[0] == 302, "panel: tokensiz -> 302")
    check(http("GET", "/staff/p/CEO_paneli.html?t=" + toks["ustoz"])[0] == 302, "panel: ustoz CEO panelini ocholmaydi -> 302")
    check(http("GET", "/staff/p/Admin_paneli.html?t=" + toks["ustoz"])[0] == 302, "panel: ustoz to'liq Admin panelini ocholmaydi")
    check(http("GET", "/staff/p/Admin_paneli.html?rejim=lms&t=" + toks["ustoz"])[0] == 200, "panel: ustoz LMS ni ochadi")
    check(http("GET", "/staff/p/Ustoz_paneli.html?t=" + toks["assistent"])[0] == 302, "panel: assistent ustoz rejimini ocholmaydi")
    check(http("GET", "/staff/p/Ustoz_paneli.html?rejim=assistent&t=" + toks["assistent"])[0] == 200, "panel: assistent rejimi -> 200")
    check(http("GET", "/staff/p/Nomalum.html?t=" + au["token"])[0] == 404, "panel: noma'lum fayl -> 404")
    fake_role = auth.make_panel_token(secret, 900004, "ceo")  # imzo to'g'ri, lekin bazada u assistent
    check(http("GET", "/staff/p/CEO_paneli.html?t=" + fake_role)[0] == 302, "panel: rol bazadan olinadi (tokendagi emas)")

    s, _, inv = jhttp("POST", "/api/x/invite", {"role": "ustoz"}, X("ceo"))
    check(s == 200 and inv["link"].startswith(f"https://t.me/{config.SINOV_XODIM_USERNAME}?start=t_") and inv["expires"],
          "invite: ceo havola oldi", inv)
    check(jhttp("POST", "/api/x/invite", {"role": "ustoz"}, X("admin"))[0] == 403, "invite: admin -> 403")
    check(jhttp("POST", "/api/x/invite", {"role": "ceo"}, X("ceo"))[0] == 400, "invite: ceo roli -> 400")
    code = inv["link"].split("start=t_", 1)[1]
    st = dbm.Store(DB)
    nowd = dbm.now_tz()
    check(st.invite_redeem(code, {"id": 900010, "first_name": "Yangi", "last_name": "Ustoz"}, nowd) == ("ustoz", None), "invite: ishlatildi")
    check(st.invite_redeem(code, {"id": 900011, "first_name": "Boshqa"}, nowd)[1] == "yaroqsiz", "invite: bir martalik")
    code2 = jhttp("POST", "/api/x/invite", {"role": "admin"}, X("ceo"))[2]["link"].split("start=t_", 1)[1]
    with con() as c:
        c.execute("UPDATE invites SET expires_at=? WHERE code=?", (dbm.iso(nowd - timedelta(minutes=1)), code2))
    check(st.invite_redeem(code2, {"id": 900012, "first_name": "Kech"}, nowd)[1] == "yaroqsiz", "invite: muddati o'tgan")

    s, _, sf = jhttp("GET", "/api/x/staff", None, X("ceo"))
    check(s == 200 and {x["id"] for x in sf["staff"]} >= {900001, 900002, 900003, 900004, 900010}
          and set(sf["staff"][0]) == {"id", "name", "username", "role", "added_at"}, "staff: ro'yxat")
    check(jhttp("GET", "/api/x/staff", None, X("admin"))[0] == 403, "staff: admin -> 403")
    check(jhttp("POST", "/api/x/staff/remove", {"id": 900001}, X("ceo"))[0] == 400, "staff/remove: o'zini -> 400")
    check(jhttp("POST", "/api/x/staff/remove", {"id": 900010}, X("admin"))[0] == 403, "staff/remove: admin -> 403")
    check(jhttp("POST", "/api/x/staff/remove", {"id": 900010}, X("ceo"))[2] == {"ok": True}, "staff/remove: ceo o'chirdi")
    gone = {"id": 900010, "first_name": "Yangi", "last_name": "Ustoz"}
    check(jhttp("GET", "/api/x/stats", None, X(gone))[0] == 403, "o'chirilgan xodim -> 403")
    check(jhttp("POST", "/api/x/staff/remove", {"id": 999}, X("ceo"))[0] == 400, "staff/remove: yo'q xodim -> 400")

    log("-- PDF")
    s, _, b = jhttp("POST", "/api/s/pdf", {"dars": 8}, S("aziza"))
    check(s == 200 and b == {"ok": True, "sinov": True}, "pdf: sinovda yubormaydi", (s, b))
    s, _, b = jhttp("POST", "/api/s/pdf", {"dars": 8}, S("aziza"))
    check(s == 429, "pdf: 20 s ichida qayta -> 429", (s, b))
    check(jhttp("POST", "/api/s/pdf", {"dars": 99}, S("jahongir"))[0] == 400, "pdf: noma'lum dars -> 400")
    with con() as c:
        c.executemany("INSERT INTO events(user_id, kind, ref, xp, at) VALUES (800003, 'pdf', '1', 0, ?)",
                      [(dbm.iso(nowd - timedelta(seconds=30 + i)),) for i in range(15)])
    check(jhttp("POST", "/api/s/pdf", {"dars": 1}, S({"id": 800003, "first_name": "Malika"}))[0] == 429, "pdf: kuniga 15 tadan keyin -> 429")

    log("-- marshrutlar, sarlavhalar, kesh")
    s, h, _ = http("GET", "/")
    check(s == 302 and h.get("Location") == "/app/", "/ -> 302 /app/")
    for path in ("/staff/", "/staff/staff.js", "/staff/staff.css", "/content/kurs.json", "/shared/icons.svg", "/shared/fonts.css"):
        s, h, _ = http("GET", path)
        if s == 404:
            log(f"  (o'tkazildi: {path} hali yo'q)")
            continue
        check(s == 200 and h.get("Cache-Control") == "no-cache" and h.get("ETag") and h.get("Last-Modified"),
              f"kesh no-cache + ETag: {path}", (s, h.get("Cache-Control")))
        check(h.get("X-Content-Type-Options") == "nosniff" and h.get("Referrer-Policy") == "no-referrer", f"xavfsizlik sarlavhalari: {path}")
    s, h, _ = http("GET", "/staff/staff.js")
    if s == 200:
        check(h.get("Content-Type", "").startswith("text/javascript"), "MIME: .js -> text/javascript", h.get("Content-Type"))
        check(http("GET", "/staff/staff.js", headers={"If-None-Match": h["ETag"]})[0] == 304, "statik: If-None-Match -> 304")
    fonts = sorted((config.SHARED_DIR / "fonts").glob("*.woff2"))
    if fonts:
        s, h, _ = http("GET", "/shared/fonts/" + fonts[0].name)
        check(s == 200 and h.get("Cache-Control") == "public, max-age=604800" and h.get("Content-Type") == "font/woff2",
              "kesh: shrift 7 kun", (s, h.get("Cache-Control"), h.get("Content-Type")))
    s, h, _ = http("GET", "/content/dars/01/001.webp")
    if s == 200:
        check(h.get("Cache-Control") == "public, max-age=604800" and h.get("Content-Type") == "image/webp", "kesh: slayd rasmi 7 kun")
    s, h, _ = http("GET", "/app/")
    check(s in (200, 404), "/app/ javob beradi", s)
    if s == 200:
        check(h.get("Cache-Control") == "no-cache" and h.get("Content-Type", "").startswith("text/html"), "/app/: html no-cache")
    check(http("GET", "/app")[0] == 302 and http("GET", "/staff")[0] == 302, "/app va /staff -> 302")
    s, h, b = http("GET", "/api/yoq")
    check(s == 404 and json.loads(b) == {"xato": "Topilmadi"}, "noma'lum API -> 404 JSON")
    s, h, b = http("POST", "/api/s/event", raw_body=b"{buzuq", headers=S({"id": 800004, "first_name": "Sardor"}))
    check(s == 400, "buzuq JSON -> 400", s)
    big = json.dumps({"type": "slide", "dars": 1, "idx": 1, "pad": "x" * 70000}).encode()
    s, h, b = http("POST", "/api/s/event", raw_body=big, headers=S({"id": 800003, "first_name": "Malika"}))
    check(s == 413, "64 KB dan katta so'rov -> 413", s)
    check(http("GET", "/content/")[0] == 404 and http("GET", "/content/dars/")[0] == 404, "papka ro'yxati yo'q -> 404")

    log("-- yo'l chetlab o'tish (traversal)")
    attacks = ["/content/..%2F..%2Fserver%2F.env", "/content/..%2F..%2Fserver%2Fconfig.py", "/staff/p/../../server/config.py",
               "/staff/p/..%2F..%2Fserver%2Fconfig.py", "/content/%2e%2e/%2e%2e/server/config.py", "/shared/..%5C..%5Cserver%5Cconfig.py",
               "/app/..%2F..%2Fserver%2Fdb.py", "/content/kurs.json%00.png", "/content/NUL", "/content/dars/../../server/main.py",
               "/staff/p%2FCEO_paneli.html", "/staff/P%2FCEO_paneli.html", "/staff/p/CEO_paneli.html%2F..%2F..%2F..%2Fserver%2Fconfig.py",
               "/content/C:%5CWindows%5Cwin.ini", "/media/video/..%2F..%2Fserver%2Fvideolar.json", "/shared/%2e%2e/%2e%2e/data/secret.key",
               "/content/.%2F.%2F..%2F..%2Fdata%2Fsecret.key", "/staff/./p/CEO_paneli.html"]
    for a in attacks:
        s, h, body = raw(a)
        check(s in (400, 404) or (s == 302 and h.get("Location") == "/staff/"), f"traversal rad: {a}", (s, body[:80]))
        check(b"SINOV" not in body and b"TALABA_BOT_TOKEN" not in body and b"import " not in body, f"traversal: maxfiy mazmun yo'q: {a}")

    log("-- video (Range)")
    vfile = config.VIDEOLAR_FILE
    vids = json.loads(vfile.read_text(encoding="utf-8")) if vfile.exists() else []
    if vids and Path(vids[0]["fayl"]).is_file():
        size = Path(vids[0]["fayl"]).stat().st_size
        s, h, b = http("GET", f"/media/video/{vids[0]['id']}", headers={"Range": "bytes=0-1023"})
        check(s == 206 and h.get("Content-Range") == f"bytes 0-1023/{size}" and len(b) == 1024 and h.get("Content-Type") == "video/mp4"
              and h.get("Accept-Ranges") == "bytes", "video: 206 + Content-Range", (s, h.get("Content-Range"), h.get("Content-Type")))
        s, h, b = http("GET", f"/media/video/{vids[0]['id']}", headers={"Range": f"bytes={size - 100}-"})
        check(s == 206 and len(b) == 100 and h.get("Content-Range") == f"bytes {size - 100}-{size - 1}/{size}", "video: oxirgi 100 bayt")
        check(h.get("Cache-Control") == "public, max-age=604800", "video: kesh 7 kun")
        s, h, _ = raw(f"/media/video/{vids[0]['id']}", {"Range": f"bytes={size + 10}-"})
        check(s == 416, "video: chegaradan tashqari Range -> 416", s)
    else:
        check(False, "video fayli topilmadi (server/videolar.json)")
    check(http("GET", "/media/video/yoq")[0] == 404, "video: noma'lum id -> 404")


# ---------------------------------------------------------------- ishga tushirish
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--faqat", choices=["unit", "api", "tg", "qa"])
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--db", default=str(DB.relative_to(ROOT)))
    ap.add_argument("--out", default=str(OUT.relative_to(ROOT)))
    a = ap.parse_args()
    configure(a.port, ROOT / a.db, ROOT / a.out)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.faqat in (None, "unit"):
        unit_tests()
    if a.faqat in (None, "api"):
        api_tests()
    if a.faqat in (None, "tg"):
        import test_server_tg
        test_server_tg.run(check, log)
    if a.faqat in (None, "qa"):
        import test_server_qa
        test_server_qa.run(check, log, sys.modules[__name__])
    log(f"\nNATIJA: {R.ok} ta OK, {len(R.fails)} ta XATO ({time.time() - t0:.0f} s)")
    for f in R.fails:
        log("  - " + f)
    (OUT / "natija.txt").write_text("\n".join(R.lines), encoding="utf-8")
    return 0 if not R.fails else 1


if __name__ == "__main__":
    sys.exit(main())

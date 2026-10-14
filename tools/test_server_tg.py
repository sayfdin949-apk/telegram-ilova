"""E2E sinov: haqiqiy ishchi kod yo'li (main.py --fake-tg) + soxta Telegram + boshqar.start/stop.

    python tools/test_server.py --faqat tg      (yoki to'g'ridan-to'g'ri: python tools/test_server_tg.py)

Tekshiriladi: botlar ishga tushganda menyu tugmalari/buyruqlar/tavsiflar, /start (talaba), ulash kodi -> CEO,
/taklif + taklif havolasi (bir martalik), CEO ga xabarnoma, /ochiq 12 (API da ko'rinadi), /statistika, /xodimlar,
PDF yuborish (birinchi yuklash, keyin file_id keshi), 19:00 eslatma va 21:00 hisobot (--jobs-now), Forbidden,
matnlarda emoji/diniy so'z yo'qligi, web_app manzillari, loglarda token yo'qligi, yumshoq to'xtatish.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import boshqar  # noqa: E402
import config  # noqa: E402
import jarayon  # noqa: E402
from fake_telegram import FakeTelegram  # noqa: E402
from sinov_initdata import SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN, XODIM, make  # noqa: E402

PORT = 8796
DB = ROOT / "data" / "sinov_qa_server_tg.db"
OUT = ROOT / "_sinov" / "qa-server"
HOLAT = OUT / "tg_holat.json"
PID = OUT / "tg_main.pid"
BASE = f"http://127.0.0.1:{PORT}"
JOBS_AFTER = 55  # soniya: kunlik vazifalar shundan keyin bir marta ishlaydi (03.10: /kirish qadamlari qo'shildi)

EMOJI_RE = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2B00, 0x2BFF), (0x2190, 0x21FF))) + chr(0xFE0F) + chr(0x200D) + "]")
DINIY = ("assalomu", "alaykum", "bismillah", "insha", "alloh", "duo", "namoz")

ALI = {"id": 700001, "first_name": "Ali", "last_name": "Valiyev", "username": "ali_v", "language_code": "uz"}
BLOK = {"id": 700002, "first_name": "Bloklangan", "language_code": "uz"}
BOTIR = {"id": 700003, "first_name": "Botir", "last_name": "Sobirov", "username": "botir_s", "language_code": "uz"}
CEO = XODIM["ceo"]
USTOZ = XODIM["ustoz"]
BEGONA = {"id": 900009, "first_name": "Begona", "language_code": "uz"}
IKKINCHI = {"id": 900005, "first_name": "Ikkinchi", "language_code": "uz"}


def api(method: str, path: str, body=None, init: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if init:
        h["X-Init-Data"] = init
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def run(check, log) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (DB, Path(str(DB) + "-wal"), Path(str(DB) + "-shm"), HOLAT, PID):
        try:
            p.unlink()
        except OSError:
            pass
    fake = FakeTelegram()
    fake.fail_once.add("setchatmenubutton")  # menyu tugmasi birinchi urinishda xato -> server qayta urinishi kerak
    fake.conflict_polls = 2                   # birinchi getUpdates lar 409 Conflict -> polling davom etishi kerak
    url = fake.start()
    log(f"\n== SOXTA TELEGRAM (e2e): {url} ==")
    out: list[str] = []
    t_start = time.time()
    code = boshqar.start(extra_args=["--fake-tg", url, "--port", str(PORT), "--db", str(DB.relative_to(ROOT)),
                                     "--holat", str(HOLAT), "--pid", str(PID), "--jobs-now", str(JOBS_AFTER)],
                         holat_path=HOLAT, pid_path=PID, wait=60, out=out.append, scan=False)
    (OUT / "tg_boshqar_start.txt").write_text("\n".join(out), encoding="utf-8")
    check(code == 0 and any("Botlar ishga tushdi" in s for s in out), "boshqar.start: pythonw main.py --fake-tg ishga tushdi", out)
    try:
        h = json.loads(HOLAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        h = {}
    pid = int(h.get("pid") or 0)
    try:
        _body(check, log, fake, h, out, t_start)
    except Exception:
        import traceback
        check(False, "e2e kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        sout: list[str] = []
        if pid:
            boshqar.stop(holat_path=HOLAT, pid_path=PID, only_pids={pid}, out=sout.append)
            t0 = time.time()
            while time.time() - t0 < 15 and jarayon.pid_alive(pid):
                time.sleep(0.3)
            check(not jarayon.pid_alive(pid), "boshqar.stop: jarayon to'xtadi", sout)
            h2 = boshqar.read_holat(HOLAT) or {}
            check(h2.get("holat") == "to'xtadi" and not PID.exists(), "to'xtagandan keyin: holat 'to'xtadi', pid fayli o'chirildi", h2.get("holat"))
            logtxt = (config.LOG_DIR / f"sinov_{PORT}.log").read_text(encoding="utf-8", errors="ignore")
            check("to'xtatish so'raldi" in logtxt.split("ishga tushmoqda (rejim fake")[-1], "yumshoq to'xtatish (stop fayli) ishladi")
            check(SINOV_TALABA_TOKEN not in logtxt and SINOV_XODIM_TOKEN not in logtxt and "SINOVtalaba" not in logtxt,
                  "logda tokenlar yo'q")
        fake.stop()


def _texts(fake) -> list[tuple[str, str]]:
    out = []
    for c in fake.get_calls():
        p = c["params"]
        for k in ("text", "caption", "description", "short_description"):
            if isinstance(p.get(k), str):
                out.append((c["method"], p[k]))
        rm = p.get("reply_markup")
        if isinstance(rm, dict):
            for row in rm.get("inline_keyboard", []):
                for b in row:
                    out.append((c["method"] + ".button", b.get("text", "")))
        mb = p.get("menu_button")
        if isinstance(mb, dict):
            out.append(("menu_button", mb.get("text", "")))
        for cmd in p.get("commands") or []:
            if isinstance(cmd, dict):
                out.append(("command", cmd.get("description", "")))
    return out


def _web_app_urls(fake) -> list[str]:
    urls = []
    for c in fake.get_calls():
        p = c["params"]
        rm = p.get("reply_markup")
        if isinstance(rm, dict):
            for row in rm.get("inline_keyboard", []):
                for b in row:
                    if "web_app" in b:
                        urls.append(b["web_app"]["url"])
        mb = p.get("menu_button")
        if isinstance(mb, dict) and "web_app" in mb:
            urls.append(mb["web_app"]["url"])
    return urls


def _say(fake, bot: str, who: dict, text: str, pred=None, timeout: float = 15):
    """Xabar yuboradi va botning shu chatga javobini kutadi."""
    m = fake.mark()
    fake.push_message(bot, who, text)
    return fake.wait_for(lambda c: c["bot"] == bot and c["method"] == "sendMessage" and c.get("chat_id") == who["id"]
                         and (pred is None or pred(c)), timeout=timeout, start=m)


def _button(c) -> dict | None:
    try:
        return c["params"]["reply_markup"]["inline_keyboard"][0][0]
    except (KeyError, IndexError, TypeError):
        return None


def _body(check, log, fake, h: dict, out: list[str], t_start: float) -> None:
    kod = h.get("ulash_kodi") or ""
    check(h.get("url") == BASE and h.get("talaba_bot") == "noon_talaba_sinov_bot" and h.get("xodim_bot") == "noon_xodim_sinov_bot"
          and re.fullmatch(r"\d{6}", kod), "holat.json: url, bot nomlari, 6 xonali ulash kodi", h)
    check(any(f"Xodimlar botiga shu kodni yuboring: {kod}" in s for s in out), "boshqar.start ulash kodini ko'rsatdi")
    check(any("https://t.me/noon_talaba_sinov_bot" in s for s in out) and any(f"{BASE}/app/" in s for s in out),
          "boshqar.start havolalarni ko'rsatdi")

    t0 = time.time()
    while time.time() - t0 < 20 and not (fake.polls["talaba"] and fake.polls["xodim"]):
        time.sleep(0.1)
    check(fake.polls["talaba"] > 0 and fake.polls["xodim"] > 0, "ikkala bot getUpdates bilan so'rov qilmoqda")
    check(fake.conflicts_sent == 2, "409 Conflict dan keyin polling davom etdi", fake.conflicts_sent)

    log("-- boshqar: holat, ikkinchi start, yagona nusxa")
    pid = int(h.get("pid") or 0)
    lines: list[str] = []
    boshqar.holat(holat_path=HOLAT, pid_path=PID, out=lines.append)
    check(lines and lines[0].startswith(f"Holat: ishlayapti (PID {pid},") and any(kod in s for s in lines), "boshqar.holat", lines[:3])
    lines = []
    rc = boshqar.start(extra_args=["--fake-tg", "http://127.0.0.1:1", "--port", str(PORT)], holat_path=HOLAT, pid_path=PID,
                       wait=5, out=lines.append, scan=False)
    check(rc == 0 and lines and lines[0] == f"Server allaqachon ishlayapti (PID {pid}).", "boshqar.start: ishlab turganda qayta ishga tushirmaydi", lines[:2])
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "server" / "main.py"), "--fake-tg", "http://127.0.0.1:1", "--port", str(PORT),
                        "--db", str(DB.relative_to(ROOT)), "--holat", str(OUT / "tg_holat_ikkinchi.json"), "--pid", str(PID)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=60, creationflags=config.CREATE_NO_WINDOW)
    check(r.returncode == 3 and not (OUT / "tg_holat_ikkinchi.json").exists(), "main.py: ikkinchi nusxa (main.pid band) -> chiqish kodi 3",
          (r.returncode, r.stderr[-200:]))
    check(jarayon.pid_alive(pid), "birinchi nusxa ishlashda davom etmoqda")

    log("-- ishga tushganda: buyruqlar, tavsif, menyu tugmasi")
    # 03.10 (SPEC 10.5): xodimlar botining menyusi admin panelni (/admin/) ochadi
    for bot, menu_text, path in (("talaba", "Darslar", "/app/"), ("xodim", "Boshqaruv", "/admin/")):
        calls = fake.get_calls(bot)
        methods = [c["method"] for c in calls]
        dw = [c for c in calls if c["method"] == "deleteWebhook"]
        check("getMe" in methods and dw and str(dw[0]["params"].get("drop_pending_updates")).lower() == "true",
              f"{bot}: getMe + deleteWebhook(drop_pending_updates)")
        for mth in ("setMyCommands", "setMyDescription", "setMyShortDescription", "setChatMenuButton"):
            check(mth in methods, f"{bot}: {mth} chaqirildi")
        mb = [c for c in calls if c["method"] == "setChatMenuButton"]
        mbp = mb[-1]["params"].get("menu_button") if mb else None
        check(mbp == {"type": "web_app", "text": menu_text, "web_app": {"url": BASE + path}}, f"{bot}: menyu tugmasi -> {path}", mbp)
        cm = [c for c in calls if c["method"] == "setMyCommands"]
        cmds = cm[-1]["params"].get("commands") if cm else []
        check(isinstance(cmds, list) and len(cmds) >= 3 and all(re.fullmatch(r"[a-z_]{1,32}", x["command"]) for x in cmds),
              f"{bot}: buyruqlar ro'yxati", cmds)

    log("-- talabalar boti")
    c = _say(fake, "talaba", ALI, "/start")
    check(c and c["params"]["text"].startswith("Salom, Ali!\n\nMuhammadamin fonetika kursiga xush kelibsiz. Bu yerda 36 ta dars")
          and c["params"]["text"].endswith("Pastdagi tugma orqali darslarni oching."), "/start: salomlashish matni", c and c["params"]["text"])
    check(c and _button(c) == {"text": "Darslarni ochish", "web_app": {"url": BASE + "/app/"}}, "/start: web_app tugmasi", c and _button(c))
    c = _say(fake, "talaba", ALI, "/start dars8")
    check(c and _button(c)["web_app"]["url"] == BASE + "/app/?dars=8", "/start dars8 -> ?dars=8", c and _button(c))
    c = _say(fake, "talaba", ALI, "/video")
    check(c and _button(c)["web_app"]["url"] == BASE + "/app/?tab=video", "/video -> ?tab=video", c and _button(c))
    c = _say(fake, "talaba", ALI, "/darslar")
    check(c and _button(c)["web_app"]["url"] == BASE + "/app/?tab=darslar", "/darslar -> ?tab=darslar")
    c = _say(fake, "talaba", ALI, "/yordam")
    check(c and "/darslar" in c["params"]["text"] and "/video" in c["params"]["text"], "/yordam: buyruqlar")
    c = _say(fake, "talaba", ALI, "salom")
    check(c and _button(c) is not None, "oddiy matn -> yo'l-yo'riq + tugma")
    _say(fake, "talaba", BLOK, "/start")
    _say(fake, "talaba", BOTIR, "/start")
    con = sqlite3.connect(DB, timeout=20)
    try:
        r = con.execute("SELECT first_name, username, pm_ok FROM users WHERE id=?", (ALI["id"],)).fetchone()
        check(r == ("Ali", "ali_v", 1), "talaba bazaga yozildi (pm_ok=1)", r)
    finally:
        con.close()

    log("-- xodimlar boti: ulash")
    c = _say(fake, "xodim", BEGONA, "/start")
    check(c and c["params"]["text"].startswith("Bu bot faqat Muhammadamin xodimlari uchun.") and "4 - Holat.bat" in c["params"]["text"]
          and kod not in c["params"]["text"] and _button(c) is None,
          "ulanmagan bot: begona /start -> rad + egasiga yo'riq (kod oshkor emas)", c and c["params"]["text"])
    wrong = "100000" if kod != "100000" else "100001"
    c = _say(fake, "xodim", CEO, wrong)
    check(c and c["params"]["text"].startswith("Kod noto'g'ri"), "noto'g'ri kod -> rad", c and c["params"]["text"])
    c = _say(fake, "xodim", CEO, kod)
    check(c and "CEO sifatida ulandingiz" in c["params"]["text"] and _button(c) == {"text": "Boshqaruvni ochish", "web_app": {"url": BASE + "/admin/"}},
          "to'g'ri kod -> CEO + Boshqaruv tugmasi (/admin/)", c and c["params"])
    time.sleep(0.5)
    check((boshqar.read_holat(HOLAT) or {}).get("ulash_kodi") is None, "holat.json: ulash kodi o'chirildi")
    c = _say(fake, "xodim", BEGONA, kod)
    check(c and c["params"]["text"] == "Bu bot faqat Muhammadamin xodimlari uchun.", "kodni qayta ishlatib bo'lmaydi")
    c = _say(fake, "xodim", CEO, "/start")
    check(c and c["params"]["text"] == "Salom, Muhammad! Rolingiz: CEO.", "CEO /start: rol", c and c["params"]["text"])
    s, b = api("POST", "/api/x/auth", {}, make(SINOV_XODIM_TOKEN, CEO))
    check(s == 200 and b["role"] == "ceo", "xodim API: ulangan CEO kira oladi", (s, b and b.get("role")))

    log("-- takliflar")
    c = _say(fake, "xodim", CEO, "/taklif ustoz")
    m = re.search(r"https://t\.me/noon_xodim_sinov_bot\?start=t_([A-Za-z0-9_-]+)", c["params"]["text"]) if c else None
    check(m is not None and "bir marta" in c["params"]["text"], "/taklif ustoz -> havola", c and c["params"]["text"])
    inv = m.group(1) if m else "yoq"
    mk = fake.mark()
    c = _say(fake, "xodim", USTOZ, f"/start t_{inv}")
    check(c and "Rolingiz: Ustoz" in c["params"]["text"] and _button(c)["web_app"]["url"] == BASE + "/admin/", "taklif ishlatildi -> Ustoz",
          c and c["params"]["text"])
    n = fake.wait_for(lambda x: x["method"] == "sendMessage" and x.get("chat_id") == CEO["id"] and "Yangi xodim qo'shildi" in x["params"]["text"],
                      start=mk)
    check(n and n["params"]["text"] == "Yangi xodim qo'shildi: Dilnoza Karimova (@dilnoza_k) - Ustoz.", "CEO ga xabarnoma", n and n["params"]["text"])
    c = _say(fake, "xodim", IKKINCHI, f"/start t_{inv}")
    check(c and "yaroqsiz" in c["params"]["text"], "taklif ikkinchi marta -> yaroqsiz", c and c["params"]["text"])
    c = _say(fake, "xodim", USTOZ, "/taklif admin")
    check(c and c["params"]["text"] == "Bu buyruq faqat CEO uchun.", "ustoz /taklif -> rad")
    c = _say(fake, "xodim", CEO, "/taklif")
    check(c and c["params"]["text"].startswith("Foydalanish: /taklif"), "/taklif argumentsiz -> yo'riq")

    log("-- /ochiq, /statistika, /xodimlar")
    # 03.10 (SPEC 10.1): ustoz endi faqat ko'radi; o'zgartirish - CEO va admin
    c = _say(fake, "xodim", USTOZ, "/ochiq 12")
    check(c and "faqat CEO yoki admin" in c["params"]["text"], "ustoz /ochiq 12 -> rad (03.10 dan)", c and c["params"]["text"])
    c = _say(fake, "xodim", USTOZ, "/ochiq")
    check(c and c["params"]["text"].startswith("Ochiq darslar: 36 / 36."), "ustoz /ochiq -> faqat ko'rish", c and c["params"]["text"])
    c = _say(fake, "xodim", CEO, "/ochiq 12")
    check(c and c["params"]["text"].startswith("Saqlandi. Ochiq darslar: 12 / 36."), "CEO /ochiq 12", c and c["params"]["text"])
    s, b = api("POST", "/api/s/me", {}, make(SINOV_TALABA_TOKEN, ALI))
    check(s == 200 and b["course"]["open"] == 12, "talaba API: course.open = 12", (s, b and b.get("course")))
    s, b = api("POST", "/api/s/event", {"type": "slide", "dars": 13, "idx": 1}, make(SINOV_TALABA_TOKEN, ALI))
    check(s == 403, "talaba: 13-dars yopiq -> 403", s)
    c = _say(fake, "xodim", CEO, "/ochiq")
    check(c and c["params"]["text"].startswith("Ochiq darslar: 12 / 36."), "CEO /ochiq -> ko'rsatadi")
    c = _say(fake, "xodim", CEO, "/ochiq 99")
    check(c and c["params"]["text"].startswith("Foydalanish: /ochiq"), "/ochiq 99 -> yo'riq")
    log("-- /kirish (admin panelga brauzer orqali)")
    c = _say(fake, "xodim", CEO, "/kirish")
    b = _button(c) if c else None
    check(c and b and b.get("text") == "Admin panelni ochish" and "web_app" not in b
          and re.fullmatch(re.escape(BASE) + r"/admin/kirish\?k=[A-Za-z0-9_-]{32}", b.get("url", ""))
          and "http" not in c["params"]["text"], "/kirish (CEO) -> bir martalik URL tugma (matnda havola yo'q)", c and c["params"])
    if b and b.get("url"):
        class _NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        op = urllib.request.build_opener(_NoRedir)
        try:
            op.open(b["url"], timeout=15)
            st1, hd1 = 200, {}
        except urllib.error.HTTPError as e:
            st1, hd1 = e.code, e.headers
        check(st1 == 302 and hd1.get("Location") == "/admin/" and "noon_admin=" in (hd1.get("Set-Cookie") or ""),
              "/kirish havolasi -> 302 /admin/ + noon_admin cookie", (st1, dict(hd1 or {})))
        try:
            op.open(b["url"], timeout=15)
            st2 = 200
        except urllib.error.HTTPError as e:
            st2 = e.code
        check(st2 == 403, "/kirish havolasi ikkinchi marta -> 403", st2)
    c = _say(fake, "xodim", USTOZ, "/kirish")
    check(c and _button(c) and "/admin/kirish?k=" in _button(c).get("url", ""), "/kirish (ustoz) -> havola")
    c = _say(fake, "xodim", CEO, "/statistika")
    check(c and c["params"]["text"].startswith("Statistika (") and "O'quvchilar: 3" in c["params"]["text"]
          and "Ochiq darslar: 12 / 36" in c["params"]["text"], "/statistika", c and c["params"]["text"])
    c = _say(fake, "xodim", CEO, "/xodimlar")
    check(c and c["params"]["text"].startswith("Xodimlar (2):") and "Ustoz" in c["params"]["text"], "/xodimlar", c and c["params"]["text"])
    c = _say(fake, "xodim", USTOZ, "/xodimlar")
    check(c and c["params"]["text"] == "Bu buyruq faqat CEO uchun.", "ustoz /xodimlar -> rad")
    c = _say(fake, "xodim", USTOZ, "/yordam")
    check(c and "/ochiq" in c["params"]["text"] and "/taklif" not in c["params"]["text"], "ustoz /yordam: rolga mos")

    log("-- PDF (birinchi yuklash, keyin file_id keshi)")
    mk = fake.mark()
    s, b = api("POST", "/api/s/pdf", {"dars": 8}, make(SINOV_TALABA_TOKEN, ALI))
    check(s == 403 and b == {"xato": "Avval 7-darsni tugating"}, "pdf: 8-dars (ketma-ketlik bo'yicha yopiq) -> 403", (s, b))
    s, b = api("POST", "/api/s/pdf", {"dars": 1}, make(SINOV_TALABA_TOKEN, ALI))
    check(s == 200 and b == {"ok": True}, "pdf: Ali ga yuborildi", (s, b))
    d = fake.wait_for(lambda x: x["method"] == "sendDocument" and x.get("chat_id") == ALI["id"], start=mk)
    check(d and d["files"].get("document", {}).get("filename") == "01-dars (Arab tiliga kirish).pdf"
          and d["files"]["document"]["size"] > 100000 and d["params"].get("caption") == "1-dars. Arab tiliga kirish",
          "pdf: fayl yuklandi (nomi, hajmi, izoh)", d and (d["files"], d["params"].get("caption")))
    s, b = api("POST", "/api/s/pdf", {"dars": 1}, make(SINOV_TALABA_TOKEN, BOTIR))
    d2 = fake.wait_for(lambda x: x["method"] == "sendDocument" and x.get("chat_id") == BOTIR["id"], start=mk)
    check(s == 200 and d2 and not d2["files"] and d2["params"].get("document") == "FAKEFILE0001", "pdf: ikkinchi marta file_id keshidan",
          d2 and (d2["files"], d2["params"].get("document")))
    s, b = api("POST", "/api/s/pdf", {"dars": 1}, make(SINOV_TALABA_TOKEN, ALI))
    check(s == 429, "pdf: 20 s ichida -> 429", s)
    fake.block(BLOK["id"])
    s, b = api("POST", "/api/s/pdf", {"dars": 1}, make(SINOV_TALABA_TOKEN, BLOK))
    check(s == 409 and b and "/start" in b.get("xato", ""), "pdf: bot bloklangan -> 409 + tushunarli xato", (s, b))

    log(f"-- kunlik vazifalar (--jobs-now {JOBS_AFTER} s)")
    left = JOBS_AFTER - (time.time() - t_start)
    check(left > 3, "kunlik vazifalardan oldin hamma qadamlar tugadi", f"{left:.1f} s qoldi")
    e1 = fake.wait_for(lambda x: x["bot"] == "talaba" and x["method"] == "sendMessage" and x.get("chat_id") == ALI["id"]
                       and x["params"]["text"].startswith("Bugungi darsni davom ettiramizmi?"), timeout=JOBS_AFTER + 30)
    check(e1 and _button(e1) == {"text": "Darsni davom ettirish", "web_app": {"url": BASE + "/app/"}}, "19:00 eslatma: Ali ga, tugma bilan",
          e1 and e1["params"])
    e3 = fake.wait_for(lambda x: x["method"] == "sendMessage" and x.get("chat_id") == BOTIR["id"]
                       and x["params"]["text"].startswith("Bugungi darsni"), timeout=10)
    check(e3 is not None, "19:00 eslatma: Botir ga")
    time.sleep(1.0)
    con = sqlite3.connect(DB, timeout=20)
    try:
        bl = con.execute("SELECT blocked FROM users WHERE id=?", (BLOK["id"],)).fetchone()
    finally:
        con.close()
    check(bl == (1,), "eslatma: bloklagan foydalanuvchi belgilandi (Forbidden e'tiborsiz)", bl)
    hs = fake.wait_for(lambda x: x["bot"] == "xodim" and x["method"] == "sendMessage" and x.get("chat_id") == CEO["id"]
                       and x["params"]["text"].startswith("Kunlik hisobot ("), timeout=15)
    check(hs and "Yangi o'quvchilar: 3" in hs["params"]["text"], "21:00 hisobot: CEO ga", hs and hs["params"]["text"])
    check(not fake.get_calls(None, "sendMessage") or all(x.get("chat_id") != USTOZ["id"] or "Kunlik hisobot" not in x["params"]["text"]
                                                         for x in fake.get_calls(None, "sendMessage")), "hisobot faqat CEO ga")

    log("-- menyu tugmasi: birinchi urinish xato bo'lsa, server qayta o'rnatadi")
    for bot in ("talaba", "xodim"):
        mbs = fake.wait_for(lambda x, b=bot: x["bot"] == b and x["method"] == "setChatMenuButton" and not x.get("failed"), timeout=40)
        nfail = len([x for x in fake.get_calls(bot, "setChatMenuButton") if x.get("failed")])
        check(mbs is not None and nfail == 1, f"{bot}: menyu tugmasi xatodan keyin qayta o'rnatildi", (nfail, mbs and mbs["params"]))

    log("-- matnlar: emoji va diniy so'zlar yo'q, web_app manzillari to'g'ri")
    texts = _texts(fake)
    bad = [t for _, t in texts if EMOJI_RE.search(t)]
    check(texts and not bad, f"emoji yo'q ({len(texts)} ta matn)", bad[:3])
    bad = [t for _, t in texts if any(w in t.lower() for w in DINIY)]
    check(not bad, "diniy so'z/salomlashish yo'q", bad[:3])
    urls = _web_app_urls(fake)
    check(urls and all(u == BASE + "/app/" or u == BASE + "/admin/" or u.startswith(BASE + "/app/?") for u in urls),
          f"web_app manzillari ({len(urls)} ta) to'g'ri", sorted(set(urls)))
    (OUT / "tg_xabarlar.json").write_text(json.dumps([{"bot": c["bot"], "method": c["method"], "chat_id": c.get("chat_id"),
                                                       "params": c["params"], "files": c["files"]} for c in fake.get_calls()],
                                                     ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    ok = [0]
    fails = []

    def _check(cond, name, detail=""):
        if cond:
            ok[0] += 1
            print("  OK  ", name, flush=True)
        else:
            fails.append(name)
            print("  XATO", name, "::", detail, flush=True)
        return bool(cond)
    run(_check, print)
    print(f"\nNATIJA: {ok[0]} ta OK, {len(fails)} ta XATO")
    sys.exit(1 if fails else 0)

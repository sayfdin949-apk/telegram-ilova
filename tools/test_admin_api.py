"""SPEC 10 (1-bosqich) server sinovlari: /api/s/track, funksiyalar, admin panel API (rollar), /kirish cookie,
amallar jurnali, savollar bo'yicha test javoblari, seed, yorliqlar.

    python tools/test_admin_api.py                 # o'z sinov serverini ishga tushiradi (8801, data/sinov_srv10.db, --seed)
    python tools/test_admin_api.py --perf          # + 10k o'quvchi / 1M ui_events bilan tezlik sinovi (vaqtinchalik baza)
    python tools/test_admin_api.py --port 8802 --db data/sinov_x.db
    python tools/test_admin_api.py --kirish ceo --port 8802 --db data/sinov_x.db
                                                   # ishlab turgan SINOV serveri uchun: bir martalik /admin/kirish havolasi
                                                   # va tayyor cookie (noon_admin) qiymati (Playwright: ctx.add_cookies)

Natija: _sinov/server10/natija.txt. Faqat o'zi ishga tushirgan serverni to'xtatadi.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
import types
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import auth  # noqa: E402
import config  # noqa: E402
import db as dbm  # noqa: E402
import yorliqlar  # noqa: E402
from sinov_initdata import SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN, TALABA, XODIM, make  # noqa: E402

PORT = 8801
DB = ROOT / "data" / "sinov_srv10.db"
OUT = ROOT / "_sinov" / "server10"
BASE = f"http://127.0.0.1:{PORT}"
TZ = config.TZ
ROLES = ("ceo", "admin", "ustoz", "assistent")
XATO_BOLIM = {"xato": "Bu bo'lim sizga ochiq emas"}
XATO_FUNKSIYA = {"xato": "Bu funksiya hozircha o'chirilgan"}
SECTIONS = {  # 04.10 (SPEC 11.5): + duellar, takliflar (ceo, admin - faqat ko'rish)
    "ceo": ["bosh", "oquvchilar", "voronka", "tugmalar", "qurilmalar", "kurs", "testlar", "duellar", "takliflar", "xodimlar",
            "funksiyalar", "jurnal"],
    "admin": ["bosh", "oquvchilar", "voronka", "tugmalar", "qurilmalar", "kurs", "testlar", "duellar", "takliflar", "jurnal"],
    "ustoz": ["oquvchilar", "kurs", "testlar"],
}
UA = {
    "android": "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36",
    "iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "ipad": "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "win": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)",
    "linux": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
}
# (platform, w, h, ua) -> (os, device, device_label)
DEVICE_TABLE = [
    (("android", 412, 915, UA["android"]), ("Android", "telefon", "Android telefon")),
    (("android", 800, 1280, UA["android"]), ("Android", "planshet", "Android planshet")),
    (("android", 1280, 600, UA["android"]), ("Android", "planshet", "Android planshet")),
    (("android", 599, 960, UA["android"]), ("Android", "telefon", "Android telefon")),
    (("ANDROID", 360, 780, ""), ("Android", "telefon", "Android telefon")),
    (("ios", 390, 844, UA["iphone"]), ("iOS", "telefon", "iPhone")),
    (("ios", 430, 932, UA["ipad"]), ("iOS", "planshet", "iPad")),
    (("ios", 744, 1133, UA["iphone"]), ("iOS", "planshet", "iPad")),
    (("ios", 699, 1000, UA["iphone"]), ("iOS", "telefon", "iPhone")),
    (("tdesktop", 384, 694, UA["win"]), ("Windows", "kompyuter", "Windows kompyuter")),
    (("tdesktop", 384, 694, UA["mac"]), ("macOS", "kompyuter", "Mac")),
    (("tdesktop", 384, 694, UA["linux"]), ("Linux", "kompyuter", "Linux kompyuter")),
    (("tdesktop", 384, 694, ""), ("Kompyuter", "kompyuter", "Kompyuter")),
    (("macos", 384, 694, UA["mac"]), ("macOS", "kompyuter", "Mac")),
    (("weba", 1280, 720, UA["win"]), ("Windows", "brauzer", "Telegram Web (brauzer)")),
    (("webk", 1440, 900, UA["mac"]), ("macOS", "brauzer", "Telegram Web (brauzer)")),
    (("web", 1280, 720, UA["linux"]), ("Linux", "brauzer", "Telegram Web (brauzer)")),
    (("unknown", 1280, 720, UA["win"]), ("Windows", "nomalum", "Noma'lum")),
    ((None, None, None, None), ("Noma'lum", "nomalum", "Noma'lum")),
]


def configure(port: int, db: Path, out: Path) -> None:
    global PORT, DB, OUT, BASE
    PORT, DB, OUT = port, db, out
    BASE = f"http://127.0.0.1:{PORT}"


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
        R.fails.append(f"{name} :: {str(detail)[:400]}")
        log(f"  XATO {name} :: {str(detail)[:400]}")
    return bool(cond)


# ---------------------------------------------------------------- HTTP
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def http(method: str, path: str, body=None, headers: dict | None = None, raw_body: bytes | None = None):
    data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with _OPENER.open(req, timeout=30) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def jh(method, path, body=None, headers=None):
    s, h, b = http(method, path, body, headers)
    try:
        return s, h, json.loads(b) if b else None
    except ValueError:
        return s, h, None


def S(who="aziza", **kw):
    u = TALABA[who] if isinstance(who, str) else who
    return {"X-Init-Data": make(SINOV_TALABA_TOKEN, u, **kw)}


def X(who="ceo", **kw):
    u = XODIM[who] if isinstance(who, str) else who
    return {"X-Init-Data": make(SINOV_XODIM_TOKEN, u, **kw)}


def COOKIE(token: str, csrf: bool = False) -> dict:
    h = {"Cookie": f"{config.COOKIE_NOMI}={token}"}
    if csrf:
        h["X-Requested-With"] = "noon"
    return h


@contextmanager
def con():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


def new_sid() -> str:
    return str(uuid.uuid4())


DEV ={"platform": "android", "version": "8.0", "w": 412, "h": 915, "dpr": 2.6, "scheme": "light", "ua": UA["android"]}


def ev(k, n, r=None, s=None, d=None, t=None):
    e = {"k": k, "n": n}
    if r is not None:
        e["r"] = r
    if s is not None:
        e["s"] = s
    if d is not None:
        e["d"] = d
    if t is not None:
        e["t"] = t
    return e


# ---------------------------------------------------------------- server jarayoni
def start_server() -> subprocess.Popen:
    OUT.mkdir(parents=True, exist_ok=True)
    for suf in ("", "-wal", "-shm"):
        try:
            Path(str(DB) + suf).unlink()
        except OSError:
            pass
    out = open(OUT / "server_stdout.txt", "w", encoding="utf-8")
    p = subprocess.Popen([sys.executable, str(ROOT / "server" / "main.py"), "--sinov", "--port", str(PORT),
                          "--db", str(DB.relative_to(ROOT)), "--seed"], cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT,
                         creationflags=config.CREATE_NO_WINDOW)
    t0 = time.time()
    while time.time() - t0 < 40:
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
    raise RuntimeError("server 40 s da javob bermadi")


def stop_server(p: subprocess.Popen) -> bool:
    stop_file = config.DATA_DIR / f"sinov_{PORT}.stop"
    stop_file.write_text("stop", encoding="ascii")
    try:
        p.wait(15)
        return True
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(5)
        return False
    finally:
        try:
            stop_file.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- UNIT
def unit_tests() -> None:
    log("\n== UNIT: qurilma tasnifi, yorliqlar, funksiyalar ==")
    for (platform, w, h, ua), (os_, device, label) in DEVICE_TABLE:
        got = dbm.classify_device(platform, w, h, ua)
        check(got == (os_, device) and dbm.device_label(*reversed(got)) == label,
              f"classify_device({platform}, {w}x{h}) -> {os_}/{device} '{label}'", (got, dbm.device_label(got[1], got[0])))
    labels = {dbm.device_label(d, o) for d, o in (("telefon", "Android"), ("planshet", "Android"), ("telefon", "iOS"),
                                                   ("planshet", "iOS"), ("kompyuter", "Windows"), ("kompyuter", "macOS"),
                                                   ("kompyuter", "Linux"), ("brauzer", "Windows"), ("nomalum", None))}
    check(labels == {"Android telefon", "Android planshet", "iPhone", "iPad", "Windows kompyuter", "Mac", "Linux kompyuter",
                     "Telegram Web (brauzer)", "Noma'lum"}, "device_label: SPEC dagi 9 ta yorliq", labels)

    # yorliqlar: app.js dagi har data-act va ekran kaliti uchun o'zbekcha yorliq
    js = (ROOT / "web" / "app" / "app.js").read_text(encoding="utf-8")
    acts = set(re.findall(r'data-act="([a-z0-9][a-z0-9_-]*)"', js))
    acts |= set(re.findall(r"\bitem\(\s*'([a-z0-9][a-z0-9_-]*)'", js))
    acts |= set(re.findall(r"\bpvCard\([^)]*?,\s*'([a-z0-9][a-z0-9_-]*)'\s*\)", js))
    acts |= set(re.findall(r"\berrBlock\([^)]*?,\s*'([a-z0-9][a-z0-9_-]*)'\s*\)", js))
    m = re.search(r"const ACT = \{(.*?)\n  \};", js, re.S)
    act_keys = set(re.findall(r"^\s{4}'?([a-z][a-z0-9-]*)'?\s*\(", m.group(1), re.M)) if m else set()
    acts |= act_keys
    m2 = re.search(r"const SCR = \{(.*?)\n  \};", js, re.S)
    scr = set(re.findall(r"^\s{4}([a-z][a-z0-9_-]*):", m2.group(1), re.M)) if m2 else set()
    missing = sorted(a for a in acts if a not in yorliqlar.TUGMA_NOMI)
    check(len(acts) >= 30 and len(act_keys) >= 30, f"app.js: data-act qiymatlari topildi ({len(acts)} ta, ACT: {len(act_keys)})",
          sorted(acts))
    check(not missing, "yorliqlar.TUGMA_NOMI: app.js dagi barcha data-act lar", missing)
    miss_s = sorted(s for s in scr | {"bosh", "darslar", "video", "reyting", "profil", "dars", "kitob", "player", "mashq", "natija"}
                    if s not in yorliqlar.EKRAN_NOMI)
    check(len(scr) >= 10 and not miss_s, f"yorliqlar.EKRAN_NOMI: barcha ekran kalitlari ({len(scr)} ta SCR)", miss_s)
    # talaba ilovasi agenti bilan kelishilgan nomlar (03.10): ilova aynan shularni yuboradi
    c_scr = ["bosh", "darslar", "video", "reyting", "profil", "dars", "kitob", "player", "mashq", "natija", "sheet-tugadi",
             "sheet-videolar", "sheet-zoom", "ob-salom", "ob-uslub", "ob-rejim"]
    c_clk = ["tab", "back", "lesson", "video", "vids", "sheet-close", "sheet-bg", "quiz", "pick", "qz-check", "qz-next",
             "qz-restart", "qz-retry", "test-retry", "vw-prev", "vw-next", "vw-go", "vw-finish", "vw-zoom", "zm-s", "zm-close",
             "hint-ok", "dk-prev", "dk-next", "dk-finish", "dk-fs", "dk-reload", "kitob", "davr", "rating-retry", "set-uslub",
             "set-rejim", "set-arab", "set-esl", "ob-style", "ob-mode", "ob-next", "ob-done", "tg-back"]
    miss_c = [k for k in c_scr if k not in yorliqlar.EKRAN_NOMI] + [k for k in c_clk if k not in yorliqlar.TUGMA_NOMI]
    check(not miss_c, f"yorliqlar: kelishilgan {len(c_scr)} ekran + {len(c_clk)} tugma nomi (tg-back ham)", miss_c)
    check(yorliqlar.voqea_nomi("end", "dars") and yorliqlar.voqea_nomi("resume", "dars") != "resume", "yorliqlar: end/resume")
    bad = [k for k, v in {**yorliqlar.TUGMA_NOMI, **yorliqlar.EKRAN_NOMI}.items() if not v or v == k]
    check(not bad, "yorliqlar: bo'sh yoki kalitning o'zi bo'lgan yorliq yo'q", bad)
    check(yorliqlar.tugma_nomi("lesson") == "Darsni ochish" and yorliqlar.tugma_nomi("quiz") == "Mashqni boshlash"
          and yorliqlar.tugma_nomi("pick") == "Javob tanlash" and yorliqlar.tugma_nomi("qz-check") == "Javobni tekshirish"
          and yorliqlar.tugma_nomi("dk-next") == "Keyingi slayd" and yorliqlar.tugma_nomi("tab") == "Bo'lim almashtirish"
          and yorliqlar.tugma_nomi("set-rejim") == "Rejimni o'zgartirish", "yorliqlar: SPEC dagi namunalar")
    check(yorliqlar.tugma_nomi("tab", "darslar") == "Bo'lim almashtirish: Darslar"
          and yorliqlar.tugma_nomi("set-rejim", "dark") == "Rejimni o'zgartirish: Tungi"
          and yorliqlar.tugma_nomi("lesson", "8") == "Darsni ochish: 8-dars", "yorliqlar: ref qo'shiladi (tab -> bo'lim nomi)")
    check(yorliqlar.tugma_nomi("yangi-tugma") == "yangi-tugma" and yorliqlar.ekran_nomi("nimadir") == "nimadir"
          and yorliqlar.ekran_nomi("sheet-yangi").startswith("Oyna") and yorliqlar.ekran_nomi("ob-9").startswith("Tanishuv"),
          "yorliqlar: noma'lum kalit -> o'zi (sheet-/ob- prefikslari tushunarli)")
    check(yorliqlar.ekran_nomi("ob-korinish") == "Tanishuv: manzara tanlash"
          and yorliqlar.tugma_nomi("set-manzara", "voha") == "Manzarani tanlash: Voha", "yorliqlar: 05.10 manzara nomlari (egasi)")
    check(yorliqlar.qiymat_nomi("tab", "darslar") == "Darslar" and yorliqlar.qiymat_nomi("set-manzara", "shom") == "Shom"
          and yorliqlar.qiymat_nomi("lesson", "8") == "8-dars" and yorliqlar.qiymat_nomi("pick", "2") is None
          and yorliqlar.qiymat_nomi("tab", None) is None and yorliqlar.qiymat_nomi(None, "x") is None, "yorliqlar.qiymat_nomi (ref -> nom)")
    every = " ".join(list(yorliqlar.TUGMA_NOMI.values()) + list(yorliqlar.EKRAN_NOMI.values()))
    check(all(ord(ch) < 0x2190 for ch in every), "yorliqlar: emoji/maxsus belgilar yo'q")
    # funksiyalar
    check([k for k, _, _, _ in config.FUNKSIYALAR] == ["reyting", "video", "test", "ball", "uslub", "eslatma", "hisobot", "duel",
                                                       "taklif", "qollanma"], "config.FUNKSIYALAR: SPEC 10.3 tartibi")
    usl = next(x for x in config.FUNKSIYALAR if x[0] == "uslub")
    check(usl[1] == "Manzara tanlash" and "manzara" in usl[2].lower(), "config.FUNKSIYALAR: uslub -> 'Manzara tanlash' (egasi, 05.10)", usl[:2])
    st = dbm.Store(Path(tempfile.mkdtemp()) / "f.db")
    check(st.features() == {k: True for k in config.FUNKSIYA_KALITLARI}, "funksiyalar: standart - hammasi yoqilgan")
    f, ch = st.set_feature("video", False)
    check(f["video"] is False and ch and st.feature_on("video") is False and st.feature_on("reyting"), "funksiya o'chirildi")
    check(st.set_feature("video", False)[1] is False, "funksiya: o'zgarmasa changed=False")
    st.set_setting("features", "{buzuq")
    check(st.features()["video"] is True, "funksiyalar: buzuq JSON -> standart")
    check(config.OCHISH_ROLLARI == ("ceo", "admin"), "OCHISH_ROLLARI = (ceo, admin)")
    unit_funnel_tanishuv()


def unit_funnel_tanishuv() -> None:
    """05.10 (egasi): voronka 2-qadami "Tanishuvni tugatdi" = ob-done / ob-skip tugmasi (istalgan vaqt) YOKI users.uslub (eski)."""
    path = Path(tempfile.mkdtemp()) / "v.db"
    st = dbm.Store(path)
    now = dbm.now_tz()
    new, old = dbm.iso(now - timedelta(days=1)), dbm.iso(now - timedelta(days=60))
    users = [(1, "game", new), (2, None, new), (3, None, new), (4, None, new), (5, None, new), (6, None, new), (7, None, old),
             (8, None, new)]
    ev_ = [(2, "click", "ob-done"), (3, "click", "ob-skip"), (4, "click", "ob-next"), (5, "screen", "ob-done"), (7, "click", "ob-done"),
           (8, "click", "ob-done"), (8, "click", "ob-done"), (1, "click", "tab")]
    with sqlite3.connect(path) as c:
        c.executemany("INSERT INTO users(id, first_name, joined_at, last_seen, uslub, rejim) VALUES (?,?,?,?,?,?)",
                      [(u, f"U{u}", j, j, us, "auto") for u, us, j in users])
        c.executemany("INSERT INTO ui_events(session_id, user_id, at, kind, name) VALUES (?,?,?,?,?)",
                      [(f"s{u}", u, dbm.iso_ms(now - timedelta(hours=i + 1)), k, n) for i, (u, k, n) in enumerate(ev_)])
        plan = " | ".join(r[3] for r in c.execute(
            "EXPLAIN QUERY PLAN SELECT e.user_id FROM ui_events e INDEXED BY ui_events_kind WHERE e.kind='click' AND e.name IN ('ob-done','ob-skip')"))
    f = st.funnel(now, 30)
    stp = {x["key"]: x for x in f["steps"]}
    check(f["joined"] == 7 and stp["tanishuv"]["users"] == 4 and stp["tanishuv"]["nomi"] == "Tanishuvni tugatdi" and "uslub" not in stp,
          "voronka: tanishuv = uslub (1) + ob-done (2, 8 - bir marta) + ob-skip (3); ob-next / 'ob-done' ekrani / davrdan oldingi yo'q",
          (f["joined"], stp.get("tanishuv")))
    check([x["key"] for x in f["steps"]][:3] == ["kirdi", "tanishuv", "d1_boshladi"], "voronka: tartib kirdi -> tanishuv -> d1_boshladi",
          [x["key"] for x in f["steps"]])
    check("ui_events_kind" in plan, "voronka: tanishuv so'rovi ui_events_kind indeksidan foydalanadi", plan)
    st.close()


# ---------------------------------------------------------------- API
def api_tests() -> None:
    log("\n== API (sinov server, port %d, %s) ==" % (PORT, DB.name))
    p = start_server()
    try:
        _api_body()
    except Exception:
        check(False, "API sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        check(stop_server(p), "server stop fayli bilan yumshoq to'xtadi")
    logtxt = (config.LOG_DIR / f"sinov_{PORT}.log").read_text(encoding="utf-8", errors="ignore")
    check(SINOV_TALABA_TOKEN not in logtxt and SINOV_XODIM_TOKEN not in logtxt and not config.TOKEN_ANY_RE.search(logtxt),
          "sinov logida token yo'q")


def _api_body() -> None:
    from kurs import Kurs
    kurs_m = Kurs()
    secret = auth.load_secret()
    kurs = json.loads((config.CONTENT_DIR / "kurs.json").read_text(encoding="utf-8"))
    lessons = {x["n"]: x for x in kurs["darslar"]}
    test8 = json.loads((config.CONTENT_DIR / "test" / "08.json").read_text(encoding="utf-8"))
    now = datetime.now(TZ)
    today = now.date()

    # ---- avval vaqtga bog'liq tekshiruvlar (jonli seanslar server ishga tushgandan keyin ~3 daqiqa "hozir faol")
    log("-- overview (seed: jonli seanslar)")
    s, h, ov = jh("GET", "/api/x/overview", None, X("ceo"))
    base_keys = {"students", "active_today", "active_7d", "new_7d", "lessons_done", "videos_done", "tests_done", "avg_xp",
                 "styles", "modes", "daily", "recent"}
    check(s == 200 and base_keys <= set(ov) and {"active_now", "sessions_today", "avg_session_min", "devices", "live"} <= set(ov),
          "overview: /stats maydonlari + yangi maydonlar", ov and sorted(ov))
    check(h.get("Cache-Control") == "no-store", "API: Cache-Control no-store")
    check(ov["active_now"] >= 2 and 2 <= len(ov["live"]) <= 10, "overview: hozir faol >= 2 (seed jonli seanslari)",
          (ov.get("active_now"), len(ov.get("live", []))))
    lv = ov["live"][0] if ov["live"] else {}
    check({"name", "screen_label", "device_label", "since"} <= set(lv) and lv["screen_label"] and lv["device_label"],
          "overview.live: name, screen_label, device_label, since", lv)
    with con() as c:
        n_today = c.execute("SELECT COUNT(*) FROM sessions WHERE started_at >= ?", (dbm.iso(dbm.day_start(today)),)).fetchone()[0]
    check(ov["sessions_today"] == n_today and ov["avg_session_min"] > 0, "overview: sessions_today bazaga mos, avg_session_min > 0",
          (ov["sessions_today"], n_today, ov["avg_session_min"]))
    check(0 < len(ov["devices"]) <= 5 and all(set(d) == {"label", "users"} for d in ov["devices"])
          and [d["users"] for d in ov["devices"]] == sorted([d["users"] for d in ov["devices"]], reverse=True),
          "overview.devices: top 5, kamayish tartibida", ov["devices"])
    check(len(ov["daily"]) == 14 and ov["daily"][-1]["day"] == today.isoformat(), "overview: daily 14 kun (standart)")
    # 05.10 (admin NUQTA): o'tgan hafta, duellar holati, So'nggi faollikda duellar
    with con() as c:
        a7 = (today - timedelta(days=13)).isoformat(), (today - timedelta(days=7)).isoformat()
        o_act = c.execute("SELECT COUNT(DISTINCT user_id) FROM days WHERE day >= ? AND day <= ?", a7).fetchone()[0]
        o_new = c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ? AND joined_at < ?",
                          (dbm.iso(dbm.day_start(today - timedelta(days=13))), dbm.iso(dbm.day_start(today - timedelta(days=6))))).fetchone()[0]
        n_dd = c.execute("SELECT COUNT(*) FROM events WHERE kind='duel_done'").fetchone()[0]
    check(ov.get("oldingi") == {"active_7d": o_act, "new_7d": o_new}, "overview.oldingi: o'tgan hafta (8-14 kun oldin) bazaga mos",
          (ov.get("oldingi"), o_act, o_new))
    s2, _, dx = jh("GET", "/api/x/duels?days=14", None, X("ceo"))
    dd = ov.get("duels") or {}
    check(set(dd) == {"days", "total", "decided", "draws", "active", "expired"} and dd["days"] == 14 and dd["total"] == dx["total"]
          and dd["decided"] == dx["finished"] - dx["draws"] and dd["draws"] == dx["draws"] and dd["active"] == dx["active"]
          and dd["expired"] == dx["expired"] and dd["decided"] + dd["draws"] + dd["active"] + dd["expired"] == dd["total"] and dd["total"] > 0,
          "overview.duels: holatlar /api/x/duels bilan bir xil", (dd, {k: dx.get(k) for k in ("total", "finished", "draws", "active", "expired")}))
    rec = ov["recent"]
    check(len(rec) <= 20 and [x["at"] for x in rec] == sorted([x["at"] for x in rec], reverse=True)
          and {x["kind"] for x in rec} <= {"lesson_done", "test_done", "video_done", "duel_done"}, "overview.recent: <= 20, yangisi birinchi, 4 xil", rec[:2])
    rd = jh("GET", "/api/x/overview?days=90", None, X("ceo"))[2]
    s3, _, st0 = jh("GET", "/api/x/stats", None, X("ceo"))
    check(n_dd > 0 and all(x["kind"] != "duel_done" for x in st0["recent"]), "stats: eski /api/x/stats o'zgarmagan (duelsiz)", n_dd)
    # 06.10 (egasi, "1 ha"): /api/x/stats ham korinish qaytaradi (xodimlar sahifasi - 4 rol); eski maydonlar aynan saqlangan
    check(s3 == 200 and set(st0) == base_keys | {"korinish"}, "stats: aynan eski maydonlar + korinish", sorted(st0))
    check(st0["korinish"] == ov["korinish"] and st0["korinish"]["days"] == 14, "stats.korinish (14 kun) = overview.korinish", st0.get("korinish"))
    for role in ROLES:
        s4, _, st4 = jh("GET", "/api/x/stats?days=7", None, X(role))
        k7 = dbm.Store(DB).korinish_report(dbm.now_tz(), 7)
        check(s4 == 200 and st4["korinish"] == k7 and len(st4["daily"]) == 7, f"stats?days=7 ({role}): korinish va daily davrga mos",
              (s4, st4.get("korinish")))
    for bad in ("0", "91", "abc"):
        check(jh("GET", "/api/x/stats?days=" + bad, None, X("ustoz"))[0] == 400, f"stats?days={bad} -> 400")
    with con() as c:
        last_dd = c.execute("SELECT at FROM events WHERE kind='duel_done' ORDER BY at DESC, id DESC LIMIT 1").fetchone()[0]
    in_top = sum(1 for x in st0["recent"] if x["at"] > last_dd) < 20
    check((not in_top) or any(x["kind"] == "duel_done" for x in rd["recent"]), "overview.recent: oxirgi duel ham ko'rinadi (20 talik ichida bo'lsa)", last_dd)
    dr = [x for x in rd["recent"] if x["kind"] == "duel_done"] + dbm.Store(DB).recent_duels(5)
    check(len(dr) >= 5, "recent_duels: seed duellari bor", len(dr))
    check(all(x["result"] in ("yutdi", "yutqazdi", "durrang") and x["ref"].endswith(" bilan") and re.fullmatch(r"\d+:\d+", x.get("natija", "")) and x["duel_id"]
              for x in dr), "overview.recent: duel - raqib ('X bilan'), natija, hisob", dr[:2])
    s, _, ov7 = jh("GET", "/api/x/overview?days=7", None, X("admin"))
    check(s == 200 and len(ov7["daily"]) == 7, "overview?days=7 -> 7 kun", s)
    for bad in ("0", "91", "abc", "-1"):
        check(jh("GET", f"/api/x/overview?days={bad}", None, X("ceo"))[0] == 400, f"overview?days={bad} -> 400")

    # ---- seed realizmi
    log("-- seed: seanslar, harakatlar, test javoblari")
    with con() as c:
        per = {r[0]: r[1] for r in c.execute("SELECT user_id, COUNT(*) FROM sessions GROUP BY user_id")}
        studs = [r[0] for r in c.execute("SELECT id FROM users WHERE id BETWEEN 800001 AND 800015")]
        labels = {dbm.device_label(r[0], r[1]) for r in c.execute("SELECT DISTINCT device, os FROM sessions")}
        bad_cnt = c.execute("""SELECT COUNT(*) FROM sessions s WHERE s.screens != (SELECT COUNT(*) FROM ui_events e
                                 WHERE e.session_id=s.id AND e.kind='screen')
                               OR s.clicks != (SELECT COUNT(*) FROM ui_events e WHERE e.session_id=s.id AND e.kind='click')""").fetchone()[0]
        rng = c.execute("SELECT MIN(started_at), MAX(last_at) FROM sessions").fetchone()
        names = c.execute("SELECT kind, name, COUNT(*) FROM ui_events GROUP BY kind, name").fetchall()
        bad_order = c.execute("SELECT COUNT(*) FROM sessions WHERE last_at < started_at OR (ended_at IS NOT NULL AND ended_at < started_at)").fetchone()[0]
        ta = c.execute("SELECT COUNT(*) FROM test_answers").fetchone()[0]
        tr = c.execute("""SELECT COUNT(*) FROM tests t WHERE t.tries > 0 AND t.last != (SELECT COUNT(*) FROM test_answers a
                            WHERE a.user_id=t.user_id AND a.dars=t.dars AND a.try_no=t.tries AND a.ok=1)""").fetchone()[0]
        exp_ta = c.execute("SELECT SUM(tries * total) FROM tests").fetchone()[0]
        ob = c.execute("SELECT COUNT(DISTINCT user_id) FROM ui_events WHERE name LIKE 'ob-%'").fetchone()[0]
        jt = {r[0]: r[1] for r in c.execute("SELECT id, joined_at FROM users")}
        early = c.execute("SELECT user_id, MIN(started_at) FROM sessions GROUP BY user_id").fetchall()
    check(len(studs) == 15 and all(3 <= per.get(u, 0) <= 8 for u in studs), "seed: har o'quvchida 3-8 seans",
          {u: per.get(u) for u in studs})
    check(len(labels) >= 5, f"seed: turli qurilmalar ({len(labels)} xil)", labels)
    check(bad_cnt == 0 and bad_order == 0, "seed: seans hisoblagichlari va vaqtlari ui_events ga mos", (bad_cnt, bad_order))
    check(rng[0] >= dbm.iso(dbm.day_start(today - timedelta(days=14))) and rng[1] <= dbm.iso(datetime.now(TZ)),
          "seed: seanslar oxirgi 14 kun ichida, kelajakda emas", rng)
    check(all(e[1] >= jt[e[0]] for e in early), "seed: seanslar o'quvchi qo'shilgandan keyin")
    unl = [f"{k}:{n}" for k, n, _ in names if (k == "click" and n not in yorliqlar.TUGMA_NOMI)
           or (k == "screen" and n not in yorliqlar.EKRAN_NOMI)]
    check(not unl and len(names) >= 25, f"seed: {len(names)} xil ekran/tugma, hammasining yorlig'i bor", unl)
    check(ob >= 3, "seed: tanishuv (ob-salom / ob-korinish / ob-uslub ...) ekranlari bor", ob)
    # 05.10: NUQTA davrida qo'shilganlar - NUQTA tanishuvi (ob-korinish, ob-done | ob-skip), eskilari - eski (ob-uslub)
    with con() as c:
        obk = {r[0]: r[1] for r in c.execute("""SELECT user_id, group_concat(name) FROM ui_events WHERE kind='click'
                                                AND name IN ('ob-done','ob-skip') GROUP BY user_id""")}
        nq_ob = {r[0] for r in c.execute("SELECT DISTINCT user_id FROM ui_events WHERE kind='screen' AND name='ob-korinish'")}
        old_ob = {r[0] for r in c.execute("SELECT DISTINCT user_id FROM ui_events WHERE kind='screen' AND name='ob-uslub'")}
        no_usl = {r[0] for r in c.execute("SELECT id FROM users WHERE uslub IS NULL AND id BETWEEN 800001 AND 800015")}
        man_ob = {r[0]: r[1] for r in c.execute("SELECT user_id, ref FROM ui_events WHERE kind='click' AND name='set-manzara'"
                                                " AND screen='ob-korinish'")}
    check(len(nq_ob) >= 4 and old_ob and not (nq_ob & old_ob) and set(obk) == nq_ob | old_ob
          and {"ob-done", "ob-skip"} <= set(",".join(obk.values()).split(",")),
          "seed: NUQTA tanishuvi (ob-korinish -> ob-done / ob-skip) va eski tanishuv (ob-uslub)", (obk, nq_ob, old_ob))
    check(bool(no_usl & set(obk)) and bool(no_usl - set(obk)),
          "seed: uslubsiz o'quvchilarning bir qismi tanishuvni tugatgan (tugma), bir qismi yo'q (eski)", (no_usl, set(obk)))
    check(man_ob and all(dbm.SEED_MANZARA.get(u) == v for u, v in man_ob.items()),
          "seed: tanishuvda manzara tanlaganlar - o'z manzarasi (SEED_MANZARA)", man_ob)
    check(ta > 0 and ta == exp_ta and tr == 0, "seed: test_answers har urinish x savol; oxirgi urinish to'g'rilari = tests.last",
          (ta, exp_ta, tr))

    # ---- /api/s/track
    log("-- /api/s/track")
    sid = new_sid()
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "device": DEV, "events": [ev("screen", "bosh")]})
    check(s == 401, "track: initData yo'q -> 401", s)
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "events": [ev("screen", "bosh")]}, S("jahongir"))
    check(s == 400 and "device" in b["xato"], "track: yangi seans, device yo'q -> 400", (s, b))
    t_ms = int(time.time() * 1000)
    evs = [ev("screen", "bosh", t=t_ms - 9000), ev("click", "tab", "darslar", "bosh", t=t_ms - 8000),
           ev("screen", "darslar", d=1200, t=t_ms - 7900), ev("click", "lesson", 8, "darslar", t=t_ms - 6000),
           ev("screen", "dars", "8", d=1900.4, t=t_ms - 5900), ev("click", "dk-next", None, "dars", t=t_ms - 3000)]
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "device": DEV, "events": evs}, S("jahongir"))
    check(s == 200 and b == {"ok": True}, "track: birinchi so'rov (device + 6 voqea) -> ok", (s, b))
    with con() as c:
        row = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        evr = c.execute("SELECT * FROM ui_events WHERE session_id=? ORDER BY id", (sid,)).fetchall()
        u2 = c.execute("SELECT uslub, rejim FROM users WHERE id=800002").fetchone()
    check(row and row["user_id"] == 800002 and row["platform"] == "android" and row["os"] == "Android" and row["device"] == "telefon"
          and row["tg_version"] == "8.0" and row["screen"] == "412x915" and row["scheme"] == "light" and row["ua"] == UA["android"],
          "track: seans qatori (platforma, os, qurilma, ekran o'lchami, sxema, UA)", row and dict(row))
    check(row and (row["uslub"], row["rejim"]) == (u2["uslub"], u2["rejim"]), "track: uslub/rejim foydalanuvchi sozlamasidan")
    check(row and row["screens"] == 3 and row["clicks"] == 3 and row["ended_at"] is None, "track: hisoblagichlar 3 ekran, 3 tugma")
    check([(e["kind"], e["name"], e["ref"], e["screen"], e["dur_ms"]) for e in evr] ==
          [("screen", "bosh", None, None, None), ("click", "tab", "darslar", "bosh", None), ("screen", "darslar", None, "bosh", 1200),
           ("click", "lesson", "8", "darslar", None), ("screen", "dars", "8", "darslar", 1900), ("click", "dk-next", None, "dars", None)],
          "track: voqealar (screen ustuni = tark etilgan ekran, r son -> matn, d butun)", [tuple(e)[3:] for e in evr])
    at0 = datetime.fromisoformat(evr[0]["at"]) if evr else None
    check(at0 and abs(at0.timestamp() * 1000 - (t_ms - 9000)) < 2, "track: mijoz vaqti (t) +-10 daqiqa ichida -> ishlatildi",
          evr and evr[0]["at"])
    check(row and row["started_at"] <= evr[0]["at"][:19] + "+05:00", "track: started_at = birinchi voqea vaqti", row and row["started_at"])
    # davomi: device ixtiyoriy; uzoq vaqt -> server vaqti; end / resume
    far = int((time.time() - 3600) * 1000)
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "events": [ev("screen", "darslar", d=500, t=far), ev("end", "darslar", d=100)]},
                 S("jahongir"))
    with con() as c:
        row = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        last2 = c.execute("SELECT * FROM ui_events WHERE session_id=? ORDER BY id DESC LIMIT 2", (sid,)).fetchall()
    check(s == 200 and row["ended_at"] is not None and row["screens"] == 4, "track: 'end' -> ended_at; device keyingi so'rovda shart emas",
          (s, b, row and row["ended_at"]))
    srv_t = datetime.fromisoformat(last2[1]["at"])
    check(abs(srv_t.timestamp() - time.time()) < 60, "track: t 1 soat farq -> server vaqti olindi", last2[1]["at"])
    check(last2[1]["screen"] == "dars" and last2[0]["kind"] == "end" and last2[0]["screen"] == "darslar",
          "track: 'darslar' voqeasining screen = oldingi 'dars'; end.screen = joriy ekran", [dict(x) for x in last2])
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "events": [{"k": "resume"}]}, S("jahongir"))
    with con() as c:
        row = c.execute("SELECT ended_at, last_at FROM sessions WHERE id=?", (sid,)).fetchone()
        rs = c.execute("SELECT name FROM ui_events WHERE session_id=? ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
    check(s == 200 and row["ended_at"] is None and rs["name"] == "darslar", "track: 'resume' (n siz) -> ended_at tozalandi, n = joriy ekran",
          (s, b, dict(row), rs and rs["name"]))
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "device": dict(DEV, scheme="dark"), "events": []}, S("jahongir"))
    with con() as c:
        sch = c.execute("SELECT scheme FROM sessions WHERE id=?", (sid,)).fetchone()[0]
    check(s == 200 and sch == "dark", "track: bo'sh voqealar + device.scheme yangilanadi", (s, sch))
    # egalik va validatsiya
    s, _, b = jh("POST", "/api/s/track", {"sid": sid, "device": DEV, "events": [ev("screen", "bosh")]}, S("aziza"))
    check(s == 400, "track: boshqa o'quvchining sid -> 400", (s, b))
    bad_sids = ["", "abc", sid.upper(), sid[:-1], sid + "0", "g" * 36, sid.replace("-", "_"), 12345, None]
    for bs in bad_sids:
        s, _, _ = jh("POST", "/api/s/track", {"sid": bs, "device": DEV, "events": []}, S("aziza"))
        check(s == 400, f"track: sid {str(bs)[:12]!r} -> 400", s)
    sid2 = new_sid()
    vuser = {"id": 800404, "first_name": "Validatsiya"}
    # tuzilma noto'g'ri -> butun so'rov 400 (hech narsa yozilmaydi)
    for name, evs_ in (("101 voqea", [ev("click", "dk-next")] * 101), ("voqealar ro'yxat emas", "x")):
        s, _, b = jh("POST", "/api/s/track", {"sid": sid2, "device": DEV, "events": evs_}, S(vuser))
        check(s == 400 and isinstance(b, dict) and "xato" in b, f"track: {name} -> 400", (s, b))
    with con() as c:
        check(c.execute("SELECT COUNT(*) FROM sessions WHERE id=?", (sid2,)).fetchone()[0] == 0, "track: 400 so'rov seans yaratmadi")
    # bitta noto'g'ri voqea -> o'sha voqea o'tkazib yuboriladi, qolganlari yoziladi (ilova 400 da to'plamni tashlaydi)
    cases = [
        ("k noma'lum", [ev("tap", "x")]),
        ("n katta harf", [ev("click", "Tab")]),
        ("n 41 belgi", [ev("click", "a" * 41)]),
        ("n bo'sh", [ev("click", "")]),
        ("n yo'q (click)", [{"k": "click"}]),
        ("n bo'shliq bilan", [ev("click", "dk next")]),
        ("r 41 belgi", [ev("click", "lesson", "x" * 41)]),
        ("s 41 belgi", [ev("click", "lesson", "8", "s" * 41)]),
        ("d manfiy", [ev("screen", "bosh", d=-1)]),
        ("d > 86400000", [ev("screen", "bosh", d=86_400_001)]),
        ("d matn", [ev("screen", "bosh", d="5")]),
        ("t matn", [ev("screen", "bosh", t="kecha")]),
        ("voqea obyekt emas", [1]),
    ]
    for name, evs_ in cases:
        s, _, b = jh("POST", "/api/s/track", {"sid": sid2, "device": DEV, "events": [ev("click", "vw-go", s="dars")] + evs_},
                     S(vuser))
        check(s == 200 and b == {"ok": True, "skipped": 1}, f"track: {name} -> o'tkazib yuborildi (200, skipped 1)", (s, b))
    with con() as c:
        rows = c.execute("SELECT kind, name FROM ui_events WHERE session_id=?", (sid2,)).fetchall()
    check(len(rows) == len(cases) and all(tuple(r) == ("click", "vw-go") for r in rows),
          "track: faqat to'g'ri voqealar yozildi (device har so'rovda kelsa ham rad etilmaydi)", [tuple(r) for r in rows][:5])
    s, _, b = jh("POST", "/api/s/track", {"sid": sid2, "device": DEV, "events": [ev("click", "dk-next", s="dars")] * 100}, S(vuser))
    with con() as c:
        n100 = c.execute("SELECT clicks FROM sessions WHERE id=?", (sid2,)).fetchone()
    check(s == 200 and b == {"ok": True} and n100 and n100[0] == 100 + len(cases), "track: 100 voqea -> 200", (s, b, n100 and n100[0]))
    check(jh("POST", "/api/s/track", {"sid": sid2, "device": "x", "events": []}, S(vuser))[0] == 400, "track: device obyekt emas -> 400")
    big = json.dumps({"sid": sid2, "events": [], "pad": "x" * 70000}).encode()
    check(http("POST", "/api/s/track", raw_body=big, headers=S(vuser))[0] == 413, "track: 64 KB dan katta -> 413")
    # qurilma tasnifi API orqali
    for (platform, w, h, ua), (os_, device, label) in DEVICE_TABLE:
        sd = new_sid()
        dv = {"platform": platform, "version": "8.0", "w": w, "h": h, "ua": ua}
        s, _, b = jh("POST", "/api/s/track", {"sid": sd, "device": dv, "events": [ev("screen", "bosh")]}, S({"id": 800401, "first_name": "Qurilma"}))
        with con() as c:
            r = c.execute("SELECT os, device FROM sessions WHERE id=?", (sd,)).fetchone()
        check(s == 200 and r and (r["os"], r["device"]) == (os_, device), f"track: {platform} {w}x{h} -> {os_} / {device}",
              (s, b, r and tuple(r)))
    # tezlik cheklovi: 30 so'rov / daqiqa
    rl_user = {"id": 800402, "first_name": "Tez"}
    sd = new_sid()
    codes = [jh("POST", "/api/s/track", {"sid": sd, "device": DEV, "events": [ev("click", "dk-next")]}, S(rl_user))[0] for _ in range(32)]
    check(codes.count(200) == 30 and codes[-2:] == [429, 429], "track: 30 so'rov/daqiqadan keyin 429", codes)

    # ---- funksiyalar
    log("-- funksiyalar (SPEC 10.3)")
    s, _, me = jh("POST", "/api/s/me", {}, S("aziza"))
    check(s == 200 and me.get("features") == {k: True for k in config.FUNKSIYA_KALITLARI}, "me.features: 10 kalit, hammasi true",
          me and me.get("features"))
    s, _, f = jh("GET", "/api/x/features", None, X("ceo"))
    check(s == 200 and [m["key"] for m in f["meta"]] == list(config.FUNKSIYA_KALITLARI)
          and all(set(m) == {"key", "nomi", "tavsif", "bosqich"} and m["bosqich"] in (1, 2, 3) for m in f["meta"]),
          "x/features: meta (key, nomi, tavsif, bosqich)", f)
    check(next(m for m in f["meta"] if m["key"] == "uslub")["nomi"] == "Manzara tanlash", "x/features: uslub nomi 'Manzara tanlash'")
    for role in ("admin", "ustoz", "assistent"):
        s, _, b = jh("POST", "/api/x/features", {"key": "reyting", "on": False}, X(role))
        check(s == 403, f"x/features POST: {role} -> 403", (s, b))
    check(jh("POST", "/api/x/features", {"key": "yoq", "on": False}, X("ceo"))[0] == 400, "x/features: noma'lum kalit -> 400")
    check(jh("POST", "/api/x/features", {"key": "video", "on": "false"}, X("ceo"))[0] == 400, "x/features: on bool emas -> 400")

    def feat(key, on):
        return jh("POST", "/api/x/features", {"key": key, "on": on}, X("ceo"))
    s, _, b = feat("reyting", False)
    check(s == 200 and b["ok"] and b["features"]["reyting"] is False, "reyting o'chirildi", (s, b))
    s, _, b = jh("GET", "/api/s/rating?davr=hafta", None, S("aziza"))
    check(s == 403 and b == XATO_FUNKSIYA, "reyting o'chiq: /api/s/rating -> 403", (s, b))
    check(jh("POST", "/api/s/me", {}, S("aziza"))[2]["features"]["reyting"] is False, "me.features.reyting = false")
    feat("reyting", True)
    check(jh("GET", "/api/s/rating?davr=hafta", None, S("aziza"))[0] == 200, "reyting yoqildi: /api/s/rating -> 200")
    vids = json.loads(config.VIDEOLAR_FILE.read_text(encoding="utf-8")) if config.VIDEOLAR_FILE.exists() else []
    vid = vids[0]["id"] if vids else "d02"
    s0 = http("GET", f"/media/video/{vid}", headers={"Range": "bytes=0-9"})[0]
    feat("video", False)
    check(http("GET", f"/media/video/{vid}", headers={"Range": "bytes=0-9"})[0] == 404, "video o'chiq: /media/video -> 404")
    feat("video", True)
    check(http("GET", f"/media/video/{vid}", headers={"Range": "bytes=0-9"})[0] == s0 and s0 in (206, 404),
          "video yoqildi: /media/video avvalgidek", s0)
    key8 = [q["ok"] for q in test8["savollar"]]
    with con() as c:
        before = c.execute("SELECT COUNT(*) FROM test_answers WHERE user_id=800002 AND dars=8").fetchone()[0]
    feat("test", False)
    s, _, b = jh("POST", "/api/s/event", {"type": "test_done", "dars": 8, "answers": key8}, S("jahongir"))
    with con() as c:
        after = c.execute("SELECT COUNT(*) FROM test_answers WHERE user_id=800002 AND dars=8").fetchone()[0]
    check(s == 403 and b == XATO_FUNKSIYA and after == before, "test o'chiq: test_done -> 403, javoblar yozilmadi", (s, b))
    feat("test", True)
    feat("uslub", False)
    me = jh("POST", "/api/s/me", {}, S("aziza"))[2]
    with con() as c:
        dbu = c.execute("SELECT uslub FROM users WHERE id=800001").fetchone()[0]
    check(me["prefs"]["uslub"] == "game" and dbu is None, "uslub o'chiq: tanlamagan o'quvchi -> 'game' (bazaga yozilmaydi)",
          (me["prefs"], dbu))
    me_j = jh("POST", "/api/s/me", {}, S("jahongir"))[2]
    check(me_j["prefs"]["uslub"] == "game", "uslub o'chiq: tanlagan o'quvchi o'z uslubida", me_j["prefs"])
    feat("uslub", True)
    check(jh("POST", "/api/s/me", {}, S("aziza"))[2]["prefs"]["uslub"] is None, "uslub yoqildi: Aziza yana null")
    # 19:00 eslatma va 21:00 hisobot (callback lar to'g'ridan-to'g'ri, soxta bot bilan)
    import staff_bot
    import student_bot
    from kurs import Kurs

    class FakeBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text, reply_markup=None, **kw):
            self.sent.append((chat_id, text, reply_markup))

    config.XABAR_ORALIQ = 0.0
    st = dbm.Store(DB)
    t19 = datetime.now(TZ).replace(hour=19, minute=0, second=0, microsecond=0)
    svc = types.SimpleNamespace(store=st, kurs=Kurs(), base_url=BASE, brend="Muhammadamin", now=lambda: t19)
    ctx = types.SimpleNamespace(application=types.SimpleNamespace(bot_data={"svc": svc}))
    for key, job in (("eslatma", student_bot.job_eslatma), ("hisobot", staff_bot.job_hisobot)):
        feat(key, False)
        b1 = FakeBot()
        ctx.bot = b1
        asyncio.run(job(ctx))
        feat(key, True)
        b2 = FakeBot()
        ctx.bot = b2
        asyncio.run(job(ctx))
        check(not b1.sent and b2.sent, f"{key} o'chiq -> hech narsa yuborilmadi; yoqilgach yuborildi", (len(b1.sent), len(b2.sent)))
    hb = [x for x in b2.sent]
    btn = hb[0][2].inline_keyboard[0][0] if hb and hb[0][2] else None
    check(btn is not None and btn.web_app.url == BASE + "/admin/", "21:00 hisobot tugmasi -> /admin/", btn)
    check(jh("GET", "/api/x/features", None, X("ceo"))[2]["features"] == {k: True for k in config.FUNKSIYA_KALITLARI},
          "funksiyalar oxirida hammasi qayta yoqilgan")

    # ---- test_done -> test_answers
    log("-- test_done -> test_answers")
    with con() as c:
        tries0 = c.execute("SELECT tries FROM tests WHERE user_id=800002 AND dars=8").fetchone()
    tries0 = tries0[0] if tries0 else 0
    picks = [key8[0], (key8[1] + 1) % 4, key8[2]]
    s, _, b = jh("POST", "/api/s/event", {"type": "test_done", "dars": 8, "answers": picks}, S("jahongir"))
    with con() as c:
        rows = c.execute("SELECT q, pick, ok, try_no FROM test_answers WHERE user_id=800002 AND dars=8 AND try_no=? ORDER BY q",
                         (tries0 + 1,)).fetchall()
    exp = [(1, key8[0], 1), (2, (key8[1] + 1) % 4, 0), (3, key8[2], 1)] + [(i + 1, None, 0) for i in range(3, len(key8))]
    check(s == 200 and b["item"]["tries"] == tries0 + 1 and [(r["q"], r["pick"], r["ok"]) for r in rows] == exp,
          "test_done: har savolga qator (q 1 dan, try_no = tries, javobsiz -> pick NULL, ok 0)", [tuple(r) for r in rows])
    s, _, b = jh("POST", "/api/s/event", {"type": "test_done", "dars": 8, "answers": key8}, S("jahongir"))
    with con() as c:
        okc = c.execute("SELECT SUM(ok), COUNT(*) FROM test_answers WHERE user_id=800002 AND dars=8 AND try_no=?", (tries0 + 2,)).fetchone()
    check(s == 200 and tuple(okc) == (len(key8), len(key8)), "test_done: ikkinchi urinish alohida try_no bilan", tuple(okc))

    # ---- rollar x marshrutlar
    log("-- rollar (SPEC 10.1): initData, X-Staff-Token, cookie")
    with con() as c:
        any_sid = c.execute("SELECT id FROM sessions WHERE user_id=800001 ORDER BY started_at DESC LIMIT 1").fetchone()[0]
    toks = {r: auth.make_panel_token(secret, XODIM[r]["id"], r) for r in ROLES}
    A3 = {"ceo", "admin", "ustoz"}
    A2 = {"ceo", "admin"}
    ALL = set(ROLES)
    routes = [
        ("GET", "/api/x/me", None, A3, True),
        ("GET", "/api/x/overview", None, A2, True),
        ("GET", "/api/x/students", None, ALL, False),
        ("GET", "/api/x/student?id=800001", None, A3, True),
        ("GET", f"/api/x/session?id={any_sid}", None, A3, True),
        ("GET", "/api/x/funnel", None, A2, True),
        ("GET", "/api/x/clicks", None, A2, True),
        ("GET", "/api/x/devices", None, A2, True),
        ("GET", "/api/x/tests", None, A3, True),
        ("GET", "/api/x/test?dars=8", None, A3, True),
        ("GET", "/api/x/dropoff?dars=8", None, A3, True),
        ("GET", "/api/x/features", None, {"ceo"}, True),
        ("POST", "/api/x/features", {"key": "duel", "on": True}, {"ceo"}, True),
        ("GET", "/api/x/audit", None, A2, True),
        ("POST", "/api/x/open", {"n": 36}, A2, False),
        ("GET", "/api/x/stats", None, ALL, False),
        ("GET", "/api/x/course", None, ALL, False),
        ("GET", "/api/x/staff", None, {"ceo"}, False),
    ]
    for method, path, body, allowed, bolim in routes:
        for role in ROLES:
            for how, hdr in (("initData", X(role)), ("token", {"X-Staff-Token": toks[role]}),
                             ("cookie", COOKIE(toks[role], csrf=True))):
                s, _, b = jh(method, path, body, hdr)
                if role in allowed:
                    good = s == 200
                else:
                    good = s == 403 and isinstance(b, dict) and "xato" in b and (not bolim or b == XATO_BOLIM)
                check(good, f"rol: {role:9s} {method} {path.split('?')[0]} ({how}) -> {'200' if role in allowed else '403'}",
                      (s, b if not isinstance(b, dict) else {k: b[k] for k in list(b)[:3]}))
        for name, hdr in (("headersiz", {}), ("talaba imzosi", S("aziza")), ("begona", X("begona")),
                          ("buzuq cookie", COOKIE("abc.def", csrf=True))):
            s, _, b = jh(method, path, body, hdr)
            check(s in (401, 403) and isinstance(b, dict) and "xato" in b, f"rol: {name} {method} {path.split('?')[0]} -> 401/403", (s, b))

    # ---- /api/x/me
    log("-- /api/x/me")
    for role in ("ceo", "admin", "ustoz"):
        s, _, me = jh("GET", "/api/x/me", None, X(role))
        check(s == 200 and me["role"] == role and me["sections"] == SECTIONS[role] and me["brend"] == "Muhammadamin"
              and me["browser"] is False and me["features"] == {k: True for k in config.FUNKSIYA_KALITLARI}
              and me["user"]["id"] == XODIM[role]["id"],
              f"me: {role} bo'limlari {len(SECTIONS[role])} ta, browser=false", me)
        ce = me["can_edit"]
        check(ce == {"kurs": role in ("ceo", "admin"), "funksiyalar": role == "ceo", "xodimlar": role == "ceo"},
              f"me: {role} can_edit", ce)
    check(jh("GET", "/api/x/me", None, X("ustoz"))[2]["access"] == {"oquvchilar": "read", "kurs": "read", "testlar": "read"},
          "me: ustoz access = read")
    s, _, b = jh("GET", "/api/x/me", None, X("assistent"))
    check(s == 403 and b == XATO_BOLIM, "me: assistent -> 403 'Bu bo'lim sizga ochiq emas'", (s, b))
    check(jh("GET", "/api/x/me", None, COOKIE(toks["admin"]))[2]["browser"] is True, "me: cookie bilan browser=true")

    # ---- o'quvchilar ro'yxati va kartasi
    log("-- /api/x/students, /api/x/student, /api/x/session")
    s, _, sl = jh("GET", "/api/x/students", None, X("ustoz"))
    keys = {"id", "name", "username", "joined_at", "last_seen", "xp", "streak", "lessons_done", "videos_done", "uslub", "rejim",
            "device_label", "sessions", "last_session_at", "manzara", "mavzu"}  # 06.10: + manzara, mavzu (oxirgi ko'rinish)
    az = next((x for x in sl["students"] if x["id"] == 800001), None)
    with con() as c:
        n_az = c.execute("SELECT COUNT(*), MAX(started_at) FROM sessions WHERE user_id=800001").fetchone()
    check(s == 200 and set(sl["students"][0]) == keys, "students: eski maydonlar + device_label, sessions, last_session_at",
          sl["students"][0] if sl.get("students") else sl)
    check(az and az["sessions"] == n_az[0] and az["last_session_at"] == n_az[1] and az["device_label"] == "Android telefon",
          "students: Aziza seanslari bazaga mos", (az, tuple(n_az)))
    with con() as c:
        kor = {r[0]: (r[1], r[2]) for r in c.execute(
            """SELECT user_id, manzara, mavzu FROM (SELECT user_id, manzara, mavzu,
                 ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY started_at DESC, rowid DESC) AS rn
               FROM sessions WHERE manzara IS NOT NULL) WHERE rn = 1""")}
    got = {x["id"]: (x["manzara"], x["mavzu"]) for x in sl["students"]}
    want = {u: kor.get(u, (None, None)) for u in got}
    check(got == want and any(v[0] for v in got.values()) and any(v[0] is None for v in got.values()),
          "students: manzara/mavzu = manzarasi bor oxirgi seansdan (yo'q bo'lsa null)", {u: (got[u], want[u]) for u in got if got[u] != want[u]})
    s, _, sd = jh("GET", "/api/x/student?id=800001", None, X("ustoz"))
    check(s == 200 and set(sd) >= {"user", "prefs", "stats", "devices", "lessons", "tests", "videos", "sessions"},
          "student: maydonlar", sd and sorted(sd))
    check(sd["user"]["id"] == 800001 and sd["user"]["name"] == "Aziza Karimova" and sd["prefs"]["uslub"] is None
          and set(sd["stats"]) >= {"xp", "streak", "best_streak"} and sd["stats"]["streak"] == 3,
          "student: user, prefs, stats (seriya 3)", (sd["user"], sd["stats"]))
    check(len(sd["lessons"]) == len(lessons) and all(set(x) >= {"n", "nomi", "seen", "slaydlar", "done_at", "started_at"} for x in sd["lessons"])
          and sd["lessons"][7]["n"] == 8 and sd["lessons"][7]["seen"] == 3 and sd["lessons"][0]["done_at"],
          "student: 36 dars (8-dars 3 slayd ko'rilgan, 1-dars tugagan)", sd["lessons"][7])
    t8 = next((t for t in sd["tests"] if t["dars"] == 8), None)
    check(t8 and t8["tries"] == 2 and len(t8["last_answers"]) == len(key8)
          and all(set(a) == {"q", "pick", "ok"} for a in t8["last_answers"]) and sum(a["ok"] for a in t8["last_answers"]) == t8["last"],
          "student: tests + last_answers (oxirgi urinish)", t8)
    check(all(set(v) >= {"id", "nomi", "pos", "davomiylik", "done_at"} for v in sd["videos"])
          and any(v["id"] == "d02" and v["pos"] == 312.5 for v in sd["videos"]), "student: videolar (d02 pos 312.5)")
    check(sd["devices"] and all(set(d) >= {"label", "os", "platform", "tg_version", "screen", "last_at", "sessions"} for d in sd["devices"])
          and sum(d["sessions"] for d in sd["devices"]) == n_az[0], "student: qurilmalar (seanslar yig'indisi)", sd["devices"])
    ss = sd["sessions"]
    check(0 < len(ss) <= 50 and all(set(x) >= {"id", "started_at", "dur_s", "device_label", "screens", "clicks", "ended"} for x in ss)
          and [x["started_at"] for x in ss] == sorted([x["started_at"] for x in ss], reverse=True)
          and any(x["ended"] is False for x in ss), "student: seanslar (yangisi birinchi, jonli seans ended=false)", ss[:2])
    for q, code in (("id=abc", 400), ("id=", 400), ("", 400), ("id=1", 404), ("id=99999999999999", 400)):
        check(jh("GET", f"/api/x/student?{q}", None, X("ceo"))[0] == code, f"student?{q} -> {code}")
    s, _, se = jh("GET", f"/api/x/session?id={any_sid}", None, X("admin"))
    tl = se["timeline"] if s == 200 else []
    check(s == 200 and se["user"] == {"id": 800001, "name": "Aziza Karimova"} and se["session"]["id"] == any_sid
          and len(tl) == se["session"]["screens"] + se["session"]["clicks"] + sum(1 for x in tl if x["kind"] in ("end", "resume")),
          "session: user, seans, timeline soni hisoblagichlarga mos", s)
    check(tl and all(set(x) == {"at", "kind", "name", "label", "ref", "ref_label", "screen", "screen_label", "dur_ms"} for x in tl)
          and [x["at"] for x in tl] == sorted(x["at"] for x in tl) and all(x["label"] for x in tl),
          "session: timeline maydonlari, xronologik, yorliqlar bor", tl[:3])
    tab = next((x for x in tl if x["kind"] == "click" and x["name"] == "tab"), None)
    check(tab is None or tab["label"].startswith("Bo'lim almashtirish: "), "session: tab tugmasi yorlig'ida bo'lim nomi", tab)
    # 05.10: ref_label - ichki id o'rniga o'qiladigan nom (duel -> "X bilan", video -> "N-dars videosi", dars -> "N-dars")
    rich = None
    for uid in range(800001, 800016):
        for sx in jh("GET", f"/api/x/student?id={uid}", None, X("ceo"))[2]["sessions"]:
            t2 = jh("GET", f"/api/x/session?id={sx['id']}", None, X("ceo"))[2]
            nm = {e["name"] for e in t2["timeline"]}
            if "player" in nm and "duel" in nm:
                rich = (uid, t2)
                break
        if rich:
            break
    if check(rich is not None, "session: duel va video bor seed seansi topildi"):
        uid, t2 = rich
        with con() as c:
            def rival(did):
                r = c.execute("SELECT a_id, b_id FROM duels WHERE id=?", (did,)).fetchone()
                if not r:
                    return None
                o = r[1] if r[0] == uid else r[0] if r[1] == uid else None
                u = c.execute("SELECT first_name, last_name, username FROM users WHERE id=?", (o,)).fetchone() if o else None
                return dbm.short_name(*u) if u else None
            bad_r = []
            for e in t2["timeline"]:
                r, lab = e["ref"], e["ref_label"]
                if r in (None, ""):
                    ok = lab is None
                elif e["name"] in ("duel", "duel-natija", "duel-open", "duel-start"):
                    ok = lab == f"{rival(r)} bilan"
                elif e["name"] in ("player", "video"):
                    n = kurs_m.lesson_of_video(r)
                    vs = [v["id"] for v in kurs_m.lesson_videos(kurs_m.lesson(n) or {})]
                    ok = lab == (f"{n}-dars {vs.index(r) + 1}-videosi" if len(vs) > 1 else f"{n}-dars videosi")
                elif e["name"] in ("pick", "duel-pick", "tab", "davr", "set-rejim", "set-arab", "set-manzara", "set-aylanish", "zm-s", "vw-go"):
                    ok = lab is None
                elif e["kind"] == "screen" and r.isdigit():
                    ok = lab == f"{int(r)}-dars"
                else:
                    ok = True
                if not ok:
                    bad_r.append((e["kind"], e["name"], r, lab))
        labs = {e["ref_label"] for e in t2["timeline"] if e["ref_label"]}
        check(not bad_r and any(x.endswith(" bilan") for x in labs) and any("videosi" in x for x in labs) and any(x.endswith("-dars") for x in labs),
              "session.ref_label: raqib, video va dars nomlari (ref xom qoladi)", bad_r[:4] or sorted(labs)[:6])
    for q, code in (("id=bad", 400), ("id=" + new_sid(), 404), ("", 400)):
        check(jh("GET", f"/api/x/session?{q}", None, X("ceo"))[0] == code, f"session?{q[:12]} -> {code}")
    # 2000 dan ko'p voqea -> 2000
    sbig = new_sid()
    u403 = {"id": 800403, "first_name": "Ko'p"}
    for _ in range(21):  # 21 so'rov - 30/daqiqa cheklovidan past
        jh("POST", "/api/s/track", {"sid": sbig, "device": DEV, "events": [ev("click", "dk-next", s="dars")] * 100}, S(u403))
    s, _, se = jh("GET", f"/api/x/session?id={sbig}", None, X("ceo"))
    check(s == 200 and len(se["timeline"]) == 2000 and se["session"]["clicks"] == 2100, "session: timeline <= 2000",
          (s, len(se.get("timeline", [])), se.get("session", {}).get("clicks")))

    # ---- voronka, tugmalar, qurilmalar
    log("-- /api/x/funnel, /api/x/clicks, /api/x/devices")
    s, _, fn = jh("GET", "/api/x/funnel?days=30", None, X("admin"))
    want = ["kirdi", "tanishuv", "d1_boshladi", "d1_tugatdi", "t1", "d2_boshladi", "d5_tugatdi", "d10_tugatdi", "d20_tugatdi",
            "d36_tugatdi"]
    check(s == 200 and [x["key"] for x in fn["steps"]] == want and all(set(x) == {"key", "nomi", "users"} and x["nomi"] for x in fn["steps"]),
          "funnel: 10 qadam SPEC tartibida (05.10: uslub -> tanishuv)", fn and fn.get("steps"))
    check(fn["steps"][1]["nomi"] == "Tanishuvni tugatdi" and "Uslub tanladi" not in json.dumps(fn, ensure_ascii=False),
          "funnel: 2-qadam 'Tanishuvni tugatdi' (eski 'Uslub tanladi' yo'q)", fn["steps"][1])
    since30 = dbm.iso(dbm.day_start(today - timedelta(days=29)))
    with con() as c:
        j = c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since30,)).fetchone()[0]
        us = c.execute("""SELECT COUNT(*) FROM users u WHERE joined_at >= ? AND (uslub IS NOT NULL OR EXISTS (SELECT 1 FROM ui_events e
                          WHERE e.user_id=u.id AND e.kind='click' AND e.name IN ('ob-done','ob-skip')))""", (since30,)).fetchone()[0]
        us_old = c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ? AND uslub IS NOT NULL", (since30,)).fetchone()[0]
        d1 = c.execute("""SELECT COUNT(*) FROM users u WHERE joined_at >= ? AND EXISTS (SELECT 1 FROM lessons l
                          WHERE l.user_id=u.id AND l.dars=1 AND l.done_at IS NOT NULL)""", (since30,)).fetchone()[0]
        t1 = c.execute("""SELECT COUNT(*) FROM users u WHERE joined_at >= ? AND EXISTS (SELECT 1 FROM tests t
                          WHERE t.user_id=u.id AND t.dars=1 AND t.tries>0)""", (since30,)).fetchone()[0]
        l8 = c.execute("SELECT COUNT(*), SUM(done_at IS NOT NULL) FROM lessons WHERE dars=8").fetchone()
    st_ = {x["key"]: x["users"] for x in fn["steps"]}
    check(fn["joined"] == j and st_["kirdi"] <= j and st_["tanishuv"] == us and st_["d1_tugatdi"] == d1 and st_["t1"] == t1 and t1 > 0,
          "funnel: qadamlar bazaga mos (tanishuv, d1_tugatdi, t1 > 0)", (fn["joined"], j, st_, us, d1, t1))
    check(us_old < st_["tanishuv"] < j, "funnel: tanishuv = eski uslub + ob-done/ob-skip tugmasi (seed: 0 ham emas, hamma ham emas)",
          (us_old, st_["tanishuv"], j))
    f8 = next((x for x in fn["lessons"] if x["n"] == 8), {})
    check(len(fn["lessons"]) == len(lessons) and f8.get("started") == l8[0] and f8.get("done") == (l8[1] or 0),
          "funnel.lessons: 36 dars, 8-dars boshlagan/tugatgan bazaga mos", (f8, tuple(l8)))
    s, _, ck = jh("GET", "/api/x/clicks?days=7", None, X("ceo"))
    tops = ck.get("top", []) if s == 200 else []
    check(s == 200 and 0 < len(tops) <= 50 and all(set(x) == {"name", "ref", "ref_label", "label", "screen", "screen_label", "count", "users"} for x in tops)
          and [x["count"] for x in tops] == sorted([x["count"] for x in tops], reverse=True),
          "clicks: top (<= 50, kamayish tartibida, maydonlar)", tops[:2])
    tabs = [x for x in tops if x["name"] == "tab"]
    check(all(x["ref"] and ":" in x["label"] for x in tabs)
          and len({(x["screen"], x["ref"]) for x in tabs}) == len(tabs)
          and all(x["ref"] is None for x in tops if x["name"] not in ("tab", "davr", "set-rejim", "set-uslub", "set-arab",
                                                                     "set-manzara", "set-aylanish")),
          "clicks: 'tab' bo'lim bo'yicha alohida qatorlar (ref + yorliq)", tabs[:3])
    check(all(x["ref_label"] == yorliqlar.qiymat_nomi(x["name"], x["ref"]) for x in tops)
          and all(x["ref_label"] == yorliqlar.ekran_nomi(x["ref"]) and x["label"].endswith(x["ref_label"]) for x in tabs)
          and all(x["ref_label"] is None for x in tops if x["ref"] is None), "clicks: ref_label (o'qiladigan qiymat, ref xom)", tabs[:2])
    since7 = dbm.iso(dbm.day_start(today - timedelta(days=6)))
    with con() as c:
        top_db = c.execute("""SELECT name, screen, COUNT(*), COUNT(DISTINCT user_id) FROM ui_events WHERE kind='click' AND at >= ?
                              GROUP BY name, screen ORDER BY COUNT(*) DESC LIMIT 1""", (since7,)).fetchone()
        v_db = c.execute("SELECT COUNT(*) FROM ui_events WHERE kind='screen' AND at >= ? AND name='dars'", (since7,)).fetchone()[0]
        daily_db = c.execute("SELECT COUNT(*) FROM ui_events WHERE kind='click' AND at >= ?", (dbm.iso(dbm.day_start(today)),)).fetchone()[0]
    check(tops and (tops[0]["name"], tops[0]["screen"], tops[0]["count"], tops[0]["users"]) == tuple(top_db),
          "clicks: eng ko'p bosilgan tugma bazaga mos", (tops[:1], tuple(top_db) if top_db else None))
    check(tops and tops[0]["label"] == yorliqlar.tugma_nomi(tops[0]["name"]) and tops[0]["label"] != tops[0]["name"], "clicks: yorliqlar")
    dars_v = next((x for x in ck["screens"] if x["name"] == "dars"), {})
    check(dars_v.get("views") == v_db and dars_v.get("label") == "Dars (taqdimot)" and (dars_v.get("avg_ms") or 0) > 0
          and all(set(x) == {"name", "label", "views", "users", "avg_ms"} for x in ck["screens"]),
          "clicks.screens: ko'rishlar, foydalanuvchilar, o'rtacha vaqt", dars_v)
    check(len(ck["daily"]) == 7 and ck["daily"][-1]["day"] == today.isoformat() and ck["daily"][-1]["clicks"] == daily_db,
          "clicks.daily: 7 kun, bugungi tugmalar bazaga mos", (ck["daily"][-1], daily_db))
    s, _, dv = jh("GET", "/api/x/devices?days=30", None, X("ceo"))
    with con() as c:
        n_u = c.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE started_at >= ?", (since30,)).fetchone()[0]
    dims = ("device", "os", "platform", "tg_version", "scheme")
    check(s == 200 and dv["users"] == n_u and all(sum(x["users"] for x in dv[k]) == n_u for k in dims + ("labels",))
          and all(set(x) == {"key", "label", "users"} for k in dims + ("screen", "labels") for x in dv[k]) and len(dv["screen"]) <= 10,
          "devices: har o'quvchi bir marta (oxirgi seansi), har o'lchov yig'indisi = users", (dv.get("users"), n_u))
    ja = next((x for x in dv["labels"] if x["key"] == "Android telefon"), None)
    check(ja and ja["users"] >= 1 and any(x["key"] == "telefon" and x["label"] == "Telefon" for x in dv["device"]),
          "devices: yorliqlar (Android telefon, Telefon)", dv["labels"])

    # ---- testlar, darsdan chiqib ketish
    log("-- /api/x/tests, /api/x/test, /api/x/dropoff")
    s, _, ts = jh("GET", "/api/x/tests", None, X("ustoz"))
    with con() as c:
        since = c.execute("SELECT MIN(at) FROM test_answers").fetchone()[0]
        t8db = c.execute("SELECT COUNT(*), SUM(tries), AVG(best) FROM tests WHERE dars=8 AND tries>0").fetchone()
    t8s = next((x for x in ts.get("lessons", []) if x["dars"] == 8), {})
    check(s == 200 and ts["since"] == since and len(ts["lessons"]) == len(lessons)
          and all(set(x) == {"dars", "nomi", "has_test", "savollar", "takers", "attempts", "avg_best", "perfect", "hardest"} for x in ts["lessons"])
          and all(x["savollar"] == (5 if x["has_test"] else 0) for x in ts["lessons"]),
          "tests: since, 36 dars, maydonlar", (ts.get("since"), since))
    check(t8s.get("takers") == t8db[0] and t8s.get("attempts") == t8db[1] and t8s.get("avg_best") == round(t8db[2], 1)
          and t8s.get("has_test") is True and t8s.get("hardest") and set(t8s["hardest"]) == {"q", "wrong_pct"},
          "tests: 8-dars bazaga mos, eng qiyin savol", (t8s, tuple(t8db)))
    s, _, td = jh("GET", "/api/x/test?dars=8", None, X("admin"))
    sv = td.get("savollar", []) if s == 200 else []
    verb = all({k: q[k] for k in ("q", "opts", "ok", "izoh") if k in q} == {k: o[k] for k in ("q", "opts", "ok", "izoh") if k in o}
               for q, o in zip(sv, test8["savollar"]))
    check(s == 200 and td["dars"] == 8 and len(sv) == len(test8["savollar"]) and verb, "test?dars=8: savollar matni o'zgarmagan (verbatim)", s)
    with con() as c:
        q1 = c.execute("SELECT COUNT(*), SUM(ok=0) FROM test_answers WHERE dars=8 AND q=1").fetchone()
    check(sv and sv[0]["answers"] == q1[0] and sv[0]["wrong_pct"] == round(100 * q1[1] / q1[0]) and len(sv[0]["picks"]) == len(sv[0]["opts"])
          and sum(sv[0]["picks"]) + sv[0]["skipped"] == sv[0]["answers"], "test: answers, wrong_pct, picks bazaga mos", sv[:1])
    check(td["students"] and all(set(x) == {"id", "name", "best", "total", "tries", "updated_at"} for x in td["students"]),
          "test: o'quvchilar ro'yxati", td.get("students", [])[:1])
    check(jh("GET", "/api/x/test?dars=99", None, X("ceo"))[0] == 400 and jh("GET", "/api/x/test", None, X("ceo"))[0] == 400,
          "test: noma'lum / yo'q dars -> 400")
    s, _, do = jh("GET", "/api/x/dropoff?dars=8", None, X("ustoz"))
    with con() as c:
        by = dict(c.execute("SELECT idx, COUNT(*) FROM slides WHERE dars=8 GROUP BY idx").fetchall())
    check(s == 200 and do["slaydlar"] == lessons[8]["slaydlar"] and len(do["seen"]) == lessons[8]["slaydlar"]
          and all(x["users"] == by.get(x["idx"], 0) for x in do["seen"]), "dropoff: har slaydni ko'rganlar bazaga mos", do)
    check(jh("GET", "/api/x/dropoff?dars=0", None, X("ceo"))[0] == 400, "dropoff?dars=0 -> 400")

    # ---- /kirish -> cookie
    log("-- /kirish havolasi va cookie")
    import staff_bot
    st = dbm.Store(DB)
    bsvc = types.SimpleNamespace(store=st, kurs=Kurs(), base_url=BASE, brend="Muhammadamin", xodim_username="b_bot", now=dbm.now_tz)
    r = staff_bot.handle_kirish(bsvc, XODIM["ceo"], dbm.now_tz())
    m = re.fullmatch(re.escape(BASE) + r"/admin/kirish\?k=([A-Za-z0-9_-]{32})", r.link[1]) if r.link else None
    check(r.link and r.link[0] == "Admin panelni ochish" and m and "http" not in r.text and r.button is None,
          "/kirish (ceo): URL tugma (matnda havola yo'q)", (r.text, r.link))
    mk = staff_bot.markup(r.button, r.link)
    check(mk.inline_keyboard[0][0].url == r.link[1] and mk.inline_keyboard[0][0].web_app is None, "/kirish: oddiy url tugma (web_app emas)")
    code = m.group(1) if m else "x"
    with con() as c:
        ll = c.execute("SELECT * FROM login_links WHERE code=?", (code,)).fetchone()
    ttl = (datetime.fromisoformat(ll["expires_at"]) - datetime.fromisoformat(ll["created_at"])).total_seconds() if ll else 0
    check(ll and ll["staff_id"] == 900001 and ttl == 600 and ll["used_at"] is None, "/kirish: login_links qatori, 10 daqiqa", ll and dict(ll))
    ra = staff_bot.handle_kirish(bsvc, XODIM["assistent"], dbm.now_tz())
    check(ra.link is None and "ochiq" in ra.text, "/kirish: assistent -> havola yo'q", ra.text)
    rb = staff_bot.handle_kirish(bsvc, {"id": 123987, "first_name": "Begona"}, dbm.now_tz())
    check(rb.link is None and rb.text == "Bu bot faqat Muhammadamin xodimlari uchun.", "/kirish: begona -> rad", rb.text)
    rn = staff_bot.handle_kirish(types.SimpleNamespace(**dict(vars(bsvc), base_url=None)), XODIM["ceo"], dbm.now_tz())
    check(rn.link is None and "tayyorlanmoqda" in rn.text, "/kirish: manzil yo'q -> kuting", rn.text)
    s, h, body = http("GET", f"/admin/kirish?k={code}")
    sc = h.get("Set-Cookie", "") if h else ""
    tok = re.search(r"noon_admin=([^;]+)", sc)
    check(s == 302 and h.get("Location") == "/admin/", "/admin/kirish: 302 -> /admin/", (s, h and h.get("Location")))
    low = sc.lower()
    check(tok and "httponly" in low and "samesite=lax" in low and "path=/" in low and "max-age=43200" in low and "secure" not in low,
          "cookie: HttpOnly, SameSite=Lax, Path=/, Max-Age=43200 (http -> Secure yo'q)", sc)
    check(h.get("Cache-Control") == "no-store", "/admin/kirish: no-store")
    ctok = tok.group(1) if tok else ""
    info = auth.read_panel_token(secret, ctok)
    check(info and info["id"] == 900001 and info["role"] == "ceo", "cookie qiymati = panel token (ceo)", info)
    s, _, body = http("GET", f"/admin/kirish?k={code}")
    txt = body.decode("utf-8", "replace")
    check(s == 403 and "Havola eskirgan. Xodimlar botiga <b>/kirish</b> deb yozing." in txt and "<html" in txt,
          "/admin/kirish: ikkinchi marta -> 'Havola eskirgan' sahifasi", (s, txt[:200]))
    check(http("GET", "/admin/kirish?k=" + "A" * 32)[0] == 403 and http("GET", "/admin/kirish")[0] == 403,
          "/admin/kirish: noma'lum / bo'sh kod -> 403")
    r2 = staff_bot.handle_kirish(bsvc, XODIM["admin"], dbm.now_tz())
    code2 = r2.link[1].split("k=", 1)[1]
    with con() as c:
        c.execute("UPDATE login_links SET expires_at=? WHERE code=?", (dbm.iso(datetime.now(TZ) - timedelta(seconds=1)), code2))
    check(http("GET", f"/admin/kirish?k={code2}")[0] == 403, "/admin/kirish: muddati o'tgan -> 403")
    r3 = staff_bot.handle_kirish(bsvc, XODIM["ustoz"], dbm.now_tz())
    s, h, _ = http("GET", "/admin/kirish?k=" + r3.link[1].split("k=", 1)[1], headers={"X-Forwarded-Proto": "https"})
    sc3 = h.get("Set-Cookie", "")
    check(s == 302 and "secure" in sc3.lower(), "cookie: X-Forwarded-Proto: https -> Secure", sc3)
    utok = re.search(r"noon_admin=([^;]+)", sc3).group(1)
    check(jh("GET", "/api/x/student?id=800001", None, COOKIE(utok))[0] == 200
          and jh("GET", "/api/x/overview", None, COOKIE(utok))[2] == XATO_BOLIM, "cookie (ustoz): o'quvchi kartasi 200, Bosh sahifa 403")
    # rol o'zgargan (assistent) xodimning havolasi ishlamaydi
    r4 = staff_bot.handle_kirish(bsvc, XODIM["admin"], dbm.now_tz())
    with con() as c:
        c.execute("UPDATE staff SET role='assistent' WHERE id=900002")
    s4 = http("GET", "/admin/kirish?k=" + r4.link[1].split("k=", 1)[1])[0]
    with con() as c:
        c.execute("UPDATE staff SET role='admin' WHERE id=900002")
    check(s4 == 403, "/admin/kirish: havola yaratilgandan keyin assistent bo'lgan xodim -> 403", s4)
    # cookie bilan API
    s, _, me = jh("GET", "/api/x/me", None, COOKIE(ctok))
    check(s == 200 and me["browser"] is True and me["role"] == "ceo", "cookie: GET /api/x/me -> 200, browser=true", (s, me))
    s, _, b = jh("POST", "/api/x/features", {"key": "duel", "on": True}, COOKIE(ctok))
    check(s == 403 and "xato" in b, "cookie: POST X-Requested-With siz -> 403 (CSRF)", (s, b))
    s, _, b = jh("POST", "/api/x/features", {"key": "duel", "on": True}, dict(COOKIE(ctok), **{"X-Requested-With": "XMLHttpRequest"}))
    check(s == 403, "cookie: X-Requested-With noto'g'ri qiymat -> 403", s)
    check(jh("POST", "/api/x/features", {"key": "duel", "on": True}, COOKIE(ctok, csrf=True))[0] == 200, "cookie: POST + X-Requested-With: noon -> 200")
    check(jh("POST", "/api/x/open", {"n": 36}, COOKIE(ctok))[0] == 403, "cookie: /api/x/open CSRF siz -> 403")
    check(jh("POST", "/api/x/features", {"key": "duel", "on": True}, X("ceo"))[0] == 200, "initData bilan POST: X-Requested-With shart emas")
    s, _, b = jh("GET", "/api/x/me", None, COOKIE(ctok[:-2] + ("00" if not ctok.endswith("00") else "11")))
    check(s == 401 and "/kirish" in b["xato"], "cookie: buzilgan -> 401 '/kirish' yo'rig'i", (s, b))
    old_tok = auth.make_panel_token(secret, 900001, "ceo", ttl=-5)
    check(jh("GET", "/api/x/me", None, COOKIE(old_tok))[0] == 401, "cookie: muddati o'tgan -> 401")
    s, h, b = http("POST", "/api/x/logout", {}, COOKIE(ctok))
    check(s == 403, "logout: X-Requested-With siz -> 403", s)
    s, h, b = http("POST", "/api/x/logout", {}, COOKIE(ctok, csrf=True))
    lo = h.get("Set-Cookie", "")
    check(s == 200 and json.loads(b) == {"ok": True} and re.search(r'noon_admin=("")?;', lo) and "max-age=0" in lo.lower(),
          "logout: cookie tozalandi (Max-Age=0)", (s, lo))
    # chiqarilgan xodimning cookie si
    st.staff_set({"id": 900020, "first_name": "Vaqtincha", "last_name": "Admin"}, "admin", 900001, dbm.now_tz())
    r5 = staff_bot.handle_kirish(bsvc, {"id": 900020, "first_name": "Vaqtincha", "last_name": "Admin"}, dbm.now_tz())
    s, h, _ = http("GET", "/admin/kirish?k=" + r5.link[1].split("k=", 1)[1])
    vtok = re.search(r"noon_admin=([^;]+)", h.get("Set-Cookie", "")).group(1)
    check(jh("GET", "/api/x/overview", None, COOKIE(vtok))[0] == 200, "vaqtinchalik admin cookie bilan kirdi")
    check(jh("POST", "/api/x/staff/remove", {"id": 900020}, X("ceo"))[2] == {"ok": True}, "CEO vaqtinchalik adminni chiqardi")
    s, _, b = jh("GET", "/api/x/overview", None, COOKIE(vtok))
    check(s == 403 and b == {"xato": "Bu bo'lim faqat xodimlar uchun"}, "chiqarilgan xodim cookie -> 403", (s, b))
    # /kirish chegarasi: soatiga 20 ta
    with con() as c:
        c.executemany("INSERT INTO login_links(code, staff_id, created_at, expires_at) VALUES (?,?,?,?)",
                      [(f"limit{i:030d}", 900003, dbm.iso(datetime.now(TZ)), dbm.iso(datetime.now(TZ))) for i in range(20)])
    rl = staff_bot.handle_kirish(bsvc, XODIM["ustoz"], dbm.now_tz())
    check(rl.link is None and "ko'p" in rl.text, "/kirish: soatiga 20 tadan keyin rad", rl.text)

    # ---- amallar jurnali
    log("-- amallar jurnali (audit)")
    check(jh("POST", "/api/x/open", {"n": 20}, X("admin"))[2] == {"ok": True, "open": 20}, "open: admin 20")
    s, _, b = jh("POST", "/api/x/open", {"n": 21}, X("ustoz"))
    check(s == 403, "open: ustoz endi -> 403 (OCHISH_ROLLARI)", (s, b))
    jh("POST", "/api/x/open", {"n": 36}, X("ceo"))
    jh("POST", "/api/x/features", {"key": "ball", "on": False}, X("ceo"))
    jh("POST", "/api/x/features", {"key": "ball", "on": True}, X("ceo"))
    jh("POST", "/api/x/invite", {"role": "ustoz"}, X("ceo"))
    s, _, au = jh("GET", "/api/x/audit?limit=50", None, X("admin"))
    items = au.get("items", []) if s == 200 else []
    acts = [x["action"] for x in items]
    check(s == 200 and all(set(x) >= {"at", "staff_name", "action", "label", "detail"} for x in items)
          and [x["at"] for x in items] == sorted([x["at"] for x in items], reverse=True), "audit: maydonlar, yangisi birinchi", items[:2])
    for a in ("open", "feature", "invite", "staff_remove", "kirish"):
        check(a in acts, f"audit: '{a}' yozilgan", acts[:12])
    op = next((x for x in items if x["action"] == "open" and x["detail"].get("to") == 36), None)
    check(op and op["staff_name"] == "Muhammad Amin" and op["label"] == "Ochiq darslar soni o'zgardi: 20 -> 36",
          "audit: ochiq darslar 20 -> 36 (CEO)", op)
    fe = next((x for x in items if x["action"] == "feature" and x["detail"].get("key") == "ball"), None)
    check(fe and fe["label"] == "Funksiya yoqildi: Ball, seriya va kunlik maqsad", "audit: funksiya yorlig'i", fe)
    rm = next((x for x in items if x["action"] == "staff_remove"), None)
    check(rm and rm["detail"].get("id") == 900020 and "Vaqtincha Admin" in rm["label"], "audit: chiqarilgan xodim", rm)
    kr = next((x for x in items if x["action"] == "kirish" and x["staff_name"] == "Vaqtincha Admin"), None)
    check(kr is not None, "audit: kirish - chiqarilgan xodim ismi saqlangan", [x for x in items if x["action"] == "kirish"][:3])
    check(not any(k.startswith("_") for x in items for k in x["detail"]), "audit: ichki maydonlar (_ism) ko'rsatilmaydi")
    check(len(jh("GET", "/api/x/audit?limit=2", None, X("ceo"))[2]["items"]) == 2 and jh("GET", "/api/x/audit?limit=0", None, X("ceo"))[0] == 400,
          "audit: limit")

    # ---- xodimlar boti (Telegramsiz)
    log("-- xodimlar boti: /admin/, /ochiq, /yordam, /kirish")
    r = staff_bot.handle_start(bsvc, XODIM["ceo"], "", dbm.now_tz())
    check(r.button == ("Boshqaruvni ochish", BASE + "/admin/"), "/start: tugma -> /admin/", r.button)
    r = staff_bot.handle_ochiq(bsvc, XODIM["ustoz"], ["5"], dbm.now_tz())
    check("faqat CEO yoki admin" in r.text and st.course_open(36) == 36, "/ochiq 5 (ustoz) -> rad", r.text)
    r = staff_bot.handle_ochiq(bsvc, XODIM["ustoz"], [], dbm.now_tz())
    check(r.text.startswith("Ochiq darslar: 36 / 36.") and "O'zgartirish" not in r.text, "/ochiq (ustoz): faqat ko'rish", r.text)
    r = staff_bot.handle_ochiq(bsvc, XODIM["assistent"], [], dbm.now_tz())
    check(r.text == "Bu buyruq siz uchun emas.", "/ochiq (assistent) -> rad", r.text)
    r = staff_bot.handle_ochiq(bsvc, XODIM["admin"], ["30"], dbm.now_tz())
    with con() as c:
        last = c.execute("SELECT staff_id, action, detail FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    check(r.text.startswith("Saqlandi. Ochiq darslar: 30 / 36.") and last["action"] == "open" and last["staff_id"] == 900002
          and json.loads(last["detail"]).get("via") == "bot", "/ochiq 30 (admin) -> saqlandi + audit (via bot)", (r.text, last and tuple(last)))
    staff_bot.handle_ochiq(bsvc, XODIM["ceo"], ["36"], dbm.now_tz())
    for role in ROLES:
        t = staff_bot.handle_yordam(bsvc, XODIM[role]).text
        check(("/kirish" in t) == (role != "assistent") and ("/ochiq 12" in t) == (role in ("ceo", "admin")),
              f"/yordam ({role}): /kirish va /ochiq rolga mos", t)
    check(("kirish", "Admin panelga brauzer orqali kirish") in staff_bot.COMMANDS, "buyruqlar ro'yxatida /kirish")

    class MBot:
        def __init__(self):
            self.mb = None

        async def set_chat_menu_button(self, menu_button=None, **kw):
            self.mb = menu_button
    mbot = MBot()
    ok = asyncio.run(staff_bot.set_menu(types.SimpleNamespace(bot=mbot), bsvc))
    check(ok and mbot.mb.web_app.url == BASE + "/admin/" and mbot.mb.text == "Boshqaruv", "menyu tugmasi 'Boshqaruv' -> /admin/", mbot.mb)

    # ---- statik /admin/
    log("-- /admin/ statik")
    s, h, _ = http("GET", "/admin")
    check(s == 302 and h.get("Location") == "/admin/", "/admin -> 302 /admin/")
    s, h, _ = http("GET", "/admin/")
    if (config.ADMIN_DIR / "index.html").is_file():
        check(s == 200 and h.get("Cache-Control") == "no-cache" and h.get("Content-Type", "").startswith("text/html")
              and h.get("X-Content-Type-Options") == "nosniff", "/admin/: index.html (no-cache)", (s, h.get("Cache-Control")))
        for f in sorted(config.ADMIN_DIR.glob("*.*")):
            s, h, _ = http("GET", "/admin/" + f.name)
            check(s == 200 and h.get("Cache-Control") in ("no-cache", "public, max-age=604800"), f"/admin/{f.name} -> 200", s)
    else:
        check(s == 404, "/admin/: web/admin hali yo'q -> 404 (admin panel agenti yaratadi)", s)
    for a in ("/admin/..%2F..%2Fserver%2Fconfig.py", "/admin/%2e%2e/server/db.py", "/admin/.env", "/admin/kirish/../../server/web.py"):
        s, _, body = http("GET", a)
        check(s in (400, 403, 404) and b"import " not in body, f"/admin traversal rad: {a}", s)

    # ---- talaba API eski xatti-harakati buzilmagan
    log("-- orqaga moslik")
    s, _, me = jh("POST", "/api/s/me", {}, S("aziza"))
    # 04.10 (SPEC 11.3): + duel_pending
    check(s == 200 and set(me) == {"user", "prefs", "stats", "progress", "course", "features", "duel_pending"},
          "me: eski maydonlar + features + duel_pending", sorted(me))
    s, _, au2 = jh("POST", "/api/x/auth", {}, X("ustoz"))
    check(s == 200 and [p["key"] for p in au2["panels"]] == ["ustoz", "lms"], "x/auth (eski /staff ilova) ishlayapti")


# ---------------------------------------------------------------- tezlik (10k o'quvchi / 1M ui_events)
def perf_tests() -> None:
    log("\n== TEZLIK: 10 000 o'quvchi, 1 000 000 ui_events (vaqtinchalik baza) ==")
    import random
    from kurs import Kurs
    d = Path(tempfile.mkdtemp())
    path = d / "perf.db"
    st = dbm.Store(path)
    kurs = Kurs()
    now = dbm.now_tz()
    rng = random.Random(5)
    c = st._conn()
    t0 = time.time()
    # tez yuklash: indekslarsiz yoziladi, keyin Store.init() indekslarni qayta yaratadi
    for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall():
        c.execute(f"DROP INDEX {name}")
    c.execute("PRAGMA cache_size=-262144")
    c.execute("PRAGMA synchronous=OFF")
    c.execute("BEGIN")
    n_users, n_ev = 10_000, 1_000_000
    c.executemany("INSERT INTO users(id, first_name, last_name, username, joined_at, last_seen, uslub, rejim) VALUES (?,?,?,?,?,?,?,?)",
                  ((100000 + i, f"Ism{i}", f"Fam{i}", f"user{i}", dbm.iso(now - timedelta(days=rng.randint(0, 60))),
                    dbm.iso(now - timedelta(minutes=rng.randint(0, 80000))), rng.choice(["game", "glass", None]), "auto")
                   for i in range(n_users)))
    sess = []
    for i in range(100_000):
        u = 100000 + rng.randrange(n_users)
        st_t = now - timedelta(seconds=rng.randint(0, 60 * 86400))
        pf = rng.choice(dbm.SEED_QURILMALAR)
        os_, dv = dbm.classify_device(pf[0], pf[2], pf[3], pf[4])
        sess.append((str(uuid.UUID(int=rng.getrandbits(128), version=4)), u, dbm.iso(st_t), dbm.iso(st_t + timedelta(seconds=300)),
                     None, pf[0], pf[1], os_, dv, f"{pf[2]}x{pf[3]}", "light", "game", "auto", pf[4], 4, 6))
    c.executemany("""INSERT INTO sessions(id, user_id, started_at, last_at, ended_at, platform, tg_version, os, device, screen, scheme,
                     uslub, rejim, ua, screens, clicks) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", sess)
    names_c = list(yorliqlar.TUGMA_NOMI)
    names_s = ["bosh", "darslar", "dars", "video", "reyting", "profil", "mashq", "natija"]

    def gen():
        for i in range(n_ev):
            s_ = sess[i % len(sess)]
            at = datetime.fromisoformat(s_[2]) + timedelta(seconds=(i // len(sess)) * 7)
            if i % 3 == 0:
                yield (s_[0], s_[1], dbm.iso_ms(at), "screen", rng.choice(names_s), None, rng.choice(names_s), rng.randint(500, 60000))
            else:
                yield (s_[0], s_[1], dbm.iso_ms(at), "click", rng.choice(names_c), None, rng.choice(names_s), None)
    c.executemany("INSERT INTO ui_events(session_id, user_id, at, kind, name, ref, screen, dur_ms) VALUES (?,?,?,?,?,?,?,?)", gen())
    c.executemany("INSERT OR IGNORE INTO lessons(user_id, dars, started_at, done_at) VALUES (?,?,?,?)",
                  ((100000 + rng.randrange(n_users), rng.randint(1, 36), dbm.iso(now), dbm.iso(now) if rng.random() < .7 else None)
                   for _ in range(150_000)))
    c.executemany("INSERT OR IGNORE INTO slides(user_id, dars, idx, seen_at) VALUES (?,?,?,?)",
                  ((100000 + rng.randrange(n_users), rng.randint(1, 36), rng.randint(1, 15), dbm.iso(now)) for _ in range(1_000_000)))
    c.executemany("INSERT OR IGNORE INTO days(user_id, day, xp) VALUES (?,?,?)",
                  ((100000 + rng.randrange(n_users), (now.date() - timedelta(days=rng.randint(0, 60))).isoformat(), rng.randint(0, 80))
                   for _ in range(200_000)))
    c.executemany("INSERT OR IGNORE INTO tests(user_id, dars, best, last, total, tries, updated_at) VALUES (?,?,?,?,?,?,?)",
                  ((100000 + rng.randrange(n_users), rng.randint(1, 36), rng.randint(0, 5), rng.randint(0, 5), 5, rng.randint(1, 3),
                    dbm.iso(now)) for _ in range(30_000)))
    c.executemany("INSERT OR IGNORE INTO test_answers(user_id, dars, try_no, q, pick, ok, at) VALUES (?,?,?,?,?,?,?)",
                  ((100000 + rng.randrange(n_users), rng.randint(1, 36), 1, rng.randint(1, 5), rng.randint(0, 3), rng.randint(0, 1),
                    dbm.iso(now)) for _ in range(150_000)))
    c.execute("COMMIT")
    t1 = time.time()
    st.init()  # indekslar (CREATE INDEX IF NOT EXISTS)
    c.execute("ANALYZE")
    c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    log(f"  (baza tayyorlandi: yozish {t1 - t0:.0f} s, indekslar {time.time() - t1:.0f} s, "
        f"{path.stat().st_size // (1024 * 1024)} MB)")
    sid = sess[0][0]
    cases = [
        ("overview (stats + qo'shimcha)", lambda: (st.staff_stats(now, kurs.lesson_of_video, 14), st.overview_extra(now))),
        ("students (500 ta)", lambda: st.students("", now)),
        ("students ?q=ism12", lambda: st.students("ism12", now)),
        ("student kartasi", lambda: st.student_detail(sess[0][1], kurs, now)),
        ("session timeline", lambda: st.session_detail(sid)),
        ("funnel 30 kun", lambda: st.funnel(now, 30)),
        ("clicks 7 kun", lambda: st.clicks_report(now, 7)),
        ("clicks 30 kun", lambda: st.clicks_report(now, 30)),
        ("devices 30 kun", lambda: st.devices_report(now, 30)),
        ("tests", lambda: st.tests_summary(kurs)),
        ("test?dars=8", lambda: st.test_detail(8, kurs.test(8) or {"savollar": []})),
        ("dropoff 8", lambda: st.dropoff(8, 15)),
        ("course_stats", lambda: st.course_stats()),
    ]
    for name, fn in cases:
        fn()  # isitish
        t1 = time.perf_counter()
        fn()
        dt = (time.perf_counter() - t1) * 1000
        check(dt < 1500, f"tezlik: {name}: {dt:.0f} ms", f"{dt:.0f} ms")
    # track yozish tezligi
    t1 = time.perf_counter()
    for i in range(200):
        st.track(100001, str(uuid.UUID(int=i + 1, version=4)), {"platform": "android", "w": 412, "h": 915},
                 [(now, "click", "dk-next", None, "dars", None)] * 20, now)
    dt = (time.perf_counter() - t1) * 1000 / 200
    check(dt < 100, f"tezlik: track (20 voqea) yozish: {dt:.1f} ms / so'rov", f"{dt:.1f} ms")
    plan = " | ".join(r[3] for r in c.execute(
        "EXPLAIN QUERY PLAN SELECT name, screen, COUNT(*) FROM ui_events INDEXED BY ui_events_vaqt WHERE kind='click' AND at >= ? GROUP BY name, screen",
        ("2026-01-01",)))
    check("COVERING INDEX ui_events_vaqt" in plan, "clicks so'rovi qamrovchi indeksdan foydalanadi", plan)
    st.close()
    try:
        for f in d.iterdir():
            f.unlink()
        d.rmdir()
    except OSError:
        pass


# ---------------------------------------------------------------- ishga tushirish
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--db", default=str(DB.relative_to(ROOT)))
    ap.add_argument("--out", default=str(OUT.relative_to(ROOT)))
    ap.add_argument("--faqat", choices=["unit", "api", "perf"])
    ap.add_argument("--perf", action="store_true", help="tezlik sinovini ham o'tkazish (sekin kompyuterda bir necha daqiqa)")
    ap.add_argument("--kirish", choices=["ceo", "admin", "ustoz"], help="sinov bazasi uchun kirish havolasi + cookie chiqarish")
    a = ap.parse_args()
    configure(a.port, ROOT / a.db, ROOT / a.out)
    if a.kirish:
        if DB.resolve() == config.DB_FILE.resolve():
            print("Ishchi baza (data/noon.db) uchun ishlatilmaydi.", file=sys.stderr)
            return 2
        st = dbm.Store(DB)
        uid = XODIM[a.kirish]["id"]
        if not st.staff_get(uid):
            print(f"{DB.name} da {uid} xodim yo'q (server --seed bilan ishga tushirilganmi?)", file=sys.stderr)
            return 2
        code, exp = st.login_create(uid, dbm.now_tz())
        print(f"Bir martalik havola (10 daqiqa): {BASE}/admin/kirish?k={code}")
        print(f"Cookie: {config.COOKIE_NOMI}={auth.make_panel_token(auth.load_secret(), uid, a.kirish)}")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.faqat in (None, "unit"):
        unit_tests()
    if a.faqat in (None, "api"):
        api_tests()
    if a.faqat == "perf" or (a.faqat is None and a.perf):
        perf_tests()
    log(f"\nNATIJA: {R.ok} ta OK, {len(R.fails)} ta XATO ({time.time() - t0:.0f} s)")
    for f in R.fails:
        log("  - " + f)
    (OUT / "natija.txt").write_text("\n".join(R.lines), encoding="utf-8")
    return 0 if not R.fails else 1


if __name__ == "__main__":
    sys.exit(main())

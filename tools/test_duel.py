"""SPEC 11 (2-bosqich) server sinovlari: duellar va do'st takliflari.

    python tools/test_duel.py                    # unit + API (8820, data/sinov_p2_duel.db, --seed) + soxta Telegram (8821)
    python tools/test_duel.py --faqat unit|api|tg
    python tools/test_duel.py --port 8822 --tg-port 8823

Tekshiriladi: tasodifiy / do'st duellari, qabul xatolari (o'zi, eskirgan, ishlatilgan, umumiy dars yo'q), start/finish
validatsiyasi, kech yuborish, ball (teng natijada vaqt, durrang), bir vaqtda tugatishda ball aniq bir marta, limitlar,
muddat (lazy + soatlik vazifa), funksiya o'chirilganda 403 va bot parametrlari e'tiborsiz, umumiy dars qoidasi (savol
o'yinchi tugatmagan darsdan hech qachon kelmaydi), taklif faqat yangi o'quvchiga, o'zini taklif, 1-dars bonusi ikkalasiga
aniq bir marta, bot xabarlari (soxta Telegram: /start duel_ va ref_), xodim API (rollar), o'quvchi kartasi, seed.
Natija: _sinov/p2-duel/natija.txt. Faqat o'zi ishga tushirgan serverlarni to'xtatadi.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import types
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import config  # noqa: E402
import db as dbm  # noqa: E402
import yorliqlar  # noqa: E402
from sinov_initdata import SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN, TALABA, XODIM, make  # noqa: E402

PORT = 8820
TG_PORT = 8821
DB = ROOT / "data" / "sinov_p2_duel.db"
TG_DB = ROOT / "data" / "sinov_p2_duel_tg.db"
OUT = ROOT / "_sinov" / "p2-duel"
BASE = f"http://127.0.0.1:{PORT}"
TZ = config.TZ
ROLES = ("ceo", "admin", "ustoz", "assistent")
XATO_BOLIM = {"xato": "Bu bo'lim sizga ochiq emas"}
XATO_FUNKSIYA = {"xato": "Bu funksiya hozircha o'chirilgan"}
EMOJI_RE = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in ((0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2B00, 0x2BFF),
                                                                       (0x2190, 0x21FF))) + chr(0xFE0F) + chr(0x200D) + "]")
DINIY = ("assalomu", "alaykum", "bismillah", "insha", "alloh", "duo", "namoz")
TESTS = {}


def test_of(n: int) -> list:
    if n not in TESTS:
        TESTS[n] = json.loads((config.CONTENT_DIR / "test" / f"{n:02d}.json").read_text(encoding="utf-8"))["savollar"]
    return TESTS[n]


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
        R.fails.append(f"{name} :: {str(detail)[:500]}")
        log(f"  XATO {name} :: {str(detail)[:500]}")
    return bool(cond)


# ---------------------------------------------------------------- HTTP
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def http(method: str, path: str, body=None, headers: dict | None = None, base: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    req = urllib.request.Request((base or BASE) + path, data=data, method=method, headers=h)
    try:
        with _OPENER.open(req, timeout=30) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def jh(method, path, body=None, headers=None, base=None):
    s, h, b = http(method, path, body, headers, base)
    try:
        return s, json.loads(b) if b else None
    except ValueError:
        return s, None


def U(uid: int, first: str, last: str = "Sinov", username: str | None = None) -> dict:
    return {"id": uid, "first_name": first, "last_name": last, "username": username or f"u{uid}", "language_code": "uz"}


def S(who) -> dict:
    u = TALABA[who] if isinstance(who, str) else who
    return {"X-Init-Data": make(SINOV_TALABA_TOKEN, u)}


def X(who="ceo") -> dict:
    u = XODIM[who] if isinstance(who, str) else who
    return {"X-Init-Data": make(SINOV_XODIM_TOKEN, u)}


_DB_PATH = [DB]


@contextmanager
def con():
    c = sqlite3.connect(_DB_PATH[0], timeout=20)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


def iso(dt: datetime) -> str:
    return dbm.iso(dt)


def now_tz() -> datetime:
    return dbm.now_tz()


def give(uid: int, lessons, when: datetime | None = None) -> None:
    """O'quvchi uchun darslarni bazaga "tugatilgan" deb yozadi (ketma-ketlik va 80% qoidasini chetlab - sinov)."""
    t = iso(when or (now_tz() - timedelta(days=1)))
    with con() as c:
        for n in lessons:
            c.execute("INSERT OR REPLACE INTO lessons(user_id, dars, started_at, done_at) VALUES (?,?,?,?)", (uid, n, t, t))


def me(u) -> dict:
    return jh("POST", "/api/s/me", {}, S(u))[1]


def feat(key: str, on: bool, base: str | None = None):
    return jh("POST", "/api/x/features", {"key": key, "on": on}, X("ceo"), base)


def duel_row(did: str) -> dict:
    with con() as c:
        r = c.execute("SELECT * FROM duels WHERE id=?", (did,)).fetchone()
    return dict(r) if r else {}


def keys_of(did: str) -> list[tuple[int, int, int]]:
    """[(dars, q (1 dan), to'g'ri javob)] - bazadagi savollar tartibida."""
    qs = json.loads(duel_row(did)["questions"])
    return [(x["dars"], x["q"], test_of(x["dars"])[x["q"] - 1]["ok"]) for x in qs]


def answers_for(did: str, correct: int, ms: list[int] | int = 5000, missing_ms: set | None = None) -> list[dict]:
    ks = keys_of(did)
    out = []
    for i, (_, _, ok) in enumerate(ks):
        m = ms[i] if isinstance(ms, list) else ms
        a = {"pick": ok if i < correct else (ok + 1) % 4}
        if not (missing_ms and i in missing_ms):
            a["ms"] = m
        out.append(a)
    return out


def play(u, did: str, correct: int, ms=5000):
    s1, st = jh("POST", "/api/s/duel/start", {"id": did}, S(u))
    s2, fn = jh("POST", "/api/s/duel/finish", {"id": did, "answers": answers_for(did, correct, ms)}, S(u))
    return s1, st, s2, fn


def xp_today(uid: int) -> int:
    with con() as c:
        r = c.execute("SELECT xp FROM days WHERE user_id=? AND day=?", (uid, now_tz().date().isoformat())).fetchone()
    return r[0] if r else 0


def events_of(kind: str, ref: str | None = None) -> list:
    with con() as c:
        if ref is None:
            return [dict(r) for r in c.execute("SELECT * FROM events WHERE kind=? ORDER BY id", (kind,))]
        return [dict(r) for r in c.execute("SELECT * FROM events WHERE kind=? AND ref=? ORDER BY id", (kind, ref))]


# ---------------------------------------------------------------- UNIT
def unit_tests() -> None:
    log("\n== UNIT: ball, g'olib, savol tanlash, validatsiya, yorliqlar, matnlar ==")
    keys = [0, 1, 2, 3, 0]
    good = [{"pick": k, "ms": 4000} for k in keys]
    check(dbm.duel_score(keys, good, False)[:2] == (5, 20000), "duel_score: 5 to'g'ri, 20000 ms", dbm.duel_score(keys, good, False))
    slow = [dict(a) for a in good]
    slow[0]["ms"] = 15001
    slow[1]["ms"] = None
    slow[2]["pick"] = None
    c_, ms_, oks = dbm.duel_score(keys, slow, False)
    check((c_, ms_, oks) == (2, 15000 + 15000 + 4000 * 3, [False, False, False, True, True]),
          "duel_score: ms > 15000 -> xato (vaqt 15000), ms yo'q -> xato (15000), javobsiz -> xato", (c_, ms_, oks))
    check(dbm.duel_score(keys, [dict(a, ms=15000) for a in good], False)[0] == 5, "duel_score: aynan 15000 ms - vaqtida")
    check(dbm.duel_score(keys, good, True) == (0, 75000, [False] * 5), "duel_score: kech yuborilgan -> 0 to'g'ri, 75000 ms")
    check(dbm.duel_winner(4, 50000, 3, 10000) == "a" and dbm.duel_winner(2, 1, 3, 99999) == "b", "duel_winner: ko'proq to'g'ri yutadi")
    check(dbm.duel_winner(4, 30000, 4, 30001) == "a" and dbm.duel_winner(4, 30001, 4, 30000) == "b", "duel_winner: teng - kam vaqt yutadi")
    check(dbm.duel_winner(3, 42000, 3, 42000) is None, "duel_winner: to'liq teng -> durrang (None)")
    import random as _r
    rng = _r.Random(1)
    qs = dbm.Store._pick_questions({8, 9}, {n: 5 for n in range(1, 37)}, rng)
    check(len(qs) == 5 and all(x["dars"] in (8, 9) and 1 <= x["q"] <= 5 for x in qs) and len({(x["dars"], x["q"]) for x in qs}) == 5,
          "_pick_questions: 5 ta, faqat umumiy darslardan, takrorsiz", qs)
    check(len(dbm.Store._pick_questions({4}, {4: 3}, rng) or []) == 3, "_pick_questions: 3 ta savol bo'lsa - 3 ta")
    check(dbm.Store._pick_questions({4}, {4: 2}, rng) is None and dbm.Store._pick_questions(set(), {4: 5}, rng) is None,
          "_pick_questions: 3 tadan kam / umumiy dars yo'q -> None")
    check(dbm.Store._pick_questions({7}, {8: 5}, rng) is None, "_pick_questions: testi yo'q dars hisobga olinmaydi")
    seen = set()
    for i in range(300):
        for x in dbm.Store._pick_questions({1, 2, 3}, {1: 5, 2: 5, 3: 5}, _r.Random(i)):
            seen.add((x["dars"], x["q"]))
    check(len(seen) == 15, "_pick_questions: barcha umumiy savollar tanlanishi mumkin (adolatli)", len(seen))

    import web
    ok5 = [{"pick": 1, "ms": 1000}] * 5
    check(web.norm_duel_answers(ok5, 5) == ok5, "norm_duel_answers: to'g'ri 5 ta javob")
    check(web.norm_duel_answers([{"pick": None}, {"pick": 0, "ms": None}, {"pick": 3, "ms": 0}, {"pick": 2, "ms": 60000},
                                 {"pick": 1, "ms": 1234.0}], 5)[0] == {"pick": None, "ms": None},
          "norm_duel_answers: pick null, ms yo'q/null, 0, 60000, 1234.0 qabul")
    bads = [("4 ta", ok5[:4]), ("6 ta", ok5 + ok5[:1]), ("ro'yxat emas", "x"), ("obyekt emas", [1] * 5),
            ("pick 4", [{"pick": 4, "ms": 1}] + ok5[1:]), ("pick -1", [{"pick": -1, "ms": 1}] + ok5[1:]),
            ("pick bool", [{"pick": True, "ms": 1}] + ok5[1:]), ("pick matn", [{"pick": "1", "ms": 1}] + ok5[1:]),
            ("pick kasr", [{"pick": 1.0, "ms": 1}] + ok5[1:]), ("ms -1", [{"pick": 1, "ms": -1}] + ok5[1:]),
            ("ms 60001", [{"pick": 1, "ms": 60001}] + ok5[1:]), ("ms matn", [{"pick": 1, "ms": "100"}] + ok5[1:]),
            ("ms kasr", [{"pick": 1, "ms": 12.5}] + ok5[1:]), ("ms bool", [{"pick": 1, "ms": True}] + ok5[1:]),
            ("ms NaN", [{"pick": 1, "ms": math.nan}] + ok5[1:])]
    for name, v in bads:
        try:
            web.norm_duel_answers(v, 5)
            check(False, f"norm_duel_answers rad etadi: {name}")
        except dbm.Xato as e:
            check(e.status == 400, f"norm_duel_answers rad etadi: {name} -> 400")

    # yorliqlar (SPEC 11.4)
    scr = ["duellar", "duel", "duel-natija", "taklif", "sheet-duel-yangi"]
    clk = ["duel-new", "duel-random", "duel-friend", "duel-open", "duel-start", "duel-pick", "duel-share", "duel-copy",
           "taklif-open", "taklif-share", "taklif-copy"]
    miss = [k for k in scr if k not in yorliqlar.EKRAN_NOMI] + [k for k in clk if k not in yorliqlar.TUGMA_NOMI]
    check(not miss, f"yorliqlar: {len(scr)} ekran + {len(clk)} tugma (SPEC 11.4)", miss)
    labels = [yorliqlar.EKRAN_NOMI[k] for k in scr] + [yorliqlar.TUGMA_NOMI[k] for k in clk]
    check(all(v and all(ord(ch) < 0x2190 for ch in v) for v in labels), "yorliqlar: bo'sh emas, emoji yo'q", labels)
    # rollar jadvali
    check(config.BOLIMLAR["duellar"][2] == {"ceo": "read", "admin": "read"}
          and config.BOLIMLAR["takliflar"][2] == {"ceo": "read", "admin": "read"}, "config: duellar/takliflar - ceo, admin (ko'rish)")
    # bot matnlari
    import student_bot as sb
    texts = [sb.duel_chaqiruv_text("Ali V."), sb.duel_qabul_text("Ali V."), sb.duel_natija_text("yutdi", 4, 3, "Ali V.", 15),
             sb.duel_natija_text("yutqazdi", 3, 4, "Ali V.", 0), sb.duel_natija_text("durrang", 3, 3, "Ali V.", 5),
             sb.duel_taklif_text("Ali V."), sb.DUEL_ESKI_TEXT, sb.DUEL_OZI_TEXT, sb.taklif_bonus_text("Ali V.")]
    check(texts[0] == "Ali V. sizni duelga chaqirdi. 24 soat ichida javob bering." and texts[1] == "Ali V. duelni qabul qildi."
          and texts[2].startswith("Duel natijasi: siz yutdingiz 4:3") and texts[3].startswith("Duel natijasi: siz yutqazdingiz 3:4")
          and texts[4].startswith("Duel natijasi: durrang 3:3") and texts[5].startswith("Duelga taklif")
          and texts[8] == "Do'stingiz Ali V. 1-darsni tugatdi: sizga va unga +50 ball.", "bot matnlari (SPEC 11.3)", texts)
    check(not any(EMOJI_RE.search(t) or any(w in t.lower() for w in DINIY) for t in texts), "bot matnlari: emoji va diniy so'z yo'q")
    check(sb.duel_url("https://a.b", "abcdefghij") == "https://a.b/app/?duel=abcdefghij"
          and sb.duel_kod_url("https://a.b/", "abcdefghij") == "https://a.b/app/?duel_kod=abcdefghij" and sb.duel_url(None, "x") is None,
          "bot: WebApp manzillari ?duel= va ?duel_kod=")

    db_unit_tests()


def db_unit_tests() -> None:
    """Store darajasida: ikki alohida ulanish (ikki jarayon kabi) bir vaqtda tugatadi -> ball aniq bir marta; muddat."""
    log("-- unit: Store (vaqtinchalik baza) - bir vaqtda tugatish, muddat, kech yuborish")
    path = Path(tempfile.mkdtemp()) / "duel.db"
    st = dbm.Store(path)
    now = now_tz()
    pool = {n: 5 for n in range(1, 37)}
    for uid in (1, 2):
        st.upsert_user({"id": uid, "first_name": f"T{uid}"}, now)
    with st._c(True) as c:
        for uid in (1, 2):
            c.execute("INSERT INTO lessons(user_id, dars, started_at, done_at) VALUES (?, 8, ?, ?)", (uid, iso(now), iso(now)))
    keys = [0] * 5
    for rnd in range(6):
        did = st.duel_new_random(1, pool, now) if rnd == 0 else None
        if did is None:
            code, _ = st.duel_invite_create(1, pool, now)
            did, _ = st.duel_accept(2, code, pool, now)
        st.duel_start(1, did, now)
        st.duel_start(2, did, now)
        bar = threading.Barrier(2)
        res = {}

        def fin(uid, correct):
            s2 = dbm.Store(path)  # alohida ulanish (boshqa jarayon kabi)
            ans = [{"pick": 0 if i < correct else 1, "ms": 3000} for i in range(5)]
            bar.wait()
            res[uid] = s2.duel_finish(uid, did, ans, keys, now + timedelta(seconds=20))
        ts = [threading.Thread(target=fin, args=(1, 4)), threading.Thread(target=fin, args=(2, 3))]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        with st._c() as c:
            ev = c.execute("SELECT user_id, xp FROM events WHERE kind='duel_done' AND ref=?", (did,)).fetchall()
            row = c.execute("SELECT status, winner_id FROM duels WHERE id=?", (did,)).fetchone()
        check(len(ev) == 2 and sorted(tuple(x) for x in ev) == [(1, 15), (2, 0)] and tuple(row) == ("tugadi", 1)
              and sum(1 for r in res.values() if r["resolved"]) == 1,
              f"bir vaqtda tugatish ({rnd + 1}): natija va ball aniq bir marta (ikki ulanish)", (ev and [tuple(x) for x in ev], tuple(row)))
    with st._c() as c:
        xp1 = c.execute("SELECT SUM(xp) FROM days WHERE user_id=1").fetchone()[0]
    check(xp1 == 15 * 6, "g'olib balli days jadvalida (6 x 15)", xp1)
    # kech yuborish
    code, _ = st.duel_invite_create(1, pool, now)
    did, _ = st.duel_accept(2, code, pool, now)
    st.duel_start(1, did, now)
    r = st.duel_finish(1, did, [{"pick": 0, "ms": 1000}] * 5, keys, now + timedelta(seconds=config.DUEL_OYNA + 1))
    check(r["late"] and r["row"]["a_correct"] == 0 and r["row"]["a_ms"] == 75000, "kech yuborish (106 s) -> 0 to'g'ri", dict(r["row"]))
    st.duel_start(2, did, now + timedelta(seconds=200))
    r = st.duel_finish(2, did, [{"pick": 0, "ms": 1000}] * 5, keys, now + timedelta(seconds=200 + config.DUEL_OYNA))
    check(not r["late"] and r["resolved"] and r["row"]["winner_id"] == 2, "aynan 105 s -> vaqtida; raqib yutdi", dict(r["row"]))
    # muddat va 105 s oynasi
    code, _ = st.duel_invite_create(1, pool, now)
    did, _ = st.duel_accept(2, code, pool, now)
    t_exp = now + timedelta(seconds=config.DUEL_MUDDAT)
    st.duel_start(1, did, t_exp - timedelta(seconds=10))
    check(st.duels_expire(t_exp + timedelta(seconds=5)) == 0, "muddat: o'ynayotgan o'yinchi oynasi tugaguncha belgilanmaydi")
    rr = st.duel_get(did)
    check(st.duel_view(rr, 1, t_exp + timedelta(seconds=5)) == "sizning_navbat"
          and st.duel_view(rr, 2, t_exp + timedelta(seconds=5)) == "muddati_otdi", "muddat: o'ynayotgan - navbat, ikkinchisi - muddati o'tdi")
    try:
        st.duel_start(2, did, t_exp + timedelta(seconds=5))
        check(False, "muddat o'tgach start -> 410")
    except dbm.Xato as e:
        check(e.status == 410, "muddat o'tgach start -> 410", e.status)
    check(st.duels_expire(t_exp + timedelta(seconds=200)) == 1 and st.duel_get(did)["status"] == "muddati_otdi",
          "soatlik vazifa: oynadan keyin 'muddati_otdi'")
    with st._c() as c:
        n_ev = c.execute("SELECT COUNT(*) FROM events WHERE kind='duel_done' AND ref=?", (did,)).fetchone()[0]
    check(n_ev == 0, "muddati o'tgan duel: ball yo'q")


# ---------------------------------------------------------------- server
def start_server(args: list[str], port: int, out_name: str) -> subprocess.Popen:
    OUT.mkdir(parents=True, exist_ok=True)
    out = open(OUT / out_name, "w", encoding="utf-8")
    p = subprocess.Popen([sys.executable, str(ROOT / "server" / "main.py"), *args], cwd=str(ROOT), stdout=out,
                         stderr=subprocess.STDOUT, creationflags=config.CREATE_NO_WINDOW)
    t0 = time.time()
    while time.time() - t0 < 60:
        if p.poll() is not None:
            raise RuntimeError("server to'xtab qoldi: " + (OUT / out_name).read_text(encoding="utf-8"))
        try:
            s, _, _ = http("GET", "/", base=f"http://127.0.0.1:{port}")
            if s in (301, 302):
                return p
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.3)
    p.kill()
    raise RuntimeError("server 60 s da javob bermadi")


def stop_server(p: subprocess.Popen, stop_file: Path) -> bool:
    stop_file.write_text("stop", encoding="ascii")
    try:
        p.wait(20)
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


def wipe(path: Path) -> None:
    for suf in ("", "-wal", "-shm"):
        try:
            Path(str(path) + suf).unlink()
        except OSError:
            pass


# ---------------------------------------------------------------- API
def api_tests() -> None:
    log(f"\n== API (sinov server, port {PORT}, {DB.name}, --seed) ==")
    _DB_PATH[0] = DB
    wipe(DB)
    p = start_server(["--sinov", "--port", str(PORT), "--db", str(DB.relative_to(ROOT)), "--seed"], PORT, "server_stdout.txt")
    try:
        _api_body()
    except Exception:
        check(False, "API sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        check(stop_server(p, config.DATA_DIR / f"sinov_{PORT}.stop"), "server stop fayli bilan yumshoq to'xtadi")
    logtxt = (config.LOG_DIR / f"sinov_{PORT}.log").read_text(encoding="utf-8", errors="ignore")
    check(SINOV_TALABA_TOKEN not in logtxt and not config.TOKEN_ANY_RE.search(logtxt), "sinov logida token yo'q")


def _api_body() -> None:
    seed_tests()
    friend_tests()
    play_tests()
    random_tests()
    limit_tests()
    expiry_tests()
    concurrency_tests()
    referral_tests()
    switch_tests()
    staff_tests()


def seed_tests() -> None:
    log("-- seed: namuna duellar (har holat), takliflar, umumiy dars qoidasi, ball")
    with con() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM duels")]
        done = {}
        for r in c.execute("SELECT user_id, dars, done_at FROM lessons WHERE done_at IS NOT NULL"):
            done[(r["user_id"], r["dars"])] = r["done_at"]
        statuses = {r["status"] for r in rows}
        refs = [dict(r) for r in c.execute("SELECT * FROM referrals")]
        n_inv = c.execute("SELECT COUNT(*), COUNT(used_by) FROM duel_invites").fetchone()
        dsum = c.execute("SELECT SUM(xp) FROM days").fetchone()[0]
        esum = c.execute("SELECT SUM(xp) FROM events WHERE kind IN ('duel_done', 'taklif_bonus')").fetchone()[0]
        names = {r[0] for r in c.execute("SELECT DISTINCT name FROM ui_events")}
    check(len(rows) >= 8 and statuses == {"tugadi", "faol", "muddati_otdi"}, f"seed: {len(rows)} duel, holatlar: tugadi, faol, muddati_otdi",
          statuses)
    bad = []
    for r in rows:
        for x in json.loads(r["questions"]):
            for uid in (r["a_id"], r["b_id"]):
                d = done.get((uid, x["dars"]))
                if not d or d > r["created_at"]:
                    bad.append((r["id"], uid, x["dars"]))
            if not 1 <= x["q"] <= len(test_of(x["dars"])):
                bad.append((r["id"], "q", x))
        if len(json.loads(r["questions"])) != 5:
            bad.append((r["id"], "n"))
    check(not bad, "seed: har savol ikkala o'yinchi duelgacha tugatgan, testi bor darsdan", bad[:5])
    fin = [r for r in rows if r["status"] == "tugadi"]
    ok_w = all((r["winner_id"] is None) == (r["a_correct"] == r["b_correct"] and r["a_ms"] == r["b_ms"]) for r in fin)
    check(fin and ok_w and any(r["winner_id"] is None for r in fin)
          and any(r["a_correct"] == r["b_correct"] and r["winner_id"] for r in fin), "seed: g'oliblar qoidaga mos (durrang va vaqt bo'yicha)")
    check(len(refs) == 5 and sum(1 for r in refs if r["rewarded_at"]) == 4 and n_inv[0] >= 5 and n_inv[1] >= 3,
          "seed: 5 taklif (4 tasi bonusli), do'st havolalari", (len(refs), n_inv and tuple(n_inv)))
    check(esum and dsum and esum <= dsum, "seed: duel va taklif ballari days jadvalida", (esum, dsum))
    check({"duellar", "duel", "duel-natija", "taklif", "duel-start", "duel-pick", "taklif-share"} <= names,
          "seed: seanslarda duel / taklif ekranlari va tugmalari", sorted(n for n in names if "duel" in n or "taklif" in n))
    # Aziza: har holatdagi duellar
    s, d = jh("GET", "/api/s/duels", None, S("aziza"))
    sts = [x["status"] for x in d["items"]] if s == 200 else []
    check(s == 200 and d["can"] is True and d["reason"] is None and sts[0] == "sizning_navbat"
          and set(sts) == {"sizning_navbat", "raqib_navbati", "tugadi", "muddati_otdi"},
          "Aziza /api/s/duels: barcha holatlar, avval 'sizning_navbat'", sts)
    check(d["stats"] == {"played": 2, "won": 1, "lost": 1, "draw": 0}, "Aziza duel statistikasi", d.get("stats"))
    item_keys = {"id", "mode", "rival", "me_role", "status", "my", "their", "result", "xp", "created_at", "expires_at"}
    check(all(item_keys <= set(x) for x in d["items"]) and all(set(x["rival"]) == {"id", "name"} for x in d["items"]),
          "item: SPEC 11.3 maydonlari", d["items"][:1])
    check(all((x["their"] is None) == (x["status"] != "tugadi") for x in d["items"])
          and all((x["result"] is None) == (x["status"] != "tugadi") for x in d["items"]),
          "item: their/result faqat ikkalasi tugatgach")
    w = next((x for x in d["items"] if x["id"] == "seedduel03"), {})
    check(w.get("result") == "yutdi" and w.get("xp") == 15 and w.get("my", {}).get("correct") == 4 == w.get("their", {}).get("correct")
          and w["my"]["ms"] < w["their"]["ms"], "seedduel03: teng to'g'ri, Aziza tezroq -> yutdi +15", w)
    ex = next((x for x in d["items"] if x["id"] == "seedduel09"), {})
    check(ex.get("status") == "muddati_otdi" and duel_row("seedduel09")["status"] == "faol",
          "seedduel09: bazada 'faol', lekin muddati o'tgan -> API 'muddati_otdi' (lazy)", ex.get("status"))
    s, b = jh("POST", "/api/s/duel/start", {"id": "seedduel09"}, S("aziza"))
    check(s == 409, "seedduel09: o'ynab bo'lingan -> start 409", (s, b))
    m = me("aziza")
    check(m.get("duel_pending") == 1 and set(m) >= {"user", "prefs", "stats", "progress", "course", "features", "duel_pending"},
          "me.duel_pending = 1 (seedduel05)", m.get("duel_pending"))
    s, t = jh("GET", "/api/s/taklif", None, S("aziza"))
    check(s == 200 and t["link"] == "https://t.me/noon_talaba_sinov_bot?start=ref_sd800001" and t["bonus"] == 50 and t["earned"] == 50
          and len(t["friends"]) == 2 and sorted((f["done1"], f["rewarded"]) for f in t["friends"]) == [(False, False), (True, True)]
          and all(set(f) >= {"name", "joined_at", "done1", "rewarded"} for f in t["friends"]) and "share_text" in t,
          "Aziza /api/s/taklif: havola, +50, 2 do'st (biri bonusli)", t)
    s, dj = jh("GET", "/api/s/duels", None, S("jahongir"))
    check(s == 200 and dj["stats"] == {"played": 3, "won": 1, "lost": 1, "draw": 1} and all(x["status"] == "tugadi" for x in dj["items"]),
          "Jahongir: 3 tugagan duel (1 yutuq, 1 mag'lubiyat, 1 durrang)", dj.get("stats"))
    s, dd = jh("GET", "/api/s/duels", None, S(U(800005, "Dilshod", "Ergashev", "dilshod_e")))
    check(s == 200 and len(dd["invites"]) == 1 and dd["invites"][0]["code"] == "seedinv001"
          and dd["invites"][0]["link"].endswith("?start=duel_seedinv001") and dd["limits"]["open"] == 2,
          "Dilshod: ochiq do'st havolasi ro'yxatda, ochiq = 2 (duel + havola)", (dd.get("invites"), dd.get("limits")))
    s, one = jh("GET", "/api/s/duel?id=seedduel03", None, S("aziza"))
    rv = one.get("review") if s == 200 else None
    check(s == 200 and one["duel"]["id"] == "seedduel03" and rv and len(rv) == 5
          and all({"q", "opts", "ok", "pick", "izoh"} <= set(x) for x in rv), "GET /api/s/duel: tugagan duel + review", s)
    ks = keys_of("seedduel03")
    check(rv and all(x["q"] == test_of(dn)[q - 1]["q"] and x["opts"] == test_of(dn)[q - 1]["opts"] and x["ok"] == ok
                     and x["izoh"] == test_of(dn)[q - 1].get("izoh") for x, (dn, q, ok) in zip(rv, ks)),
          "review: savol, variantlar, to'g'ri javob, izoh - test JSON dan o'zgarishsiz")
    s, one = jh("GET", "/api/s/duel?id=seedduel05", None, S("aziza"))
    check(s == 200 and one["review"] is None and one["duel"]["status"] == "sizning_navbat" and one["duel"]["rival_done"] is True,
          "GET /api/s/duel: o'ynalmagan -> review null (javoblar oshkor emas)", one)
    check(jh("GET", "/api/s/duel?id=seedduel01", None, S("aziza"))[0] == 404, "GET /api/s/duel: begona duel -> 404")
    check(jh("GET", "/api/s/duel?id=BAD", None, S("aziza"))[0] == 400, "GET /api/s/duel: noto'g'ri id -> 400")


F1, F2, F3, F4, F5 = (U(810001, "Farhod"), U(810002, "Feruza"), U(810003, "Fotima"), U(810004, "Fazliddin"), U(810005, "Firdavs"))


def friend_tests() -> None:
    log("-- do'st dueli: havola, qabul, xatolar")
    for u in (F1, F2, F3, F4, F5):
        me(u)
    give(F1["id"], [30, 31])
    give(F2["id"], [30])
    give(F4["id"], [30])
    give(F5["id"], [31, 32])
    s, d = jh("GET", "/api/s/duels", None, S(F3))
    check(s == 200 and d["can"] is False and d["reason"] == "Duel uchun avval kamida bitta darsni va uning testini tugating",
          "dars tugatmagan: can=false + sabab", d)
    s, b = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F3))
    check(s == 409 and b["xato"] == dbm.XATO_DUEL_SHART, "dars tugatmagan: do'st havolasi -> 409", (s, b))
    for bad in ({}, {"mode": "x"}, {"mode": None}):
        check(jh("POST", "/api/s/duel/new", bad, S(F1))[0] == 400, f"duel/new {bad} -> 400")
    t0 = now_tz()
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F1))
    code = inv.get("code", "") if s == 200 else ""
    exp = datetime.fromisoformat(inv["expires_at"]) if s == 200 else t0
    check(s == 200 and re.fullmatch(r"[a-z0-9]{10}", code) and inv["link"] == f"https://t.me/noon_talaba_sinov_bot?start=duel_{code}"
          and inv["share_text"] == "Fonetika kursida duelga chaqiraman: 5 savol, har biriga 15 soniya."
          and abs((exp - t0).total_seconds() - 86400) < 30, "duel/new friend: kod, havola, share_text, 24 soat", inv)
    s, d = jh("GET", "/api/s/duels", None, S(F1))
    check(s == 200 and [x["code"] for x in d["invites"]] == [code] and d["limits"]["open"] == 1 and d["limits"]["today"] == 1,
          "duels: ochiq havola ro'yxatda, limitlar", (d.get("invites"), d.get("limits")))
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(F1))
    check(s == 400 and b == {"xato": "O'zingizni chaqira olmaysiz"}, "accept: o'z havolasi -> 400", (s, b))
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(F3))
    check(s == 409 and b == {"xato": "Duel uchun ikkalangiz ham kamida bitta darsni va uning testini tugatgan bo'lishingiz kerak"},
          "accept: umumiy tugatilgan dars yo'q -> 409", (s, b))
    give(F3["id"], [32])
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(F3))
    check(s == 409, "accept: faqat F3 tugatgan dars (32) - umumiy emas -> 409", (s, b))
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(F2))
    did = b["duel"]["id"] if s == 200 else ""
    check(s == 200 and b["duel"]["mode"] == "friend" and b["duel"]["me_role"] == "b" and b["duel"]["status"] == "sizning_navbat"
          and b["duel"]["rival"] == {"id": F1["id"], "name": "Farhod S."} and b["duel"]["lessons"] == [30] and b["duel"]["n"] == 5,
          "accept: duel yaratildi (a = taklif qilgan, b = qabul qilgan, faqat 30-dars)", b)
    r = duel_row(did)
    check(r.get("a_id") == F1["id"] and r.get("b_id") == F2["id"] and all(x["dars"] == 30 for x in json.loads(r["questions"])),
          "bazada: a/b va savollar faqat ikkalasi tugatgan darsdan", r.get("questions"))
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(F2))
    check(s == 200 and b["duel"]["id"] == did, "accept: o'sha o'quvchi qayta ochsa - o'sha duel (idempotent)", (s, b))
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(F4))
    check(s == 410 and b == {"xato": "Taklif eskirgan"}, "accept: ishlatilgan havola -> 410", (s, b))
    with con() as c:
        n_d = c.execute("SELECT COUNT(*) FROM duels WHERE a_id=?", (F1["id"],)).fetchone()[0]
    check(n_d == 1, "takroriy qabul yangi duel yaratmadi", n_d)
    s, inv2 = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F1))
    with con() as c:
        c.execute("UPDATE duel_invites SET expires_at=? WHERE code=?", (iso(now_tz() - timedelta(seconds=1)), inv2["code"]))
    s, b = jh("POST", "/api/s/duel/accept", {"code": inv2["code"]}, S(F4))
    check(s == 410 and b == {"xato": "Taklif eskirgan"}, "accept: muddati o'tgan havola -> 410", (s, b))
    s, b = jh("POST", "/api/s/duel/accept", {"code": "zzzzzzzzzz"}, S(F4))
    check(s == 410, "accept: noma'lum kod -> 410", (s, b))
    for bad in ("", "ABCDEFGHIJ", "abc", None, 123, "a" * 11):
        check(jh("POST", "/api/s/duel/accept", {"code": bad}, S(F4))[0] == 400, f"accept: kod {bad!r} -> 400")
    # umumiy dars qoidasi: F5 {31, 32}, F1 {30, 31} -> faqat 31
    for i in range(2):
        s, inv3 = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F5))
        s, b = jh("POST", "/api/s/duel/accept", {"code": inv3["code"]}, S(F1))
        dd = b["duel"]["id"] if s == 200 else ""
        qs = json.loads(duel_row(dd).get("questions") or "[]")
        check(s == 200 and qs and all(x["dars"] == 31 for x in qs) and b["duel"]["lessons"] == [31],
              f"umumiy dars qoidasi ({i + 1}): {{31,32}} x {{30,31}} -> faqat 31-dars", qs)
        s, st = jh("POST", "/api/s/duel/start", {"id": dd}, S(F1))
        check(s == 200 and all(q["dars"] == 31 for q in st["questions"]), f"start: savollar 31-darsdan ({i + 1})")
    FR["did"] = did


FR: dict = {}


def play_tests() -> None:
    log("-- start / finish: validatsiya, natija, ball (teng natijada vaqt, durrang)")
    did = FR["did"]
    s, b = jh("POST", "/api/s/duel/finish", {"id": did, "answers": answers_for(did, 5)}, S(F2))
    check(s == 409 and b == {"xato": "Avval duelni boshlang"}, "finish: start dan oldin -> 409", (s, b))
    s, b = jh("POST", "/api/s/duel/start", {"id": did}, S(F3))
    check(s == 404, "start: begona o'quvchi -> 404", (s, b))
    for bad in ({}, {"id": "x"}, {"id": 5}):
        check(jh("POST", "/api/s/duel/start", bad, S(F2))[0] == 400, f"start {bad} -> 400")
    st, h, raw = http("POST", "/api/s/duel/start", {"id": did}, S(F2))
    b = json.loads(raw) if st == 200 else {}
    body = raw.decode("utf-8")
    ks = keys_of(did)
    check(st == 200 and b["id"] == did and b["sec"] == 15 and len(b["questions"]) == 5
          and all(set(q) == {"n", "dars", "q", "opts"} for q in b["questions"]) and '"ok"' not in body and "izoh" not in body,
          "start: 5 savol, 15 s, javob kaliti va izoh YO'Q", b)
    check(all(q["q"] == test_of(dn)[qn - 1]["q"] and q["opts"] == test_of(dn)[qn - 1]["opts"] and q["dars"] == dn
              for q, (dn, qn, _) in zip(b["questions"], ks)), "start: savol va variantlar test JSON dan o'zgarishsiz")
    check(0 < b["left_ms"] <= config.DUEL_OYNA * 1000 and b["deadline"] > b["started_at"], "start: started_at, deadline, left_ms", b)
    time.sleep(1.1)
    s, b2 = jh("POST", "/api/s/duel/start", {"id": did}, S(F2))
    check(s == 200 and b2["questions"] == b["questions"] and b2["started_at"] == b["started_at"],
          "start: qayta -> o'sha savollar, boshlanish vaqti o'zgarmaydi (idempotent)")
    bads = [("4 javob", answers_for(did, 5)[:4]), ("pick 4", [{"pick": 4, "ms": 1}] * 5), ("ms 60001", [{"pick": 1, "ms": 60001}] * 5),
            ("ms kasr", [{"pick": 1, "ms": 1.5}] * 5), ("javoblar yo'q", None), ("pick matn", [{"pick": "1", "ms": 5}] * 5)]
    for name, ans in bads:
        s, b3 = jh("POST", "/api/s/duel/finish", {"id": did, "answers": ans}, S(F2))
        check(s == 400 and "xato" in b3, f"finish: {name} -> 400", (s, b3))
    check(duel_row(did)["b_done"] is None, "noto'g'ri finish so'rovlari hech narsa yozmadi")
    # F2: 4 to'g'ri, 30 s; F1: 4 to'g'ri, 40 s -> F2 tezroq -> yutadi
    s, fn = jh("POST", "/api/s/duel/finish", {"id": did, "answers": answers_for(did, 4, 6000)}, S(F2))
    rv = fn.get("review") or []
    check(s == 200 and fn["duel"]["status"] == "raqib_navbati" and fn["duel"]["my"] == {"correct": 4, "ms": 30000, "late": False}
          and fn["duel"]["their"] is None and fn["xp_added"] == 0 and fn["late"] is False,
          "finish (birinchi): raqib_navbati, my 4/30000, their null, ball yo'q", fn.get("duel"))
    check(len(rv) == 5 and all({"q", "opts", "ok", "pick", "izoh"} <= set(x) for x in rv) and [x["togri"] for x in rv] == [True] * 4 + [False]
          and all(x["ok"] == k for x, (_, _, k) in zip(rv, ks)), "finish: review (to'g'ri javob + izoh tugatgandan keyin)", rv[:1])
    s, b = jh("POST", "/api/s/duel/finish", {"id": did, "answers": answers_for(did, 5)}, S(F2))
    check(s == 409 and b == {"xato": "Siz bu duelni allaqachon o'ynagansiz"}, "finish: qayta -> 409", (s, b))
    check(jh("POST", "/api/s/duel/start", {"id": did}, S(F2))[0] == 409, "start: tugatgandan keyin -> 409")
    x1, x2 = xp_today(F1["id"]), xp_today(F2["id"])
    s1, st1, s2, fn1 = play(F1, did, 4, 8000)
    check(s1 == 200 and s2 == 200 and fn1["duel"]["status"] == "tugadi" and fn1["duel"]["result"] == "yutqazdi"
          and fn1["duel"]["their"] == {"correct": 4, "ms": 30000} and fn1["duel"]["my"]["ms"] == 40000 and fn1["xp_added"] == 0,
          "teng to'g'ri (4:4) - F2 tezroq (30 s < 40 s) -> F1 yutqazdi", fn1.get("duel"))
    s, d2 = jh("GET", "/api/s/duels", None, S(F2))
    it = next((x for x in d2["items"] if x["id"] == did), {})
    check(it.get("result") == "yutdi" and it.get("xp") == 15 and it.get("their") == {"correct": 4, "ms": 40000},
          "F2: yutdi +15 (their ko'rinadi)", it)
    check(xp_today(F2["id"]) == x2 + 15 and xp_today(F1["id"]) == x1, "ball days jadvalida (bugungi): g'olib +15, mag'lub 0",
          (xp_today(F2["id"]) - x2, xp_today(F1["id"]) - x1))
    ev = events_of("duel_done", did)
    check(sorted((e["user_id"], e["xp"]) for e in ev) == [(F1["id"], 0), (F2["id"], 15)] and all(e["info"] == "4:4" for e in ev),
          "events 'duel_done' (ref = duel id) ikkalasiga", ev)
    m2 = me(F2)
    check(m2["stats"]["today_xp"] == xp_today(F2["id"]) and m2["stats"]["streak"] >= 1, "me.stats: duel balli kunlik maqsad/seriyada")
    rt = jh("GET", "/api/s/rating?davr=hafta", None, S(F2))[1]
    check(rt["me"]["xp"] >= 15, "reyting: duel balli hisobga olinadi", rt["me"])
    # durrang: ikkalasi 3 to'g'ri, bir xil vaqt
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F2))
    s, b = jh("POST", "/api/s/duel/accept", {"code": inv["code"]}, S(F4))
    d3 = b["duel"]["id"]
    x2, x4 = xp_today(F2["id"]), xp_today(F4["id"])
    play(F2, d3, 3, 7000)
    _, _, s, fn = play(F4, d3, 3, 7000)
    check(s == 200 and fn["duel"]["result"] == "durrang" and fn["xp_added"] == 5 and xp_today(F2["id"]) == x2 + 5
          and xp_today(F4["id"]) == x4 + 5, "durrang (3:3, teng vaqt) -> ikkalasiga +5", fn.get("duel"))
    s, b = jh("GET", f"/api/s/duel?id={d3}", None, S(F2))
    check(b["duel"]["result"] == "durrang" and b["duel"]["xp"] == 5, "durrang: birinchi o'yinchi ham +5 ko'radi")
    # ko'proq to'g'ri yutadi (vaqtdan qat'i nazar); ms > 15000 va ms yo'q -> xato
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F4))
    s, b = jh("POST", "/api/s/duel/accept", {"code": inv["code"]}, S(F2))
    d4 = b["duel"]["id"]
    jh("POST", "/api/s/duel/start", {"id": d4}, S(F4))
    ans = answers_for(d4, 5, [1000, 15001, 1000, 1000, 1000], missing_ms={2})
    s, fn = jh("POST", "/api/s/duel/finish", {"id": d4, "answers": ans}, S(F4))
    check(s == 200 and fn["duel"]["my"]["correct"] == 3 and fn["duel"]["my"]["ms"] == 1000 * 3 + 15000 + 15000
          and [x["togri"] for x in fn["review"]] == [True, False, False, True, True],
          "ms > 15000 va ms yo'q -> xato (vaqti 15000 hisoblanadi)", fn.get("duel"))
    _, _, s, fn = play(F2, d4, 4, 14000)
    check(s == 200 and fn["duel"]["result"] == "yutdi" and fn["xp_added"] == 15, "ko'proq to'g'ri (4 > 3) yutadi, sekinroq bo'lsa ham",
          fn.get("duel"))
    # kech yuborish: start dan 105 s dan keyin -> 0 to'g'ri
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(F4))
    s, b = jh("POST", "/api/s/duel/accept", {"code": inv["code"]}, S(F2))
    d5 = b["duel"]["id"]
    jh("POST", "/api/s/duel/start", {"id": d5}, S(F4))
    with con() as c:
        c.execute("UPDATE duels SET a_started=? WHERE id=?", (iso(now_tz() - timedelta(seconds=config.DUEL_OYNA + 5)), d5))
    s, fn = jh("POST", "/api/s/duel/finish", {"id": d5, "answers": answers_for(d5, 5, 1000)}, S(F4))
    check(s == 200 and fn["late"] is True and fn["duel"]["my"] == {"correct": 0, "ms": 75000, "late": True}
          and not any(x["togri"] for x in fn["review"]), "kech yuborish (start + 110 s) -> 0 to'g'ri, late=true", fn.get("duel"))
    _, _, s, fn = play(F2, d5, 1, 9000)
    check(s == 200 and fn["duel"]["result"] == "yutdi", "kechikkan raqibga qarshi 1 to'g'ri ham yutadi", fn.get("duel"))
    FR["d3"] = d3


R1, R2, R3, R4, P1, P2, B1, B2, N1 = (U(811001, "Rustam"), U(811002, "Rano"), U(811003, "Ravshan"), U(811004, "Rayhon"),
                                      U(811011, "Pulat"), U(811012, "Parizod"), U(811021, "Bahrom"), U(811022, "Barno"),
                                      U(811031, "Nodir"))


def random_tests() -> None:
    log("-- tasodifiy raqib: tanlov qoidalari")
    P3 = U(811013, "Pokiza")
    for u in (R1, R2, R3, R4, P1, P2, P3, B1, B2, N1):
        me(u)
    for u in (R1, R2, R3, R4):
        give(u["id"], [33])
    give(R1["id"], [22])  # R1 da yana bir dars - savollar baribir faqat umumiy (33) dan
    rivals = []
    for i in range(3):
        s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(R1))
        dd = b["duel"] if s == 200 else {}
        rivals.append(dd.get("rival", {}).get("id"))
        qs = json.loads(duel_row(dd.get("id", "")).get("questions") or "[]")
        check(s == 200 and dd["mode"] == "random" and dd["me_role"] == "a" and dd["status"] == "sizning_navbat"
              and dd["rival"]["id"] in (R2["id"], R3["id"], R4["id"]) and qs and all(x["dars"] == 33 for x in qs),
              f"random ({i + 1}): raqib R2-R4 dan, savollar faqat umumiy 33-darsdan", (s, dd, qs))
    check(len(set(rivals)) == 3, "random: tugallanmagan dueli bor raqib qayta tanlanmaydi (3 xil raqib)", rivals)
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(R1))
    check(s == 429 and "tugallanmagan" in b["xato"], "random: 3 ta tugallanmagan chiquvchi duel -> 429", (s, b))
    s, d = jh("GET", "/api/s/duels", None, S(R2))
    check(s == 200 and me(R2)["duel_pending"] == sum(1 for x in d["items"] if x["status"] == "sizning_navbat") >= 1,
          "raqib: duel_pending belgisi", d.get("items"))
    # bir juftlik 24 soatda bir marta (tugagan bo'lsa ham); oxirgi 7 kunda kirmagan tanlanmaydi
    for u in (P1, P2, P3):
        give(u["id"], [34])
    with con() as c:
        c.execute("UPDATE users SET last_seen=? WHERE id=?", (iso(now_tz() - timedelta(days=8)), P3["id"]))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(P1))
    dp = b["duel"]["id"] if s == 200 else ""
    check(s == 200 and b["duel"]["rival"]["id"] == P2["id"], "random: yagona mos raqib P2 (8 kun oldin kirgan P3 emas)", (s, b))
    play(P1, dp, 3)
    play(P2, dp, 2)
    check(duel_row(dp).get("status") == "tugadi", "P1-P2 dueli tugadi")
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(P1))
    check(s == 409 and b == {"xato": "Hozircha mos raqib topilmadi. Do'stingizni chaqirib ko'ring."},
          "random: o'sha raqib 24 soat ichida qayta tanlanmaydi, faol emas tanlanmaydi -> 409", (s, b))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(P2))
    check(s == 409, "random: teskari yo'nalishda ham (P2 -> P1) 24 soat -> 409", (s, b))
    with con() as c:
        c.execute("UPDATE users SET last_seen=? WHERE id=?", (iso(now_tz()), P3["id"]))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(P1))
    check(s == 200 and b["duel"]["rival"]["id"] == P3["id"], "random: P3 qayta faol bo'lgach -> P3", (s, b))
    with con() as c:
        c.execute("UPDATE duels SET created_at=? WHERE id=?", (iso(now_tz() - timedelta(hours=25)), dp))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(P2))
    check(s == 200 and b["duel"]["rival"]["id"] in (P1["id"], P3["id"]), "random: 24 soatdan keyin P1 yana mumkin", (s, b))
    # bloklangan / faol bo'lmagan / o'zi tanlanmaydi
    give(B1["id"], [35])
    give(B2["id"], [35])
    with con() as c:
        c.execute("UPDATE users SET blocked=1 WHERE id=?", (B2["id"],))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(B1))
    check(s == 409, "random: botni bloklagan raqib tanlanmaydi (o'zi ham) -> 409", (s, b))
    with con() as c:
        c.execute("UPDATE users SET blocked=0 WHERE id=?", (B2["id"],))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(B1))
    check(s == 200 and b["duel"]["rival"]["id"] == B2["id"], "random: blok olingach -> tanlanadi", (s, b))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(N1))
    check(s == 409 and b["xato"] == dbm.XATO_DUEL_SHART, "random: o'zi hech dars tugatmagan -> 409 (sabab)", (s, b))
    # adolat: eng kam band 5 nomzod orasidan tasodifiy (H1, H2 da 5 tadan o'ynalmagan duel bor - tanlanmaydi)
    H = [U(811100 + i, f"Hilola{i}") for i in range(1, 8)]
    K = [U(811200 + i, f"Kamron{i}") for i in range(1, 5)]
    for u in H + K:
        me(u)
        give(u["id"], [23])
    with con() as c:
        for i, h in enumerate(H[:2]):
            for j in range(5):
                c.execute("""INSERT INTO duels(id, a_id, b_id, mode, lessons, questions, created_at, expires_at, status)
                             VALUES (?,?,?,?,?,?,?,?, 'faol')""",
                          (f"band{i}{j}xxxx", 811999, h["id"], "friend", "[23]", json.dumps([{"dars": 23, "q": k} for k in range(1, 6)]),
                           iso(now_tz()), iso(now_tz() + timedelta(hours=20))))
    chosen = []
    for k in K:
        for _ in range(3):
            s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(k))
            if s == 200:
                chosen.append(b["duel"]["rival"]["id"])
    busy = {H[0]["id"], H[1]["id"]}
    check(len(chosen) == 12 and not (set(chosen) & busy) and len(set(chosen)) >= 5,
          f"random: band o'quvchilar tanlanmaydi, raqiblar taqsimlanadi ({len(set(chosen))} xil)", chosen)


def limit_tests() -> None:
    log("-- limitlar: 3 ta tugallanmagan, kuniga 10 ta")
    L1, L2 = U(812001, "Lola"), U(812002, "Laziz")
    for u in (L1, L2):
        me(u)
        give(u["id"], [29])
    codes = []
    for i in range(3):
        s, b = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(L1))
        codes.append(b.get("code"))
        check(s == 200, f"havola {i + 1}/3 -> 200", (s, b))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(L1))
    check(s == 429 and "tugallanmagan" in b["xato"], "4-havola (3 ta ochiq) -> 429", (s, b))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(L1))
    check(s == 429, "ochiq havolalar ham hisoblanadi: random -> 429", (s, b))
    with con() as c:
        c.execute("UPDATE duel_invites SET expires_at=? WHERE code=?", (iso(now_tz() - timedelta(seconds=1)), codes[0]))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(L1))
    check(s == 200, "eskirgan havola ochiq hisoblanmaydi -> yana mumkin", (s, b))
    t = iso(now_tz())
    with con() as c:
        c.executemany("INSERT INTO duel_invites(code, from_id, created_at, expires_at, used_by) VALUES (?,?,?,?,?)",
                      [(f"lim{i:07d}", L2["id"], t, t, 1) for i in range(10)])
    s, b = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(L2))
    check(s == 429 and "kunlik" in b["xato"], "kuniga 10 ta duel -> 11-si 429 (kunlik chegara)", (s, b))
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(L2))
    check(s == 429 and "kunlik" in b["xato"], "kunlik chegara random ga ham", (s, b))
    s, d = jh("GET", "/api/s/duels", None, S(L2))
    check(d["limits"] == {"today": 10, "daily": 10, "open": 0, "max_open": 3}, "duels.limits", d.get("limits"))
    with con() as c:
        c.execute("UPDATE duel_invites SET created_at=? WHERE from_id=?", (iso(now_tz() - timedelta(days=1)), L2["id"]))
    check(jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(L2))[0] == 200, "kechagi duellar bugungi chegaraga kirmaydi")


def expiry_tests() -> None:
    log("-- muddat: 24 soat (lazy) + soatlik vazifa, 105 s oyna")
    E1, E2 = U(813001, "Elyor"), U(813002, "Elmira")
    for u in (E1, E2):
        me(u)
        give(u["id"], [28])
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(E1))
    s, b = jh("POST", "/api/s/duel/accept", {"code": inv["code"]}, S(E2))
    d1 = b["duel"]["id"]
    play(E1, d1, 5)
    past = now_tz() - timedelta(hours=25)
    with con() as c:
        c.execute("UPDATE duels SET created_at=?, expires_at=? WHERE id=?", (iso(past), iso(past + timedelta(hours=24)), d1))
    s, d = jh("GET", f"/api/s/duel?id={d1}", None, S(E2))
    check(s == 200 and d["duel"]["status"] == "muddati_otdi" and duel_row(d1)["status"] == "faol",
          "24 soat o'tdi: API 'muddati_otdi' (bazada hali 'faol' - lazy)", d.get("duel"))
    check(jh("GET", f"/api/s/duel?id={d1}", None, S(E1))[1]["duel"]["status"] == "muddati_otdi", "birinchi o'yinchi uchun ham muddati_otdi")
    s, b = jh("POST", "/api/s/duel/start", {"id": d1}, S(E2))
    check(s == 410 and b == {"xato": "Duel muddati o'tgan"}, "muddati o'tgan duelni boshlash -> 410", (s, b))
    check(me(E2)["duel_pending"] == 0, "muddati o'tgan duel duel_pending ga kirmaydi")
    st = dbm.Store(DB)
    n = st.duels_expire(now_tz())
    check(n >= 1 and duel_row(d1)["status"] == "muddati_otdi" and duel_row(d1)["finished_at"] == duel_row(d1)["expires_at"],
          "soatlik vazifa (duels_expire): 'muddati_otdi' yozildi", n)
    check(not events_of("duel_done", d1), "muddati o'tgan duel: ball yo'q")
    # oyna: E1 boshladi, keyin muddat o'tdi -> E1 105 s ichida tugata oladi, E2 boshlay olmaydi
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(E1))
    s, b = jh("POST", "/api/s/duel/accept", {"code": inv["code"]}, S(E2))
    d2 = b["duel"]["id"]
    jh("POST", "/api/s/duel/start", {"id": d2}, S(E1))
    with con() as c:
        c.execute("UPDATE duels SET expires_at=? WHERE id=?", (iso(now_tz() - timedelta(seconds=5)), d2))
    v1 = jh("GET", f"/api/s/duel?id={d2}", None, S(E1))[1]["duel"]["status"]
    v2 = jh("GET", f"/api/s/duel?id={d2}", None, S(E2))[1]["duel"]["status"]
    check((v1, v2) == ("sizning_navbat", "muddati_otdi"), "oyna: o'ynayotgan - navbat, ikkinchisi - muddati o'tdi", (v1, v2))
    st.duels_expire(now_tz())
    check(duel_row(d2)["status"] == "faol", "soatlik vazifa o'ynayotgan o'yinchini kutadi (105 s oyna)")
    check(jh("POST", "/api/s/duel/start", {"id": d2}, S(E2))[0] == 410, "oyna: ikkinchi o'yinchi boshlay olmaydi -> 410")
    s, fn = jh("POST", "/api/s/duel/finish", {"id": d2, "answers": answers_for(d2, 5)}, S(E1))
    check(s == 200 and fn["duel"]["my"]["correct"] == 5 and fn["duel"]["status"] == "muddati_otdi" and fn["xp_added"] == 0,
          "oyna: o'ynayotgan tugatdi (5 to'g'ri), raqib o'ynamagan -> muddati o'tdi, ball yo'q", fn.get("duel"))


def concurrency_tests() -> None:
    log("-- bir vaqtda tugatish (HTTP): ball aniq bir marta")
    G1, G2 = U(814001, "G'ayrat"), U(814002, "Gulbahor")
    for u in (G1, G2):
        me(u)
        give(u["id"], [27])
    for rnd in range(3):
        s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(G1))
        s, b = jh("POST", "/api/s/duel/accept", {"code": inv["code"]}, S(G2))
        dd = b["duel"]["id"]
        jh("POST", "/api/s/duel/start", {"id": dd}, S(G1))
        jh("POST", "/api/s/duel/start", {"id": dd}, S(G2))
        a1, a2 = answers_for(dd, 5, 3000), answers_for(dd, 2, 3000)
        bar = threading.Barrier(4)

        def go(u, ans):
            bar.wait()
            return jh("POST", "/api/s/duel/finish", {"id": dd, "answers": ans}, S(u))
        with ThreadPoolExecutor(4) as pool:
            res = list(pool.map(lambda x: go(*x), [(G1, a1), (G2, a2), (G1, a1), (G2, a2)]))
        codes = sorted(r[0] for r in res)
        ev = events_of("duel_done", dd)
        xs = sorted((e["user_id"], e["xp"]) for e in ev)
        check(codes == [200, 200, 409, 409] and xs == [(G1["id"], 15), (G2["id"], 0)] and duel_row(dd)["status"] == "tugadi"
              and sum(r[1].get("xp_added", 0) for r in res if r[0] == 200) in (0, 15),
              f"4 ta bir vaqtdagi finish ({rnd + 1}): 2 x 200, 2 x 409, ball bir marta", (codes, xs))


RF = U(815001, "Rahbar", "Taklifchi")


def referral_tests() -> None:
    log("-- do'st taklifi: bog'lash (faqat yangi), o'zini taklif, 1-dars bonusi (bir marta, ikkalasiga)")
    import student_bot as sb
    me(RF)
    s, t = jh("GET", "/api/s/taklif", None, S(RF))
    code = t["link"].split("start=ref_", 1)[1] if s == 200 else ""
    check(s == 200 and re.fullmatch(r"[a-z0-9]{8}", code) and t["friends"] == [] and t["earned"] == 0 and t["invited"] == 0,
          "taklif: shaxsiy havola (ref_ + 8 belgi), hali do'st yo'q", t)
    check(jh("GET", "/api/s/taklif", None, S(RF))[1]["link"] == t["link"], "taklif: havola o'zgarmaydi")
    st = dbm.Store(DB)
    svc = types.SimpleNamespace(store=st, base_url=BASE)
    now = now_tz()
    yangi1, yangi2, yangi3, eski = U(815011, "Yangi", "Bir"), U(815012, "Yangi", "Ikki"), U(815013, "Yangi", "Uch"), U(815020, "Eski")
    me(eski)

    def bot_start(u, payload):
        is_new = st.upsert_user(u, now, "bot")
        return is_new, sb.handle_start_payload(svc, u["id"], payload, is_new, now)
    n1, r1 = bot_start(yangi1, f"ref_{code}")
    n2, r2 = bot_start(eski, f"ref_{code}")
    _, r3 = bot_start(RF, f"ref_{code}")
    with con() as c:
        refs = {r["invitee_id"]: r["inviter_id"] for r in c.execute("SELECT * FROM referrals WHERE inviter_id=?", (RF["id"],))}
    check(n1 and r1 is None and refs == {yangi1["id"]: RF["id"]}, "bot /start ref_: yangi o'quvchi bog'landi (oddiy salomlashish)", refs)
    check(not n2 and eski["id"] not in refs, "bot /start ref_: mavjud o'quvchi bog'lanmaydi")
    check(RF["id"] not in refs and st.ref_link(RF["id"], code, now) is None, "o'zini taklif - e'tiborsiz")
    check(st.ref_link(999001, "zzzzzzzz", now) is None and st.ref_link(999002, "BAD", now) is None, "noma'lum / buzuq kod - e'tiborsiz")
    check(st.ref_link(yangi1["id"], code, now) is None, "ikkinchi marta bog'lanmaydi")
    bot_start(yangi2, f"ref_{code}")
    feat("taklif", False)
    bot_start(yangi3, f"ref_{code}")
    feat("taklif", True)
    with con() as c:
        linked = {r[0] for r in c.execute("SELECT invitee_id FROM referrals WHERE inviter_id=?", (RF["id"],))}
    check(linked == {yangi1["id"], yangi2["id"]}, "taklif o'chiq paytida /start ref_ - bog'lanmaydi", linked)
    # 1-darsni tugatish -> ikkalasiga +50 (bir marta)
    n1s = json.loads((config.CONTENT_DIR / "kurs.json").read_text(encoding="utf-8"))["darslar"][0]["slaydlar"]
    need = math.ceil(0.8 * n1s)

    def slides(u):
        me(u)
        with con() as c:
            c.executemany("INSERT OR IGNORE INTO slides(user_id, dars, idx, seen_at) VALUES (?,?,?,?)",
                          [(u["id"], 1, i, iso(now_tz())) for i in range(1, need + 1)])
    slides(yangi1)
    xr, xy = xp_today(RF["id"]), xp_today(yangi1["id"])
    s, b = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(yangi1))
    check(s == 200 and b["xp_added"] == 20 and b.get("taklif_bonus") == 50, "lesson_done 1: xp_added 20 + taklif_bonus 50", b)
    check(xp_today(RF["id"]) == xr + 50 and xp_today(yangi1["id"]) == xy + 20 + 50 and b["stats"]["today_xp"] == xy + 70,
          "bonus ikkalasiga days jadvalida (+50)", (xp_today(RF["id"]) - xr, xp_today(yangi1["id"]) - xy))
    s, b = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(yangi1))
    check(s == 200 and "taklif_bonus" not in b and xp_today(RF["id"]) == xr + 50, "qayta lesson_done -> bonus yo'q")
    ev = [e for e in events_of("taklif_bonus") if e["user_id"] in (RF["id"], yangi1["id"])]
    check(sorted((e["user_id"], e["ref"], e["xp"]) for e in ev) == sorted([(RF["id"], str(yangi1["id"]), 50),
                                                                         (yangi1["id"], str(RF["id"]), 50)]),
          "events 'taklif_bonus' ikkalasiga, bir marta", ev)
    # bir vaqtda ikki lesson_done -> bonus bir marta
    slides(yangi2)
    with ThreadPoolExecutor(3) as pool:
        res = list(pool.map(lambda _: jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(yangi2)), range(3)))
    nb = sum(1 for s_, b_ in res if s_ == 200 and b_.get("taklif_bonus"))
    n_ev = len([e for e in events_of("taklif_bonus") if e["user_id"] == yangi2["id"]])
    check(all(s_ == 200 for s_, _ in res) and nb == 1 and n_ev == 1, "bir vaqtdagi 3 ta lesson_done -> bonus aniq bir marta", (nb, n_ev))
    s, t = jh("GET", "/api/s/taklif", None, S(RF))
    check(t["earned"] == 100 and t["invited"] == 2 and t["rewarded"] == 2 and all(f["done1"] and f["rewarded"] for f in t["friends"]),
          "taklif qilgan: earned 100, 2 do'st (1-dars tugagan, bonusli)", t)
    # taklif o'chiq bo'lsa bonus berilmaydi
    yangi4 = U(815014, "Yangi", "Tort")
    bot_start(yangi4, f"ref_{code}")
    slides(yangi4)
    feat("taklif", False)
    s, b = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(yangi4))
    feat("taklif", True)
    with con() as c:
        rw = c.execute("SELECT rewarded_at FROM referrals WHERE invitee_id=?", (yangi4["id"],)).fetchone()
    check(s == 200 and "taklif_bonus" not in b and rw and rw[0] is None, "taklif o'chiq: 1-dars bonusi berilmaydi", (b, rw and tuple(rw)))
    # SPEC 11.6: bonus "kutib turadi" - funksiya qayta yoqilgach 1-dars lesson_done qayta yuborilsa, bir marta beriladi
    s, b = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(yangi4))
    s2, b2 = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(yangi4))
    check(s == 200 and b.get("taklif_bonus") == 50 and b["xp_added"] == 0 and "taklif_bonus" not in b2,
          "taklif yoqilgach: keyingi lesson_done 1 -> bonus bir marta (dars balli qayta yo'q)", (b, b2))
    # boshqa dars bonus bermaydi
    yangi5 = U(815015, "Yangi", "Besh")
    bot_start(yangi5, f"ref_{code}")
    give(yangi5["id"], [1])
    with con() as c:
        c.executemany("INSERT OR IGNORE INTO slides(user_id, dars, idx, seen_at) VALUES (?,?,?,?)",
                      [(yangi5["id"], 2, i, iso(now_tz())) for i in range(1, 60)])
    s, b = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 2}, S(yangi5))
    check(s == 200 and "taklif_bonus" not in b, "2-dars tugatilganda bonus yo'q (faqat 1-dars)", (s, b))


def switch_tests() -> None:
    log("-- funksiya o'chirgichlari: duel, taklif")
    feat("duel", False)
    reqs = [("GET", "/api/s/duels", None), ("GET", "/api/s/duel?id=seedduel05", None), ("POST", "/api/s/duel/new", {"mode": "random"}),
            ("POST", "/api/s/duel/new", {"mode": "friend"}), ("POST", "/api/s/duel/accept", {"code": "seedinv001"}),
            ("POST", "/api/s/duel/start", {"id": "seedduel05"}),
            ("POST", "/api/s/duel/finish", {"id": "seedduel05", "answers": [{"pick": 0, "ms": 1}] * 5})]
    for m, p, body in reqs:
        s, b = jh(m, p, body, S("aziza"))
        check(s == 403 and b == XATO_FUNKSIYA, f"duel o'chiq: {m} {p.split('?')[0]} -> 403", (s, b))
    m_ = me("aziza")
    check(m_["features"]["duel"] is False and m_["duel_pending"] == 0, "duel o'chiq: me.features.duel=false, duel_pending=0", m_.get("duel_pending"))
    check(duel_row("seedduel05")["b_started"] is None, "duel o'chiq: hech narsa yozilmadi")
    feat("duel", True)
    check(jh("GET", "/api/s/duels", None, S("aziza"))[0] == 200 and me("aziza")["duel_pending"] == 1, "duel yoqildi -> 200")
    feat("taklif", False)
    s, b = jh("GET", "/api/s/taklif", None, S("aziza"))
    check(s == 403 and b == XATO_FUNKSIYA, "taklif o'chiq: /api/s/taklif -> 403", (s, b))
    feat("taklif", True)
    check(jh("GET", "/api/s/taklif", None, S("aziza"))[0] == 200, "taklif yoqildi -> 200")
    check(jh("GET", "/api/x/features", None, X("ceo"))[1]["features"] == {k: True for k in config.FUNKSIYA_KALITLARI},
          "oxirida barcha funksiyalar yoqilgan")


def staff_tests() -> None:
    log("-- xodim API: /api/x/duels, /api/x/referrals, o'quvchi kartasi, bo'limlar")
    for path in ("/api/x/duels", "/api/x/duels?days=7", "/api/x/referrals"):
        for role in ROLES:
            s, b = jh("GET", path, None, X(role))
            if role in ("ceo", "admin"):
                check(s == 200, f"{path} ({role}) -> 200", s)
            else:
                check(s == 403 and b == XATO_BOLIM, f"{path} ({role}) -> 403 'Bu bo'lim sizga ochiq emas'", (s, b))
    check(jh("GET", "/api/x/duels")[0] == 401 and jh("GET", "/api/x/referrals", None, S("aziza"))[0] == 401, "x/duels: autentifikatsiyasiz -> 401")
    for bad in ("0", "367", "abc"):
        check(jh("GET", f"/api/x/duels?days={bad}", None, X("ceo"))[0] == 400, f"x/duels?days={bad} -> 400")
    s, d = jh("GET", "/api/x/duels?days=30", None, X("admin"))
    since = dbm.iso(dbm.day_start(now_tz().date() - timedelta(days=29)))
    with con() as c:
        tot, fin, drw = c.execute("""SELECT COUNT(*), SUM(status='tugadi'), SUM(status='tugadi' AND winner_id IS NULL)
                                     FROM duels WHERE created_at >= ?""", (since,)).fetchone()
        players = c.execute("SELECT COUNT(*) FROM (SELECT a_id FROM duels WHERE created_at >= ? UNION SELECT b_id FROM duels WHERE created_at >= ?)",
                            (since, since)).fetchone()[0]
        recent_db = [r[0] for r in c.execute("SELECT id FROM duels ORDER BY created_at DESC, id LIMIT 20")]
    keys = {"days", "total", "finished", "expired", "draws", "players", "daily", "top", "recent"}
    check(s == 200 and keys <= set(d) and d["total"] == tot and d["finished"] == fin and d["draws"] == drw and d["players"] == players
          and d["expired"] + d["finished"] + d["active"] == d["total"] and d["expired"] >= 2,
          "x/duels: sonlar bazaga mos (total, finished, draws, players, expired)", {k: d.get(k) for k in keys - {"daily", "top", "recent"}})
    check(len(d["daily"]) == 30 and d["daily"][-1]["day"] == now_tz().date().isoformat()
          and sum(x["created"] for x in d["daily"]) == tot and all(set(x) == {"day", "created", "finished"} for x in d["daily"]),
          "x/duels.daily: 30 kun, yig'indi = total")
    check(d["top"] and all(set(x) >= {"id", "name", "played", "won"} for x in d["top"])
          and [x["won"] for x in d["top"]] == sorted([x["won"] for x in d["top"]], reverse=True), "x/duels.top: g'alabalar bo'yicha", d["top"][:3])
    rc = d["recent"]
    check([x["id"] for x in rc] == recent_db and all(set(x) >= {"id", "at", "a", "b", "result", "status"} for x in rc)
          and all(set(x["a"]) >= {"id", "name", "correct"} for x in rc), "x/duels.recent: oxirgi 20, maydonlar", rc[:1])
    s3 = next((x for x in rc if x["id"] == "seedduel03"), None)
    s9 = next((x for x in rc if x["id"] == "seedduel09"), None)
    if s3:
        check(s3["result"] == "b" and s3["status"] == "tugadi" and s3["b"]["name"] == "Aziza Karimova", "recent: seedduel03 -> b (Aziza) yutdi", s3)
    if s9:
        check(s9["status"] == "muddati_otdi" and s9["result"] is None, "recent: seedduel09 -> muddati_otdi", s9)
    s, rf = jh("GET", "/api/x/referrals", None, X("ceo"))
    with con() as c:
        tr, rw = c.execute("SELECT COUNT(*), COUNT(rewarded_at) FROM referrals").fetchone()
    check(s == 200 and rf["total"] == tr and rf["rewarded"] == rw and set(rf) >= {"total", "rewarded", "top", "recent"}
          and all(set(x) >= {"id", "name", "invited", "rewarded"} for x in rf["top"])
          and all(set(x) >= {"at", "inviter", "invitee", "rewarded"} for x in rf["recent"])
          and [x["at"] for x in rf["recent"]] == sorted([x["at"] for x in rf["recent"]], reverse=True),
          "x/referrals: sonlar bazaga mos, top, recent (yangisi birinchi)", {k: rf.get(k) for k in ("total", "rewarded")})
    top1 = rf["top"][0] if rf["top"] else {}
    check(top1.get("invited", 0) >= 2, "x/referrals.top: eng ko'p taklif qilgan birinchi", top1)
    # o'quvchi kartasi
    s, sd = jh("GET", "/api/x/student?id=800002", None, X("ustoz"))
    check(s == 200 and sd["duels"]["played"] == 3 and sd["duels"]["won"] == 1 and sd["duels"]["lost"] == 1 and sd["duels"]["draw"] == 1
          and sd["invited"] == 2 and sd["invited_by"] is None, "karta (Jahongir): duels 3/1/1/1, taklif qilgan 2", (sd.get("duels"), sd.get("invited")))
    s, sd = jh("GET", "/api/x/student?id=800014", None, X("admin"))
    check(s == 200 and sd["invited_by"] and sd["invited_by"]["id"] == 800001 and sd["invited_by"]["name"] == "Aziza Karimova"
          and sd["invited"] == 0, "karta (Kamola): invited_by = Aziza", sd.get("invited_by"))
    s, sd = jh("GET", "/api/x/student?id=800001", None, X("ceo"))
    check(s == 200 and sd["invited"] == 2 and sd["duels"]["played"] == 2 and sd["duels"]["active"] == 2 and sd["duels"]["expired"] == 1,
          "karta (Aziza): 2 taklif, 2 tugagan, 2 faol, 1 muddati o'tgan duel", sd.get("duels"))
    # bo'limlar
    for role, want in (("ceo", True), ("admin", True), ("ustoz", False)):
        s, m = jh("GET", "/api/x/me", None, X(role))
        has = "duellar" in m["sections"] and "takliflar" in m["sections"]
        check(s == 200 and has == want and (not want or (m["access"]["duellar"] == "read" and m["access"]["takliflar"] == "read")),
              f"x/me ({role}): duellar/takliflar {'bor (read)' if want else 'yo`q'}", m.get("sections"))
    s, f = jh("GET", "/api/x/features", None, X("ceo"))
    meta = {x["key"]: x for x in f["meta"]}
    check("hali tayyor emas" not in meta["duel"]["tavsif"] and "hali tayyor emas" not in meta["taklif"]["tavsif"]
          and meta["duel"]["bosqich"] == 2, "x/features: duel/taklif tavsifi yangilangan", (meta["duel"], meta["taklif"]))


# ---------------------------------------------------------------- soxta Telegram (bot xabarlari)
def tg_tests() -> None:
    from fake_telegram import FakeTelegram

    class SlowFake(FakeTelegram):
        slow_s = 0.0

        async def handle(self, request):
            if self.slow_s and request.match_info["method"].lower() == "sendmessage":
                await asyncio.sleep(self.slow_s)
            return await super().handle(request)

    global BASE
    base_saved = BASE
    BASE = f"http://127.0.0.1:{TG_PORT}"
    _DB_PATH[0] = TG_DB
    holat, pid = OUT / "tg_holat.json", OUT / "tg_main.pid"
    wipe(TG_DB)
    for p in (holat, pid):
        try:
            p.unlink()
        except OSError:
            pass
    fake = SlowFake()
    url = fake.start()
    log(f"\n== SOXTA TELEGRAM (port {TG_PORT}, {TG_DB.name}): {url} ==")
    proc = None
    try:
        proc = start_server(["--fake-tg", url, "--port", str(TG_PORT), "--db", str(TG_DB.relative_to(ROOT)), "--holat", str(holat),
                             "--pid", str(pid), "--jobs-now", "30", "--log", str(OUT / "tg_server.log")], TG_PORT, "tg_stdout.txt")
        t_start = time.time()
        h = {}
        for _ in range(120):
            try:
                h = json.loads(holat.read_text(encoding="utf-8"))
                if h.get("holat") == "ishlayapti":
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.25)
        check(h.get("holat") == "ishlayapti" and h.get("talaba_bot") == "noon_talaba_sinov_bot", "server --fake-tg ishga tushdi", h)
        _tg_body(fake, t_start)
    except Exception:
        check(False, "soxta Telegram sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        if proc is not None:
            check(stop_server(proc, pid.with_suffix(".stop")), "fake-tg server yumshoq to'xtadi")
        fake.stop()
        BASE = base_saved
        _DB_PATH[0] = DB
    logtxt = (OUT / "tg_server.log").read_text(encoding="utf-8", errors="ignore") if (OUT / "tg_server.log").exists() else ""
    check(logtxt and SINOV_TALABA_TOKEN not in logtxt and "SINOVtalaba" not in logtxt and not config.TOKEN_ANY_RE.search(logtxt),
          "fake-tg logida token yo'q")


def _say(fake, who: dict, text: str, pred=None, timeout: float = 15):
    m = fake.mark()
    fake.push_message("talaba", who, text)
    return fake.wait_for(lambda c: c["bot"] == "talaba" and c["method"] == "sendMessage" and c.get("chat_id") == who["id"]
                         and (pred is None or pred(c)), timeout=timeout, start=m)


def _btn(c):
    try:
        return c["params"]["reply_markup"]["inline_keyboard"][0][0]
    except (KeyError, IndexError, TypeError):
        return None


def _wait_msg(fake, chat_id: int, needle: str, start: int, timeout: float = 15):
    return fake.wait_for(lambda c: c["bot"] == "talaba" and c["method"] == "sendMessage" and c.get("chat_id") == chat_id
                         and needle in (c["params"].get("text") or ""), timeout=timeout, start=start)


def _tg_body(fake, t_start: float) -> None:
    A, B, C, D, E = (U(700101, "Ali", "Valiyev"), U(700102, "Botir", "Sobirov"), U(700103, "Chori", "Toshev"),
                     U(700104, "Dono", "Aliyeva"), U(700105, "Erkin", "Olimov"))
    with con() as c:  # funksiyalarni almashtirish uchun CEO (yangi bazada xodim yo'q)
        c.execute("INSERT OR IGNORE INTO staff(id, first_name, last_name, username, role, added_at) VALUES (?,?,?,?,?,?)",
                  (900001, "Muhammad", "Amin", "muhammad_amin", "ceo", iso(now_tz())))
    # soatlik vazifa (--jobs-now 30) uchun muddati o'tgan duel
    for u in (A, B, C, D, E):
        c = _say(fake, u, "/start")
        check(c and c["params"]["text"].startswith(f"Salom, {u['first_name']}!"), f"/start ({u['first_name']})", c and c["params"]["text"])
        me(u)
    give(A["id"], [30, 31])
    give(B["id"], [31])
    give(C["id"], [30])
    give(D["id"], [32])
    give(E["id"], [32])
    past = now_tz() - timedelta(hours=30)
    with con() as c:
        c.execute("""INSERT INTO duels(id, a_id, b_id, mode, lessons, questions, created_at, expires_at, a_started, a_done,
                     a_answers, a_correct, a_ms, status) VALUES ('expiredd01', ?, ?, 'random', '[31]', ?, ?, ?, ?, ?, '[]', 3, 40000, 'faol')""",
                  (A["id"], B["id"], json.dumps([{"dars": 31, "q": i} for i in range(1, 6)]), iso(past), iso(past + timedelta(hours=24)),
                   iso(past + timedelta(minutes=1)), iso(past + timedelta(minutes=2))))
    # tasodifiy duel: raqibga xabar; HTTP javob xabarni kutmaydi
    fake.slow_s = 3.0
    mk = fake.mark()
    t0 = time.time()
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(A))
    took = time.time() - t0
    fake.slow_s = 0.0
    did = b["duel"]["id"] if s == 200 else ""
    rival = b["duel"]["rival"]["id"] if s == 200 else 0
    check(s == 200 and rival in (B["id"], C["id"]) and took < 2.0, f"random duel: 200, javob xabarni kutmadi ({took:.2f} s, xabar 3 s sekin)",
          (s, b, took))
    m = _wait_msg(fake, rival, "sizni duelga chaqirdi", mk)
    check(m and m["params"]["text"] == "Ali V. sizni duelga chaqirdi. 24 soat ichida javob bering."
          and _btn(m) == {"text": "Duelni ochish", "web_app": {"url": f"{BASE}/app/?duel={did}"}},
          "raqibga xabar: '{ism} sizni duelga chaqirdi...' + 'Duelni ochish' (?duel=)", m and m["params"])
    rv_user = B if rival == B["id"] else C
    mk = fake.mark()
    play(A, did, 5, 3000)
    s1, _, s2, fn = play(rv_user, did, 2, 9000)
    check(s2 == 200 and fn["duel"]["result"] == "yutqazdi", "raqib ikkinchi bo'lib tugatdi", fn.get("duel"))
    m = _wait_msg(fake, A["id"], "Duel natijasi", mk)
    check(m and m["params"]["text"].startswith("Duel natijasi: siz yutdingiz 5:2") and "+15 ball" in m["params"]["text"]
          and _btn(m) == {"text": "Natijani ko'rish", "web_app": {"url": f"{BASE}/app/?duel={did}"}},
          "birinchi o'yinchiga natija xabari (siz yutdingiz 5:2, +15 ball)", m and m["params"])
    check(not fake.wait_for(lambda c: c["method"] == "sendMessage" and c.get("chat_id") == rival and "Duel natijasi" in
                            (c["params"].get("text") or ""), timeout=1.5, start=mk), "ikkinchi o'yinchiga natija xabari yuborilmaydi (javobda bor)")
    # do'st havolasi: /start duel_<kod>
    s, inv = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(A))
    code = inv["code"]
    check(inv["link"] == f"https://t.me/noon_talaba_sinov_bot?start=duel_{code}", "do'st havolasi bot nomi bilan", inv)
    c = _say(fake, C, f"/start duel_{code}")
    check(c and c["params"]["text"].startswith("Duelga taklif\n\nAli V. sizni") and _btn(c) == {"text": "Duelni ochish",
          "web_app": {"url": f"{BASE}/app/?duel_kod={code}"}}, "/start duel_<kod>: 'Duelga taklif' + ?duel_kod=", c and c["params"])
    c = _say(fake, B, "/start duel_zzzzzzzzzz")
    check(c and c["params"]["text"].startswith("Bu duel taklifi eskirgan") and _btn(c)["web_app"]["url"] == f"{BASE}/app/",
          "/start duel_<noma'lum>: eskirgan matni", c and c["params"])
    c = _say(fake, A, f"/start duel_{code}")
    check(c and c["params"]["text"].startswith("Bu sizning duel havolangiz"), "/start duel_<o'z kodi>: tushuntirish", c and c["params"])
    mk = fake.mark()
    s, b = jh("POST", "/api/s/duel/accept", {"code": code}, S(C))
    did2 = b["duel"]["id"] if s == 200 else ""
    m = _wait_msg(fake, A["id"], "duelni qabul qildi", mk)
    check(s == 200 and m and m["params"]["text"] == "Chori T. duelni qabul qildi."
          and _btn(m)["web_app"]["url"] == f"{BASE}/app/?duel={did2}", "qabul -> taklif qilganga xabar", m and m["params"])
    jh("POST", "/api/s/duel/accept", {"code": code}, S(C))
    time.sleep(1.0)
    n_acc = len([x for x in fake.get_calls("talaba", "sendMessage") if x.get("chat_id") == A["id"] and "qabul qildi" in x["params"]["text"]])
    check(n_acc == 1, "takroriy accept (idempotent) qayta xabar yubormaydi", n_acc)
    c = _say(fake, B, f"/start duel_{code}")
    check(c and c["params"]["text"].startswith("Bu duel taklifi eskirgan"), "/start duel_<ishlatilgan kod> (boshqa odam): eskirgan")
    # duel o'chiq -> /start duel_ oddiy salomlashish
    s, inv2 = jh("POST", "/api/s/duel/new", {"mode": "friend"}, S(B))
    feat("duel", False, BASE)
    c = _say(fake, C, f"/start duel_{inv2['code']}")
    check(c and c["params"]["text"].startswith("Salom, Chori!") and _btn(c) == {"text": "Darslarni ochish", "web_app": {"url": f"{BASE}/app/"}},
          "duel o'chiq: /start duel_ -> oddiy salomlashish", c and c["params"])
    feat("duel", True, BASE)
    # taklif: /start ref_<kod>
    s, t = jh("GET", "/api/s/taklif", None, S(A))
    rcode = t["link"].split("start=ref_", 1)[1]
    N, N2, N3 = U(700110, "Nodira", "Yangi"), U(700111, "Nozim", "Yangi"), U(700112, "Nigora", "Yangi")
    c = _say(fake, N, f"/start ref_{rcode}")
    check(c and c["params"]["text"].startswith("Salom, Nodira!") and _btn(c)["web_app"]["url"] == f"{BASE}/app/",
          "/start ref_<kod> (yangi): oddiy salomlashish", c and c["params"])
    _say(fake, B, f"/start ref_{rcode}")
    _say(fake, A, f"/start ref_{rcode}")
    feat("taklif", False, BASE)
    _say(fake, N2, f"/start ref_{rcode}")
    feat("taklif", True, BASE)
    _say(fake, N3, "/start ref_zzzzzzzz")
    with con() as c_:
        refs = {r[0]: r[1] for r in c_.execute("SELECT invitee_id, inviter_id FROM referrals")}
    check(refs == {N["id"]: A["id"]}, "bot: faqat yangi o'quvchi bog'landi (mavjud, o'zi, o'chiq paytida, noma'lum kod - yo'q)", refs)
    # N 1-darsni tugatadi -> A ga xabar
    me(N)
    n1s = json.loads((config.CONTENT_DIR / "kurs.json").read_text(encoding="utf-8"))["darslar"][0]["slaydlar"]
    with con() as c_:
        c_.executemany("INSERT OR IGNORE INTO slides(user_id, dars, idx, seen_at) VALUES (?,?,?,?)",
                       [(N["id"], 1, i, iso(now_tz())) for i in range(1, math.ceil(0.8 * n1s) + 1)])
    mk = fake.mark()
    s, b = jh("POST", "/api/s/event", {"type": "lesson_done", "dars": 1}, S(N))
    m = _wait_msg(fake, A["id"], "1-darsni tugatdi", mk)
    check(s == 200 and b.get("taklif_bonus") == 50 and m and m["params"]["text"] == "Do'stingiz Nodira Y. 1-darsni tugatdi: sizga va unga +50 ball."
          and _btn(m) == {"text": "Ilovani ochish", "web_app": {"url": f"{BASE}/app/?tab=profil"}},
          "taklif bonusi: taklif qilganga xabar (+50)", (b, m and m["params"]))
    # bloklagan raqib: Forbidden -> blocked=1, javob 200
    fake.block(D["id"])
    mk = fake.mark()
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(E))
    check(s == 200 and b["duel"]["rival"]["id"] == D["id"], "random: yagona raqib D", (s, b))
    fake.wait_for(lambda c: c["method"] == "sendMessage" and c.get("chat_id") == D["id"], timeout=10, start=mk)
    blocked = None
    for _ in range(40):
        with con() as c_:
            blocked = c_.execute("SELECT blocked FROM users WHERE id=?", (D["id"],)).fetchone()[0]
        if blocked:
            break
        time.sleep(0.25)
    check(blocked == 1, "bloklagan foydalanuvchi: Forbidden e'tiborsiz, blocked=1 belgilandi", blocked)
    s, b = jh("POST", "/api/s/duel/new", {"mode": "random"}, S(E))
    check(s == 409, "random: bloklangan raqib endi tanlanmaydi -> 409", (s, b))
    # soatlik vazifa (--jobs-now 30)
    left = 30 - (time.time() - t_start)
    if left > -5:
        time.sleep(max(0.0, left) + 3)
    st_ = None
    for _ in range(40):
        st_ = duel_row("expiredd01").get("status")
        if st_ == "muddati_otdi":
            break
        time.sleep(0.25)
    check(st_ == "muddati_otdi", "soatlik vazifa (JobQueue, --jobs-now): muddati o'tgan duel belgilandi", st_)
    check(not [x for x in fake.get_calls("talaba", "sendMessage") if "expiredd01" in json.dumps(x["params"])],
          "muddat o'tganda xabar yuborilmaydi")
    # matnlar
    texts = []
    urls = []
    for x in fake.get_calls("talaba", "sendMessage"):
        texts.append(x["params"].get("text") or "")
        bt = _btn(x)
        if bt:
            texts.append(bt.get("text", ""))
            if "web_app" in bt:
                urls.append(bt["web_app"]["url"])
    check(texts and not [t for t in texts if EMOJI_RE.search(t)], f"bot matnlarida emoji yo'q ({len(texts)} ta)")
    check(not [t for t in texts if any(w in t.lower() for w in DINIY)], "bot matnlarida diniy so'z yo'q")
    check(urls and all(u == f"{BASE}/app/" or u.startswith(f"{BASE}/app/?") for u in urls), "web_app manzillari /app/ ...", sorted(set(urls))[:8])
    (OUT / "tg_xabarlar.json").write_text(json.dumps([{"chat_id": x.get("chat_id"), "params": x["params"]}
                                                      for x in fake.get_calls("talaba", "sendMessage")], ensure_ascii=False, indent=1),
                                          encoding="utf-8")


# ---------------------------------------------------------------- ishga tushirish
def main() -> int:
    global PORT, TG_PORT, BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--faqat", choices=["unit", "api", "tg"])
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--tg-port", type=int, default=TG_PORT)
    a = ap.parse_args()
    PORT, TG_PORT = a.port, a.tg_port
    BASE = f"http://127.0.0.1:{PORT}"
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.faqat in (None, "unit"):
        unit_tests()
    if a.faqat in (None, "api"):
        api_tests()
    if a.faqat in (None, "tg"):
        tg_tests()
    log(f"\nNATIJA: {R.ok} ta OK, {len(R.fails)} ta XATO ({time.time() - t0:.0f} s)")
    for f in R.fails:
        log("  - " + f)
    (OUT / "natija.txt").write_text("\n".join(R.lines), encoding="utf-8")
    return 0 if not R.fails else 1


if __name__ == "__main__":
    sys.exit(main())

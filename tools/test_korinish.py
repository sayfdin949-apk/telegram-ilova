"""05.10 NUQTA ko'rinishi (SPEC 10.4, 10.6): sessions.manzara / mavzu / aylan, /api/s/track validatsiyasi,
eski bazani ko'chirish (ALTER TABLE), /api/x/overview va /api/x/devices dagi "korinish" hisoboti, rollar, seed.

    python tools/test_korinish.py                       # 8891 (seed) + 8892 (eski baza), data/sinov_korinish*.db
    python tools/test_korinish.py --port 8893 --port2 8894
    python tools/test_korinish.py --faqat unit|api|kochirish

Natija: _sinov/korinish/natija.txt. Faqat o'zi ishga tushirgan serverlarni to'xtatadi; ishchi bazaga (data/noon.db) tegmaydi.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import config  # noqa: E402
import db as dbm  # noqa: E402
from sinov_initdata import SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN, TALABA, XODIM, make  # noqa: E402

PORT, PORT2 = 8891, 8892
DB = ROOT / "data" / "sinov_korinish.db"
DB_OLD = ROOT / "data" / "sinov_korinish_eski.db"
OUT = ROOT / "_sinov" / "korinish"
ORIG_DB_PY = OUT / "orig" / "db.py"   # 05.10 gacha bo'lgan db.py nusxasi (eski sxema shundan olinadi)
TZ = config.TZ
KEYS = list(config.MANZARA_KALITLARI)
LABELS = {"sahro": "Sahro", "voha": "Voha", "shahar": "Shahar", "qahva": "Qahva", "xattot": "Xattot", "shom": "Shom"}
KOR_KEYS = {"days", "since", "users", "manzara", "tanlov", "mavzu", "soat"}   # soat - 05.10 (admin NUQTA)
MZ_KEYS = {"key", "label", "users", "sessions", "tanlagan"}
XATO_BOLIM = {"xato": "Bu bo'lim sizga ochiq emas"}
DEV = {"platform": "android", "version": "8.0", "w": 412, "h": 915, "dpr": 2.6, "scheme": "light",
       "ua": "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"}


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


# ---------------------------------------------------------------- HTTP va server
def http(port: int, method: str, path: str, body=None, headers: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"} if data is not None else {}
    h.update(headers or {})
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        raw, st = e.read(), e.code
    try:
        return st, json.loads(raw) if raw else None
    except ValueError:
        return st, None


def S(who="aziza"):
    u = TALABA[who] if isinstance(who, str) else who
    return {"X-Init-Data": make(SINOV_TALABA_TOKEN, u)}


def X(who="ceo"):
    return {"X-Init-Data": make(SINOV_XODIM_TOKEN, XODIM[who])}


def con(path: Path):
    c = sqlite3.connect(path, timeout=20)
    c.row_factory = sqlite3.Row
    return c


def q_all(path: Path, sql: str, args=()):
    c = con(path)
    try:
        return [dict(r) for r in c.execute(sql, args)]
    finally:
        c.close()


def start(port: int, db: Path, seed: bool, tag: str) -> subprocess.Popen:
    OUT.mkdir(parents=True, exist_ok=True)
    out = open(OUT / f"server_{tag}.txt", "w", encoding="utf-8")
    args = [sys.executable, str(ROOT / "server" / "main.py"), "--sinov", "--port", str(port), "--db", str(db.relative_to(ROOT))]
    if seed:
        args.append("--seed")
    p = subprocess.Popen(args, cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT, creationflags=config.CREATE_NO_WINDOW)
    t0 = time.time()
    while time.time() - t0 < 40:
        if p.poll() is not None:
            raise RuntimeError("server to'xtab qoldi: " + (OUT / f"server_{tag}.txt").read_text(encoding="utf-8"))
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
            urllib.request.build_opener(_NoRedirect).open(req, timeout=5)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302):
                return p
        except OSError:
            pass
        time.sleep(0.3)
    p.kill()
    raise RuntimeError("server 40 s da javob bermadi")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def stop(p: subprocess.Popen, port: int) -> bool:
    stop_file = config.DATA_DIR / f"sinov_{port}.stop"
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


def drop_db(path: Path) -> None:
    for suf in ("", "-wal", "-shm"):
        try:
            Path(str(path) + suf).unlink()
        except OSError:
            pass


def old_schema() -> str:
    """05.10 gacha bo'lgan sxema (manzara/mavzu/aylan ustunlarisiz) - zaxira nusxadagi db.py dan."""
    spec = importlib.util.spec_from_file_location("db_eski_korinish", ORIG_DB_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert "manzara" not in m.SCHEMA
    return m.SCHEMA


def expected(rows: list[dict], since: str, days: int, first_all: str | None) -> dict:
    """Hisobotni bazadagi xom qatorlardan Python da qayta hisoblash (SQL dan mustaqil)."""
    inp = [r for r in rows if r["started_at"] >= since]
    sess = {k: sum(1 for r in inp if r["manzara"] == k) for k in KEYS}
    mav = {m: sum(1 for r in inp if r["mavzu"] == m) for m in ("kun", "tun")}
    latest: dict[int, dict] = {}
    for r in inp:
        if r["manzara"] not in KEYS:
            continue
        cur = latest.get(r["user_id"])
        if cur is None or (r["started_at"], r["rid"]) > (cur["started_at"], cur["rid"]):
            latest[r["user_id"]] = r
    users = {k: sum(1 for r in latest.values() if r["manzara"] == k) for k in KEYS}
    chosen = {k: sum(1 for r in latest.values() if r["manzara"] == k and r["aylan"] == 0) for k in KEYS}
    items = sorted(({"key": k, "label": LABELS[k], "users": users[k], "sessions": sess[k], "tanlagan": chosen[k]} for k in KEYS),
                   key=lambda x: (-x["sessions"], -x["users"], KEYS.index(x["key"])))
    # soat: davrda boshlangan BARCHA seanslar (manzarasizlari ham), Toshkent soati (started_at +05:00)
    hours = [int(r["started_at"][11:13]) for r in inp]
    return {"days": days, "since": first_all, "users": len(latest), "manzara": items,
            "tanlov": {"aylan": sum(1 for r in latest.values() if r["aylan"] == 1),
                       "tanlangan": sum(1 for r in latest.values() if r["aylan"] == 0)},
            "mavzu": mav, "soat": [{"hour": h, "opens": hours.count(h)} for h in range(24)]}


def rows_of(path: Path) -> list[dict]:
    return q_all(path, "SELECT rowid AS rid, user_id, started_at, manzara, mavzu, aylan FROM sessions")


def first_of(path: Path):
    return q_all(path, f"SELECT MIN(started_at) AS m FROM sessions WHERE manzara IN ({','.join('?' * len(KEYS))})", KEYS)[0]["m"]


def shape_ok(k) -> bool:
    return (isinstance(k, dict) and set(k) == KOR_KEYS and isinstance(k["users"], int)
            and [x["key"] for x in k["manzara"]] and sorted(x["key"] for x in k["manzara"]) == sorted(KEYS)
            and all(set(x) == MZ_KEYS and x["label"] == LABELS[x["key"]] and 0 <= x["tanlagan"] <= x["users"] for x in k["manzara"])
            and set(k["tanlov"]) == {"aylan", "tanlangan"} and set(k["mavzu"]) == {"kun", "tun"}
            and [x["hour"] for x in k["soat"]] == list(range(24)) and all(set(x) == {"hour", "opens"} and x["opens"] >= 0 for x in k["soat"]))


# ---------------------------------------------------------------- UNIT: ko'chirish va hisobot (serversiz)
def unit_tests() -> None:
    log("\n== UNIT: eski bazani ko'chirish, korinish_report ==")
    tmp = Path(tempfile.mkdtemp(prefix="korinish_"))
    # 1) eski sxema + ma'lumot -> Store() ustunlarni qo'shadi, ma'lumot o'zgarmaydi
    p = tmp / "eski.db"
    c = sqlite3.connect(p)
    c.executescript(old_schema())
    c.execute("INSERT INTO users(id, first_name, joined_at, uslub, rejim) VALUES (1, 'Eski', '2026-10-01T09:00:00+05:00', 'game', 'dark')")
    c.execute("""INSERT INTO sessions(id, user_id, started_at, last_at, ended_at, platform, tg_version, os, device, screen, scheme,
                 uslub, rejim, ua, screens, clicks) VALUES ('11111111-1111-4111-8111-111111111111', 1, '2026-10-01T10:00:00+05:00',
                 '2026-10-01T10:05:00+05:00', NULL, 'android', '8.0', 'Android', 'telefon', '412x915', 'light', 'game', 'dark',
                 'UA', 3, 4)""")
    c.execute("""INSERT INTO ui_events(session_id, user_id, at, kind, name) VALUES ('11111111-1111-4111-8111-111111111111', 1,
                 '2026-10-01T10:00:01.000+05:00', 'screen', 'bosh')""")
    c.commit()
    before = [dict(zip([d[0] for d in c.execute("SELECT * FROM sessions").description], r))
              for r in c.execute("SELECT * FROM sessions")]
    n_cols_old = len(c.execute("PRAGMA table_info(sessions)").fetchall())
    c.close()
    st = dbm.Store(p)
    cols = [r[1] for r in st._conn().execute("PRAGMA table_info(sessions)")]
    check(cols[-3:] == ["manzara", "mavzu", "aylan"] and len(cols) == n_cols_old + 3,
          "ko'chirish: sessions ga manzara, mavzu, aylan qo'shildi (oxirida)", cols)
    after = [dict(r) for r in st._conn().execute("SELECT * FROM sessions")]
    check(len(after) == 1 and {k: after[0][k] for k in before[0]} == before[0]
          and (after[0]["manzara"], after[0]["mavzu"], after[0]["aylan"]) == (None, None, None),
          "ko'chirish: eski qator o'zgarmadi, yangi ustunlar NULL", after)
    check(st._conn().execute("SELECT COUNT(*) FROM ui_events").fetchone()[0] == 1
          and st._conn().execute("SELECT first_name FROM users WHERE id=1").fetchone()[0] == "Eski",
          "ko'chirish: boshqa jadvallar ham joyida")
    st.close()
    try:
        st2 = dbm.Store(p)
        n2 = len(st2._conn().execute("PRAGMA table_info(sessions)").fetchall())
        st2.close()
        check(n2 == n_cols_old + 3, "ko'chirish: qayta ishga tushirish xatosiz, ustunlar takrorlanmaydi", n2)
    except Exception as e:  # noqa: BLE001
        check(False, "ko'chirish: qayta ishga tushirish xatosiz", repr(e))
    # bir vaqtda bir nechta jarayon/oqim (server + sinov skripti) ko'chirmoqchi bo'lsa. Baza WAL rejimida (ishchi baza
    # kabi): WAL bo'lmagan bazada bir vaqtdagi "PRAGMA journal_mode=WAL" ning o'zi 05.10 gacha ham "locked" berishi mumkin edi.
    errs: list = []
    cols2: list = []
    for k in range(5):
        p2 = tmp / f"eski2_{k}.db"
        c = sqlite3.connect(p2)
        c.executescript(old_schema())
        c.execute("PRAGMA journal_mode=WAL")
        c.close()

        def opener():
            try:
                dbm.Store(p2).close()
            except Exception as e:  # noqa: BLE001
                errs.append(repr(e))
        th = [threading.Thread(target=opener) for _ in range(6)]
        for t in th:
            t.start()
        for t in th:
            t.join()
        c = sqlite3.connect(p2)
        cols2 = [r[1] for r in c.execute("PRAGMA table_info(sessions)")]
        c.close()
        if cols2.count("manzara") != 1:
            break
    check(not errs and cols2.count("manzara") == 1 and cols2[-3:] == ["manzara", "mavzu", "aylan"],
          "ko'chirish: 5 marta x 6 oqim bir vaqtda (WAL baza) - xatosiz, bitta nusxa", (errs, cols2))
    # yangi baza: CREATE TABLE da ustunlar bor, tartib ko'chirilgan baza bilan bir xil
    st3 = dbm.Store(tmp / "yangi.db")
    cols3 = [r[1] for r in st3._conn().execute("PRAGMA table_info(sessions)")]
    check(cols3 == cols, "yangi baza: ustunlar ko'chirilgan baza bilan bir xil tartibda", (cols3, cols))

    # 2) korinish_report: qo'lda yozilgan seanslar bo'yicha aniq kutilgan raqamlar
    now = dbm.now_tz().replace(hour=12, minute=0, second=0)
    d = lambda n, h=10, m=0: dbm.iso(now - timedelta(days=n) + timedelta(hours=h - 12, minutes=m))  # noqa: E731
    sid = lambda: str(uuid.uuid4())  # noqa: E731
    rows = [  # (user, started, manzara, mavzu, aylan)
        (1, d(20), "voha", "kun", 1),        # A: davrdan tashqarida (14 kun), 30 kunda bor
        (1, d(3), "sahro", "kun", 1),
        (1, d(1), "voha", "tun", 0),         # A oxirgisi: voha, tanlangan
        (2, d(2), "shahar", "kun", 1),
        (2, d(2), "qahva", "kun", 1),        # B: bir xil vaqt - keyin yozilgani (rowid) oxirgi -> qahva
        (3, d(2), None, "tun", None),        # C: manzarasiz (o'quvchi hisobiga kirmaydi), mavzu hisoblanadi
        (4, d(1), "xattot", None, None),     # D: aylan noma'lum - tanlovda yo'q
        (5, d(1), "pushti", "kun", 1),       # E: noma'lum kalit (bazaga qo'lda yozilgan) - e'tiborsiz, mavzu hisoblanadi
        (6, d(4), "shom", "kun", 1), (6, d(3), "shom", "kun", 1), (6, d(0, 9), "shom", "kun", 1),   # F: shom x3
        (7, d(0, 8), None, None, None),      # G: eski ilova (ko'rinish yo'q)
    ]
    with st3._c(True) as cc:
        for uid, at, man, mav, ayl in rows:
            cc.execute("INSERT INTO sessions(id, user_id, started_at, last_at, manzara, mavzu, aylan) VALUES (?,?,?,?,?,?,?)",
                       (sid(), uid, at, at, man, mav, ayl))
    r14 = st3.korinish_report(now, 14)
    hz = lambda m: [{"hour": h, "opens": m.get(h, 0)} for h in range(24)]  # noqa: E731
    want14 = {"days": 14, "since": d(20), "users": 4,
              "manzara": [{"key": "shom", "label": "Shom", "users": 1, "sessions": 3, "tanlagan": 0},
                          {"key": "voha", "label": "Voha", "users": 1, "sessions": 1, "tanlagan": 1},
                          {"key": "qahva", "label": "Qahva", "users": 1, "sessions": 1, "tanlagan": 0},
                          {"key": "xattot", "label": "Xattot", "users": 1, "sessions": 1, "tanlagan": 0},
                          {"key": "sahro", "label": "Sahro", "users": 0, "sessions": 1, "tanlagan": 0},
                          {"key": "shahar", "label": "Shahar", "users": 0, "sessions": 1, "tanlagan": 0}],
              "tanlov": {"aylan": 2, "tanlangan": 1}, "mavzu": {"kun": 7, "tun": 2},
              "soat": hz({8: 1, 9: 1, 10: 9})}   # 11 seans: manzarasiz (C, G) va noma'lum (E) ham soatda hisoblanadi
    check(r14 == want14, "korinish_report (14 kun): aniq raqamlar (oxirgi seans, teng vaqtda rowid, NULL/noma'lum e'tiborsiz; "
          "tanlagan - o'zi tanlagan o'quvchi; soat - barcha seanslar)", json.dumps(r14, ensure_ascii=False))
    r30 = st3.korinish_report(now, 30)
    check(r30["users"] == 4 and next(x for x in r30["manzara"] if x["key"] == "voha")["sessions"] == 2
          and r30["mavzu"] == {"kun": 8, "tun": 2} and r30["manzara"][0]["key"] == "shom" and r30["soat"] == hz({8: 1, 9: 1, 10: 10}),
          "korinish_report (30 kun): davrdan tashqaridagi seans qo'shildi", r30)
    r1 = st3.korinish_report(now, 1)
    check(r1["users"] == 1 and r1["manzara"][0] == {"key": "shom", "label": "Shom", "users": 1, "sessions": 1, "tanlagan": 0}
          and r1["soat"] == hz({8: 1, 9: 1})
          and r1["tanlov"] == {"aylan": 1, "tanlangan": 0} and r1["mavzu"] == {"kun": 1, "tun": 0} and r1["since"] == d(20),
          "korinish_report (1 kun): faqat bugun; since - davrdan qat'i nazar", r1)
    r_bo = dbm.Store(tmp / "bosh.db").korinish_report(now, 14)
    check(r_bo == {"days": 14, "since": None, "users": 0, "tanlov": {"aylan": 0, "tanlangan": 0}, "mavzu": {"kun": 0, "tun": 0},
                   "manzara": [{"key": k, "label": LABELS[k], "users": 0, "sessions": 0, "tanlagan": 0} for k in KEYS], "soat": hz({})},
          "korinish_report: bo'sh baza - 6 ta nol (ilova tartibida), since null", r_bo)
    check(expected(rows_of(tmp / "yangi.db"), dbm.Store._since(now, 14), 14, d(20)) == r14,
          "korinish_report: mustaqil Python hisobi bilan bir xil")
    st3.close()


# ---------------------------------------------------------------- API: seed, track, hisobot, rollar
def api_tests() -> None:
    log(f"\n== API (sinov server, port {PORT}, {DB.name}, --seed) ==")
    drop_db(DB)
    p = start(PORT, DB, True, "seed")
    try:
        _api_body()
    except Exception:
        check(False, "API sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        check(stop(p, PORT), "server stop fayli bilan yumshoq to'xtadi")


def _api_body() -> None:
    now = dbm.now_tz()
    since14, since30 = dbm.Store._since(now, 14), dbm.Store._since(now, 30)
    # ---- seed
    log("-- seed")
    ss = q_all(DB, "SELECT user_id, started_at, manzara, mavzu, aylan, rejim FROM sessions")
    cut = dbm.iso(dbm.day_start(dbm.today_of(now) - timedelta(days=dbm.SEED_KORINISH_KUN - 1)))
    new = [r for r in ss if r["started_at"] >= cut]
    old = [r for r in ss if r["started_at"] < cut]
    check(new and all(r["manzara"] in KEYS and r["mavzu"] in ("kun", "tun") and r["aylan"] in (0, 1) for r in new),
          f"seed: oxirgi {dbm.SEED_KORINISH_KUN} kundagi {len(new)} seansda manzara/mavzu/aylan bor", new[:3])
    check(old and all(r["manzara"] is None and r["mavzu"] is None and r["aylan"] is None for r in old),
          f"seed: undan oldingi {len(old)} seans - eski ilova (NULL)", old[:3])
    check(all(r["mavzu"] == "kun" for r in new if r["rejim"] == "light") and all(r["mavzu"] == "tun" for r in new if r["rejim"] == "dark")
          and {r["mavzu"] for r in new} == {"kun", "tun"}, "seed: mavzu rejimga mos (light -> kun, dark -> tun), ikkalasi ham bor")
    fixed = {r["user_id"] for r in new if r["aylan"] == 0}
    check(fixed == set(dbm.SEED_MANZARA) and all(r["manzara"] == dbm.SEED_MANZARA[r["user_id"]] for r in new if r["aylan"] == 0)
          and len({r["manzara"] for r in new}) == 6, "seed: tanlagan o'quvchilar o'z manzarasida, qolganlari aylanadi, 6 manzara ham bor",
          sorted(fixed))
    # ---- overview / devices: tuzilma va qiymatlar (mustaqil hisob bilan)
    log("-- /api/x/overview, /api/x/devices: korinish")
    s, ov = http(PORT, "GET", "/api/x/overview", None, X("ceo"))
    k = (ov or {}).get("korinish")
    check(s == 200 and shape_ok(k) and {"styles", "modes", "devices", "live"} <= set(ov),
          "overview: korinish (days, since, users, manzara[6], tanlov, mavzu) + eski styles/modes saqlangan", k)
    first = first_of(DB)
    check(k == expected(rows_of(DB), since14, 14, first), "overview.korinish (14 kun) = bazadan mustaqil hisob",
          json.dumps(k, ensure_ascii=False))
    check(k["users"] > 0 and sum(x["users"] for x in k["manzara"]) == k["users"]
          and k["tanlov"]["aylan"] + k["tanlov"]["tanlangan"] == k["users"] and k["tanlov"]["tanlangan"] == len(dbm.SEED_MANZARA)
          and all(k["manzara"][i]["sessions"] >= k["manzara"][i + 1]["sessions"] for i in range(5)),
          "overview.korinish: har o'quvchi bir marta; aylan + tanlangan = users; seanslar bo'yicha kamayish tartibida", k)
    n14 = len([r for r in rows_of(DB) if r["started_at"] >= since14])
    check(sum(x["opens"] for x in k["soat"]) == n14 and sum(x["tanlagan"] for x in k["manzara"]) == k["tanlov"]["tanlangan"],
          "overview.korinish.soat: 24 soat yig'indisi = davrdagi barcha seanslar; tanlagan yig'indisi = tanlangan", (n14, k["soat"]))
    check(k["since"] == first and k["since"] >= cut[:10], "overview.korinish.since = manzara yozilgan birinchi seans", k["since"])
    log("     namuna: " + json.dumps(k, ensure_ascii=False))
    s, ov7 = http(PORT, "GET", "/api/x/overview?days=7", None, X("admin"))
    check(s == 200 and ov7["korinish"] == expected(rows_of(DB), dbm.Store._since(now, 7), 7, first),
          "overview?days=7 (admin): korinish davrga mos", ov7 and ov7.get("korinish"))
    s, dv = http(PORT, "GET", "/api/x/devices?days=30", None, X("ceo"))
    check(s == 200 and dv["korinish"] == expected(rows_of(DB), since30, 30, first) and "device" in dv and "scheme" in dv,
          "devices?days=30: korinish (30 kun) + eski maydonlar", dv and dv.get("korinish"))
    s, dv1 = http(PORT, "GET", "/api/x/devices?days=1", None, X("admin"))
    check(s == 200 and dv1["korinish"] == expected(rows_of(DB), dbm.Store._since(now, 1), 1, first),
          "devices?days=1 (admin): faqat bugungi seanslar", dv1 and dv1.get("korinish"))
    # ---- rollar
    log("-- rollar")
    for who, want in (("ceo", 200), ("admin", 200), ("ustoz", 403), ("assistent", 403)):
        for path in ("/api/x/overview", "/api/x/devices"):
            s, b = http(PORT, "GET", path, None, X(who))
            check(s == want and (want == 200 and "korinish" in b or want == 403 and b == XATO_BOLIM),
                  f"{path}: {who} -> {want}", (s, b if s != 200 else sorted(b)))
    # 06.10 (egasi, "1 ha"): /api/x/stats (xodimlar sahifasi) - barcha 4 rol, davr = statistika davri (standart 14)
    for who in ("ceo", "admin", "ustoz", "assistent"):
        s, st = http(PORT, "GET", "/api/x/stats", None, X(who))
        check(s == 200 and st.get("korinish") == expected(rows_of(DB), since14, 14, first) and {"styles", "modes"} <= set(st),
              f"/api/x/stats: {who} -> 200, korinish (14 kun) = mustaqil hisob, eski styles/modes saqlangan",
              (s, (st or {}).get("korinish")))
    s, st7 = http(PORT, "GET", "/api/x/stats?days=7", None, X("assistent"))
    check(s == 200 and st7["korinish"] == expected(rows_of(DB), dbm.Store._since(now, 7), 7, first) and len(st7["daily"]) == 7,
          "/api/x/stats?days=7 (assistent): korinish davrga mos", st7 and st7.get("korinish"))
    s, b = http(PORT, "GET", "/api/x/stats", None, S("aziza"))
    check(s in (401, 403) and "korinish" not in (b or {}), "stats: talaba initData bilan -> rad etildi", (s, b))
    # O'quvchilar ro'yxati: oxirgi ko'rinish (manzarasi bor eng so'nggi seans; teng vaqtda - keyin yozilgani)
    s, sl = http(PORT, "GET", "/api/x/students", None, X("assistent"))
    last: dict[int, dict] = {}
    for r in rows_of(DB):
        if r["manzara"] in KEYS and (r["user_id"] not in last or (r["started_at"], r["rid"]) > (last[r["user_id"]]["started_at"], last[r["user_id"]]["rid"])):
            last[r["user_id"]] = r
    got = {x["id"]: (x.get("manzara"), x.get("mavzu")) for x in (sl or {}).get("students", [])}
    want = {u: ((last[u]["manzara"], last[u]["mavzu"]) if u in last else (None, None)) for u in got}
    check(s == 200 and got and got == want and any(v == (None, None) for v in got.values()),
          "students: manzara/mavzu = oxirgi manzarali seans, yo'q bo'lsa null (eski uslub/rejim saqlangan)",
          {u: (got[u], want[u]) for u in got if got[u] != want[u]})
    s, b = http(PORT, "GET", "/api/x/overview", None, S("aziza"))
    check(s in (401, 403) and "korinish" not in (b or {}), "overview: talaba initData bilan -> rad etildi", (s, b))
    s, b = http(PORT, "GET", "/api/x/overview")
    check(s == 401, "overview: kirishsiz -> 401", s)

    # ---- /api/s/track: validatsiya
    log("-- /api/s/track: manzara, mavzu, aylan")

    def row(sid):
        r = q_all(DB, "SELECT * FROM sessions WHERE id=?", (sid,))
        return r[0] if r else None

    def track(sid, dev, who="jahongir", evs=None):
        body = {"sid": sid, "events": evs if evs is not None else [{"k": "screen", "n": "bosh"}]}
        if dev is not None:
            body["device"] = dev
        return http(PORT, "POST", "/api/s/track", body, S(who))

    sid = str(uuid.uuid4())
    s, b = track(sid, dict(DEV, manzara="voha", mavzu="kun", aylan=True))
    r = row(sid)
    check(s == 200 and b == {"ok": True} and r and (r["manzara"], r["mavzu"], r["aylan"]) == ("voha", "kun", 1),
          "track: to'g'ri qiymatlar yozildi (voha, kun, aylan=1)", (s, b, r and (r["manzara"], r["mavzu"], r["aylan"])))
    s, b = track(sid, dict(DEV, scheme="dark", manzara="shom", mavzu="tun", aylan=False), evs=[{"k": "click", "n": "tab", "r": "profil"}])
    r = row(sid)
    check(s == 200 and r and (r["manzara"], r["mavzu"], r["aylan"], r["scheme"]) == ("voha", "tun", 1, "dark") and r["clicks"] == 1,
          "track: keyingi device - mavzu va scheme yangilandi, manzara/aylan ochilgandagidek qoldi",
          r and (r["manzara"], r["mavzu"], r["aylan"], r["scheme"]))
    s, b = track(sid, {"mavzu": "kunduz"}, evs=[])
    r = row(sid)
    check(s == 200 and r["mavzu"] == "tun", "track: keyingi device da noto'g'ri mavzu - o'zgarmaydi", (s, r["mavzu"]))
    bad = [
        ("manzara noma'lum", {"manzara": "pushti"}, (None, "kun", 1)),
        ("manzara son", {"manzara": 5}, (None, "kun", 1)),
        ("manzara ro'yxat", {"manzara": ["voha"]}, (None, "kun", 1)),
        ("manzara obyekt", {"manzara": {"v": "voha"}}, (None, "kun", 1)),
        ("manzara uzun", {"manzara": "voha" * 50}, (None, "kun", 1)),
        ("manzara null", {"manzara": None}, (None, "kun", 1)),
        ("manzara katta harf/bo'shliq", {"manzara": " Voha "}, ("voha", "kun", 1)),
        ("mavzu noma'lum", {"mavzu": "kunduz"}, ("sahro", None, 1)),
        ("mavzu light", {"mavzu": "light"}, ("sahro", None, 1)),
        ("mavzu son", {"mavzu": 1}, ("sahro", None, 1)),
        ("aylan matn", {"aylan": "ha"}, ("sahro", "kun", None)),
        ("aylan 2", {"aylan": 2}, ("sahro", "kun", None)),
        ("aylan 1.0", {"aylan": 1.0}, ("sahro", "kun", None)),
        ("aylan null", {"aylan": None}, ("sahro", "kun", None)),
        ("aylan 0 (son)", {"aylan": 0}, ("sahro", "kun", 0)),
        ("aylan 1 (son)", {"aylan": 1}, ("sahro", "kun", 1)),
        ("aylan false", {"aylan": False}, ("sahro", "kun", 0)),
        ("hammasi noto'g'ri", {"manzara": "x", "mavzu": "y", "aylan": "z"}, (None, None, None)),
    ]
    for name, patch, want in bad:
        sid_b = str(uuid.uuid4())
        dev = dict(DEV, manzara="sahro", mavzu="kun", aylan=True)
        dev.update(patch)
        s, b = track(sid_b, dev, who="aziza")
        r = row(sid_b)
        n_ev = q_all(DB, "SELECT COUNT(*) AS n FROM ui_events WHERE session_id=?", (sid_b,))[0]["n"]
        check(s == 200 and r and (r["manzara"], r["mavzu"], r["aylan"]) == want and n_ev == 1 and r["platform"] == "android",
              f"track: {name} -> 200, faqat o'sha maydon tashlandi {want}", (s, b, r and (r["manzara"], r["mavzu"], r["aylan"]), n_ev))
    # eski ilova (ko'rinish maydonlarisiz) -> NULL; keyingi so'rov bo'sh manzara/aylan ni to'ldiradi
    sid_o = str(uuid.uuid4())
    s, b = track(sid_o, DEV, who="aziza")
    r = row(sid_o)
    check(s == 200 and (r["manzara"], r["mavzu"], r["aylan"]) == (None, None, None), "track: eski ilova device -> NULL", (s, b))
    s, b = track(sid_o, dict(DEV, manzara="qahva", mavzu="tun", aylan=False), who="aziza", evs=[])
    r = row(sid_o)
    check(s == 200 and (r["manzara"], r["mavzu"], r["aylan"]) == ("qahva", "tun", 0),
          "track: keyingi so'rov bo'sh manzara/aylan ni to'ldirdi", (s, b, dict(r)))
    # device obyekt emas -> avvalgidek 400 (tuzilma xatosi); ko'rinish maydonlari hech qachon 400 bermaydi
    s, b = track(str(uuid.uuid4()), "x", who="aziza")
    check(s == 400, "track: device obyekt emas -> 400 (o'zgarmagan)", (s, b))
    # yangi o'quvchi seansi hisobotda darhol ko'rinadi
    s, ov2 = http(PORT, "GET", "/api/x/overview", None, X("ceo"))
    check(s == 200 and ov2["korinish"] == expected(rows_of(DB), dbm.Store._since(dbm.now_tz(), 14), 14, first_of(DB)),
          "overview.korinish: track dan keyin ham bazadan mustaqil hisobga teng", ov2 and ov2.get("korinish"))
    # ---- seans tafsiloti va o'quvchi kartasi
    s, se = http(PORT, "GET", f"/api/x/session?id={sid}", None, X("ceo"))
    check(s == 200 and (se["session"]["manzara"], se["session"]["mavzu"], se["session"]["aylan"]) == ("voha", "tun", True),
          "session: manzara, mavzu, aylan (bool)", se and se.get("session"))
    s, sd = http(PORT, "GET", "/api/x/student?id=800001", None, X("admin"))
    lst = (sd or {}).get("sessions") or []
    check(s == 200 and lst and all({"manzara", "mavzu", "aylan"} <= set(x) for x in lst)
          and any(x["aylan"] is None and x["manzara"] is None for x in lst) and any(x["manzara"] in KEYS for x in lst),
          "student.sessions[]: manzara/mavzu/aylan (eski seanslarda null)", lst[:2])


# ---------------------------------------------------------------- Ko'chirish: eski baza bilan haqiqiy server
def kochirish_tests() -> None:
    log(f"\n== KO'CHIRISH: eski sxemadagi baza bilan server (port {PORT2}, {DB_OLD.name}) ==")
    drop_db(DB_OLD)
    c = sqlite3.connect(DB_OLD)
    c.executescript(old_schema())
    c.execute("PRAGMA journal_mode=WAL")
    ceo = XODIM["ceo"]
    c.execute("INSERT INTO staff(id, first_name, last_name, username, role, added_at) VALUES (?,?,?,?, 'ceo', ?)",
              (ceo["id"], ceo["first_name"], ceo["last_name"], ceo["username"], "2026-09-30T09:00:00+05:00"))
    az = TALABA["aziza"]
    c.execute("INSERT INTO users(id, first_name, last_name, username, joined_at, last_seen, uslub, rejim) VALUES (?,?,?,?,?,?,?,?)",
              (az["id"], az["first_name"], az["last_name"], az["username"], "2026-09-30T09:00:00+05:00", "2026-10-04T18:00:00+05:00",
               "game", "auto"))
    now = dbm.now_tz()
    old_sids = []
    for i in range(3):
        at = dbm.iso(now - timedelta(days=i + 1))
        sid = str(uuid.UUID(int=0x1234 + i, version=4))
        old_sids.append(sid)
        c.execute("""INSERT INTO sessions(id, user_id, started_at, last_at, ended_at, platform, tg_version, os, device, screen,
                     scheme, uslub, rejim, ua, screens, clicks) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (sid, az["id"], at, at, at, "ios", "8.0", "iOS", "telefon", "390x844", "light", "game", "auto", "UA", 2 + i, i))
        c.execute("INSERT INTO ui_events(session_id, user_id, at, kind, name) VALUES (?,?,?,?,?)",
                  (sid, az["id"], at[:19] + ".000" + at[19:], "screen", "bosh"))
    c.commit()
    before = {r[0]: tuple(r) for r in c.execute("SELECT * FROM sessions")}
    n_ev = c.execute("SELECT COUNT(*) FROM ui_events").fetchone()[0]
    c.close()
    check(len(before) == 3, "eski baza tayyor (3 seans, manzara ustunisiz)")
    p = start(PORT2, DB_OLD, False, "eski")
    try:
        cols = [r["name"] for r in q_all(DB_OLD, "PRAGMA table_info(sessions)")]
        check(cols[-3:] == ["manzara", "mavzu", "aylan"], "server ishga tushganda ustunlar qo'shildi", cols)
        after = q_all(DB_OLD, "SELECT * FROM sessions")
        same = all(tuple(r[k] for k in list(r)[:-3]) == before[r["id"]] and (r["manzara"], r["mavzu"], r["aylan"]) == (None,) * 3
                   for r in after)
        check(len(after) == 3 and same, "eski seanslar o'zgarmadi, yangi ustunlar NULL", after[:1])
        check(q_all(DB_OLD, "SELECT COUNT(*) AS n FROM ui_events")[0]["n"] == n_ev, "ui_events joyida")
        s, ov = http(PORT2, "GET", "/api/x/overview", None, X("ceo"))
        k = (ov or {}).get("korinish")
        check(s == 200 and shape_ok(k) and k["users"] == 0 and k["since"] is None
              and all(x["users"] == 0 and x["sessions"] == 0 for x in k["manzara"]) and [x["key"] for x in k["manzara"]] == KEYS,
              "overview: eski ma'lumotda korinish bo'sh (since null, 6 ta nol)", k)
        s, dv = http(PORT2, "GET", "/api/x/devices", None, X("ceo"))
        check(s == 200 and dv["users"] == 1 and dv["korinish"]["users"] == 0, "devices: eski seanslar hisoblanadi, korinish bo'sh",
              (s, dv and dv.get("users")))
        s, st = http(PORT2, "GET", "/api/x/stats", None, X("ceo"))
        s2, sl = http(PORT2, "GET", "/api/x/students", None, X("ceo"))
        a0 = ((sl or {}).get("students") or [{}])[0]
        check(s == 200 and st["korinish"] == k and s2 == 200 and a0.get("manzara") is None and a0.get("mavzu") is None
              and a0.get("uslub") == "game" and "manzara" in a0 and "mavzu" in a0,
              "eski ma'lumot: stats.korinish bo'sh, students manzara/mavzu = null (uslub saqlangan)", (s, s2, a0))
        sid = str(uuid.uuid4())
        s, b = http(PORT2, "POST", "/api/s/track", {"sid": sid, "device": dict(DEV, manzara="xattot", mavzu="tun", aylan=False),
                                                     "events": [{"k": "screen", "n": "bosh"}]}, S("aziza"))
        r = q_all(DB_OLD, "SELECT manzara, mavzu, aylan FROM sessions WHERE id=?", (sid,))
        check(s == 200 and r and r[0] == {"manzara": "xattot", "mavzu": "tun", "aylan": 0}, "ko'chirilgan bazaga track yozildi",
              (s, b, r))
        s, ov = http(PORT2, "GET", "/api/x/overview", None, X("ceo"))
        k = ov["korinish"]
        check(k["users"] == 1 and k["manzara"][0] == {"key": "xattot", "label": "Xattot", "users": 1, "sessions": 1, "tanlagan": 1}
              and k["tanlov"] == {"aylan": 0, "tanlangan": 1} and k["mavzu"] == {"kun": 0, "tun": 1} and k["since"],
              "overview: yangi seans hisobotda", k)
    except Exception:
        check(False, "ko'chirish sinovi kutilmaganda to'xtadi", traceback.format_exc())
    finally:
        check(stop(p, PORT2), "server (eski baza) yumshoq to'xtadi")
    # ikkinchi ishga tushirish: ustunlar bor - tegilmaydi
    p = start(PORT2, DB_OLD, False, "eski2")
    try:
        cols = [r["name"] for r in q_all(DB_OLD, "PRAGMA table_info(sessions)")]
        check(cols.count("manzara") == 1 and len(q_all(DB_OLD, "SELECT id FROM sessions")) == 4,
              "qayta ishga tushirish: ustunlar takrorlanmadi, 4 seans joyida", cols)
        s, ov = http(PORT2, "GET", "/api/x/overview", None, X("ceo"))
        check(s == 200 and ov["korinish"]["users"] == 1, "qayta ishga tushirishdan keyin overview ishlaydi", s)
    finally:
        check(stop(p, PORT2), "server (qayta) yumshoq to'xtadi")


# ---------------------------------------------------------------- ishga tushirish
def main() -> int:
    global PORT, PORT2, DB, DB_OLD
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--port2", type=int, default=PORT2)
    ap.add_argument("--db", default=str(DB.relative_to(ROOT)))
    ap.add_argument("--db2", default=str(DB_OLD.relative_to(ROOT)))
    ap.add_argument("--faqat", choices=["unit", "api", "kochirish"])
    a = ap.parse_args()
    PORT, PORT2, DB, DB_OLD = a.port, a.port2, ROOT / a.db, ROOT / a.db2
    for pth in (DB, DB_OLD):
        if pth.resolve() == config.DB_FILE.resolve() or not pth.name.startswith("sinov_"):
            print("Faqat data/sinov_*.db bilan ishlaydi (ishchi bazaga tegilmaydi).", file=sys.stderr)
            return 2
    if config.PORT in (PORT, PORT2):
        print(f"{config.PORT} - ishchi server porti.", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if a.faqat in (None, "unit"):
        unit_tests()
    if a.faqat in (None, "api"):
        api_tests()
    if a.faqat in (None, "kochirish"):
        kochirish_tests()
    log(f"\nNATIJA: {R.ok} ta OK, {len(R.fails)} ta XATO ({time.time() - t0:.0f} s)")
    for f in R.fails:
        log("  - " + f)
    (OUT / "natija.txt").write_text("\n".join(R.lines), encoding="utf-8")
    return 0 if not R.fails else 1


if __name__ == "__main__":
    sys.exit(main())

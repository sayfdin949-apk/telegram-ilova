"""SQLite ombori (WAL): o'quvchilar, kunlik ball, progress, xodimlar, takliflar, sozlamalar, PDF keshi.

Har bir oqim bitta doimiy ulanishdan foydalanadi; WAL rejimi bir nechta jarayon (server, sinovlar) bilan xavfsiz ishlaydi.
Biznes mantiq (ball berish, seriya, reyting, statistika) shu yerda oddiy funksiyalar ko'rinishida - sinash oson.
"""
from __future__ import annotations

import hmac
import json
import random
import re
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import config
from config import TZ

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  first_name TEXT NOT NULL DEFAULT '',
  last_name TEXT NOT NULL DEFAULT '',
  username TEXT,
  photo_url TEXT,
  language_code TEXT,
  joined_at TEXT NOT NULL,
  last_seen TEXT,
  uslub TEXT,
  rejim TEXT NOT NULL DEFAULT 'auto',
  arab TEXT NOT NULL DEFAULT 'm',
  eslatma INTEGER NOT NULL DEFAULT 1,
  pm_ok INTEGER NOT NULL DEFAULT 0,
  blocked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS days (
  user_id INTEGER NOT NULL,
  day TEXT NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day)
);
CREATE INDEX IF NOT EXISTS days_day ON days(day);
CREATE TABLE IF NOT EXISTS slides (
  user_id INTEGER NOT NULL,
  dars INTEGER NOT NULL,
  idx INTEGER NOT NULL,
  seen_at TEXT NOT NULL,
  PRIMARY KEY (user_id, dars, idx)
);
CREATE TABLE IF NOT EXISTS lessons (
  user_id INTEGER NOT NULL,
  dars INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  done_at TEXT,
  PRIMARY KEY (user_id, dars)
);
CREATE TABLE IF NOT EXISTS videos (
  user_id INTEGER NOT NULL,
  vid TEXT NOT NULL,
  pos REAL NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  done_at TEXT,
  PRIMARY KEY (user_id, vid)
);
CREATE TABLE IF NOT EXISTS tests (
  user_id INTEGER NOT NULL,
  dars INTEGER NOT NULL,
  best INTEGER NOT NULL DEFAULT 0,
  last INTEGER NOT NULL DEFAULT 0,
  total INTEGER NOT NULL DEFAULT 0,
  tries INTEGER NOT NULL DEFAULT 0,
  perfect_at TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, dars)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  ref TEXT,
  xp INTEGER NOT NULL DEFAULT 0,
  at TEXT NOT NULL,
  info TEXT
);
CREATE INDEX IF NOT EXISTS events_at ON events(at);
CREATE INDEX IF NOT EXISTS events_user ON events(user_id, kind, at);
CREATE TABLE IF NOT EXISTS staff (
  id INTEGER PRIMARY KEY,
  first_name TEXT NOT NULL DEFAULT '',
  last_name TEXT NOT NULL DEFAULT '',
  username TEXT,
  role TEXT NOT NULL CHECK (role IN ('ceo','admin','ustoz','assistent')),
  added_at TEXT NOT NULL,
  added_by INTEGER
);
CREATE TABLE IF NOT EXISTS invites (
  code TEXT PRIMARY KEY,
  role TEXT NOT NULL,
  created_by INTEGER,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_by INTEGER,
  used_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE TABLE IF NOT EXISTS pdf_cache (
  bot_id INTEGER NOT NULL,
  dars INTEGER NOT NULL,
  file_id TEXT NOT NULL,
  size INTEGER,
  mtime REAL,
  at TEXT NOT NULL,
  PRIMARY KEY (bot_id, dars)
);
-- 03.10 (SPEC 10.2): seanslar, ilova ichidagi harakatlar, savollar bo'yicha test javoblari, amallar jurnali, kirish havolalari
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  started_at TEXT NOT NULL,
  last_at TEXT NOT NULL,
  ended_at TEXT,
  platform TEXT, tg_version TEXT, os TEXT, device TEXT,
  screen TEXT, scheme TEXT, uslub TEXT, rejim TEXT, ua TEXT,
  screens INTEGER NOT NULL DEFAULT 0,
  clicks INTEGER NOT NULL DEFAULT 0,
  manzara TEXT, mavzu TEXT, aylan INTEGER  -- 05.10: NUQTA ko'rinishi (eski bazaga Store.init ALTER bilan qo'shadi)
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id, started_at);
CREATE INDEX IF NOT EXISTS sessions_at ON sessions(started_at);
CREATE INDEX IF NOT EXISTS sessions_last ON sessions(last_at);
CREATE TABLE IF NOT EXISTS ui_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  at TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  ref TEXT,
  screen TEXT,
  dur_ms INTEGER
);
CREATE INDEX IF NOT EXISTS ui_events_sess ON ui_events(session_id, id);
CREATE INDEX IF NOT EXISTS ui_events_kind ON ui_events(kind, name, at);
CREATE INDEX IF NOT EXISTS ui_events_user ON ui_events(user_id, at);
CREATE INDEX IF NOT EXISTS ui_events_vaqt ON ui_events(kind, at, name, screen, user_id, dur_ms);
CREATE TABLE IF NOT EXISTS test_answers (
  user_id INTEGER NOT NULL,
  dars INTEGER NOT NULL,
  try_no INTEGER NOT NULL,
  q INTEGER NOT NULL,
  pick INTEGER,
  ok INTEGER NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (user_id, dars, try_no, q)
);
CREATE INDEX IF NOT EXISTS test_answers_dars ON test_answers(dars, q, pick, ok);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  staff_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  detail TEXT
);
CREATE TABLE IF NOT EXISTS login_links (
  code TEXT PRIMARY KEY,
  staff_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT
);
CREATE INDEX IF NOT EXISTS slides_dars ON slides(dars, idx);
-- 03.10 (SPEC 11): duellar va do'st taklifi
CREATE TABLE IF NOT EXISTS duels (
  id TEXT PRIMARY KEY,
  a_id INTEGER NOT NULL,
  b_id INTEGER NOT NULL,
  mode TEXT NOT NULL,
  lessons TEXT NOT NULL,
  questions TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  a_started TEXT, a_done TEXT, a_answers TEXT, a_correct INTEGER, a_ms INTEGER,
  b_started TEXT, b_done TEXT, b_answers TEXT, b_correct INTEGER, b_ms INTEGER,
  status TEXT NOT NULL,
  winner_id INTEGER,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS duels_a ON duels(a_id, created_at);
CREATE INDEX IF NOT EXISTS duels_b ON duels(b_id, created_at);
CREATE INDEX IF NOT EXISTS duels_status ON duels(status, expires_at);
CREATE INDEX IF NOT EXISTS duels_hisob ON duels(created_at, status, mode, winner_id, a_id, b_id);
CREATE INDEX IF NOT EXISTS duels_tugash ON duels(status, finished_at);
CREATE TABLE IF NOT EXISTS duel_invites (
  code TEXT PRIMARY KEY,
  from_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_by INTEGER,
  duel_id TEXT
);
CREATE INDEX IF NOT EXISTS duel_invites_from ON duel_invites(from_id, created_at);
CREATE TABLE IF NOT EXISTS ref_codes (
  user_id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS referrals (
  invitee_id INTEGER PRIMARY KEY,
  inviter_id INTEGER NOT NULL,
  at TEXT NOT NULL,
  rewarded_at TEXT
);
CREATE INDEX IF NOT EXISTS referrals_inviter ON referrals(inviter_id, at);
CREATE INDEX IF NOT EXISTS referrals_at ON referrals(at);
CREATE INDEX IF NOT EXISTS users_seen ON users(last_seen);
"""
TABLES = ("users", "days", "slides", "lessons", "videos", "tests", "events", "staff", "invites", "settings", "pdf_cache",
          "sessions", "ui_events", "test_answers", "audit", "login_links", "duels", "duel_invites", "ref_codes", "referrals")
DUEL_ID_ALIFBO = "abcdefghijklmnopqrstuvwxyz0123456789"
DUEL_ID_RE = re.compile(r"^[a-z0-9]{10}$")
REF_RE = re.compile(r"^[a-z0-9]{8}$")
XATO_DUEL_SHART = "Duel uchun avval kamida bitta darsni va uning testini tugating"
XATO_DUEL_UMUMIY = "Duel uchun ikkalangiz ham kamida bitta darsni va uning testini tugatgan bo'lishingiz kerak"
XATO_DUEL_RAQIB = "Hozircha mos raqib topilmadi. Do'stingizni chaqirib ko'ring."
XATO_DUEL_TOPILMADI = "Duel topilmadi"
XATO_DUEL_MUDDAT = "Duel muddati o'tgan"
XATO_DUEL_OYNADI = "Siz bu duelni allaqachon o'ynagansiz"
XATO_DUEL_BOSHLANMAGAN = "Avval duelni boshlang"
XATO_TAKLIF_ESKI = "Taklif eskirgan"
XATO_TAKLIF_OZI = "O'zingizni chaqira olmaysiz"
RECENT_KINDS = ("lesson_done", "video_done", "test_done")
TRACK_KINDS = ("screen", "click", "end", "resume")
QURILMA_NOMI = {"telefon": "Telefon", "planshet": "Planshet", "kompyuter": "Kompyuter", "brauzer": "Brauzer (Telegram Web)",
                "nomalum": "Noma'lum"}
PLATFORMA_NOMI = {"android": "Android", "android_x": "Telegram X (Android)", "ios": "iOS", "tdesktop": "Telegram Desktop",
                  "macos": "Telegram macOS", "unigram": "Unigram (Windows)", "weba": "Telegram Web A",
                  "webk": "Telegram Web K", "web": "Telegram Web", "unknown": "Noma'lum"}
SXEMA_NOMI = {"light": "Kunduzgi", "dark": "Tungi"}
# 05.10 (SPEC 10.4): eski bazalarga qo'shiladigan ustunlar (jadval, ustun, tur) - mavjud qatorlarda NULL
QOSHIMCHA_USTUNLAR = (("sessions", "manzara", "TEXT"), ("sessions", "mavzu", "TEXT"), ("sessions", "aylan", "INTEGER"))


# ---------------------------------------------------------------- vaqt yordamchilari
def now_tz() -> datetime:
    return datetime.now(TZ).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(TZ).replace(microsecond=0).isoformat()


def iso_ms(dt: datetime) -> str:
    """Millisoniyali ISO (ilova harakatlari uchun): 2026-10-03T10:00:05.123+05:00."""
    return dt.astimezone(TZ).isoformat(timespec="milliseconds")


def parse_iso(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except (TypeError, ValueError):
        return None


def today_of(dt: datetime) -> date:
    return dt.astimezone(TZ).date()


def day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=TZ)


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------- nom yordamchilari
def short_name(first: str | None, last: str | None, username: str | None = None) -> str:
    f, l = (first or "").strip(), (last or "").strip()
    if f and l:
        return f"{f} {l[0].upper()}."
    if f:
        return f
    if l:
        return l
    if username:
        return username
    return "O'quvchi"


def full_name(first: str | None, last: str | None, username: str | None = None) -> str:
    n = " ".join(x for x in ((first or "").strip(), (last or "").strip()) if x)
    return n or (username or "") or "Noma'lum"


def streak_from_days(days, today: date) -> tuple[int, int]:
    """days: ball >= 1 bo'lgan kunlar (date yoki 'YYYY-MM-DD'). (joriy seriya, eng uzun seriya).
    Joriy seriya bugundan (bugun ball bo'lmasa - kechadan) orqaga uzluksiz kunlar soni."""
    ds = set()
    for d in days:
        ds.add(d if isinstance(d, date) else date.fromisoformat(d))
    best = run = 0
    prev = None
    for d in sorted(ds):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    one = timedelta(days=1)
    if today in ds:
        cur_day = today
    elif today - one in ds:
        cur_day = today - one
    else:
        return 0, best
    cur = 0
    while cur_day in ds:
        cur += 1
        cur_day -= one
    return cur, max(best, cur)


def os_from_ua(ua: str | None, default: str) -> str:
    ua = ua or ""
    if "Windows" in ua:
        return "Windows"
    if "iPhone" in ua or "iPad" in ua or "iPod" in ua:
        return "iOS"
    if "Android" in ua:
        return "Android"
    if "CrOS" in ua:
        return "ChromeOS"
    if "Mac OS X" in ua or "Macintosh" in ua:
        return "macOS"
    if "Linux" in ua:
        return "Linux"
    return default


def classify_device(platform: str | None, w=None, h=None, ua: str | None = None) -> tuple[str, str]:
    """Telegram.WebApp.platform + ekran o'lchami + UA -> (os, device).
    device: 'telefon' | 'planshet' | 'kompyuter' | 'brauzer' | 'nomalum' (SPEC 10.4)."""
    p = (platform or "").strip().lower()
    ua = ua or ""
    try:
        small = min(int(w), int(h)) if w and h else 0
    except (TypeError, ValueError):
        small = 0
    if p in ("android", "android_x"):
        return "Android", ("planshet" if small >= 600 else "telefon")
    if p == "ios":
        return "iOS", ("planshet" if "iPad" in ua or small >= 700 else "telefon")
    if p == "tdesktop":
        return os_from_ua(ua, "Kompyuter"), "kompyuter"
    if p == "unigram":
        return "Windows", "kompyuter"
    if p == "macos":
        return "macOS", "kompyuter"
    if p in ("weba", "webk", "web"):
        return os_from_ua(ua, "Noma'lum"), "brauzer"
    return os_from_ua(ua, "Noma'lum"), "nomalum"


def device_label(device: str | None, os_: str | None) -> str:
    """Odam o'qiydigan nom: "Android telefon", "iPhone", "iPad", "Windows kompyuter", "Mac", ..."""
    if device == "telefon":
        return {"Android": "Android telefon", "iOS": "iPhone"}.get(os_ or "", "Telefon")
    if device == "planshet":
        return {"Android": "Android planshet", "iOS": "iPad"}.get(os_ or "", "Planshet")
    if device == "kompyuter":
        return {"Windows": "Windows kompyuter", "macOS": "Mac", "Linux": "Linux kompyuter"}.get(os_ or "", "Kompyuter")
    if device == "brauzer":
        return "Telegram Web (brauzer)"
    return "Noma'lum"


def _dur_s(a: str | None, b: str | None) -> int:
    da, db_ = parse_iso(a), parse_iso(b)
    if not da or not db_:
        return 0
    return max(0, int(round((db_ - da).total_seconds())))


# ---------------------------------------------------------------- duel yordamchilari (SPEC 11.1)
def duel_score(keys: list, answers: list[dict], late: bool) -> tuple[int, int, list[bool]]:
    """keys: har savolning to'g'ri javobi (0 dan); answers: [{"pick": int|None, "ms": int|None}].
    (to'g'ri javoblar, jami ms, har savol to'g'rimi). ms > 15 000 yoki yo'q -> xato (vaqt hisobiga 15 000).
    Kech yuborilgan (late) natija: 0 to'g'ri, vaqt = savollar x 15 000."""
    lim = config.DUEL_SONIYA * 1000
    oks: list[bool] = []
    total = 0
    for k, a in zip(keys, answers):
        ms, pick = a.get("ms"), a.get("pick")
        in_time = ms is not None and ms <= lim
        oks.append(bool(in_time and pick is not None and pick == k))
        total += min(ms, lim) if ms is not None else lim
    if late:
        return 0, lim * len(keys), [False] * len(keys)
    return sum(oks), total, oks


def duel_winner(a_correct: int, a_ms: int, b_correct: int, b_ms: int) -> str | None:
    """'a' | 'b' | None (durrang): ko'proq to'g'ri javob; teng bo'lsa - kamroq jami vaqt; u ham teng bo'lsa - durrang."""
    if a_correct != b_correct:
        return "a" if a_correct > b_correct else "b"
    if a_ms != b_ms:
        return "a" if a_ms < b_ms else "b"
    return None


def duel_window_start(now: datetime) -> str:
    """Hozir ham o'ynayotgan (start dan beri 105 s o'tmagan) o'yinchini aniqlash uchun chegara."""
    return iso(now - timedelta(seconds=config.DUEL_OYNA))


def duel_effective(r, now_s: str, win_s: str) -> str:
    """Bazadagi holat + vaqt: 'faol' | 'tugadi' | 'muddati_otdi' (muddati o'tgani soatlik vazifani kutmasdan).
    Muddati o'tgan paytda o'ynayotgan o'yinchi bo'lsa, uning oynasi (105 s) tugaguncha duel faol."""
    if r["status"] != "faol":
        return r["status"]
    if r["expires_at"] > now_s:
        return "faol"
    for p in ("a", "b"):
        if r[p + "_started"] and not r[p + "_done"] and r[p + "_started"] > win_s:
            return "faol"
    return "muddati_otdi"


# "hozir faol" duel (SQL; :now, :win nomli parametrlar bilan)
DUEL_FAOL_SQL = ("(d.status='faol' AND (d.expires_at > :now OR COALESCE(d.a_started > :win AND d.a_done IS NULL, 0) "
                 "OR COALESCE(d.b_started > :win AND d.b_done IS NULL, 0)))")


def new_code(n: int = 10) -> str:
    return "".join(secrets.choice(DUEL_ID_ALIFBO) for _ in range(n))


class Xato(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato (HTTP status bilan)."""

    def __init__(self, status: int, xato: str):
        super().__init__(xato)
        self.status = status
        self.xato = xato


# ---------------------------------------------------------------- ombor
class Store:
    """Har oqim uchun bitta doimiy ulanish (Windows da har safar fayl ochish sekin bo'lishi mumkin).
    Barcha usullar sinxron; server va botlar bitta asyncio oqimida ishlaydi - tranzaksiyalar aralashmaydi."""

    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.init()

    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=20, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA busy_timeout=20000")
            c.execute("PRAGMA synchronous=NORMAL")
            self._local.c = c
        return c

    def close(self) -> None:
        c = getattr(self._local, "c", None)
        if c is not None:
            c.close()
            self._local.c = None

    @contextmanager
    def _c(self, write: bool = False):
        c = self._conn()
        if write:
            c.execute("BEGIN IMMEDIATE")
        try:
            yield c
        except BaseException:
            if write and c.in_transaction:
                c.execute("ROLLBACK")
            raise
        if write and c.in_transaction:
            c.execute("COMMIT")

    def init(self) -> None:
        c = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        try:
            c.execute("PRAGMA busy_timeout=20000")
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)
            self._migrate(c)
            c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('schema', '1')")
        finally:
            c.close()

    @staticmethod
    def _migrate(c) -> None:
        """Eski bazaga yangi ustunlarni qo'shadi (bor bo'lsa - tegmaydi; mavjud ma'lumot o'zgarmaydi).
        Bir vaqtda ikki jarayon qo'shmoqchi bo'lsa, ikkinchisining "duplicate column" xatosi e'tiborga olinmaydi."""
        for table, col, typ in QOSHIMCHA_USTUNLAR:
            have = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
            if col in have:
                continue
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise

    def reset(self) -> None:
        with self._c(True) as c:
            for t in TABLES:
                c.execute(f"DELETE FROM {t}")
            c.execute("DELETE FROM sqlite_sequence WHERE name IN ('events', 'ui_events', 'audit')")
            c.execute("INSERT OR IGNORE INTO settings(key, value) VALUES ('schema', '1')")

    # ------------------------------------------------------------ sozlamalar
    def get_setting(self, key: str, default=None):
        with self._c() as c:
            r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r and r["value"] is not None else default

    def set_setting(self, key: str, value) -> None:
        with self._c(True) as c:
            if value is None:
                c.execute("DELETE FROM settings WHERE key=?", (key,))
            else:
                c.execute("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (key, str(value)))

    def course_open(self, jami: int) -> int:
        v = self.get_setting("course_open")
        try:
            n = int(v) if v is not None else jami
        except ValueError:
            n = jami
        return max(1, min(n, jami))

    def set_course_open(self, n: int) -> None:
        self.set_setting("course_open", int(n))

    # ------------------------------------------------------------ ketma-ket ochilish
    def done_lessons(self, uid: int) -> set[int]:
        with self._c() as c:
            return {r[0] for r in c.execute("SELECT dars FROM lessons WHERE user_id=? AND done_at IS NOT NULL", (uid,))}

    @staticmethod
    def available_of(done: set[int], open_n: int) -> list[int]:
        """Dars n ochiq: n <= ochiq darslar soni VA (n == 1 yoki (n-1)-dars tugatilgan)."""
        return [n for n in range(1, max(0, open_n) + 1) if n == 1 or (n - 1) in done]

    def available(self, uid: int, open_n: int) -> list[int]:
        return self.available_of(self.done_lessons(uid), open_n)

    def lesson_done(self, uid: int, dars: int) -> bool:
        with self._c() as c:
            return c.execute("SELECT 1 FROM lessons WHERE user_id=? AND dars=? AND done_at IS NOT NULL",
                             (uid, dars)).fetchone() is not None

    # ------------------------------------------------------------ o'quvchilar
    def upsert_user(self, u: dict, now: datetime, source: str = "app") -> bool:
        """Telegram foydalanuvchisini yozadi/yangilaydi. True - yangi o'quvchi."""
        with self._c(True) as c:
            return self._upsert_user(c, u, now, source)

    def _upsert_user(self, c, u: dict, now: datetime, source: str) -> bool:
        uid = int(u["id"])
        first = str(u.get("first_name") or "")[:64]
        last = str(u.get("last_name") or "")[:64]
        username = (str(u.get("username")) if u.get("username") else None)
        username = username[:64] if username else None
        photo = u.get("photo_url") if isinstance(u.get("photo_url"), str) and u["photo_url"].startswith("https://") else None
        lang = str(u.get("language_code"))[:8] if u.get("language_code") else None
        pm = 1 if (source == "bot" or u.get("allows_write_to_pm") is True) else 0
        t = iso(now)
        existed = c.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone() is not None
        c.execute(
            """INSERT INTO users(id, first_name, last_name, username, photo_url, language_code, joined_at, last_seen, pm_ok)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET first_name=excluded.first_name, last_name=excluded.last_name,
                 username=excluded.username, photo_url=COALESCE(excluded.photo_url, users.photo_url),
                 language_code=COALESCE(excluded.language_code, users.language_code),
                 last_seen=excluded.last_seen, pm_ok=MAX(users.pm_ok, excluded.pm_ok)""",
            (uid, first, last, username, photo, lang, t, t, pm))
        if source == "bot":
            c.execute("UPDATE users SET blocked=0 WHERE id=?", (uid,))
        else:
            # ilovaga kirish - faollik belgisi (ball 0 bo'lsa ham)
            c.execute("INSERT OR IGNORE INTO days(user_id, day, xp) VALUES (?, ?, 0)", (uid, today_of(now).isoformat()))
        if not existed:
            c.execute("INSERT INTO events(user_id, kind, ref, xp, at) VALUES (?, 'join', ?, 0, ?)", (uid, source, t))
        return not existed

    def get_user(self, uid: int):
        with self._c() as c:
            return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def set_prefs(self, uid: int, prefs: dict) -> None:
        cols = {k: prefs[k] for k in ("uslub", "rejim", "arab", "eslatma") if k in prefs}
        if not cols:
            return
        if "eslatma" in cols:
            cols["eslatma"] = 1 if cols["eslatma"] else 0
        sets = ", ".join(f"{k}=?" for k in cols)
        with self._c(True) as c:
            c.execute(f"UPDATE users SET {sets} WHERE id=?", (*cols.values(), uid))

    def mark_blocked(self, uid: int) -> None:
        with self._c(True) as c:
            c.execute("UPDATE users SET blocked=1 WHERE id=?", (uid,))

    @staticmethod
    def user_public(r) -> dict:
        return {"id": r["id"], "first_name": r["first_name"], "last_name": r["last_name"],
                "username": r["username"], "photo_url": r["photo_url"]}

    @staticmethod
    def prefs_of(r) -> dict:
        return {"uslub": r["uslub"], "rejim": r["rejim"], "arab": r["arab"], "eslatma": bool(r["eslatma"])}

    # ------------------------------------------------------------ ball
    @staticmethod
    def _add_xp(c, uid: int, xp: int, now: datetime) -> None:
        if xp > 0:
            c.execute("""INSERT INTO days(user_id, day, xp) VALUES (?, ?, ?)
                         ON CONFLICT(user_id, day) DO UPDATE SET xp = days.xp + excluded.xp""",
                      (uid, today_of(now).isoformat(), xp))

    @staticmethod
    def _lesson_item(c, uid: int, dars: int) -> dict:
        seen = [r[0] for r in c.execute("SELECT idx FROM slides WHERE user_id=? AND dars=? ORDER BY idx", (uid, dars))]
        r = c.execute("SELECT done_at FROM lessons WHERE user_id=? AND dars=?", (uid, dars)).fetchone()
        return {"seen": seen, "done_at": r["done_at"] if r else None}

    @staticmethod
    def _video_item(c, uid: int, vid: str) -> dict:
        r = c.execute("SELECT pos, done_at FROM videos WHERE user_id=? AND vid=?", (uid, vid)).fetchone()
        return {"pos": float(r["pos"]) if r else 0.0, "done_at": r["done_at"] if r else None}

    @staticmethod
    def _test_item(c, uid: int, dars: int) -> dict:
        r = c.execute("SELECT best, last, total, tries FROM tests WHERE user_id=? AND dars=?", (uid, dars)).fetchone()
        return ({"best": r["best"], "last": r["last"], "total": r["total"], "tries": r["tries"]} if r
                else {"best": 0, "last": 0, "total": 0, "tries": 0})

    # --- voqealar (ichki: tayyor ulanish bilan; tashqi: o'z tranzaksiyasi bilan)
    def _ev_slide(self, c, uid: int, dars: int, idx: int, now: datetime) -> tuple[int, dict]:
        t = iso(now)
        c.execute("INSERT OR IGNORE INTO lessons(user_id, dars, started_at) VALUES (?,?,?)", (uid, dars, t))
        cur = c.execute("INSERT OR IGNORE INTO slides(user_id, dars, idx, seen_at) VALUES (?,?,?,?)", (uid, dars, idx, t))
        xp = config.XP_SLAYD if cur.rowcount == 1 else 0
        self._add_xp(c, uid, xp, now)
        return xp, self._lesson_item(c, uid, dars)

    def _ev_lesson_done(self, c, uid: int, dars: int, total_slides: int, now: datetime) -> tuple[int, dict]:
        seen = c.execute("SELECT COUNT(*) FROM slides WHERE user_id=? AND dars=?", (uid, dars)).fetchone()[0]
        need = (config.DARS_TUGATISH_FOIZ * total_slides + 99) // 100  # ceil(0.8 * n), butun sonlarda
        if total_slides <= 0 or seen < need:
            raise Xato(400, f"Darsni tugatish uchun kamida {need} ta slaydni ko'ring (hozir {seen} ta).")
        t = iso(now)
        c.execute("INSERT OR IGNORE INTO lessons(user_id, dars, started_at) VALUES (?,?,?)", (uid, dars, t))
        cur = c.execute("UPDATE lessons SET done_at=? WHERE user_id=? AND dars=? AND done_at IS NULL", (t, uid, dars))
        xp = 0
        if cur.rowcount == 1:
            xp = config.XP_DARS
            self._add_xp(c, uid, xp, now)
            c.execute("INSERT INTO events(user_id, kind, ref, xp, at) VALUES (?, 'lesson_done', ?, ?, ?)",
                      (uid, str(dars), xp, t))
        return xp, self._lesson_item(c, uid, dars)

    def _ev_video_pos(self, c, uid: int, vid: str, pos: float, now: datetime) -> tuple[int, dict]:
        t = iso(now)
        c.execute("""INSERT INTO videos(user_id, vid, pos, updated_at) VALUES (?,?,?,?)
                     ON CONFLICT(user_id, vid) DO UPDATE SET pos=excluded.pos, updated_at=excluded.updated_at""",
                  (uid, vid, float(pos), t))
        return 0, self._video_item(c, uid, vid)

    def _ev_video_done(self, c, uid: int, vid: str, now: datetime, pos: float | None = None) -> tuple[int, dict]:
        t = iso(now)
        c.execute("INSERT OR IGNORE INTO videos(user_id, vid, pos, updated_at) VALUES (?,?,0,?)", (uid, vid, t))
        if pos is not None:
            c.execute("UPDATE videos SET pos=?, updated_at=? WHERE user_id=? AND vid=?", (float(pos), t, uid, vid))
        cur = c.execute("UPDATE videos SET done_at=? WHERE user_id=? AND vid=? AND done_at IS NULL", (t, uid, vid))
        xp = 0
        if cur.rowcount == 1:
            xp = config.XP_VIDEO
            self._add_xp(c, uid, xp, now)
            c.execute("INSERT INTO events(user_id, kind, ref, xp, at) VALUES (?, 'video_done', ?, ?, ?)", (uid, vid, xp, t))
        return xp, self._video_item(c, uid, vid)

    def _ev_test_done(self, c, uid: int, dars: int, correct: int, total: int, now: datetime,
                      answers: list[tuple] | None = None) -> tuple[int, dict, bool]:
        """answers: [(pick | None, ok: bool), ...] savollar tartibida -> test_answers (q 1 dan boshlanadi,
        try_no = yangilangandan keyingi tests.tries)."""
        t = iso(now)
        r = c.execute("SELECT best, tries, perfect_at FROM tests WHERE user_id=? AND dars=?", (uid, dars)).fetchone()
        old_best = r["best"] if r else 0
        new_best = max(old_best, correct)
        xp = config.XP_TEST_HAR_BIR * (new_best - old_best)
        perfect = correct == total and total > 0
        first_perfect = perfect and (r is None or r["perfect_at"] is None)
        if first_perfect:
            xp += config.XP_MUKAMMAL
        c.execute("""INSERT INTO tests(user_id, dars, best, last, total, tries, perfect_at, updated_at)
                     VALUES (?,?,?,?,?,1,?,?)
                     ON CONFLICT(user_id, dars) DO UPDATE SET best=excluded.best, last=excluded.last,
                       total=excluded.total, tries=tests.tries+1,
                       perfect_at=COALESCE(tests.perfect_at, excluded.perfect_at), updated_at=excluded.updated_at""",
                  (uid, dars, new_best, correct, total, t if perfect else None, t))
        self._add_xp(c, uid, xp, now)
        c.execute("INSERT INTO events(user_id, kind, ref, xp, at, info) VALUES (?, 'test_done', ?, ?, ?, ?)",
                  (uid, str(dars), xp, t, f"{correct}/{total}"))
        item = self._test_item(c, uid, dars)
        if answers:
            c.executemany("""INSERT OR REPLACE INTO test_answers(user_id, dars, try_no, q, pick, ok, at)
                             VALUES (?,?,?,?,?,?,?)""",
                          [(uid, dars, item["tries"], i + 1, (p if isinstance(p, int) and not isinstance(p, bool) else None),
                            1 if ok else 0, t) for i, (p, ok) in enumerate(answers)])
        return xp, item, first_perfect

    def ev_slide(self, uid, dars, idx, now):
        with self._c(True) as c:
            return self._ev_slide(c, uid, dars, idx, now)

    def ev_lesson_done(self, uid, dars, total_slides, now):
        with self._c(True) as c:
            return self._ev_lesson_done(c, uid, dars, total_slides, now)

    def ev_lesson_done_full(self, uid, dars, total_slides, now, taklif: bool = True):
        """lesson_done + do'st taklifi bonusi (SPEC 11.1): taklif bilan kelgan o'quvchi 1-darsni tugatganda ikkalasiga
        +50 ball (bir marta, shu tranzaksiyada). (xp, item, bonus | None); bonus = {"inviter_id","invitee_id","xp"}."""
        with self._c(True) as c:
            xp, item = self._ev_lesson_done(c, uid, dars, total_slides, now)
            bonus = self._referral_reward(c, uid, now) if (taklif and dars == 1) else None
        return xp, item, bonus

    def _referral_reward(self, c, uid: int, now: datetime) -> dict | None:
        r = c.execute("SELECT inviter_id FROM referrals WHERE invitee_id=? AND rewarded_at IS NULL", (uid,)).fetchone()
        if not r:
            return None
        if not c.execute("SELECT 1 FROM lessons WHERE user_id=? AND dars=1 AND done_at IS NOT NULL", (uid,)).fetchone():
            return None
        t = iso(now)
        cur = c.execute("UPDATE referrals SET rewarded_at=? WHERE invitee_id=? AND rewarded_at IS NULL", (t, uid))
        if cur.rowcount != 1:
            return None
        inviter, x = r["inviter_id"], config.XP_TAKLIF
        for who, other in ((uid, inviter), (inviter, uid)):
            self._add_xp(c, who, x, now)
            c.execute("INSERT INTO events(user_id, kind, ref, xp, at) VALUES (?, 'taklif_bonus', ?, ?, ?)", (who, str(other), x, t))
        return {"inviter_id": inviter, "invitee_id": uid, "xp": x}

    def ev_video_pos(self, uid, vid, pos, now):
        with self._c(True) as c:
            return self._ev_video_pos(c, uid, vid, pos, now)

    def ev_video_done(self, uid, vid, now, pos=None):
        with self._c(True) as c:
            return self._ev_video_done(c, uid, vid, now, pos)

    def ev_test_done(self, uid, dars, correct, total, now, answers=None):
        with self._c(True) as c:
            return self._ev_test_done(c, uid, dars, correct, total, now, answers)

    def log_event(self, uid: int, kind: str, ref: str | None, now: datetime, info: str | None = None) -> None:
        with self._c(True) as c:
            c.execute("INSERT INTO events(user_id, kind, ref, xp, at, info) VALUES (?,?,?,0,?,?)", (uid, kind, ref, iso(now), info))

    # ------------------------------------------------------------ o'quvchi ko'rinishi
    def stats(self, uid: int, today: date) -> dict:
        with self._c() as c:
            rows = c.execute("SELECT day, xp FROM days WHERE user_id=? ORDER BY day", (uid,)).fetchall()
        xp_by = {r["day"]: r["xp"] for r in rows}
        total = sum(xp_by.values())
        cur, best = streak_from_days([d for d, x in xp_by.items() if x > 0], today)
        week = [{"day": (today - timedelta(days=i)).isoformat(), "xp": xp_by.get((today - timedelta(days=i)).isoformat(), 0)}
                for i in range(6, -1, -1)]
        return {"xp": total, "streak": cur, "best_streak": best, "today_xp": xp_by.get(today.isoformat(), 0),
                "goal": config.KUNLIK_MAQSAD, "week": week}

    def progress(self, uid: int) -> dict:
        with self._c() as c:
            lessons: dict[str, dict] = {}
            for r in c.execute("SELECT dars, done_at FROM lessons WHERE user_id=? ORDER BY dars", (uid,)):
                lessons[str(r["dars"])] = {"seen": [], "done_at": r["done_at"]}
            for r in c.execute("SELECT dars, idx FROM slides WHERE user_id=? ORDER BY dars, idx", (uid,)):
                lessons.setdefault(str(r["dars"]), {"seen": [], "done_at": None})["seen"].append(r["idx"])
            videos = {r["vid"]: {"pos": float(r["pos"]), "done_at": r["done_at"]}
                      for r in c.execute("SELECT vid, pos, done_at FROM videos WHERE user_id=?", (uid,))}
            tests = {str(r["dars"]): {"best": r["best"], "last": r["last"], "total": r["total"], "tries": r["tries"]}
                     for r in c.execute("SELECT dars, best, last, total, tries FROM tests WHERE user_id=?", (uid,))}
        return {"lessons": lessons, "videos": videos, "tests": tests}

    def _streaks(self, c, uids, today: date) -> dict[int, int]:
        uids = list(uids)
        out = {u: 0 for u in uids}
        since = (today - timedelta(days=800)).isoformat()
        by: dict[int, list] = {}
        for i in range(0, len(uids), 500):
            part = uids[i:i + 500]
            q = ",".join("?" * len(part))
            for r in c.execute(f"SELECT user_id, day FROM days WHERE xp > 0 AND day >= ? AND user_id IN ({q})", (since, *part)):
                by.setdefault(r["user_id"], []).append(r["day"])
        for u, ds in by.items():
            out[u] = streak_from_days(ds, today)[0]
        return out

    def rating(self, uid: int, davr: str, today: date, top_n: int = 20) -> dict:
        with self._c() as c:
            if davr == "hafta":
                rows = c.execute("""SELECT u.id, u.first_name, u.last_name, u.username, SUM(d.xp) AS xp
                                    FROM days d JOIN users u ON u.id = d.user_id
                                    WHERE d.day >= ? GROUP BY u.id HAVING SUM(d.xp) > 0
                                    ORDER BY xp DESC, u.id ASC""", (monday_of(today).isoformat(),)).fetchall()
            else:
                rows = c.execute("""SELECT u.id, u.first_name, u.last_name, u.username, SUM(d.xp) AS xp
                                    FROM days d JOIN users u ON u.id = d.user_id
                                    GROUP BY u.id HAVING SUM(d.xp) > 0
                                    ORDER BY xp DESC, u.id ASC""").fetchall()
            top = rows[:top_n]
            me_idx = next((i for i, r in enumerate(rows) if r["id"] == uid), None)
            streaks = self._streaks(c, [r["id"] for r in top] + [uid], today)
            me_row = c.execute("SELECT first_name, last_name, username FROM users WHERE id=?", (uid,)).fetchone()
        out_top = [{"rank": i + 1, "name": short_name(r["first_name"], r["last_name"], r["username"]), "xp": r["xp"],
                    "streak": streaks.get(r["id"], 0), "me": r["id"] == uid} for i, r in enumerate(top)]
        if me_idx is not None:
            me = {"rank": me_idx + 1, "xp": rows[me_idx]["xp"]}
        else:
            me = {"rank": len(rows) + 1, "xp": 0}
        me["name"] = short_name(me_row["first_name"], me_row["last_name"], me_row["username"]) if me_row else "Siz"
        me["streak"] = streaks.get(uid, 0)
        return {"top": out_top, "me": me}

    # ------------------------------------------------------------ PDF cheklovlari va keshi
    def pdf_usage(self, uid: int, now: datetime) -> tuple[str | None, int]:
        start = iso(day_start(today_of(now)))
        with self._c() as c:
            last = c.execute("SELECT MAX(at) FROM events WHERE user_id=? AND kind='pdf'", (uid,)).fetchone()[0]
            cnt = c.execute("SELECT COUNT(*) FROM events WHERE user_id=? AND kind='pdf' AND at >= ?", (uid, start)).fetchone()[0]
        return last, cnt

    def pdf_cache_get(self, bot_id: int, dars: int):
        with self._c() as c:
            return c.execute("SELECT file_id, size, mtime FROM pdf_cache WHERE bot_id=? AND dars=?", (bot_id, dars)).fetchone()

    def pdf_cache_set(self, bot_id: int, dars: int, file_id: str, size: int, mtime: float, now: datetime) -> None:
        with self._c(True) as c:
            c.execute("""INSERT INTO pdf_cache(bot_id, dars, file_id, size, mtime, at) VALUES (?,?,?,?,?,?)
                         ON CONFLICT(bot_id, dars) DO UPDATE SET file_id=excluded.file_id, size=excluded.size,
                           mtime=excluded.mtime, at=excluded.at""", (bot_id, dars, file_id, size, mtime, iso(now)))

    def pdf_cache_drop(self, bot_id: int, dars: int) -> None:
        with self._c(True) as c:
            c.execute("DELETE FROM pdf_cache WHERE bot_id=? AND dars=?", (bot_id, dars))

    # ------------------------------------------------------------ xodimlar ko'rinishi
    def staff_stats(self, now: datetime, video_lesson=lambda vid: None, days: int = 14) -> dict:
        today = today_of(now)
        days = max(1, min(int(days), 366))
        d7 = (today - timedelta(days=6)).isoformat()
        d14 = today - timedelta(days=days - 1)
        with self._c() as c:
            students = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_today = c.execute("SELECT COUNT(DISTINCT user_id) FROM days WHERE day=?", (today.isoformat(),)).fetchone()[0]
            active_7d = c.execute("SELECT COUNT(DISTINCT user_id) FROM days WHERE day>=?", (d7,)).fetchone()[0]
            new_7d = c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?",
                               (iso(day_start(today - timedelta(days=6))),)).fetchone()[0]
            lessons_done = c.execute("SELECT COUNT(*) FROM lessons WHERE done_at IS NOT NULL").fetchone()[0]
            videos_done = c.execute("SELECT COUNT(*) FROM videos WHERE done_at IS NOT NULL").fetchone()[0]
            tests_done = c.execute("SELECT COUNT(*) FROM tests WHERE tries > 0").fetchone()[0]
            total_xp = c.execute("SELECT COALESCE(SUM(xp), 0) FROM days").fetchone()[0]
            styles = {"game": 0, "glass": 0, "none": 0}
            for r in c.execute("SELECT uslub, COUNT(*) AS n FROM users GROUP BY uslub"):
                styles["none" if r["uslub"] not in ("game", "glass") else r["uslub"]] += r["n"]
            modes = {"light": 0, "dark": 0, "auto": 0}
            for r in c.execute("SELECT rejim, COUNT(*) AS n FROM users GROUP BY rejim"):
                modes[r["rejim"] if r["rejim"] in modes else "auto"] += r["n"]
            per_day = {r["day"]: (r["a"], r["x"]) for r in c.execute(
                "SELECT day, COUNT(DISTINCT user_id) AS a, COALESCE(SUM(xp),0) AS x FROM days WHERE day >= ? GROUP BY day",
                (d14.isoformat(),))}
            q = ",".join("?" * len(RECENT_KINDS))
            recent_rows = c.execute(
                f"""SELECT e.kind, e.ref, e.at, e.info, u.first_name, u.last_name, u.username
                    FROM events e JOIN users u ON u.id = e.user_id
                    WHERE e.kind IN ({q}) ORDER BY e.at DESC, e.id DESC LIMIT 20""", RECENT_KINDS).fetchall()
        daily = []
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            a, x = per_day.get(d, (0, 0))
            daily.append({"day": d, "active": a, "xp": x})
        recent = []
        for r in recent_rows:
            ref = r["ref"] or ""
            if r["kind"] == "video_done":
                n = video_lesson(ref)
                ref_txt = f"{n}-dars" if n else ref
            else:
                ref_txt = f"{ref}-dars" if ref.isdigit() else ref
            item = {"name": short_name(r["first_name"], r["last_name"], r["username"]), "kind": r["kind"],
                    "ref": ref_txt, "at": r["at"]}
            if r["info"]:
                item["natija"] = r["info"]
            recent.append(item)
        return {"students": students, "active_today": active_today, "active_7d": active_7d, "new_7d": new_7d,
                "lessons_done": lessons_done, "videos_done": videos_done, "tests_done": tests_done,
                "avg_xp": round(total_xp / students) if students else 0, "styles": styles, "modes": modes,
                "daily": daily, "recent": recent}

    def students(self, q: str, now: datetime, limit: int = 500) -> list[dict]:
        today = today_of(now)
        q = (q or "").strip().lower()[:64]
        args: list = []
        where = ""
        if q:
            esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            like = f"%{esc}%"
            where = """WHERE lower(u.first_name || ' ' || u.last_name) LIKE ? ESCAPE '\\'
                       OR lower(COALESCE(u.username, '')) LIKE ? ESCAPE '\\' OR CAST(u.id AS TEXT) = ?"""
            args = [like, like, q.lstrip("@")]
            if q.startswith("@"):
                args[1] = "%" + esc.lstrip("@") + "%"
        qm = ",".join("?" * len(config.MANZARA_KALITLARI))
        with self._c() as c:
            # avval saralangan <= limit ta foydalanuvchi, keyin faqat ular uchun yig'indilar (10k o'quvchida ham tez)
            rows = c.execute(f"""
                SELECT u.*, COALESCE((SELECT SUM(xp) FROM days d WHERE d.user_id=u.id), 0) AS xp,
                  (SELECT COUNT(*) FROM lessons l WHERE l.user_id=u.id AND l.done_at IS NOT NULL) AS lessons_done,
                  (SELECT COUNT(*) FROM videos v WHERE v.user_id=u.id AND v.done_at IS NOT NULL) AS videos_done,
                  (SELECT COUNT(*) FROM sessions s WHERE s.user_id=u.id) AS n_sess,
                  (SELECT MAX(s.started_at) FROM sessions s WHERE s.user_id=u.id) AS last_sess,
                  (SELECT s.device || '|' || COALESCE(s.os, '') FROM sessions s WHERE s.user_id=u.id
                   ORDER BY s.started_at DESC LIMIT 1) AS dev,
                  (SELECT s.manzara || '|' || COALESCE(s.mavzu, '') FROM sessions s
                   WHERE s.user_id=u.id AND s.manzara IN ({qm})
                   ORDER BY s.started_at DESC, s.rowid DESC LIMIT 1) AS kor
                FROM (SELECT * FROM users u {where}
                      ORDER BY COALESCE(u.last_seen, u.joined_at) DESC, u.id DESC LIMIT ?) u
                ORDER BY COALESCE(u.last_seen, u.joined_at) DESC, u.id DESC""",
                (*config.MANZARA_KALITLARI, *args, limit)).fetchall()
            streaks = self._streaks(c, [r["id"] for r in rows], today)
        out = []
        for r in rows:
            dev = (r["dev"] or "").split("|", 1) if r["dev"] else None
            # 06.10: oxirgi ko'rinish - manzarasi yozilgan eng so'nggi seansdan (05.10 gacha seanslar / yo'q bo'lsa null)
            kor = (r["kor"] or "").split("|", 1) if r["kor"] else None
            mavzu = kor[1] if kor and len(kor) > 1 and kor[1] in config.MAVZULAR else None
            out.append({"id": r["id"], "name": full_name(r["first_name"], r["last_name"], r["username"]),
                        "username": r["username"], "joined_at": r["joined_at"], "last_seen": r["last_seen"], "xp": r["xp"],
                        "streak": streaks.get(r["id"], 0), "lessons_done": r["lessons_done"], "videos_done": r["videos_done"],
                        "uslub": r["uslub"], "rejim": r["rejim"],
                        "device_label": device_label(dev[0], dev[1] if len(dev) > 1 else None) if dev else None,
                        "sessions": r["n_sess"], "last_session_at": r["last_sess"],
                        "manzara": kor[0] if kor else None, "mavzu": mavzu})
        return out

    def course_stats(self) -> dict[int, dict]:
        out: dict[int, dict] = {}
        with self._c() as c:
            for r in c.execute("""SELECT dars, COUNT(*) AS started, SUM(done_at IS NOT NULL) AS done
                                  FROM lessons GROUP BY dars"""):
                out.setdefault(r["dars"], {})
                out[r["dars"]].update(started=r["started"], done=r["done"] or 0)
            for r in c.execute("SELECT dars, AVG(best) AS a FROM tests WHERE tries > 0 GROUP BY dars"):
                out.setdefault(r["dars"], {})["test_avg"] = round(r["a"], 1) if r["a"] is not None else None
        return out

    def reminder_targets(self, now: datetime) -> list[dict]:
        today = today_of(now)
        since = iso(now - timedelta(days=config.ESLATMA_FAOL_KUN))
        with self._c() as c:
            rows = c.execute("""SELECT u.id, u.first_name FROM users u
                                WHERE u.eslatma=1 AND u.blocked=0 AND u.last_seen >= ?
                                  AND NOT EXISTS (SELECT 1 FROM days d WHERE d.user_id=u.id AND d.day=? AND d.xp > 0)
                                ORDER BY u.id""", (since, today.isoformat())).fetchall()
            streaks = self._streaks(c, [r["id"] for r in rows], today)
        return [{"id": r["id"], "first_name": r["first_name"], "streak": streaks.get(r["id"], 0)} for r in rows]

    def daily_summary(self, now: datetime) -> dict:
        today = today_of(now)
        start = iso(day_start(today))
        with self._c() as c:
            new = c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (start,)).fetchone()[0]
            active = c.execute("SELECT COUNT(DISTINCT user_id) FROM days WHERE day=?", (today.isoformat(),)).fetchone()[0]
            lessons = c.execute("SELECT COUNT(*) FROM lessons WHERE done_at >= ?", (start,)).fetchone()[0]
            students = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return {"day": today.isoformat(), "new": new, "active": active, "lessons_done": lessons, "students": students}

    # ------------------------------------------------------------ xodimlar
    def staff_get(self, uid: int):
        with self._c() as c:
            return c.execute("SELECT * FROM staff WHERE id=?", (uid,)).fetchone()

    def staff_count(self) -> int:
        with self._c() as c:
            return c.execute("SELECT COUNT(*) FROM staff").fetchone()[0]

    def staff_list(self) -> list:
        with self._c() as c:
            return c.execute("""SELECT * FROM staff ORDER BY CASE role WHEN 'ceo' THEN 0 WHEN 'admin' THEN 1
                                WHEN 'ustoz' THEN 2 ELSE 3 END, added_at, id""").fetchall()

    def staff_by_role(self, role: str) -> list:
        with self._c() as c:
            return c.execute("SELECT * FROM staff WHERE role=? ORDER BY id", (role,)).fetchall()

    def staff_set(self, u: dict, role: str, by: int | None, now: datetime) -> None:
        with self._c(True) as c:
            self._staff_set(c, u, role, by, now)

    @staticmethod
    def _staff_set(c, u: dict, role: str, by: int | None, now: datetime) -> None:
        if role not in config.ROLLAR:
            raise ValueError("rol")
        c.execute("""INSERT INTO staff(id, first_name, last_name, username, role, added_at, added_by) VALUES (?,?,?,?,?,?,?)
                     ON CONFLICT(id) DO UPDATE SET first_name=excluded.first_name, last_name=excluded.last_name,
                       username=excluded.username, role=excluded.role""",
                  (int(u["id"]), str(u.get("first_name") or "")[:64], str(u.get("last_name") or "")[:64],
                   (str(u["username"])[:64] if u.get("username") else None), role, iso(now), by))

    def staff_update_names(self, u: dict) -> None:
        with self._c(True) as c:
            c.execute("UPDATE staff SET first_name=?, last_name=?, username=? WHERE id=?",
                      (str(u.get("first_name") or "")[:64], str(u.get("last_name") or "")[:64],
                       (str(u["username"])[:64] if u.get("username") else None), int(u["id"])))

    def staff_remove(self, actor_id: int, target_id: int) -> str | None:
        """None - o'chirildi; aks holda xato matni."""
        with self._c(True) as c:
            t = c.execute("SELECT role FROM staff WHERE id=?", (target_id,)).fetchone()
            if not t:
                return "Bunday xodim topilmadi."
            if target_id == actor_id:
                return "O'zingizni o'chira olmaysiz."
            if t["role"] == "ceo":
                n = c.execute("SELECT COUNT(*) FROM staff WHERE role='ceo'").fetchone()[0]
                if n <= 1:
                    return "Oxirgi CEO ni o'chirib bo'lmaydi."
            c.execute("DELETE FROM staff WHERE id=?", (target_id,))
        return None

    def pair_ceo(self, u: dict, code: str, now: datetime) -> str:
        """Ulash kodi bilan birinchi CEO ni qo'shish: 'ok' | 'band' (xodim bor) | 'xato' (kod noto'g'ri)."""
        with self._c(True) as c:
            if c.execute("SELECT COUNT(*) FROM staff").fetchone()[0] > 0:
                return "band"
            r = c.execute("SELECT value FROM settings WHERE key='ulash_kodi'").fetchone()
            stored = r["value"] if r and r["value"] else ""
            if not stored or not hmac.compare_digest(stored.encode(), str(code).strip().encode()):
                return "xato"
            self._staff_set(c, u, "ceo", None, now)
            c.execute("DELETE FROM settings WHERE key='ulash_kodi'")
        return "ok"

    def ensure_pair_code(self) -> str | None:
        """Xodimlar jadvali bo'sh bo'lsa - 6 xonali ulash kodini qaytaradi (bo'lmasa yaratadi)."""
        with self._c(True) as c:
            if c.execute("SELECT COUNT(*) FROM staff").fetchone()[0] > 0:
                c.execute("DELETE FROM settings WHERE key='ulash_kodi'")
                return None
            r = c.execute("SELECT value FROM settings WHERE key='ulash_kodi'").fetchone()
            if r and r["value"] and r["value"].isdigit() and len(r["value"]) == 6:
                return r["value"]
            code = str(100000 + secrets.randbelow(900000))
            c.execute("INSERT INTO settings(key, value) VALUES ('ulash_kodi', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (code,))
            return code

    def invite_create(self, role: str, by: int, now: datetime, ttl: int = config.TAKLIF_MUDDAT) -> tuple[str, str]:
        if role not in config.TAKLIF_ROLLARI:
            raise ValueError("rol")
        code = secrets.token_urlsafe(12)
        exp = iso(now + timedelta(seconds=ttl))
        with self._c(True) as c:
            c.execute("INSERT INTO invites(code, role, created_by, created_at, expires_at) VALUES (?,?,?,?,?)",
                      (code, role, by, iso(now), exp))
        return code, exp

    def invites_recent(self, by: int, now: datetime, seconds: int = 3600) -> int:
        with self._c() as c:
            return c.execute("SELECT COUNT(*) FROM invites WHERE created_by=? AND created_at >= ?",
                             (by, iso(now - timedelta(seconds=seconds)))).fetchone()[0]

    def invite_redeem(self, code: str, u: dict, now: datetime) -> tuple[str | None, str | None]:
        """(rol, None) - muvaffaqiyat; (None, 'yaroqsiz' | 'ceo') - xato. Bir martalik, muddati 48 soat."""
        if not isinstance(code, str) or not code or len(code) > 64:
            return None, "yaroqsiz"
        with self._c(True) as c:
            r = c.execute("SELECT * FROM invites WHERE code=?", (code,)).fetchone()
            if not r or r["used_by"] is not None or r["expires_at"] <= iso(now):
                return None, "yaroqsiz"
            cur = c.execute("SELECT role FROM staff WHERE id=?", (int(u["id"]),)).fetchone()
            if cur and cur["role"] == "ceo":
                return None, "ceo"
            c.execute("UPDATE invites SET used_by=?, used_at=? WHERE code=? AND used_by IS NULL", (int(u["id"]), iso(now), code))
            self._staff_set(c, u, r["role"], r["created_by"], now)
            return r["role"], None

    # ------------------------------------------------------------ funksiyalar (SPEC 10.3)
    @staticmethod
    def _features_of(raw) -> dict:
        try:
            d = json.loads(raw) if raw else {}
        except ValueError:
            d = {}
        if not isinstance(d, dict):
            d = {}
        return {k: (d[k] if isinstance(d.get(k), bool) else True) for k in config.FUNKSIYA_KALITLARI}

    def features(self) -> dict:
        return self._features_of(self.get_setting("features"))

    def feature_on(self, key: str) -> bool:
        return self.features().get(key, True)

    def set_feature(self, key: str, on: bool) -> tuple[dict, bool]:
        """(yangi holat, o'zgardimi)."""
        if key not in config.FUNKSIYA_KALITLARI:
            raise ValueError("funksiya")
        with self._c(True) as c:
            r = c.execute("SELECT value FROM settings WHERE key='features'").fetchone()
            cur = self._features_of(r["value"] if r else None)
            changed = cur[key] != bool(on)
            cur[key] = bool(on)
            c.execute("INSERT INTO settings(key, value) VALUES ('features', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (json.dumps(cur, separators=(",", ":")),))
        return cur, changed

    # ------------------------------------------------------------ amallar jurnali (audit)
    @staticmethod
    def _audit(c, staff_id: int, action: str, detail: dict | None, now: datetime) -> None:
        c.execute("INSERT INTO audit(at, staff_id, action, detail) VALUES (?,?,?,?)",
                  (iso(now), int(staff_id), action, json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":"))))

    def audit_add(self, staff_id: int, action: str, detail: dict | None, now: datetime) -> None:
        """detail ichida "_ism" (xodim ismi) saqlanadi - xodim keyin chiqarilsa ham jurnalda ismi qoladi."""
        d = dict(detail or {})
        with self._c(True) as c:
            r = c.execute("SELECT first_name, last_name, username FROM staff WHERE id=?", (int(staff_id),)).fetchone()
            if r:
                d.setdefault("_ism", full_name(r["first_name"], r["last_name"], r["username"]))
            self._audit(c, staff_id, action, d, now)

    def audit_list(self, limit: int = 200) -> list[dict]:
        limit = max(1, min(int(limit), 1000))
        with self._c() as c:
            rows = c.execute("""SELECT a.*, s.first_name, s.last_name, s.username FROM audit a
                                LEFT JOIN staff s ON s.id = a.staff_id ORDER BY a.id DESC LIMIT ?""", (limit,)).fetchall()
        out = []
        for r in rows:
            try:
                d = json.loads(r["detail"]) if r["detail"] else {}
            except ValueError:
                d = {}
            if not isinstance(d, dict):
                d = {}
            name = (full_name(r["first_name"], r["last_name"], r["username"]) if r["first_name"] is not None
                    else d.get("_ism") or str(r["staff_id"]))
            out.append({"id": r["id"], "at": r["at"], "staff_id": r["staff_id"], "staff_name": name, "action": r["action"],
                        "detail": {k: v for k, v in d.items() if not k.startswith("_")}})
        return out

    # ------------------------------------------------------------ /kirish havolalari (brauzer orqali admin panel)
    def login_create(self, staff_id: int, now: datetime, ttl: int = config.KIRISH_MUDDAT) -> tuple[str, str]:
        code = secrets.token_urlsafe(24)
        exp = iso(now + timedelta(seconds=ttl))
        with self._c(True) as c:
            c.execute("DELETE FROM login_links WHERE expires_at < ?", (iso(now - timedelta(days=2)),))
            c.execute("INSERT INTO login_links(code, staff_id, created_at, expires_at) VALUES (?,?,?,?)",
                      (code, int(staff_id), iso(now), exp))
        return code, exp

    def login_recent(self, staff_id: int, now: datetime, seconds: int = 3600) -> int:
        with self._c() as c:
            return c.execute("SELECT COUNT(*) FROM login_links WHERE staff_id=? AND created_at >= ?",
                             (int(staff_id), iso(now - timedelta(seconds=seconds)))).fetchone()[0]

    def login_use(self, code, now: datetime):
        """Havolani tekshiradi va ishlatilgan deb belgilaydi. Xodim qatori (admin panelga ruxsati bor) yoki None."""
        if not isinstance(code, str) or not 20 <= len(code) <= 64:
            return None
        with self._c(True) as c:
            r = c.execute("SELECT * FROM login_links WHERE code=?", (code,)).fetchone()
            if not r or r["used_at"] is not None or r["expires_at"] <= iso(now):
                return None
            cur = c.execute("UPDATE login_links SET used_at=? WHERE code=? AND used_at IS NULL", (iso(now), code))
            if cur.rowcount != 1:
                return None
            s = c.execute("SELECT * FROM staff WHERE id=?", (r["staff_id"],)).fetchone()
            if not s or s["role"] not in config.ADMIN_ROLLARI:
                return None
            self._audit(c, s["id"], "kirish", {"_ism": full_name(s["first_name"], s["last_name"], s["username"])}, now)
            return s

    # ------------------------------------------------------------ ilova ichidagi harakatlar (SPEC 10.4)
    def track(self, uid: int, sid: str, dev: dict | None, evs: list[tuple], now: datetime) -> None:
        """dev: {"platform","version","w","h","scheme","ua","manzara","mavzu","aylan"} (birinchi so'rovda shart; ko'rinish
        maydonlari tekshirilgan yoki None); evs: [(datetime, kind, name, ref, screen, dur_ms)] - mijoz tartibida.
        "screen" voqeasida `screen` ustuni = tark etilgan (oldingi) ekran, dur_ms = undagi vaqt.
        Keyingi so'rovlardagi device: scheme va mavzu yangilanadi (kun/tun seans ichida almashishi mumkin), manzara va
        aylan faqat bo'sh bo'lsa to'ldiriladi (seans manzarasi = ochilgandagisi)."""
        with self._c(True) as c:
            r = c.execute("SELECT user_id FROM sessions WHERE id=?", (sid,)).fetchone()
            if r is not None and r["user_id"] != uid:
                raise Xato(400, "Seans raqami noto'g'ri")
            if r is None:
                if not dev:
                    raise Xato(400, "Seansning birinchi so'rovida qurilma ma'lumoti (device) kerak")
                os_, device = classify_device(dev.get("platform"), dev.get("w"), dev.get("h"), dev.get("ua"))
                u = c.execute("SELECT uslub, rejim FROM users WHERE id=?", (uid,)).fetchone()
                start = min([e[0] for e in evs] + [now])
                w, h = dev.get("w"), dev.get("h")
                ayl = dev.get("aylan")
                c.execute("""INSERT INTO sessions(id, user_id, started_at, last_at, platform, tg_version, os, device, screen,
                               scheme, uslub, rejim, ua, manzara, mavzu, aylan) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (sid, uid, iso(start), iso(now), dev.get("platform"), dev.get("version"), os_, device,
                           f"{w}x{h}" if w and h else None, dev.get("scheme"),
                           u["uslub"] if u else None, u["rejim"] if u else None, dev.get("ua"),
                           dev.get("manzara"), dev.get("mavzu"), None if ayl is None else int(bool(ayl))))
                cur_screen = None
            else:
                if dev:
                    sets, args = [], []
                    if dev.get("scheme"):
                        sets.append("scheme=?")
                        args.append(dev["scheme"])
                    if dev.get("mavzu"):
                        sets.append("mavzu=?")
                        args.append(dev["mavzu"])
                    if dev.get("manzara"):
                        sets.append("manzara=COALESCE(manzara, ?)")
                        args.append(dev["manzara"])
                    if dev.get("aylan") is not None:
                        sets.append("aylan=COALESCE(aylan, ?)")
                        args.append(int(bool(dev["aylan"])))
                    if sets:
                        c.execute(f"UPDATE sessions SET {', '.join(sets)} WHERE id=?", (*args, sid))
                x = c.execute("SELECT name FROM ui_events WHERE session_id=? AND kind='screen' ORDER BY id DESC LIMIT 1",
                              (sid,)).fetchone()
                cur_screen = x["name"] if x else None
            rows = []
            screens = clicks = 0
            ended: tuple | None = None   # None - o'zgarmaydi; (qiymat,) - ended_at shu qiymat (None ham bo'lishi mumkin)
            last = now
            for at, kind, name, ref, scr, dur in evs:
                if not name:  # end/resume: n yuborilmasa - joriy ekran
                    name = scr or cur_screen or kind
                if kind == "screen":
                    screen_col = cur_screen if cur_screen is not None else scr
                    cur_screen = name
                    screens += 1
                else:
                    screen_col = scr or cur_screen
                    if kind == "click":
                        clicks += 1
                    elif kind == "end":
                        ended = (iso(at),)
                    elif kind == "resume":
                        ended = (None,)
                last = max(last, at)
                rows.append((sid, uid, iso_ms(at), kind, name, ref, screen_col, dur))
            if rows:
                c.executemany("""INSERT INTO ui_events(session_id, user_id, at, kind, name, ref, screen, dur_ms)
                                 VALUES (?,?,?,?,?,?,?,?)""", rows)
            if ended is None:
                c.execute("UPDATE sessions SET last_at=MAX(last_at, ?), screens=screens+?, clicks=clicks+? WHERE id=?",
                          (iso(last), screens, clicks, sid))
            else:
                c.execute("""UPDATE sessions SET last_at=MAX(last_at, ?), screens=screens+?, clicks=clicks+?, ended_at=?
                             WHERE id=?""", (iso(last), screens, clicks, ended[0], sid))

    # ------------------------------------------------------------ admin panel tahlillari (SPEC 10.6)
    @staticmethod
    def _since(now: datetime, days: int) -> str:
        return iso(day_start(today_of(now) - timedelta(days=max(1, int(days)) - 1)))

    def overview_extra(self, now: datetime, ekran=lambda k: k or "") -> dict:
        today_start = iso(day_start(today_of(now)))
        live_since = iso(now - timedelta(seconds=config.FAOL_HOZIR))
        with self._c() as c:
            active_now = c.execute("""SELECT COUNT(DISTINCT user_id) FROM sessions
                                      WHERE last_at >= ? AND ended_at IS NULL""", (live_since,)).fetchone()[0]
            r = c.execute("""SELECT COUNT(*) AS n, AVG((julianday(last_at) - julianday(started_at)) * 1440.0) AS m
                             FROM sessions WHERE started_at >= ?""", (today_start,)).fetchone()
            live = c.execute("""SELECT s.id, s.user_id, s.started_at, s.last_at, s.device, s.os,
                                  u.first_name, u.last_name, u.username,
                                  (SELECT e.name FROM ui_events e WHERE e.session_id = s.id AND e.kind = 'screen'
                                   ORDER BY e.id DESC LIMIT 1) AS cur
                                FROM sessions s LEFT JOIN users u ON u.id = s.user_id
                                WHERE s.last_at >= ? AND s.ended_at IS NULL
                                ORDER BY s.last_at DESC LIMIT 10""", (live_since,)).fetchall()
            devs = c.execute("""WITH last AS (SELECT user_id, device, os, MAX(started_at) AS m FROM sessions
                                              WHERE started_at >= ? GROUP BY user_id)
                                SELECT device, os, COUNT(*) AS n FROM last GROUP BY device, os""",
                             (self._since(now, 30),)).fetchall()
        by_label: dict[str, int] = {}
        for d in devs:
            lb = device_label(d["device"], d["os"])
            by_label[lb] = by_label.get(lb, 0) + d["n"]
        top = sorted(by_label.items(), key=lambda x: (-x[1], x[0]))[:5]
        return {"active_now": active_now, "sessions_today": r["n"] or 0,
                "avg_session_min": round(r["m"], 1) if r["m"] is not None else 0,
                "devices": [{"label": k, "users": v} for k, v in top],
                "live": [{"session_id": x["id"], "user_id": x["user_id"],
                          "name": full_name(x["first_name"], x["last_name"], x["username"]),
                          "screen": x["cur"], "screen_label": ekran(x["cur"]),
                          "device_label": device_label(x["device"], x["os"]), "since": x["started_at"],
                          "last_at": x["last_at"]} for x in live]}

    # Tanishuv tugadi: talaba ilovasida "Boshlash" (ob-done) yoki "O'tkazib yuborish" (ob-skip) bosilgan (SPEC 10.6, 05.10)
    TANISHUV_TUGMALAR = ("ob-done", "ob-skip")

    def funnel(self, now: datetime, days: int = 30) -> dict:
        since = self._since(now, days)
        ob = ",".join(f"'{k}'" for k in self.TANISHUV_TUGMALAR)
        steps = [
            ("kirdi", "Ilovaga kirdi",
             "EXISTS (SELECT 1 FROM sessions s WHERE s.user_id=u.id) OR EXISTS (SELECT 1 FROM days d WHERE d.user_id=u.id)"),
            # 05.10 (egasi): "Uslub tanladi" o'rniga. NUQTA ilovasi uslub yubormaydi -> tanishuv tugmasi (istalgan vaqt);
            # eski (kuzatuvdan / NUQTA dan oldingi) o'quvchilar - users.uslub. Ichki so'rov bog'lanmagan: bir marta,
            # ui_events_kind(kind, name, at) indeksi bo'yicha faqat shu 2 tugma qatorlari o'qiladi.
            ("tanishuv", "Tanishuvni tugatdi",
             f"u.uslub IS NOT NULL OR u.id IN (SELECT e.user_id FROM ui_events e INDEXED BY ui_events_kind "
             f"WHERE e.kind='click' AND e.name IN ({ob}))"),
            ("d1_boshladi", "1-darsni boshladi", "EXISTS (SELECT 1 FROM lessons l WHERE l.user_id=u.id AND l.dars=1)"),
            ("d1_tugatdi", "1-darsni tugatdi",
             "EXISTS (SELECT 1 FROM lessons l WHERE l.user_id=u.id AND l.dars=1 AND l.done_at IS NOT NULL)"),
            ("t1", "1-dars testini yechdi", "EXISTS (SELECT 1 FROM tests t WHERE t.user_id=u.id AND t.dars=1 AND t.tries > 0)"),
            ("d2_boshladi", "2-darsni boshladi", "EXISTS (SELECT 1 FROM lessons l WHERE l.user_id=u.id AND l.dars=2)"),
        ]
        for n in (5, 10, 20, 36):
            steps.append((f"d{n}_tugatdi", f"{n}-darsni tugatdi" if n != 36 else "Kursni tugatdi (36-dars)",
                          f"EXISTS (SELECT 1 FROM lessons l WHERE l.user_id=u.id AND l.dars={n} AND l.done_at IS NOT NULL)"))
        cols = ", ".join(f"COALESCE(SUM(CASE WHEN {cond} THEN 1 ELSE 0 END), 0)" for _, _, cond in steps)
        with self._c() as c:
            r = c.execute(f"SELECT COUNT(*), {cols} FROM users u WHERE u.joined_at >= ?", (since,)).fetchone()
        return {"days": days, "since": since, "joined": r[0],
                "steps": [{"key": k, "nomi": nomi, "users": r[i + 1]} for i, (k, nomi, _) in enumerate(steps)]}

    # bu tugmalarning ma'nosi ref da (qaysi bo'lim / qaysi rejim) - reytingda ref bo'yicha alohida qatorlar
    REF_TUGMALAR = ("tab", "davr", "set-rejim", "set-uslub", "set-arab", "set-manzara", "set-aylanish")

    def clicks_report(self, now: datetime, days: int = 7, ekran=lambda k: k or "",
                      tugma=lambda k, r=None: k or "") -> dict:
        since = self._since(now, days)
        today = today_of(now)
        qm = ",".join("?" * len(self.REF_TUGMALAR))
        with self._c() as c:
            top = [dict(r) for r in c.execute(
                f"""SELECT name, screen, NULL AS ref, COUNT(*) AS n, COUNT(DISTINCT user_id) AS u
                    FROM ui_events INDEXED BY ui_events_vaqt WHERE kind='click' AND at >= ? AND name NOT IN ({qm})
                    GROUP BY name, screen ORDER BY n DESC, name LIMIT 50""", (since, *self.REF_TUGMALAR))]
            top += [dict(r) for r in c.execute(
                f"""SELECT name, screen, ref, COUNT(*) AS n, COUNT(DISTINCT user_id) AS u
                    FROM ui_events INDEXED BY ui_events_kind WHERE kind='click' AND name IN ({qm}) AND at >= ?
                    GROUP BY name, screen, ref""", (*self.REF_TUGMALAR, since))]
            top = sorted(top, key=lambda r: (-r["n"], r["name"], r["ref"] or ""))[:50]
            views = {r["name"]: (r["n"], r["u"]) for r in c.execute(
                """SELECT name, COUNT(*) AS n, COUNT(DISTINCT user_id) AS u FROM ui_events INDEXED BY ui_events_vaqt
                   WHERE kind='screen' AND at >= ? GROUP BY name""", (since,))}
            durs = {r["screen"]: r["m"] for r in c.execute(
                """SELECT screen, AVG(dur_ms) AS m FROM ui_events INDEXED BY ui_events_vaqt
                   WHERE kind IN ('screen', 'end') AND at >= ? AND screen IS NOT NULL AND dur_ms > 0
                   GROUP BY screen""", (since,))}
            per_day = {r["d"]: (r["c"], r["v"]) for r in c.execute(
                """SELECT substr(at, 1, 10) AS d, SUM(kind='click') AS c, SUM(kind='screen') AS v
                   FROM ui_events INDEXED BY ui_events_vaqt WHERE kind IN ('click', 'screen') AND at >= ?
                   GROUP BY d""", (since,))}
        screens = [{"name": k, "label": ekran(k), "views": v[0], "users": v[1],
                    "avg_ms": int(round(durs[k])) if durs.get(k) is not None else None}
                   for k, v in sorted(views.items(), key=lambda x: (-x[1][0], x[0]))]
        daily = []
        for i in range(max(1, int(days)) - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            cl, vw = per_day.get(d, (0, 0))
            daily.append({"day": d, "clicks": cl or 0, "views": vw or 0})
        return {"days": days, "top": [{"name": r["name"], "ref": r["ref"], "label": tugma(r["name"], r["ref"]),
                                       "screen": r["screen"],
                                       "screen_label": ekran(r["screen"]), "count": r["n"], "users": r["u"]} for r in top],
                "screens": screens, "daily": daily}

    def devices_report(self, now: datetime, days: int = 30) -> dict:
        since = self._since(now, days)
        with self._c() as c:
            rows = c.execute("""
                WITH last AS (SELECT user_id, device, os, platform, tg_version, screen, scheme, MAX(started_at) AS m
                              FROM sessions WHERE started_at >= ? GROUP BY user_id)
                SELECT 'device' AS dim, device AS v, NULL AS v2, COUNT(*) AS n FROM last GROUP BY device
                UNION ALL SELECT 'label', device, os, COUNT(*) FROM last GROUP BY device, os
                UNION ALL SELECT 'os', os, NULL, COUNT(*) FROM last GROUP BY os
                UNION ALL SELECT 'platform', platform, NULL, COUNT(*) FROM last GROUP BY platform
                UNION ALL SELECT 'tg_version', tg_version, NULL, COUNT(*) FROM last GROUP BY tg_version
                UNION ALL SELECT 'screen', screen, NULL, COUNT(*) FROM last GROUP BY screen
                UNION ALL SELECT 'scheme', scheme, NULL, COUNT(*) FROM last GROUP BY scheme
                UNION ALL SELECT 'users', NULL, NULL, COUNT(*) FROM last""", (since,)).fetchall()
        out: dict = {"days": days, "users": 0, "device": [], "labels": [], "os": [], "platform": [], "tg_version": [],
                     "screen": [], "scheme": []}
        lab: dict[str, int] = {}
        for r in rows:
            dim, v, n = r["dim"], r["v"], r["n"]
            if dim == "users":
                out["users"] = n
                continue
            if dim == "label":
                k = device_label(v, r["v2"])
                lab[k] = lab.get(k, 0) + n
                continue
            key = v if v is not None else ""
            if dim == "device":
                label = QURILMA_NOMI.get(v or "nomalum", v or "Noma'lum")
            elif dim == "platform":
                label = PLATFORMA_NOMI.get(v or "unknown", v or "Noma'lum")
            elif dim == "scheme":
                label = SXEMA_NOMI.get(v or "", "Noma'lum")
            elif dim == "screen":
                label = v.replace("x", " x ") if v else "Noma'lum"
            else:
                label = v or "Noma'lum"
            out[dim].append({"key": key, "label": label, "users": n})
        out["labels"] = [{"key": k, "label": k, "users": n} for k, n in lab.items()]
        for k in ("device", "labels", "os", "platform", "tg_version", "screen", "scheme"):
            out[k].sort(key=lambda x: (-x["users"], x["label"]))
        out["screen"] = out["screen"][:10]
        return out

    def korinish_report(self, now: datetime, days: int = 30) -> dict:
        """NUQTA ko'rinishi (SPEC 10.6): davrdagi seanslar bo'yicha manzaralar va kun/tun; o'quvchi darajasidagi
        raqamlar (users, tanlov, manzara[].users) - har o'quvchi bir marta, davrdagi oxirgi (manzarasi bor) seansi bo'yicha.
        since - manzara yozilgan birinchi seans (davrdan qat'i nazar; 05.10 gacha seanslarda ko'rinish yo'q)."""
        since = self._since(now, days)
        keys = config.MANZARA_KALITLARI
        qm = ",".join("?" * len(keys))
        with self._c() as c:
            first = c.execute(f"SELECT MIN(started_at) FROM sessions WHERE manzara IN ({qm})", keys).fetchone()[0]
            sess = {r["manzara"]: r["n"] for r in c.execute(
                f"""SELECT manzara, COUNT(*) AS n FROM sessions WHERE started_at >= ? AND manzara IN ({qm})
                    GROUP BY manzara""", (since, *keys))}
            mav = {r["mavzu"]: r["n"] for r in c.execute(
                """SELECT mavzu, COUNT(*) AS n FROM sessions WHERE started_at >= ? AND mavzu IN ('kun', 'tun')
                   GROUP BY mavzu""", (since,))}
            last = c.execute(
                f"""SELECT manzara, aylan, COUNT(*) AS n FROM (
                      SELECT manzara, aylan,
                             ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY started_at DESC, rowid DESC) AS rn
                      FROM sessions WHERE started_at >= ? AND manzara IN ({qm}))
                    WHERE rn = 1 GROUP BY manzara, aylan""", (since, *keys)).fetchall()
            # 05.10 (admin NUQTA): ilova ochilishlari Toshkent soati bo'yicha - davrda boshlangan BARCHA seanslar
            # (started_at doim +05:00 bilan yoziladi, soat = 12-13-belgilar)
            soat = {r[0]: r[1] for r in c.execute(
                """SELECT CAST(substr(started_at, 12, 2) AS INTEGER) AS h, COUNT(*) FROM sessions
                   WHERE started_at >= ? GROUP BY h""", (since,))}
        users_of = dict.fromkeys(keys, 0)
        tanlagan_of = dict.fromkeys(keys, 0)   # 05.10: shu manzarani o'zi tanlab qo'ygan o'quvchilar (oxirgi seansda aylan=0)
        aylan = tanlangan = 0
        for r in last:
            users_of[r["manzara"]] += r["n"]
            if r["aylan"] == 1:
                aylan += r["n"]
            elif r["aylan"] == 0:
                tanlangan += r["n"]
                tanlagan_of[r["manzara"]] += r["n"]
        order = {k: i for i, k in enumerate(keys)}
        manzara = sorted(({"key": k, "label": label, "users": users_of[k], "sessions": sess.get(k, 0), "tanlagan": tanlagan_of[k]}
                          for k, label in config.MANZARALAR),
                         key=lambda x: (-x["sessions"], -x["users"], order[x["key"]]))
        return {"days": days, "since": first, "users": sum(users_of.values()), "manzara": manzara,
                "tanlov": {"aylan": aylan, "tanlangan": tanlangan},
                "mavzu": {m: mav.get(m, 0) for m in config.MAVZULAR},
                "soat": [{"hour": h, "opens": soat.get(h, 0)} for h in range(24)]}

    # ------------------------------------------------------------ admin NUQTA Bosh sahifa qo'shimchalari (05.10)
    def week_compare(self, now: datetime) -> dict:
        """O'tgan hafta (8-14 kun oldin) - "7 kunda faol" va "Yangi (7 kun)" bilan solishtirish uchun."""
        today = today_of(now)
        a, b = today - timedelta(days=13), today - timedelta(days=7)
        with self._c() as c:
            act = c.execute("SELECT COUNT(DISTINCT user_id) FROM days WHERE day >= ? AND day <= ?",
                            (a.isoformat(), b.isoformat())).fetchone()[0]
            new = c.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ? AND joined_at < ?",
                            (iso(day_start(a)), iso(day_start(b + timedelta(days=1))))).fetchone()[0]
        return {"active_7d": act, "new_7d": new}

    def duel_summary(self, now: datetime, days: int = 14) -> dict:
        """Davrda boshlangan duellar holati (Bosh sahifa kartasi): g'olib aniqlangan / durrang / davom etmoqda / muddati o'tgan.
        Ta'riflar duels_report bilan bir xil (holat o'qilganda hisoblanadi)."""
        p = {"since": self._since(now, days), "now": iso(now), "win": duel_window_start(now)}
        with self._c() as c:
            r = c.execute("""SELECT COUNT(*) AS t, COALESCE(SUM(status='tugadi'), 0) AS f,
                                    COALESCE(SUM(status='tugadi' AND winner_id IS NULL), 0) AS dr
                             FROM duels WHERE created_at >= :since""", p).fetchone()
            active = c.execute(f"SELECT COUNT(*) FROM duels d WHERE d.status='faol' AND d.created_at >= :since AND {DUEL_FAOL_SQL}",
                               p).fetchone()[0]
        return {"days": days, "total": r["t"], "decided": r["f"] - r["dr"], "draws": r["dr"], "active": active,
                "expired": r["t"] - r["f"] - active}

    def recent_duels(self, limit: int = 20) -> list[dict]:
        """So'nggi faollik uchun tugagan duellar (events 'duel_done'): kim, kim bilan, hisob (my:their), natija."""
        with self._c() as c:
            rows = c.execute("""SELECT e.ref, e.at, e.info, e.xp, e.user_id, u.first_name, u.last_name, u.username,
                                       d.a_id, d.b_id, d.winner_id,
                                       ua.first_name AS a_fn, ua.last_name AS a_ln, ua.username AS a_un,
                                       ub.first_name AS b_fn, ub.last_name AS b_ln, ub.username AS b_un
                                FROM events e JOIN users u ON u.id = e.user_id
                                LEFT JOIN duels d ON d.id = e.ref
                                LEFT JOIN users ua ON ua.id = d.a_id LEFT JOIN users ub ON ub.id = d.b_id
                                WHERE e.kind = 'duel_done' ORDER BY e.at DESC, e.id DESC LIMIT ?""", (limit,)).fetchall()
        out = []
        for r in rows:
            if r["a_id"] == r["user_id"]:
                rival = short_name(r["b_fn"], r["b_ln"], r["b_un"])
            elif r["b_id"] == r["user_id"]:
                rival = short_name(r["a_fn"], r["a_ln"], r["a_un"])
            else:
                rival = None
            res = ("durrang" if r["winner_id"] is None else "yutdi" if r["winner_id"] == r["user_id"] else "yutqazdi") \
                if r["a_id"] is not None else ("yutdi" if (r["xp"] or 0) >= config.XP_DUEL_YUTUQ else
                                               "durrang" if (r["xp"] or 0) > 0 else "yutqazdi")
            item = {"name": short_name(r["first_name"], r["last_name"], r["username"]), "kind": "duel_done",
                    "ref": f"{rival} bilan" if rival else "", "at": r["at"], "result": res, "duel_id": r["ref"]}
            if r["info"]:
                item["natija"] = r["info"]
            out.append(item)
        return out

    def duel_rivals(self, uid: int, ids) -> dict[str, str]:
        """Seans voqealaridagi duel id -> raqibning qisqa ismi (shu o'quvchiga nisbatan)."""
        ids = sorted({i for i in ids if isinstance(i, str)})[:300]
        if not ids:
            return {}
        q = ",".join("?" * len(ids))
        with self._c() as c:
            rows = c.execute(f"{self._DUEL_SELECT} WHERE d.id IN ({q})", ids).fetchall()
        out = {}
        for r in rows:
            if r["a_id"] == uid:
                out[r["id"]] = short_name(r["b_fn"], r["b_ln"], r["b_un"])
            elif r["b_id"] == uid:
                out[r["id"]] = short_name(r["a_fn"], r["a_ln"], r["a_un"])
        return out

    def tests_summary(self, kurs) -> dict:
        with self._c() as c:
            since = c.execute("SELECT MIN(at) FROM test_answers").fetchone()[0]
            agg = {r["dars"]: r for r in c.execute(
                """SELECT dars, COUNT(*) AS takers, COALESCE(SUM(tries), 0) AS attempts, AVG(best) AS avg_best,
                          SUM(CASE WHEN total > 0 AND best >= total THEN 1 ELSE 0 END) AS perfect
                   FROM tests WHERE tries > 0 GROUP BY dars""")}
            hard: dict[int, dict] = {}
            for r in c.execute("SELECT dars, q, COUNT(*) AS n, SUM(ok = 0) AS w FROM test_answers GROUP BY dars, q"):
                pct = round(100.0 * (r["w"] or 0) / r["n"]) if r["n"] else 0
                h = hard.get(r["dars"])
                if h is None or pct > h["wrong_pct"]:
                    hard[r["dars"]] = {"q": r["q"], "wrong_pct": pct, "answers": r["n"]}
        lessons = []
        for ls in kurs.lessons():
            n = ls["n"]
            a = agg.get(n)
            h = hard.get(n)
            t = kurs.test(n)
            lessons.append({"dars": n, "nomi": ls.get("nomi"), "has_test": t is not None,
                            "savollar": len(t["savollar"]) if t else 0,
                            "takers": a["takers"] if a else 0, "attempts": a["attempts"] if a else 0,
                            "avg_best": round(a["avg_best"], 1) if a and a["avg_best"] is not None else None,
                            "perfect": a["perfect"] if a else 0,
                            "hardest": {"q": h["q"], "wrong_pct": h["wrong_pct"]} if h and h["wrong_pct"] > 0 else None})
        return {"since": since, "lessons": lessons}

    def test_detail(self, dars: int, test: dict, limit: int = 500) -> dict:
        qs = test.get("savollar") or []
        with self._c() as c:
            picks: dict[int, dict] = {}
            for r in c.execute("""SELECT q, pick, COUNT(*) AS n, SUM(ok = 0) AS w FROM test_answers WHERE dars=?
                                  GROUP BY q, pick""", (dars,)):
                p = picks.setdefault(r["q"], {"n": 0, "w": 0, "by": {}})
                p["n"] += r["n"]
                p["w"] += r["w"] or 0
                p["by"][r["pick"]] = p["by"].get(r["pick"], 0) + r["n"]
            studs = c.execute("""SELECT t.user_id, t.best, t.total, t.tries, t.updated_at, u.first_name, u.last_name, u.username
                                 FROM tests t LEFT JOIN users u ON u.id = t.user_id
                                 WHERE t.dars=? AND t.tries > 0 ORDER BY t.best DESC, t.updated_at DESC LIMIT ?""",
                              (dars, limit)).fetchall()
        savollar = []
        for i, q in enumerate(qs):
            item = dict(q) if isinstance(q, dict) else {"q": q}
            p = picks.get(i + 1, {"n": 0, "w": 0, "by": {}})
            nopt = len(item.get("opts") or []) or 4
            item.update({"n": i + 1, "answers": p["n"], "wrong_pct": round(100.0 * p["w"] / p["n"]) if p["n"] else None,
                         "picks": [p["by"].get(j, 0) for j in range(nopt)], "skipped": p["by"].get(None, 0)})
            savollar.append(item)
        return {"savollar": savollar,
                "students": [{"id": r["user_id"], "name": full_name(r["first_name"], r["last_name"], r["username"]),
                              "best": r["best"], "total": r["total"], "tries": r["tries"], "updated_at": r["updated_at"]}
                             for r in studs]}

    def dropoff(self, dars: int, slaydlar: int) -> dict:
        with self._c() as c:
            by = {r["idx"]: r["n"] for r in c.execute("SELECT idx, COUNT(*) AS n FROM slides WHERE dars=? GROUP BY idx", (dars,))}
            r = c.execute("SELECT COUNT(*) AS s, SUM(done_at IS NOT NULL) AS d FROM lessons WHERE dars=?", (dars,)).fetchone()
        total = max(slaydlar, max(by) if by else 0)
        return {"slaydlar": slaydlar, "started": r["s"] or 0, "done": r["d"] or 0,
                "seen": [{"idx": i, "users": by.get(i, 0)} for i in range(1, total + 1)]}

    def student_detail(self, uid: int, kurs, now: datetime) -> dict | None:
        today = today_of(now)
        with self._c() as c:
            u = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            if not u:
                return None
            seen = {r["dars"]: r["n"] for r in c.execute(
                "SELECT dars, COUNT(*) AS n FROM slides WHERE user_id=? GROUP BY dars", (uid,))}
            lrows = {r["dars"]: r for r in c.execute("SELECT dars, started_at, done_at FROM lessons WHERE user_id=?", (uid,))}
            trows = c.execute("SELECT * FROM tests WHERE user_id=? ORDER BY dars", (uid,)).fetchall()
            last_ans: dict[int, list] = {}
            for r in c.execute("""SELECT a.dars, a.q, a.pick, a.ok FROM test_answers a
                                  JOIN (SELECT dars, MAX(try_no) AS t FROM test_answers WHERE user_id=? GROUP BY dars) m
                                    ON m.dars = a.dars AND m.t = a.try_no
                                  WHERE a.user_id=? ORDER BY a.dars, a.q""", (uid, uid)):
                last_ans.setdefault(r["dars"], []).append({"q": r["q"], "pick": r["pick"], "ok": bool(r["ok"])})
            vrows = {r["vid"]: r for r in c.execute("SELECT vid, pos, done_at FROM videos WHERE user_id=?", (uid,))}
            devs = c.execute("""SELECT device, os, platform, tg_version, screen, MAX(last_at) AS last_at, COUNT(*) AS n
                                FROM sessions WHERE user_id=? GROUP BY device, os, platform, tg_version, screen
                                ORDER BY last_at DESC""", (uid,)).fetchall()
            sess = c.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY started_at DESC LIMIT 50", (uid,)).fetchall()
            n_sess = c.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (uid,)).fetchone()[0]
            # 2-bosqich (SPEC 11.5): duellar va takliflar
            p = self._duel_params(uid, now)
            dr = c.execute(f"""SELECT COALESCE(SUM(d.status='tugadi'), 0) AS played,
                                      COALESCE(SUM(d.status='tugadi' AND d.winner_id = :me), 0) AS won,
                                      COALESCE(SUM(d.status='tugadi' AND d.winner_id IS NULL), 0) AS draw,
                                      COALESCE(SUM(CASE WHEN {DUEL_FAOL_SQL} THEN 1 ELSE 0 END), 0) AS active,
                                      COUNT(*) AS total
                               FROM duels d WHERE d.id IN (SELECT id FROM duels WHERE a_id=:me
                                                           UNION ALL SELECT id FROM duels WHERE b_id=:me)""", p).fetchone()
            ib = c.execute("""SELECT r.inviter_id, r.at, r.rewarded_at, u.first_name, u.last_name, u.username
                              FROM referrals r LEFT JOIN users u ON u.id = r.inviter_id WHERE r.invitee_id=?""", (uid,)).fetchone()
            n_inv = c.execute("SELECT COUNT(*), COUNT(rewarded_at) FROM referrals WHERE inviter_id=?", (uid,)).fetchone()
            ref_xp = c.execute("SELECT COALESCE(SUM(xp), 0) FROM events WHERE user_id=? AND kind='taklif_bonus'", (uid,)).fetchone()[0]
        st = self.stats(uid, today)
        lessons = []
        for ls in kurs.lessons():
            n = ls["n"]
            lr = lrows.get(n)
            lessons.append({"n": n, "nomi": ls.get("nomi"), "seen": seen.get(n, 0), "slaydlar": kurs.slides(n),
                            "started_at": lr["started_at"] if lr else None, "done_at": lr["done_at"] if lr else None})
        videos = []
        for ls in kurs.lessons():
            for v in kurs.lesson_videos(ls):
                vr = vrows.get(v["id"])
                videos.append({"id": v["id"], "dars": ls["n"], "nomi": v.get("nomi"), "davomiylik": v.get("davomiylik"),
                               "pos": float(vr["pos"]) if vr else 0.0, "done_at": vr["done_at"] if vr else None})
        return {
            "user": {"id": u["id"], "first_name": u["first_name"], "last_name": u["last_name"], "username": u["username"],
                     "photo_url": u["photo_url"], "name": full_name(u["first_name"], u["last_name"], u["username"]),
                     "joined_at": u["joined_at"], "last_seen": u["last_seen"], "blocked": bool(u["blocked"])},
            "prefs": self.prefs_of(u),
            "stats": {"xp": st["xp"], "streak": st["streak"], "best_streak": st["best_streak"], "today_xp": st["today_xp"],
                      "week": st["week"]},
            "devices": [{"label": device_label(d["device"], d["os"]), "device": d["device"], "os": d["os"],
                         "platform": d["platform"], "tg_version": d["tg_version"], "screen": d["screen"],
                         "last_at": d["last_at"], "sessions": d["n"]} for d in devs],
            "lessons": lessons,
            "tests": [{"dars": t["dars"], "best": t["best"], "last": t["last"], "total": t["total"], "tries": t["tries"],
                       "updated_at": t["updated_at"], "last_answers": last_ans.get(t["dars"], [])} for t in trows],
            "videos": videos,
            "sessions_total": n_sess,
            "sessions": [self._session_brief(s) for s in sess],
            "duels": {"played": dr["played"], "won": dr["won"], "lost": dr["played"] - dr["won"] - dr["draw"], "draw": dr["draw"],
                      "active": dr["active"], "expired": dr["total"] - dr["played"] - dr["active"]},
            "invited_by": ({"id": ib["inviter_id"], "name": full_name(ib["first_name"], ib["last_name"], ib["username"]),
                            "at": ib["at"], "rewarded": ib["rewarded_at"] is not None} if ib else None),
            "invited": n_inv[0],
            "invited_rewarded": n_inv[1],
            "taklif_xp": ref_xp,
        }

    @staticmethod
    def _session_brief(s) -> dict:
        return {"id": s["id"], "started_at": s["started_at"], "last_at": s["last_at"], "ended_at": s["ended_at"],
                "dur_s": _dur_s(s["started_at"], s["last_at"]), "device_label": device_label(s["device"], s["os"]),
                "platform": s["platform"], "screens": s["screens"], "clicks": s["clicks"], "ended": s["ended_at"] is not None,
                "manzara": s["manzara"], "mavzu": s["mavzu"], "aylan": None if s["aylan"] is None else bool(s["aylan"])}

    def session_detail(self, sid: str, limit: int = 2000):
        with self._c() as c:
            s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
            if not s:
                return None
            u = c.execute("SELECT first_name, last_name, username FROM users WHERE id=?", (s["user_id"],)).fetchone()
            ev = c.execute("""SELECT id, at, kind, name, ref, screen, dur_ms FROM ui_events WHERE session_id=?
                              ORDER BY id LIMIT ?""", (sid, limit)).fetchall()
        sess = self._session_brief(s)
        sess.update({"user_id": s["user_id"], "device": s["device"], "os": s["os"], "tg_version": s["tg_version"],
                     "screen": s["screen"], "scheme": s["scheme"], "uslub": s["uslub"], "rejim": s["rejim"], "ua": s["ua"]})
        user = {"id": s["user_id"], "name": full_name(u["first_name"], u["last_name"], u["username"]) if u else str(s["user_id"])}
        return sess, user, [dict(r) for r in ev]

    # ------------------------------------------------------------ duellar (SPEC 11)
    # pool: {dars: savollar soni} - testi bor darslar (kurs.test(n)); faqat ikkala o'yinchi ham tugatgan (lessons.done_at)
    # darslardan savol olinadi. Barcha yozuvlar bitta BEGIN IMMEDIATE tranzaksiyada - limitlar va ball aniq bir marta.
    _DUEL_SELECT = """SELECT d.*, ua.first_name AS a_fn, ua.last_name AS a_ln, ua.username AS a_un,
                         ub.first_name AS b_fn, ub.last_name AS b_ln, ub.username AS b_un
                      FROM duels d LEFT JOIN users ua ON ua.id = d.a_id LEFT JOIN users ub ON ub.id = d.b_id"""

    @staticmethod
    def _done_set(c, uid: int) -> set[int]:
        return {r[0] for r in c.execute("SELECT dars FROM lessons WHERE user_id=? AND done_at IS NOT NULL", (uid,))}

    def _tested_done(self, c, uid: int, pool: dict) -> list[int]:
        return sorted(n for n in self._done_set(c, uid) if n in pool)

    def duel_can(self, uid: int, pool: dict) -> bool:
        with self._c() as c:
            return bool(self._tested_done(c, uid, pool))

    @staticmethod
    def _pick_questions(common, pool: dict, rng) -> list[dict] | None:
        """Umumiy darslardagi barcha savollardan tasodifiy 5 tasi ([{"dars","q"}], q 1 dan); 3 tadan kam bo'lsa None."""
        pairs = [(n, q) for n in sorted(common) for q in range(1, int(pool.get(n) or 0) + 1)]
        k = min(config.DUEL_SAVOLLAR, len(pairs))
        if k < config.DUEL_MIN_SAVOL:
            return None
        return [{"dars": n, "q": q} for n, q in rng.sample(pairs, k)]

    @staticmethod
    def _duel_params(uid: int, now: datetime) -> dict:
        return {"me": uid, "now": iso(now), "win": duel_window_start(now), "day": iso(day_start(today_of(now)))}

    def _duel_usage(self, c, uid: int, now: datetime) -> tuple[int, int]:
        """(bugun boshlagan duellari: tasodifiy + do'st havolalari, tugallanmagan chiquvchi duellar + ochiq havolalar)."""
        p = self._duel_params(uid, now)
        today = c.execute("""SELECT (SELECT COUNT(*) FROM duels WHERE a_id=:me AND mode='random' AND created_at >= :day)
                                  + (SELECT COUNT(*) FROM duel_invites WHERE from_id=:me AND created_at >= :day)""", p).fetchone()[0]
        open_ = c.execute(f"""SELECT (SELECT COUNT(*) FROM duels d WHERE d.a_id=:me AND {DUEL_FAOL_SQL})
                                   + (SELECT COUNT(*) FROM duel_invites WHERE from_id=:me AND used_by IS NULL AND expires_at > :now)""",
                          p).fetchone()[0]
        return today, open_

    def duel_usage(self, uid: int, now: datetime) -> tuple[int, int]:
        with self._c() as c:
            return self._duel_usage(c, uid, now)

    def _duel_check_limits(self, c, uid: int, now: datetime) -> None:
        today, open_ = self._duel_usage(c, uid, now)
        if today >= config.DUEL_KUNLIK:
            raise Xato(429, f"Bugun {config.DUEL_KUNLIK} ta duel boshladingiz - bu kunlik chegara. Ertaga yana urinib ko'ring.")
        if open_ >= config.DUEL_OCHIQ:
            raise Xato(429, f"Sizda {open_} ta tugallanmagan duel bor. Yangisini boshlash uchun avval ularning natijasini kuting.")

    def _duel_insert(self, c, a: int, b: int, mode: str, qs: list[dict], now: datetime) -> str:
        lessons = sorted({x["dars"] for x in qs})
        for _ in range(50):
            did = new_code(10)
            try:
                c.execute("""INSERT INTO duels(id, a_id, b_id, mode, lessons, questions, created_at, expires_at, status)
                             VALUES (?,?,?,?,?,?,?,?, 'faol')""",
                          (did, a, b, mode, json.dumps(lessons), json.dumps(qs, separators=(",", ":")), iso(now),
                           iso(now + timedelta(seconds=config.DUEL_MUDDAT))))
                return did
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("duel id")

    def duel_new_random(self, uid: int, pool: dict, now: datetime, rng=None) -> str:
        """Tasodifiy raqib: oxirgi 7 kunda kirgan, bloklamagan, kamida bitta testli darsni ikkalasi ham tugatgan,
        bu o'quvchi bilan tugallanmagan dueli yo'q va 24 soat ichida tasodifiy juftlik bo'lmagan o'quvchi.
        Eng yaqinda faol 30 nomzoddan eng kam band (o'ynamagan duellari kam) 5 tasi orasidan tasodifiy tanlanadi."""
        rng = rng or random.SystemRandom()
        with self._c(True) as c:
            mine = self._tested_done(c, uid, pool)
            if not mine:
                raise Xato(409, XATO_DUEL_SHART)
            self._duel_check_limits(c, uid, now)
            p = self._duel_params(uid, now)
            p.update({"since": iso(now - timedelta(days=config.DUEL_FAOL_KUN)),
                      "rep": iso(now - timedelta(seconds=config.DUEL_TAKROR)), "lim": config.DUEL_NOMZOD})
            names = []
            for i, n in enumerate(mine):
                p[f"l{i}"] = n
                names.append(f":l{i}")
            cands = [r[0] for r in c.execute(f"""
                SELECT u.id FROM users u
                WHERE u.last_seen >= :since AND u.id != :me AND u.blocked = 0
                  AND EXISTS (SELECT 1 FROM lessons l WHERE l.user_id = u.id AND l.done_at IS NOT NULL
                              AND l.dars IN ({",".join(names)}))
                  AND NOT EXISTS (SELECT 1 FROM duels d
                                  WHERE ((d.a_id = :me AND d.b_id = u.id) OR (d.a_id = u.id AND d.b_id = :me))
                                    AND (({DUEL_FAOL_SQL}) OR (d.mode = 'random' AND d.created_at >= :rep)))
                ORDER BY u.last_seen DESC, u.id LIMIT :lim""", p)]
            if not cands:
                raise Xato(409, XATO_DUEL_RAQIB)
            q = ",".join("?" * len(cands))
            busy = {r[0]: r[1] for r in c.execute(f"""
                SELECT uid, COUNT(*) FROM (
                  SELECT d.b_id AS uid FROM duels d WHERE d.b_id IN ({q}) AND d.b_done IS NULL AND d.status='faol' AND d.expires_at > ?
                  UNION ALL
                  SELECT d.a_id FROM duels d WHERE d.a_id IN ({q}) AND d.a_done IS NULL AND d.status='faol' AND d.expires_at > ?)
                GROUP BY uid""", (*cands, iso(now), *cands, iso(now)))}
            order = sorted(range(len(cands)), key=lambda i: (busy.get(cands[i], 0), i))
            head = order[:config.DUEL_TANLOV]
            rng.shuffle(head)
            mine_set = set(mine)
            for i in head + order[config.DUEL_TANLOV:]:
                rival = cands[i]
                common = mine_set & self._done_set(c, rival)
                qs = self._pick_questions(common, pool, rng)
                if qs:
                    return self._duel_insert(c, uid, rival, "random", qs, now)
            raise Xato(409, XATO_DUEL_RAQIB)

    def duel_invite_create(self, uid: int, pool: dict, now: datetime) -> tuple[str, str]:
        """Do'stga duel havolasi (bir martalik, 24 soat). (code, expires_at)."""
        with self._c(True) as c:
            if not self._tested_done(c, uid, pool):
                raise Xato(409, XATO_DUEL_SHART)
            self._duel_check_limits(c, uid, now)
            exp = iso(now + timedelta(seconds=config.DUEL_TAKLIF_MUDDAT))
            for _ in range(50):
                code = new_code(10)
                try:
                    c.execute("INSERT INTO duel_invites(code, from_id, created_at, expires_at) VALUES (?,?,?,?)",
                              (code, uid, iso(now), exp))
                    return code, exp
                except sqlite3.IntegrityError:
                    continue
        raise RuntimeError("duel kodi")

    def duel_invite_get(self, code: str):
        """Bot uchun: havola qatori + taklif qilgan ismi (yoki None)."""
        if not isinstance(code, str) or not DUEL_ID_RE.fullmatch(code):
            return None
        with self._c() as c:
            return c.execute("""SELECT i.*, u.first_name, u.last_name, u.username FROM duel_invites i
                                LEFT JOIN users u ON u.id = i.from_id WHERE i.code=?""", (code,)).fetchone()

    def duel_invites_open(self, uid: int, now: datetime) -> list:
        with self._c() as c:
            return c.execute("""SELECT code, created_at, expires_at FROM duel_invites
                                WHERE from_id=? AND used_by IS NULL AND expires_at > ? ORDER BY created_at DESC""",
                             (uid, iso(now))).fetchall()

    def duel_accept(self, uid: int, code: str, pool: dict, now: datetime, rng=None) -> tuple[str, bool]:
        """Do'st havolasini qabul qilish: a = taklif qilgan, b = shu o'quvchi. (duel_id, yangi_yaratildimi).
        Shu o'quvchi havolani qayta ochsa - o'sha duel qaytariladi (ilova qayta yuklanganda ham xato bo'lmaydi)."""
        rng = rng or random.SystemRandom()
        with self._c(True) as c:
            r = c.execute("SELECT * FROM duel_invites WHERE code=?", (code,)).fetchone()
            if not r:
                raise Xato(410, XATO_TAKLIF_ESKI)
            if r["from_id"] == uid:
                raise Xato(400, XATO_TAKLIF_OZI)
            if r["used_by"] == uid and r["duel_id"]:
                return r["duel_id"], False
            if r["used_by"] is not None or r["expires_at"] <= iso(now):
                raise Xato(410, XATO_TAKLIF_ESKI)
            common = set(self._tested_done(c, uid, pool)) & self._done_set(c, r["from_id"])
            qs = self._pick_questions(common, pool, rng)
            if not qs:
                raise Xato(409, XATO_DUEL_UMUMIY)
            did = self._duel_insert(c, r["from_id"], uid, "friend", qs, now)
            cur = c.execute("UPDATE duel_invites SET used_by=?, duel_id=? WHERE code=? AND used_by IS NULL", (uid, did, code))
            if cur.rowcount != 1:
                raise Xato(410, XATO_TAKLIF_ESKI)  # (bir vaqtda ikki kishi) - tranzaksiya bekor qilinadi
            return did, True

    def duel_get(self, did: str, uid: int | None = None):
        """Duel qatori (ismlar bilan); uid berilsa - faqat shu o'quvchi ishtirok etgan bo'lsa."""
        if not isinstance(did, str) or not DUEL_ID_RE.fullmatch(did):
            return None
        with self._c() as c:
            r = c.execute(f"{self._DUEL_SELECT} WHERE d.id=?", (did,)).fetchone()
        if r is None or (uid is not None and uid not in (r["a_id"], r["b_id"])):
            return None
        return r

    @staticmethod
    def duel_view(r, uid: int, now: datetime) -> str:
        """O'quvchi nuqtai nazaridan holat: sizning_navbat | raqib_navbati | tugadi | muddati_otdi."""
        now_s, win_s = iso(now), duel_window_start(now)
        me = "a" if r["a_id"] == uid else "b"
        eff = duel_effective(r, now_s, win_s)
        if eff != "faol":
            return eff
        if r[me + "_done"]:
            return "raqib_navbati"
        if r["expires_at"] <= now_s and not (r[me + "_started"] and r[me + "_started"] > win_s):
            return "muddati_otdi"   # raqib hali o'ynayapti (oxirgi 105 s), lekin bu o'quvchi endi boshlay olmaydi
        return "sizning_navbat"

    @staticmethod
    def _late(r, p: str) -> bool:
        a, b = parse_iso(r[p + "_started"]), parse_iso(r[p + "_done"])
        return bool(a and b and (b - a).total_seconds() > config.DUEL_OYNA)

    @classmethod
    def duel_item(cls, r, uid: int, now: datetime) -> dict:
        me = "a" if r["a_id"] == uid else "b"
        ot = "b" if me == "a" else "a"
        st = cls.duel_view(r, uid, now)
        done = st == "tugadi"
        result = None
        xp = 0
        if done:
            if r["winner_id"] is None:
                result, xp = "durrang", config.XP_DUEL_DURRANG
            elif r["winner_id"] == uid:
                result, xp = "yutdi", config.XP_DUEL_YUTUQ
            else:
                result = "yutqazdi"
        try:
            lessons = json.loads(r["lessons"])
            n = len(json.loads(r["questions"]))
        except (TypeError, ValueError):
            lessons, n = [], 0
        return {
            "id": r["id"], "mode": r["mode"],
            "rival": {"id": r[ot + "_id"], "name": short_name(r[ot + "_fn"], r[ot + "_ln"], r[ot + "_un"])},
            "me_role": me, "status": st,
            "my": ({"correct": r[me + "_correct"], "ms": r[me + "_ms"], "late": cls._late(r, me)} if r[me + "_done"] else None),
            "their": ({"correct": r[ot + "_correct"], "ms": r[ot + "_ms"]} if done else None),
            "result": result, "xp": xp, "created_at": r["created_at"], "expires_at": r["expires_at"],
            "finished_at": r["finished_at"] if done else None,
            "lessons": lessons, "n": n, "started": bool(r[me + "_started"]), "rival_done": bool(r[ot + "_done"]),
        }

    def duels_for(self, uid: int, now: datetime, limit: int = 30) -> list:
        """Oxirgi duellar: tugallanmaganlari birinchi (avval "sizning navbatingiz"), keyin yangisi birinchi."""
        p = self._duel_params(uid, now)
        p["lim"] = limit
        with self._c() as c:
            rows = c.execute(f"""{self._DUEL_SELECT}
                                 WHERE d.id IN (SELECT id FROM duels WHERE a_id=:me UNION ALL SELECT id FROM duels WHERE b_id=:me)
                                 ORDER BY CASE WHEN {DUEL_FAOL_SQL} THEN 0 ELSE 1 END, d.created_at DESC, d.id
                                 LIMIT :lim""", p).fetchall()
        return rows

    def duel_stats(self, uid: int) -> dict:
        with self._c() as c:
            r = c.execute("""SELECT COUNT(*) AS played, COALESCE(SUM(winner_id = :me), 0) AS won,
                                    COALESCE(SUM(winner_id IS NULL), 0) AS draw
                             FROM duels WHERE status='tugadi'
                               AND id IN (SELECT id FROM duels WHERE a_id=:me UNION ALL SELECT id FROM duels WHERE b_id=:me)""",
                          {"me": uid}).fetchone()
        played, won, draw = r["played"], r["won"], r["draw"]
        return {"played": played, "won": won, "lost": played - won - draw, "draw": draw}

    def duel_pending(self, uid: int, now: datetime) -> int:
        """Shu o'quvchining navbati bo'lgan duellar soni (ilovadagi belgi uchun)."""
        p = self._duel_params(uid, now)
        with self._c() as c:
            return c.execute("""SELECT
                (SELECT COUNT(*) FROM duels WHERE a_id=:me AND a_done IS NULL AND status='faol' AND (expires_at > :now OR a_started > :win))
              + (SELECT COUNT(*) FROM duels WHERE b_id=:me AND b_done IS NULL AND status='faol' AND (expires_at > :now OR b_started > :win))""",
                             p).fetchone()[0]

    def duel_start(self, uid: int, did: str, now: datetime):
        """O'yinni boshlash (idempotent: qayta chaqirilsa o'sha savollar, boshlanish vaqti o'zgarmaydi). (qator, 'a'|'b')."""
        now_s = iso(now)
        with self._c(True) as c:
            r = c.execute("SELECT * FROM duels WHERE id=? AND (a_id=? OR b_id=?)", (did, uid, uid)).fetchone()
            if not r:
                raise Xato(404, XATO_DUEL_TOPILMADI)
            me = "a" if r["a_id"] == uid else "b"
            if r[me + "_done"]:
                raise Xato(409, XATO_DUEL_OYNADI)
            if self.duel_view(r, uid, now) != "sizning_navbat":
                raise Xato(410, XATO_DUEL_MUDDAT)
            if not r[me + "_started"]:
                c.execute(f"UPDATE duels SET {me}_started=? WHERE id=? AND {me}_started IS NULL", (now_s, did))
                r = c.execute("SELECT * FROM duels WHERE id=?", (did,)).fetchone()
        return r, me

    def duel_finish(self, uid: int, did: str, answers: list[dict], keys: list, now: datetime) -> dict:
        """Javoblarni yozadi; ikkinchi o'yinchi tugatganda natija va ball (aniq bir marta: shartli UPDATE).
        -> {"row", "me", "xp", "resolved": bool, "late", "oks"}"""
        now_s = iso(now)
        with self._c(True) as c:
            r = c.execute("SELECT * FROM duels WHERE id=? AND (a_id=? OR b_id=?)", (did, uid, uid)).fetchone()
            if not r:
                raise Xato(404, XATO_DUEL_TOPILMADI)
            me = "a" if r["a_id"] == uid else "b"
            if r[me + "_done"]:
                raise Xato(409, XATO_DUEL_OYNADI)
            if not r[me + "_started"]:
                raise Xato(409, XATO_DUEL_BOSHLANMAGAN)
            if self.duel_view(r, uid, now) != "sizning_navbat":
                raise Xato(410, XATO_DUEL_MUDDAT)
            started = parse_iso(r[me + "_started"])
            late = (now - started).total_seconds() > config.DUEL_OYNA
            correct, ms, oks = duel_score(keys, answers, late)
            cur = c.execute(f"""UPDATE duels SET {me}_done=?, {me}_answers=?, {me}_correct=?, {me}_ms=?
                                WHERE id=? AND {me}_done IS NULL AND {me}_started IS NOT NULL AND status='faol'""",
                            (now_s, json.dumps(answers, separators=(",", ":")), correct, ms, did))
            if cur.rowcount != 1:
                raise Xato(409, XATO_DUEL_OYNADI)
            r = c.execute("SELECT * FROM duels WHERE id=?", (did,)).fetchone()
            xp_me = 0
            resolved = False
            if r["a_done"] and r["b_done"]:
                w = duel_winner(r["a_correct"], r["a_ms"], r["b_correct"], r["b_ms"])
                wid = r[w + "_id"] if w else None
                cur = c.execute("UPDATE duels SET status='tugadi', winner_id=?, finished_at=? WHERE id=? AND status='faol'",
                                (wid, now_s, did))
                if cur.rowcount == 1:
                    resolved = True
                    for pl in ("a", "b"):
                        ot = "b" if pl == "a" else "a"
                        x = config.XP_DUEL_DURRANG if w is None else (config.XP_DUEL_YUTUQ if w == pl else 0)
                        self._add_xp(c, r[pl + "_id"], x, now)
                        c.execute("INSERT INTO events(user_id, kind, ref, xp, at, info) VALUES (?, 'duel_done', ?, ?, ?, ?)",
                                  (r[pl + "_id"], did, x, now_s, f"{r[pl + '_correct']}:{r[ot + '_correct']}"))
                        if pl == me:
                            xp_me = x
        return {"row": self.duel_get(did), "me": me, "xp": xp_me, "resolved": resolved, "late": late, "oks": oks}

    def duels_expire(self, now: datetime) -> int:
        """Soatlik vazifa: 24 soatda tugamagan duellarni 'muddati_otdi' deb belgilaydi (ball yo'q, xabar yo'q).
        Hozir o'ynayotgan o'yinchining 105 s oynasi tugashi kutiladi."""
        with self._c(True) as c:
            cur = c.execute("""UPDATE duels SET status='muddati_otdi', finished_at=expires_at
                               WHERE status='faol' AND expires_at <= :now
                                 AND (a_started IS NULL OR a_done IS NOT NULL OR a_started <= :win)
                                 AND (b_started IS NULL OR b_done IS NOT NULL OR b_started <= :win)""",
                            {"now": iso(now), "win": duel_window_start(now)})
            return cur.rowcount

    # ------------------------------------------------------------ do'st taklifi (SPEC 11.1)
    def ref_code(self, uid: int) -> str:
        """Shaxsiy taklif kodi (8 belgi [a-z0-9]); birinchi so'rovda yaratiladi."""
        with self._c(True) as c:
            r = c.execute("SELECT code FROM ref_codes WHERE user_id=?", (uid,)).fetchone()
            if r:
                return r[0]
            for _ in range(50):
                code = new_code(8)
                try:
                    c.execute("INSERT INTO ref_codes(user_id, code) VALUES (?,?)", (uid, code))
                    return code
                except sqlite3.IntegrityError:
                    continue
        raise RuntimeError("taklif kodi")

    def ref_link(self, invitee_id: int, code: str, now: datetime) -> int | None:
        """Yangi o'quvchini taklif qilganga bog'laydi (bot /start ref_<kod>; faqat yangi o'quvchi uchun chaqiriladi).
        O'zini taklif qilish, noma'lum kod, allaqachon bog'langan - e'tiborsiz (None). Muvaffaqiyat - taklif qilgan id."""
        if not isinstance(code, str) or not REF_RE.fullmatch(code):
            return None
        with self._c(True) as c:
            r = c.execute("SELECT user_id FROM ref_codes WHERE code=?", (code,)).fetchone()
            if not r or r[0] == invitee_id:
                return None
            cur = c.execute("INSERT OR IGNORE INTO referrals(invitee_id, inviter_id, at) VALUES (?,?,?)",
                            (invitee_id, r[0], iso(now)))
            return r[0] if cur.rowcount == 1 else None

    def referrals_of(self, uid: int, limit: int = 100) -> tuple[list[dict], int, int, int]:
        """(do'stlar ro'yxati, jami taklif qilinganlar, bonus berilganlar, taklifdan olingan ball)."""
        with self._c() as c:
            rows = c.execute("""SELECT r.invitee_id, r.at, r.rewarded_at, u.first_name, u.last_name, u.username, u.joined_at,
                                  EXISTS (SELECT 1 FROM lessons l WHERE l.user_id = r.invitee_id AND l.dars = 1
                                          AND l.done_at IS NOT NULL) AS done1
                                FROM referrals r LEFT JOIN users u ON u.id = r.invitee_id
                                WHERE r.inviter_id=? ORDER BY r.at DESC, r.invitee_id LIMIT ?""", (uid, limit)).fetchall()
            total, rewarded = c.execute("SELECT COUNT(*), COUNT(rewarded_at) FROM referrals WHERE inviter_id=?",
                                        (uid,)).fetchone()
            earned = c.execute("SELECT COALESCE(SUM(xp), 0) FROM events WHERE user_id=? AND kind='taklif_bonus'",
                               (uid,)).fetchone()[0]
        friends = [{"name": short_name(r["first_name"], r["last_name"], r["username"]), "joined_at": r["joined_at"] or r["at"],
                    "done1": bool(r["done1"]), "rewarded": r["rewarded_at"] is not None} for r in rows]
        return friends, total, rewarded, earned

    # ------------------------------------------------------------ admin panel: duellar va takliflar (SPEC 11.5)
    def duels_report(self, now: datetime, days: int = 30) -> dict:
        since = self._since(now, days)
        today = today_of(now)
        p = {"since": since, "now": iso(now), "win": duel_window_start(now)}
        total = finished_n = draws = rnd = 0
        players: set[int] = set()
        created: dict[str, int] = {}
        played: dict[int, int] = {}
        won: dict[int, int] = {}
        with self._c() as c:
            # bitta o'tish, qoplovchi indeks (duels_hisob) bilan - jadval qatorlariga murojaat yo'q
            for day, status, mode, wid, a, b in c.execute(
                    """SELECT substr(created_at, 1, 10), status, mode, winner_id, a_id, b_id FROM duels
                       WHERE created_at >= :since""", p):
                total += 1
                rnd += mode == "random"
                created[day] = created.get(day, 0) + 1
                players.add(a)
                players.add(b)
                if status == "tugadi":
                    finished_n += 1
                    draws += wid is None
                    for x in (a, b):
                        played[x] = played.get(x, 0) + 1
                    if wid is not None:
                        won[wid] = won.get(wid, 0) + 1
            active = c.execute(f"SELECT COUNT(*) FROM duels d WHERE d.status='faol' AND d.created_at >= :since AND {DUEL_FAOL_SQL}",
                               p).fetchone()[0]
            finished = {r[0]: r[1] for r in c.execute(
                """SELECT substr(finished_at, 1, 10), COUNT(*) FROM duels WHERE status='tugadi' AND finished_at >= :since
                   GROUP BY 1""", p)}
            top_ids = sorted(played, key=lambda u: (-won.get(u, 0), -played[u], u))[:10]
            q = ",".join("?" * len(top_ids))
            names = {r["id"]: r for r in c.execute(f"SELECT id, first_name, last_name, username FROM users WHERE id IN ({q})",
                                                    top_ids)} if top_ids else {}
            recent = c.execute(f"{self._DUEL_SELECT} ORDER BY d.created_at DESC, d.id LIMIT 20").fetchall()
        daily = []
        for i in range(max(1, int(days)) - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            daily.append({"day": d, "created": created.get(d, 0), "finished": finished.get(d, 0)})

        def nm(u):
            r = names.get(u)
            return full_name(r["first_name"], r["last_name"], r["username"]) if r else full_name(None, None)
        return {"days": days, "since": since, "total": total, "finished": finished_n,
                "expired": total - finished_n - active, "active": active, "draws": draws,
                "players": len(players), "modes": {"random": rnd, "friend": total - rnd}, "daily": daily,
                "top": [{"id": u, "name": nm(u), "played": played[u], "won": won.get(u, 0)} for u in top_ids],
                "recent": [self._duel_staff_item(r, now) for r in recent]}

    @staticmethod
    def _duel_staff_item(r, now: datetime) -> dict:
        st = duel_effective(r, iso(now), duel_window_start(now))
        res = None
        if st == "tugadi":
            res = "durrang" if r["winner_id"] is None else ("a" if r["winner_id"] == r["a_id"] else "b")

        def side(p):
            return {"id": r[p + "_id"], "name": full_name(r[p + "_fn"], r[p + "_ln"], r[p + "_un"]),
                    "correct": r[p + "_correct"], "ms": r[p + "_ms"], "done": r[p + "_done"] is not None}
        try:
            lessons = json.loads(r["lessons"])
        except (TypeError, ValueError):
            lessons = []
        return {"id": r["id"], "at": r["created_at"], "mode": r["mode"], "a": side("a"), "b": side("b"), "result": res,
                "winner_id": r["winner_id"], "status": st, "finished_at": r["finished_at"] if st != "faol" else None,
                "expires_at": r["expires_at"], "lessons": lessons}

    def referrals_report(self, limit: int = 20) -> dict:
        with self._c() as c:
            agg = c.execute("SELECT COUNT(*) AS t, COUNT(rewarded_at) AS r FROM referrals").fetchone()
            earned = c.execute("SELECT COALESCE(SUM(xp), 0) FROM events WHERE kind='taklif_bonus'").fetchone()[0]
            top = c.execute("""SELECT r.inviter_id, COUNT(*) AS invited, COUNT(r.rewarded_at) AS rewarded,
                                      u.first_name, u.last_name, u.username
                               FROM referrals r LEFT JOIN users u ON u.id = r.inviter_id
                               GROUP BY r.inviter_id ORDER BY invited DESC, rewarded DESC, r.inviter_id LIMIT 10""").fetchall()
            recent = c.execute("""SELECT r.*, a.first_name AS a_fn, a.last_name AS a_ln, a.username AS a_un,
                                         b.first_name AS b_fn, b.last_name AS b_ln, b.username AS b_un
                                  FROM referrals r LEFT JOIN users a ON a.id = r.inviter_id
                                  LEFT JOIN users b ON b.id = r.invitee_id
                                  ORDER BY r.at DESC, r.invitee_id LIMIT ?""", (limit,)).fetchall()
        return {"total": agg["t"], "rewarded": agg["r"], "bonus": config.XP_TAKLIF, "earned": earned,
                "top": [{"id": r["inviter_id"], "name": full_name(r["first_name"], r["last_name"], r["username"]),
                         "invited": r["invited"], "rewarded": r["rewarded"]} for r in top],
                "recent": [{"at": r["at"], "inviter": {"id": r["inviter_id"], "name": full_name(r["a_fn"], r["a_ln"], r["a_un"])},
                            "invitee": {"id": r["invitee_id"], "name": full_name(r["b_fn"], r["b_ln"], r["b_un"])},
                            "rewarded": r["rewarded_at"] is not None, "rewarded_at": r["rewarded_at"]} for r in recent]}

    # ------------------------------------------------------------ namuna ma'lumotlar (--seed)
    def seed(self, now: datetime, kurs=None) -> None:
        """Bazani tozalab, aniq (deterministik) namuna ma'lumot bilan to'ldiradi: 4 xodim va 15 o'quvchi."""
        self.reset()
        slides_of = (lambda n: (kurs.slides(n) if kurs else 0) or 15)
        test_total = 5
        test_dars = 8
        vid, vid_dars, vid_len = "d02", 2, 1934.0
        boshqa_v: list[tuple] = []  # qolgan videolar: (id, dars, davomiylik)
        if kurs is not None:
            t = kurs.test(8)
            if t:
                test_total = len(t["savollar"])
            hamma = []
            for ls in kurs.lessons():
                for v in kurs.lesson_videos(ls):
                    dv = v.get("davomiylik")
                    hamma.append((v["id"], ls["n"], float(dv) if isinstance(dv, (int, float)) and dv > 0 else 1800.0))
            if hamma:
                (vid, vid_dars, vid_len), boshqa_v = hamma[0], hamma[1:]
        today = today_of(now)

        def answers_for(n: int, correct: int, salt: int) -> tuple[int, int, list]:
            """Savollar bo'yicha deterministik javoblar: (jami, to'g'ri, [(pick, ok)])."""
            t = kurs.test(n) if kurs is not None else None
            qs = t["savollar"] if t else [{"ok": 0, "opts": ["a", "b", "c", "d"]}] * test_total
            total = len(qs)
            correct = max(0, min(correct, total))
            rng = random.Random(salt)
            hard = n % total  # har testda bitta "qiyin" savol: eng ko'p xato shunda
            order = [i for i in rng.sample(range(total), total) if i != hard] + [hard]
            good = set(order[:correct])
            out = []
            for i, q in enumerate(qs):
                k = q.get("ok", 0) if isinstance(q, dict) else 0
                nopt = len(q.get("opts") or []) if isinstance(q, dict) else 4
                nopt = nopt or 4
                out.append((k, True) if i in good else ((k + 1 + rng.randrange(max(1, nopt - 1))) % nopt, False))
            return total, correct, out

        yol = _seed_yol()
        with self._c(True) as c:
            for sid, first, last, uname, role, ago in SEED_STAFF:
                self._staff_set(c, {"id": sid, "first_name": first, "last_name": last, "username": uname}, role,
                                None if role == "ceo" else 900001, day_start(today - timedelta(days=ago)) + timedelta(hours=9))
            for ago, sid, action, detail, hour in SEED_AUDIT:
                ism = next((f"{s[1]} {s[2]}" for s in SEED_STAFF if s[0] == sid), str(sid))
                self._audit(c, sid, action, dict(detail, _ism=ism),
                            day_start(today - timedelta(days=ago)) + timedelta(hours=hour))
            for (uid, first, last, uname, uslub, rejim, joined, active, done, partial, video, test) in SEED_STUDENTS:
                active = sorted(active, reverse=True)  # eng eskisi birinchi
                jd = today - timedelta(days=joined)
                jt = day_start(jd) + timedelta(hours=9, minutes=uid % 50)
                if joined == 0:
                    jt = min(jt, now - timedelta(minutes=40))
                    jt = max(jt, day_start(today))
                c.execute("""INSERT INTO users(id, first_name, last_name, username, language_code, joined_at, last_seen,
                             uslub, rejim, arab, eslatma, pm_ok) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                          (uid, first, last, uname, "uz", iso(jt), iso(jt), uslub, rejim,
                           "l" if uid % 4 == 0 else "m", 0 if uid % 7 == 0 else 1))
                c.execute("INSERT INTO events(user_id, kind, ref, xp, at) VALUES (?, 'join', 'bot', 0, ?)", (uid, iso(jt)))
                # harakatlar ketma-ketligi: slaydlar va dars tugatish
                acts: list[tuple] = []
                for n in range(1, done + 2):
                    k = slides_of(n) if n <= done else min(partial, slides_of(n))
                    for i in range(1, k + 1):
                        acts.append(("slide", n, i))
                    if n <= done:
                        acts.append(("done", n))
                        if n <= 3:  # 1-3-darslar mini testlari (voronka "1-dars testini yechdi" va Testlar bo'limi uchun)
                            tries_n = 1 + (uid + n) % 2
                            last_score = 5 - (uid + n) % 3
                            for j in range(tries_n):
                                acts.append(("testn", n, max(0, last_score - (tries_n - 1 - j) * 2), j))
                extra: list[tuple] = []
                if video and done >= vid_dars - 1:
                    extra.append(("video", video))
                # qolgan videolar (masalan to'liq yozuvlar): faqat darsi ochiq bo'lsa (ketma-ketlik qoidasi)
                if video == "done":
                    for j, (v2, d2, l2) in enumerate(boshqa_v):
                        if done >= d2 - 1:
                            extra.append(("video2", v2, "done" if (uid + j) % 2 == 0 else round(l2 * 0.4, 1), l2))
                if test and done >= test_dars - 1:
                    tries, best = test
                    for j in range(tries):
                        extra.append(("test", max(0, best - (tries - 1 - j))))
                # kunlarga taqsimlash
                per = max(1, -(-len(acts) // len(active)))
                last_t = jt
                n_test8 = 0
                for di, ago in enumerate(active):
                    d = today - timedelta(days=ago)
                    chunk = acts[di * per:(di + 1) * per]
                    if di == len(active) - 1:
                        chunk = acts[di * per:] + extra
                    if not chunk:
                        chunk = [("visit",)]
                    k = len(chunk)
                    if ago == 0:
                        lead = 60 + (uid % 9) * 420  # o'quvchilar bugun turli vaqtda faol bo'lsin
                        span = max(0.0, min(20.0 * k, (now - day_start(d)).total_seconds() - lead - 60))
                        times = [max(day_start(d), now - timedelta(seconds=lead + span - span * i / max(1, k)))
                                 for i in range(k)]
                    else:
                        base = day_start(d) + timedelta(hours=17, minutes=(uid * 13) % 120)
                        times = [base + timedelta(seconds=20 * i) for i in range(k)]
                    times = [max(t, jt) for t in times]
                    for a, t in zip(chunk, times):
                        if a[0] == "slide":
                            self._ev_slide(c, uid, a[1], a[2], t)
                        elif a[0] == "done":
                            self._ev_lesson_done(c, uid, a[1], slides_of(a[1]), t)
                        elif a[0] == "video":
                            v = a[1]
                            if v == "done":
                                self._ev_video_done(c, uid, vid, t, pos=vid_len)
                            else:
                                self._ev_video_pos(c, uid, vid, float(v), t)
                        elif a[0] == "video2":
                            if a[2] == "done":
                                self._ev_video_done(c, uid, a[1], t, pos=a[3])
                            else:
                                self._ev_video_pos(c, uid, a[1], float(a[2]), t)
                        elif a[0] == "test":
                            tot, cor, ans = answers_for(test_dars, a[1], uid * 31 + n_test8)
                            n_test8 += 1
                            self._ev_test_done(c, uid, test_dars, cor, tot, t, ans)
                        elif a[0] == "testn":
                            tot, cor, ans = answers_for(a[1], a[2], uid * 17 + a[1] * 5 + a[3])
                            self._ev_test_done(c, uid, a[1], cor, tot, t, ans)
                        else:
                            c.execute("INSERT OR IGNORE INTO days(user_id, day, xp) VALUES (?, ?, 0)", (uid, d.isoformat()))
                        last_t = max(last_t, t)
                last_s = self._seed_sessions(c, now, today, uid, jt, uslub, rejim, active, done, video, bool(test),
                                             vid, test_total, yol.get(uid))
                c.execute("UPDATE users SET last_seen=? WHERE id=?", (iso(max(last_t, last_s or last_t)), uid))
            self._seed_duels(c, now, today, kurs)
            self._seed_refs(c)

    def _seed_duels(self, c, now: datetime, today: date, kurs) -> None:
        """Namuna duellar (SEED_DUELS): savollar faqat ikkalasi duelgacha tugatgan, testi bor darslardan; ball va
        voqealar haqiqiy yo'l bilan bir xil (days + events 'duel_done')."""
        pool: dict[int, int] = {}
        tests: dict[int, list] = {}
        for n in range(1, 37) if kurs is None else [x["n"] for x in kurs.lessons()]:
            t = kurs.test(n) if kurs is not None else {"savollar": [{"ok": 0}] * 5}
            if t:
                pool[n], tests[n] = len(t["savollar"]), t["savollar"]

        def at(when) -> datetime:
            if when[0] == "h":
                return now - timedelta(hours=when[1])
            return day_start(today - timedelta(days=when[1])) + timedelta(hours=when[2])

        done_of: dict[int, dict[int, str]] = {}
        for r in c.execute("SELECT user_id, dars, done_at FROM lessons WHERE done_at IS NOT NULL"):
            done_of.setdefault(r["user_id"], {})[r["dars"]] = r["done_at"]
        for code, frm, when, used_by, did in SEED_DUEL_TAKLIF:
            t = at(when)
            c.execute("INSERT INTO duel_invites(code, from_id, created_at, expires_at, used_by, duel_id) VALUES (?,?,?,?,?,?)",
                      (code, frm, iso(t), iso(t + timedelta(seconds=config.DUEL_TAKLIF_MUDDAT)), used_by, did))
        for did, a, b, mode, when, ap, bp, holat in SEED_DUELS:
            created = at(when)
            cs = iso(created)
            da, db_ = done_of.get(a, {}), done_of.get(b, {})
            common = [n for n in pool if da.get(n, "~") <= cs and db_.get(n, "~") <= cs]
            rng = random.Random(did)
            qs = self._pick_questions(common, pool, rng)
            if not qs:
                raise RuntimeError(f"seed: {did} uchun umumiy tugatilgan dars yo'q")
            keys = [tests[x["dars"]][x["q"] - 1].get("ok", 0) for x in qs]
            exp = created + timedelta(seconds=config.DUEL_MUDDAT)
            c.execute("""INSERT INTO duels(id, a_id, b_id, mode, lessons, questions, created_at, expires_at, status)
                         VALUES (?,?,?,?,?,?,?,?, 'faol')""",
                      (did, a, b, mode, json.dumps(sorted({x["dars"] for x in qs})), json.dumps(qs, separators=(",", ":")),
                       cs, iso(exp)))
            fin = {}
            for side, play in (("a", ap), ("b", bp)):
                if not play:
                    continue
                correct, total_ms, after = play
                st = created + timedelta(minutes=after)
                dn = st + timedelta(seconds=total_ms // 1000 + 4)
                n = len(keys)
                order = list(range(n))
                rng.shuffle(order)
                good = set(order[:correct])
                base, rem = divmod(total_ms, n)
                msl = [base] * n
                if n >= 4:  # har xil vaqtlar, yig'indi o'zgarmaydi
                    j1, j2 = rng.randint(0, 2500), rng.randint(0, 2500)
                    msl[0], msl[1], msl[2], msl[3] = base + j1, base - j1, base + j2, base - j2
                msl[-1] += rem
                answers = [{"pick": k if i in good else (k + 1 + rng.randrange(3)) % 4, "ms": msl[i]} for i, k in enumerate(keys)]
                cor, ms, _ = duel_score(keys, answers, False)
                c.execute(f"UPDATE duels SET {side}_started=?, {side}_done=?, {side}_answers=?, {side}_correct=?, {side}_ms=? "
                          "WHERE id=?", (iso(st), iso(dn), json.dumps(answers, separators=(",", ":")), cor, ms, did))
                fin[side] = (cor, ms, dn)
            if "a" in fin and "b" in fin:
                w = duel_winner(fin["a"][0], fin["a"][1], fin["b"][0], fin["b"][1])
                t_end = max(fin["a"][2], fin["b"][2])
                c.execute("UPDATE duels SET status='tugadi', winner_id=?, finished_at=? WHERE id=?",
                          ((a if w == "a" else b) if w else None, iso(t_end), did))
                for side, uid, other in (("a", a, "b"), ("b", b, "a")):
                    x = config.XP_DUEL_DURRANG if w is None else (config.XP_DUEL_YUTUQ if w == side else 0)
                    self._add_xp(c, uid, x, t_end)
                    c.execute("INSERT INTO events(user_id, kind, ref, xp, at, info) VALUES (?, 'duel_done', ?, ?, ?, ?)",
                              (uid, did, x, iso(t_end), f"{fin[side][0]}:{fin[other][0]}"))
            elif holat == "muddati_otdi":
                c.execute("UPDATE duels SET status='muddati_otdi', finished_at=expires_at WHERE id=?", (did,))

    def _seed_refs(self, c) -> None:
        """Namuna do'st takliflari (SEED_REFS): bog'lanish = taklif qilingan qo'shilgan vaqt; bonus - u 1-darsni
        tugatgan paytda ikkalasiga +50 (haqiqiy yo'l bilan bir xil)."""
        for inviter in sorted({x[1] for x in SEED_REFS}):
            c.execute("INSERT INTO ref_codes(user_id, code) VALUES (?, ?)", (inviter, f"sd{inviter % 1000000:06d}"))
        for invitee, inviter in SEED_REFS:
            j = c.execute("SELECT joined_at FROM users WHERE id=?", (invitee,)).fetchone()[0]
            c.execute("INSERT INTO referrals(invitee_id, inviter_id, at) VALUES (?,?,?)", (invitee, inviter, j))
            l1 = c.execute("SELECT done_at FROM lessons WHERE user_id=? AND dars=1 AND done_at IS NOT NULL", (invitee,)).fetchone()
            if l1:
                self._referral_reward(c, invitee, parse_iso(l1[0]))

    # --- namuna seanslar: ekranlar va tugmalar ketma-ketligi (admin panel tahlillari uchun)
    def _seed_sessions(self, c, now: datetime, today: date, uid: int, jt: datetime, uslub, rejim, active: list,
                       done: int, video, has_test8: bool, vid: str, nq: int, yol: dict | None = None) -> datetime | None:
        rng = random.Random(uid * 7919)
        days = sorted(active, reverse=True)  # eng eskisi birinchi
        if len(days) > 8:
            days = [days[round(i * (len(days) - 1) / 7)] for i in range(8)]
        plan = [(ago, "asosiy") for ago in days]
        k = 0
        while len(plan) < 3:  # kamida 3 seans: faol kunlarga qo'shimcha (ertalabki) seanslar
            plan.append((days[k % len(days)], "ertalab"))
            k += 1
        plan.sort(key=lambda x: (-x[0], 0 if x[1] == "ertalab" else 1))
        dev_main, dev_alt = SEED_QURILMA_TANLOV.get(uid, (0, None))
        live = uid in SEED_JONLI
        rows_s, rows_e = [], []
        last_seen = None
        n_korinish = 0  # NUQTA ko'rinishi yozilgan seanslar (o'z rng si yo'q - qolgan namuna o'zgarmaydi)
        today_plan = [i for i, p in enumerate(plan) if p[0] == 0]
        for si, (ago, typ) in enumerate(plan):
            J = _Yol(rng)
            first = si == 0
            ob_day = first and (today - timedelta(days=ago)) == jt.astimezone(TZ).date()
            if ob_day and ago < SEED_KORINISH_KUN:
                self._seed_tanishuv(J, uid, rejim)   # NUQTA ilovasi tanishuvi (voronka "Tanishuvni tugatdi")
            elif ob_day and uslub:                   # eski ilova tanishuvi (uslub va rejim tanlash)
                J.screen("ob-salom")
                J.wait(3, 8)
                J.click("ob-next")
                J.screen("ob-uslub")
                J.wait(4, 12)
                J.click("ob-style", uslub)
                J.wait(1, 3)
                J.click("ob-next")
                J.screen("ob-rejim")
                J.wait(2, 6)
                J.click("ob-mode", rejim)
                J.wait(1, 2)
                J.click("ob-done")
            J.screen("bosh")
            n_les = max(1, min(done + 1, round((si + 1) / len(plan) * (done + 1))))
            journeys = ["dars"]
            if video and si == len(plan) - 2:
                journeys.append("video")
            if rng.random() < 0.45:
                journeys.append(rng.choice(["reyting", "profil", "reyting"]))
            if has_test8 and si == len(plan) - 1 and done >= 7:
                journeys = ["mashq8"] + journeys[1:]
            if yol and typ == "asosiy" and ago in yol:   # 2-bosqich: shu kungi duel / taklif yo'llari
                journeys = journeys[:1] + list(yol[ago]) + journeys[1:]
            for jn in journeys:
                if isinstance(jn, tuple):
                    self._seed_duel_yol(J, rng, jn, nq)
                elif jn == "dars":
                    J.wait(2, 8)
                    J.click("tab", "darslar")
                    J.screen("darslar")
                    J.wait(3, 12)
                    J.click("lesson", str(n_les))
                    J.screen("dars", str(n_les))
                    for _ in range(rng.randint(3, 9)):
                        J.wait(8, 35)
                        J.click("dk-next")
                    if n_les <= done and rng.random() < 0.6:
                        J.wait(2, 6)
                        J.click("dk-finish")
                        J.screen("sheet-tugadi", str(n_les))
                        J.wait(2, 5)
                        if n_les <= 3 or rng.random() < 0.3:
                            J.click("quiz", str(n_les))
                            J.screen("mashq", str(n_les))
                            self._seed_quiz(J, rng, nq)
                            J.screen("natija", str(n_les))
                            J.wait(4, 10)
                            J.click("tab", "bosh")
                            J.screen("bosh")
                        else:
                            J.click("sheet-close")
                            J.screen("dars", str(n_les))
                            J.wait(1, 3)
                            J.click("back")
                            J.screen("darslar")
                    else:
                        J.wait(1, 3)
                        J.click("back")
                        J.screen("darslar")
                elif jn == "mashq8":
                    J.wait(2, 6)
                    J.click("lesson", "8")
                    J.screen("dars", "8")
                    J.wait(5, 15)
                    J.click("back")
                    J.screen("darslar")
                    J.click("quiz", "8")
                    J.screen("mashq", "8")
                    self._seed_quiz(J, rng, nq)
                    J.screen("natija", "8")
                    J.wait(3, 8)
                    J.click("qz-retry", "8")
                    J.screen("mashq", "8")
                    self._seed_quiz(J, rng, nq)
                    J.screen("natija", "8")
                elif jn == "video":
                    J.wait(2, 6)
                    J.click("tab", "video")
                    J.screen("video")
                    J.wait(3, 9)
                    J.click("video", vid)
                    J.screen("player", vid)
                    J.wait(60, 420)
                    J.click("back")
                    J.screen("video")
                elif jn == "reyting":
                    J.wait(2, 6)
                    J.click("tab", "reyting")
                    J.screen("reyting")
                    J.wait(4, 12)
                    J.click("davr", "umumiy")
                    J.wait(3, 9)
                elif jn == "profil":
                    J.wait(2, 6)
                    J.click("tab", "profil")
                    J.screen("profil")
                    J.wait(3, 9)
                    if rng.random() < 0.5:
                        J.click("set-rejim", rng.choice(["light", "dark", "auto"]))
                    else:
                        J.click("set-arab", rng.choice(["m", "l"]))
                    J.wait(2, 5)
            is_live = live and ago == 0 and si == today_plan[-1]
            if not is_live:
                J.wait(2, 10)
                J.end()
            dur = J.t
            # vaqt oynasi
            day0 = day_start(today - timedelta(days=ago))
            lo = max(day0, jt + timedelta(seconds=20))
            if ago == 0:
                # bugungi seanslar [lo, hi_last] oralig'iga ketma-ket joylanadi; jonli seans hozirgina signal bergan
                pos, m = today_plan.index(si), len(today_plan)
                lead = 25 + (uid % 5) * 30 if live else 60 + (uid % 9) * 420
                hi_last = max(now - timedelta(seconds=lead), lo + timedelta(seconds=10 * m))
                hi_last = min(hi_last, now - timedelta(seconds=5))
                span = max(0.0, (hi_last - lo).total_seconds())
                slot_lo = lo + timedelta(seconds=span * pos / m)
                slot_hi = lo + timedelta(seconds=span * (pos + 1) / m)
                start = max(slot_lo, slot_hi - timedelta(seconds=dur))
                scale = min(1.0, max(0.0, (slot_hi - start).total_seconds()) / dur) if dur > 0 else 1.0
            else:
                base_h = 17 if typ == "asosiy" else 8
                start = max(lo, day0 + timedelta(hours=base_h, minutes=(uid * 13) % 120 if typ == "asosiy" else uid % 40)
                            - timedelta(minutes=2))
                scale = 1.0
            sid = str(_uuid4(rng))
            dvi = dev_alt if (dev_alt is not None and si % 3 == 2) else dev_main
            platform, ver, w, h, ua = SEED_QURILMALAR[dvi]
            os_, device = classify_device(platform, w, h, ua)
            scheme = rejim if rejim in ("light", "dark") else ("dark" if uid % 3 == 0 else "light")
            times = [min(now, start + timedelta(seconds=e[0] * scale)) for e in J.ev]
            n_scr = n_clk = 0
            for e, at in zip(J.ev, times):
                _, kind, name, ref, scr, d = e
                n_scr += kind == "screen"
                n_clk += kind == "click"
                if d is not None:
                    d = int(d * scale)
                rows_e.append((sid, uid, iso_ms(at), kind, name, ref, scr, d))
            ended = iso(times[-1]) if J.ev and J.ev[-1][1] == "end" else None
            # NUQTA ko'rinishi: oxirgi SEED_KORINISH_KUN kun (undan oldin - eski ilova, NULL). Aylanishdagi manzara har
            # ochilishda keyingisi; tanlagan o'quvchi (SEED_MANZARA) birinchi shunday seansdan keyin o'sha manzarada.
            # mavzu: rejim light -> kun, dark -> tun, auto -> seans boshlangan soat (06:00-18:59 kun).
            manzara = mavzu = aylan = None
            if ago < SEED_KORINISH_KUN:
                fixed = SEED_MANZARA.get(uid)
                if fixed and n_korinish >= 1:
                    manzara, aylan = fixed, 0
                else:
                    manzara, aylan = config.MANZARA_KALITLARI[(uid + si) % len(config.MANZARA_KALITLARI)], 1
                hour = times[0].astimezone(TZ).hour
                mavzu = "kun" if rejim == "light" else "tun" if rejim == "dark" else ("kun" if 6 <= hour < 19 else "tun")
                n_korinish += 1
            rows_s.append((sid, uid, iso(times[0]), iso(times[-1]), ended, platform, ver, os_, device, f"{w}x{h}", scheme,
                           uslub, rejim, ua, n_scr, n_clk, manzara, mavzu, aylan))
            last_seen = max(last_seen, times[-1]) if last_seen else times[-1]
        c.executemany("""INSERT INTO sessions(id, user_id, started_at, last_at, ended_at, platform, tg_version, os, device,
                           screen, scheme, uslub, rejim, ua, screens, clicks, manzara, mavzu, aylan)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows_s)
        c.executemany("""INSERT INTO ui_events(session_id, user_id, at, kind, name, ref, screen, dur_ms)
                         VALUES (?,?,?,?,?,?,?,?)""", rows_e)
        return last_seen

    @staticmethod
    def _seed_tanishuv(J, uid: int, rejim) -> None:
        """NUQTA ilovasi tanishuvi (web/app: salom -> ko'rinish -> qanday -> ball). Manzarani tanlaganlar (SEED_MANZARA)
        shu yerda tanlaydi; SEED_TANISHUV_SKIP "qanday" qadamida o'tkazib yuboradi, qolganlar "Boshlash" ni bosadi."""
        J.screen("ob-salom")
        J.wait(3, 8)
        J.click("ob-next")
        J.screen("ob-korinish")
        J.wait(4, 12)
        if uid in SEED_MANZARA:
            J.click("set-manzara", SEED_MANZARA[uid])
            J.wait(1, 3)
        if rejim in ("light", "dark"):
            J.click("set-rejim", rejim)
            J.wait(1, 2)
        J.click("ob-next")
        J.screen("ob-qanday")
        J.wait(3, 9)
        if uid in SEED_TANISHUV_SKIP:
            J.click("ob-skip")
            return
        J.click("ob-next")
        J.screen("ob-ball")
        J.wait(3, 8)
        J.click("ob-done")

    @staticmethod
    def _seed_duel_yol(J, rng, jn: tuple, nq: int) -> None:
        """Duellar / taklif ekranlari va tugmalari (SPEC 11.4 nomlari)."""
        kind, did = jn
        J.wait(2, 6)
        if kind == "taklif":
            J.click("tab", "profil")
            J.screen("profil")
            J.wait(2, 6)
            J.click("taklif-open")
            J.screen("taklif")
            J.wait(4, 10)
            J.click("taklif-share")
            J.wait(3, 8)
            J.click("back")
            J.screen("profil")
            J.wait(1, 3)
            J.click("tab", "bosh")
            J.screen("bosh")
            return
        J.click("duel-open")          # Bosh sahifadagi "Duel" kartasi
        J.screen("duellar")
        J.wait(2, 6)
        if kind in ("random", "friend"):
            J.click("duel-new")
            J.screen("sheet-duel-yangi")
            J.wait(2, 5)
        if kind == "friend":
            J.click("duel-friend")
            J.wait(1, 3)
            J.click("duel-share")
            J.wait(2, 5)
            J.screen("duellar")
        else:
            if kind == "random":
                J.click("duel-random")
            else:
                J.click("duel-open", did)
            J.screen("duel", did)
            J.wait(2, 5)
            J.click("duel-start", did)
            for _ in range(nq):
                J.wait(3, 12)
                J.click("duel-pick", str(rng.randrange(4)))
            J.wait(1, 2)
            J.screen("duel-natija", did)
            J.wait(4, 12)
            J.click("back")
            J.screen("duellar")
        J.wait(1, 4)
        J.click("back")
        J.screen("bosh")

    @staticmethod
    def _seed_quiz(J, rng, nq: int) -> None:
        for _ in range(nq):
            J.wait(4, 15)
            J.click("pick", str(rng.randrange(4)))
            J.wait(1, 3)
            J.click("qz-check")
            J.wait(2, 7)
            J.click("qz-next")


class _Yol:
    """Namuna seans uchun voqealar ketma-ketligi (soniyalarda nisbiy vaqt)."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.t = 0.0
        self.ev: list[tuple] = []
        self.cur: str | None = None
        self.cur_t = 0.0

    def wait(self, a: float, b: float) -> None:
        self.t += self.rng.uniform(a, b)

    def screen(self, name: str, ref: str | None = None) -> None:
        self.t += self.rng.uniform(0.3, 1.2)
        d = int((self.t - self.cur_t) * 1000) if self.cur else None
        self.ev.append((self.t, "screen", name, ref, self.cur, d))
        self.cur, self.cur_t = name, self.t

    def click(self, name: str, ref: str | None = None) -> None:
        self.ev.append((self.t, "click", name, ref, self.cur, None))

    def end(self) -> None:
        self.ev.append((self.t, "end", self.cur or "end", None, self.cur, int((self.t - self.cur_t) * 1000)))


def _uuid4(rng: random.Random):
    import uuid
    return uuid.UUID(int=rng.getrandbits(128), version=4)


# namuna qurilmalar: (platform, Telegram versiyasi, eni, bo'yi, UA)
SEED_QURILMALAR = [
    ("android", "8.0", 412, 915, "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/129.0.0.0 Mobile Safari/537.36"),
    ("android", "7.10", 393, 873, "Mozilla/5.0 (Linux; Android 13; 23021RAAEG) AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/128.0.0.0 Mobile Safari/537.36"),
    ("ios", "8.0", 390, 844, "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 "
                             "(KHTML, like Gecko) Mobile/15E148"),
    ("android", "8.0", 800, 1280, "Mozilla/5.0 (Linux; Android 13; SM-X200) AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/129.0.0.0 Safari/537.36"),
    ("ios", "7.10", 820, 1180, "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                               "Mobile/15E148"),
    ("tdesktop", "8.0", 384, 694, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/129.0.0.0 Safari/537.36"),
    ("macos", "8.0", 384, 694, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)"),
    ("weba", "8.0", 1280, 720, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/129.0.0.0 Safari/537.36"),
]
# o'quvchi -> (asosiy qurilma, ikkinchi qurilma | None); ikkinchisi har 3-seansda
SEED_QURILMA_TANLOV = {
    800001: (0, 5), 800002: (2, None), 800003: (1, 6), 800004: (0, None), 800005: (5, 0), 800006: (2, None),
    800007: (1, None), 800008: (3, 2), 800009: (0, 7), 800010: (4, None), 800011: (1, None), 800012: (2, None),
    800013: (7, None), 800014: (0, None), 800015: (1, None),
}
SEED_JONLI = {800001, 800003, 800011}   # bugungi seansi hali ochiq ("hozir faol")
# NUQTA ko'rinishi (05.10): seanslarda faqat oxirgi shuncha kunda; o'quvchi -> tanlagan manzarasi (qolganlari aylanishda)
SEED_KORINISH_KUN = 7
SEED_MANZARA = {800002: "voha", 800003: "shom", 800005: "xattot", 800008: "qahva", 800010: "sahro", 800012: "voha"}
# NUQTA davrida qo'shilganlar (SEED_KORINISH_KUN) birinchi seansda NUQTA tanishuvini o'tadi; bular "qanday" qadamida
# "O'tkazib yuborish" ni bosadi (ob-skip), qolganlari "Boshlash" (ob-done). 800012 va 800015 da uslub yo'q -
# voronkada "Tanishuvni tugatdi" ga faqat shu tugmalar bilan kiradi.
SEED_TANISHUV_SKIP = {800011, 800015}
# amallar jurnali: (necha kun oldin, xodim, amal, tafsilot, soat) - vaqt tartibida
SEED_AUDIT = [
    (20, 900001, "invite", {"role": "admin"}, 8.5),
    (15, 900001, "invite", {"role": "ustoz"}, 8.5),
    (10, 900001, "invite", {"role": "assistent"}, 8.5),
    (5, 900002, "open", {"from": 30, "to": 36}, 10.0),
    (2, 900001, "feature", {"key": "reyting", "on": False}, 11.0),
    (2, 900001, "feature", {"key": "reyting", "on": True}, 12.0),
    (1, 900003, "kirish", {}, 18.0),
]

# 2-bosqich (SPEC 11): namuna duellar - har holat bor. (id, a, b, rejim, vaqt, a_o'yini, b_o'yini, bazadagi holat)
# vaqt: ("d", necha kun oldin, soat) yoki ("h", necha soat oldin); o'yin: (to'g'ri, jami ms, yaratilgandan necha daqiqa keyin)
# Savollar faqat ikkalasi ham duel vaqtigacha tugatgan darslardan olinadi (seed buni tekshiradi).
SEED_DUELS = [
    ("seedduel10", 800002, 800005, "random", ("d", 6, 17.8), (2, 52000, 3), (5, 36000, 25), "tugadi"),    # Dilshod yutdi
    ("seedduel01", 800002, 800003, "random", ("d", 3, 17.5), (4, 38000, 4), (3, 45000, 35), "tugadi"),    # Jahongir yutdi
    ("seedduel02", 800005, 800002, "friend", ("d", 2, 17.2), (3, 42000, 3), (3, 42000, 50), "tugadi"),    # durrang
    ("seedduel04", 800001, 800008, "friend", ("d", 2, 17.4), (3, 47100, 3), (5, 33600, 40), "tugadi"),    # Nilufar yutdi
    ("seedduel08", 800010, 800012, "friend", ("d", 2, 19.3), (2, 51000, 5), None, "muddati_otdi"),        # muddati o'tdi
    ("seedduel09", 800001, 800004, "random", ("d", 2, 18.3), (4, 39900, 2), None, "faol"),                # muddati o'tgan
    # (bazada hali 'faol' - soatlik vazifa belgilaydi; API hozirdanoq "muddati_otdi" ko'rsatadi)
    ("seedduel03", 800003, 800001, "random", ("d", 1, 17.0), (4, 41200, 2), (4, 38750, 30), "tugadi"),    # teng: Aziza tezroq
    ("seedduel06", 800006, 800009, "random", ("h", 3.0), None, None, "faol"),                            # ikkalasi o'ynamagan
    ("seedduel05", 800005, 800001, "random", ("h", 2.0), (4, 40100, 3), None, "faol"),                   # Aziza navbati
    ("seedduel07", 800001, 800003, "friend", ("h", 1.0), (3, 44000, 2), None, "faol"),                   # Malika navbati
]
# do'st havolalari: (kod, kimdan, vaqt, kim ishlatdi, duel)
SEED_DUEL_TAKLIF = [
    ("seedinv002", 800005, ("d", 2, 17.15), 800002, "seedduel02"),
    ("seedinv003", 800001, ("d", 2, 17.35), 800008, "seedduel04"),
    ("seedinv005", 800010, ("d", 2, 19.25), 800012, "seedduel08"),
    ("seedinv004", 800001, ("h", 1.1), 800003, "seedduel07"),
    ("seedinv006", 800003, ("d", 2, 19.0), None, None),             # ishlatilmagan, muddati o'tgan
    ("seedinv001", 800005, ("h", 0.5), None, None),                 # ochiq havola (Dilshod)
]
# do'st takliflari: (taklif qilingan, taklif qilgan) - bonus taklif qilingan 1-darsni tugatgan paytda
SEED_REFS = [(800014, 800001), (800015, 800001), (800012, 800002), (800011, 800002), (800009, 800005)]


def _seed_yol() -> dict[int, dict[int, list]]:
    """Namuna seanslarga qo'shiladigan duel/taklif yo'llari: {o'quvchi: {necha kun oldin: [(tur, duel), ...]}}."""
    out: dict[int, dict[int, list]] = {}

    def add(uid, ago, j):
        out.setdefault(uid, {}).setdefault(ago, []).append(j)
    for did, a, b, mode, when, ap, bp, _ in SEED_DUELS:
        ago = when[1] if when[0] == "d" else 0
        if ap:
            if mode == "friend":
                add(a, ago, ("friend", did))
            add(a, ago, ("random", did) if mode == "random" else ("play", did))
        if bp:
            add(b, ago, ("play", did))
    for invitee, inviter in SEED_REFS:
        s = next(x for x in SEED_STUDENTS if x[0] == invitee)
        add(inviter, s[6], ("taklif", None))
    return out


SEED_STAFF = [
    (900001, "Muhammad", "Amin", "muhammad_amin", "ceo", 30),
    (900002, "Nodira", "Salimova", "nodira_s", "admin", 20),
    (900003, "Dilnoza", "Karimova", "dilnoza_k", "ustoz", 15),
    (900004, "Bekzod", "Aliyev", "bekzod_a", "assistent", 10),
]

# id, ism, familiya, username, uslub, rejim, necha kun oldin qo'shilgan, faol kunlar (0 = bugun),
# tugatilgan darslar soni, keyingi darsda ko'rilgan slaydlar, video ("done" | pozitsiya | None), test (urinish, eng yaxshi)
SEED_STUDENTS = [
    (800001, "Aziza", "Karimova", "aziza_k", None, "auto", 13, [13, 12, 11, 10, 9, 2, 1, 0], 7, 3, 312.5, (2, 4)),
    (800002, "Jahongir", "Rasulov", "jahongir_r", "game", "light", 13, [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1], 12, 5, "done", (1, 5)),
    (800003, "Malika", "Tursunova", "malika_t", "glass", "dark", 12, [11, 10, 8, 7, 5, 4, 3, 1, 0], 9, 2, "done", (2, 3)),
    (800004, "Sardor", "Toshmatov", "sardor_t", "game", "auto", 11, [10, 9, 8, 6, 5, 2, 1], 5, 4, "done", None),
    (800005, "Dilshod", "Ergashev", "dilshod_e", "glass", "light", 10, [9, 8, 7, 6, 5, 4, 3, 2, 1, 0], 10, 0, "done", (3, 4)),
    (800006, "Gulnoza", "Mirzayeva", "gulnoza_m", "game", "dark", 9, [8, 7, 6, 3, 2, 0], 4, 6, 640.0, None),
    (800007, "Bobur", "Xolmatov", "bobur_x", None, "auto", 13, [13, 12, 11], 2, 3, None, None),
    (800008, "Nilufar", "Saidova", "nilufar_s", "glass", "auto", 7, [6, 5, 4, 3, 2, 1], 8, 1, "done", (1, 2)),
    (800009, "Otabek", "Nazarov", "otabek_n", "game", "light", 6, [6, 4, 2, 0], 3, 5, None, None),
    (800010, "Shahnoza", "Umarova", "shahnoza_u", "game", "auto", 5, [5, 4, 3, 2, 1], 6, 2, 1210.0, None),
    (800011, "Jasur", "", "jasur_o", "glass", "dark", 4, [4, 3, 0], 2, 0, None, None),
    (800012, "Madina", "Sobirova", "madina_s", None, "auto", 3, [3, 2, 1], 3, 7, None, None),
    (800013, "Sherzod", "Usmonov", None, "game", "dark", 12, [12, 9], 1, 8, None, None),
    (800014, "Kamola", "Yo'ldosheva", "kamola_y", "glass", "light", 1, [1, 0], 1, 2, None, None),
    (800015, "Temur", "Alimov", "temur_a", None, "auto", 0, [0], 0, 4, None, None),
]

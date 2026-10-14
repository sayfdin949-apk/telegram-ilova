"""aiohttp ilovasi: statik fayllar, demo panellar (token + inyeksiya), video (Range), talaba va xodim API.

Server faqat 127.0.0.1 da tinglaydi; tashqariga faqat cloudflared tunnel orqali chiqadi.
Barcha javoblarda: X-Content-Type-Options: nosniff, Referrer-Policy: no-referrer.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import re
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

from aiohttp import web

import auth
import config
import student_bot
import yorliqlar
from db import (DUEL_ID_RE, TRACK_KINDS, XATO_DUEL_SHART, Store, Xato, duel_score, iso, now_tz, parse_iso, short_name,
                today_of)
from kurs import VID_RE, Kurs

log = logging.getLogger("noon.web")

MIME = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8", ".map": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".svg": "image/svg+xml", ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".ico": "image/x-icon", ".avif": "image/avif",
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".pdf": "application/pdf",
}
# rasmlar, shriftlar, video - uzoq kesh; html/js/css/json/svg (ikon to'plami ham) - har safar tekshiriladi
LONG_CACHE = {".webp", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".avif", ".woff2", ".woff", ".ttf", ".otf",
              ".mp4", ".webm", ".mp3"}
CACHE_LONG = "public, max-age=604800"
CACHE_REVALIDATE = "no-cache"
RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {f"COM{i}" for i in range(10)} | {f"LPT{i}" for i in range(10)}

HEAD_INJECT = ('<meta name="referrer" content="no-referrer">'
               '<link rel="preload" href="/staff/adapter.js" as="script">'  # adapter erta yuklansin (rejim "miltillamasin")
               '<script src="https://telegram.org/js/telegram-web-app.js?59"></script>')
BODY_INJECT = '<script src="/staff/adapter.js"></script>'

XATO_KIRISH_T = "Kirish tasdiqlanmadi. Ilovani bot orqali qayta oching."
XATO_KIRISH_X = "Kirish tasdiqlanmadi. Boshqaruvni xodimlar boti orqali qayta oching."
XATO_KIRISH_A = "Kirish muddati tugagan. Xodimlar botiga /kirish deb yozing."
XATO_XODIM = "Bu bo'lim faqat xodimlar uchun"
XATO_RUXSAT = "Bu amal uchun ruxsatingiz yo'q"
XATO_BOLIM = "Bu bo'lim sizga ochiq emas"
XATO_FUNKSIYA = "Bu funksiya hozircha o'chirilgan"
XATO_CSRF = "So'rov rad etildi (xavfsizlik tekshiruvi). Sahifani yangilab, qayta urinib ko'ring."
XATO_KOP = "Juda ko'p so'rov. Birozdan keyin qayta urinib ko'ring."

SID_RE = re.compile(r"^[0-9a-f-]{36}$")
KALIT_RE = re.compile(r"^[a-z0-9_-]{1,40}$")

KIRISH_ESKI_HTML = """<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>Havola eskirgan</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;
font-family:"Be Vietnam Pro",system-ui,sans-serif;color:#0D3A1A;
background:radial-gradient(circle at 30% 20%,#D7F1D2,#E3F2E2 45%,#EAF4EA)}
.k{background:#fff;border:1px solid #D5E6D3;border-radius:16px;box-shadow:0 8px 24px rgba(13,58,26,.08);
padding:28px 24px;max-width:420px;width:100%}h1{font-size:20px;margin:0 0 10px}
.t{width:78px;height:6px;border-radius:3px;background:linear-gradient(135deg,#6AEF5A,#3DCB36 55%,#2EB82E);margin:0 0 16px}
p{margin:0;color:#3A6040;line-height:1.55}b{color:#0D3A1A}</style></head>
<body><div class="k"><h1>Havola eskirgan</h1><div class="t"></div>
<p>Havola eskirgan. Xodimlar botiga <b>/kirish</b> deb yozing.</p>
<p style="margin-top:10px;color:#5A8060;font-size:14px">Kirish havolasi 10 daqiqa amal qiladi va faqat bir marta ishlaydi.</p>
</div></body></html>"""


# ---------------------------------------------------------------- yordamchilar
class Limiter:
    """Sirpanuvchi oyna: har kalitga `per` soniyada ko'pi bilan `n` ta."""

    def __init__(self, n: int, per: float):
        self.n, self.per = n, per
        self.hits: dict = {}

    def hit(self, key) -> bool:
        now = time.monotonic()
        dq = self.hits.get(key)
        if dq is None:
            dq = self.hits[key] = deque()
        while dq and now - dq[0] > self.per:
            dq.popleft()
        if len(dq) >= self.n:
            return False
        dq.append(now)
        if len(self.hits) > 20000:
            for k in [k for k, v in self.hits.items() if not v or now - v[-1] > self.per]:
                self.hits.pop(k, None)
        return True


def safe_path(root: Path, rel: str) -> Path | None:
    """URL dagi nisbiy yo'lni root ichida xavfsiz faylga aylantiradi; chiqib ketish urinishlari -> None."""
    if not rel or len(rel) > 300 or any(ch in rel for ch in ("\\", "\x00", ":")):
        return None
    parts = rel.split("/")
    for p in parts:
        if p in ("", ".", "..") or p.startswith(".") or p.endswith((".", " ")) or any(ord(ch) < 32 for ch in p):
            return None
        if p.split(".")[0].upper() in RESERVED:
            return None
    try:
        root_r = root.resolve()
        path = root_r.joinpath(*parts).resolve()
    except (OSError, ValueError):
        return None
    if path == root_r or not path.is_relative_to(root_r):
        return None
    return path


def file_response(path: Path) -> web.FileResponse:
    ext = path.suffix.lower()
    return web.FileResponse(path, headers={
        "Content-Type": MIME.get(ext, "application/octet-stream"),
        "Cache-Control": CACHE_LONG if ext in LONG_CACHE else CACHE_REVALIDATE,
    })


def need_int(d: dict, key: str, lo: int | None = None, hi: int | None = None) -> int:
    v = d.get(key)
    if isinstance(v, bool):
        v = None
    elif isinstance(v, float) and v.is_integer():
        v = int(v)
    elif isinstance(v, str) and v.strip().isdigit() and len(v.strip()) <= 9:
        v = int(v.strip())
    if not isinstance(v, int):
        raise Xato(400, f"'{key}' butun son bo'lishi kerak")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise Xato(400, f"'{key}' qiymati noto'g'ri")
    return v


def q_int(request: web.Request, key: str, default: int | None = None, lo: int | None = None, hi: int | None = None) -> int:
    """So'rov satridagi butun son (?days=14); yo'q bo'lsa - default (default None bo'lsa 400)."""
    v = (request.query.get(key) or "").strip()
    if not v:
        if default is None:
            raise Xato(400, f"'{key}' ko'rsatilmagan")
        return default
    if not v.isdigit() or len(v) > 12:
        raise Xato(400, f"'{key}' butun son bo'lishi kerak")
    n = int(v)
    if (lo is not None and n < lo) or (hi is not None and n > hi):
        raise Xato(400, f"'{key}' qiymati noto'g'ri")
    return n


def _short_str(v, key: str, limit: int = 40) -> str | None:
    """Ixtiyoriy qisqa matn (r, s): None | matn <= limit | son -> matn."""
    if v is None:
        return None
    if isinstance(v, bool):
        raise Xato(400, f"'{key}' noto'g'ri")
    if isinstance(v, (int, float)) and math.isfinite(v):
        v = str(int(v)) if float(v).is_integer() else str(v)
    if not isinstance(v, str) or len(v) > limit or any(ord(ch) < 32 for ch in v):
        raise Xato(400, f"'{key}' noto'g'ri (ko'pi bilan {limit} belgi)")
    return v or None


def norm_device(dev) -> dict:
    if not isinstance(dev, dict):
        raise Xato(400, "'device' noto'g'ri")

    def s(key, n):
        v = dev.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            v = str(v)
        return v.strip()[:n] if isinstance(v, str) and v.strip() else None

    def dim(key):
        v = dev.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 < v <= 100000:
            return None
        return int(round(v))
    def one_of(key, allowed):
        v = dev.get(key)
        v = v.strip().lower() if isinstance(v, str) else None
        return v if v in allowed else None

    platform = s("platform", 20)
    scheme = dev.get("scheme") if dev.get("scheme") in ("light", "dark") else None
    # NUQTA ko'rinishi (SPEC 10.4): noto'g'ri qiymat faqat o'sha maydonni tashlaydi (so'rov 400 bo'lmaydi)
    aylan = dev.get("aylan")
    if not isinstance(aylan, bool):
        aylan = bool(aylan) if type(aylan) is int and aylan in (0, 1) else None
    return {"platform": platform.lower() if platform else None, "version": s("version", 12), "w": dim("w"), "h": dim("h"),
            "scheme": scheme, "ua": s("ua", 300), "manzara": one_of("manzara", config.MANZARA_KALITLARI),
            "mavzu": one_of("mavzu", config.MAVZULAR), "aylan": aylan}


def norm_event(e, now: datetime) -> tuple:
    """Mijoz voqeasi -> (datetime, kind, name, ref, screen, dur_ms); noto'g'ri bo'lsa Xato(400)."""
    if not isinstance(e, dict):
        raise Xato(400, "Voqea noto'g'ri")
    k = e.get("k")
    if k not in TRACK_KINDS:
        raise Xato(400, "Voqea turi noto'g'ri (screen, click, end, resume)")
    n = e.get("n")
    s = _short_str(e.get("s"), "s")
    if not (n is None and k in ("end", "resume")) and (not isinstance(n, str) or not KALIT_RE.fullmatch(n)):
        raise Xato(400, "'n' noto'g'ri (ko'pi bilan 40 belgi: a-z 0-9 _ -)")  # end/resume da n ixtiyoriy (joriy ekran)
    r = _short_str(e.get("r"), "r")
    d = e.get("d")
    if d is not None:
        if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d) or not 0 <= d <= 86_400_000:
            raise Xato(400, "'d' noto'g'ri (0 - 86400000 ms)")
        d = int(round(d))
    t = e.get("t")
    at = now
    if t is not None:
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
            raise Xato(400, "'t' noto'g'ri")
        if abs(t / 1000.0 - now.timestamp()) <= config.TRACK_SOAT_FARQI:
            at = datetime.fromtimestamp(t / 1000.0, config.TZ)
    return at, k, n, r, s, d


def norm_duel_answers(v, n: int) -> list[dict]:
    """Duel javoblari (qat'iy): aynan n ta {"pick": 0..3 | null, "ms": 0..60000 butun | yo'q/null}."""
    if not isinstance(v, list) or len(v) != n:
        raise Xato(400, f"Javoblar ro'yxati noto'g'ri ({n} ta javob kerak)")
    out = []
    for a in v:
        if not isinstance(a, dict):
            raise Xato(400, "Javob noto'g'ri")
        pick = a.get("pick")
        if pick is not None and (isinstance(pick, bool) or not isinstance(pick, int) or not 0 <= pick <= 3):
            raise Xato(400, "'pick' 0-3 yoki null bo'lishi kerak")
        ms = a.get("ms")
        if ms is not None:
            if isinstance(ms, float) and math.isfinite(ms) and ms.is_integer():
                ms = int(ms)
            if isinstance(ms, bool) or not isinstance(ms, int) or not 0 <= ms <= config.DUEL_MS_MAX:
                raise Xato(400, f"'ms' 0-{config.DUEL_MS_MAX} oralig'idagi butun son bo'lishi kerak")
        out.append({"pick": pick, "ms": ms})
    return out


def need_num(d: dict, key: str) -> float:
    v = d.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise Xato(400, f"'{key}' musbat son bo'lishi kerak")
    return float(v)


async def read_json(request: web.Request) -> dict:
    if request.content_length is not None and request.content_length > config.API_BODY_LIMIT:
        raise Xato(413, "So'rov juda katta")
    try:
        raw = await request.read()
    except web.HTTPRequestEntityTooLarge:
        raise Xato(413, "So'rov juda katta")
    if len(raw) > config.API_BODY_LIMIT:
        raise Xato(413, "So'rov juda katta")
    if not raw.strip():
        return {}
    try:
        d = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise Xato(400, "Noto'g'ri so'rov (JSON)")
    if not isinstance(d, dict):
        raise Xato(400, "Noto'g'ri so'rov")
    return d


class Services:
    """Server qismlari o'rtasidagi umumiy holat (web, botlar, main)."""

    def __init__(self, store: Store, kurs: Kurs, *, sinov: bool, talaba_token: str, xodim_token: str, secret: bytes,
                 brend: str = config.BREND, app_dir: Path = config.APP_DIR, staff_dir: Path = config.STAFF_DIR,
                 shared_dir: Path = config.SHARED_DIR, admin_dir: Path = config.ADMIN_DIR):
        self.store = store
        self.kurs = kurs
        self.sinov = sinov
        self.talaba_token = talaba_token
        self.xodim_token = xodim_token
        self.secret = secret
        self.brend = brend
        self.app_dir = Path(app_dir)
        self.staff_dir = Path(staff_dir)
        self.admin_dir = Path(admin_dir)
        self.panel_dir = self.staff_dir / "p"
        self.shared_dir = Path(shared_dir)
        self.base_url: str | None = None
        self.talaba_username: str | None = config.SINOV_TALABA_USERNAME if sinov else None
        self.xodim_username: str | None = config.SINOV_XODIM_USERNAME if sinov else None
        self.pdf_sender = None       # async (uid, dars) -> None; Xato(409, ...) - bot xabar yubora olmadi
        self.notifier = None         # async (uid, text, tugma_yozuvi | None, url | None) -> bool (talabalar boti xabari)
        self.now = now_tz            # sinovda almashtirish mumkin
        self.started = now_tz()
        self.bg_tasks: set = set()

    @property
    def content_dir(self) -> Path:
        return self.kurs.content_dir


# ---------------------------------------------------------------- ilova
def build_app(svc: Services) -> web.Application:
    store, kurs = svc.store, svc.kurs
    api_lim = Limiter(config.API_LIMIT_MIN, 60)
    ev_lim = Limiter(config.EVENT_LIMIT_MIN, 60)
    track_lim = Limiter(config.TRACK_LIMIT_MIN, 60)
    panel_cache: dict[str, tuple] = {}

    # ------------------------------------------------------------ middleware va sarlavhalar
    @web.middleware
    async def errors(request: web.Request, handler):
        is_api = request.path.startswith("/api/")
        t0 = time.monotonic()
        try:
            return await handler(request)
        except Xato as e:
            body = {"xato": e.xato}
            if e.status == 401 and request.path.startswith("/api/x/") and svc.xodim_username:
                body["bot"] = svc.xodim_username  # admin panel kirish ekrani "@bot" havolasini ko'rsatadi
            return web.json_response(body, status=e.status)
        except web.HTTPException as e:
            if 300 <= e.status < 400:
                raise
            if is_api:
                msg = {404: "Topilmadi", 405: "Bu usul qo'llanmaydi", 413: "So'rov juda katta"}.get(e.status, "So'rov bajarilmadi")
                return web.json_response({"xato": msg}, status=e.status)
            if e.status == 404:
                return web.Response(status=404, text="Topilmadi", content_type="text/plain", charset="utf-8")
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("ichki xato: %s %s", request.method, request.path)
            if is_api:
                return web.json_response({"xato": "Serverda xatolik. Birozdan keyin qayta urinib ko'ring."}, status=500)
            return web.Response(status=500, text="Serverda xatolik", content_type="text/plain", charset="utf-8")
        finally:
            dt = time.monotonic() - t0
            if is_api and dt > 2 and request.path != "/api/s/pdf":
                log.warning("sekin so'rov: %s %s %.1f s", request.method, request.path, dt)

    async def on_prepare(request: web.Request, response: web.StreamResponse) -> None:
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["Referrer-Policy"] = "no-referrer"
        h["Server"] = "noon"  # aiohttp/Python versiyasini oshkor qilmaslik
        if request.path.startswith("/api/"):
            h["Cache-Control"] = "no-store"
        elif "Cache-Control" not in h:
            h["Cache-Control"] = CACHE_REVALIDATE

    app = web.Application(middlewares=[errors], client_max_size=config.API_BODY_LIMIT)
    app.on_response_prepare.append(on_prepare)

    # ------------------------------------------------------------ statik
    def static(root_attr: str, block_panels: bool = False):
        async def handler(request: web.Request):
            root = getattr(svc, root_attr)
            p = safe_path(root, request.match_info.get("path", ""))
            if p is None:
                raise web.HTTPNotFound()
            if block_panels and p.is_relative_to(svc.panel_dir.resolve()):
                raise web.HTTPNotFound()  # panellar faqat /staff/p/{name}?t= orqali
            if not p.is_file():
                raise web.HTTPNotFound()
            return file_response(p)
        return handler

    def index(root_attr: str):
        async def handler(request: web.Request):
            p = getattr(svc, root_attr) / "index.html"
            if not p.is_file():
                raise web.HTTPNotFound()
            return file_response(p)
        return handler

    def redirect(to: str):
        async def handler(request: web.Request):
            raise web.HTTPFound(to)
        return handler

    # ------------------------------------------------------------ demo panellar
    def panel_bytes(path: Path) -> tuple[bytes, str]:
        st = path.stat()
        key = (st.st_mtime_ns, st.st_size)
        c = panel_cache.get(path.name)
        if c and c[0] == key:
            return c[1], c[2]
        s = path.read_text(encoding="utf-8")
        m = re.search(r"<head\b[^>]*>", s, re.I)
        s = (s[:m.end()] + HEAD_INJECT + s[m.end():]) if m else (HEAD_INJECT + s)
        i = s.lower().rfind("</body>")
        s = (s[:i] + BODY_INJECT + s[i:]) if i >= 0 else (s + BODY_INJECT)
        body = s.encode("utf-8")
        etag = '"p-' + hashlib.sha256(body).hexdigest()[:24] + '"'
        panel_cache[path.name] = (key, body, etag)
        return body, etag

    async def panel(request: web.Request):
        name = request.match_info.get("name", "")
        if name not in config.PANEL_FAYLLARI:
            raise web.HTTPNotFound()
        info = auth.read_panel_token(svc.secret, request.query.get("t", ""))
        row = store.staff_get(info["id"]) if info else None
        if not row or not auth.panel_allowed(row["role"], name, request.query.get("rejim")):
            raise web.HTTPFound("/staff/")
        path = svc.panel_dir / name
        if not path.is_file():
            raise web.HTTPNotFound()
        body, etag = await asyncio.get_running_loop().run_in_executor(None, panel_bytes, path)
        headers = {"Cache-Control": "private, no-cache", "ETag": etag}
        inm = request.headers.get("If-None-Match", "")
        if etag in [x.strip() for x in inm.split(",")]:
            return web.Response(status=304, headers=headers)
        return web.Response(body=body, headers=headers, content_type="text/html", charset="utf-8")

    # ------------------------------------------------------------ video
    async def video(request: web.Request):
        vid = request.match_info.get("vid", "")
        if not VID_RE.fullmatch(vid):
            raise web.HTTPNotFound()
        if not store.feature_on("video"):
            raise web.HTTPNotFound()  # CEO "Video darslar" funksiyasini o'chirgan
        p = kurs.video_path(vid)
        if p is None or not p.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(p, headers={"Content-Type": "video/mp4", "Cache-Control": CACHE_LONG})

    # ------------------------------------------------------------ talaba API
    def student(request: web.Request) -> dict:
        user = auth.check_init_data(request.headers.get("X-Init-Data", ""), svc.talaba_token, config.TALABA_INITDATA_MUDDAT)
        if not user:
            raise Xato(401, XATO_KIRISH_T)
        if not api_lim.hit(("s", user["id"])):
            raise Xato(429, XATO_KOP)
        return user

    def ensure_user(user: dict, now: datetime):
        r = store.get_user(user["id"])
        if r is None:
            store.upsert_user(user, now, "app")
            r = store.get_user(user["id"])
        return r

    def open_count() -> int:
        return store.course_open(kurs.jami())

    def check_order(uid: int, dars: int, open_n: int) -> None:
        """Ustoz ochgan darslar ichida ham ketma-ketlik: dars faqat oldingisi tugatilgandan keyin ochiladi."""
        if dars > open_n:
            raise Xato(403, "Bu dars hali ochilmagan. Ustoz ochganda ochiladi.")
        if dars > 1 and not store.lesson_done(uid, dars - 1):
            raise Xato(403, f"Avval {dars - 1}-darsni tugating")

    def check_lesson(dars: int, open_n: int, uid: int) -> int:
        if kurs.lesson(dars) is None:
            raise Xato(400, "Bunday dars yo'q")
        check_order(uid, dars, open_n)
        return kurs.slides(dars)

    def course_payload(uid: int) -> dict:
        jami = kurs.jami()
        open_n = store.course_open(jami)
        return {"open": open_n, "jami": jami, "available": store.available(uid, open_n)}

    def me_payload(uid: int, now: datetime) -> dict:
        r = store.get_user(uid)
        features = store.features()
        prefs = Store.prefs_of(r)
        if not features.get("uslub", True) and prefs["uslub"] is None:
            prefs["uslub"] = "game"  # uslub tanlash o'chirilgan: tanlamaganlar O'yinli uslubda ko'radi (bazaga yozilmaydi)
        return {"user": Store.user_public(r), "prefs": prefs, "stats": store.stats(uid, today_of(now)),
                "progress": store.progress(uid), "course": course_payload(uid), "features": features,
                "duel_pending": store.duel_pending(uid, now) if features.get("duel", True) else 0}

    # ------------------------------------------------------------ talabalar boti xabarlari (fonda; HTTP javobni kutdirmaydi)
    def notify(uid: int, text: str, label: str | None = None, url: str | None = None) -> None:
        if svc.sinov or svc.notifier is None:
            log.info("bot xabari yuborilmadi (%s): o'quvchi %s", "sinov" if svc.sinov else "bot ulanmagan", uid)
            return
        task = asyncio.create_task(svc.notifier(uid, text, label if url else None, url))

        def _done(t: asyncio.Task):
            svc.bg_tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                log.warning("bot xabari yuborilmadi (o'quvchi %s): %s", uid, t.exception().__class__.__name__)
        svc.bg_tasks.add(task)
        task.add_done_callback(_done)

    # ------------------------------------------------------------ duel yordamchilari (SPEC 11)
    def duel_pool() -> dict[int, int]:
        """Testi bor darslar: {dars: savollar soni} (kurs.test - fayl o'zgarsa o'zi qayta o'qiladi)."""
        out = {}
        for ls in kurs.lessons():
            t = kurs.test(ls["n"])
            if t:
                out[ls["n"]] = len(t["savollar"])
        return out

    def duel_questions(r) -> list[tuple[dict, dict]]:
        """Duel savollari: [(bazadagi {"dars","q"}, test JSON dagi savol)] - matnlar o'zgarishsiz."""
        try:
            qs = json.loads(r["questions"])
        except (TypeError, ValueError):
            qs = []
        out = []
        for x in qs:
            t = kurs.test(x.get("dars")) if isinstance(x, dict) else None
            sv = t["savollar"] if t else []
            i = (x.get("q") or 0) - 1 if isinstance(x, dict) else -1
            if not (0 <= i < len(sv)) or not isinstance(sv[i], dict):
                raise Xato(409, "Duel savollari topilmadi. Yangi duel boshlang.")
            out.append((x, sv[i]))
        if not out:
            raise Xato(409, "Duel savollari topilmadi. Yangi duel boshlang.")
        return out

    def duel_review(r, me: str) -> list[dict] | None:
        """O'yinchi tugatgandan keyin: savol, variantlar, to'g'ri javob, tanlagani, izoh (verbatim)."""
        if not r[me + "_done"]:
            return None
        qs = duel_questions(r)
        try:
            ans = json.loads(r[me + "_answers"] or "[]")
        except ValueError:
            ans = []
        ans = (ans + [{}] * len(qs))[:len(qs)]
        _, _, oks = duel_score([q.get("ok") for _, q in qs], ans, Store._late(r, me))
        return [{"n": i + 1, "dars": x["dars"], "q": q.get("q"), "opts": q.get("opts"), "ok": q.get("ok"),
                 "pick": a.get("pick"), "ms": a.get("ms"), "izoh": q.get("izoh"), "togri": ok}
                for i, ((x, q), a, ok) in enumerate(zip(qs, ans, oks))]

    def duel_link_url(did: str) -> str | None:
        return student_bot.duel_url(svc.base_url, did)

    def need_feature(key: str) -> None:
        if not store.feature_on(key):
            raise Xato(403, XATO_FUNKSIYA)

    def bot_link(payload: str) -> str:
        if not svc.talaba_username:
            raise Xato(503, "Talabalar boti hali ulanmagan. Birozdan keyin qayta urinib ko'ring.")
        return f"https://t.me/{svc.talaba_username}?start={payload}"

    async def s_me(request: web.Request):
        user = student(request)
        await read_json(request)
        now = svc.now()
        store.upsert_user(user, now, "app")
        return web.json_response(me_payload(user["id"], now))

    async def s_event(request: web.Request):
        user = student(request)
        uid = user["id"]
        if not ev_lim.hit(uid):
            raise Xato(429, XATO_KOP)
        d = await read_json(request)
        now = svc.now()
        ensure_user(user, now)
        typ = d.get("type")
        open_n = open_count()
        extra: dict = {}
        if typ == "slide":
            dars = need_int(d, "dars")
            total = check_lesson(dars, open_n, uid)
            idx = need_int(d, "idx")
            if not 1 <= idx <= total:
                raise Xato(400, "Slayd raqami noto'g'ri")
            xp, item = store.ev_slide(uid, dars, idx, now)
        elif typ == "lesson_done":
            dars = need_int(d, "dars")
            total = check_lesson(dars, open_n, uid)
            xp, item, bonus = store.ev_lesson_done_full(uid, dars, total, now, taklif=store.feature_on("taklif"))
            if bonus:
                # do'st taklifi: ikkalasiga +50 (xp_added faqat dars balli; bonus alohida maydonda)
                extra["taklif_bonus"] = bonus["xp"]
                me_r = store.get_user(uid)
                ism = short_name(me_r["first_name"], me_r["last_name"], me_r["username"]) if me_r else "Do'stingiz"
                notify(bonus["inviter_id"], student_bot.taklif_bonus_text(ism, bonus["xp"]), student_bot.TUGMA_ILOVA,
                       student_bot.app_url(svc.base_url, "profil"))
        elif typ in ("video_pos", "video_done"):
            vid = d.get("vid")
            meta = kurs.video_meta(vid) if isinstance(vid, str) and VID_RE.fullmatch(vid) else None
            if not meta:
                raise Xato(400, "Bunday video yo'q")
            n = meta.get("dars")
            if isinstance(n, int):
                check_order(uid, n, open_n)
            dur = meta.get("davomiylik")
            pos = None
            if typ == "video_pos" or "pos" in d:
                pos = need_num(d, "pos")
                if isinstance(dur, (int, float)) and dur > 0:
                    pos = min(pos, float(dur))
            if typ == "video_pos":
                xp, item = store.ev_video_pos(uid, vid, pos, now)
            else:
                xp, item = store.ev_video_done(uid, vid, now, pos)
        elif typ == "test_done":
            if not store.feature_on("test"):
                raise Xato(403, XATO_FUNKSIYA)
            dars = need_int(d, "dars")
            check_lesson(dars, open_n, uid)
            t = kurs.test(dars)
            if not t:
                raise Xato(400, "Bu darsda mashq yo'q")
            qs = t["savollar"]
            answers = d.get("answers")
            if not isinstance(answers, list) or not 1 <= len(answers) <= len(qs):
                raise Xato(400, "Javoblar ro'yxati noto'g'ri")
            for a in answers:
                if a is not None and (isinstance(a, bool) or not isinstance(a, int)):
                    raise Xato(400, "Javoblar ro'yxati noto'g'ri")
            natija = []
            picks = []
            for i, q in enumerate(qs):
                a = answers[i] if i < len(answers) else None
                natija.append(isinstance(q, dict) and a is not None and a == q.get("ok"))
                picks.append((a, natija[-1]))
            correct, total = sum(natija), len(qs)
            xp, item, first_perfect = store.ev_test_done(uid, dars, correct, total, now, picks)
            extra = {"correct": correct, "total": total, "best": item["best"], "perfect": correct == total,
                     "bonus": config.XP_MUKAMMAL if first_perfect else 0, "natija": natija}
        else:
            raise Xato(400, "Noma'lum voqea turi")
        out = {"xp_added": xp, "stats": store.stats(uid, today_of(now)), "item": item, "course": course_payload(uid)}
        out.update(extra)
        return web.json_response(out)

    async def s_prefs(request: web.Request):
        user = student(request)
        d = await read_json(request)
        prefs: dict = {}
        if "uslub" in d:
            if d["uslub"] not in ("game", "glass", None):
                raise Xato(400, "Uslub noto'g'ri")
            prefs["uslub"] = d["uslub"]
        if "rejim" in d:
            if d["rejim"] not in ("auto", "light", "dark"):
                raise Xato(400, "Rejim noto'g'ri")
            prefs["rejim"] = d["rejim"]
        if "arab" in d:
            if d["arab"] not in ("m", "l"):
                raise Xato(400, "Arabcha matn o'lchami noto'g'ri")
            prefs["arab"] = d["arab"]
        if "eslatma" in d:
            if not isinstance(d["eslatma"], bool):
                raise Xato(400, "Eslatma qiymati noto'g'ri")
            prefs["eslatma"] = d["eslatma"]
        ensure_user(user, svc.now())
        store.set_prefs(user["id"], prefs)
        return web.json_response({"ok": True})

    async def s_rating(request: web.Request):
        user = student(request)
        if not store.feature_on("reyting"):
            raise Xato(403, XATO_FUNKSIYA)
        davr = request.query.get("davr", "hafta")
        if davr not in ("hafta", "umumiy"):
            raise Xato(400, "Davr noto'g'ri (hafta yoki umumiy)")
        now = svc.now()
        ensure_user(user, now)
        return web.json_response(store.rating(user["id"], davr, today_of(now)))

    async def s_pdf(request: web.Request):
        user = student(request)
        uid = user["id"]
        d = await read_json(request)
        now = svc.now()
        ensure_user(user, now)
        dars = need_int(d, "dars")
        check_lesson(dars, open_count(), uid)
        if kurs.pdf_path(dars) is None:
            raise Xato(404, "Bu dars uchun PDF topilmadi")
        last, cnt = store.pdf_usage(uid, now)
        if last:
            try:
                ago = (now - datetime.fromisoformat(last)).total_seconds()
            except ValueError:
                ago = config.PDF_ORALIQ
            if ago < config.PDF_ORALIQ:
                raise Xato(429, f"PDF ni {config.PDF_ORALIQ} soniyada bir marta so'rash mumkin. Birozdan keyin urinib ko'ring.")
        if cnt >= config.PDF_KUNLIK:
            raise Xato(429, f"Bugungi PDF limiti tugadi ({config.PDF_KUNLIK} ta). Ertaga qayta urinib ko'ring.")
        store.log_event(uid, "pdf", str(dars), now)
        if svc.sinov:
            return web.json_response({"ok": True, "sinov": True})
        if svc.pdf_sender is None:
            raise Xato(503, "Bot hozircha ishlamayapti. Birozdan keyin qayta urinib ko'ring.")
        task = asyncio.create_task(svc.pdf_sender(uid, dars))
        done, _ = await asyncio.wait({task}, timeout=8)
        if task in done:
            exc = task.exception()
            if exc is None:
                return web.json_response({"ok": True})
            if isinstance(exc, Xato):
                raise exc
            log.warning("PDF yuborilmadi (dars %s): %s", dars, exc.__class__.__name__)
            raise Xato(502, "PDF yuborilmadi. Birozdan keyin qayta urinib ko'ring.")

        def _done(t: asyncio.Task):
            svc.bg_tasks.discard(t)
            if not t.cancelled() and t.exception() is not None:
                log.warning("PDF (fon) yuborilmadi (dars %s): %s", dars, t.exception().__class__.__name__)
        svc.bg_tasks.add(task)
        task.add_done_callback(_done)
        return web.json_response({"ok": True, "kutish": True})

    async def s_track(request: web.Request):
        """Ilova ichidagi yo'l: seans, ekranlar, tugmalar, qurilma (SPEC 10.4). Xatolar ilovada ko'rsatilmaydi."""
        user = student(request)
        uid = user["id"]
        if not track_lim.hit(uid):
            raise Xato(429, XATO_KOP)
        d = await read_json(request)
        sid = d.get("sid")
        if not isinstance(sid, str) or not SID_RE.fullmatch(sid):
            raise Xato(400, "'sid' noto'g'ri")
        dev = norm_device(d["device"]) if d.get("device") is not None else None
        evs = d.get("events")
        if evs is None:
            evs = []
        if not isinstance(evs, list):
            raise Xato(400, "'events' ro'yxat bo'lishi kerak")
        if len(evs) > config.TRACK_MAX_EVENTS:
            raise Xato(400, f"Bitta so'rovda ko'pi bilan {config.TRACK_MAX_EVENTS} ta voqea yuboriladi")
        now = svc.now()
        items, skipped = [], 0
        for e in evs:  # bitta noto'g'ri voqea butun to'plamni yo'qotmasin - o'tkazib yuboriladi
            try:
                items.append(norm_event(e, now))
            except Xato:
                skipped += 1
        ensure_user(user, now)
        store.track(uid, sid, dev, items, now)
        return web.json_response({"ok": True, "skipped": skipped} if skipped else {"ok": True})

    # ------------------------------------------------------------ duellar (SPEC 11.3)
    def need_duel_id(v) -> str:
        if not isinstance(v, str) or not DUEL_ID_RE.fullmatch(v):
            raise Xato(400, "Duel raqami noto'g'ri")
        return v

    def my_name(uid: int) -> str:
        r = store.get_user(uid)
        return short_name(r["first_name"], r["last_name"], r["username"]) if r else "O'quvchi"

    def invite_out(row) -> dict:
        return {"code": row["code"], "link": bot_link("duel_" + row["code"]), "created_at": row["created_at"],
                "expires_at": row["expires_at"]}

    async def s_duels(request: web.Request):
        user = student(request)
        need_feature("duel")
        uid = user["id"]
        now = svc.now()
        ensure_user(user, now)
        can = store.duel_can(uid, duel_pool())
        today, open_ = store.duel_usage(uid, now)
        items = [Store.duel_item(r, uid, now) for r in store.duels_for(uid, now, 30)]
        rank = {"sizning_navbat": 0, "raqib_navbati": 1}
        items.sort(key=lambda x: rank.get(x["status"], 2))  # barqaror: ichida yangisi birinchi qoladi
        invites = [invite_out(r) for r in store.duel_invites_open(uid, now)] if svc.talaba_username else []
        return web.json_response({
            "can": can, "reason": None if can else XATO_DUEL_SHART, "stats": store.duel_stats(uid), "items": items,
            "invites": invites, "pending": sum(1 for x in items if x["status"] == "sizning_navbat"),
            "limits": {"today": today, "daily": config.DUEL_KUNLIK, "open": open_, "max_open": config.DUEL_OCHIQ},
            "rules": {"savollar": config.DUEL_SAVOLLAR, "sec": config.DUEL_SONIYA, "xp_win": config.XP_DUEL_YUTUQ,
                      "xp_draw": config.XP_DUEL_DURRANG, "hours": config.DUEL_MUDDAT // 3600}})

    async def s_duel(request: web.Request):
        """Bitta duel (?duel=<id> ochilganda va natija ekranida): {"duel", "review" | null}."""
        user = student(request)
        need_feature("duel")
        uid = user["id"]
        did = need_duel_id((request.query.get("id") or "").strip())
        now = svc.now()
        r = store.duel_get(did, uid)
        if r is None:
            raise Xato(404, "Duel topilmadi")
        me = "a" if r["a_id"] == uid else "b"
        return web.json_response({"duel": Store.duel_item(r, uid, now), "review": duel_review(r, me)})

    async def s_duel_new(request: web.Request):
        user = student(request)
        need_feature("duel")
        uid = user["id"]
        d = await read_json(request)
        mode = d.get("mode")
        if mode not in ("random", "friend"):
            raise Xato(400, "Duel turi noto'g'ri (random yoki friend)")
        now = svc.now()
        ensure_user(user, now)
        if mode == "friend":
            bot_link("duel_")  # bot ulanmagan bo'lsa - havola yaratilmaydi (503)
            code, exp = store.duel_invite_create(uid, duel_pool(), now)
            return web.json_response({"code": code, "link": bot_link("duel_" + code),
                                      "share_text": "Fonetika kursida duelga chaqiraman: "
                                                    f"{config.DUEL_SAVOLLAR} savol, har biriga {config.DUEL_SONIYA} soniya.",
                                      "expires_at": exp})
        did = store.duel_new_random(uid, duel_pool(), now)
        r = store.duel_get(did)
        log.info("duel %s: tasodifiy (%s -> %s)", did, uid, r["b_id"])
        notify(r["b_id"], student_bot.duel_chaqiruv_text(my_name(uid)), student_bot.TUGMA_DUEL, duel_link_url(did))
        return web.json_response({"duel": Store.duel_item(r, uid, now)})

    async def s_duel_accept(request: web.Request):
        user = student(request)
        need_feature("duel")
        uid = user["id"]
        d = await read_json(request)
        code = d.get("code")
        if not isinstance(code, str) or not DUEL_ID_RE.fullmatch(code):
            raise Xato(400, "Taklif kodi noto'g'ri")
        now = svc.now()
        ensure_user(user, now)
        did, created = store.duel_accept(uid, code, duel_pool(), now)
        r = store.duel_get(did)
        if created:
            log.info("duel %s: do'st taklifi qabul qilindi (%s -> %s)", did, r["a_id"], uid)
            notify(r["a_id"], student_bot.duel_qabul_text(my_name(uid)), student_bot.TUGMA_DUEL, duel_link_url(did))
        return web.json_response({"duel": Store.duel_item(r, uid, now)})

    async def s_duel_start(request: web.Request):
        user = student(request)
        need_feature("duel")
        uid = user["id"]
        d = await read_json(request)
        did = need_duel_id(d.get("id"))
        now = svc.now()
        ensure_user(user, now)
        r0 = store.duel_get(did, uid)
        if r0 is None:
            raise Xato(404, "Duel topilmadi")
        qs = duel_questions(r0)  # savollar mavjudligini boshlashdan oldin tekshirish
        r, me = store.duel_start(uid, did, now)
        started = parse_iso(r[me + "_started"])
        deadline = started + timedelta(seconds=config.DUEL_OYNA)
        return web.json_response({
            "id": did, "sec": config.DUEL_SONIYA, "started_at": r[me + "_started"], "deadline": iso(deadline),
            "left_ms": max(0, int((deadline - now).total_seconds() * 1000)),
            "questions": [{"n": i + 1, "dars": x["dars"], "q": q.get("q"), "opts": q.get("opts")}
                          for i, (x, q) in enumerate(qs)]})

    async def s_duel_finish(request: web.Request):
        user = student(request)
        need_feature("duel")
        uid = user["id"]
        d = await read_json(request)
        did = need_duel_id(d.get("id"))
        now = svc.now()
        ensure_user(user, now)
        r0 = store.duel_get(did, uid)
        if r0 is None:
            raise Xato(404, "Duel topilmadi")
        qs = duel_questions(r0)
        answers = norm_duel_answers(d.get("answers"), len(qs))
        res = store.duel_finish(uid, did, answers, [q.get("ok") for _, q in qs], now)
        r, me = res["row"], res["me"]
        if res["resolved"]:
            ot = "b" if me == "a" else "a"
            other = r[ot + "_id"]
            w = r["winner_id"]
            natija = "durrang" if w is None else ("yutdi" if w == other else "yutqazdi")
            xp = config.XP_DUEL_DURRANG if w is None else (config.XP_DUEL_YUTUQ if w == other else 0)
            log.info("duel %s tugadi: g'olib %s", did, w)
            notify(other, student_bot.duel_natija_text(natija, r[ot + "_correct"], r[me + "_correct"], my_name(uid), xp),
                   student_bot.TUGMA_NATIJA, duel_link_url(did))
        return web.json_response({"duel": Store.duel_item(r, uid, now), "xp_added": res["xp"], "late": res["late"],
                                  "review": duel_review(r, me)})

    async def s_taklif(request: web.Request):
        user = student(request)
        need_feature("taklif")
        uid = user["id"]
        now = svc.now()
        ensure_user(user, now)
        link = bot_link("ref_" + store.ref_code(uid))
        friends, total, rewarded, earned = store.referrals_of(uid)
        return web.json_response({
            "link": link, "share_text": f"Arab tili fonetikasini telefoningizda o'rganing — {svc.brend} fonetika kursi.",
            "bonus": config.XP_TAKLIF, "earned": earned, "invited": total, "rewarded": rewarded, "friends": friends})

    # ------------------------------------------------------------ xodim API
    def staff(request: web.Request):
        """Kirish: X-Init-Data (xodimlar boti) -> X-Staff-Token (panel tokeni) -> noon_admin cookie (brauzer).
        Cookie bilan POST so'rovlarda X-Requested-With: noon shart (CSRF). Rol har doim bazadan olinadi."""
        init = request.headers.get("X-Init-Data", "")
        user = None
        via = "init"
        if init:
            user = auth.check_init_data(init, svc.xodim_token, config.XODIM_INITDATA_MUDDAT)
            if not user:
                raise Xato(401, XATO_KIRISH_X)
            uid = user["id"]
        elif request.headers.get("X-Staff-Token"):
            via = "token"
            info = auth.read_panel_token(svc.secret, request.headers.get("X-Staff-Token", ""))
            if not info:
                raise Xato(401, XATO_KIRISH_X)
            uid = info["id"]
        else:
            ck = request.cookies.get(config.COOKIE_NOMI, "")
            if not ck:
                raise Xato(401, XATO_KIRISH_X)
            info = auth.read_panel_token(svc.secret, ck)
            if not info:
                raise Xato(401, XATO_KIRISH_A)
            via = "cookie"
            if request.method not in ("GET", "HEAD") and request.headers.get(config.CSRF_SARLAVHA) != config.CSRF_QIYMAT:
                raise Xato(403, XATO_CSRF)
            uid = info["id"]
        request["via"] = via
        if not api_lim.hit(("x", uid)):
            raise Xato(429, XATO_KOP)
        row = store.staff_get(uid)
        if not row:
            raise Xato(403, XATO_XODIM)
        if user and ((user.get("first_name") or "") != row["first_name"] or (user.get("last_name") or "") != row["last_name"]
                     or (user.get("username") or None) != row["username"]):
            store.staff_update_names(user)
            row = store.staff_get(uid)
        return row, user

    def need_role(row, roles) -> None:
        if row["role"] not in roles:
            raise Xato(403, XATO_RUXSAT)

    def need_section(row, key: str, edit: bool = False) -> str:
        """SPEC 10.1 jadvali: bo'lim rolga ochiqmi (edit=True - o'zgartirish huquqi ham kerak)."""
        acc = config.BOLIMLAR[key][2].get(row["role"])
        if not acc:
            raise Xato(403, XATO_BOLIM)
        if edit and acc != "edit":
            raise Xato(403, XATO_RUXSAT)
        return acc

    def staff_user(row, user) -> dict:
        return {"id": row["id"], "first_name": row["first_name"], "last_name": row["last_name"], "username": row["username"],
                "photo_url": (user or {}).get("photo_url") if isinstance((user or {}).get("photo_url"), str) else None}

    async def x_auth(request: web.Request):
        row, user = staff(request)
        await read_json(request)
        token = auth.make_panel_token(svc.secret, row["id"], row["role"])
        u = staff_user(row, user)
        return web.json_response({"user": u, "role": row["role"], "rol_nomi": config.ROL_NOMI[row["role"]],
                                  "brend": svc.brend, "token": token, "panels": auth.panels_for(row["role"], token)})

    async def x_stats(request: web.Request):
        staff(request)
        # 06.10 (egasi, "1 ha"): xodimlar sahifasi (barcha 4 rol) ham Ko'rinish kartasini ko'rsatadi - shaxsiy ma'lumot yo'q.
        # Davr = statistika davri (?days=, standart 14); eski maydonlar (styles/modes ...) o'zgarmagan.
        days = q_int(request, "days", 14, 1, 90)
        now = svc.now()
        out = store.staff_stats(now, kurs.lesson_of_video, days)
        out["korinish"] = store.korinish_report(now, days)
        return web.json_response(out)

    async def x_students(request: web.Request):
        staff(request)
        return web.json_response({"students": store.students(request.query.get("q", ""), svc.now())})

    async def x_course(request: web.Request):
        staff(request)
        cs = store.course_stats()
        lessons = []
        for ls in kurs.lessons():
            n = ls["n"]
            s = cs.get(n, {})
            vids = kurs.lesson_videos(ls)
            lessons.append({"n": n, "nomi": ls.get("nomi"), "qism": ls.get("qism"), "slaydlar": kurs.slides(n),
                            "video": bool(vids), "videolar": len(vids), "test": bool(ls.get("test")),
                            "done": s.get("done", 0), "started": s.get("started", 0), "test_avg": s.get("test_avg")})
        jami = kurs.jami()
        return web.json_response({"open": store.course_open(jami), "jami": jami, "lessons": lessons,
                                  "qismlar": kurs.qismlar()})

    async def x_open(request: web.Request):
        row, _ = staff(request)
        need_role(row, config.OCHISH_ROLLARI)
        d = await read_json(request)
        jami = kurs.jami()
        n = need_int(d, "n", 1, jami)
        old = store.course_open(jami)
        store.set_course_open(n)
        if old != n:
            store.audit_add(row["id"], "open", {"from": old, "to": n}, svc.now())
        log.info("ochiq darslar: %s (xodim %s)", n, row["id"])
        return web.json_response({"ok": True, "open": n})

    async def x_invite(request: web.Request):
        row, _ = staff(request)
        need_role(row, ("ceo",))
        d = await read_json(request)
        role = d.get("role")
        if role not in config.TAKLIF_ROLLARI:
            raise Xato(400, "Rol noto'g'ri (admin, ustoz yoki assistent)")
        now = svc.now()
        if store.invites_recent(row["id"], now) >= config.TAKLIF_SOATIGA:
            raise Xato(429, XATO_KOP)
        if not svc.xodim_username:
            raise Xato(503, "Xodimlar boti hali ulanmagan. Birozdan keyin qayta urinib ko'ring.")
        code, exp = store.invite_create(role, row["id"], now)
        store.audit_add(row["id"], "invite", {"role": role, "expires": exp}, now)
        return web.json_response({"link": f"https://t.me/{svc.xodim_username}?start=t_{code}", "expires": exp, "role": role})

    async def x_staff(request: web.Request):
        row, _ = staff(request)
        need_role(row, ("ceo",))
        out = [{"id": r["id"], "name": f"{r['first_name']} {r['last_name']}".strip() or (r["username"] or str(r["id"])),
                "username": r["username"], "role": r["role"], "added_at": r["added_at"]} for r in store.staff_list()]
        return web.json_response({"staff": out})

    async def x_staff_remove(request: web.Request):
        row, _ = staff(request)
        need_role(row, ("ceo",))
        d = await read_json(request)
        target = need_int(d, "id", 1)
        t = store.staff_get(target)
        err = store.staff_remove(row["id"], target)
        if err:
            raise Xato(400, err)
        store.audit_add(row["id"], "staff_remove",
                        {"id": target, "name": f"{t['first_name']} {t['last_name']}".strip() or (t["username"] or str(target)),
                         "role": t["role"]}, svc.now())
        log.info("xodim o'chirildi: %s (CEO %s)", target, row["id"])
        return web.json_response({"ok": True})

    # ------------------------------------------------------------ admin panel API (SPEC 10.6)
    async def x_me(request: web.Request):
        row, user = staff(request)
        role = row["role"]
        if role not in config.ADMIN_ROLLARI:
            raise Xato(403, XATO_BOLIM)
        sections = [k for k, (_, _, acc) in config.BOLIMLAR.items() if role in acc]
        return web.json_response({
            "user": staff_user(row, user), "role": role, "rol_nomi": config.ROL_NOMI[role], "sections": sections,
            "access": {k: config.BOLIMLAR[k][2][role] for k in sections},
            "can_edit": {"kurs": role in config.OCHISH_ROLLARI, "funksiyalar": role == "ceo", "xodimlar": role == "ceo"},
            "features": store.features(), "brend": svc.brend, "browser": request.get("via") == "cookie"})

    async def x_overview(request: web.Request):
        row, _ = staff(request)
        need_section(row, "bosh")
        days = q_int(request, "days", 14, 1, 90)
        now = svc.now()
        out = store.staff_stats(now, kurs.lesson_of_video, days)
        out.update(store.overview_extra(now, yorliqlar.ekran_nomi))
        out["korinish"] = store.korinish_report(now, days)  # 05.10: "Uslub tanlovi" o'rniga (styles/modes - eski panel uchun)
        # 05.10 (admin NUQTA): o'tgan hafta bilan solishtirish, duellar holati, So'nggi faollikda duellar ham
        out["oldingi"] = store.week_compare(now)
        out["duels"] = store.duel_summary(now, days)
        rec = out.get("recent") or []
        out["recent"] = sorted(rec + store.recent_duels(20), key=lambda x: x.get("at") or "", reverse=True)[:20]
        return web.json_response(out)

    async def x_student(request: web.Request):
        row, _ = staff(request)
        need_section(row, "oquvchilar")
        uid = q_int(request, "id", None, 1)
        out = store.student_detail(uid, kurs, svc.now())
        if out is None:
            raise Xato(404, "O'quvchi topilmadi")
        return web.json_response(out)

    async def x_session(request: web.Request):
        row, _ = staff(request)
        need_section(row, "oquvchilar")
        sid = (request.query.get("id") or "").strip()
        if not SID_RE.fullmatch(sid):
            raise Xato(400, "'id' noto'g'ri")
        res = store.session_detail(sid)
        if res is None:
            raise Xato(404, "Seans topilmadi")
        sess, user, events = res
        vcache: dict = {}
        rivals = store.duel_rivals(user["id"], {e["ref"] for e in events
                                                if isinstance(e["ref"], str) and DUEL_ID_RE.fullmatch(e["ref"])})
        timeline = [{"at": e["at"], "kind": e["kind"], "name": e["name"],
                     "label": yorliqlar.voqea_nomi(e["kind"], e["name"], e["ref"]), "ref": e["ref"],
                     "ref_label": ref_label(e["kind"], e["name"], e["ref"], rivals, vcache), "screen": e["screen"],
                     "screen_label": yorliqlar.ekran_nomi(e["screen"]), "dur_ms": e["dur_ms"]} for e in events]
        return web.json_response({"session": sess, "user": user, "timeline": timeline})

    def video_label(vid: str) -> str | None:
        m = kurs.video_meta(vid)
        n = m.get("dars") if m else None
        if not isinstance(n, int):
            return None
        ids = [v.get("id") for v in kurs.lesson_videos(kurs.lesson(n) or {})]
        if len(ids) > 1 and vid in ids:
            return f"{n}-dars {ids.index(vid) + 1}-videosi"
        return f"{n}-dars videosi"

    def ref_label(kind: str, name: str | None, ref, rivals: dict, vcache: dict) -> str | None:
        """05.10: ichki id o'rniga o'qiladigan nom - duel id -> "Kamola Y. bilan", video id -> "2-dars videosi",
        dars raqami -> "7-dars". Topilmasa None (ref xom holicha qoladi)."""
        if ref is None or ref == "":
            return None
        r = str(ref)
        if r in rivals:
            return f"{rivals[r]} bilan"
        if r.isdigit():
            if kind == "screen" or name in yorliqlar.DARS_REF_TUGMALAR:
                return f"{int(r)}-dars"
            return None
        if not VID_RE.fullmatch(r):
            return None
        if r not in vcache:
            vcache[r] = video_label(r)     # so'rov ichidagi kesh (video_meta kurs bo'ylab qidiradi)
        return vcache[r]

    async def x_funnel(request: web.Request):
        row, _ = staff(request)
        need_section(row, "voronka")
        days = q_int(request, "days", 30, 1, 366)
        out = store.funnel(svc.now(), days)
        cs = store.course_stats()
        out["lessons"] = [{"n": ls["n"], "nomi": ls.get("nomi"), "started": cs.get(ls["n"], {}).get("started", 0),
                           "done": cs.get(ls["n"], {}).get("done", 0)} for ls in kurs.lessons()]
        return web.json_response(out)

    async def x_clicks(request: web.Request):
        row, _ = staff(request)
        need_section(row, "tugmalar")
        days = q_int(request, "days", 7, 1, 90)
        out = store.clicks_report(svc.now(), days, yorliqlar.ekran_nomi, yorliqlar.tugma_nomi)
        for t in out["top"]:
            t["ref_label"] = yorliqlar.qiymat_nomi(t["name"], t["ref"])   # 05.10: ref xom qoladi, o'qiladigan nomi alohida
        return web.json_response(out)

    async def x_devices(request: web.Request):
        row, _ = staff(request)
        need_section(row, "qurilmalar")
        days = q_int(request, "days", 30, 1, 366)
        now = svc.now()
        out = store.devices_report(now, days)
        out["korinish"] = store.korinish_report(now, days)
        return web.json_response(out)

    async def x_tests(request: web.Request):
        row, _ = staff(request)
        need_section(row, "testlar")
        return web.json_response(store.tests_summary(kurs))

    async def x_test(request: web.Request):
        row, _ = staff(request)
        need_section(row, "testlar")
        dars = q_int(request, "dars", None, 1, 999)
        ls = kurs.lesson(dars)
        if ls is None:
            raise Xato(400, "Bunday dars yo'q")
        t = kurs.test(dars)
        if not t:
            raise Xato(404, "Bu darsda test yo'q")
        out = {"dars": dars, "nomi": ls.get("nomi"), "test_nomi": t.get("nomi")}
        out.update(store.test_detail(dars, t))
        return web.json_response(out)

    async def x_dropoff(request: web.Request):
        row, _ = staff(request)
        need_section(row, "kurs")
        dars = q_int(request, "dars", None, 1, 999)
        ls = kurs.lesson(dars)
        if ls is None:
            raise Xato(400, "Bunday dars yo'q")
        out = {"dars": dars, "nomi": ls.get("nomi")}
        out.update(store.dropoff(dars, kurs.slides(dars)))
        return web.json_response(out)

    def features_meta() -> list[dict]:
        return [{"key": k, "nomi": nomi, "tavsif": tavsif, "bosqich": b} for k, nomi, tavsif, b in config.FUNKSIYALAR]

    async def x_features(request: web.Request):
        row, _ = staff(request)
        need_section(row, "funksiyalar")
        return web.json_response({"features": store.features(), "meta": features_meta()})

    async def x_features_set(request: web.Request):
        row, _ = staff(request)
        need_section(row, "funksiyalar", edit=True)
        d = await read_json(request)
        key, on = d.get("key"), d.get("on")
        if key not in config.FUNKSIYA_KALITLARI:
            raise Xato(400, "Bunday funksiya yo'q")
        if not isinstance(on, bool):
            raise Xato(400, "'on' true yoki false bo'lishi kerak")
        feats, changed = store.set_feature(key, on)
        if changed:
            store.audit_add(row["id"], "feature", {"key": key, "on": on}, svc.now())
            log.info("funksiya %s: %s (CEO %s)", key, "yoqildi" if on else "o'chirildi", row["id"])
        return web.json_response({"ok": True, "features": feats})

    async def x_audit(request: web.Request):
        row, _ = staff(request)
        need_section(row, "jurnal")
        limit = q_int(request, "limit", 200, 1, 1000)
        items = store.audit_list(limit)
        for it in items:
            it["action_nomi"] = yorliqlar.AMAL_NOMI.get(it["action"], it["action"])
            it["label"] = yorliqlar.amal_matni(it["action"], it["detail"])
        return web.json_response({"items": items})

    async def x_duels(request: web.Request):
        row, _ = staff(request)
        need_section(row, "duellar")
        days = q_int(request, "days", 30, 1, 366)
        return web.json_response(store.duels_report(svc.now(), days))

    async def x_referrals(request: web.Request):
        row, _ = staff(request)
        need_section(row, "takliflar")
        return web.json_response(store.referrals_report())

    async def x_logout(request: web.Request):
        if request.headers.get(config.CSRF_SARLAVHA) != config.CSRF_QIYMAT:
            raise Xato(403, XATO_CSRF)
        resp = web.json_response({"ok": True})
        resp.del_cookie(config.COOKIE_NOMI, path="/")
        return resp

    # ------------------------------------------------------------ admin panel: brauzer orqali kirish (/kirish havolasi)
    def is_https(request: web.Request) -> bool:
        fp = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        return request.secure or fp == "https"

    async def admin_kirish(request: web.Request):
        row = store.login_use(request.query.get("k", ""), svc.now())
        if not row:
            return web.Response(status=403, text=KIRISH_ESKI_HTML, content_type="text/html", charset="utf-8",
                                headers={"Cache-Control": "no-store"})
        token = auth.make_panel_token(svc.secret, row["id"], row["role"])
        resp = web.Response(status=302, headers={"Location": "/admin/", "Cache-Control": "no-store"})
        resp.set_cookie(config.COOKIE_NOMI, token, max_age=config.COOKIE_MUDDAT, path="/", httponly=True,
                        samesite="Lax", secure=is_https(request))
        log.info("admin panelga kirish (brauzer): xodim %s", row["id"])
        return resp

    async def api_404(request: web.Request):
        raise Xato(404, "Topilmadi")

    # ------------------------------------------------------------ marshrutlar (tartib muhim)
    r = app.router
    r.add_get("/", redirect("/app/"))
    r.add_get("/app", redirect("/app/"))
    r.add_get("/app/", index("app_dir"))
    r.add_get("/app/{path:.+}", static("app_dir"))
    r.add_get("/staff", redirect("/staff/"))
    r.add_get("/staff/", index("staff_dir"))
    r.add_get("/staff/p/{name}", panel)
    r.add_get("/staff/{path:.+}", static("staff_dir", block_panels=True))
    r.add_get("/admin", redirect("/admin/"))
    r.add_get("/admin/", index("admin_dir"))
    r.add_get("/admin/kirish", admin_kirish)
    r.add_get("/admin/{path:.+}", static("admin_dir"))
    r.add_get("/shared/{path:.+}", static("shared_dir"))
    r.add_get("/content/{path:.+}", static("content_dir"))
    r.add_get("/media/video/{vid}", video)
    r.add_post("/api/s/me", s_me)
    r.add_post("/api/s/event", s_event)
    r.add_post("/api/s/prefs", s_prefs)
    r.add_get("/api/s/rating", s_rating)
    r.add_post("/api/s/pdf", s_pdf)
    r.add_post("/api/s/track", s_track)
    r.add_get("/api/s/duels", s_duels)
    r.add_get("/api/s/duel", s_duel)
    r.add_post("/api/s/duel/new", s_duel_new)
    r.add_post("/api/s/duel/accept", s_duel_accept)
    r.add_post("/api/s/duel/start", s_duel_start)
    r.add_post("/api/s/duel/finish", s_duel_finish)
    r.add_get("/api/s/taklif", s_taklif)
    r.add_post("/api/x/auth", x_auth)
    r.add_get("/api/x/stats", x_stats)
    r.add_get("/api/x/students", x_students)
    r.add_get("/api/x/course", x_course)
    r.add_post("/api/x/open", x_open)
    r.add_post("/api/x/invite", x_invite)
    r.add_get("/api/x/staff", x_staff)
    r.add_post("/api/x/staff/remove", x_staff_remove)
    r.add_get("/api/x/me", x_me)
    r.add_get("/api/x/overview", x_overview)
    r.add_get("/api/x/student", x_student)
    r.add_get("/api/x/session", x_session)
    r.add_get("/api/x/funnel", x_funnel)
    r.add_get("/api/x/clicks", x_clicks)
    r.add_get("/api/x/devices", x_devices)
    r.add_get("/api/x/tests", x_tests)
    r.add_get("/api/x/test", x_test)
    r.add_get("/api/x/dropoff", x_dropoff)
    r.add_get("/api/x/features", x_features)
    r.add_post("/api/x/features", x_features_set)
    r.add_get("/api/x/audit", x_audit)
    r.add_get("/api/x/duels", x_duels)
    r.add_get("/api/x/referrals", x_referrals)
    r.add_post("/api/x/logout", x_logout)
    r.add_route("*", "/api/{tail:.*}", api_404)
    return app

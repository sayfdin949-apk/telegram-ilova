"""Noon Telegram ilova - bitta jarayon: aiohttp server + cloudflared tunnel + ikkita bot.

  python server/main.py                         ishchi rejim (server/.env kerak; odatda "2 - Botlarni ishga tushirish.bat")
  python server/main.py --sinov [--port 8791] [--db data/sinov_X.db] [--seed]
                                                sinov: botsiz va tunnelsiz, soxta (SINOV) tokenlar bilan
  python server/main.py --fake-tg http://127.0.0.1:PORT [--port N] [--db ...] [--holat F] [--pid F] [--jobs-now]
                                                haqiqiy kod yo'li, lekin Telegram o'rniga tools/fake_telegram.py (sinov)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:  # Linux server (VPS)
    import fcntl

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aiohttp import web  # noqa: E402

import auth  # noqa: E402
import config  # noqa: E402
import jarayon  # noqa: E402
from db import Store, iso, now_tz  # noqa: E402
from kurs import Kurs  # noqa: E402

log = logging.getLogger("noon.main")


class Fatal(Exception):
    pass


# ---------------------------------------------------------------- log
class RedactFormatter(logging.Formatter):
    """Tokenlar logga hech qachon tushmasin (httpx URL larida token bo'ladi)."""

    def __init__(self, fmt: str, secrets: list[str]):
        super().__init__(fmt)
        self.secrets = [s for s in secrets if s]

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        for t in self.secrets:
            s = s.replace(t, "***")
        return config.TOKEN_ANY_RE.sub("***", s)


def setup_logging(mode: str, port: int, log_path: Path | None, secrets: list[str]) -> Path:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    if log_path is None:
        log_path = config.LOG_FILE if mode == "prod" else config.LOG_DIR / f"sinov_{port}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    big = mode == "prod"
    fh = RotatingFileHandler(log_path, maxBytes=(2 if big else 1) * 1024 * 1024, backupCount=3 if big else 1,
                             encoding="utf-8", delay=True)
    fmt = RedactFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s", secrets)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if sys.stderr is not None and hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.WARNING)
        sh.setFormatter(fmt)
        root.addHandler(sh)
    for name in ("httpx", "httpcore", "apscheduler", "aiohttp.access", "hpack"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    return log_path


# ---------------------------------------------------------------- yagona nusxa va holat.json
class PidLock:
    """data/main.pid: ichida PID; fayl oxiridan keyingi baytga Windows qulfi (jarayon o'lsa o'zi yechiladi)."""

    def __init__(self, path: Path):
        self.path = path
        self.f = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path, "a+", encoding="ascii")
        try:
            if os.name == "nt":
                f.seek(1024)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        f.seek(0)
        f.truncate()
        f.write(str(os.getpid()))
        f.flush()
        self.f = f
        return True

    def release(self) -> None:
        if not self.f:
            return
        try:
            if os.name == "nt":
                self.f.seek(1024)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        self.f.close()
        self.f = None
        try:
            self.path.unlink()
        except OSError:
            pass


class Holat:
    def __init__(self, path: Path | None, port: int):
        self.path = path
        self.conflict_last = 0.0  # oxirgi 409 Conflict vaqti (time.monotonic)
        self.data = {"pid": os.getpid(), "boshlangan": iso(now_tz()), "holat": "ishga tushmoqda", "url": None,
                     "talaba_bot": None, "xodim_bot": None, "ulash_kodi": None, "xato": None, "port": port}

    def update(self, **kw) -> None:
        self.data.update(kw)
        self.data["yangilangan"] = iso(now_tz())
        if not self.path:
            return
        text = json.dumps(self.data, ensure_ascii=False, indent=2)
        tmp = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(text, encoding="utf-8")
            for _ in range(20):
                try:
                    os.replace(tmp, self.path)
                    return
                except PermissionError:
                    time.sleep(0.05)
            self.path.write_text(text, encoding="utf-8")
        except OSError as e:
            log.warning("holat.json yozilmadi: %s", e)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------- yordamchi vazifalar
async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> bool:
    """True - to'xtatish so'raldi."""
    try:
        await asyncio.wait_for(stop.wait(), seconds)
        return True
    except asyncio.TimeoutError:
        return False


async def watch_stop_file(path: Path, stop: asyncio.Event) -> None:
    while not stop.is_set():
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
            log.info("to'xtatish so'raldi (%s)", path.name)
            stop.set()
            return
        if await _sleep_or_stop(stop, 1.0):
            return


async def init_bot(app, name: str, holat: Holat, stop: asyncio.Event) -> None:
    from telegram.error import InvalidToken, NetworkError, RetryAfter, TimedOut
    delay = 5
    while True:
        try:
            await app.initialize()
            return
        except RetryAfter as e:  # Telegram "kuting" dedi (tez-tez qayta ishga tushirilganda)
            from student_bot import retry_seconds
            wait = retry_seconds(e) + 1
            log.warning("%s boti: Telegram %.0f s kutishni so'radi", name, wait)
            if await _sleep_or_stop(stop, min(wait, 300)):
                raise asyncio.CancelledError()
        except InvalidToken:
            raise Fatal(f"{name} boti tokeni noto'g'ri yoki bekor qilingan. "
                        "\"1 - Tokenlarni kiritish.bat\" ni qayta ishga tushiring.")
        except (NetworkError, TimedOut) as e:
            log.warning("%s boti: Telegramga ulanib bo'lmadi (%s), %s s dan keyin qayta", name, e.__class__.__name__, delay)
            holat.update(xato="Telegramga ulanib bo'lmadi (internetni tekshiring). Qayta urinilmoqda.")
            if await _sleep_or_stop(stop, delay):
                raise asyncio.CancelledError()
            delay = min(60, delay * 2)


async def start_polling(app, name: str, holat: Holat, stop: asyncio.Event) -> None:
    from telegram import Update
    from telegram.error import Conflict, NetworkError, TelegramError, TimedOut
    last = {"t": 0.0, "c0": 0.0, "c1": 0.0}

    def on_poll_error(e: TelegramError) -> None:  # PTB talabi: korutina emas
        now = time.monotonic()
        if isinstance(e, Conflict):
            # qayta ishga tushganda eski getUpdates ~10 s davom etadi - faqat 1 daqiqadan uzoq davom etsa ogohlantiramiz
            if now - last["c1"] > 120:
                last["c0"] = now
            last["c1"] = now
            holat.conflict_last = now
            if now - last["c0"] > 60:
                holat.update(xato=f"{name} boti tokeni bilan {KONFLIKT_MATN}")
        if now - last["t"] > 60:
            last["t"] = now
            log.warning("%s boti getUpdates xatosi: %s", name, e.__class__.__name__)
        elif not isinstance(e, (NetworkError, Conflict)):
            log.warning("%s boti getUpdates xatosi: %s", name, e.__class__.__name__)

    delay = 5
    while True:
        try:
            await app.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES,
                                            bootstrap_retries=3, error_callback=on_poll_error)
            return
        except (NetworkError, TimedOut) as e:
            log.warning("%s boti: polling boshlanmadi (%s), %s s dan keyin qayta", name, e.__class__.__name__, delay)
            holat.update(xato="Telegramga ulanib bo'lmadi (internetni tekshiring). Qayta urinilmoqda.")
            if await _sleep_or_stop(stop, delay):
                raise asyncio.CancelledError()
            delay = min(60, delay * 2)


TUNNEL_TEKSHIRUV = 10  # soniya
MENYU_TEKSHIRUV = 30    # soniya
KONFLIKT_MATN = "boshqa dastur ham ishlayapti. O'sha dasturni to'xtating."
KONFLIKT_TOZALASH = 180  # soniya: shuncha vaqt 409 Conflict bo'lmasa, holat.json dagi ogohlantirish o'chadi


async def conflict_clear(holat: Holat, stop: asyncio.Event) -> None:
    """409 Conflict ogohlantirishi o'z-o'zidan o'chadi, agar boshqa dastur to'xtagan bo'lsa (qayta ishga tushirmasdan)."""
    while not stop.is_set():
        if await _sleep_or_stop(stop, MENYU_TEKSHIRUV):
            return
        xato = holat.data.get("xato") or ""
        if xato.endswith(KONFLIKT_MATN) and time.monotonic() - getattr(holat, "conflict_last", 0.0) > KONFLIKT_TOZALASH:
            log.info("409 Conflict to'xtadi - ogohlantirish o'chirildi")
            holat.update(xato=None)


async def duel_muddat_loop(store, stop: asyncio.Event) -> None:
    """Sinov rejimi (botlarsiz, JobQueue yo'q): muddati o'tgan duellarni har soatda belgilash."""
    while not stop.is_set():
        if await _sleep_or_stop(stop, config.DUEL_MUDDAT_TEKSHIRUV):
            return
        try:
            n = store.duels_expire(now_tz())
            if n:
                log.info("muddati o'tgan duellar belgilandi: %s", n)
        except Exception:
            log.exception("duel muddati")


async def sync_menus(apps, svc) -> None:
    """Ikkala botning menyu tugmasini svc.base_url ga moslaydi (hali mos bo'lmaganlarini; xato bo'lsa keyin qayta)."""
    import staff_bot
    import student_bot
    done = getattr(svc, "menu_set", None)
    if done is None:
        done = svc.menu_set = {}
    if not svc.base_url:
        return
    for key, app, fn in (("talaba", apps[0], student_bot.set_menu), ("xodim", apps[1], staff_bot.set_menu)):
        if done.get(key) != svc.base_url and await fn(app, svc):
            done[key] = svc.base_url


async def menu_guard(apps, svc, stop: asyncio.Event) -> None:
    while not stop.is_set():
        if await _sleep_or_stop(stop, MENYU_TEKSHIRUV):
            return
        try:
            await sync_menus(apps, svc)
        except Exception:
            log.exception("menyu tugmalari")


async def tunnel_watch(tunnel, svc, apps, holat: Holat, stop: asyncio.Event) -> None:
    """cloudflared to'xtab qolsa - qayta ishga tushiradi, yangi manzilni botlar menyusiga va holat.json ga yozadi."""
    fails = 0
    while not stop.is_set():
        if await _sleep_or_stop(stop, TUNNEL_TEKSHIRUV):
            return
        if tunnel.alive() and svc.base_url:
            continue
        log.warning("tunnel ishlamayapti - qayta ishga tushirilmoqda")
        url = await tunnel.start()
        if stop.is_set():
            return
        if url:
            fails = 0
            svc.base_url = url
            await sync_menus(apps, svc)
            holat.update(url=url, xato=None, holat="ishlayapti")
        else:
            fails += 1
            holat.update(xato="Tunnel manzili olinmadi (internetni tekshiring). Qayta urinilmoqda.")
            if await _sleep_or_stop(stop, min(300, 3 * TUNNEL_TEKSHIRUV * fails)):
                return


# ---------------------------------------------------------------- asosiy oqim
async def amain(args, mode: str, port: int, db_path: Path, holat: Holat, stop_file: Path) -> int:
    import web as webmod
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _sig(*_):
        loop.call_soon_threadsafe(stop.set)
    for s in (signal.SIGINT, getattr(signal, "SIGBREAK", None), signal.SIGTERM):
        if s is not None:
            try:
                signal.signal(s, _sig)
            except (ValueError, OSError):
                pass

    store = Store(db_path)
    kurs = Kurs(Path(args.content) if args.content else config.CONTENT_DIR,
                Path(args.videolar) if args.videolar else config.VIDEOLAR_FILE)
    if args.seed:
        store.seed(now_tz(), kurs)
        log.info("namuna ma'lumotlar yozildi: %s", db_path.name)
    secret = auth.load_secret()
    svc = webmod.Services(store, kurs, sinov=(mode == "sinov"), talaba_token=args._talaba, xodim_token=args._xodim,
                          secret=secret)
    svc.on_paired = lambda: holat.update(ulash_kodi=None)

    runner = web.AppRunner(webmod.build_app(svc), access_log=None, shutdown_timeout=3)
    await runner.setup()
    try:
        await web.TCPSite(runner, config.HOST, port).start()
    except OSError:
        await runner.cleanup()
        raise Fatal(f"{port}-port band. Server allaqachon ishlayotgan bo'lishi mumkin (\"4 - Holat.bat\").")
    log.info("web server: http://%s:%s (rejim: %s, baza: %s)", config.HOST, port, mode, db_path.name)

    tasks: list[asyncio.Task] = [asyncio.create_task(watch_stop_file(stop_file, stop))]
    tunnel = None
    apps: list = []
    try:
        if mode == "sinov":
            svc.base_url = f"http://{config.HOST}:{port}"
            tasks.append(asyncio.create_task(duel_muddat_loop(store, stop)))  # botsiz rejimda ham soatlik vazifa
            holat.update(holat="ishlayapti", url=svc.base_url)
            print(f"Sinov server ishlayapti: http://{config.HOST}:{port}", flush=True)
        else:
            import staff_bot
            import student_bot
            from tunnel import Tunnel
            if mode == "fake":
                svc.base_url = f"http://{config.HOST}:{port}"
                base_api, base_file = args.fake_tg.rstrip("/") + "/bot", args.fake_tg.rstrip("/") + "/file/bot"
            elif args._public:
                base_api = base_file = None
                svc.base_url = args._public
                log.info("doimiy manzil: %s (tunnelsiz)", svc.base_url)
            else:
                base_api = base_file = None
                try:  # kompyuter band bo'lsa ham (ffmpeg, sinovlar) server tez javob bersin
                    import ctypes
                    k32 = ctypes.windll.kernel32
                    k32.GetCurrentProcess.restype = ctypes.c_void_p
                    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                    k32.SetPriorityClass(k32.GetCurrentProcess(), 0x80)
                except Exception:
                    pass
                n = await loop.run_in_executor(None, jarayon.kill_cloudflared_under_root)
                if n:
                    log.info("eski cloudflared to'xtatildi: %s", n)
                tunnel = Tunnel(port)
                svc.base_url = await tunnel.start()
                if not svc.base_url:
                    holat.update(xato="Tunnel manzili olinmadi (internetni tekshiring). Qayta urinilmoqda.")
            talaba = student_bot.build(svc.talaba_token, svc, base_api, base_file)
            xodim = staff_bot.build(svc.xodim_token, svc, base_api, base_file)
            apps = [talaba, xodim]
            await init_bot(talaba, "Talabalar", holat, stop)
            await init_bot(xodim, "Xodimlar", holat, stop)
            if talaba.bot.id == xodim.bot.id:
                raise Fatal("Ikkala token bitta botga tegishli. Ikki xil bot kerak.")
            svc.talaba_username = talaba.bot.username
            svc.xodim_username = xodim.bot.username
            svc.pdf_sender = lambda uid, dars: student_bot.send_pdf(talaba.bot, svc, uid, dars)
            svc.notifier = lambda uid, text, label, url: student_bot.notify(talaba.bot, svc, uid, text, label, url)
            code = store.ensure_pair_code()
            await student_bot.setup_ui(talaba, svc)
            await staff_bot.setup_ui(xodim, svc)
            await sync_menus(apps, svc)
            tasks.append(asyncio.create_task(menu_guard(apps, svc, stop)))
            tasks.append(asyncio.create_task(conflict_clear(holat, stop)))
            for a, name in ((talaba, "Talabalar"), (xodim, "Xodimlar")):
                await a.start()
                await start_polling(a, name, holat, stop)
            talaba.job_queue.run_daily(student_bot.job_eslatma, time=config.ESLATMA_VAQTI, name="eslatma")
            xodim.job_queue.run_daily(staff_bot.job_hisobot, time=config.HISOBOT_VAQTI, name="hisobot")
            talaba.job_queue.run_repeating(student_bot.job_duel_muddat, interval=config.DUEL_MUDDAT_TEKSHIRUV, first=60,
                                           name="duel_muddat")
            if args.jobs_now is not None:
                talaba.job_queue.run_once(student_bot.job_eslatma, when=args.jobs_now, name="eslatma_sinov")
                xodim.job_queue.run_once(staff_bot.job_hisobot, when=args.jobs_now, name="hisobot_sinov")
                talaba.job_queue.run_once(student_bot.job_duel_muddat, when=args.jobs_now, name="duel_muddat_sinov")
            if tunnel is not None:
                tasks.append(asyncio.create_task(tunnel_watch(tunnel, svc, apps, holat, stop)))
            holat.update(holat="ishlayapti", url=svc.base_url, talaba_bot=svc.talaba_username,
                         xodim_bot=svc.xodim_username, ulash_kodi=code,
                         xato=None if svc.base_url else holat.data.get("xato"))
            log.info("botlar ishlayapti: @%s, @%s; manzil: %s", svc.talaba_username, svc.xodim_username, svc.base_url)
            if mode == "fake":
                print(f"Soxta Telegram rejimi ishlayapti: {svc.base_url}", flush=True)
        await stop.wait()
        return 0
    except asyncio.CancelledError:
        return 0
    finally:
        log.info("to'xtatilmoqda...")
        for t in tasks:
            t.cancel()
        # tartib: avval web (yangi so'rov/PDF yuborish boshlanmasin), keyin fondagi PDF vazifalari,
        # keyin botlar (ularning HTTP klienti yopiladi), oxirida tunnel
        try:
            await runner.cleanup()
        except Exception as e:
            log.warning("web serverni to'xtatishda xato: %s", e.__class__.__name__)
        bg = list(svc.bg_tasks)
        for t in bg:
            t.cancel()
        if bg or tasks:
            await asyncio.wait([*bg, *tasks], timeout=5)
        for a in reversed(apps):
            try:
                if a.updater and a.updater.running:
                    await a.updater.stop()
                if a.running:
                    await a.stop()
                await a.shutdown()
            except Exception as e:
                log.warning("bot to'xtatishda xato: %s", e.__class__.__name__)
        if tunnel is not None:
            await tunnel.stop()
        log.info("to'xtadi")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Noon Telegram ilova serveri")
    p.add_argument("--sinov", action="store_true", help="sinov rejimi: botsiz, tunnelsiz")
    p.add_argument("--port", type=int, help="port (standart 8790)")
    p.add_argument("--db", help="SQLite fayli (standart data/noon.db)")
    p.add_argument("--seed", action="store_true", help="bazani tozalab, namuna ma'lumot bilan to'ldirish (faqat --sinov)")
    p.add_argument("--fake-tg", dest="fake_tg", help="soxta Telegram manzili (tools/fake_telegram.py)")
    p.add_argument("--holat", help="holat.json yo'li")
    p.add_argument("--pid", help="main.pid yo'li")
    p.add_argument("--content", help="web/content o'rniga boshqa papka (faqat sinov)")
    p.add_argument("--videolar", help="server/videolar.json o'rniga boshqa fayl (faqat sinov)")
    p.add_argument("--jobs-now", dest="jobs_now", nargs="?", type=float, const=2.0, default=None,
                   help="kunlik vazifalarni N soniyadan keyin bir marta ishga tushirish (faqat --fake-tg)")
    p.add_argument("--log", help="log fayli")
    return p.parse_args(argv)


def _abs(p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    return q if q.is_absolute() else (config.ROOT / q)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.sinov and args.fake_tg:
        print("--sinov va --fake-tg birga ishlatilmaydi", file=sys.stderr)
        return 2
    mode = "sinov" if args.sinov else ("fake" if args.fake_tg else "prod")
    if args.seed and mode != "sinov":
        print("--seed faqat --sinov bilan ishlatiladi", file=sys.stderr)
        return 2
    if (args.content or args.videolar) and mode == "prod":
        print("--content/--videolar faqat sinov uchun", file=sys.stderr)
        return 2
    if args.jobs_now is not None and mode != "fake":
        print("--jobs-now faqat --fake-tg bilan ishlatiladi", file=sys.stderr)
        return 2
    if mode == "fake" and not (args.fake_tg.startswith("http://127.0.0.1:") or args.fake_tg.startswith("http://localhost:")):
        print("--fake-tg faqat lokal manzil bo'lishi mumkin", file=sys.stderr)
        return 2
    port = args.port or config.PORT
    db_path = _abs(args.db) or config.DB_FILE
    if args.seed and db_path.resolve() == config.DB_FILE.resolve():
        print("--seed ishchi bazaga (data/noon.db) ishlatilmaydi", file=sys.stderr)
        return 2
    if mode == "prod":
        holat_path = _abs(args.holat) or config.HOLAT_FILE
        pid_path = _abs(args.pid) or config.PID_FILE
    elif mode == "fake":
        holat_path = _abs(args.holat) or (config.DATA_DIR / f"sinov_{port}.holat.json")
        pid_path = _abs(args.pid) or (config.DATA_DIR / f"sinov_{port}.pid")
    else:
        holat_path = _abs(args.holat)
        pid_path = _abs(args.pid)
    stop_file = (pid_path or (config.DATA_DIR / f"sinov_{port}.pid")).with_suffix(".stop")

    # tokenlar
    if mode == "prod":
        env = config.load_env()
        args._talaba, args._xodim = env.get("TALABA_BOT_TOKEN", ""), env.get("XODIM_BOT_TOKEN", "")
        # doimiy server (VPS + domen): tunnel kerak emas, HTTPS ni Caddy beradi
        args._public = env.get("NOON_PUBLIC_URL", "").rstrip("/")
        if args._public and not args._public.startswith("https://"):
            print("NOON_PUBLIC_URL https:// bilan boshlanishi kerak", file=sys.stderr)
            return 2
    else:
        args._talaba, args._xodim = config.SINOV_TALABA_TOKEN, config.SINOV_XODIM_TOKEN
        args._public = ""
    # avval yagona nusxa qulfi: ikkinchi nusxa ishlab turgan serverning log fayliga tegmasin (aylantirish to'qnashuvi)
    lock = None
    if pid_path is not None:
        lock = PidLock(pid_path)
        if not lock.acquire():
            msg = "Server allaqachon ishlayapti (main.pid band). Holatni ko'rish: \"4 - Holat.bat\"."
            if sys.stderr:
                print(msg, file=sys.stderr)
            return 3
    log_path = setup_logging(mode, port, _abs(args.log), [args._talaba, args._xodim])
    holat = Holat(holat_path, port)
    try:
        try:
            stop_file.unlink()
        except OSError:
            pass
        if mode == "prod":
            if not config.ENV_FILE.is_file():
                raise Fatal("server\\.env topilmadi. Avval \"1 - Tokenlarni kiritish.bat\" ni ishga tushiring.")
            if not config.TOKEN_RE.match(args._talaba) or not config.TOKEN_RE.match(args._xodim):
                raise Fatal("server\\.env dagi tokenlar noto'g'ri. \"1 - Tokenlarni kiritish.bat\" ni qayta ishga tushiring.")
            if args._talaba == args._xodim:
                raise Fatal("Ikkala token bir xil. Ikki xil bot kerak.")
        holat.update()
        log.info("ishga tushmoqda (rejim %s, port %s, log %s)", mode, port, log_path.name)
        code = asyncio.run(amain(args, mode, port, db_path, holat, stop_file))
        holat.update(holat="to'xtadi")
        return code
    except Fatal as e:
        log.error("%s", e)
        holat.update(holat="xato", xato=str(e))
        if sys.stderr:
            print(str(e), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        holat.update(holat="to'xtadi")
        return 0
    except Exception as e:
        log.exception("kutilmagan xato")
        holat.update(holat="xato", xato=f"Kutilmagan xato: {e.__class__.__name__}. Batafsil: log\\server.log")
        return 1
    finally:
        if lock:
            lock.release()


if __name__ == "__main__":
    sys.exit(main())

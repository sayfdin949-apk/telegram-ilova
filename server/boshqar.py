"""Serverni boshqarish:  python server/boshqar.py start | stop | holat

start - server ishlamayotgan bo'lsa, pythonw main.py ni yashirin va mustaqil ishga tushiradi, yangi holat.json ni
        90 soniyagacha kutadi va havolalarni chiqaradi.
stop  - avval yumshoq to'xtatish (main.stop fayli), keyin buyruq qatorida ROOT va main.py bo'lgan jarayonlarni
        hamda ROOT ichidagi cloudflared ni to'xtatadi.
holat - hozirgi holatni chiqaradi.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import jarayon  # noqa: E402

CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def read_holat(path: Path = config.HOLAT_FILE) -> dict | None:
    for _ in range(5):
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else None
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            time.sleep(0.1)
    return None


def running_pid(pid_path: Path = config.PID_FILE, scan: bool = True) -> int | None:
    try:
        pid = int(Path(pid_path).read_text(encoding="ascii").strip() or "0")
    except (OSError, ValueError):
        pid = 0
    if pid and jarayon.pid_alive(pid) and "main.py" in jarayon.cmdline_of(pid).lower():
        return pid
    if scan:
        for p in jarayon.main_processes():
            if "--sinov" not in p["cmdline"] and "--fake-tg" not in p["cmdline"]:
                return p["pid"]
    return None


def fmt_time(s: str | None) -> str:
    try:
        return datetime.fromisoformat(s).strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return s or "-"


def print_links(h: dict, out=print) -> None:
    if h.get("talaba_bot"):
        out(f"  Talabalar boti:     https://t.me/{h['talaba_bot']}")
    if h.get("xodim_bot"):
        out(f"  Xodimlar boti:      https://t.me/{h['xodim_bot']}")
    if h.get("url"):
        out(f"  Mini App (talaba):  {h['url']}/app/")
        out(f"  Admin panel:        {h['url']}/admin/  (brauzerda: xodimlar botiga /kirish)")
    else:
        out("  Tashqi manzil hali olinmagan (tunnel). Birozdan keyin \"4 - Holat.bat\" ni ishga tushiring.")
    if h.get("ulash_kodi"):
        out("")
        out(f"  Xodimlar botiga shu kodni yuboring: {h['ulash_kodi']}")
        out("  (Kodni yuborgan odam CEO bo'ladi. Kodni boshqa hech kimga bermang.)")


def start(extra_args: list[str] | None = None, holat_path: Path = config.HOLAT_FILE, pid_path: Path = config.PID_FILE,
          wait: float = 90, out=print, scan: bool = True) -> int:
    pid = running_pid(pid_path, scan=scan)
    if pid:
        out(f"Server allaqachon ishlayapti (PID {pid}).")
        h = read_holat(holat_path)
        if h:
            print_links(h, out)
        return 0
    kochdi = config.DATA_DIR / "KOCHIRILGAN.txt"
    if not extra_args and kochdi.is_file():
        # botlar VPS da ishlayapti: shu yerda ham ishga tushsa, ikkalasi bir-biriga xalaqit beradi (409 Conflict)
        out("Botlar doimiy serverga ko'chirilgan va o'sha yerda ishlayapti:")
        out("  " + kochdi.read_text(encoding="utf-8").strip())
        out("Bu kompyuterda ishga tushirilmaydi. Holat: python tools\\deploy.py holat")
        return 1
    if not extra_args and not config.ENV_FILE.is_file():
        out("server\\.env topilmadi. Avval \"1 - Tokenlarni kiritish.bat\" ni ishga tushiring.")
        return 1
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.is_file() else Path(sys.executable)
    cmd = [str(exe), str(config.SERVER_DIR / "main.py"), *(extra_args or [])]
    t0 = time.time()
    proc = None
    for flags in (config.CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB,
                  config.CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP):
        try:
            proc = subprocess.Popen(cmd, cwd=str(config.ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, close_fds=True, creationflags=flags)
            break
        except OSError:
            continue
    if proc is None:
        out("Serverni ishga tushirib bo'lmadi.")
        return 1
    out(f"Ishga tushirilmoqda (PID {proc.pid}). {int(wait)} soniyagacha kuting...")

    def fresh(h: dict | None) -> bool:
        if not h:
            return False
        if h.get("pid") == proc.pid:
            return True
        try:
            return datetime.fromisoformat(h.get("boshlangan")).timestamp() >= t0 - 1
        except (TypeError, ValueError):
            return False

    while time.time() - t0 < wait:
        time.sleep(1)
        h = read_holat(holat_path)
        if fresh(h):
            if h.get("holat") == "xato":
                out("Xato: " + str(h.get("xato")))
                return 1
            if h.get("holat") == "ishlayapti" and h.get("url"):
                out("Botlar ishga tushdi.")
                print_links(h, out)
                out("")
                out("Kompyuterni o'chirmang va uxlatmang: botlar shu kompyuterda ishlaydi.")
                return 0
        if proc.poll() is not None:
            h = read_holat(holat_path)
            if fresh(h) and h.get("xato"):
                out("Xato: " + str(h["xato"]))
            else:
                out("Server to'xtab qoldi. Sababini log\\server.log faylida ko'ring.")
            return 1
    h = read_holat(holat_path)
    if fresh(h) and h.get("holat") == "ishlayapti":
        out("Botlar ishlayapti, lekin tashqi manzil (tunnel) hali tayyor emas.")
        print_links(h, out)
        return 0
    out(f"Server {int(wait)} soniyada tayyor bo'lmadi. \"4 - Holat.bat\" bilan tekshiring yoki log\\server.log ni ko'ring.")
    if h and h.get("xato"):
        out("Oxirgi xato: " + str(h["xato"]))
    return 1


def stop(holat_path: Path = config.HOLAT_FILE, pid_path: Path = config.PID_FILE, only_pids: set[int] | None = None,
         out=print, wait: float = 20) -> int:
    pid = running_pid(pid_path, scan=only_pids is None)
    if only_pids is not None and pid not in only_pids:
        pid = None
    if pid:
        out("To'xtatilmoqda...")
        flag = Path(pid_path).with_suffix(".stop")
        try:
            flag.write_text("stop", encoding="ascii")
        except OSError:
            pass
        t0 = time.time()
        while time.time() - t0 < wait and jarayon.pid_alive(pid):
            time.sleep(0.5)
    killed = 0
    # faqat ishchi nusxa (sinov serverlariga tegilmaydi); sinovda - faqat berilgan PID lar
    targets = jarayon.main_processes(include_tests=only_pids is not None)
    if only_pids is not None:
        targets = [p for p in targets if p["pid"] in only_pids]
    for p in targets:
        if jarayon.kill(p["pid"]):
            killed += 1
    cf = jarayon.kill_cloudflared_under_root() if only_pids is None else 0
    h = read_holat(holat_path)
    if h and h.get("holat") != "to'xtadi" and not jarayon.pid_alive(int(h.get("pid") or 0)):
        h["holat"] = "to'xtadi"
        try:
            Path(holat_path).write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
    if pid or killed or cf:
        out("To'xtatildi.")
    else:
        out("Server ishlamayotgan edi.")
    return 0


def holat(holat_path: Path = config.HOLAT_FILE, pid_path: Path = config.PID_FILE, out=print) -> int:
    h = read_holat(holat_path)
    pid = running_pid(pid_path)
    if pid:
        if h and h.get("pid") == pid:
            out(f"Holat: ishlayapti (PID {pid}, {fmt_time(h.get('boshlangan'))} dan beri)")
            print_links(h, out)
            if h.get("xato"):
                out("")
                out("Ogohlantirish: " + str(h["xato"]))
        else:
            out(f"Holat: ishlayapti (PID {pid}), ma'lumot hali yozilmagan. Birozdan keyin qayta tekshiring.")
    else:
        out("Holat: to'xtatilgan.")
        if h and h.get("xato"):
            out("Oxirgi xato: " + str(h["xato"]))
        out("Ishga tushirish: \"2 - Botlarni ishga tushirish.bat\".")
    out("Log: log\\server.log")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "holat"
    if cmd == "start":
        return start()
    if cmd == "stop":
        return stop()
    if cmd == "holat":
        return holat()
    print("Foydalanish: python server\\boshqar.py start | stop | holat")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

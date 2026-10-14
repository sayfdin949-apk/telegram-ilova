"""Botlarni doimiy serverga (VPS, Ubuntu 24.04) ko'chirish va yangilash — shu kompyuterdan.

    python tools/deploy.py kalit                      # SSH kalit yaratadi, ochiq qismini ko'rsatadi (VPS yaratishda kerak)
    python tools/deploy.py sozla IP DOMEN [--user U]  # serverni sozlaydi (Python, HTTPS, xizmat, zaxira) — botlar hali shu yerda
    python tools/deploy.py kochir --tasdiq            # bu yerdagi botlarni to'xtatib, baza+tokenlarni serverga o'tkazadi
    python tools/deploy.py yangila                    # yangi dars/test/video/kodni serverga yuboradi va qayta ishga tushiradi
    python tools/deploy.py holat                      # serverdagi holat va oxirgi log
    python tools/deploy.py zaxira                     # serverdagi oxirgi baza zaxirasini "zaxira" papkasiga yuklab oladi

Tokenlar (server/.env) faqat SSH orqali serverga yuboriladi, ekranga va logga chiqmaydi.
Parol ishlatilmaydi: kirish faqat SSH kalit bilan (~/.ssh/noon_vps).
"""
from __future__ import annotations

import io
import json
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
import config  # noqa: E402

KEY = Path.home() / ".ssh" / "noon_vps"
CFG = ROOT / "deploy" / "server.json"
KOCHDI = config.DATA_DIR / "KOCHIRILGAN.txt"
APP = "/opt/noon"


def say(*a):
    print(*a, flush=True)


def die(msg: str, code: int = 1):
    say("XATO: " + msg)
    sys.exit(code)


# ---------------------------------------------------------------- sozlama
def load_cfg() -> dict:
    if not CFG.is_file():
        die("Server hali sozlanmagan. Avval: python tools/deploy.py sozla IP DOMEN")
    return json.loads(CFG.read_text(encoding="utf-8"))


def ssh_base(c: dict) -> list[str]:
    return ["-i", str(KEY), "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=15"]


def target(c: dict) -> str:
    return f"{c.get('user', 'root')}@{c['ip']}"


def sudo(c: dict) -> str:
    return "" if c.get("user", "root") == "root" else "sudo "


def ssh(c: dict, cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(["ssh", *ssh_base(c), target(c), cmd], text=True, encoding="utf-8", errors="replace",
                       capture_output=capture)
    if check and r.returncode != 0:
        die(f"serverda buyruq bajarilmadi (kod {r.returncode})" + (f": {(r.stderr or '').strip()[:300]}" if capture else ""))
    return r


def scp(c: dict, local: Path, remote: str) -> None:
    r = subprocess.run(["scp", *ssh_base(c), "-q", str(local), f"{target(c)}:{remote}"])
    if r.returncode != 0:
        die(f"faylni yuborib bo'lmadi: {local.name}")


# ---------------------------------------------------------------- paket
def videolar() -> list[dict]:
    return json.loads(config.VIDEOLAR_FILE.read_text(encoding="utf-8"))


def build_package(dest: Path) -> int:
    """server kodi + web + videolar + deploy -> tar.gz (tokenlar, baza, loglar KIRMAYDI)."""
    n = 0

    def skip(p: Path) -> bool:
        return "__pycache__" in p.parts or p.suffix in (".pyc", ".log")

    with tarfile.open(dest, "w:gz", compresslevel=6) as tar:
        for p in sorted((ROOT / "server").glob("*.py")):
            tar.add(p, f"server/{p.name}")
            n += 1
        vs = []
        for v in videolar():
            src = Path(v["fayl"])
            if not src.is_file():
                die(f"video topilmadi: {src}")
            rel = f"video/{v['id']}{src.suffix.lower()}"
            tar.add(src, rel)
            vs.append({**v, "fayl": rel})
            n += 1
        data = json.dumps(vs, ensure_ascii=False, indent=2).encode("utf-8")
        ti = tarfile.TarInfo("server/videolar.json")
        ti.size, ti.mtime = len(data), int(time.time())
        tar.addfile(ti, io.BytesIO(data))
        for base in ("web", "deploy"):
            for p in sorted((ROOT / base).rglob("*")):
                if p.is_file() and not skip(p) and p.name != "server.json":
                    tar.add(p, p.relative_to(ROOT).as_posix())
                    n += 1
    return n


def upload_and_setup(c: dict, faqat_kod: bool) -> None:
    with tempfile.TemporaryDirectory() as td:
        pk = Path(td) / "noon.tar.gz"
        say("Paket yig'ilmoqda...")
        n = build_package(pk)
        say(f"  {n} ta fayl, {pk.stat().st_size / 1e6:.0f} MB")
        say("Serverga yuborilmoqda...")
        scp(c, pk, "/tmp/noon.tar.gz")
        scp(c, ROOT / "deploy" / "setup.sh", "/tmp/noon_setup.sh")
    say("Server sozlanmoqda (birinchi marta 3-5 daqiqa)...")
    flag = " --faqat-kod" if faqat_kod else ""
    ssh(c, f"{sudo(c)}bash /tmp/noon_setup.sh {c['domen']} /tmp/noon.tar.gz{flag} && rm -f /tmp/noon.tar.gz")


def https_ok(url: str, timeout: float = 20) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200, str(r.status)
    except Exception as e:  # noqa: BLE001
        return False, e.__class__.__name__ + ": " + str(e)[:120]


# ---------------------------------------------------------------- buyruqlar
def cmd_kalit() -> None:
    if not KEY.is_file():
        KEY.parent.mkdir(exist_ok=True)
        r = subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "noon-vps", "-f", str(KEY), "-q"])
        if r.returncode != 0:
            die("ssh-keygen ishlamadi")
        say("Yangi SSH kalit yaratildi.")
    pub = KEY.with_suffix(".pub").read_text(encoding="ascii").strip()
    (ROOT / "deploy" / "ssh_kalit_ochiq.txt").write_text(pub + "\n", encoding="ascii")
    say("VPS yaratayotganda 'SSH key' maydoniga shu qatorni joylang (bu ochiq kalit, maxfiy emas):\n")
    say(pub)


def cmd_sozla(ip: str, domen: str, user: str) -> None:
    if not KEY.is_file():
        die("SSH kalit yo'q. Avval: python tools/deploy.py kalit")
    domen = domen.lower().strip().removeprefix("https://").strip("/")
    c = {"ip": ip, "domen": domen, "user": user}
    say(f"Ulanish: {target(c)} ...")
    r = ssh(c, "cat /etc/os-release | grep -E '^(PRETTY_NAME)='", check=False, capture=True)
    if r.returncode != 0:
        die("serverga ulanib bo'lmadi. IP to'g'rimi va VPS yaratilganda SSH kalit qo'shilganmi?\n  " + (r.stderr or "").strip()[:300])
    say("  " + r.stdout.strip())
    CFG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    upload_and_setup(c, faqat_kod=False)
    try:
        got = socket.gethostbyname(domen)
    except OSError:
        got = None
    if got != ip:
        say(f"\nDIQQAT: {domen} hali bu serverga yo'naltirilmagan (DNS: {got or 'topilmadi'}, kerak: {ip}).")
        say("Domen panelida A yozuvini qo'shing; tarqalishi 5 daqiqadan bir necha soatgacha.")
    say("\nServer tayyor. Botlar hali shu kompyuterda. Ko'chirish: python tools/deploy.py kochir --tasdiq")


def cmd_kochir(tasdiq: bool) -> None:
    c = load_cfg()
    if not tasdiq:
        die("Bu buyruq shu kompyuterdagi botlarni to'xtatadi. Ishonchingiz komil bo'lsa: kochir --tasdiq")
    try:
        got = socket.gethostbyname(c["domen"])
    except OSError:
        got = None
    if got != c["ip"]:
        die(f"{c['domen']} hali {c['ip']} ga yo'naltirilmagan (DNS: {got or 'topilmadi'}). Domen panelida A yozuvini tekshiring.")
    env = config.load_env()
    if not env.get("TALABA_BOT_TOKEN") or not env.get("XODIM_BOT_TOKEN"):
        die("server/.env da tokenlar yo'q")
    url = f"https://{c['domen']}"

    say("1/5 Shu kompyuterdagi botlar to'xtatilmoqda...")
    subprocess.run([sys.executable, str(ROOT / "server" / "boshqar.py"), "stop"])
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        say("2/5 Baza nusxasi olinmoqda...")
        db = td / "noon.db"
        src = sqlite3.connect(config.DB_FILE)
        dst = sqlite3.connect(db)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
        lines = [f"{k}={v}" for k, v in env.items() if k != "NOON_PUBLIC_URL"] + [f"NOON_PUBLIC_URL={url}"]
        envf = td / "env"
        envf.write_text("\n".join(lines) + "\n", encoding="utf-8")
        say("3/5 Baza, kalit va tokenlar serverga yuborilmoqda (ekranga chiqmaydi)...")
        ssh(c, f"{sudo(c)}systemctl stop noon || true", check=False)
        scp(c, db, "/tmp/noon.db")
        scp(c, config.SECRET_FILE, "/tmp/noon_secret.key")
        scp(c, envf, "/tmp/noon_env")
    s = sudo(c)
    ssh(c, f"{s}install -o noon -g noon -m 600 /tmp/noon.db {APP}/data/noon.db && "
           f"{s}rm -f {APP}/data/noon.db-wal {APP}/data/noon.db-shm && "
           f"{s}install -o noon -g noon -m 600 /tmp/noon_secret.key {APP}/data/secret.key && "
           f"{s}install -o noon -g noon -m 600 /tmp/noon_env {APP}/server/.env && "
           f"{s}rm -f /tmp/noon.db /tmp/noon_secret.key /tmp/noon_env && {s}systemctl restart noon")
    say("4/5 Serverda botlar ishga tushmoqda...")
    ok, info = False, ""
    for _ in range(18):
        time.sleep(5)
        r = ssh(c, f"{s}cat {APP}/data/holat.json 2>/dev/null", check=False, capture=True)
        try:
            h = json.loads(r.stdout or "{}")
        except ValueError:
            h = {}
        if h.get("holat") == "ishlayapti":
            ok, info = https_ok(url + "/app/")
            if ok:
                break
        info = info or h.get("xato") or h.get("holat") or "javob yo'q"
    if not ok:
        say(f"Serverda ishga tushmadi ({info}). Orqaga qaytarilmoqda: botlar yana shu kompyuterda ishlaydi.")
        ssh(c, f"{s}systemctl stop noon", check=False)
        subprocess.run([sys.executable, str(ROOT / "server" / "boshqar.py"), "start"])
        ssh(c, f"{s}journalctl -u noon -n 25 --no-pager", check=False)
        sys.exit(1)
    KOCHDI.write_text(f"{url}  (server {c['ip']}, {time.strftime('%Y-%m-%d %H:%M')})\n", encoding="utf-8")
    say("5/5 Tayyor.")
    say(f"  Mini App:  {url}/app/")
    say(f"  Admin panel:  {url}/admin/  (brauzerda: xodimlar botiga /kirish)")
    say("Botlar endi serverda ishlaydi — bu kompyuter o'chsa ham.")


def cmd_yangila() -> None:
    c = load_cfg()
    upload_and_setup(c, faqat_kod=True)
    ok, info = https_ok(f"https://{c['domen']}/app/")
    say("Yangilandi." if ok else f"Diqqat: sayt javob bermadi ({info}). Holat: python tools/deploy.py holat")


def cmd_holat() -> None:
    c = load_cfg()
    s = sudo(c)
    ssh(c, f"echo '-- xizmat:'; {s}systemctl is-active noon; echo '-- holat:'; {s}cat {APP}/data/holat.json 2>/dev/null | "
           f"grep -E '\"(holat|url|boshlangan|xato)\"'; echo '-- disk:'; df -h / | tail -1; echo '-- zaxiralar:'; "
           f"ls -1t {APP}/backup 2>/dev/null | head -3; echo '-- oxirgi log:'; {s}tail -n 8 {APP}/log/server.log", check=False)
    ok, info = https_ok(f"https://{c['domen']}/app/")
    say(f"-- https://{c['domen']}/app/ : {'ishlayapti' if ok else info}")


def cmd_zaxira() -> None:
    c = load_cfg()
    r = ssh(c, f"ls -1t {APP}/backup/noon-*.db 2>/dev/null | head -1", check=False, capture=True)
    f = (r.stdout or "").strip()
    if not f:
        die("serverda hali zaxira yo'q (har kuni tunda olinadi)")
    out = ROOT / "zaxira"
    out.mkdir(exist_ok=True)
    rr = subprocess.run(["scp", *ssh_base(c), "-q", f"{target(c)}:{f}", str(out / Path(f).name)])
    if rr.returncode != 0:
        die("yuklab bo'lmadi")
    say(f"Saqlandi: {out / Path(f).name}")


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        say(__doc__)
        return
    cmd, rest = argv[1], argv[2:]
    if cmd == "kalit":
        cmd_kalit()
    elif cmd == "sozla":
        user = "root"
        if "--user" in rest:
            i = rest.index("--user")
            user = rest[i + 1]
            rest = rest[:i] + rest[i + 2:]
        if len(rest) != 2:
            die("ishlatish: sozla IP DOMEN [--user U]")
        cmd_sozla(rest[0], rest[1], user)
    elif cmd == "kochir":
        cmd_kochir("--tasdiq" in rest)
    elif cmd == "yangila":
        cmd_yangila()
    elif cmd == "holat":
        cmd_holat()
    elif cmd == "zaxira":
        cmd_zaxira()
    else:
        die(f"noma'lum buyruq: {cmd}")


if __name__ == "__main__":
    main(sys.argv)

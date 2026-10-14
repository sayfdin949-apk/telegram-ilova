"""Windows jarayonlari bilan ishlash: ro'yxat, tirikligini tekshirish, to'xtatish.

psutil bo'lsa undan, bo'lmasa PowerShell (Get-CimInstance) dan foydalanadi.
Faqat ROOT ichidagi narsalar to'xtatiladi - boshqa dasturlarga tegilmaydi.
"""
from __future__ import annotations

import json
import os
import subprocess

import config

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


def _ps_json(script: str) -> list[dict]:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, timeout=60, creationflags=config.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return []
    out = (r.stdout or "").strip()
    if not out:
        return []
    try:
        d = json.loads(out)
    except ValueError:
        return []
    return d if isinstance(d, list) else [d]


def processes(names: tuple[str, ...]) -> list[dict]:
    """[{pid, name, exe, cmdline}] berilgan nomli (masalan 'python.exe') jarayonlar."""
    names_l = {n.lower() for n in names}
    res = []
    if psutil is not None:
        for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                info = p.info
                if (info.get("name") or "").lower() not in names_l:
                    continue
                cmd = info.get("cmdline") or []
                res.append({"pid": info["pid"], "name": info.get("name") or "", "exe": info.get("exe") or "",
                            "cmdline": subprocess.list2cmdline(cmd) if isinstance(cmd, list) else str(cmd)})
            except Exception:
                continue
        return res
    flt = " OR ".join(f"Name='{n}'" for n in names)
    rows = _ps_json(f'Get-CimInstance Win32_Process -Filter "{flt}" | '
                    "Select-Object ProcessId, Name, ExecutablePath, CommandLine | ConvertTo-Json -Compress")
    for r in rows:
        res.append({"pid": int(r.get("ProcessId") or 0), "name": r.get("Name") or "",
                    "exe": r.get("ExecutablePath") or "", "cmdline": r.get("CommandLine") or ""})
    return res


def pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    if psutil is not None:
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False
    rows = _ps_json(f'Get-CimInstance Win32_Process -Filter "ProcessId={int(pid)}" | Select-Object ProcessId | ConvertTo-Json -Compress')
    return bool(rows)


def cmdline_of(pid: int) -> str:
    if psutil is not None:
        try:
            return subprocess.list2cmdline(psutil.Process(pid).cmdline())
        except Exception:
            return ""
    rows = _ps_json(f'Get-CimInstance Win32_Process -Filter "ProcessId={int(pid)}" | Select-Object CommandLine | ConvertTo-Json -Compress')
    return (rows[0].get("CommandLine") or "") if rows else ""


def kill(pid: int) -> bool:
    if not pid or pid == os.getpid():
        return False
    if psutil is not None:
        try:
            p = psutil.Process(pid)
            p.kill()
            try:
                p.wait(10)
            except Exception:
                pass
            return True
        except Exception:
            return False
    try:
        r = subprocess.run(["taskkill", "/PID", str(int(pid)), "/F"], capture_output=True, timeout=30,
                           creationflags=config.CREATE_NO_WINDOW)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _under_root(path: str) -> bool:
    if not path:
        return False
    try:
        return os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(str(config.ROOT)) + os.sep)
    except (ValueError, OSError):
        return False


def cloudflared_under_root() -> list[dict]:
    return [p for p in processes(("cloudflared.exe",)) if _under_root(p["exe"])]


def kill_cloudflared_under_root() -> int:
    n = 0
    for p in cloudflared_under_root():
        if kill(p["pid"]):
            n += 1
    return n


TEST_FLAGS = ("--sinov", "--fake-tg")


def is_test_cmdline(cmdline: str) -> bool:
    """Sinov nusxasi (--sinov / --fake-tg): ishchi serverni to'xtatishda ularga tegilmaydi."""
    c = (cmdline or "").lower()
    return any(f in c for f in TEST_FLAGS)


def is_main_cmdline(cmdline: str) -> bool:
    c = (cmdline or "").lower()
    return str(config.ROOT).lower() in c and "main.py" in c


def main_processes(include_tests: bool = False) -> list[dict]:
    """Buyruq qatorida ROOT va main.py bo'lgan python jarayonlari (ishlab turgan server).
    Standart: faqat ishchi nusxa (sinov serverlari - --sinov / --fake-tg - kirmaydi)."""
    out = []
    for p in processes(("python.exe", "pythonw.exe", "py.exe")):
        if p["pid"] == os.getpid() or not is_main_cmdline(p["cmdline"]):
            continue
        if not include_tests and is_test_cmdline(p["cmdline"]):
            continue
        out.append(p)
    return out

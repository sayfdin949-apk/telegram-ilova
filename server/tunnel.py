"""cloudflared quick tunnel: tashqi HTTPS manzil (https://*.trycloudflare.com), har ishga tushganda yangi.

server/bin/cloudflared.exe tunnel --url http://127.0.0.1:PORT --no-autoupdate
Manzil cloudflared ning stderr chiqishidan olinadi; keyin stderr doim o'qib turiladi (bufer to'lib qolmasligi uchun).
"""
from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import time
from pathlib import Path

import config

log = logging.getLogger("noon.tunnel")
URL_RE = re.compile(r"https://(?!api\.)[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com")


def parse_url(line: str) -> str | None:
    m = URL_RE.search(line or "")
    return m.group(0) if m else None


class Tunnel:
    def __init__(self, port: int, exe: Path = config.CLOUDFLARED, args: list[str] | None = None):
        self.port = port
        self.exe = Path(exe)
        self.args = args if args is not None else ["tunnel", "--protocol", "http2", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]
        self.proc: asyncio.subprocess.Process | None = None
        self.url: str | None = None
        self.ready = False
        self.dead = False
        self._drain_task: asyncio.Task | None = None
        self._last_err = 0.0

    def alive(self) -> bool:
        # jarayon tirik bo'lsa ham, Cloudflare quick tunnelni o'chirib yuborgan bo'lishi mumkin (uzoq internet uzilishidan keyin)
        return self.proc is not None and self.proc.returncode is None and not self.dead

    async def start(self, timeout: float = 90) -> str | None:
        await self.stop()
        self.url, self.ready, self.dead = None, False, False
        if not self.exe.is_file():
            log.error("cloudflared topilmadi: %s", self.exe)
            return None
        try:
            self.proc = await asyncio.create_subprocess_exec(
                str(self.exe), *self.args,
                stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
                creationflags=config.CREATE_NO_WINDOW | getattr(subprocess, "HIGH_PRIORITY_CLASS", 0))
        except OSError as e:
            log.error("cloudflared ishga tushmadi: %s", e)
            self.proc = None
            return None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while self.url is None:
            left = deadline - loop.time()
            if left <= 0:
                break
            try:
                line = await asyncio.wait_for(self.proc.stderr.readline(), left)
            except (asyncio.TimeoutError, ValueError):
                break
            if not line:
                break
            self.url = parse_url(line.decode("utf-8", "ignore"))
        if self.url:
            # manzil chiqdi; ulanish ro'yxatdan o'tishini qisqa kutamiz (bo'lmasa ham davom etamiz)
            deadline = loop.time() + 25
            while not self.ready:
                left = deadline - loop.time()
                if left <= 0:
                    break
                try:
                    line = await asyncio.wait_for(self.proc.stderr.readline(), left)
                except (asyncio.TimeoutError, ValueError):
                    break
                if not line:
                    break
                if "Registered tunnel connection" in line.decode("utf-8", "ignore"):
                    self.ready = True
            self._drain_task = asyncio.create_task(self._drain(self.proc))
            log.info("tunnel: %s (tayyor=%s)", self.url, self.ready)
            return self.url
        log.error("tunnel manzili olinmadi")
        await self.stop()
        return None

    async def _drain(self, proc: asyncio.subprocess.Process) -> None:
        try:
            while proc.returncode is None:
                line = await proc.stderr.readline()
                if not line:
                    break
                s = line.decode("utf-8", "ignore")
                if "Tunnel not found" in s and not self.dead:
                    self.dead = True
                    log.warning("tunnel: Cloudflare manzilni o'chirgan - yangisi olinadi")
                if " ERR " in s and time.monotonic() - self._last_err > 10:
                    self._last_err = time.monotonic()
                    log.warning("tunnel: %s", s.strip()[:300])
        except (asyncio.CancelledError, OSError, ValueError):
            pass

    async def stop(self) -> None:
        p = self.proc
        if p is not None and p.returncode is None:
            try:
                p.kill()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(p.wait(), 10)
            except (asyncio.TimeoutError, ProcessLookupError):
                pass
        t = self._drain_task
        self._drain_task = None
        if p is self.proc:
            self.proc = None
        if t is not None and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                cur = asyncio.current_task()
                if cur is not None and cur.cancelling():
                    raise  # bizni ham to'xtatishyapti - bekor qilishni yutib yubormaymiz
            except Exception:
                pass

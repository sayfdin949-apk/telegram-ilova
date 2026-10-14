"""Soxta Telegram Bot API serveri - FAQAT sinov uchun (haqiqiy Telegramga hech narsa yuborilmaydi).

Server main.py ni `--fake-tg http://127.0.0.1:PORT` bilan ishga tushiring: ikkala bot shu serverga ulanadi.
Qo'llab-quvvatlanadigan usullar: getMe, getUpdates (long-poll), sendMessage, sendDocument, setMyCommands,
setChatMenuButton, setMyDescription, setMyShortDescription, deleteWebhook (+ getMyCommands, getChatMenuButton,
answerCallbackQuery, close, logOut).

Python ichidan (sinovlarda):
    fake = FakeTelegram(); url = fake.start()            # alohida oqimda ishlaydi
    fake.push_message("talaba", {"id": 700001, "first_name": "Ali"}, "/start dars8")
    fake.wait_for(lambda c: c["method"] == "sendMessage" and c["chat_id"] == 700001)
    fake.block(700002)                                   # bu chatga yuborish 403 Forbidden qaytaradi
    fake.stop()

Buyruq qatoridan:  python tools/fake_telegram.py --port 8899
    POST /_ctl/push   {"bot": "talaba"|"xodim", "from": {...}, "text": "..."}
    GET  /_ctl/calls[?bot=talaba&method=sendMessage]
    POST /_ctl/block  {"chat_id": 700002}
"""
from __future__ import annotations

import argparse
import asyncio
import json
import threading
import time

from aiohttp import web

SINOV_TALABA_TOKEN = "1111111111:SINOVtalabaAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
SINOV_XODIM_TOKEN = "2222222222:SINOVxodimBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

DEFAULT_BOTS = {
    "talaba": {"token": SINOV_TALABA_TOKEN, "id": 1111111111, "username": "noon_talaba_sinov_bot",
               "first_name": "Muhammadamin darslar"},
    "xodim": {"token": SINOV_XODIM_TOKEN, "id": 2222222222, "username": "noon_xodim_sinov_bot",
              "first_name": "Muhammadamin boshqaruv"},
}
JSON_PARAMS = {"reply_markup", "menu_button", "commands", "allowed_updates", "scope", "entities",
               "caption_entities", "link_preview_options", "reply_parameters"}


class FakeTelegram:
    def __init__(self, bots: dict | None = None):
        self.bots = bots or DEFAULT_BOTS
        self.by_token = {b["token"]: k for k, b in self.bots.items()}
        self.calls: list[dict] = []
        self.queues: dict[str, list] = {k: [] for k in self.bots}
        self.next_update = {k: 1 for k in self.bots}
        self.polls = {k: 0 for k in self.bots}
        self.fail_once: set[str] = set()       # shu usullarning har bot uchun birinchi chaqiruvi 500 qaytaradi
        self.conflict_polls = 0                # shuncha getUpdates 409 Conflict qaytaradi (boshqa nusxa polling qilayotgandek)
        self.conflicts_sent = 0
        self._failed: set[tuple[str, str]] = set()
        self.blocked: set[int] = set()
        self.msg_id = 1000
        self.file_n = 0
        self.lock = threading.Lock()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.events: dict[str, asyncio.Event] = {}
        self.runner: web.AppRunner | None = None
        self.thread: threading.Thread | None = None
        self.url: str | None = None
        self._ready = threading.Event()

    # ------------------------------------------------------------ HTTP
    def build_app(self) -> web.Application:
        app = web.Application(client_max_size=60 * 1024 * 1024)
        app.router.add_route("*", "/bot{token}/{method}", self.handle)
        app.router.add_post("/_ctl/push", self.ctl_push)
        app.router.add_get("/_ctl/calls", self.ctl_calls)
        app.router.add_post("/_ctl/block", self.ctl_block)
        return app

    @staticmethod
    def _err(code: int, desc: str) -> web.Response:
        return web.json_response({"ok": False, "error_code": code, "description": desc}, status=code)

    async def _params(self, request: web.Request) -> tuple[dict, dict]:
        params: dict = {}
        files: dict = {}
        params.update(request.query)
        ctype = request.content_type or ""
        if ctype.startswith("multipart/"):
            reader = await request.multipart()
            async for part in reader:
                if part.filename:
                    data = await part.read()
                    files[part.name] = {"filename": part.filename, "size": len(data)}
                else:
                    params[part.name] = await part.text()
        elif request.can_read_body:
            if ctype == "application/json":
                try:
                    params.update(await request.json())
                except ValueError:
                    pass
            else:
                params.update(await request.post())
        out = {}
        for k, v in params.items():
            if k in JSON_PARAMS and isinstance(v, str):
                try:
                    v = json.loads(v)
                except ValueError:
                    pass
            out[k] = v
        return out, files

    def _record(self, bot: str, method: str, params: dict, files: dict) -> dict:
        call = {"bot": bot, "method": method, "params": params, "files": files, "t": time.time()}
        cid = params.get("chat_id")
        if cid is not None:
            try:
                call["chat_id"] = int(cid)
            except (TypeError, ValueError):
                call["chat_id"] = cid
        with self.lock:
            self.calls.append(call)
        return call

    def _bot_user(self, bot: str) -> dict:
        b = self.bots[bot]
        return {"id": b["id"], "is_bot": True, "first_name": b["first_name"], "username": b["username"],
                "can_join_groups": True, "can_read_all_group_messages": False, "supports_inline_queries": False,
                "can_connect_to_business": False, "has_main_web_app": False}

    def _message(self, bot: str, chat_id: int, **extra) -> dict:
        with self.lock:
            self.msg_id += 1
            mid = self.msg_id
        m = {"message_id": mid, "date": int(time.time()), "chat": {"id": chat_id, "type": "private"},
             "from": self._bot_user(bot)}
        m.update(extra)
        return m

    async def handle(self, request: web.Request) -> web.Response:
        token = request.match_info["token"]
        method = request.match_info["method"]
        bot = self.by_token.get(token)
        if bot is None:
            return self._err(401, "Unauthorized")
        params, files = await self._params(request)
        m = method.lower()
        if method != "getUpdates":
            call = self._record(bot, method, params, files)
            if m in self.fail_once and (bot, m) not in self._failed:
                self._failed.add((bot, m))
                call["failed"] = True
                return self._err(500, "Internal Server Error: fake fail_once")
        ok = lambda result: web.json_response({"ok": True, "result": result})  # noqa: E731
        if m == "getme":
            return ok(self._bot_user(bot))
        if m == "deletewebhook":
            if str(params.get("drop_pending_updates", "")).lower() == "true":
                with self.lock:
                    self.queues[bot].clear()
            return ok(True)
        if m == "getupdates":
            with self.lock:
                conflict = self.conflict_polls > 0
                if conflict:
                    self.conflict_polls -= 1
                    self.conflicts_sent += 1
            if conflict:
                return self._err(409, "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running")
            return ok(await self._get_updates(bot, params))
        if m in ("setmycommands", "setchatmenubutton", "setmydescription", "setmyshortdescription",
                 "answercallbackquery", "close", "logout", "setmyname"):
            return ok(True)
        if m == "getmycommands":
            return ok([])
        if m == "getchatmenubutton":
            return ok({"type": "default"})
        if m in ("sendmessage", "senddocument"):
            try:
                chat_id = int(params.get("chat_id"))
            except (TypeError, ValueError):
                return self._err(400, "Bad Request: chat_id is empty")
            if chat_id in self.blocked:
                return self._err(403, "Forbidden: bot was blocked by the user")
            if m == "sendmessage":
                return ok(self._message(bot, chat_id, text=params.get("text", "")))
            doc = params.get("document")
            if "document" in files:
                with self.lock:
                    self.file_n += 1
                    fid = f"FAKEFILE{self.file_n:04d}"
                fname, size = files["document"]["filename"], files["document"]["size"]
            elif isinstance(doc, str) and doc:
                fid, fname, size = doc, "cached.pdf", 0
            else:
                return self._err(400, "Bad Request: there is no document in the request")
            return ok(self._message(bot, chat_id, caption=params.get("caption", ""),
                                    document={"file_id": fid, "file_unique_id": "U" + fid, "file_name": fname,
                                              "file_size": size, "mime_type": "application/pdf"}))
        return self._err(400, f"Bad Request: method {method} is not supported by fake server")

    async def _get_updates(self, bot: str, params: dict) -> list:
        try:
            offset = int(params.get("offset", 0) or 0)
        except ValueError:
            offset = 0
        try:
            timeout = float(params.get("timeout", 0) or 0)
        except ValueError:
            timeout = 0.0
        try:
            limit = int(params.get("limit", 100) or 100)
        except ValueError:
            limit = 100
        deadline = time.monotonic() + min(timeout, 30)
        with self.lock:
            self.polls[bot] += 1
        ev = self.events[bot]
        while True:
            ev.clear()
            with self.lock:
                if offset:
                    self.queues[bot] = [u for u in self.queues[bot] if u["update_id"] >= offset]
                ready = list(self.queues[bot][:limit])
            if ready or time.monotonic() >= deadline:
                return ready
            try:
                await asyncio.wait_for(ev.wait(), max(0.01, deadline - time.monotonic()))
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------ boshqaruv (HTTP)
    async def ctl_push(self, request: web.Request) -> web.Response:
        d = await request.json()
        uid = self._push(d["bot"], d["from"], d["text"])
        return web.json_response({"ok": True, "update_id": uid})

    async def ctl_calls(self, request: web.Request) -> web.Response:
        return web.json_response(self.get_calls(request.query.get("bot"), request.query.get("method")))

    async def ctl_block(self, request: web.Request) -> web.Response:
        d = await request.json()
        self.blocked.add(int(d["chat_id"]))
        return web.json_response({"ok": True})

    # ------------------------------------------------------------ boshqaruv (Python)
    def _push(self, bot: str, frm: dict, text: str) -> int:
        frm = dict(frm)
        frm.setdefault("is_bot", False)
        frm.setdefault("first_name", "Sinov")
        with self.lock:
            uid = self.next_update[bot]
            self.next_update[bot] += 1
            self.msg_id += 1
            msg = {"message_id": self.msg_id, "date": int(time.time()),
                   "chat": {"id": frm["id"], "type": "private", "first_name": frm.get("first_name"),
                            "username": frm.get("username")},
                   "from": frm, "text": text}
            if text.startswith("/"):
                cmd = text.split()[0]
                msg["entities"] = [{"type": "bot_command", "offset": 0, "length": len(cmd)}]
            self.queues[bot].append({"update_id": uid, "message": msg})
        if self.loop and bot in self.events:
            self.loop.call_soon_threadsafe(self.events[bot].set)
        return uid

    def push_message(self, bot: str, frm: dict, text: str) -> int:
        return self._push(bot, frm, text)

    def block(self, chat_id: int) -> None:
        self.blocked.add(int(chat_id))

    def get_calls(self, bot: str | None = None, method: str | None = None) -> list[dict]:
        with self.lock:
            return [c for c in self.calls if (bot is None or c["bot"] == bot) and (method is None or c["method"] == method)]

    def wait_for(self, pred, timeout: float = 15.0, start: int = 0) -> dict | None:
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self.lock:
                for c in self.calls[start:]:
                    if pred(c):
                        return c
            time.sleep(0.05)
        return None

    def mark(self) -> int:
        with self.lock:
            return len(self.calls)

    # ------------------------------------------------------------ ishga tushirish
    def start(self, port: int = 0) -> str:
        def run():
            loop = asyncio.new_event_loop()
            self.loop = loop
            asyncio.set_event_loop(loop)
            self.events = {k: asyncio.Event() for k in self.bots}

            async def boot():
                self.runner = web.AppRunner(self.build_app(), access_log=None)
                await self.runner.setup()
                site = web.TCPSite(self.runner, "127.0.0.1", port)
                await site.start()
                real = site._server.sockets[0].getsockname()[1]
                self.url = f"http://127.0.0.1:{real}"
                self._ready.set()
            loop.run_until_complete(boot())
            loop.run_forever()
            loop.run_until_complete(self.runner.cleanup())
            loop.close()
        self.thread = threading.Thread(target=run, name="fake-telegram", daemon=True)
        self.thread.start()
        if not self._ready.wait(15):
            raise RuntimeError("fake telegram ishga tushmadi")
        return self.url

    def stop(self) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(10)


def main() -> None:
    ap = argparse.ArgumentParser(description="Soxta Telegram Bot API (sinov)")
    ap.add_argument("--port", type=int, default=8899)
    a = ap.parse_args()
    fake = FakeTelegram()
    url = fake.start(a.port)
    print(f"Soxta Telegram: {url}  (to'xtatish: Ctrl+C)", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fake.stop()


if __name__ == "__main__":
    main()

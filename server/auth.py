"""Telegram WebApp initData imzosini tekshirish va panel tokenlari (HMAC-SHA256).

initData: secret = HMAC_SHA256(key="WebAppData", msg=bot_token); hash = HMAC_SHA256(secret, data_check_string).
Panel token: base64url(JSON {"id","role","exp"}) + "." + hex HMAC-SHA256(data/secret.key, payload).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import urllib.parse
from pathlib import Path

import config

MAX_INITDATA = 8192
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_B64URL = re.compile(r"^[A-Za-z0-9_-]{1,400}$")


def check_init_data(init_data: str, token: str, max_age: int, now: float | None = None) -> dict | None:
    """To'g'ri bo'lsa initData.user (dict, int id bilan), aks holda None."""
    if not init_data or not token or not isinstance(init_data, str) or len(init_data) > MAX_INITDATA:
        return None
    try:
        pairs = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    h = pairs.pop("hash", None)
    if not h or not _HEX64.fullmatch(h):
        return None
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, h.lower()):
        return None
    try:
        auth_date = int(pairs.get("auth_date", "0"))
        user = json.loads(pairs.get("user", "null"))
    except ValueError:
        return None
    t = time.time() if now is None else now
    if auth_date <= 0 or t - auth_date > max_age or auth_date - t > 24 * 3600:
        return None
    if not isinstance(user, dict):
        return None
    uid = user.get("id")
    if not isinstance(uid, int) or isinstance(uid, bool) or uid <= 0:
        return None
    return user


# ---------------------------------------------------------------- maxfiy kalit
def load_secret(path: Path = config.SECRET_FILE) -> bytes:
    """data/secret.key (32 tasodifiy bayt). Yo'q bo'lsa yaratadi (bir vaqtda ishga tushgan jarayonlarga chidamli)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(50):
        try:
            data = path.read_bytes()
            if len(data) >= 32:
                return data[:32]
        except FileNotFoundError:
            try:
                fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
            except FileExistsError:
                pass
            else:
                key = os.urandom(32)
                with os.fdopen(fd, "wb") as f:
                    f.write(key)
                return key
        time.sleep(0.05)
    raise RuntimeError("secret.key o'qilmadi")


# ---------------------------------------------------------------- panel tokeni
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_panel_token(key: bytes, uid: int, role: str, ttl: int = config.PANEL_TOKEN_MUDDAT,
                     now: float | None = None) -> str:
    exp = int((time.time() if now is None else now) + ttl)
    payload = _b64e(json.dumps({"id": int(uid), "role": role, "exp": exp}, separators=(",", ":")).encode())
    sig = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_panel_token(key: bytes, token: str, now: float | None = None) -> dict | None:
    if not token or not isinstance(token, str) or len(token) > 512 or token.count(".") != 1:
        return None
    payload, sig = token.split(".")
    if not _B64URL.fullmatch(payload) or not _HEX64.fullmatch(sig):
        return None
    calc = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, sig.lower()):
        return None
    try:
        d = json.loads(_b64d(payload))
    except (ValueError, TypeError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("id"), int) or not isinstance(d.get("exp"), int):
        return None
    if d.get("role") not in config.ROLLAR:
        return None
    if d["exp"] <= (time.time() if now is None else now):
        return None
    return d


def panel_allowed(role: str, name: str, rejim: str | None) -> bool:
    """Rol shu panel faylini shu rejimda ochishi mumkinmi (config.ROL_PANELLARI bo'yicha)."""
    for key in config.ROL_PANELLARI.get(role, ()):
        f, r, _ = config.PANELLAR[key]
        if f == name and (r or None) == (rejim or None):
            return True
    return False


def panels_for(role: str, token: str) -> list[dict]:
    out = []
    t = urllib.parse.quote(token, safe="")
    for key in config.ROL_PANELLARI.get(role, ()):
        f, r, nomi = config.PANELLAR[key]
        q = f"?rejim={r}&t={t}" if r else f"?t={t}"
        out.append({"key": key, "nomi": nomi, "url": f"/staff/p/{f}{q}"})
    return out

"""Sinov uchun imzolangan Telegram WebApp initData yasash (faqat soxta SINOV tokenlari bilan).

    from sinov_initdata import make, TALABA, XODIM, SINOV_TALABA_TOKEN, SINOV_XODIM_TOKEN
    init = make(SINOV_TALABA_TOKEN, TALABA["aziza"])

Buyruq qatori:  python tools/sinov_initdata.py talaba aziza   |   python tools/sinov_initdata.py xodim ceo
"""
import hashlib
import hmac
import json
import sys
import time
import urllib.parse

SINOV_TALABA_TOKEN = "1111111111:SINOVtalabaAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
SINOV_XODIM_TOKEN = "2222222222:SINOVxodimBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

TALABA = {
    "aziza": {"id": 800001, "first_name": "Aziza", "last_name": "Karimova", "username": "aziza_k", "language_code": "uz"},
    "jahongir": {"id": 800002, "first_name": "Jahongir", "last_name": "Rasulov", "username": "jahongir_r", "language_code": "uz"},
    "yangi": {"id": 800099, "first_name": "Sardor", "last_name": "", "username": "", "language_code": "uz"},
}
XODIM = {
    "ceo": {"id": 900001, "first_name": "Muhammad", "last_name": "Amin", "username": "muhammad_amin", "language_code": "uz"},
    "admin": {"id": 900002, "first_name": "Nodira", "last_name": "Salimova", "username": "nodira_s", "language_code": "uz"},
    "ustoz": {"id": 900003, "first_name": "Dilnoza", "last_name": "Karimova", "username": "dilnoza_k", "language_code": "uz"},
    "assistent": {"id": 900004, "first_name": "Bekzod", "last_name": "Aliyev", "username": "bekzod_a", "language_code": "uz"},
    "begona": {"id": 800001, "first_name": "Aziza", "last_name": "Karimova", "username": "aziza_k", "language_code": "uz"},
}


def make(token: str, user: dict, auth_date: int | None = None, extra: dict | None = None) -> str:
    """Telegram qoidasi bo'yicha: secret = HMAC_SHA256("WebAppData", token); hash = HMAC_SHA256(secret, data_check_string)."""
    pairs = {
        "auth_date": str(int(auth_date if auth_date is not None else time.time())),
        "query_id": "AAHsinov0000",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    if extra:
        pairs.update({k: str(v) for k, v in extra.items()})
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(pairs)


if __name__ == "__main__":
    kim, nom = (sys.argv[1:3] + ["talaba", "aziza"][len(sys.argv[1:3]):])[:2]
    if kim == "talaba":
        print(make(SINOV_TALABA_TOKEN, TALABA[nom]))
    else:
        print(make(SINOV_XODIM_TOKEN, XODIM[nom]))

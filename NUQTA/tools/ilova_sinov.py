#!/usr/bin/env python
"""Ilova STAGING dagi jonli taqdimotni ilovadagidek (iframe + postMessage) sinash.
Lokal http (shu jarayon ichida, NUQTA\\web ildizi) — jonli server va jonli web\\ ga tegilmaydi.

    python ilova_sinov.py [--chiqish DIR]

Har holat (dars, so'zli slayd k — dars ichidagi raqam):
  1. iframe: /content/taqdimot/<dek>/index.html?from=F&to=T&start=1 -> {noon:'slide', n:1, total:T-F+1}
  2. {noon:'goto', n:k} -> n=k; hamma bosqich {noon:'next'} bilan ochiladi
  3. so'zni bosish (1280 — sichqoncha, telefon — barmoq) -> audio.play(ovoz/<id>.mp3); slayd o'zgarmaydi, 'end' yo'q
  4. ovoz/<id>.mp3 — http 200, audio/mpeg
  5. {noon:'next'} -> n=k+1 (navigatsiya buzilmagan); 1280 da: oxirgi slayddan keyin {noon:'end'}
Skrinshot (so'z «o'ynayotgan» holatda): 1280x720, 844x390 (telefon yotiq), 390x844 (tik) -> DIR\\dNN_<en>.png,
kontakt DIR\\kontakt.png, natija DIR\\natija.json. Chiqish kodi 1 — biror tekshiruv o'tmasa.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

ST = Path(__file__).resolve().parent.parent           # Telegram ilova\NUQTA
WEB = ST / "web"
KURS = WEB / "content" / "kurs.json"
HOLATLAR = [(1, 4), (2, 4), (3, 8), (4, 4)]           # (dars, so'zli slayd — dars ichida)
KORINISH = [("1280", {"width": 1280, "height": 720}, False),
            ("844x390", {"width": 844, "height": 390}, True),
            ("390x844", {"width": 390, "height": 844}, True)]

INIT = r"""
(() => {
  window.__plays = [];
  const op = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    window.__plays.push(String(this.src || this.currentSrc || '').slice(-60));
    try { const r = op.call(this); return r && r.catch ? r.catch(() => {}) : r; } catch (e) { return Promise.resolve(); }
  };
})();
"""

HARNESS = """<!doctype html><html lang="uz" data-nuqta="fixed" data-v="sahro" data-m="kun"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ilova sinovi</title>
<style>html,body{margin:0;height:100%;background:#E8DABA}iframe{border:0;width:100%;height:100%;display:block}</style></head>
<body><iframe id="f" title="taqdimot" allow="fullscreen" referrerpolicy="no-referrer"></iframe>
<script>
window.__msgs = [];
var f = document.getElementById('f');
addEventListener('message', function (e) { if (e.source === f.contentWindow && e.origin === location.origin) __msgs.push(e.data); });
window.post = function (m) { f.contentWindow.postMessage(m, location.origin); };
</script></body></html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".mp3": "audio/mpeg", ".webp": "image/webp",
                      ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8"}

    def log_message(self, *a):
        pass


def launch(p):
    for ch in ("chrome", "msedge", None):
        try:
            return p.chromium.launch(channel=ch) if ch else p.chromium.launch()
        except Exception:  # noqa: BLE001
            continue
    raise SystemExit("XATO: Chrome/Edge topilmadi")


def oxirgi(page):
    return page.evaluate("() => { const s = __msgs.filter(m => m && m.noon === 'slide'); return s.length ? s[s.length - 1] : null; }")


def kut_n(page, n, timeout=10000):
    page.wait_for_function("n => { const s = __msgs.filter(m => m && m.noon === 'slide'); return s.length && s[s.length - 1].n === n; }",
                           arg=n, timeout=timeout)


def och(page, k):
    """k-slayddagi hamma bosqichni ochish (ilovadagi «Keyingi» tugmasi kabi)."""
    for _ in range(40):
        m = oxirgi(page)
        if m and m.get("n") == k and m.get("step", 0) >= m.get("steps", 1) - 1:
            return True
        page.evaluate("() => post({noon: 'next'})")
        page.wait_for_timeout(430)
    return False


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chiqish", default=str(ST / "_sinov" / "ilova" / "iframe"))
    a = ap.parse_args()
    out = Path(a.chiqish)
    out.mkdir(parents=True, exist_ok=True)
    kurs = {d["n"]: d for d in json.loads(KURS.read_text(encoding="utf-8"))["darslar"]}

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(WEB)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    print(f"lokal sinov serveri: {base} (ildiz {WEB})", flush=True)

    nat, xato, rasmlar = {}, [], []
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            br = launch(p)
            for vnom, vp, mobil in KORINISH:
                ctx = br.new_context(viewport=vp, device_scale_factor=1, is_mobile=mobil, has_touch=mobil)
                ctx.add_init_script(INIT)
                page = ctx.new_page()
                page.route("**/__harness.html", lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8",
                                                                      body=HARNESS))
                page.goto(f"{base}/__harness.html", wait_until="load")
                for dars, k in HOLATLAR:
                    key = f"d{dars:02d}_{vnom}"
                    r = {"ok": False}
                    nat[key] = r
                    try:
                        t = kurs[dars]["taqdimot"]
                        total = t["to"] - t["from"] + 1
                        url = f"{t['url']}?from={t['from']}&to={t['to']}&start=1"
                        page.evaluate("u => { window.__msgs = []; document.getElementById('f').src = u; }", url)
                        page.wait_for_function("() => __msgs.some(m => m && m.noon === 'slide')", timeout=120000)
                        m0 = oxirgi(page)
                        r["boshlanish"] = m0
                        r["boshlanish_ok"] = m0["n"] == 1 and m0["total"] == total
                        page.evaluate("k => post({noon: 'goto', n: k})", k)
                        kut_n(page, k)
                        r["bosqich_ochildi"] = och(page, k)
                        fr = next(f for f in page.frames if "/content/taqdimot/" in f.url)
                        ws = fr.locator(".slide.active .nq-soz")
                        r["soz_soni"] = ws.count()
                        if not r["soz_soni"]:
                            raise RuntimeError("faol slaydda so'z ovozi yo'q")
                        sid = ws.first.get_attribute("data-soz")
                        fr.evaluate("() => { window.__plays = []; }")
                        n0 = page.evaluate("() => __msgs.length")
                        if mobil:
                            ws.first.tap()
                        else:
                            ws.first.click()
                        page.wait_for_timeout(450)
                        plays = fr.evaluate("() => window.__plays.slice()")
                        keyin = page.evaluate("n0 => __msgs.slice(n0)", n0)
                        r["bosish"] = {"plays": plays, "kutilgan": sid, "yangi_xabarlar": keyin}
                        r["bosish_ok"] = (len(plays) == 1 and f"{sid}.mp3" in plays[0]
                                          and all(x.get("n") == k for x in keyin if x.get("noon") == "slide")
                                          and not any(x.get("noon") == "end" for x in keyin))
                        r["mp3"] = fr.evaluate("id => fetch('ovoz/' + encodeURIComponent(id) + '.mp3').then(x => "
                                               "x.arrayBuffer().then(b => [x.status, x.headers.get('content-type'), b.byteLength]))", sid)
                        r["mp3_ok"] = r["mp3"][0] == 200 and "audio/mpeg" in (r["mp3"][1] or "") and r["mp3"][2] > 1000
                        # skrinshot: so'z «o'ynayotgan» ko'rinishda
                        fr.evaluate("() => { const w = document.querySelector('.slide.active .nq-soz'); if (w) w.classList.add('nq-ijro'); }")
                        page.wait_for_timeout(200)
                        f = out / f"{key}.png"
                        page.screenshot(path=str(f))
                        rasmlar.append(f)
                        fr.evaluate("() => document.querySelectorAll('.nq-ijro').forEach(w => w.classList.remove('nq-ijro'))")
                        # navigatsiya: keyingi slayd
                        page.evaluate("() => post({noon: 'next'})")
                        kut_n(page, k + 1)
                        r["keyingi_ok"] = True
                        if not mobil:
                            page.evaluate("t => post({noon: 'goto', n: t})", total)
                            kut_n(page, total)
                            och(page, total)
                            page.evaluate("() => post({noon: 'next'})")
                            page.wait_for_function("() => __msgs.some(m => m && m.noon === 'end')", timeout=8000)
                            r["end_ok"] = True
                        r["ok"] = all(r.get(x, True) for x in ("boshlanish_ok", "bosqich_ochildi", "bosish_ok", "mp3_ok",
                                                                 "keyingi_ok", "end_ok"))
                    except Exception as e:  # noqa: BLE001
                        r["xato"] = f"{type(e).__name__}: {str(e)[:300]}"
                    if not r["ok"]:
                        xato.append(key)
                    print(f"{key}: {'OK' if r['ok'] else 'XATO'} | so'z {r.get('soz_soni')} | bosish {r.get('bosish_ok')} "
                          f"| mp3 {r.get('mp3')} | keyingi {r.get('keyingi_ok')} | end {r.get('end_ok', '-')}"
                          + (f" | {r['xato']}" if r.get("xato") else ""), flush=True)
                ctx.close()
            br.close()
    finally:
        srv.shutdown()
    if rasmlar:
        from PIL import Image, ImageDraw
        th = []
        for f in rasmlar:
            im = Image.open(f).convert("RGB")
            im.thumbnail((560, 560))
            th.append((f.stem, im))
        cols = 4
        cw, ch = max(i.width for _, i in th), max(i.height for _, i in th) + 22
        rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (cw + 12) + 12, rows * (ch + 12) + 12), "#E4DCC8")
        dr = ImageDraw.Draw(sheet)
        for i, (nm, im) in enumerate(th):
            x, y = 12 + (i % cols) * (cw + 12), 12 + (i // cols) * (ch + 12)
            dr.text((x, y), nm, fill="#5A4423")
            sheet.paste(im, (x, y + 20))
        sheet.save(out / "kontakt.png")
    (out / "natija.json").write_text(json.dumps({"holatlar": nat, "xato": xato}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("hammasi OK" if not xato else f"XATO: {xato}", "->", out, flush=True)
    return 1 if xato else 0


if __name__ == "__main__":
    sys.exit(main())

# NUQTA demo: rasmlar, PDF va avtomatik tekshiruv (bitta brauzer, Playwright + Chrome).
#   python suratlar.py asosiy     -> "demo - kunduzgi.png" (Sahro), "demo - tungi.png" (Voha, duel natijasi)
#   python suratlar.py yonma      -> _tekshiruv\yonma\<manzara>_<rejim>.png (12 ta, kichraytirilgan)
#   python suratlar.py tel        -> _tekshiruv\390\... (390 px telefon, ekranma-ekran) + tekshiruv.json
#   python suratlar.py pdf        -> demo.pdf (1–6 kunduzgi Sahro, 7–12 tungi Voha)
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEMO = ROOT / "demo.html"
TEK = ROOT / "_tekshiruv"
SCRATCH = Path(r"C:\Users\N.M\AppData\Local\Temp\claude\c--Users-N-M\cddbee38-8a02-4529-8449-91945a48ae29\scratchpad")
V6 = ["sahro", "voha", "shahar", "qahva", "xattot", "shom"]
EKRAN = ["bosh", "darslar", "dars", "mashq", "duel", "profil"]

CHECK_JS = r"""
(scope) => {
  const root = scope ? document.querySelector(scope) : document.body;
  const lin = c => { c /= 255; return c <= .04045 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4); };
  const L = c => .2126 * lin(c.r) + .7152 * lin(c.g) + .0722 * lin(c.b);
  function parse(s) {
    if (!s) return null;
    let m = s.match(/^rgba?\(([^)]+)\)/);
    if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; }
    m = s.match(/^color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: \/ ([\d.e-]+))?\)/);
    if (m) return { r: +m[1] * 255, g: +m[2] * 255, b: +m[3] * 255, a: m[4] === undefined ? 1 : +m[4] };
    m = s.match(/^#([0-9a-f]{6})$/i);
    if (m) return { r: parseInt(m[1].slice(0, 2), 16), g: parseInt(m[1].slice(2, 4), 16), b: parseInt(m[1].slice(4, 6), 16), a: 1 };
    return null;
  }
  const hex = c => '#' + [c.r, c.g, c.b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
  function hsl(c) {
    const r = c.r / 255, g = c.g / 255, b = c.b / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
    let h = 0, s = 0;
    if (mx !== mn) { const d = mx - mn; s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn);
      h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h *= 60; }
    return { h, s, l };
  }
  function bad(c) {
    if (!c || c.a < .05) return null;
    if (c.r >= 245 && c.g >= 245 && c.b >= 245) return 'oq';
    if (L(c) < .02) return "qora/juda to'q";
    const { h, s, l } = hsl(c);
    if ((h >= 290 && h <= 350 && s > .2 && l > .4) || ((h > 350 || h < 15) && s > .35 && l > .7)) return 'pushti';
    return null;
  }
  const blend = (top, bot) => ({ r: top.r * top.a + bot.r * (1 - top.a), g: top.g * top.a + bot.g * (1 - top.a), b: top.b * top.a + bot.b * (1 - top.a), a: 1 });
  function effBg(el) {
    const layers = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const c = parse(getComputedStyle(e).backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; }
    }
    let acc = layers.length && layers[layers.length - 1].a >= 1 ? layers.pop() : { r: 232, g: 218, b: 186, a: 1 };
    while (layers.length) acc = blend(layers.pop(), acc);
    return acc;
  }
  const name = el => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : '');
  const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0; };
  const colors = {}, contrast = [], taps = [];
  const note = (k, c, el) => { const key = k + ' ' + hex(c); if (!colors[key]) colors[key] = name(el); };
  for (const el of root.querySelectorAll('*')) {
    if (!vis(el)) continue;
    const cs = getComputedStyle(el);
    const inSvg = el.closest('svg');
    if (inSvg) {
      for (const at of ['fill', 'stroke']) { const c = parse(el.getAttribute(at) || ''); const b = bad(c); if (b) note(b + ' (sahna ' + at + ')', c, el); }
      continue;
    }
    const bgc = parse(cs.backgroundColor); const b1 = bad(bgc); if (b1) note(b1 + ' (fon)', bgc, el);
    for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
      if (parseFloat(cs['border' + side + 'Width']) > 0) { const c = parse(cs['border' + side + 'Color']); const b = bad(c); if (b) note(b + ' (chegara)', c, el); }
    }
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (hasText) {
      const fg = parse(cs.color), b2 = bad(fg); if (b2) note(b2 + ' (matn)', fg, el);
      const bg = effBg(el), f = fg.a < 1 ? blend(fg, bg) : fg;
      const l1 = L(f), l2 = L(bg), cr = (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05);
      if (cr < 4.5) contrast.push({ el: name(el), text: el.textContent.trim().slice(0, 40), ratio: +cr.toFixed(2), fg: hex(f), bg: hex(bg), size: cs.fontSize });
    }
  }
  for (const el of root.querySelectorAll('.ph-in button, .ph-in a, .ph-in [role="switch"]')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 44 - .5 || r.height < 44 - .5) taps.push({ el: name(el), text: el.textContent.trim().slice(0, 30), w: Math.round(r.width), h: Math.round(r.height) });
  }
  const over = [];
  for (const sc of root.querySelectorAll('.scr')) {
    if (sc.scrollHeight > sc.clientHeight + 2 && vis(sc)) over.push({ el: name(sc.closest('.dm-ph')) + ' ' + (sc.closest('.dm-ph') || {}).dataset?.scr, ortiqcha_px: sc.scrollHeight - sc.clientHeight });
  }
  return { colors, contrast, taps, over, v: document.documentElement.dataset.v, m: document.documentElement.dataset.m };
}
"""


def url(**q):
    from urllib.parse import urlencode
    return DEMO.resolve().as_uri() + "?" + urlencode(q)


def launch(p):
    for ch in ("chrome", "msedge"):
        try:
            return p.chromium.launch(channel=ch)
        except Exception:  # noqa: BLE001
            continue
    return p.chromium.launch()


def open_page(br, w, h, dpr, **q):
    pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=dpr)
    pg.goto(url(**q), wait_until="load")
    pg.evaluate("document.fonts.ready.then(() => true)")
    pg.wait_for_timeout(350)
    return pg


def yonma(br, v, m, out, dpr=1.5, duel="savol"):
    pg = open_page(br, 2680, 1000, dpr, v=v, m=m, chiz=1, kor="hammasi", duel=duel)
    pg.screenshot(path=str(out), full_page=True)
    res = pg.evaluate(CHECK_JS, ".dm-stage")
    pg.close()
    return res


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "asosiy"
    TEK.mkdir(exist_ok=True)
    with sync_playwright() as p:
        br = launch(p)
        if cmd == "asosiy":
            r1 = yonma(br, "sahro", "kun", ROOT / "demo - kunduzgi.png")
            r2 = yonma(br, "voha", "tun", ROOT / "demo - tungi.png", duel="natija")
            (TEK / "tekshiruv_asosiy.json").write_text(json.dumps([r1, r2], ensure_ascii=False, indent=1), encoding="utf-8")
            print(json.dumps([r1, r2], ensure_ascii=False, indent=1)[:6000])
        elif cmd == "yonma":
            d = TEK / "yonma"; d.mkdir(exist_ok=True)
            from PIL import Image
            allr = []
            for v in V6:
                for m in ("kun", "tun"):
                    f = d / f"{v}_{m}.png"
                    r = yonma(br, v, m, f, dpr=1, duel="natija" if m == "tun" else "savol")
                    im = Image.open(f); im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS); im.save(f)
                    allr.append(r)
                    print(v, m, "rang:", len(r["colors"]), "kontrast<4.5:", len(r["contrast"]), "tap<44:", len(r["taps"]), "sig'madi:", r["over"])
            (TEK / "tekshiruv_yonma.json").write_text(json.dumps(allr, ensure_ascii=False, indent=1), encoding="utf-8")
        elif cmd == "tel":
            d = TEK / "390"; d.mkdir(exist_ok=True)
            combos = [("sahro", "kun"), ("sahro", "tun"), ("voha", "kun"), ("voha", "tun"), ("shom", "kun"), ("shahar", "tun")]
            allr = []
            for v, m in combos:
                for e in EKRAN + ["duel-natija"]:
                    scr, duel = ("duel", "natija") if e == "duel-natija" else (e, "savol")
                    pg = open_page(br, 390, 844, 2, v=v, m=m, kor="bitta", ekran=scr, duel=duel)
                    el = pg.query_selector(".dm-ph.on .ph-in")
                    el.screenshot(path=str(d / f"{v}_{m}_{e}.png"))
                    r = pg.evaluate(CHECK_JS, ".dm-ph.on")
                    r["ekran"] = e
                    allr.append(r)
                    pg.close()
                print(v, m, "tayyor")
            (TEK / "tekshiruv_390.json").write_text(json.dumps(allr, ensure_ascii=False, indent=1), encoding="utf-8")
            agg = {"rang": {}, "kontrast": [], "tap": [], "sigmadi": []}
            for r in allr:
                agg["rang"].update(r["colors"])
                agg["kontrast"] += [dict(x, ekran=r["ekran"], v=r["v"], m=r["m"]) for x in r["contrast"]]
                agg["tap"] += [dict(x, ekran=r["ekran"]) for x in r["taps"]]
                agg["sigmadi"] += [dict(x, ekran=r["ekran"], v=r["v"], m=r["m"]) for x in r["over"]]
            print(json.dumps(agg, ensure_ascii=False, indent=1)[:8000])
        elif cmd == "pdf":
            import fitz
            parts = []
            for v, m, duel in (("sahro", "kun", "savol"), ("voha", "tun", "natija")):
                pg = open_page(br, 390, 844, 1, v=v, m=m, pdf=1, kor="hammasi", duel=duel)
                pg.evaluate("NUQTA.render()")
                pg.wait_for_timeout(200)
                pg.emulate_media(media="print")
                f = SCRATCH / f"_qism_{v}_{m}.pdf"
                pg.pdf(path=str(f), prefer_css_page_size=True, print_background=True)
                pg.close()
                parts.append(f)
            out = fitz.open()
            for f in parts:
                with fitz.open(str(f)) as d:
                    out.insert_pdf(d)
            out.save(str(ROOT / "demo.pdf"))
            print("PDF sahifalar:", out.page_count)
            out.close()
        br.close()


if __name__ == "__main__":
    main()

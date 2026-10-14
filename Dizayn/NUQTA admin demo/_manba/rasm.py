# NUQTA admin demo — rasmga olish va tekshiruv (bitta brauzer).
#   python rasm.py tez  [ekran] [kun|tun] [pc|tel] [manzara]  -> _tekshiruv\tez_*.png (bitta ekran, to'liq sahifa)
#   python rasm.py hammasi                                     -> 3 ta yakuniy PNG + _tekshiruv (alohida ekranlar, sinovlar)
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
TEK = OUT / "_tekshiruv"
DEMO = (OUT / "demo.html").resolve().as_uri()
BG = (232, 218, 186)  # Sahro --bg (kontakt fon)


def launch(p):
    for ch in ("chrome", "msedge"):
        try:
            return p.chromium.launch(channel=ch)
        except Exception:  # noqa: BLE001
            continue
    return p.chromium.launch()


def prep(page, scr, mode="kun", dev="pc", v="sahro", toza=True):
    page.evaluate(f"""() => {{ DEMO.toza({str(toza).lower()}); DEMO.theme('{v}', '{mode}'); DEMO.setDev('{dev}'); DEMO.go('{scr}'); }}""")
    page.evaluate("document.fonts.ready.then(() => true)")
    page.wait_for_timeout(350)


def shot_pc(page, path):
    """Kompyuter: oyna balandligini sahifa balandligiga tenglab olamiz — yopishqoq yon panel butun bo'yi bo'ylab chiqadi."""
    h = page.evaluate("() => document.documentElement.scrollHeight")
    page.set_viewport_size({"width": 1440, "height": max(900, h)})
    page.wait_for_timeout(300)
    h2 = page.evaluate("() => document.documentElement.scrollHeight")
    if h2 != h:
        page.set_viewport_size({"width": 1440, "height": max(900, h2)})
        page.wait_for_timeout(200)
    page.screenshot(path=str(path), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.wait_for_timeout(150)


def shot_tel_frames(page, scr, mode, prefix, max_frames=5):
    """Telefon: ekran ichidagi aylantirish bo'yicha ketma-ket kadrlar (har biri 844 px)."""
    prep(page, scr, mode, "tel")
    h = page.evaluate("() => document.getElementById('screen').scrollHeight")
    view = 792
    paths, top, i = [], 0, 0
    while i < max_frames:
        page.evaluate(f"() => document.getElementById('screen').scrollTop = {top}")
        page.wait_for_timeout(120)
        p = TEK / f"{prefix}_{i + 1}.png"
        page.locator("#device").screenshot(path=str(p))
        paths.append(p)
        i += 1
        if top + view >= h:
            break
        top = min(top + view - 56, h - view)  # yopishqoq sarlavha ostida 56 px ustma-ust
    page.evaluate("() => document.getElementById('screen').scrollTop = 0")
    return paths, h


def label_font(size):
    for f in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fade_crop(im, h, fade=180):
    """Uzun sahifani h balandlikda qirqib, pastini fon rangiga yumshoq so'ndiradi (davomi bor degan ishora)."""
    im = im.crop((0, 0, im.width, h))
    grad = Image.new("L", (1, fade))
    for y in range(fade):
        grad.putpixel((0, y), int(255 * (y / fade) ** 1.6))
    mask = Image.new("L", im.size, 0)
    mask.paste(grad.resize((im.width, fade)), (0, h - fade))
    im.paste(Image.new("RGB", im.size, BG), (0, 0), mask)
    return im


def compose(tiles, cols, out, scale=1.0, gap=32, labels=None, max_h=None):
    ims = []
    for k, t in enumerate(tiles):
        im = Image.open(t).convert("RGB")
        mh = max_h[k] if isinstance(max_h, (list, tuple)) else max_h
        if mh and im.height > mh:
            im = fade_crop(im, mh)
        if scale != 1.0:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        ims.append(im)
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    lab_h = 40 if labels else 0
    cw = max(im.width for im in ims)
    W = gap + cols * (cw + gap)
    rh = [max(im.height for im in r) + lab_h for r in rows]
    H = gap + sum(h + gap for h in rh)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f = label_font(22)
    y = gap
    k = 0
    for r, hh in zip(rows, rh):
        x = gap
        for im in r:
            if labels:
                d.text((x, y), labels[k], fill=(90, 68, 35), font=f)
            sheet.paste(im, (x, y + lab_h))
            x += cw + gap
            k += 1
        y += hh + gap
    sheet.save(out, optimize=True)
    return sheet.size


CHECK_JS = r"""
() => {
  const lum = c => { const m = c.match(/[\d.]+/g); if (!m) return null; const [r,g,b,a] = m.map(Number);
    const f = v => { v /= 255; return v <= .03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); };
    return { L: .2126*f(r) + .7152*f(g) + .0722*f(b), a: a === undefined ? 1 : a, rgb:[r,g,b] }; };
  const ratio = (a, b) => { const x = Math.max(a, b), y = Math.min(a, b); return (x + .05) / (y + .05); };
  function bgOf(el) {
    let e = el;
    while (e && e.nodeType === 1) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none' && !cs.backgroundImage.startsWith('url')) return { grad: true };
      const c = lum(cs.backgroundColor);
      if (c && c.a > .9) return c;
      e = e.parentElement;
    }
    return lum(getComputedStyle(document.body).backgroundColor);
  }
  const vis = el => { const r = el.getBoundingClientRect(); if (!r.width || !r.height) return false;
    let e = el; while (e) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false; e = e.parentElement; } return true; };
  const low = [], seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n; let total = 0;
  while ((n = walker.nextNode())) {
    const t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    if (el.closest('template,script,style,.sr,caption,[hidden],.dbar,.tg-head,.tel-cap,[data-scene]')) continue;
    if (!vis(el)) continue;
    const cs = getComputedStyle(el);
    let fg = lum(cs.color); let bg;
    if (el.closest('svg')) { fg = lum(cs.fill); bg = bgOf(el.closest('svg').parentElement); }
    else bg = bgOf(el);
    if (!fg || !bg || bg.grad) continue;
    let op = 1, e = el; while (e) { op *= +getComputedStyle(e).opacity; e = e.parentElement; }
    total++;
    const r = ratio(fg.L, bg.L);
    const size = parseFloat(cs.fontSize), bold = +cs.fontWeight >= 700;
    const need = (size >= 24 || (bold && size >= 18.66)) ? 3 : 4.5;
    if (r < need && op > .6) low.push({ t: t.slice(0, 40), r: +r.toFixed(2), need, size, fg: cs.color, bg: 'rgb(' + bg.rgb.join(',') + ')' });
  }
  const hs = [...document.querySelectorAll('h1,h2,h3,h4')].filter(vis).map(h => h.tagName);
  const ovX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
  const scr = document.getElementById('screen');
  const ovScreen = scr.scrollWidth > scr.clientWidth + 1;
  const wide = [...document.querySelectorAll('#screen *')].filter(e => { const r = e.getBoundingClientRect(), s = scr.getBoundingClientRect(); return vis(e) && r.width > 0 && r.right > s.right + 1; }).slice(0, 8).map(e => e.tagName + '.' + e.className);
  return { total, low: low.slice(0, 40), lowN: low.length, hs, ovX, ovScreen, wide };
}
"""

TARGET_JS = r"""
(min) => {
  const vis = el => { const r = el.getBoundingClientRect(); if (!r.width || !r.height) return false;
    let e = el; while (e) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; e = e.parentElement; } return true; };
  const els = [...document.querySelectorAll('#device button, #device a, #device input, #device select, #device [role=switch], #device [tabindex]:not([tabindex="-1"])')].filter(vis);
  const bad = els.map(e => { const r = e.getBoundingClientRect(); return { e: (e.getAttribute('aria-label') || e.textContent || e.tagName).trim().slice(0, 30), w: Math.round(r.width), h: Math.round(r.height) }; })
    .filter(x => x.w < min || x.h < min);
  return { n: els.length, bad };
}
"""


def tez(args):
    scr = args[0] if args else "bosh"
    mode = args[1] if len(args) > 1 else "kun"
    dev = args[2] if len(args) > 2 else "pc"
    v = args[3] if len(args) > 3 else "sahro"
    TEK.mkdir(exist_ok=True)
    with sync_playwright() as p:
        br = launch(p)
        page = br.new_page(viewport={"width": 1440, "height": 900})
        page.goto(DEMO)
        if dev == "tel":
            paths, h = shot_tel_frames(page, scr, mode, f"tez_{scr}_{mode}_tel_{v}", 8)
            print("kadrlar:", len(paths), "balandlik:", h)
        else:
            prep(page, scr, mode, dev, v)
            path = TEK / f"tez_{scr}_{mode}_{dev}_{v}.png"
            shot_pc(page, path)
            print(path)
        res = page.evaluate(CHECK_JS)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        br.close()


def hammasi():
    TEK.mkdir(exist_ok=True)
    rep = {}
    with sync_playwright() as p:
        br = launch(p)
        page = br.new_page(viewport={"width": 1440, "height": 900})
        page.goto(DEMO)
        # 1) kompyuter, kunduzgi — 4 ekran
        pcs = []
        for scr in ("bosh", "safar", "tugmalar", "funksiyalar"):
            prep(page, scr, "kun", "pc")
            pth = TEK / f"pc_kun_{scr}.png"
            shot_pc(page, pth)
            pcs.append(pth)
            rep[f"pc_kun_{scr}"] = page.evaluate(CHECK_JS)
        hb = Image.open(pcs[0]).height
        compose(pcs, 2, OUT / "demo - kompyuter.png", scale=0.75,
                labels=["1. Bosh sahifa — yangi «Ko'rinish» kartasi", "2. O'quvchining ilovadagi safari (boshlanishi)",
                        "3. Tugmalar va ekranlar", "4. Funksiyalar"], max_h=[None, hb, None, None])
        # 2) tungi — Bosh + Safar
        tuns = []
        for scr in ("bosh", "safar"):
            prep(page, scr, "tun", "pc")
            pth = TEK / f"pc_tun_{scr}.png"
            shot_pc(page, pth)
            tuns.append(pth)
            rep[f"pc_tun_{scr}"] = page.evaluate(CHECK_JS)
        hb = Image.open(tuns[0]).height
        compose(tuns, 2, OUT / "demo - tungi.png", scale=0.75,
                labels=["Bosh sahifa — tungi («oy nuri»)", "Ilovadagi safar — tungi (boshlanishi)"], max_h=[None, hb])
        # 3) telefon 390 — Bosh + Safar, ketma-ket kadrlar
        tel_tiles, tel_labels = [], []
        for scr, nom in (("bosh", "Bosh sahifa"), ("safar", "Safar")):
            paths, h = shot_tel_frames(page, scr, "kun", f"tel_kun_{scr}", 4)
            rep[f"tel_kun_{scr}"] = page.evaluate(CHECK_JS)
            rep[f"tel_kun_{scr}_44px"] = page.evaluate(TARGET_JS, 44)
            tel_tiles += paths
            tel_labels += [f"{nom} · {i + 1}" for i in range(len(paths))]
            while len(tel_tiles) % 4:
                tel_tiles.append(paths[-1]); tel_labels.append("")
        # bo'sh to'ldiruvchilarni olib tashlab, qatorlarni 4 tadan teramiz
        compose_rows(tel_tiles, tel_labels, OUT / "demo - telefon.png")
        # 4) qo'shimcha sinovlar
        for scr in ("tugmalar", "funksiyalar"):
            prep(page, scr, "tun", "pc")
            rep[f"pc_tun_{scr}"] = page.evaluate(CHECK_JS)
            paths, h = shot_tel_frames(page, scr, "tun", f"tel_tun_{scr}", 2)
            rep[f"tel_tun_{scr}"] = page.evaluate(CHECK_JS)
            rep[f"tel_tun_{scr}_44px"] = page.evaluate(TARGET_JS, 44)
        for scr in ("bosh", "safar"):
            paths, h = shot_tel_frames(page, scr, "tun", f"tel_tun_{scr}", 2)
            rep[f"tel_tun_{scr}"] = page.evaluate(CHECK_JS)
        prep(page, "bosh", "kun", "pc")
        rep["pc_24px"] = page.evaluate(TARGET_JS, 24)
        # fokus halqasi (klaviatura) — kunduzgi va tungi
        for mode in ("kun", "tun"):
            for scr, sel, card in (("bosh", '[data-k="bm"][data-val="xp"]', "section[aria-labelledby=h-faol]"),
                                   ("funksiyalar", '#fGroups .sw', "#fGroups .card")):
                prep(page, scr, mode, "pc")
                page.keyboard.press("Tab")
                page.focus(sel)
                page.wait_for_timeout(150)
                page.locator(card).first.screenshot(path=str(TEK / f"fokus_{scr}_{mode}.png"))
        # holatlar rangsiz ham ajraladimi (grayscale)
        prep(page, "funksiyalar", "kun", "pc")
        page.add_style_tag(content="html{filter:grayscale(1)}")
        page.wait_for_timeout(150)
        page.locator("#fGroups").screenshot(path=str(TEK / "grayscale_funksiyalar.png"))
        # boshqa manzaralar: Bosh sahifaning birinchi ekrani, kun va tun
        page.goto(DEMO)
        mz = []
        for v in ("sahro", "voha", "shahar", "qahva", "xattot", "shom"):
            for mode in ("kun", "tun"):
                prep(page, "bosh", mode, "pc", v)
                pth = TEK / f"mz_{v}_{mode}.png"
                page.screenshot(path=str(pth))
                rep[f"pc_{mode}_bosh_{v}"] = page.evaluate(CHECK_JS)
                mz.append(pth)
        compose(mz, 4, TEK / "manzaralar_kontakt.png", scale=0.4, gap=16,
                labels=[f"{v} · {m}" for v in ("Sahro", "Voha", "Shahar", "Qahva", "Xattot", "Shom") for m in ("kun", "tun")])
        br.close()
    (TEK / "tekshiruv.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, r in rep.items():
        if "lowN" in r:
            print(f"{k}: matn {r['total']}, past kontrast {r['lowN']}, sarlavhalar {''.join(h[1] for h in r['hs'])}, toshish {r['ovX'] or r['ovScreen']}")
        else:
            print(f"{k}: elementlar {r['n']}, kichik {len(r['bad'])} {r['bad'][:6]}")


def compose_rows(tiles, labels, out):
    real = [(t, l) for t, l in zip(tiles, labels) if l]
    rows, cur, last = [], [], None
    for t, l in real:
        key = l.split(" · ")[0]
        if last is not None and key != last:
            rows.append(cur); cur = []
        cur.append((t, l)); last = key
    rows.append(cur)
    ims = [[(Image.open(t).convert("RGB"), l) for t, l in r] for r in rows]
    gap, lab = 28, 40
    cw = max(im.width for r in ims for im, _ in r)
    chh = max(im.height for r in ims for im, _ in r)
    cols = max(len(r) for r in ims)
    W = gap + cols * (cw + gap)
    H = gap + len(ims) * (chh + lab + gap)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet); f = label_font(22)
    y = gap
    for r in ims:
        x = gap
        for im, l in r:
            d.text((x + 8, y), l, fill=(90, 68, 35), font=f)
            sheet.paste(im, (x, y + lab))
            x += cw + gap
        y += chh + lab + gap
    sheet.save(out, optimize=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tez":
        tez(sys.argv[2:])
    else:
        hammasi()

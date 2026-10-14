"""Kitob skanerlari (A4 betlar) uchun tozalash: "Scanned with CamScanner" belgisi va chetdagi barmoq.

tools/kontent.py har bir A4 (kitob) sahifani render qilgach shu funksiyani chaqiradi - faqat ilova nusxasi
(web/content/dars/NN/*.webp) tozalanadi, manba PDF larga tegilmaydi.

    from skaner_tozala import tozala
    img, info = tozala(pil_rgb_image)      # info: {"belgi": (x0,y0,x1,y1) | None, "barmoq": [...]}

Sinov (oldin/keyin kontakt varaqlari):  python tools/skaner_tozala.py <chiqish papkasi>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

VERSIYA = "skaner-v1"


# ---------------------------------------------------------------- CamScanner belgisi
def belgi_topish(g: np.ndarray) -> tuple[int, int, int, int] | None:
    """g - kulrang (H, W) uint8. Belgi pastki o'ng burchakda, oq hoshiyada: qidiruv oynasi x >= 0.78W, y >= 0.955H.
    Qaytaradi (x0, y0, x1, y1) - belgining to'liq to'rtburchagi (biroz kengaytirilgan) yoki None."""
    H, W = g.shape
    x0w, y0w = int(W * 0.78), int(H * 0.955)
    win = g[y0w:, x0w:]
    tuq = win < 120                    # "CS" logotipi va "CamScanner" yozuvi (to'q)
    if tuq.sum() < (W / 1000) ** 2 * 150:
        return None
    ys, xs = np.nonzero(win < 215)      # ramka chiziqlari va "Scanned with" (och kulrang) ham
    # faqat to'q qism atrofidagi piksellar (ramka bilan birga) - tasodifiy dog'larni chiqarib tashlash
    ty, tx = np.nonzero(tuq)
    cx0, cx1, cy0, cy1 = tx.min(), tx.max(), ty.min(), ty.max()
    pad = int(W * 0.04)
    m = (xs >= cx0 - pad) & (xs <= cx1 + pad) & (ys >= cy0 - pad) & (ys <= cy1 + pad)
    if not m.any():
        return None
    bx0, bx1, by0, by1 = xs[m].min(), xs[m].max(), ys[m].min(), ys[m].max()
    bw, bh = (bx1 - bx0) / W, (by1 - by0) / H
    if not (0.09 <= bw <= 0.19 and 0.022 <= bh <= 0.05):   # belgining odatiy o'lchami: ~0.135W x ~0.037H
        return None
    e = max(2, int(W * 0.006))
    return (int(x0w + bx0 - e), int(y0w + by0 - e), int(min(W, x0w + bx1 + e + 1)), int(min(H, y0w + by1 + e + 1)))


# ---------------------------------------------------------------- chap chetdagi barmoq
def barmoq_niqobi(rgb: np.ndarray) -> np.ndarray | None:
    """Chap chetdagi (x < 0.13W) teri rangidagi katta dog' -> niqob (H, W) uint8 yoki None.
    Matndagi qizil harflar (to'yinganligi juda yuqori) va kichik dog'lar hisobga olinmaydi."""
    import cv2
    H, W = rgb.shape[:2]
    xw = int(W * 0.13)
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb[:, :xw]), cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    teri = ((h <= 24) | (h >= 170)) & (s >= 40) & (s <= 215) & (v >= 60)
    teri = teri.astype(np.uint8)
    teri = cv2.morphologyEx(teri, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(teri, 8)
    niqob = np.zeros((H, W), np.uint8)
    topildi = False
    min_maydon = (W / 1000) ** 2 * 1500
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if a < min_maydon or x > W * 0.09 or w < W * 0.025 or hh < W * 0.03:
            continue
        niqob[:, :xw][lab == i] = 255
        topildi = True
    if not topildi:
        return None
    # barmoq soyasi va chegarasi ham tozalansin
    k = max(3, int(W * 0.02)) | 1
    return cv2.dilate(niqob, np.ones((k, k), np.uint8))


def _ustun_toldir(rgb: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Niqobdagi piksellarni har ustunda yuqoridagi va pastdagi eng yaqin toza piksel orasida chiziqli to'ldiradi:
    qog'oz chekkasi (tik chiziq) va fon saqlanadi, niqobdan tashqaridagi matn o'zgarmaydi."""
    out = rgb.astype(np.float32)
    H = rgb.shape[0]
    for x in np.nonzero(m.any(axis=0))[0]:
        ys = np.nonzero(m[:, x])[0]
        for seg in np.split(ys, np.nonzero(np.diff(ys) > 1)[0] + 1):
            a, b = int(seg[0]) - 1, int(seg[-1]) + 1
            ta = out[a, x].copy() if a >= 0 else out[min(H - 1, b), x].copy()
            tb = out[b, x].copy() if b < H else ta
            t = ((seg - a) / max(1, b - a))[:, None]
            out[seg, x] = ta * (1 - t) + tb * t
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- asosiy
def _qogoz_rangi(rgb: np.ndarray, x0, y0, x1, y1) -> np.ndarray:
    """Faqat to'rtburchak TASHQARISIDAGI halqa (belgining och kulrang ichi hisobga olinmaydi)."""
    H, W = rgb.shape[:2]
    m = max(4, int(W * 0.01))
    ya, yb, xa, xb = max(0, y0 - m), min(H, y1 + m), max(0, x0 - m), min(W, x1 + m)
    blok = rgb[ya:yb, xa:xb]
    tash = np.ones(blok.shape[:2], bool)
    tash[y0 - ya:y1 - ya, x0 - xa:x1 - xa] = False
    a = blok[tash]
    return np.median(a, axis=0) if len(a) else np.array([255, 255, 255])


def tozala(img, barmoq: bool = True):
    """PIL RGB rasm -> (tozalangan PIL rasm, info). O'zgarish bo'lmasa o'sha rasm qaytadi."""
    import cv2
    from PIL import Image
    rgb = np.asarray(img.convert("RGB")).copy()
    H, W = rgb.shape[:2]
    info = {"belgi": None, "barmoq": None}
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    b = belgi_topish(g)
    if b:
        x0, y0, x1, y1 = b
        atrof = _qogoz_rangi(rgb, x0, y0, x1, y1)
        # oq hoshiya: atrofdagi qog'oz/fon rangi bilan to'ldiriladi, chegara inpaint bilan silliqlanadi
        rgb[y0:y1, x0:x1] = atrof.astype(np.uint8)
        niq = np.zeros((H, W), np.uint8)
        e = max(2, int(W * 0.003))
        niq[max(0, y0 - e):y1 + e, max(0, x0 - e):x1 + e] = 255
        niq[y0 + e:y1 - e, x0 + e:x1 - e] = 0
        rgb = cv2.inpaint(rgb, niq, 3, cv2.INPAINT_TELEA)
        info["belgi"] = b
    if barmoq:
        nq = barmoq_niqobi(rgb)
        if nq is not None:
            ys, xs = np.nonzero(nq)
            rgb = _ustun_toldir(rgb, nq > 0)
            info["barmoq"] = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    if not info["belgi"] and not info["barmoq"]:
        return img, info
    return Image.fromarray(rgb), info


# ---------------------------------------------------------------- sinov: oldin/keyin
def _sinov(out: Path) -> int:
    """Mavjud web/content A4 betlarida belgini topadi va oldin/keyin kesimlarini kontakt varaqqa yig'adi.
    (Fayllarni o'zgartirmaydi.)"""
    import json
    from PIL import Image, ImageDraw
    root = Path(__file__).resolve().parent.parent
    k = json.loads((root / "web" / "content" / "kurs.json").read_text(encoding="utf-8"))
    sahifalar = []
    for d in k["darslar"]:
        for u in d.get("kitob_betlari") or []:
            sahifalar.append(root / "web" / u.lstrip("/"))
        if d.get("nisbat") == "a4":
            sahifalar += [root / "web" / d["rasm"].lstrip("/") / f"{i:03d}.webp" for i in range(1, d["slaydlar"] + 1)]
    out.mkdir(parents=True, exist_ok=True)
    qator = []
    for p in sahifalar:
        im = Image.open(p).convert("RGB")
        t, info = tozala(im)
        qator.append((p, im, t, info))
        print(p.parent.name + "/" + p.name, info)
    cw, ch = 330, 190
    sheet = Image.new("RGB", (cw * 2 * 3 + 20, (len(qator) + 2) // 3 * (ch + 18)), "white")
    dr = ImageDraw.Draw(sheet)
    for i, (p, a, b, info) in enumerate(qator):
        W, H = a.size
        box = (W - cw, H - ch, W, H)
        x, y = (i % 3) * (cw * 2 + 7), (i // 3) * (ch + 18)
        sheet.paste(a.crop(box), (x, y + 16))
        sheet.paste(b.crop(box), (x + cw, y + 16))
        dr.text((x + 2, y + 2), f"{p.parent.name}/{p.name} belgi={'ha' if info['belgi'] else 'YOQ'}", fill="red")
    sheet.save(out / "belgi_oldin_keyin.png")
    return 0


if __name__ == "__main__":
    sys.exit(_sinov(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("_sinov/skaner")))

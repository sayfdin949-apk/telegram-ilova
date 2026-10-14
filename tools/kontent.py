#!/usr/bin/env python
"""Fonetika kursi kontentini Mini App uchun tayyorlaydi (docs/SPEC.md, 2-bo'lim).

    python tools/kontent.py                      # hammasi; o'zgarmagan narsa qayta qilinmaydi
    python tools/kontent.py --majbur             # hammasini qaytadan yasash
    python tools/kontent.py --faqat slayd,kurs   # faqat tanlangan bosqichlar
        bosqichlar: shrift, slayd, test, video, kurs, tekshir
    python tools/kontent.py --ishchi 10          # slayd render jarayonlari soni

Natija:
    web/content/kurs.json, web/content/dars/NN/NNN.webp + thumb.webp, web/content/test/NN.json,
    web/content/video/<id>.webp, server/videolar.json, web/shared/fonts.css (+ Nunito woff2).
Manbalar (PDF, Dars jadvali, test HTML, video) faqat o'qiladi; matnlar so'zma-so'z olinadi.
Holat fayli (qayta ishlamaslik uchun): tools/_kontent_holat.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import struct
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
CONTENT = WEB / "content"
DARS_OUT = CONTENT / "dars"
TEST_OUT = CONTENT / "test"
VIDEO_OUT = CONTENT / "video"
KURS_JSON = CONTENT / "kurs.json"
SHARED = WEB / "shared"
FONTS = SHARED / "fonts"
FONTS_CSS = SHARED / "fonts.css"
VIDEOLAR_JSON = ROOT / "server" / "videolar.json"
HOLAT = ROOT / "tools" / "_kontent_holat.json"

DESKTOP = Path(os.environ.get("USERPROFILE") or str(Path.home())) / "Desktop"
KURS_DIR = DESKTOP / "taqdimot" / "Fonetika kursi (36 dars)"
PDF_DIR = KURS_DIR / "PDF"
JADVAL = KURS_DIR / "Dars jadvali.html"
NAMUNA_DIR = DESKTOP / "taqdimot" / "O'quvchi materiallari (36 dars)" / "_namuna"
VIDEO_DIR = DESKTOP / "videolar"
SIQILGAN_DIR = VIDEO_DIR / "siqilgan"
# siqilgan dars yozuvlarining nomlari (fayl nomida sarlavha yo'q) - egasi tasdiqlagan
SIQILGAN_NOMLAR = {
    "2-dars_ipad.mp4": "Darsning to'liq yozuvi",
    "3-dars_ipad.mp4": "Harflar: Roo, Zaa, Taa, Nuun, Yaa, Kaaf (to'liq yozuv)",
}
SIQILGAN_NOM_STANDART = "Darsning to'liq yozuvi"

TZ = timezone(timedelta(hours=5))  # Asia/Tashkent
KURS_NOMI = "Fonetika kursi"
BREND = "Muhammadamin"
KUTILGAN_DARS, KUTILGAN_SLAYD = 36, 543  # 543 = jonli taqdimot slaydlari (PDF rasmlari 573 ta)

W169, WA4, WTHUMB = 1280, 1000, 480     # 16:9 -> 1280x720; A4 (portret) -> 1000 px eni; thumb -> 480 px eni
SS = 2                                  # 2x render + LANCZOS kichraytirish (silliqroq arabcha harakatlar)
WEBP_Q, WEBP_M = 80, 6
IMZO = f"v1;ss{SS}-lanczos;q{WEBP_Q}m{WEBP_M};{W169}/{WA4}/{WTHUMB}"
POSTER_W, POSTER_H, POSTER_ULUSH = 1280, 720, 0.08

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")
NUNITO_CSS = "https://fonts.googleapis.com/css2?family=Nunito:wght@700..900&display=swap"
LATIN = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, "
         "U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD")
LATIN_EXT = ("U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, "
             "U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, "
             "U+A720-A7FF")
ARABIC = "U+0600-06FF, U+0750-077F, U+0870-08FF, U+200C-200E, U+FB50-FDFF, U+FE70-FEFC"

OGOH: list[str] = []   # ogohlantirishlar (manbadagi kuzatuvlar)
XATO: list[str] = []   # xatolar -> chiqish kodi 1


def log(*a) -> None:
    print(*a, flush=True)


def ogoh(s: str) -> None:
    OGOH.append(s)
    log("  ogohlantirish: " + s)


def xato(s: str) -> None:
    XATO.append(s)
    log("  XATO: " + s)


# ---------------------------------------------------------------- fayl yozish (atomik, faqat o'zgarsa)

def _almashtir(tmp: Path, path: Path) -> None:
    for i in range(25):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # server faylni o'qiyotgan bo'lishi mumkin (Windows)
            time.sleep(0.08 * (i + 1))
    os.replace(tmp, path)


def yoz(path: Path, data: bytes) -> bool:
    """Fayl o'zgargan bo'lsagina yozadi (mtime/ETag saqlanadi). True = yozildi."""
    try:
        if path.is_file() and path.stat().st_size == len(data) and path.read_bytes() == data:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_bytes(data)
    _almashtir(tmp, path)
    return True


def json_bayt(obj, ichki_qator: str | None = None) -> bytes:
    """Ixcham, o'qilishi oson JSON: ichki_qator kalitidagi ro'yxat elementlari bittadan qatorda."""
    if ichki_qator is None:
        return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    qatorlar = ["{"]
    kalitlar = list(obj)
    for i, k in enumerate(kalitlar):
        v = obj[k]
        vergul = "," if i < len(kalitlar) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            ichi = ",\n".join("  " + json.dumps(x, ensure_ascii=False) for x in v)
            qatorlar.append(f" {json.dumps(k)}: [\n{ichi}\n ]{vergul}")
        else:
            qatorlar.append(f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}{vergul}")
    qatorlar.append("}")
    return ("\n".join(qatorlar) + "\n").encode("utf-8")


def holat_oqish() -> dict:
    try:
        return json.loads(HOLAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def holat_yoz(h: dict) -> None:
    yoz(HOLAT, json_bayt(h))


def fayl_imzo(p: Path) -> list:
    st = p.stat()
    return [p.name, st.st_size, st.st_mtime_ns]


# ---------------------------------------------------------------- kichik HTML DOM (std-lib)

class El:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict, parent: "El | None"):
        self.tag, self.attrs, self.children, self.parent = tag, attrs, [], parent

    def cls(self, c: str) -> bool:
        return c in (self.attrs.get("class") or "").split()


class _DomParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
            "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = El("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        el = El(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(el)
        if tag not in self.VOID:
            self.cur = el

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(El(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        el = self.cur
        while el is not self.root and el.tag != tag:
            el = el.parent
        if el is not self.root:
            self.cur = el.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def dom(path: Path) -> El:
    p = _DomParser()
    p.feed(path.read_text(encoding="utf-8"))
    p.close()
    return p.root


def elementlar(el: El):
    for c in el.children:
        if isinstance(c, El):
            yield c
            yield from elementlar(c)


def topish(el: El, tag: str, cls: str | None = None) -> list[El]:
    return [e for e in elementlar(el) if e.tag == tag and (cls is None or e.cls(cls))]


def bosh_joy(s: str) -> str:
    """HTML ko'rinishidagidek: faqat ASCII bo'shliqlarni bittaga qisqartiradi (NBSP va boshqalarga tegmaydi)."""
    return re.sub(r"[ \t\n\r\f]+", " ", s).strip()


def matn(el: El, tashla=None, br: str = " ") -> str:
    qism = []

    def yur(e: El):
        for c in e.children:
            if isinstance(c, str):
                qism.append(c)
            elif c.tag == "br":
                qism.append(br)
            elif c.tag in ("style", "script"):
                continue
            elif tashla is None or not tashla(c):
                yur(c)
    yur(el)
    return bosh_joy("".join(qism)) if br == " " else "".join(qism)


# ---------------------------------------------------------------- 1. shriftlar

def shriftlar(majbur: bool) -> None:
    t0 = time.time()
    FONTS.mkdir(parents=True, exist_ok=True)
    nunito = {"latin": FONTS / "nunito-latin.woff2", "latin-ext": FONTS / "nunito-latin-ext.woff2"}
    if majbur or not all(p.is_file() and p.stat().st_size > 10000 for p in nunito.values()):
        req = urllib.request.Request(NUNITO_CSS, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            css = r.read().decode("utf-8")
        for sub, path in nunito.items():
            m = re.search(r"/\* " + re.escape(sub) + r" \*/\s*@font-face\s*\{(.*?)\}", css, flags=re.S)
            if not m:
                raise RuntimeError(f"Google Fonts javobida Nunito {sub} topilmadi")
            blok = m.group(1)
            url = re.search(r"src:\s*url\((https://[^)]+\.woff2)\)", blok).group(1)
            rng = re.search(r"unicode-range:\s*([^;]+);", blok).group(1).strip()
            if rng != (LATIN if sub == "latin" else LATIN_EXT):
                ogoh(f"Nunito {sub} unicode-range Google'da boshqacha: {rng}")
            if "font-weight: 700 900" not in blok:
                ogoh(f"Nunito {sub}: o'zgaruvchan (700 900) shrift emas")
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                data = r.read()
            if data[:4] != b"wOF2":
                raise RuntimeError(f"Nunito {sub}: woff2 emas")
            yoz(path, data)
            log(f"  Nunito {sub}: {len(data) // 1024} KB yuklandi")

    def ff(oila, fayl, vazn, rng, uslub="normal"):
        if not (FONTS / fayl).is_file():
            xato(f"shrift fayli yo'q: web/shared/fonts/{fayl}")
        return (f"@font-face{{font-family:'{oila}';font-style:{uslub};font-weight:{vazn};font-display:swap;"
                f"src:url(fonts/{fayl}) format('woff2');unicode-range:{rng};}}")

    q = ["/* Noon - shriftlar. tools/kontent.py yasaydi, qo'lda tahrirlamang.",
         "   Nunito 700-900: 'O'yinli' (game) uslubi. Be Vietnam Pro: 'Shisha' (glass) uslubi va xodimlar ilovasi.",
         "   Arabcha: font-family:\"Sakkal Majalla\",\"Noto Naskh Arabic\",serif (Noto Naskh shu yerdan). */",
         ff("Nunito", "nunito-latin-ext.woff2", "700 900", LATIN_EXT),
         ff("Nunito", "nunito-latin.woff2", "700 900", LATIN)]
    for w in (400, 500, 600, 700, 800):
        q.append(ff("Be Vietnam Pro", f"be-vietnam-pro-latin-ext-{w}-normal.woff2", w, LATIN_EXT))
        q.append(ff("Be Vietnam Pro", f"be-vietnam-pro-latin-{w}-normal.woff2", w, LATIN))
    q.append(ff("Be Vietnam Pro", "be-vietnam-pro-latin-400-italic.woff2", 400, LATIN, "italic"))
    for w in (400, 700):
        q.append(ff("Noto Naskh Arabic", f"noto-naskh-arabic-arabic-{w}-normal.woff2", w, ARABIC))
    o = yoz(FONTS_CSS, ("\n".join(q) + "\n").encode("utf-8"))
    holat = "yangilandi" if o else "o'zgarishsiz"
    log(f"shrift: fonts.css {holat} ({len(q) - 3} @font-face), {time.time() - t0:.1f} s")


# ---------------------------------------------------------------- 2. manbalar: jadval + PDF

RIM = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


def jadval_oqish() -> tuple[list[dict], dict[int, dict]]:
    root = dom(JADVAL)
    qismlar: dict[int, dict] = {}
    darslar: dict[int, dict] = {}
    joriy = None
    for el in elementlar(root):
        if el.tag == "h2":
            sarlavha = matn(el, tashla=lambda e: e.cls("cnt"))
            m = re.match(r"^([IVX]+)\.\s+(.+)$", sarlavha)
            if not m or m.group(1) not in RIM:
                continue
            n = RIM[m.group(1)]
            if n not in qismlar:
                qismlar[n] = {"n": n, "nomi": m.group(2), "darslar": []}
            joriy = n
        elif el.tag == "tr":
            tds = [c for c in el.children if isinstance(c, El) and c.tag == "td"]
            if len(tds) != 4 or not tds[0].cls("n"):
                continue
            if joriy is None:
                raise RuntimeError("Dars jadvali: qism sarlavhasidan oldin dars qatori")
            n = int(matn(tds[0]))
            if n in darslar:
                raise RuntimeError(f"Dars jadvali: {n}-dars ikki marta")
            ustun4 = matn(tds[3], br="\n")
            darslar[n] = {
                "qism": joriy,
                "mavzu": matn(tds[1]),
                "kitob": matn(tds[2]),
                "taqdimot": [bosh_joy(matn(b)) for b in topish(tds[3], "b")],
                "oraliqlar": [(int(a), int(b)) for a, b in re.findall(r"slaydlar\s+(\d+)\s*[–-]\s*(\d+)", ustun4)],
                "ustun4": bosh_joy(ustun4.replace("\n", " ")),
            }
            qismlar[joriy]["darslar"].append(n)
    return [qismlar[k] for k in sorted(qismlar)], darslar


def sahifa_turi(w: float, h: float) -> str:
    if abs(w / h - 16 / 9) < 0.02:
        return "16:9"
    if abs(h / w - 842 / 595) < 0.03:
        return "a4"
    return "boshqa"


def olcham(tur: str, w: float, h: float) -> tuple[int, int]:
    if tur == "16:9":
        return W169, round(W169 * 9 / 16)
    eni = WA4 if h > w else W169
    return eni, round(eni * h / w)


def pdflar_oqish() -> dict[int, dict]:
    import pymupdf
    res: dict[int, dict] = {}
    for p in sorted(PDF_DIR.glob("*.pdf")):
        m = re.match(r"^(\d{2})-dars \((.+)\)\.pdf$", p.name)
        if not m:
            ogoh(f"PDF nomi andozaga mos emas, o'tkazildi: {p.name}")
            continue
        n = int(m.group(1))
        if n in res:
            raise RuntimeError(f"{n}-dars uchun ikkita PDF: {res[n]['fayl'].name}, {p.name}")
        with pymupdf.open(p) as doc:
            turlar, olchamlar = [], []
            for pg in doc:
                r = pg.rect
                t = sahifa_turi(r.width, r.height)
                turlar.append(t)
                olchamlar.append(olcham(t, r.width, r.height))
                if t == "boshqa":
                    ogoh(f"{n}-dars {pg.number + 1}-bet: kutilmagan o'lcham {r.width:.0f}x{r.height:.0f} pt")
        res[n] = {"fayl": p, "nomi": m.group(2), "turlar": turlar, "olchamlar": olchamlar}
    return res


def manbalar() -> tuple[list[dict], dict[int, dict]]:
    """Qismlar + har dars uchun birlashtirilgan ma'lumot (jadval + PDF)."""
    qismlar, jadval = jadval_oqish()
    pdf = pdflar_oqish()
    if set(jadval) != set(pdf):
        raise RuntimeError(f"Jadval va PDF darslari mos emas: faqat jadvalda {sorted(set(jadval) - set(pdf))}, "
                           f"faqat PDF da {sorted(set(pdf) - set(jadval))}")
    darslar = {}
    for n in sorted(jadval):
        d = {**jadval[n], **pdf[n], "n": n}
        # kuzatuv: jadvaldagi slayd oraliqlari va kitob betlari PDF bilan solishtiriladi (hech narsa o'zgartirilmaydi)
        n169 = d["turlar"].count("16:9")
        na4 = d["turlar"].count("a4")
        jad_sl = sum(b - a + 1 for a, b in d["oraliqlar"])
        mk = re.match(r"^(\d+)\s*[–-]\s*(\d+)$", d["kitob"])
        kitob_bet = int(mk.group(2)) - int(mk.group(1)) + 1 if mk else 0
        d["kuzatuv"] = {"16:9": n169, "a4": na4, "jadval_slayd": jad_sl, "kitob_bet": kitob_bet}
        darslar[n] = d
    return qismlar, darslar


def nisbat_va_a4(d: dict) -> tuple[str, list[int]]:
    turlar = d["turlar"]
    if all(t == "a4" for t in turlar):
        return "a4", []
    a4 = [i + 1 for i, t in enumerate(turlar) if t == "a4"]
    return ("a4" if turlar[0] == "a4" else "16:9"), a4


# ---------------------------------------------------------------- 3. slaydlar (multiprocessing)

_DOCS: dict = {}


def _webp_bayt(img) -> bytes:
    bio = io.BytesIO()
    img.save(bio, "WEBP", quality=WEBP_Q, method=WEBP_M)
    return bio.getvalue()


def _render_ish(ish: tuple) -> tuple:
    """Ishchi jarayon: bitta sahifa -> NNN.webp (+ thumb.webp)."""
    pdf, idx, chiqish, w, h, thumb, skaner = ish
    import pymupdf
    from PIL import Image
    t0 = time.perf_counter()
    doc = _DOCS.get(pdf)
    if doc is None:
        doc = _DOCS[pdf] = pymupdf.open(pdf)
    pg = doc[idx]
    z = SS * w / pg.rect.width
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
    katta = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    del pix
    if skaner:  # kitob skaneri (A4): "Scanned with CamScanner" belgisi va chetdagi barmoq olib tashlanadi
        from skaner_tozala import tozala
        katta, _ = tozala(katta)
    data = _webp_bayt(katta.resize((w, h), Image.LANCZOS))
    yoz(Path(chiqish), data)
    th = 0
    if thumb:
        tw, thh = WTHUMB, round(WTHUMB * h / w)
        tdata = _webp_bayt(katta.resize((tw, thh), Image.LANCZOS))
        yoz(Path(thumb), tdata)
        th = len(tdata)
    return chiqish, len(data), th, time.perf_counter() - t0


def dars_papka(n: int) -> Path:
    return DARS_OUT / f"{n:02d}"


def slayd_yozuv(d: dict) -> dict:
    """Holat yozuvi: PDF imzosi + render sozlamalari; A4 (kitob skaneri) betlari bor darsga tozalash versiyasi ham."""
    y = {"pdf": fayl_imzo(d["fayl"]), "imzo": IMZO, "sahifalar": len(d["turlar"])}
    if "a4" in d["turlar"]:
        from skaner_tozala import VERSIYA
        y["skaner"] = VERSIYA
    return y


def slaydlar(darslar: dict[int, dict], holat: dict, majbur: bool, ishchi: int) -> bool:
    t0 = time.time()
    hs = holat.setdefault("slaydlar", {})
    ishlar, qayta = [], []
    for n, d in darslar.items():
        papka = dars_papka(n)
        kalit = f"{n:02d}"
        kerak = [papka / f"{i:03d}.webp" for i in range(1, len(d["turlar"]) + 1)] + [papka / "thumb.webp"]
        yozuv = slayd_yozuv(d)
        if not majbur and hs.get(kalit) == yozuv and all(p.is_file() for p in kerak):
            continue
        qayta.append(n)
        hs.pop(kalit, None)
        for i, (w, h) in enumerate(d["olchamlar"]):
            ishlar.append((str(d["fayl"]), i, str(papka / f"{i + 1:03d}.webp"), w, h,
                           str(papka / "thumb.webp") if i == 0 else None, d["turlar"][i] == "a4"))
        # ortiqcha eski fayllar o'chirilmaydi, faqat aytiladi
        if papka.is_dir():
            ortiqcha = sorted(p.name for p in papka.glob("*.webp")
                              if p.name != "thumb.webp" and p not in kerak)
            if ortiqcha:
                ogoh(f"{n}-dars papkasida ortiqcha fayllar bor (o'chirilmadi): {', '.join(ortiqcha[:5])}")
    if not ishlar:
        log(f"slayd: hammasi tayyor ({len(darslar)} dars), {time.time() - t0:.1f} s")
        return False
    log(f"slayd: {len(qayta)} dars, {len(ishlar)} sahifa render qilinadi ({ishchi} jarayon)...")
    # og'irlarini (A4 va rasmli) oldinroq beramiz - yuk tekis taqsimlanadi
    ishlar.sort(key=lambda x: (-(x[4] * x[3]), x[0], x[1]))
    bajarildi, jami_bayt, cpu, xatolar = 0, 0, 0.0, {}
    with ProcessPoolExecutor(max_workers=ishchi) as ex:
        fut = {ex.submit(_render_ish, i): i for i in ishlar}
        for f in as_completed(fut):
            i = fut[f]
            try:
                _, b, tb, s = f.result()
                jami_bayt += b + tb
                cpu += s
            except Exception as e:  # bitta sahifa xatosi butun darsni "tayyor emas" qiladi
                xatolar.setdefault(i[0], []).append(f"{i[1] + 1}-bet: {type(e).__name__}: {e}")
            bajarildi += 1
            if bajarildi % 100 == 0 or bajarildi == len(ishlar):
                log(f"  {bajarildi}/{len(ishlar)} sahifa, {jami_bayt / 1048576:.1f} MB, {time.time() - t0:.0f} s")
    for n in qayta:
        d = darslar[n]
        if str(d["fayl"]) in xatolar:
            for x in xatolar[str(d["fayl"])]:
                xato(f"{n}-dars render: {x}")
            continue
        hs[f"{n:02d}"] = slayd_yozuv(d)
    log(f"slayd: tayyor - {len(ishlar)} sahifa, {jami_bayt / 1048576:.1f} MB, devor vaqti {time.time() - t0:.1f} s, "
        f"CPU {cpu:.0f} s")
    return True


# ---------------------------------------------------------------- 4. testlar

def _xom_matn(s: str) -> str:
    """Mustaqil tekshiruv: teglarni regex bilan olib tashlab, HTML ko'rinishidagi matn."""
    return bosh_joy(unescape(re.sub(r"<[^>]+>", "", s)))


def test_oqish(papka: Path) -> dict:
    t = dom(papka / "2-test.html")
    k = dom(papka / "3-kalit.html")
    nomi = matn(topish(t, "title")[0])
    savollar = []
    for q in topish(t, "div", "q"):
        qn = int(matn(topish(q, "div", "qn")[0]))
        qt = matn(topish(q, "div", "qt")[0])
        opts = []
        for o in topish(q, "div", "opt"):
            belgi = topish(o, "span", "m")
            harf = matn(belgi[0]) if belgi else ""
            opts.append((harf, matn(o, tashla=lambda e: e.tag == "span" and e.cls("m"))))
        if [h for h, _ in opts] != list("ABCD"[:len(opts)]) or len(opts) < 2:
            raise RuntimeError(f"{qn}-savol variant harflari kutilmagan: {[h for h, _ in opts]}")
        savollar.append({"n": qn, "q": qt, "opts": [x for _, x in opts]})
    kalit = {}
    for r in topish(k, "div", "key-row"):
        bolalar = [c for c in r.children if isinstance(c, El) and c.tag == "div"]
        if len(bolalar) != 3:
            raise RuntimeError("kalit qatori tuzilishi kutilmagan")
        kalit[int(matn(bolalar[0]))] = (matn(bolalar[1]), matn(bolalar[2]))
    if [s["n"] for s in savollar] != list(range(1, len(savollar) + 1)) or sorted(kalit) != [s["n"] for s in savollar]:
        raise RuntimeError(f"savol ({[s['n'] for s in savollar]}) va kalit ({sorted(kalit)}) raqamlari mos emas")
    natija = []
    for s in savollar:
        harf, izoh = kalit[s["n"]]
        if harf not in "ABCD"[:len(s["opts"])] or len(harf) != 1:
            raise RuntimeError(f"{s['n']}-savol kalit harfi noto'g'ri: {harf!r}")
        natija.append({"q": s["q"], "opts": s["opts"], "ok": "ABCD".index(harf), "izoh": izoh})

    # --- mustaqil qayta tekshiruv: manba fayllarni qayta o'qib, regex bilan solishtirish
    xt = (papka / "2-test.html").read_text(encoding="utf-8")
    xk = (papka / "3-kalit.html").read_text(encoding="utf-8")
    rq = [_xom_matn(x) for x in re.findall(r'<div class="qt">(.*?)</div>', xt, flags=re.S)]
    ro = [_xom_matn(x) for x in re.findall(r'<div class="opt"><span class="m">[A-D]</span>(.*?)</div>', xt, flags=re.S)]
    rk = re.findall(r'<div class="key-row"><div class="n">(\d+)</div><div class="a">([A-D])</div><div>(.*?)</div></div>',
                    xk, flags=re.S)
    if rq != [s["q"] for s in natija]:
        raise RuntimeError("qayta tekshiruv: savol matnlari manba bilan mos emas")
    if ro != [o for s in natija for o in s["opts"]]:
        raise RuntimeError("qayta tekshiruv: variant matnlari manba bilan mos emas")
    if [(int(a), "ABCD".index(b), _xom_matn(c)) for a, b, c in rk] != \
            [(i + 1, s["ok"], s["izoh"]) for i, s in enumerate(natija)]:
        raise RuntimeError("qayta tekshiruv: kalit/izohlar manba bilan mos emas")
    tom = _xom_matn(xt) + "\n" + _xom_matn(xk)
    for s in natija:
        for x in [s["q"], s["izoh"], *s["opts"]]:
            if x not in tom:
                raise RuntimeError(f"qayta tekshiruv: matn manbada topilmadi: {x[:30]!r}")
    if _xom_matn(re.search(r"<title>(.*?)</title>", xt, flags=re.S).group(1)) != nomi:
        raise RuntimeError("qayta tekshiruv: test nomi mos emas")
    return {"nomi": nomi, "savollar": natija}


def testlar_topish() -> dict[int, Path]:
    res = {}
    if NAMUNA_DIR.is_dir():
        for p in sorted(NAMUNA_DIR.iterdir()):
            m = re.match(r"^(\d{2})-dars$", p.name)
            if m and p.is_dir() and (p / "2-test.html").is_file() and (p / "3-kalit.html").is_file():
                res[int(m.group(1))] = p
    return res


def testlar(darslar: dict[int, dict]) -> tuple[dict[int, str], bool]:
    t0 = time.time()
    yollar, ozgardi = {}, False
    for n, papka in testlar_topish().items():
        if n not in darslar:
            ogoh(f"{n}-dars testi bor, lekin bunday dars yo'q - o'tkazildi")
            continue
        try:
            t = test_oqish(papka)
        except Exception as e:
            xato(f"{n}-dars testi o'qilmadi ({papka.name}): {e}")
            continue
        obj = {"dars": n, "nomi": t["nomi"], "savollar": t["savollar"]}
        if yoz(TEST_OUT / f"{n:02d}.json", json_bayt(obj, ichki_qator="savollar")):
            ozgardi = True
        yollar[n] = f"/content/test/{n:02d}.json"
        log(f"test: {n:02d}.json - {len(t['savollar'])} savol, javoblar {[s['ok'] for s in t['savollar']]}, "
            f"manba bilan qayta tekshirildi")
    for n, y in qolda_testlar(darslar).items():  # manbasiz, qo'lda qo'yilgan test/NN.json ham ulanadi
        if n not in yollar:
            yollar[n] = y
            log(f"test: {n:02d}.json - qo'lda qo'yilgan fayl ulandi")
    log(f"test: {len(yollar)} ta, {time.time() - t0:.1f} s")
    return yollar, ozgardi


def qolda_testlar(darslar: dict[int, dict]) -> dict[int, str]:
    """web/content/test/NN.json fayllari (to'g'ri sxemada bo'lsa) - _namuna manbasi bo'lmasa ham."""
    res = {}
    for f in sorted(TEST_OUT.glob("[0-9][0-9].json")) if TEST_OUT.is_dir() else []:
        n = int(f.stem)
        try:
            t = json.loads(f.read_bytes().decode("utf-8"))
            ok = t.get("dars") == n and t.get("savollar") and all(
                isinstance(s.get("opts"), list) and 0 <= s.get("ok", -1) < len(s["opts"]) for s in t["savollar"])
        except Exception:
            ok = False
        if n in darslar and ok:
            res[n] = f"/content/test/{n:02d}.json"
        elif n in darslar:
            ogoh(f"test/{f.name}: sxemaga mos emas - ulanmadi")
    return res


def test_yollari(darslar: dict[int, dict]) -> dict[int, str]:
    res = {n: f"/content/test/{n:02d}.json" for n in testlar_topish()
            if n in darslar and (TEST_OUT / f"{n:02d}.json").is_file()}
    for n, y in qolda_testlar(darslar).items():
        res.setdefault(n, y)
    return res


# ---------------------------------------------------------------- 5. video

def _atomlar(f, bosh: int, oxir: int):
    pos = bosh
    while pos + 8 <= oxir:
        f.seek(pos)
        size, typ = struct.unpack(">I4s", f.read(8))
        hl = 8
        if size == 1:
            size = struct.unpack(">Q", f.read(8))[0]
            hl = 16
        elif size == 0:
            size = oxir - pos
        if size < hl:
            break
        yield typ.decode("latin-1"), pos, size, hl
        pos += size


def mp4_malumot(path: Path) -> tuple[float, bool]:
    """(davomiylik soniya - mvhd atomidan, faststart: moov mdat dan oldinmi)."""
    with open(path, "rb") as f:
        oxir = os.fstat(f.fileno()).st_size
        top = list(_atomlar(f, 0, oxir))
        moov = next((a for a in top if a[0] == "moov"), None)
        mdat = next((a for a in top if a[0] == "mdat"), None)
        if moov is None:
            raise RuntimeError("moov atomi topilmadi")
        for typ, pos, size, hl in _atomlar(f, moov[1] + moov[3], moov[1] + moov[2]):
            if typ == "mvhd":
                f.seek(pos + hl)
                ver = f.read(4)[0]
                if ver == 1:
                    f.read(16)
                    ts, dur = struct.unpack(">IQ", f.read(12))
                else:
                    f.read(8)
                    ts, dur = struct.unpack(">II", f.read(8))
                return dur / ts, (mdat is None or moov[1] < mdat[1])
    raise RuntimeError("mvhd atomi topilmadi")


def videolar_topish() -> list[dict]:
    """1) Desktop/videolar ichidagi 'Fonetika N-dars - Nomi (motion).mp4' fayllari (yuqori daraja);
    2) Desktop/videolar/siqilgan ichidagi 'N-dars_*.mp4' (dars yozuvlari, iPad) - nomi SIQILGAN_NOMLAR dan.
    id: d{NN}, band bo'lsa oxiriga 'b' qo'shiladi (d02, d02b, d03 ...). Bir darsda bir nechta video bo'lishi mumkin."""
    res, band = [], set()

    def qosh(n: int, nomi: str, p: Path, siqilgan: bool) -> None:
        vid = f"d{n:02d}"
        while vid in band:
            vid += "b"
        band.add(vid)
        res.append({"id": vid, "dars": n, "nomi": nomi, "fayl": p, "siqilgan": siqilgan})

    if VIDEO_DIR.is_dir():
        for p in sorted(VIDEO_DIR.iterdir()):
            m = re.match(r"^Fonetika (\d+)-dars - (.+?)( \(motion\))?\.mp4$", p.name, flags=re.I)
            if m and p.is_file():
                qosh(int(m.group(1)), m.group(2), p, False)
    if SIQILGAN_DIR.is_dir():
        topilgan = []
        for p in SIQILGAN_DIR.iterdir():
            m = re.match(r"^(\d+)-dars_.+\.mp4$", p.name, flags=re.I)
            if m and p.is_file():
                topilgan.append((int(m.group(1)), p.name.lower(), p))
        for n, _, p in sorted(topilgan):
            qosh(n, SIQILGAN_NOMLAR.get(p.name, SIQILGAN_NOM_STANDART), p, True)
    return res


def video_tayyormi(v: dict) -> bool:
    """Siqilgan video hali yozilayotgan bo'lsa (ffmpeg ishlayapti: .log tugamagan yoki moov yo'q) - o'tkaziladi."""
    if not v.get("siqilgan"):
        return True
    p: Path = v["fayl"]
    lg = p.with_name(p.name + ".log")
    if lg.is_file():
        try:
            dum = lg.read_bytes()[-4000:].decode("utf-8", "replace")
        except OSError:
            dum = ""
        if not re.search(r"(muxing overhead|video:\s*\d+\s*[kKM]i?B\s+audio:)", dum):
            ogoh(f"video {p.name}: ffmpeg hali tugamagan (log yakunlanmagan) - o'tkazildi")
            return False
    try:
        mp4_malumot(p)
    except Exception as e:
        ogoh(f"video {p.name}: hali tayyor emas ({e}) - o'tkazildi")
        return False
    return True


def _poster(path: Path, davom: float, chiqish: Path) -> tuple[float, bool]:
    import cv2
    import numpy as np
    from PIL import Image
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("OpenCV videoni ocholmadi")
    tanlov = None
    try:
        for ulush in (POSTER_ULUSH, 0.10, 0.06, 0.12, 0.15, 0.20, 0.30):
            cap.set(cv2.CAP_PROP_POS_MSEC, davom * ulush * 1000)
            ok, kadr = cap.read()
            if not ok or kadr is None:
                continue
            ort, std = float(kadr.mean()), float(kadr.std())
            if tanlov is None:
                tanlov = (ulush, kadr)
            if 18 < ort < 240 and std > 10:  # qora/bir tusli o'tish kadri emas
                tanlov = (ulush, kadr)
                break
    finally:
        cap.release()
    if tanlov is None:
        raise RuntimeError("kadr o'qilmadi")
    ulush, kadr = tanlov
    h, w = kadr.shape[:2]
    k = max(POSTER_W / w, POSTER_H / h)  # "cover" + markazdan kesish (16:9 bo'lsa kesilmaydi)
    nw, nh = max(POSTER_W, round(w * k)), max(POSTER_H, round(h * k))
    kadr = cv2.resize(kadr, (nw, nh), interpolation=cv2.INTER_AREA)
    x, y = (nw - POSTER_W) // 2, (nh - POSTER_H) // 2
    kadr = np.ascontiguousarray(kadr[y:y + POSTER_H, x:x + POSTER_W, ::-1])
    yozildi = yoz(chiqish, _webp_bayt(Image.fromarray(kadr)))
    return ulush, yozildi


def videolar(holat: dict, majbur: bool) -> tuple[dict[int, dict], bool]:
    t0 = time.time()
    hv = holat.setdefault("videolar", {})
    kurs_v, server_v, ozgardi = {}, [], False
    for v in videolar_topish():
        if not video_tayyormi(v):
            continue
        try:
            davom, fast = mp4_malumot(v["fayl"])
        except Exception as e:
            xato(f"video {v['fayl'].name}: davomiylik o'qilmadi: {e}")
            continue
        poster = VIDEO_OUT / f"{v['id']}.webp"
        imzo = {"fayl": fayl_imzo(v["fayl"]), "w": POSTER_W, "h": POSTER_H, "ulush": POSTER_ULUSH}
        if majbur or hv.get(v["id"], {}).get("imzo") != imzo or not poster.is_file():
            try:
                ulush, yozildi = _poster(v["fayl"], davom, poster)
            except Exception as e:
                xato(f"video {v['id']}: poster yasalmadi: {e}")
                continue
            hv[v["id"]] = {"imzo": imzo, "kadr_ulush": ulush}
            ozgardi |= yozildi
            if ulush != POSTER_ULUSH:
                ogoh(f"video {v['id']}: {POSTER_ULUSH:.0%} dagi kadr qorong'i/bir tusli, {ulush:.0%} dagi olindi")
        if not fast:
            ogoh(f"video {v['id']}: MP4 'faststart' emas (moov oxirida) - brauzer avval fayl oxirini so'raydi")
        server_v.append({"id": v["id"], "dars": v["dars"], "nomi": v["nomi"], "fayl": str(v["fayl"])})
        kurs_v.setdefault(v["dars"], []).append(video_obj(v, davom))
        fs = "ha" if fast else "yo'q"
        log(f"video: {v['id']} ({v['dars']}-dars) {davom:.1f} s, faststart={fs}, "
            f"{v['fayl'].stat().st_size / 1048576:.0f} MB")
    if yoz(VIDEOLAR_JSON, (json.dumps(server_v, ensure_ascii=False, indent=2) + "\n").encode("utf-8")):
        log("video: server/videolar.json yozildi")
    log(f"video: {len(server_v)} ta, {time.time() - t0:.1f} s")
    return kurs_v, ozgardi


def video_obj(v: dict, davom: float) -> dict:
    return {"id": v["id"], "nomi": v["nomi"], "davomiylik": int(round(davom)),
            "poster": f"/content/video/{v['id']}.webp", "url": f"/media/video/{v['id']}"}


def video_kurs_malumot() -> dict[int, list[dict]]:
    """--faqat kurs uchun: posterni yasamasdan, kurs.json dagi video obyektlari (dars -> ro'yxat).
    Faqat posteri tayyor videolar (aks holda avval 'video' bosqichini ishga tushiring)."""
    res: dict[int, list[dict]] = {}
    for v in videolar_topish():
        if not video_tayyormi(v):
            continue
        if not (VIDEO_OUT / f"{v['id']}.webp").is_file():
            ogoh(f"video {v['id']}: posteri yo'q - kurs.json ga qo'shilmadi (--faqat video,kurs)")
            continue
        try:
            davom, _ = mp4_malumot(v["fayl"])
        except Exception as e:
            xato(f"video {v['fayl'].name}: {e}")
            continue
        res.setdefault(v["dars"], []).append(video_obj(v, davom))
    return res


# ---------------------------------------------------------------- 6. kurs.json

def kurs(qismlar: list[dict], darslar: dict[int, dict], video: dict[int, list[dict]], test: dict[int, str],
         boshqa_ozgarish: bool) -> bool:
    jami = sum(len(d["turlar"]) for d in darslar.values())
    dl = []
    for n, d in darslar.items():
        nisbat, a4 = nisbat_va_a4(d)
        obj = {"n": n, "qism": d["qism"], "nomi": d["nomi"], "mavzu": d["mavzu"], "kitob": d["kitob"],
               "slaydlar": len(d["turlar"]), "nisbat": nisbat}
        if a4:  # aralash dars (taqdimot + kitob betlari): A4 portret slaydlar raqamlari (1 dan)
            obj["a4_slaydlar"] = a4
        obj.update({"rasm": f"/content/dars/{n:02d}/", "thumb": f"/content/dars/{n:02d}/thumb.webp",
                    # "videolar" - darsning barcha videolari; "video" - birinchisi (eski o'quvchilar uchun moslik)
                    "pdf": d["fayl"].name, "video": (video.get(n) or [None])[0], "videolar": video.get(n) or [],
                    "test": test.get(n)})
        dl.append(obj)
    k = {"nomi": KURS_NOMI, "brend": BREND, "versiya": None, "jami_dars": len(dl), "jami_slayd": jami,
         "qismlar": qismlar, "darslar": dl}
    # Jonli HTML taqdimotlar (tools/taqdimot.py): taqdimot/kitob_betlari maydonlari, slaydlar = taqdimot oralig'i
    import taqdimot
    taqdimot.kursga_qoshish(k)
    jami = k["jami_slayd"]
    eski = None
    try:
        eski = json.loads(KURS_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if eski and not boshqa_ozgarish and {**eski, "versiya": None} == k and eski.get("versiya"):
        k["versiya"] = eski["versiya"]
    else:
        k["versiya"] = datetime.now(TZ).date().isoformat()
    yozildi = yoz(KURS_JSON, json_bayt(k, ichki_qator="darslar"))
    holat = "yozildi" if yozildi else "o'zgarishsiz"
    log(f"kurs: kurs.json {holat} - {len(dl)} dars, {jami} slayd, "
        f"versiya {k['versiya']}, {KURS_JSON.stat().st_size // 1024} KB")
    return yozildi


# ---------------------------------------------------------------- 7. tekshiruv

def _papka_hajmi(p: Path, naqsh: str = "*") -> tuple[int, int]:
    fayllar = [f for f in p.rglob(naqsh) if f.is_file()] if p.is_dir() else []
    return len(fayllar), sum(f.stat().st_size for f in fayllar)


def tekshir(darslar: dict[int, dict] | None) -> None:
    from PIL import Image
    t0 = time.time()
    xato_oldin = len(XATO)
    try:
        k = json.loads(KURS_JSON.read_bytes().decode("utf-8"))
    except Exception as e:
        xato(f"kurs.json o'qilmadi (UTF-8 JSON emas?): {e}")
        return
    dl = k.get("darslar", [])
    if [d["n"] for d in dl] != list(range(1, len(dl) + 1)) or k.get("jami_dars") != len(dl) or not dl:
        xato("kurs.json: darslar 1..N ketma-ket emas yoki jami_dars noto'g'ri")
        return
    if len(dl) != KUTILGAN_DARS:
        ogoh(f"darslar soni {len(dl)}, SPEC bo'yicha {KUTILGAN_DARS}")
    qd = sorted(n for q in k.get("qismlar", []) for n in q["darslar"])
    if qd != list(range(1, len(dl) + 1)) or [q["n"] for q in k["qismlar"]] != list(range(1, len(k["qismlar"]) + 1)):
        xato("kurs.json: qismlar darslarni aniq bir martadan qamramaydi")
    for q in k.get("qismlar", []):
        for n in q["darslar"]:
            if 1 <= n <= len(dl) and dl[n - 1]["qism"] != q["n"]:
                xato(f"{n}-dars qism raqami mos emas")
    jami = sum(d["slaydlar"] for d in dl)
    if jami != k.get("jami_slayd"):
        xato(f"jami_slayd {k.get('jami_slayd')} != {jami}")
    if jami != KUTILGAN_SLAYD:
        ogoh(f"jami slayd {jami}, SPEC bo'yicha {KUTILGAN_SLAYD}")
    kalitlar = ["n", "qism", "nomi", "mavzu", "kitob", "slaydlar", "nisbat", "rasm", "thumb", "pdf", "video", "videolar",
                "test"]
    qoshimcha = {"a4_slaydlar", "taqdimot", "kitob_betlari"}
    fayllar_soni, olcham_xato, rasm_jami = 0, 0, 0
    for d in dl:
        n = d["n"]
        if [x for x in d if x not in qoshimcha] != kalitlar:
            xato(f"{n}-dars kalitlari sxemaga mos emas: {list(d)}")
        if d["nisbat"] not in ("16:9", "a4"):
            xato(f"{n}-dars nisbat noto'g'ri: {d['nisbat']}")
        if not (PDF_DIR / d["pdf"]).is_file():
            xato(f"{n}-dars PDF yo'q: {d['pdf']}")
        papka = CONTENT / d["rasm"].removeprefix("/content/")
        nomlar = sorted(p.name for p in papka.glob("[0-9][0-9][0-9].webp")) if papka.is_dir() else []
        if d.get("taqdimot"):
            # taqdimotli dars: slaydlar soni HTML taqdimotdan; PDF rasmlari (eskiz va kitob betlari) PDF sahifalari soni bo'yicha
            t = d["taqdimot"]
            if not (CONTENT / t["url"].removeprefix("/content/")).is_file():
                xato(f"{n}-dars taqdimot fayli yo'q: {t['url']}")
            if d["slaydlar"] != t["to"] - t["from"] + 1:
                xato(f"{n}-dars slaydlar {d['slaydlar']} != taqdimot oralig'i {t['from']}-{t['to']}")
            kut = [f"{i:03d}.webp" for i in range(1, len(nomlar) + 1)]
            for u in d.get("kitob_betlari") or []:
                if not (CONTENT / u.removeprefix("/content/")).is_file():
                    xato(f"{n}-dars kitob beti yo'q: {u}")
        else:
            kut = [f"{i:03d}.webp" for i in range(1, d["slaydlar"] + 1)]
        if nomlar != kut:
            xato(f"{n}-dars slayd fayllari mos emas: {len(nomlar)} ta, kutilgan {len(kut)}")
        fayllar_soni += len(nomlar)
        rasm_jami += len(kut)
        a4kb = {int(u.rsplit("/", 1)[-1][:3]) for u in d.get("kitob_betlari") or []}
        if not (CONTENT / d["thumb"].removeprefix("/content/")).is_file():
            xato(f"{n}-dars thumb yo'q")
        a4 = set(d.get("a4_slaydlar") or []) | a4kb
        for i, nom in enumerate(kut, 1):
            f = papka / nom
            if not f.is_file():
                continue
            with Image.open(f) as im:
                if im.format != "WEBP":
                    xato(f"{n}-dars {nom}: WEBP emas")
                kutilgan = darslar[n]["olchamlar"][i - 1] if darslar else None
                if kutilgan is None:
                    kutilgan = (WA4, None) if (d["nisbat"] == "a4" or i in a4) else (W169, 720)
                if im.size[0] != kutilgan[0] or (kutilgan[1] and im.size[1] != kutilgan[1]):
                    olcham_xato += 1
                    if olcham_xato <= 5:
                        xato(f"{n}-dars {nom}: o'lcham {im.size}, kutilgan {kutilgan}")
        thumb = CONTENT / d["thumb"].removeprefix("/content/")
        if thumb.is_file():
            with Image.open(thumb) as im:
                if im.size[0] != WTHUMB:
                    xato(f"{n}-dars thumb eni {im.size[0]}")
        vl = d.get("videolar") or []
        if d["video"] != (vl[0] if vl else None):
            xato(f"{n}-dars: 'video' videolar ro'yxatining birinchisi emas")
        for v in vl:
            if list(v) != ["id", "nomi", "davomiylik", "poster", "url"]:
                xato(f"{n}-dars video kalitlari: {list(v)}")
            pf = CONTENT / v["poster"].removeprefix("/content/")
            if not pf.is_file():
                xato(f"{n}-dars video poster yo'q ({v['id']})")
            else:
                with Image.open(pf) as im:
                    if im.size != (POSTER_W, POSTER_H):
                        xato(f"poster o'lchami {im.size}")
        if d["test"]:
            try:
                t = json.loads((CONTENT / d["test"].removeprefix("/content/")).read_bytes().decode("utf-8"))
                if t["dars"] != n or not t["savollar"]:
                    xato(f"{n}-dars test fayli noto'g'ri")
                for s in t["savollar"]:
                    if list(s) != ["q", "opts", "ok", "izoh"] or not (0 <= s["ok"] < len(s["opts"])):
                        xato(f"{n}-dars test savoli sxemaga mos emas")
            except Exception as e:
                xato(f"{n}-dars test fayli o'qilmadi: {e}")
    if fayllar_soni != rasm_jami:
        xato(f"slayd fayllari soni {fayllar_soni}, kutilgan {rasm_jami}")
    # server/videolar.json <-> kurs.json
    try:
        sv = json.loads(VIDEOLAR_JSON.read_bytes().decode("utf-8"))
        kv = {v["id"] for d in dl for v in (d.get("videolar") or [])}
        if len(kv) != sum(len(d.get("videolar") or []) for d in dl):
            xato("kurs.json: video id lari takrorlangan")
        for v in sv:
            if list(v) != ["id", "dars", "nomi", "fayl"]:
                xato(f"videolar.json kalitlari: {list(v)}")
            if not Path(v["fayl"]).is_file():
                xato(f"videolar.json: fayl yo'q: {v['fayl']}")
        if not kv <= {v["id"] for v in sv}:
            xato("kurs.json dagi video id videolar.json da yo'q")
    except Exception as e:
        xato(f"server/videolar.json o'qilmadi: {e}")
    # fonts.css havolalari
    if FONTS_CSS.is_file():
        for u in re.findall(r"url\(([^)]+)\)", FONTS_CSS.read_text(encoding="utf-8")):
            if not (SHARED / u).is_file():
                xato(f"fonts.css: fayl yo'q {u}")
    else:
        xato("web/shared/fonts.css yo'q")
    if not (SHARED / "icons.svg").is_file():
        ogoh("web/shared/icons.svg yo'q - python tools/ikonlar.py")

    sn, sb = _papka_hajmi(DARS_OUT, "[0-9][0-9][0-9].webp")
    tn, tb = _papka_hajmi(DARS_OUT, "thumb.webp")
    _, testb = _papka_hajmi(TEST_OUT)
    _, vb = _papka_hajmi(VIDEO_OUT)
    fn, fb = _papka_hajmi(FONTS)
    a4n = sum(len(d.get("a4_slaydlar") or []) + len(d.get("kitob_betlari") or []) + (d["slaydlar"] if d["nisbat"] == "a4" else 0) for d in dl)
    yangi_xato = len(XATO) - xato_oldin
    natija = "xato yo'q" if yangi_xato == 0 else f"{yangi_xato} xato"
    log(f"tekshir: {len(dl)} dars, {fayllar_soni} slayd fayli (16:9: {fayllar_soni - a4n}, A4: {a4n}), "
        f"{tn} thumb; {natija}, {time.time() - t0:.1f} s")
    log(f"hajm: slaydlar {sb / 1048576:.1f} MB (o'rtacha {sb / max(sn, 1) / 1024:.0f} KB), thumb {tb / 1024:.0f} KB, "
        f"test {testb / 1024:.1f} KB, poster {vb / 1024:.0f} KB, kurs.json {KURS_JSON.stat().st_size / 1024:.1f} KB, "
        f"shriftlar {fn} ta {fb / 1024:.0f} KB")


# ---------------------------------------------------------------- main

def kuzatuvlar(darslar: dict[int, dict]) -> None:
    """Manbadagi farqlarni aytadi (hech narsa o'zgartirilmaydi)."""
    for n, d in darslar.items():
        k = d["kuzatuv"]
        if len(d["oraliqlar"]) > 1:
            ogoh(f"{n}-dars jadvalda {len(d['oraliqlar'])} ta slayd oralig'i: "
                 + ", ".join(f"{a}-{b}" for a, b in d["oraliqlar"]))
        if k["a4"] and k["16:9"]:
            ogoh(f"{n}-dars PDF aralash: {k['16:9']} ta 16:9 slayd + {k['a4']} ta A4 kitob beti "
                 f"(jadval: slaydlar {k['jadval_slayd']}, kitob betlari {k['kitob_bet']})")
        elif d["oraliqlar"] and k["16:9"] != k["jadval_slayd"]:
            ogoh(f"{n}-dars: PDF da {k['16:9']} slayd, jadval oraliqlari bo'yicha {k['jadval_slayd']}")
        if not d["oraliqlar"]:
            ogoh(f"{n}-dars: jadvalda taqdimot yo'q ({d['ustun4']}); PDF {len(d['turlar'])} bet, turi "
                 f"{'/'.join(sorted(set(d['turlar'])))}")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Fonetika kursi kontentini tayyorlash (web/content)")
    ap.add_argument("--majbur", action="store_true", help="hammasini qaytadan yasash")
    ap.add_argument("--faqat", default="", help="vergul bilan: shrift,slayd,test,video,kurs,tekshir")
    ap.add_argument("--ishchi", type=int, default=10, help="render jarayonlari soni (default 10)")
    ap.add_argument("--kuzatuv", action="store_true", help="manba kuzatuvlarini ham chiqarish")
    a = ap.parse_args()
    hammasi = ["shrift", "slayd", "test", "video", "kurs", "tekshir"]
    bosqich = [x.strip() for x in a.faqat.split(",") if x.strip()] or hammasi
    if set(bosqich) - set(hammasi):
        ap.error(f"noma'lum bosqich: {sorted(set(bosqich) - set(hammasi))}")

    t0 = time.time()
    holat = holat_oqish()
    if "shrift" in bosqich:
        shriftlar(a.majbur)
    yoq = [str(p) for p in (JADVAL, PDF_DIR) if not p.exists()]
    if yoq:
        log("XATO: manba topilmadi:\n  " + "\n  ".join(yoq))
        return 1
    try:
        qismlar, darslar = manbalar()
    except RuntimeError as e:
        log(f"XATO: manbalarni o'qib bo'lmadi: {e}")
        return 1
    log(f"manba: {len(darslar)} dars, {sum(len(d['turlar']) for d in darslar.values())} sahifa, "
        f"{len(qismlar)} qism ({', '.join(q['nomi'] for q in qismlar)})")
    if a.kuzatuv or "slayd" in bosqich:
        kuzatuvlar(darslar)
    ozgardi = False
    if "slayd" in bosqich:
        ozgardi |= slaydlar(darslar, holat, a.majbur, max(1, a.ishchi))
        holat_yoz(holat)
    if "test" in bosqich:
        tyol, o = testlar(darslar)
        ozgardi |= o
    else:
        tyol = test_yollari(darslar)
    if "video" in bosqich:
        vkurs, o = videolar(holat, a.majbur)
        ozgardi |= o
        holat_yoz(holat)
    else:
        vkurs = video_kurs_malumot()
    if "kurs" in bosqich:
        kurs(qismlar, darslar, vkurs, tyol, ozgardi)
        # jonli HTML taqdimotlar nusxasi (talaba rejimi) + kurs.json maydonlari - har doim oxirida
        import taqdimot
        try:
            taqdimot.main()
        except Exception as e:  # manba taqdimot topilmasa ham qolgan kontent buzilmasin
            xato(f"taqdimot: {e!r}")
    if "tekshir" in bosqich:
        tekshir(darslar)
    log(f"\nJami {time.time() - t0:.1f} s. Ogohlantirish: {len(OGOH)}, xato: {len(XATO)}.")
    if XATO:
        log("XATOLAR:\n  " + "\n  ".join(XATO))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

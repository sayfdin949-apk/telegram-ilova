#!/usr/bin/env python
"""Lucide ikonlar spraytini yig'adi: web/shared/icons.svg

    python tools/ikonlar.py            # yig'ish (tez; kesh: tools/_lucide_cache/)
    python tools/ikonlar.py --royxat   # qaysi nom qayerdan kelganini ham ko'rsatadi

Manba: https://cdn.jsdelivr.net/npm/lucide-static@0.469.0/icons/NAME.svg (ISC litsenziya).
Nomlar = BAZA ro'yxati + web/app va web/staff dagi *.html|*.js|*.css fayllardan topilganlar:
    ic('NAME')  ic("NAME")  ic(`NAME`)  icons.svg#NAME
    hamda izohdagi e'lon:  // ikonlar: name-1 name-2   (dinamik nomlar uchun)
Ishlatish:  <svg class="i" aria-hidden="true"><use href="/shared/icons.svg#NAME"/></svg>
Rang = CSS `color`. Ixtiyoriy: --i-sw (chiziq qalinligi, default 2), --i-fill (to'ldirish, default none).

Chiqish kodi: 0 = hammasi joyida; 1 = noma'lum ikon nomi bor (ro'yxat chiqadi, qolganlari baribir
yoziladi); 2 = tarmoq xatosi (nomni tekshirib bo'lmadi).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VERSIYA = "0.469.0"
URL = "https://cdn.jsdelivr.net/npm/lucide-static@" + VERSIYA + "/icons/{}.svg"

ROOT = Path(__file__).resolve().parent.parent
KESH = ROOT / "tools" / "_lucide_cache" / VERSIYA
CHIQISH = ROOT / "web" / "shared" / "icons.svg"
SKAN_PAPKALAR = [ROOT / "web" / "app", ROOT / "web" / "staff", ROOT / "web" / "admin"]  # faqat to'g'ridan-to'g'ri fayllar (p/ emas)
SKAN_KENGAYTMA = {".html", ".js", ".css"}

# Keng bazaviy to'plam: navigatsiya, media, holat, sozlamalar, grafiklar, odamlar, ta'lim.
BAZA = """
house book-open circle-play trophy user-round users-round chevron-left chevron-right chevron-up chevron-down
arrow-left arrow-right arrow-up arrow-down arrow-up-right menu ellipsis ellipsis-vertical external-link link
log-out log-in x plus minus search filter sliders-horizontal arrow-up-down layout-grid layout-dashboard
list list-ordered
play pause volume-2 volume-x skip-back skip-forward film video headphones mic image monitor-play
zoom-in zoom-out maximize-2 minimize-2 expand shrink rotate-cw rotate-ccw refresh-cw smartphone
check check-check circle-check circle-x circle-alert triangle-alert circle-help info circle-dot circle
badge-check loader-circle wifi wifi-off clock timer hourglass history lock lock-open shield shield-check
eye eye-off bell bell-off
settings sun moon sun-moon palette type save copy share-2 send download trash-2 pencil pen-line
key-round ticket toggle-left toggle-right
chart-column chart-line chart-bar trending-up trending-down activity gauge layers target
user user-plus user-x user-check user-cog users circle-user-round hand
book book-a book-check book-open-text notebook-pen graduation-cap presentation file file-text file-down
clipboard clipboard-check clipboard-list list-checks languages school
flame gem heart heart-crack star award medal crown sparkles zap rocket party-popper thumbs-up smile
footprints flag wand-sparkles lightbulb puzzle calendar calendar-days calendar-check
message-circle mail phone bot briefcase
""".split()

TAG_RE = re.compile(r"\bic\(\s*(['\"`])([a-z0-9]+(?:-[a-z0-9]+)*)\1")
HREF_RE = re.compile(r"icons\.svg#([a-z0-9]+(?:-[a-z0-9]+)*)")
ELON_RE = re.compile(r"(?://|/\*|<!--)\s*ikonlar:\s*([a-z0-9][a-z0-9 ,\-]*)")
NOM_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def skanerla() -> dict[str, set[str]]:
    """{nom: {qayerdan, ...}}"""
    topildi: dict[str, set[str]] = {}
    for n in BAZA:
        topildi.setdefault(n, set()).add("baza")
    for papka in SKAN_PAPKALAR:
        if not papka.is_dir():
            continue
        for f in sorted(papka.iterdir()):
            if not f.is_file() or f.suffix.lower() not in SKAN_KENGAYTMA:
                continue
            try:
                matn = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            joy = f.relative_to(ROOT).as_posix()
            nomlar = [m.group(2) for m in TAG_RE.finditer(matn)]
            nomlar += [m.group(1) for m in HREF_RE.finditer(matn)]
            for m in ELON_RE.finditer(matn):
                nomlar += [x for x in re.split(r"[\s,]+", m.group(1)) if x]
            for n in nomlar:
                if NOM_RE.match(n):
                    topildi.setdefault(n, set()).add(joy)
    return topildi


def almashtir(tmp: Path, path: Path) -> None:
    """os.replace + qayta urinish (Windows: server faylni o'qiyotgan bo'lsa PermissionError)."""
    for i in range(25):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.08 * (i + 1))
    os.replace(tmp, path)


def yukla(nom: str) -> tuple[str, str | None, str | None]:
    """(nom, svg_matn | None, xato | None). xato == '404' -> bunday ikon yo'q."""
    kf = KESH / f"{nom}.svg"
    if kf.is_file() and kf.stat().st_size > 50:
        return nom, kf.read_text(encoding="utf-8"), None
    oxirgi = ""
    for urinish in range(3):
        try:
            req = urllib.request.Request(URL.format(nom), headers={"User-Agent": "noon-ikonlar/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                matn = r.read().decode("utf-8")
            if "<svg" not in matn:
                return nom, None, "SVG emas"
            KESH.mkdir(parents=True, exist_ok=True)
            tmp = kf.with_name(f"{kf.name}.{os.getpid()}.tmp")
            tmp.write_text(matn, encoding="utf-8")
            almashtir(tmp, kf)
            return nom, matn, None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return nom, None, "404"
            oxirgi = f"HTTP {e.code}"
        except Exception as e:  # tarmoq
            oxirgi = type(e).__name__
        time.sleep(0.6 * (urinish + 1))
    return nom, None, oxirgi or "noma'lum xato"


def ichki(svg: str) -> str:
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    m = re.search(r"<svg\b([^>]*)>(.*)</svg>", svg, flags=re.S)
    if not m:
        raise ValueError("svg ildizi topilmadi")
    if 'viewBox="0 0 24 24"' not in m.group(1):
        raise ValueError("viewBox 0 0 24 24 emas")
    s = m.group(2)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r">\s+<", "><", s)
    s = re.sub(r"\s+/>", "/>", s)
    return s.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Lucide spraytini yig'ish (web/shared/icons.svg)")
    ap.add_argument("--royxat", action="store_true", help="har bir nom manbasini ko'rsatish")
    args = ap.parse_args()

    t0 = time.time()
    topildi = skanerla()
    nomlar = sorted(topildi)
    yangi = [n for n in nomlar if not (KESH / f"{n}.svg").is_file()]
    with ThreadPoolExecutor(max_workers=16) as ex:
        natijalar = list(ex.map(yukla, nomlar))

    noma_lum, tarmoq, belgilar = [], [], []
    for nom, svg, xato in natijalar:
        if xato == "404":
            noma_lum.append(nom)
            continue
        if xato:
            tarmoq.append((nom, xato))
            continue
        try:
            belgilar.append(
                f'<symbol id="{nom}" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                f'style="fill:var(--i-fill,none);stroke-width:var(--i-sw,2)">{ichki(svg)}</g></symbol>'
            )
        except ValueError as e:
            tarmoq.append((nom, f"buzuq SVG: {e}"))

    matn = (
        '<svg xmlns="http://www.w3.org/2000/svg">\n'
        f"<!-- Lucide icons v{VERSIYA} (ISC License, Copyright (c) Lucide Contributors). "
        "tools/ikonlar.py yasaydi - qo'lda tahrirlamang. -->\n"
        + "\n".join(belgilar)
        + "\n</svg>\n"
    )
    CHIQISH.parent.mkdir(parents=True, exist_ok=True)
    eski = CHIQISH.read_text(encoding="utf-8") if CHIQISH.is_file() else None
    if eski != matn:
        tmp = CHIQISH.with_name(f"{CHIQISH.name}.{os.getpid()}.tmp")
        tmp.write_text(matn, encoding="utf-8", newline="\n")
        almashtir(tmp, CHIQISH)
        holat = "yangilandi"
    else:
        holat = "o'zgarishsiz"

    skan = sorted(n for n, q in topildi.items() if q - {"baza"})
    print(f"icons.svg {holat}: {len(belgilar)} ikon, {CHIQISH.stat().st_size // 1024} KB, "
          f"yangi yuklangan {len([n for n in yangi if n not in noma_lum])}, "
          f"fayllardan topilgan {len(skan)}, {time.time() - t0:.1f} s")
    if args.royxat:
        for n in nomlar:
            print(f"  {n:28s} {', '.join(sorted(topildi[n]))}")

    kod = 0
    if tarmoq:
        print("\nXATO: quyidagi ikonlarni yuklab/tekshirib bo'lmadi (internetni tekshiring, qayta ishga tushiring):",
              file=sys.stderr)
        for n, x in tarmoq:
            print(f"  {n}: {x}", file=sys.stderr)
        kod = 2
    if noma_lum:
        print(f"\nXATO: Lucide {VERSIYA} da bunday ikon YO'Q ({len(noma_lum)} ta) - nomini tuzating:", file=sys.stderr)
        for n in noma_lum:
            print(f"  {n}   <- {', '.join(sorted(topildi[n]))}", file=sys.stderr)
        print("Ro'yxat: https://lucide.dev/icons/", file=sys.stderr)
        kod = 1
    return kod


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""Talabalar ilovasi kontentining NUQTA nusxasi (STAGING) — jonli web/content ga tegmaydi.

    python nuqta_kontent.py                       # hammasi (o'zgarmagan narsa qayta qilinmaydi)
    python nuqta_kontent.py --faqat taqdimot,kurs # bosqichlar: taqdimot, dars, video, kurs, tekshir
    python nuqta_kontent.py --faqat dars --darslar 1-12 --ishchi 4

Natija (hammasi Telegram ilova\\NUQTA\\ ichida):
  web/content/taqdimot/1..8/index.html — NUQTA deklar (talaba rejimi); 1-3 da so'z ovozi + taqdimot/N/ovoz/*.mp3
      manba: _manba/taqdimot/N/index.html (birinchi ishga tushishda mavjud NUQTA nusxadan olinadi, keyin o'zgarmaydi)
  web/content/dars/NN/NNN.webp + thumb.webp — NUQTA PDF lardan (kontent.py bilan bir xil o'lcham/sifat/nom);
      18-dars (NUQTA PDF yo'q) — jonlidagi rasmlar nusxasi
  web/content/video/dNN.webp — yangi motion videolar posteri (video tayyor bo'lsa)
  web/content/kurs.json — jonli kurs.json + 1-7-darslarga yangi NUQTA motion videolar (d01..d07), eski d02/d02b/d03 yo'q,
      versiya = bugun
  server/videolar.json — videolar loyihasi (fayl yo'llari dars.json "out" dan; video hali yo'q bo'lsa ham)
  joylash.json — staging -> jonli nusxalash ro'yxati (sha256 bilan)
Jonli kontent.py va skaner_tozala.py faqat import qilinadi (o'qiladi; __pycache__ yozilmaydi).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ST = Path(__file__).resolve().parent.parent                       # Telegram ilova\NUQTA
TG = ST.parent                                                     # Telegram ilova
LIVE = TG / "web" / "content"
LIVE_TOOLS = TG / "tools"
STC = ST / "web" / "content"
MANBA = ST / "_manba" / "taqdimot"
HOLAT = ST / "tools" / "_holat.json"
VIDEOLAR = ST / "server" / "videolar.json"
JOYLASH = ST / "joylash.json"
DESK = Path(os.environ.get("USERPROFILE") or str(Path.home())) / "Desktop"
NUQTA_PDF = DESK / "taqdimot" / "Fonetika kursi (36 dars)" / "NUQTA" / "PDF"
VIDEO_DIR = DESK / "videolar"
SOZ_OVOZI = Path(r"C:\Users\N.M\.claude\skills\soz-ovozi\scripts\soz_ovozi.py")
ESKI_ISH = Path(r"C:\Users\N.M\.claude\skills\eski-ishlar\scripts\eski_ish.py")
TZ = timezone(timedelta(hours=5))
SOZ_DEKLAR = (1, 2, 3)             # 1-7-darslar shu deklarda
VIDEO_DARSLAR = range(1, 8)        # yangi NUQTA motion videolar
VID_PREFIKS = "n"                  # id: n01..n07 — eski d02/d03 dagi «ko'rildi»/pozitsiya yangi videoga o'tmasin (06.10)
NOWIN = 0x08000000 if os.name == "nt" else 0

sys.path.insert(0, str(LIVE_TOOLS))
import kontent as K  # noqa: E402  (jonli tools — faqat funksiyalari ishlatiladi)


def log(*a):
    print(*a, flush=True)


def yoz(p: Path, data: bytes) -> bool:
    return K.yoz(p, data)


def arxivla(fayllar, sabab):
    fayllar = [str(f) for f in fayllar if Path(f).is_file()]
    if not fayllar:
        return
    r = subprocess.run([sys.executable, str(ESKI_ISH), *fayllar, "--sabab", sabab], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=NOWIN,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        raise SystemExit(f"XATO: eski_ish ishlamadi: {r.stderr[-300:]}")


def holat_oqish() -> dict:
    try:
        return json.loads(HOLAT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def holat_yoz(h: dict) -> None:
    HOLAT.parent.mkdir(parents=True, exist_ok=True)
    HOLAT.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- taqdimot

def taqdimot(holat: dict) -> None:
    t0 = time.time()
    for n in range(1, 9):
        out = STC / "taqdimot" / str(n) / "index.html"
        m = MANBA / str(n) / "index.html"
        if not m.is_file():
            if not out.is_file():
                raise SystemExit(f"XATO: {n}-dek NUQTA nusxasi yo'q: {out}")
            if 'id="nq-soz-js"' in out.read_text(encoding="utf-8"):
                raise SystemExit(f"XATO: {out} da so'z ovozi bor, toza manba yo'q")
            m.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out, m)
            log(f"taqdimot {n}: toza manba saqlandi -> {m}")
        if n in SOZ_DEKLAR:
            hp = ST / "tools" / f"_soz_{n}.json"
            r = subprocess.run([sys.executable, str(SOZ_OVOZI), str(m), str(out), "--dek", str(n),
                                "--kurs", str(LIVE / "kurs.json"), "--hisobot", str(hp)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NOWIN,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            for q in (r.stdout or "").splitlines():
                log(f"  [{n}] {q}")
            if r.returncode != 0:
                raise SystemExit(f"XATO: soz_ovozi ({n}-dek): {r.stderr[-800:]}")
        else:
            if not out.is_file() or out.read_bytes() != m.read_bytes():
                if out.is_file():
                    arxivla([out], f"NUQTA staging: {n}-dek manbadan qayta")
                yoz(out, m.read_bytes())
            log(f"taqdimot {n}: NUQTA dek (so'z ovozisiz) — {out.stat().st_size / 1048576:.1f} MB")
    log(f"taqdimot: {time.time() - t0:.0f} s")


# ---------------------------------------------------------------- dars rasmlari

def dars(holat: dict, darslar: set[int], ishchi: int, majbur: bool) -> None:
    import pymupdf
    t0 = time.time()
    hs = holat.setdefault("dars", {})
    ishlar, qayta = [], []
    jonli_kurs = json.loads((LIVE / "kurs.json").read_text(encoding="utf-8-sig"))
    for d in jonli_kurs["darslar"]:
        n = d["n"]
        if n not in darslar:
            continue
        papka = STC / "dars" / f"{n:02d}"
        pdf = NUQTA_PDF / d["pdf"]
        if not pdf.is_file():
            # NUQTA PDF yo'q (18-dars — faqat kitob betlari): jonli rasmlar nusxasi
            src = LIVE / "dars" / f"{n:02d}"
            k = 0
            for f in sorted(src.glob("*.webp")):
                k += yoz(papka / f.name, f.read_bytes())
            log(f"dars {n:02d}: NUQTA PDF yo'q — jonli rasmlar nusxasi ({len(list(src.glob('*.webp')))} fayl, {k} yangilandi)")
            continue
        with pymupdf.open(pdf) as doc:
            olchamlar, turlar = [], []
            for pg in doc:
                r = pg.rect
                t = K.sahifa_turi(r.width, r.height)
                turlar.append(t)
                olchamlar.append(K.olcham(t, r.width, r.height))
        yozuv = {"pdf": K.fayl_imzo(pdf), "imzo": K.IMZO, "sahifalar": len(turlar)}
        if "a4" in turlar:
            from skaner_tozala import VERSIYA
            yozuv["skaner"] = VERSIYA
        kerak = [papka / f"{i:03d}.webp" for i in range(1, len(turlar) + 1)] + [papka / "thumb.webp"]
        if not majbur and hs.get(f"{n:02d}") == yozuv and all(p.is_file() for p in kerak):
            continue
        qayta.append((n, yozuv))
        for i, (w, h) in enumerate(olchamlar):
            ishlar.append((str(pdf), i, str(papka / f"{i + 1:03d}.webp"), w, h,
                           str(papka / "thumb.webp") if i == 0 else None, turlar[i] == "a4"))
    if not ishlar:
        log(f"dars: hammasi tayyor ({len(darslar)} dars)")
        return
    log(f"dars: {len(qayta)} dars, {len(ishlar)} sahifa render ({ishchi} jarayon)...")
    ishlar.sort(key=lambda x: (-(x[4] * x[3]), x[0], x[1]))
    xatolar, bajarildi = {}, 0
    with ProcessPoolExecutor(max_workers=ishchi) as ex:
        fut = {ex.submit(K._render_ish, i): i for i in ishlar}
        for f in as_completed(fut):
            i = fut[f]
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                xatolar.setdefault(i[0], []).append(f"{i[1] + 1}-bet: {type(e).__name__}: {e}")
            bajarildi += 1
            if bajarildi % 50 == 0 or bajarildi == len(ishlar):
                log(f"  {bajarildi}/{len(ishlar)} sahifa, {time.time() - t0:.0f} s")
    for n, yozuv in qayta:
        pdf = str(NUQTA_PDF / next(d["pdf"] for d in jonli_kurs["darslar"] if d["n"] == n))
        if pdf in xatolar:
            for x in xatolar[pdf]:
                log(f"  XATO {n}-dars: {x}")
            continue
        hs[f"{n:02d}"] = yozuv
    holat_yoz(holat)
    log(f"dars: tayyor, {time.time() - t0:.0f} s")


# ---------------------------------------------------------------- video

def videolar_royxat() -> list[dict]:
    res = []
    for n in VIDEO_DARSLAR:
        dj = VIDEO_DIR / f"{n:02d}-dars motion" / "NUQTA" / "_ish" / "dars.json"
        if not dj.is_file():
            log(f"  ogohlantirish: {n}-dars motion dars.json yo'q — video qo'shilmadi")
            continue
        out = Path(json.loads(dj.read_text(encoding="utf-8"))["out"])
        m = re.match(r"^Fonetika (\d+)-dars - (.+?) \(motion\)\.mp4$", out.name)
        if not m or int(m.group(1)) != n:
            raise SystemExit(f"XATO: {dj}: kutilmagan video nomi {out.name}")
        res.append({"id": f"{VID_PREFIKS}{n:02d}", "dars": n, "nomi": m.group(2), "fayl": out})
    return res


def video(holat: dict) -> dict[int, list[dict]]:
    hv = holat.setdefault("video", {})
    kurs_v = {}
    for v in videolar_royxat():
        p: Path = v["fayl"]
        dav, poster = 0, STC / "video" / f"{v['id']}.webp"
        if p.is_file():
            try:
                davom, fast = K.mp4_malumot(p)
            except Exception as e:  # noqa: BLE001 — render hali yozilayotgan bo'lishi mumkin
                log(f"video {v['id']}: hali tayyor emas ({e}) — davomiylik 0")
                davom, fast = 0.0, True
            if davom:
                dav = int(round(davom))
                imzo = {"fayl": K.fayl_imzo(p), "w": K.POSTER_W, "h": K.POSTER_H}
                if hv.get(v["id"]) != imzo or not poster.is_file():
                    K._poster(p, davom, poster)
                    hv[v["id"]] = imzo
                log(f"video {v['id']}: {dav} s, faststart={'ha' if fast else 'YOQ'}, poster {poster.name}")
        else:
            log(f"video {v['id']}: KUTILMOQDA (fayl hali yo'q) — {p}")
        kurs_v.setdefault(v["dars"], []).append({"id": v["id"], "nomi": v["nomi"], "davomiylik": dav,
                                                 "poster": f"/content/video/{v['id']}.webp",
                                                 "url": f"/media/video/{v['id']}"})
    server_v = [{"id": v["id"], "dars": v["dars"], "nomi": v["nomi"], "fayl": str(v["fayl"])} for v in videolar_royxat()]
    data = (json.dumps(server_v, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if VIDEOLAR.is_file() and VIDEOLAR.read_bytes() != data:
        arxivla([VIDEOLAR], "NUQTA staging: videolar.json yangilandi")
    yoz(VIDEOLAR, data)
    holat_yoz(holat)
    return kurs_v


# ---------------------------------------------------------------- kurs.json

def kurs(kurs_v: dict[int, list[dict]]) -> None:
    k = json.loads((LIVE / "kurs.json").read_text(encoding="utf-8-sig"))
    for d in k["darslar"]:
        if d["n"] in VIDEO_DARSLAR:
            vl = kurs_v.get(d["n"], [])
            d["video"] = vl[0] if vl else None
            d["videolar"] = vl
    k["versiya"] = datetime.now(TZ).date().isoformat()
    out = STC / "kurs.json"
    data = K.json_bayt(k, ichki_qator="darslar")
    if out.is_file() and out.read_bytes() != data:
        arxivla([out], "NUQTA staging: kurs.json yangilandi")
    yoz(out, data)
    log(f"kurs: {out} — versiya {k['versiya']}, videolar: "
        + ", ".join(f"{d['n']}-dars {[v['id'] for v in d['videolar']]}" for d in k["darslar"] if d["videolar"]))


# ---------------------------------------------------------------- tekshiruv + joylash ro'yxati

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tekshir() -> int:
    from PIL import Image
    xato, ogoh = [], []
    k = json.loads((STC / "kurs.json").read_text(encoding="utf-8"))
    jk = json.loads((LIVE / "kurs.json").read_text(encoding="utf-8-sig"))
    if [d["n"] for d in k["darslar"]] != list(range(1, 37)):
        xato.append("kurs.json: darslar 1..36 emas")
    kalit = ["n", "qism", "nomi", "mavzu", "kitob", "slaydlar", "nisbat", "rasm", "thumb", "pdf", "video", "videolar", "test"]
    for d, j in zip(k["darslar"], jk["darslar"]):
        n = d["n"]
        if [x for x in d if x not in ("a4_slaydlar", "taqdimot", "kitob_betlari")] != kalit:
            xato.append(f"{n}: kalitlar {list(d)}")
        for x in d:
            if x not in ("video", "videolar") and d[x] != j.get(x):
                xato.append(f"{n}: '{x}' jonlidan farq qiladi")
        t = d.get("taqdimot")
        if t and not (STC / t["url"].removeprefix("/content/")).is_file():
            xato.append(f"{n}: taqdimot yo'q {t['url']}")
        papka = STC / "dars" / f"{n:02d}"
        nomlar = sorted(p.name for p in papka.glob("[0-9][0-9][0-9].webp"))
        jnom = sorted(p.name for p in (LIVE / "dars" / f"{n:02d}").glob("[0-9][0-9][0-9].webp"))
        if nomlar != [f"{i:03d}.webp" for i in range(1, len(nomlar) + 1)] or not nomlar:
            xato.append(f"{n}: dars rasmlari ketma-ket emas ({len(nomlar)})")
        if nomlar != jnom:
            ogoh.append(f"{n}-dars: rasm soni jonlida {len(jnom)}, NUQTA da {len(nomlar)}")
        for u in d.get("kitob_betlari") or []:
            if not (STC / u.removeprefix("/content/")).is_file():
                xato.append(f"{n}: kitob beti yo'q {u}")
        for nom in nomlar:
            with Image.open(papka / nom) as im, Image.open(LIVE / "dars" / f"{n:02d}" / nom) if (LIVE / "dars" / f"{n:02d}" / nom).is_file() else Image.new("RGB", im.size) as jm:
                if im.format != "WEBP" or im.size != jm.size:
                    xato.append(f"{n}/{nom}: {im.format} {im.size}, jonli {jm.size}")
        if not (papka / "thumb.webp").is_file():
            xato.append(f"{n}: thumb yo'q")
        for v in d.get("videolar") or []:
            if not (STC / v["poster"].removeprefix("/content/")).is_file():
                ogoh.append(f"{n}-dars {v['id']}: poster hali yo'q (video tayyor bo'lgach builder'ni qayta ishga tushiring)")
            if not v["davomiylik"]:
                ogoh.append(f"{n}-dars {v['id']}: davomiylik 0 (video hali yo'q)")
        if d["video"] != ((d.get("videolar") or [None])[0]):
            xato.append(f"{n}: video != videolar[0]")
    sv = json.loads(VIDEOLAR.read_text(encoding="utf-8"))
    kv = {v["id"] for d in k["darslar"] for v in d.get("videolar") or []}
    if not kv <= {v["id"] for v in sv}:
        xato.append("kurs.json video id lari videolar.json da yo'q")
    for v in sv:
        if not Path(v["fayl"]).is_file():
            ogoh.append(f"videolar.json {v['id']}: fayl hali yo'q — {v['fayl']}")
    # so'z ovozli deklar: har data-soz uchun mp3 bor
    for n in SOZ_DEKLAR:
        f = STC / "taqdimot" / str(n) / "index.html"
        h = f.read_text(encoding="utf-8")
        ids = sorted(set(re.findall(r'data-soz="([0-9_]+)"', h)))
        yoq = [i for i in ids if not (f.parent / "ovoz" / f"{i}.mp3").is_file()]
        log(f"tekshir: {n}-dek — {h.count('class=\"nq-soz\"')} so'z, {len(ids)} klip, mp3 yo'q: {len(yoq)}")
        if yoq:
            xato.append(f"{n}-dek: mp3 yo'q {yoq[:5]}")
    # joylash ro'yxati: staging -> jonli (faqat jonlidan farq qiladigan fayllar)
    juft = []
    for p in sorted(STC.rglob("*")):
        if not p.is_file() or p.name.endswith(".tmp"):
            continue
        rel = p.relative_to(STC)
        if rel.parts[0] == "taqdimot" and len(rel.parts) >= 3 and rel.parts[2] == "ovoz":
            n = int(rel.parts[1])
            hp = ST / "tools" / f"_soz_{n}.json"
            ishl = set(json.loads(hp.read_text(encoding="utf-8")).get("kliplar", [])) if hp.is_file() else set()
            if p.stem not in ishl:
                continue                       # eski ishga tushishdan qolgan, ishlatilmaydigan klip
        live = LIVE / rel
        holat_ = "yangi" if not live.is_file() else ("bir xil" if live.stat().st_size == p.stat().st_size and sha(live) == sha(p) else "almashadi")
        if holat_ != "bir xil":
            juft.append({"staging": str(p), "jonli": str(live), "holat": holat_, "bayt": p.stat().st_size, "sha256": sha(p)})
    sv_live = TG / "server" / "videolar.json"
    juft.append({"staging": str(VIDEOLAR), "jonli": str(sv_live), "holat": "almashadi", "bayt": VIDEOLAR.stat().st_size,
                 "sha256": sha(VIDEOLAR)})
    jd = {"yaratildi": datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), "fayllar": len(juft),
          "bayt": sum(x["bayt"] for x in juft), "xato": xato, "ogohlantirish": ogoh, "nusxalash": juft}
    JOYLASH.write_text(json.dumps(jd, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    c = Counter((Path(x["jonli"]).relative_to(TG).parts[2] if "content" in x["jonli"] else "server", x["holat"]) for x in juft)
    log(f"joylash: {len(juft)} fayl, {jd['bayt'] / 1048576:.1f} MB -> {JOYLASH}")
    log("  " + ", ".join(f"{a}/{b}: {n}" for (a, b), n in sorted(c.items())))
    for o in ogoh:
        log("  ogohlantirish: " + o)
    for x in xato:
        log("  XATO: " + x)
    return 1 if xato else 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--faqat", default="")
    ap.add_argument("--darslar", default="1-36")
    ap.add_argument("--ishchi", type=int, default=4)
    ap.add_argument("--majbur", action="store_true")
    a = ap.parse_args()
    hammasi = ["taqdimot", "dars", "video", "kurs", "tekshir"]
    b = [x.strip() for x in a.faqat.split(",") if x.strip()] or hammasi
    if set(b) - set(hammasi):
        ap.error(f"noma'lum bosqich: {set(b) - set(hammasi)}")
    m = re.fullmatch(r"(\d+)-(\d+)", a.darslar)
    darslar = set(range(int(m.group(1)), int(m.group(2)) + 1)) if m else {int(x) for x in a.darslar.split(",")}
    holat = holat_oqish()
    if "taqdimot" in b:
        taqdimot(holat)
    if "dars" in b:
        dars(holat, darslar, max(1, a.ishchi), a.majbur)
    kv = None
    if "video" in b or "kurs" in b:
        kv = video(holat)
    if "kurs" in b:
        kurs(kv)
    if "tekshir" in b:
        return tekshir()
    return 0


if __name__ == "__main__":
    sys.exit(main())

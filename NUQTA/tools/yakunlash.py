#!/usr/bin/env python
"""So'z ovozi + NUQTA staging — qolgan bosqichlar (06.10). Har bosqich alohida ham ishga tushadi (~2–6 daqiqa).

    python yakunlash.py kompyuter        # B: kompyuter uchun ovozli deklar 1–3 (kliplar dek ichida) + qo'shimcha o'qish ro'yxatlari
    python yakunlash.py ilova            # C: staging (nuqta_kontent.py: taqdimot 1–8 + so'z ovozi, dars rasmlari, video, kurs, tekshir)
    python yakunlash.py sinov-kompyuter  # D: ovozli deklar sinovi (1280; 390 tik/yotiq) + kontakt
    python yakunlash.py sinov-ilova      # D: staging deklar sinovi + ilova iframe sinovi (lokal http)
    python yakunlash.py hisobot          # dars bo'yicha jadval -> NUQTA\\_sinov\\yakun.json
    python yakunlash.py hammasi          # yuqoridagilar ketma-ket

Jonli Telegram ilova\\web\\, server\\, data\\ ga yozilmaydi; .claude\\ovoz\\ faqat o'qiladi; asl NUQTA deklar o'zgarmaydi.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ST = Path(__file__).resolve().parent.parent                       # Telegram ilova\NUQTA
TOOLS = ST / "tools"
STC = ST / "web" / "content"
SINOV = ST / "_sinov"
DESK = Path(os.environ.get("USERPROFILE") or str(Path.home())) / "Desktop"
KURS_NUQTA = DESK / "taqdimot" / "Fonetika kursi (36 dars)" / "NUQTA"
OVOZLI = KURS_NUQTA / "ovozli"
ROYXAT = DESK / "MUHAMMAD AMIN" / "Ovozim" / "darslar" / "NUQTA"
SKILL = Path(r"C:\Users\N.M\.claude\skills\soz-ovozi\scripts")
PY = sys.executable
NOWIN = 0x08000000 if os.name == "nt" else 0
DEKLAR = {1: "1 - Arab tiliga kirish (Fonetika 1-dars).html",
          2: "2 - Harflarning sifatlari (Fonetika 2-dars).html",
          3: "3 - Harflar (Fonetika 3-dars).html"}
SLAYDLAR = {1: "4,12,30", 2: "4,14,15", 3: "4,8,12,18"}            # so'zli slaydlar (dek raqami)


def run(cmd: list[str], nom: str) -> int:
    t0 = time.time()
    print(f"\n=== {nom}\n    {' '.join(cmd)}", flush=True)
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="replace", creationflags=NOWIN, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    for q in pr.stdout:
        print("    " + q.rstrip(), flush=True)
    kod = pr.wait()
    print(f"=== {nom}: {'OK' if kod == 0 else f'XATO (kod {kod})'}, {time.time() - t0:.0f} s", flush=True)
    return kod


def kompyuter() -> int:
    kod = 0
    for n, nom in DEKLAR.items():
        kod |= run([PY, str(SKILL / "soz_ovozi.py"), str(KURS_NUQTA / nom), str(OVOZLI / nom), "--dek", str(n), "--ichiga",
                    "--royxat", str(ROYXAT), "--hisobot", str(OVOZLI / "_ish" / f"dek{n}.json")], f"B: {n}-dek ovozli nusxa")
    return kod


def ilova() -> int:
    return run([PY, str(TOOLS / "nuqta_kontent.py")], "C: staging (nuqta_kontent.py)")


def sinov_kompyuter() -> int:
    kod = 0
    for n, nom in DEKLAR.items():
        kod |= run([PY, str(SKILL / "sinov.py"), str(KURS_NUQTA / nom), str(OVOZLI / nom), "--slaydlar", SLAYDLAR[n],
                    "--chiqish", str(SINOV / "kompyuter" / f"dek{n}")], f"D: {n}-dek (kompyuter) sinovi")
    return kod


def sinov_ilova() -> int:
    kod = 0
    for n in DEKLAR:
        kod |= run([PY, str(SKILL / "sinov.py"), str(ST / "_manba" / "taqdimot" / str(n) / "index.html"),
                    str(STC / "taqdimot" / str(n) / "index.html"), "--slaydlar", SLAYDLAR[n],
                    "--chiqish", str(SINOV / "ilova" / f"dek{n}")], f"D: {n}-dek (ilova staging) sinovi")
    kod |= run([PY, str(TOOLS / "ilova_sinov.py"), "--chiqish", str(SINOV / "ilova" / "iframe")], "D: ilova iframe sinovi")
    return kod


def _oqi(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def hisobot() -> int:
    res = {"darslar": {}, "sinov": {}, "joylash": None}
    print("\nDars | arabcha so'z (joy/unik) | ovozli (joy/unik) | yozuvsiz: so'z / harf / shakl | shubhali | "
          "qo'shilgan | boshqa darsdan | uzun klip | ro'yxat PDF")
    for n in DEKLAR:
        hk = _oqi(OVOZLI / "_ish" / f"dek{n}.json") or {}
        hi = _oqi(TOOLS / f"_soz_{n}.json") or {}
        for ds, d in (hk.get("darslar") or {}).items():
            di = (hi.get("darslar") or {}).get(ds)
            ry = (hk.get("royxat") or {}).get(ds) or {}
            x = {"dek": n, "jami_joy": d["jami_joy"], "unik": d["unik"], "ovozli_joy": d["ovozli_joy"],
                 "ovozli_unik": d["ovozli_unik"], "yoq_soz": d["yoq_soz"], "yoq_harf": d["yoq_harf"], "yoq_shakl": d["yoq_shakl"],
                 "shubhali": [f"{s['ar']} (slayd {','.join(map(str, s['slaydlar']))}, {s['klip']}, {s['oxshashlik']})"
                              for s in d["shubhali"]],
                 "qoshilgan": d["qoshilgan"], "boshqa_darsdan": d["boshqa_darsdan"], "uzun": d["uzun"],
                 "oralmadi": d["oralmadi"], "royxat_pdf": ry.get("pdf"), "royxat_json": ry.get("json"),
                 "royxat_band": ry.get("soni"),
                 "ilova_bilan_teng": bool(di) and all(di[k] == d[k] for k in ("jami_joy", "ovozli_joy", "yoq_unik", "shubhali_unik"))}
            res["darslar"][ds] = x
            print(f"{int(ds):4} | {x['jami_joy']}/{x['unik']} | {x['ovozli_joy']}/{x['ovozli_unik']} | "
                  f"{x['yoq_soz']} / {x['yoq_harf']} / {x['yoq_shakl']} | {len(x['shubhali'])} | {len(x['qoshilgan'])} | "
                  f"{len(x['boshqa_darsdan'])} | {len(x['uzun'])} | {x['royxat_pdf'] or '-'}"
                  + ("" if x["ilova_bilan_teng"] else "  [ilova nusxasi bilan FARQ yoki ilova bosqichi bajarilmagan]"))
            for s in x["shubhali"]:
                print(f"       shubhali: {s}")
    for p in sorted(SINOV.rglob("sinov.json")) + sorted(SINOV.rglob("natija.json")):
        j = _oqi(p) or {}
        res["sinov"][str(p.parent.relative_to(SINOV))] = {"xato": j.get("xato"), "kontakt": str(p.parent / "kontakt.png")}
        print(f"sinov {p.parent.relative_to(SINOV)}: {'OK' if not j.get('xato') else j.get('xato')}")
    jz = _oqi(ST / "joylash.json")
    if jz:
        res["joylash"] = {"fayllar": jz["fayllar"], "bayt": jz["bayt"], "xato": jz["xato"], "ogohlantirish": jz["ogohlantirish"]}
        print(f"joylash.json: {jz['fayllar']} fayl, {jz['bayt'] / 1048576:.1f} MB, xato {len(jz['xato'])}, "
              f"ogohlantirish {len(jz['ogohlantirish'])}")
    SINOV.mkdir(parents=True, exist_ok=True)
    (SINOV / "yakun.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {SINOV / 'yakun.json'}")
    return 0


BOSQICH = {"kompyuter": kompyuter, "ilova": ilova, "sinov-kompyuter": sinov_kompyuter, "sinov-ilova": sinov_ilova,
           "hisobot": hisobot}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    b = sys.argv[1:] or ["hammasi"]
    if b == ["hammasi"]:
        b = list(BOSQICH)
    if set(b) - set(BOSQICH):
        print(__doc__)
        return 2
    kod = 0
    for x in b:
        kod |= BOSQICH[x]()
    return kod


if __name__ == "__main__":
    sys.exit(main())

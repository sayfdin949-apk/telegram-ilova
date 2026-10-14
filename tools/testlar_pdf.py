"""Loyiha mini testlarini o'qituvchi tekshiruvi uchun bitta NOON PDF ga yig'adi (javoblar, izoh, manba bilan).
python tools/testlar_pdf.py   ->  Dizayn/Mini testlar - loyiha (o'qituvchi).html/.pdf"""
import html, json, re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
LOY = R / "web/content/test_loyiha"
KURS = json.loads((R / "web/content/kurs.json").read_text(encoding="utf-8"))
OUT = R / "Dizayn" / "Mini testlar - loyiha (o'qituvchi).html"
AR = re.compile(r"([؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿][؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿\sً-ٰٟـ]*)")
E = lambda s: html.escape(str(s), quote=False)


def ar(s):
    return AR.sub(lambda m: f'<bdi dir="rtl" class="ar">{m.group(1).strip()}</bdi> ' if m.group(1).strip() else m.group(1), E(s))


QARORLAR = [
    "Atamalar: testlarda AGENT.md shakli (Rixva, Bayniya, Takrir, Istitola, Inhirof) ishlatilgan, taqdimot va kurs fayllarida esa Roxova, Bayniyya, Tikrar, Istitala, Inhiraf. Qaysi shakl qolsin? (2-dars 1-savol, 4-dars 2-savol, 6-dars 1-savol, 7-dars 1–2-savollar)",
    "1–2-darslarda yakka harflar (masalan ء ه, ق ط ب ج د) tasnif uchun harakatsiz berilgan, garchi ular 3–7-darslarda batafsil o'tilsa ham. Ma'qulmi?",
    "9-darsning amaliy jumlalari اَلْ bilan boshlangani (15-darsda o'tiladi) uchun testga olinmadi.",
    "13-dars 3-savol: toi marbutaning to'xtab o'qilganda هْ ga aylanishi — vaqf 17-darsda o'tiladi, lekin bu 13-darsning o'z manbasida bor. Qolsinmi?",
    "19-dars 4-savol: noto'g'ri variantlardagi so'zlar keyingi darslar jadvalidan olingan (harflari o'tilgan).",
    "24-dars 5-savol: «mim aniq, g'unnasiz» gapi kitobdan emas, dars49.json eslatmasidan.",
    "22–23-darslar: amaliy jumlalarda yashiriladigan nun ustida sukun yo'q — kitobdagidek qoldirildi. 23-dars 5-savol: jumlada 3 ta yashirish deb hisoblangan.",
    "36-dars 3-savol: ko'plik mimi damma olishi kitobda alohida yozilmagan (arab tilida to'g'ri).",
    "28-dars 5-savol: «yumshoq harf» ta'rifi manbada ochiq yozilmagan, misollarga tayanadi.",
    "Lotin yozuvidagi o'qilishlarning bir qismi AGENT.md qoidasi bo'yicha tuzilgan (masalan Qomar, G'oyru, Habban, ad-darsu, Toviilaa, Baytih) — ko'z bilan tekshiring.",
]


def main():
    darslar = {d["n"]: d for d in KURS["darslar"]}
    fayllar = sorted(LOY.glob("*.json"))
    jami = sum(len(json.loads(f.read_text(encoding="utf-8"))["savollar"]) for f in fayllar)
    bloklar = []
    for f in fayllar:
        t = json.loads(f.read_text(encoding="utf-8"))
        n = t["dars"]
        d = darslar[n]
        bloklar.append(f'<div class="sec"><div class="ico">{{{{clipboard-check}}}}</div><div><h2><span class="num">{n}.</span>{E(d["mavzu"])}</h2><div class="tbar"></div></div></div>')
        for i, q in enumerate(t["savollar"], 1):
            opts = "".join(
                f'<li class="{"ok" if j == q["ok"] else ""}"><b>{"ABCD"[j]}</b> {ar(o)}{" &nbsp;<span class=\"pill lime\">to&#39;g&#39;ri</span>" if j == q["ok"] else ""}</li>'
                for j, o in enumerate(q["opts"]))
            bloklar.append(
                f'<div class="card q"><div class="qh"><span class="qn">{n}.{i}</span><b>{ar(q["q"])}</b></div>'
                f'<ul class="op">{opts}</ul><div class="iz"><b>Izoh:</b> {ar(q["izoh"])}</div>'
                f'<div class="mb">Manba: {E(q.get("manba", ""))}</div></div>')
    qarorlar = "".join(f"<li>{ar(x)}</li>" for x in QARORLAR)
    body = f"""
<section class="page">
  <header class="hero">
    <div class="kicker">{{{{list-checks}}}} Fonetika kursi · mini testlar</div>
    <h1>Mini testlar — loyiha</h1>
    <div class="sub">Har darsdan keyin 5 savollik test. O'qituvchi uchun: to'g'ri javoblar, izohlar va manbalar bilan.</div>
    <div class="tbar"></div>
    <div class="meta"><span class="pill">{len(fayllar)} dars</span><span class="pill">{jami} savol</span><span class="pill">8-dars testi avvaldan bor</span><span class="pill dark">Tasdiq kutilmoqda</span></div>
  </header>
  <div class="page-body">
    <div class="note warn">{{{{triangle-alert}}}}<div><b>Ilovaga hali qo'yilmagan.</b> Siz tasdiqlaganingizdan keyin qo'yiladi. O'zgartirish uchun «N-dars, M-savol: ...» deb yozing.</div></div>
    <div class="card"><div class="card-head">{{{{circle-help}}}}<h3>Qaroringiz kerak bo'lgan joylar</h3></div><ol class="steps">{qarorlar}</ol></div>
  </div>
  <footer class="foot"><span class="brand"><span class="dot"></span>Muhammadamin</span><span class="pno"></span></footer>
</section>
<section class="page">
  <div class="run-head"><span class="brand">Fonetika · mini testlar</span><span>Loyiha — o'qituvchi nusxasi</span></div>
  <div class="page-body">{''.join(bloklar)}</div>
  <footer class="foot"><span class="brand"><span class="dot"></span>Muhammadamin</span><span class="pno"></span></footer>
</section>"""
    css = """<style>
.q{padding:10px 14px;margin:0 0 8px}.qh{display:flex;gap:8px;align-items:baseline;font-size:12.5px}
.qn{flex:none;font-weight:800;color:#1A6A2A;min-width:30px}
.op{list-style:none;margin:6px 0 4px 38px;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:3px 14px;font-size:12px}
.op li{padding:2px 6px;border-radius:6px}.op li.ok{background:#E3F7DF}.op b{color:#5A8060;margin-right:4px}
.iz,.mb{margin-left:38px;font-size:11px;color:#3A6040}.mb{color:#7A9580;font-size:10px;margin-top:2px}
.ar{font-family:'Sakkal Majalla','Noto Naskh Arabic',serif;font-size:1.35em}
</style>"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f'<!doctype html><html lang="uz"><head><meta charset="utf-8"><title>Mini testlar — loyiha</title><!-- NOON:HEAD -->{css}</head><body>{body}</body></html>', encoding="utf-8")
    subprocess.run([sys.executable, str(Path.home() / ".claude/skills/noon-ui/scripts/build.py"), str(OUT)], check=True)


if __name__ == "__main__":
    main()

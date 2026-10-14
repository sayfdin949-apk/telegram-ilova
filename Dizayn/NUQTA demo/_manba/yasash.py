# NUQTA demo yig'uvchisi.
# demo.src.html dagi [[...]] belgilarini manbalardan AYNAN nusxa bilan almashtiradi
# (arabcha matn qo'lda yozilmaydi), keyin nuqta-ui build.py bilan internetsiz demo.html chiqaradi.
#   [[a:q4.o2]]   -> 08.json: 4-savol, 3-variant, <bdi dir="rtl" lang="ar"> ichida
#   [[m:q4.izoh]] -> 08.json matni; ichidagi arabcha bo'laklar <bdi> ga o'raladi
#   [[deck:...]]  -> taqdimot\4\index.html, 05-slayd (Alif mad harfi)
#   [[app:namuna]] -> app.js dagi arabcha o'lcham namunasi
#   [[rasm:slayd05]] -> 05-slayd rasmi (data URI)
# Manbalar faqat o'qiladi.
import html as H
import json
import re
import subprocess
import sys
from pathlib import Path

ILOVA = Path(r"C:\Users\N.M\Desktop\MUHAMMAD AMIN\Telegram ilova")
TEST = ILOVA / "web" / "content" / "test" / "08.json"
DECK = ILOVA / "web" / "content" / "taqdimot" / "4" / "index.html"
APPJS = ILOVA / "web" / "app" / "app.js"
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent
BUILD = Path(r"C:\Users\N.M\.claude\skills\nuqta-ui\scripts\build.py")

AR = "\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF"
AR_RUN = re.compile(f"[{AR}]+(?:\\s+[{AR}]+)*")


def bdi(s: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<bdi dir="rtl" lang="ar"{c}>{s}</bdi>'


def mix(s: str) -> str:
    """Matnni HTML-xavfsiz qiladi va arabcha bo'laklarni <bdi> ga o'raydi (harflar o'zgarmaydi)."""
    out, pos = [], 0
    for m in AR_RUN.finditer(s):
        out.append(H.escape(s[pos:m.start()], quote=False))
        out.append(bdi(m.group(0)))
        pos = m.end()
    out.append(H.escape(s[pos:], quote=False))
    return "".join(out)


def test_val(key: str):
    data = json.loads(TEST.read_text(encoding="utf-8"))
    q, f = key.split(".")
    Q = data["savollar"][int(q[1:]) - 1]
    if f.startswith("o"):
        return Q["opts"][int(f[1:])]
    return Q[f]


def deck_parts() -> dict:
    src = DECK.read_text(encoding="utf-8")
    blk = src[src.index("<!-- 05 -->"):src.index("<!-- 06 -->")]
    g = re.search(r'<h2 class="lhead"><span class="g">(.*?)</span><span class="nm">(.*?)</span><span class="tg">(.*?)</span>', blk)
    ps = re.findall(r'<p class="qt">(.*?)</p>', blk, flags=re.S)
    ps = [re.sub(r'<span class="ar inl">(.*?)</span>', lambda m: bdi(m.group(1), "inl"), p) for p in ps]
    tiles = re.findall(r'<span class="qe"><span class="g">(.*?)</span><span class="n">(.*?)</span></span>', blk)
    t_html = "".join(
        f'<span class="qe"><span class="g" dir="rtl" lang="ar">{g_}</span><span class="n">{n}</span></span>'
        for g_, n in tiles)
    sect = re.search(r'data-sect="(.*?)"', blk).group(1)
    return {"g": bdi(g.group(1)), "nom": g.group(2), "teg": g.group(3), "p1": ps[0], "p2": ps[1],
            "tiles": t_html, "sect": sect}


def app_sample() -> str:
    js = APPJS.read_text(encoding="utf-8")
    m = re.search(r"<span class=\"ar-sample\">\$\{bdi\('([^']+)'\)\}", js)
    return m.group(1)


def main():
    src = (HERE / "demo.src.html").read_text(encoding="utf-8")
    deck = deck_parts()
    rasm = (HERE / "slayd05_rasm.txt").read_text(encoding="utf-8").strip()
    used = []

    def rep(m):
        kind, key = m.group(1), m.group(2)
        used.append(f"{kind}:{key}")
        if kind == "a":
            return bdi(test_val(key))
        if kind == "m":
            return mix(test_val(key))
        if kind == "deck":
            return deck[key]
        if kind == "app":
            return bdi(app_sample())
        if kind == "rasm":
            return rasm
        raise SystemExit(f"Noma'lum belgi: {m.group(0)}")
    out = re.sub(r"\[\[(a|m|deck|app|rasm):([\w.]+)\]\]", rep, src)
    left = re.findall(r"\[\[[^\]]+\]\]", out)
    if left:
        raise SystemExit(f"Almashtirilmagan belgilar: {left}")
    mid = HERE / "demo.joylangan.html"
    mid.write_text(out, encoding="utf-8")
    print(f"Joylandi: {len(used)} ta belgi")
    r = subprocess.run([sys.executable, str(BUILD), str(mid), "--html", str(OUT_DIR / "demo.html")])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()

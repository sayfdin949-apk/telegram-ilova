"""Asl HTML taqdimotlarni Mini App uchun nusxalaydi va "talaba rejimi" qo'shadi (asl fayllar o'zgarmaydi).

    python tools/taqdimot.py

Natija: web/content/taqdimot/<1..8>/index.html (+ fonts/, rasmlar/) va web/content/kurs.json ga har dars uchun
"taqdimot": {"url", "from", "to"} (1-based slayd raqamlari), "slaydlar" = to-from+1; 3-7-darslarga
"kitob_betlari" (PDF dagi kitob skanerlari rasmlari). 18-dars (faqat kitob betlari) o'zgarmaydi.

Talaba rejimi (iframe ichida):  index.html?from=F&to=T[&start=K]
  ota oynaga: {noon:'slide', n, total, step, steps} va {noon:'end'};  ota oynadan: {noon:'next'|'prev'} yoki {noon:'goto', n}
"""
import html as H
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"C:\Users\N.M\Desktop\taqdimot\Fonetika kursi (36 dars)")
OUT = ROOT / "web" / "content" / "taqdimot"
KURS = ROOT / "web" / "content" / "kurs.json"

DECKS = {
    1: SRC / "1 - Arab tiliga kirish (Fonetika 1-dars)" / "Fonetika 1-dars.html",
    2: SRC / "2 - Harflarning sifatlari (Fonetika 2-dars)" / "Fonetika 2-dars.html",
    3: SRC / "3 - Harflar (Fonetika 3-dars)" / "Fonetika 3-dars.html",
    4: SRC / "4 - Mad harflari va mad qoidalari.html",
    5: SRC / "5 - Tashdid va tanvin.html",
    6: SRC / "6 - Yozilishi va o'qilishi.html",
    7: SRC / "7 - Fonetika qoidalari.html",
    8: SRC / "8 - O'qish matnlari.html",
}

GUARD_OLD = "if(busy||to===si||to<0||to>=slides.length) return;"
GUARD_NEW = ("if(busy||to===si||to<0||to>=slides.length||(window.__rng&&(to<window.__rng[0]||to>window.__rng[1]))){"
             "if(!busy&&window.__rng&&to>window.__rng[1]&&window.__onEnd)window.__onEnd();return;}")
PAINT_OLD = "function paint(upTo){"
PAINT_NEW = ("function paint(upTo){setTimeout(function(){if(window.__notify)"
             "window.__notify(si,ki,plan[si].keys.length);},0);")
JUMP_RE = re.compile(r"(function jump\(n\)\{[^\n]*\})")

STUDENT = r"""
<style id="noon-talaba">
#panel,#vid,#hint,#count,#bar,.rec,#recdot,#rectime,.lprog{display:none!important}
html,body{overscroll-behavior:none;touch-action:pan-y pinch-zoom}
html.noon-init *,html.noon-init *::before,html.noon-init *::after{transition:none!important;animation-duration:0s!important}
</style>
<script id="noon-talaba-js">
(function(){
  var q = new URLSearchParams(location.search);
  var n = document.querySelectorAll('.slide').length;
  var from = Math.max(1, Math.min(n, parseInt(q.get('from') || '1', 10) || 1));
  var to = Math.max(from, Math.min(n, parseInt(q.get('to') || String(n), 10) || n));
  var start = Math.max(1, parseInt(q.get('start') || '1', 10) || 1);
  var ready = false;
  window.__rng = [from - 1, to - 1];
  function send(m){ try { if (parent !== window) parent.postMessage(m, '*'); } catch (e) {} }
  window.__onEnd = function(){ if (ready) send({noon: 'end'}); };
  window.__notify = function(si, ki, steps){
    if (!ready || si < from - 1 || si > to - 1) return;
    send({noon: 'slide', n: si - from + 2, total: to - from + 1, step: ki, steps: steps});
  };
  function cur(){ var c = window.__deck.cur(); window.__notify(c[0], c[1], c[2]); }
  window.addEventListener('message', function(e){
    var d = e.data || {}; if (!window.__deck || !d.noon || !ready) return;
    if (d.noon === 'next') window.__deck.next();
    else if (d.noon === 'prev') window.__deck.prev();
    else if (d.noon === 'goto') window.__deck.jump(from - 2 + Math.max(1, Math.min(to - from + 1, d.n | 0)));
    else if (d.noon === 'ping') cur();
  });
  /* talaba rejimida kamera, yozib olish va to'liq ekran tugmalari ishlamaydi; Home/End darsdan tashqariga chiqarmaydi */
  window.addEventListener('keydown', function(e){
    var k = (e.key || '').toLowerCase();
    if (k === 'v' || k === 'c' || k === 'r' || k === 'f' || k === 'home' || k === 'end' || e.metaKey || e.ctrlKey) e.stopImmediatePropagation();
  }, true);
  function go(){
    var H = document.documentElement, t = Math.min(to - 1, from - 2 + start);
    H.classList.add('noon-init');
    if (t > 0) window.__deck.jump(t);
    setTimeout(function(){ H.classList.remove('noon-init'); ready = true; cur(); }, 380);
  }
  if (document.readyState === 'complete') setTimeout(go, 30); else window.addEventListener('load', function(){ setTimeout(go, 30); });
})();
</script>
"""


def jadval_oraliqlari():
    """Dars jadvali.html: dars -> (taqdimot raqami, from, to). Bir darsda bir nechta oraliq bo'lsa — birlashtiriladi."""
    h = (SRC / "Dars jadvali.html").read_text(encoding="utf-8")
    res = {}
    for tr in re.findall(r"<tr[\s\S]*?</tr>", h):
        tds = re.findall(r"<td[\s\S]*?</td>", tr)
        if not tds:
            continue
        txt = lambda s: H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()
        first = txt(tds[0])
        if not first.isdigit():
            continue
        dars = int(first)
        rng = re.findall(r"(\d)\s*-\s*[^0-9]*?slaydlar\s*(\d+)\s*[–-]\s*(\d+)", txt(" ".join(tds[1:])))
        if rng:
            deck = {int(r[0]) for r in rng}
            assert len(deck) == 1, (dars, rng)
            res[dars] = (deck.pop(), min(int(r[1]) for r in rng), max(int(r[2]) for r in rng))
    return res


def nusxala(n, src):
    dst = OUT / str(n)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for sub in ("fonts", "rasmlar"):
        p = src.parent / sub
        if p.is_dir() and n <= 3:
            shutil.copytree(p, dst / sub)
    if not (dst / "fonts").exists():
        shutil.copytree(DECKS[1].parent / "fonts", dst / "fonts")
    h = src.read_text(encoding="utf-8")
    for old, new in ((GUARD_OLD, GUARD_NEW), (PAINT_OLD, PAINT_NEW)):
        assert h.count(old) == 1, (n, old)
        h = h.replace(old, new)
    assert len(JUMP_RE.findall(h)) == 1, n
    h = JUMP_RE.sub(lambda m: m.group(1) + "\n  window.__deck={next:next,prev:prev,jump:jump,"
                    "cur:function(){return [si,ki,plan[si].keys.length];}};", h)
    i = h.rfind("</body>")
    h = h[:i] + STUDENT + h[i:]
    (dst / "index.html").write_text(h, encoding="utf-8")
    return len(re.findall(r'<section class="slide', h))


def manba_sanoq():
    """Har bir manba taqdimotdagi slaydlar soni (nusxalamasdan)."""
    return {n: len(re.findall(r'<section class="slide', p.read_text(encoding="utf-8"))) for n, p in DECKS.items()}


def kursga_qoshish(kurs, sanoq=None):
    """kurs.json lug'atiga (joyida) taqdimot maydonlarini qo'shadi. Takroriy chaqiruv natijani o'zgartirmaydi.
    tools/kontent.py ham kurs.json ni yozishdan oldin shuni chaqiradi - maydonlar hech qachon yo'qolmaydi."""
    sanoq = sanoq or manba_sanoq()
    rng = jadval_oraliqlari()
    for d in kurs["darslar"]:
        r = rng.get(d["n"])
        if not r:
            continue
        deck, a, b = r
        assert b <= sanoq[deck], (d["n"], r, sanoq[deck])
        d["taqdimot"] = {"url": f"/content/taqdimot/{deck}/index.html", "from": a, "to": b}
        a4 = d.pop("a4_slaydlar", None) or []
        if a4:
            d["kitob_betlari"] = [f"{d['rasm']}{i:03d}.webp" for i in a4]
        d["slaydlar"] = b - a + 1
    kurs["jami_slayd"] = sum(d["slaydlar"] for d in kurs["darslar"])
    return rng


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sanoq = {n: nusxala(n, p) for n, p in DECKS.items()}
    kurs = json.loads(KURS.read_text(encoding="utf-8"))
    eski = json.dumps(kurs, ensure_ascii=False, sort_keys=True)
    rng = kursga_qoshish(kurs, sanoq)
    if json.dumps(kurs, ensure_ascii=False, sort_keys=True) != eski:
        tmp = KURS.with_name(f"kurs.json.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(kurs, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, KURS)
        print("kurs.json yangilandi")
    else:
        print("kurs.json o'zgarishsiz")
    yoq = [d["n"] for d in kurs["darslar"] if "taqdimot" not in d]
    print("taqdimotlar:", sanoq)
    print("oraliqlar:", {k: v for k, v in sorted(rng.items())})
    print("taqdimotsiz darslar:", yoq, "| jami slayd:", kurs["jami_slayd"])


if __name__ == "__main__":
    main()

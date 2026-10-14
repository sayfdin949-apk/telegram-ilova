"""Xodimlar Mini App (web/staff) va demo panellar adapteri sinovi - Playwright + Edge.

    python tools/test_staff.py            # yangi sinov serveri (port 8792, data/sinov_staff.db, --seed), sinov, to'xtatish
    python tools/test_staff.py --keep     # oxirida serverni to'xtatmaslik
    python tools/test_staff.py --no-server  # 8792 da allaqachon ishlayotgan serverdan foydalanish

Rasmlar: _sinov/staff/*.png. Natija: oxirida PASS/FAIL ro'yxati, xato bo'lsa chiqish kodi 1.
05.10: xodimlar sahifasi NUQTA UI da - test_nuqta(): manzara aylanishi (nuqta.staff.manzara), kun/tun soatga qarab
(ochiq turganda ham), Telegram ranglari = --bg, 6 manzara x kun/tun, 390/1024, kontrast >= 4,5:1, oq/qora/pushti fon yo'q,
44 px, fokus halqasi, prefers-reduced-motion. Muhit: NOON_STAFF_PORT, NOON_STAFF_DB.
06.10 (egasi, "1 ha"): Bugun - "Uslub tanlovi" o'rniga Ko'rinish kartasi (check_korinish, 4 rol x telefon/kompyuter),
O'quvchilar - uslub chipi o'rniga oxirgi manzara (+ kun/tun) chipi; test_old_api(): eski server (korinish / manzara yo'q)
va bo'sh davr.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from sinov_initdata import SINOV_XODIM_TOKEN, XODIM, make  # noqa: E402

PORT = int(os.environ.get("NOON_STAFF_PORT", "8792"))          # boshqa agent bilan to'qnashmaslik uchun
DB_REL = os.environ.get("NOON_STAFF_DB", "data/sinov_staff.db")
BASE = f"http://127.0.0.1:{PORT}"
OUT = ROOT / "_sinov" / "staff"
MOCK = ROOT / "tools" / "tg_mock.js"
MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}
ROLE_PANELS = {"ceo": ["ceo", "admin", "lms", "ustoz"], "admin": ["admin", "lms"], "ustoz": ["ustoz", "lms"],
               "assistent": ["assistent"]}
LMS_IDS = ["courses", "builder", "bank", "exams", "grades", "certs", "pipeline"]

NV = ["sahro", "voha", "shahar", "qahva", "xattot", "shom"]
TABS = ["bugun", "kurs", "oquvchilar", "panellar", "xodimlar"]
# soatni soxtalashtirish: window.__off (ms) haqiqiy vaqtga qo'shiladi; __setHour(h) - mahalliy soatni h:mm ga qo'yadi
FAKE_DATE = """(function(){const R=Date;window.__off=0;class F extends R{constructor(...a){if(a.length){super(...a)}else{super(R.now()+window.__off)}}
static now(){return R.now()+window.__off}};window.Date=F;window.__setHour=function(h,m){const d=new R();window.__off=((h*60+(m||0))-(d.getHours()*60+d.getMinutes()))*60000;};})();"""

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    RESULTS.append((bool(ok), name + (f" - {detail}" if detail and not ok else "")))
    print(("  PASS " if ok else "  FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""), flush=True)
    return bool(ok)


# ---------------------------------------------------------------- server
def server_up() -> bool:
    try:
        with urllib.request.urlopen(BASE + "/staff/", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def stop_server(proc) -> None:
    stop = ROOT / "data" / f"sinov_{PORT}.stop"
    try:
        stop.write_text("stop", encoding="utf-8")
    except OSError:
        pass
    t0 = time.time()
    while time.time() - t0 < 15 and server_up():
        time.sleep(0.3)
    if proc is not None and proc.poll() is None:
        proc.terminate()
    try:
        stop.unlink()
    except OSError:
        pass


def start_server():
    if server_up():
        stop_server(None)
    proc = subprocess.Popen([sys.executable, str(ROOT / "server" / "main.py"), "--sinov", "--port", str(PORT),
                             "--db", DB_REL, "--seed"], cwd=str(ROOT),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    t0 = time.time()
    while time.time() - t0 < 40:
        if server_up():
            return proc
        if proc.poll() is not None:
            raise SystemExit("server ishga tushmadi (kod %s)" % proc.returncode)
        time.sleep(0.3)
    raise SystemExit("server 40 s ichida javob bermadi")


# ---------------------------------------------------------------- brauzer
async def launch(p):
    try:
        return await p.chromium.launch(channel="msedge")
    except Exception:
        return await p.chromium.launch(channel="chrome")


class Sess:
    def __init__(self, ctx, page, errors):
        self.ctx, self.page, self.errors = ctx, page, errors


async def session(browser, role: str | None, vp: dict, hour: int | None = None, manzara: str | None = None,
                  reduced: bool = False) -> Sess:
    mobile = vp["width"] < 600
    ctx = await browser.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile,
                                    has_touch=mobile, locale="uz-UZ", reduced_motion="reduce" if reduced else "no-preference")
    await ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    if hour is not None:  # soxta soat (NUQTA kun/tun)
        await ctx.add_init_script(script=FAKE_DATE + f"window.__setHour({hour});")
    if manzara:  # keyingi ochilish shu manzaradan keyingisi bo'ladi (faqat birinchi ochilishda yoziladi)
        await ctx.add_init_script(script="try{if(!sessionStorage.getItem('__nq')){localStorage.setItem('nuqta.staff.manzara',"
                                         + json.dumps(manzara) + ");sessionStorage.setItem('__nq','1')}}catch(e){}")
    if role:
        user = XODIM[role]
        mock = {"initData": make(SINOV_XODIM_TOKEN, user), "user": user, "version": "8.0", "platform": "android",
                "colorScheme": "light"}
        await ctx.add_init_script(script="window.__TG_MOCK = " + json.dumps(mock, ensure_ascii=False) + ";")
        await ctx.add_init_script(path=str(MOCK))

    async def block(route):
        await route.fulfill(status=200, content_type="text/javascript", body="/* sinov: telegram.org bloklangan */")

    await ctx.route("**/telegram.org/**", block)
    page = await ctx.new_page()
    errors: list[str] = []

    def on_console(m):
        if m.type != "error":
            return
        url = m.location.get("url", "") if m.location else ""
        # kutilgan API javoblari (begona 403, ataylab noto'g'ri so'rovlar) - brauzer tarmoq yozuvi, JS xatosi emas
        if m.text.startswith("Failed to load resource: the server responded with a status of 4") and "/api/x/" in url:
            return
        errors.append(f"console.{m.type}: {m.text} @ {url}")

    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    return Sess(ctx, page, errors)


async def no_overflow(page) -> tuple[bool, str]:
    sw, iw = await page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    return sw <= iw, f"scrollWidth {sw} > {iw}"


async def shot(page, name: str, full: bool = True) -> None:
    await page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)


async def calls(page) -> list:
    return await page.evaluate("(window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.__calls) || []")


async def open_home(s: Sess) -> None:
    await s.page.goto(BASE + "/staff/")
    await s.page.wait_for_selector("#page, .gate .gate-card h1", timeout=15000)


async def goto_tab(s: Sess, tab: str, mobile: bool) -> None:
    sel = (".tabbar" if mobile else ".snav") + f' [data-tab="{tab}"]'
    await s.page.click(sel)
    await s.page.wait_for_function(
        "(t) => { const b = document.getElementById('body'); return b && !b.querySelector('.sk') && !b.classList.contains('busy'); }",
        arg=tab, timeout=15000)
    await s.page.wait_for_timeout(250)


async def api(page, method: str, path: str, body=None):
    return await page.evaluate(
        """async ([m, p, b]) => { const h = {'Content-Type': 'application/json', 'X-Init-Data': Telegram.WebApp.initData};
             const r = await fetch(p, {method: m, headers: h, body: b === null ? undefined : JSON.stringify(b)});
             let d = null; try { d = await r.json(); } catch (e) {} return {status: r.status, data: d}; }""",
        [method, path, body])


# ---------------------------------------------------------------- Ko'rinish kartasi (06.10)
MZ_NOMI = {"sahro": "Sahro", "voha": "Voha", "shahar": "Shahar", "qahva": "Qahva", "xattot": "Xattot", "shom": "Shom"}


async def check_korinish(s: Sess, tag: str, mobile: bool) -> None:
    """Bugun: Ko'rinish kartasi /api/x/stats korinish bilan mos - 6 manzara (rasm bilan), tanlov, kun/tun, 24 soat grafigi
    (tungi soatlar fonda), tooltip, xulosa gapi, Jadval <-> Grafik; eski "Uslub tanlovi" yo'q."""
    p = s.page
    r = await api(p, "GET", "/api/x/stats")
    k = (r["data"] or {}).get("korinish") or {}
    check(r["status"] == 200 and k.get("days") == 14 and len(k.get("manzara", [])) == 6 and len(k.get("soat", [])) == 24,
          f"{tag}: /api/x/stats da korinish (14 kun, 6 manzara, 24 soat)", str(sorted(k)))
    body = await p.text_content("#body")
    check(await p.locator(".korc").count() == 1 and "Uslub tanlovi" not in body and "O'yinli" not in body and "Shisha" not in body,
          f"{tag}: Ko'rinish kartasi bor, eski 'Uslub tanlovi' (O'yinli/Shisha) yo'q")
    items = await p.locator(".korc .mzl li .nm b").all_text_contents()
    keys = await p.eval_on_selector_all(".korc .mzl .th", "els => els.map(e => e.dataset.v)")
    check(items == [m["label"] for m in k["manzara"]] and keys == [m["key"] for m in k["manzara"]],
          f"{tag}: Ko'rinish - 6 manzara server tartibida (eng ko'p ochilgani birinchi)", f"{items} {keys}")
    svgs = await p.locator(".korc .mzl .th svg[aria-hidden='true']").count()
    check(svgs == 6, f"{tag}: Ko'rinish - har manzara o'z rasmi bilan (6 ta kichik manzara)", str(svgs))
    tg_n = await p.locator(".korc .mzl .nm small").all_text_contents()
    check(all((f"{m['tanlagan']} kishi tanlagan" in t) if m["tanlagan"] else ("tanlaganlar yo'q" in t) for m, t in zip(k["manzara"], tg_n)),
          f"{tag}: Ko'rinish - 'N kishi tanlagan'", str(tg_n))
    dv = await p.locator(".korc .duo .dv").all_text_contents()
    tn, mv = k["tanlov"], k["mavzu"]
    tl, ml = tn["tanlangan"] + tn["aylan"], mv["kun"] + mv["tun"]
    jsr = lambda a, b: math.floor(a / b * 100 + 0.5) if b else 0  # noqa: E731 - JS Math.round(a / b * 100)
    want = [f"{jsr(tn['tanlangan'], tl)}%{tn['tanlangan']} o'quvchi", f"{jsr(tn['aylan'], tl)}%{tn['aylan']} o'quvchi",
            f"{jsr(mv['kun'], ml)}%{mv['kun']} ochilish", f"{jsr(mv['tun'], ml)}%{mv['tun']} ochilish"]
    check(dv == want, f"{tag}: Ko'rinish - o'zi tanlagan / almashadi, kunduzgi / tungi", f"{dv} != {want}")
    take = await p.text_content(".korc p.take")
    check(bool(take) and k["manzara"][0]["label"] in take and "tungi soatlarda" in take and "eng qizg'in soat" in take
          and take.count(".") == 1, f"{tag}: Ko'rinish - bitta gaplik xulosa", str(take))
    hours = [x["opens"] for x in k["soat"]]
    pk = hours.index(max(hours))
    check(await p.locator("#korChart .hit").count() == 24 and await p.locator("#korChart .band").count() == 2
          and await p.locator("#korChart .vl").text_content() == str(hours[pk]),
          f"{tag}: soatlar grafigi - 24 ustun, tungi soatlar fonda, eng ko'p ochilish yozilgan")
    hit = p.locator("#korChart .hit").nth(pk)
    await hit.scroll_into_view_if_needed()
    box = await hit.bounding_box()
    if box:
        if mobile:
            await p.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        else:
            await p.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        await p.wait_for_timeout(150)
    tip = await p.locator("#korChart .tip").text_content()
    want_tip = f"{hours[pk]} ochilish{pk:02d}:00–{pk:02d}:59{'tungi' if pk >= 19 or pk < 6 else 'kunduzgi'} soat"
    check(tip == want_tip and await p.locator("#korChart .tip").is_visible(), f"{tag}: soatlar grafigi tooltip", f"{tip!r} != {want_tip!r}")
    if mobile and tag.startswith("ceo"):
        await shot(p, f"{tag}_korinish_tooltip", full=False)
    # Jadval <-> Grafik
    btn = p.locator('[data-act="korTbl"]')
    await btn.click()
    rows = await p.locator("#korSoat tbody tr").all()
    vals = [int((await r.locator("td.r").text_content()).replace(" ", "")) for r in rows]
    pressed = await p.locator('[data-act="korTbl"]').get_attribute("aria-pressed")
    focused = await p.evaluate("document.activeElement && document.activeElement.dataset.act")
    check(vals == hours and pressed == "true" and await p.locator("#korChart").count() == 0 and focused == "korTbl",
          f"{tag}: 'Jadval' - 24 soat jadvali (grafik o'rnida), fokus tugmada", f"{vals} pressed={pressed} focus={focused}")
    if tag in ("ceo_mobil", "ceo_desktop"):
        await p.locator(".korc").scroll_into_view_if_needed()
        await shot(p, f"{tag}_korinish_jadval", full=False)
    await p.locator('[data-act="korTbl"]').click()
    check(await p.locator("#korChart .hit").count() == 24 and await p.locator('[data-act="korTbl"]').get_attribute("aria-pressed") == "false",
          f"{tag}: 'Grafik' - soatlar grafigi qaytdi")


def plain_headers(resp) -> dict:
    return {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length", "content-encoding", "content-type")}


async def test_old_api(browser) -> None:
    """Eski server (ishchi server qayta ishga tushmaguncha): stats da korinish, students da manzara/mavzu yo'q -
    karta va chiplar ko'rinmaydi, xato yo'q. Bo'sh davr: karta 'hali yo'q' holati bilan."""
    for mode in ("eski", "bosh"):
        for vp, vn in ((MOBILE, "mobil"), (DESKTOP, "desktop")):
            s = await session(browser, "ustoz", vp, hour=11)
            p = s.page

            def stats_handler(mode):  # Playwright 2 argumentli funksiyaga (route, request) beradi - shuning uchun yopilma
                async def stats(route):
                    await patch_stats(route, mode)
                return stats

            async def patch_stats(route, mode):
                resp = await route.fetch()
                d = await resp.json()
                if mode == "eski":
                    d.pop("korinish", None)
                else:  # yangi o'rnatish: hali hech kim ochmagan
                    k = d["korinish"]
                    k.update(users=0, since=None, tanlov={"aylan": 0, "tanlangan": 0}, mavzu={"kun": 0, "tun": 0},
                             soat=[{"hour": h, "opens": 0} for h in range(24)])
                    for m in k["manzara"]:
                        m.update(users=0, sessions=0, tanlagan=0)
                await route.fulfill(status=resp.status, headers=plain_headers(resp), json=d)

            async def students(route):
                resp = await route.fetch()
                d = await resp.json()
                for x in d.get("students", []):
                    x.pop("manzara", None)
                    x.pop("mavzu", None)
                await route.fulfill(status=resp.status, headers=plain_headers(resp), json=d)

            await p.route("**/api/x/stats*", stats_handler(mode))
            if mode == "eski":
                await p.route("**/api/x/students*", students)
            await open_home(s)
            await open_tab(s, "bugun", vp["width"] < 600)
            tag = f"{'eski API' if mode == 'eski' else 'bo`sh korinish'} ({vn})"
            n = await p.locator(".kpis .kpi").count()
            bars = await p.locator("#actChart svg .bar").count()
            if mode == "eski":
                check(await p.locator(".korc").count() == 0 and n == 6 and bars > 0 and await p.locator(".feed .li").count() > 0,
                      f"{tag}: Ko'rinish kartasi yashirin, qolgan Bugun to'liq", f"korc={await p.locator('.korc').count()} kpi={n} bars={bars}")
            else:
                t = await p.text_content(".korc") if await p.locator(".korc").count() else ""
                check("Ko'rinish ma'lumoti hali yo'q" in t and await p.locator(".korc .mzl, #korChart").count() == 0 and n == 6,
                      f"{tag}: Ko'rinish kartasi bo'sh holatda ('hali yo'q')", t[:120])
            ok, d = await no_overflow(p)
            check(ok, f"{tag}: gorizontal siljish yo'q", d)
            await p.locator(".korc" if mode == "bosh" else "#actChart").scroll_into_view_if_needed()
            await shot(p, f"korinish_{'eski_api' if mode == 'eski' else 'bosh'}_{vn}", full=False)
            if mode == "eski":
                await goto_tab(s, "oquvchilar", vp["width"] < 600)
                rows = await p.locator(".stu").count()
                check(rows >= 10 and await p.locator(".stu .chipu").count() == 0, f"{tag}: O'quvchilar - chipsiz, ro'yxat to'liq", str(rows))
            check(not s.errors, f"{tag}: konsol xatolari yo'q", "; ".join(s.errors[:3]))
            await s.ctx.close()


# ---------------------------------------------------------------- uy sahifasi
async def test_home(browser, role: str, vp: dict, tag: str) -> None:
    mobile = vp["width"] < 600
    s = await session(browser, role, vp)
    p = s.page
    await open_home(s)
    if role == "begona":
        h = await p.text_content(".gate-card h1")
        check(h and "Ruxsat yo'q" in h, f"{tag}: begona -> 'Ruxsat yo'q' ekrani", str(h))
        t = await p.text_content(".gate-card")
        check("taklif havolasini" in (t or ""), f"{tag}: begona -> taklif havolasi haqida matn")
        ok, d = await no_overflow(p)
        check(ok, f"{tag}: gorizontal siljish yo'q", d)
        await shot(p, f"{tag}_ruxsat_yoq", full=False)
        check(not s.errors, f"{tag}: konsol xatolari yo'q", "; ".join(s.errors[:3]))
        await s.ctx.close()
        return

    c = await calls(p)
    names = [x[0] for x in c]
    check("ready" in names and "expand" in names, f"{tag}: tg.ready() + expand()")
    # 05.10 NUQTA: Telegram sarlavha/fon rangi = joriy manzaraning --bg tokeni (eski NOON #EAF4EA emas)
    bg = await p.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()")
    check(bg.startswith("#") and bg.upper() != "#EAF4EA" and ["setHeaderColor", bg] in c and ["setBackgroundColor", bg] in c,
          f"{tag}: Telegram ranglari = manzara foni ({bg})", str([x for x in c if x[0].startswith("set")]))
    brand = await p.text_content(".top .brand b" if mobile else ".side .brand b")
    check(brand == "Muhammadamin", f"{tag}: brend 'Muhammadamin'", str(brand))
    sub = await p.text_content(".top .brand small" if mobile else ".side .brand small")
    check(sub == "Boshqaruv", f"{tag}: brend osti 'Boshqaruv'", str(sub))
    store = await p.evaluate("JSON.parse(sessionStorage.getItem('noon_x') || 'null')")
    check(bool(store and store.get("token") and store.get("panels")), f"{tag}: sessionStorage noon_x (token + panels)")
    keys = [x["key"] for x in (store or {}).get("panels", [])]
    check(keys == ROLE_PANELS[role], f"{tag}: panellar ro'yxati rolga mos", str(keys))

    tabs = await p.eval_on_selector_all((".tabbar" if mobile else ".snav") + " [data-tab]", "els => els.map(e => e.dataset.tab)")
    want = ["bugun", "kurs", "oquvchilar", "panellar"] + (["xodimlar"] if role == "ceo" else [])
    check(tabs == want, f"{tag}: bo'limlar {want}", str(tabs))

    for t in tabs:
        await goto_tab(s, t, mobile)
        ok, d = await no_overflow(p)
        check(ok, f"{tag}: '{t}' gorizontal siljish yo'q", d)
        await shot(p, f"{tag}_{t}")
        if t == "bugun":
            n = await p.locator(".kpis .kpi").count()
            check(n == 6 and await p.locator(".kpis .hero").count() == 1, f"{tag}: 6 KPI + 'Bugun faol' to'q karta", str(n))
            check(await p.locator("#actChart svg .bar").count() > 0, f"{tag}: 14 kunlik grafik chizildi")
            # tooltip
            await p.locator("#actChart").scroll_into_view_if_needed()
            box = await p.locator("#actChart .hit").last.bounding_box()
            if box:
                if mobile:
                    await p.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                else:
                    await p.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                await p.wait_for_timeout(150)
                tip = await p.locator("#actChart .tip").text_content()
                vis = await p.locator("#actChart .tip").is_visible()
                check(bool(tip) and "bugun" in tip and vis, f"{tag}: grafik tooltip (bugun)", f"{tip!r} visible={vis} box={box}")
                await shot(p, f"{tag}_bugun_tooltip", full=False) if mobile else None
            await p.click("details.dt summary")
            rows = await p.locator("details.dt tbody tr").count()
            check(rows == 14, f"{tag}: jadval ko'rinishi 14 qator", str(rows))
            await p.click('[data-act="series"][data-v="xp"]')
            check(await p.locator("#actChart svg .bar").count() > 0, f"{tag}: 'Ball' seriyasi")
            await p.click('[data-act="series"][data-v="active"]')
            # 06.10 (egasi, "1 ha"): "Uslub tanlovi" o'rniga Ko'rinish kartasi - barcha 4 rolda
            await check_korinish(s, tag, mobile)
            feed = await p.locator(".feed .li").count()
            check(feed > 0, f"{tag}: so'nggi faollik ro'yxati", str(feed))
        if t == "kurs":
            parts = await p.locator(".parts > section").count()
            check(parts == 4, f"{tag}: 4 qism", str(parts))
            les = await p.locator(".les").count()
            check(les == 36, f"{tag}: 36 dars qatori", str(les))
            has_step = await p.locator(".stepper").count()
            if role in ("assistent", "ustoz"):  # 03.10 (SPEC 10.1): ustoz ham ochiq darslarni o'zgartira olmaydi
                check(has_step == 0 and await p.locator("#ocSave").count() == 0, f"{tag}: {role}da stepper/Saqlash yo'q")
                r = await api(p, "POST", "/api/x/open", {"n": 5})
                check(r["status"] == 403, f"{tag}: {role} /api/x/open -> 403", str(r))
            else:
                check(has_step == 1, f"{tag}: stepper bor")
                if not mobile:
                    continue
                before = int(await p.text_content("#ocVal"))
                up = before <= 34
                a, b2 = ('ocInc', 'ocDec') if up else ('ocDec', 'ocInc')
                target = before + 2 if up else before - 2
                check(await p.locator('#ocSave').is_disabled(), f"{tag}: o'zgarishsiz 'Saqlash' o'chiq")
                await p.click(f'[data-act="{a}"]')
                await p.click(f'[data-act="{a}"]')
                v = int(await p.text_content("#ocVal"))
                check(v == target, f"{tag}: stepper {before} -> {target}", str(v))
                note = await p.text_content("#ocNote")
                check(("ochiladi" if up else "yopiladi") in (note or ""), f"{tag}: o'zgarish izohi", str(note))
                await shot(p, f"{tag}_kurs_stepper", full=False)
                await p.click("#ocSave")
                await p.wait_for_selector(".toast", timeout=5000)
                toast = await p.text_content(".toast")
                check("Saqlandi" in (toast or ""), f"{tag}: Saqlash toast", str(toast))
                r = await api(p, "GET", "/api/x/course")
                check(r["data"]["open"] == target, f"{tag}: server open = {target}", str(r["data"]["open"]))
                locked = await p.locator(".les.locked").count()
                check(locked == 36 - target, f"{tag}: {36 - target} ta dars 'Yopiq'", str(locked))
                await shot(p, f"{tag}_kurs_saqlandi", full=False)
                # qaytarish
                await p.click(f'[data-act="{b2}"]')
                await p.click(f'[data-act="{b2}"]')
                await p.click("#ocSave")
                await p.wait_for_function(f"() => document.getElementById('ocVal') && document.getElementById('ocVal').textContent === '{before}' && !document.getElementById('ocReset')?.offsetParent", timeout=5000)
                r = await api(p, "GET", "/api/x/course")
                check(r["data"]["open"] == before, f"{tag}: qaytarildi open = {before}", str(r["data"]["open"]))
        if t == "oquvchilar":
            n = await p.locator(".stu").count()
            check(n >= 10, f"{tag}: o'quvchilar ro'yxati", str(n))
            await p.fill("#stuQ", "aziza")
            await p.wait_for_function("() => document.querySelectorAll('.stu').length === 1", timeout=5000)
            nm = await p.text_content(".stu .stu-n b")
            check("Aziza" in (nm or ""), f"{tag}: qidiruv 'aziza'", str(nm))
            # 06.10: uslub chipi (O'yinli/Shisha) o'rniga oxirgi ko'rinish - manzara + kun/tun (API dagi bilan bir xil)
            az = ((await api(p, "GET", "/api/x/students?q=aziza"))["data"] or {}).get("students", [{}])[0]
            chip = await p.locator(".stu .chipu").all_text_contents()
            want_mz = MZ_NOMI.get(az.get("manzara"))
            want_md = {"kun": "kunduzgi", "tun": "tungi"}.get(az.get("mavzu"))
            check(want_mz and len(chip) == 1 and chip[0].startswith(want_mz) and (want_md or "") in chip[0]
                  and await p.locator(f'.stu .chipu .mzd[data-v="{az.get("manzara")}"]').count() == 1
                  and await p.locator(".stu .chipu use[href$='#" + ("moon" if az.get("mavzu") == "tun" else "sun") + "']").count() == 1,
                  f"{tag}: Aziza - oxirgi manzara chipi ({want_mz}, {want_md})", f"{chip} {az.get('manzara')} {az.get('mavzu')}")
            await p.fill("#stuQ", "")
            await p.wait_for_function("() => document.querySelectorAll('.stu').length > 1", timeout=5000)
            rows = ((await api(p, "GET", "/api/x/students?q="))["data"] or {}).get("students", [])
            n_mz = sum(1 for x in rows[:150] if x.get("manzara") in MZ_NOMI)
            chips = await p.locator(".stu .chipu").count()
            txt_all = await p.text_content("#stuList")
            check(0 < n_mz < len(rows[:150]) and chips == n_mz and "O'yinli" not in txt_all and "Shisha" not in txt_all
                  and "Tanlanmagan" not in txt_all,
                  f"{tag}: chip faqat manzarasi ma'lum o'quvchilarda ({chips}/{len(rows[:150])}), eski uslub chiplari yo'q",
                  f"chips={chips} n_mz={n_mz}")
            await p.click('[data-act="seg"][data-v="idle"]')
            await p.wait_for_timeout(100)
            await p.click('[data-act="seg"][data-v="all"]')
        if t == "panellar":
            cards = await p.eval_on_selector_all(".pcard", "els => els.map(e => e.getAttribute('href'))")
            check(len(cards) == len(ROLE_PANELS[role]) and all(c.startswith("/staff/p/") and "t=" in c for c in cards),
                  f"{tag}: panel kartalari ({len(cards)})", str(cards))
            sub = await p.locator(".pcard .p-sub").first.text_content()
            check(sub == "Dizayn namunasi · demo ma'lumotlar", f"{tag}: kartada 'Dizayn namunasi · demo ma'lumotlar'", str(sub))
        if t == "xodimlar":
            rows = await p.locator(".srow").count()
            check(rows == 4, f"{tag}: 4 xodim", str(rows))
            self_btn = await p.locator(".srow:has(.you) [data-act='rm']").count()
            check(self_btn == 0, f"{tag}: o'zini chiqarish tugmasi yo'q")
            if mobile:
                await p.click('[data-act="invRole"][data-v="admin"]')
                await p.click("#invMake")
                await p.wait_for_selector("#invLink", timeout=5000)
                link = await p.text_content("#invLink")
                check(bool(link) and link.startswith("https://t.me/noon_xodim_sinov_bot?start=t_"), f"{tag}: taklif havolasi", str(link))
                await p.click('[data-act="invCopy"]')
                await p.wait_for_timeout(200)
                clip = await p.evaluate("navigator.clipboard.readText()")
                check(clip == link, f"{tag}: 'Nusxalash' buferga yozdi", str(clip))
                await p.click('[data-act="invShare"]')
                c = await calls(p)
                share = [x for x in c if x[0] == "openTelegramLink"]
                check(bool(share) and share[-1][1].startswith("https://t.me/share/url?url=https%3A%2F%2Ft.me%2Fnoon_xodim_sinov_bot"),
                      f"{tag}: 'Telegram orqali yuborish' -> openTelegramLink", str(share[-1:]))
                await shot(p, f"{tag}_xodimlar_taklif", full=False)
                r = await api(p, "POST", "/api/x/staff/remove", {"id": XODIM["ceo"]["id"]})
                check(r["status"] == 400, f"{tag}: o'zini chiqarish -> 400", str(r))
    check(not s.errors, f"{tag}: konsol xatolari yo'q", "; ".join(s.errors[:3]))
    await s.ctx.close()


async def test_direct_panel(browser) -> None:
    """noon_x yo'q (yangi seans): panel havolasi to'g'ridan-to'g'ri ochiladi - adapter tokendan rolni oladi."""
    req = urllib.request.Request(BASE + "/api/x/auth", data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json",
                                          "X-Init-Data": make(SINOV_XODIM_TOKEN, XODIM["ustoz"])})
    with urllib.request.urlopen(req, timeout=10) as r:
        a = json.loads(r.read().decode("utf-8"))
    lms = [x for x in a["panels"] if x["key"] == "lms"][0]["url"]
    s = await session(browser, "ustoz", MOBILE)
    p = s.page
    await p.goto(BASE + lms)
    await p.wait_for_function("() => document.documentElement.dataset.noonAdapter", timeout=15000)
    await p.wait_for_function("() => { const s = JSON.parse(sessionStorage.getItem('noon_x') || '{}'); return Array.isArray(s.panels); }", timeout=8000)
    await p.wait_for_timeout(300)
    opts = await p.evaluate("Array.from(document.querySelectorAll('#roleSel option')).map(o => o.textContent)")
    check(opts == ["Ustoz", "LMS"], "to'g'ridan-to'g'ri ochish: menyu serverdan tiklandi (Ustoz, LMS)", str(opts))
    vis = await p.evaluate("Array.from(document.querySelectorAll('#side .nav-group')).filter(g => !g.hidden).length")
    check(vis == 1, "to'g'ridan-to'g'ri ochish: LMS rejimi", str(vis))
    st = await p.evaluate("JSON.parse(sessionStorage.getItem('noon_x'))")
    check(bool(st.get("token")), "to'g'ridan-to'g'ri ochish: token sessionStorage da saqlandi")
    tkn = a["token"]
    await p.goto(BASE + "/staff/p/Admin_paneli.html?t=" + urllib.parse.quote(tkn, safe=""))
    check(p.url.rstrip("/").endswith("/staff"), "ustoz rejimsiz Admin paneli -> /staff/ ga qaytariladi", p.url)
    check(not s.errors, "to'g'ridan-to'g'ri ochish: konsol xatolari yo'q", "; ".join(s.errors[:3]))
    await s.ctx.close()


async def test_extras(browser) -> None:
    """Qo'shimcha: qism yig'ish/yoyish, grafikda klaviatura, range, ?tab= havolasi."""
    s = await session(browser, "admin", MOBILE)  # 03.10: ochiq darslar (range) - faqat CEO/admin
    p = s.page
    await p.goto(BASE + "/staff/?tab=kurs")
    await p.wait_for_selector("#page")
    await p.wait_for_function("() => { const b = document.getElementById('body'); return b && !b.querySelector('.sk'); }")
    cur = await p.evaluate("(document.querySelector('[data-tab][aria-current=\"page\"]') || {}).dataset.tab")
    check(cur == "kurs", "?tab=kurs -> Kurs bo'limi ochildi", str(cur))
    shut = await p.locator(".part.shut").count()
    check(shut == 3, "telefonda 3 qism yig'iq, 1 tasi ochiq", str(shut))
    first = p.locator(".part.shut .part-tg").first
    await first.click()
    check(await p.locator(".part.shut").count() == 2, "qismni yoyish (tugma)")
    exp = await p.locator(".part:not(.shut) .part-tg").first.get_attribute("aria-expanded")
    check(exp == "true", "aria-expanded = true")
    await p.evaluate("(() => { const r = document.getElementById('ocRange'); r.value = '20'; r.dispatchEvent(new Event('input', {bubbles: true})); })()")
    v = await p.text_content("#ocVal")
    check(v == "20", "range -> 20", str(v))
    check(await p.locator("#ocSave").is_enabled(), "range o'zgargach 'Saqlash' yoqiladi")
    await p.click("#ocReset")
    check(await p.text_content("#ocVal") == "36" and await p.locator("#ocSave").is_disabled(), "'Bekor qilish' qiymatni qaytardi")
    check(not s.errors, "qo'shimcha (mobil): konsol xatolari yo'q", "; ".join(s.errors[:3]))
    await s.ctx.close()
    s = await session(browser, "ceo", DESKTOP)
    p = s.page
    await open_home(s)
    await goto_tab(s, "bugun", False)
    await p.focus("#actChart svg")
    await p.keyboard.press("ArrowLeft")
    tip = await p.locator("#actChart .tip").text_content()
    check(bool(tip) and "bugun" not in tip and await p.locator("#actChart .tip").is_visible(), "grafik: klaviatura (chap strelka) -> kecha", str(tip))
    await p.keyboard.press("Home")
    tip0 = await p.locator("#actChart .tip").text_content()
    check(bool(tip0) and tip0 != tip, "grafik: Home -> birinchi kun", str(tip0))
    await shot(p, "ceo_desktop_bugun_klaviatura", full=False)
    await p.focus("#korChart svg")
    t1 = await p.locator("#korChart .tip").text_content()
    await p.keyboard.press("ArrowRight")
    t2 = await p.locator("#korChart .tip").text_content()
    await p.keyboard.press("Home")
    t3 = await p.locator("#korChart .tip").text_content()
    check(bool(t1) and "ochilish" in t1 and t2 != t1 and t3 and "00:00–00:59" in t3 and await p.locator("#korChart .tip").is_visible(),
          "soatlar grafigi: klaviatura (fokus - eng qizg'in soat, strelka, Home -> 00:00)", f"{t1!r} {t2!r} {t3!r}")
    # avval O'quvchilar (u /course ni keshlaydi), keyin Kurs: kurs.json va test jami baribir yuklanishi kerak
    await goto_tab(s, "oquvchilar", False)
    await goto_tab(s, "kurs", False)
    crumb = await p.text_content(".crumb")
    jami_slayd = str(json.loads((ROOT / "web" / "content" / "kurs.json").read_text(encoding="utf-8"))["jami_slayd"])
    check(jami_slayd in (crumb or ""), "Kurs sarlavhasida slaydlar soni (O'quvchilar dan keyin ham)", str(crumb))
    avg8 = await p.evaluate("(() => { const r = Array.from(document.querySelectorAll('.les')).find(x => x.querySelector('.les-n').textContent === '8'); return r ? r.querySelector('.les-st span:last-child b').textContent : null; })()")
    check(bool(avg8) and avg8.endswith("/ 5"), "8-dars test o'rtachasi '/ 5' bilan", str(avg8))
    check(not s.errors, "qo'shimcha (desktop): konsol xatolari yo'q", "; ".join(s.errors[:3]))
    await s.ctx.close()


async def test_removal(browser) -> None:
    """CEO: Bekzod Aliyev (assistent) ni chiqarish - oxirida (boshqa sinovlardan keyin)."""
    victim = await session(browser, "assistent", MOBILE)  # chiqarilayotgan paytda ilovasi ochiq
    await open_home(victim)
    await goto_tab(victim, "kurs", True)
    s = await session(browser, "ceo", MOBILE)
    p = s.page
    await open_home(s)
    await goto_tab(s, "xodimlar", True)
    await p.click(f"[data-act='rm'][data-id='{XODIM['assistent']['id']}']")
    await p.wait_for_selector(".sheet", timeout=3000)
    await p.wait_for_timeout(450)  # kirish animatsiyasi tugashi uchun
    c = await calls(p)
    check(["BackButton.show"] in c, "chiqarish: oynada BackButton ko'rinadi")
    await shot(p, "ceo_mobil_xodimlar_chiqarish_oyna", full=False)
    await p.evaluate("Telegram.WebApp.__emit('backButtonClicked')")
    check(await p.locator(".sheet").count() == 0, "chiqarish: BackButton oynani yopdi")
    await p.click(f"[data-act='rm'][data-id='{XODIM['assistent']['id']}']")
    await p.click("[data-act='rmYes']")
    await p.wait_for_selector(".toast", timeout=5000)
    await p.wait_for_function("() => document.querySelectorAll('.srow').length === 3", timeout=5000)
    check(await p.locator(".srow").count() == 3, "chiqarish: Bekzod Aliyev ro'yxatdan chiqdi")
    await shot(p, "ceo_mobil_xodimlar_keyin", full=False)
    check(not s.errors, "chiqarish: konsol xatolari yo'q", "; ".join(s.errors[:3]))
    await s.ctx.close()
    # ochiq turgan ilovada yangilash -> kirish qayta tekshiriladi -> "Ruxsat yo'q"
    await victim.page.click('[data-act="refresh"]')
    await victim.page.wait_for_selector(".gate .gate-card h1", timeout=10000)
    h = await victim.page.text_content(".gate-card h1")
    check(h and "Ruxsat yo'q" in h, "ochiq ilovada chiqarilgan assistent -> 'Ruxsat yo'q'", str(h))
    check(not victim.errors, "chiqarilgan assistent: konsol xatolari yo'q", "; ".join(victim.errors[:3]))
    await victim.ctx.close()
    # chiqarilgan assistent endi kira olmaydi
    s = await session(browser, "assistent", MOBILE)
    await open_home(s)
    h = await s.page.text_content(".gate-card h1")
    check(h and "Ruxsat yo'q" in h, "chiqarilgan assistent -> 'Ruxsat yo'q'", str(h))
    await s.ctx.close()


async def test_no_telegram(browser) -> None:
    s = await session(browser, None, MOBILE)
    await s.page.goto(BASE + "/staff/")
    await s.page.wait_for_selector(".gate .gate-card h1", timeout=10000)
    h = await s.page.text_content(".gate-card h1")
    check(h == "Telegram orqali oching", "Telegramsiz brauzer -> 'Telegram orqali oching'", str(h))
    await shot(s.page, "brauzer_telegramsiz", full=False)
    await s.page.goto(BASE + "/staff/p/CEO_paneli.html")
    check(s.page.url.rstrip("/").endswith("/staff"), "tokensiz panel -> /staff/ ga qaytaradi", s.page.url)
    await s.ctx.close()


# ---------------------------------------------------------------- NUQTA UI (05.10)
NUQTA_JS = r"""
(isPhone) => {
  const out = {};
  const de = document.documentElement;
  out.overflow = Math.max(de.scrollWidth, document.body.scrollWidth) - window.innerWidth;
  out.icons = Array.from(document.querySelectorAll('use')).map(u => (u.getAttribute('href') || '').split('#')[1] || '');
  out.text = document.body.innerText;
  const vis = (el) => { const r = el.getBoundingClientRect(); if (!r.width || !r.height) return false; for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e); if (s.display === 'none' || s.visibility === 'hidden') return false; } return true; };
  const AR = /[؀-ۿݐ-ݿࡰ-ࣿﭐ-﷿ﹰ-﻿]/;
  const bad = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = tw.nextNode())) {
    if (!AR.test(n.nodeValue)) continue;
    const el = n.parentElement;
    if (el && el.closest('script,style,[data-scene],svg')) continue;
    const c = el && el.closest('[dir="rtl"][lang="ar"]');
    if (!c) bad.push(n.nodeValue.trim().slice(0, 40));
    else if (!/Sakkal Majalla/.test(getComputedStyle(c).fontFamily)) bad.push('shrift: ' + getComputedStyle(c).fontFamily.slice(0, 40));
  }
  out.arabic = bad;
  out.small = [];
  if (isPhone) {
    document.querySelectorAll('button, .btn, a, input, summary, .tab, .qt, .sb, .ib').forEach(el => {
      if (!vis(el) || el.matches('.search input')) return;
      if (el.closest('.tbl-wrap')) return;
      const r = el.getBoundingClientRect();
      if (r.height < 43.5 || r.width < 30) out.small.push((el.className || el.tagName) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height) + ' "' + (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 24) + '"');
    });
  }
  const rgb = (s) => {
    const c = (s || '').match(/color\(srgb ([^)]+)\)/);
    if (c) { const p = c[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1]; }
    const m = (s || '').match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const mix = (top, bot) => { const a = top[3]; return [top[0] * a + bot[0] * (1 - a), top[1] * a + bot[1] * (1 - a), top[2] * a + bot[2] * (1 - a), 1]; };
  function bgOf(el) {
    const pb = getComputedStyle(el, '::before');   // romb belgi (.les-n, .li-ic): matn ::before ustida
    if (pb.content !== 'none' && pb.position === 'absolute') { const c = rgb(pb.backgroundColor); if (c && c[3] >= 1) return c; }
    const stack = [];
    for (let e = el; e; e = e.parentElement) {
      const st = getComputedStyle(e);
      let c = rgb(st.backgroundColor);
      if ((!c || c[3] === 0) && /gradient/.test(st.backgroundImage) && e.matches('.tint')) {  // shom: --hero gradient - och uchi
        const m = st.backgroundImage.match(/rgba?\([^)]+\)/g); if (m) { const cs = m.map(rgb); c = cs.sort((a, b) => lum(b) - lum(a))[cs.length - 1]; }
      }
      if (c && c[3] > 0) { stack.push(c); if (c[3] >= 1) break; }
    }
    let base = rgb(getComputedStyle(document.body).backgroundColor) || [255, 255, 255, 1];
    for (let i = stack.length - 1; i >= 0; i--) base = stack[i][3] >= 1 ? stack[i] : mix(stack[i], base);
    return base;
  }
  const lowC = [];
  let nTxt = 0;
  document.querySelectorAll('body *').forEach((el) => {
    if (el.closest('svg,script,style,[aria-hidden="true"],.sr,[data-scene],noscript')) return;
    if (el.closest(':disabled,[aria-disabled="true"]')) return;
    const own = Array.from(el.childNodes).some((x) => x.nodeType === 3 && x.nodeValue.trim().length > 0);
    if (!own || !vis(el)) return;
    let op = 1; for (let e = el; e; e = e.parentElement) op *= +getComputedStyle(e).opacity;
    if (op < 0.99) return;
    const st = getComputedStyle(el), fg = rgb(st.color);
    if (!fg) return;
    const bg = bgOf(el), f = mix(fg, bg), L1 = lum(f), L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(st.fontSize), big = px >= 24 || (px >= 18.6 && +st.fontWeight >= 700);
    nTxt++;
    if (ratio < (big ? 3 : 4.5)) lowC.push(ratio.toFixed(2) + ' ' + el.tagName + '.' + (el.className || '') + ' "' + el.textContent.trim().slice(0, 24) + '"');
  });
  out.lowContrast = lowC.slice(0, 8);
  out.nText = nTxt;
  const badBg = [];
  document.querySelectorAll('*').forEach((el) => {
    const c = rgb(getComputedStyle(el).backgroundColor);
    if (!c || c[3] < 0.5) return;
    const [r, g, b] = c;
    const white = r > 245 && g > 245 && b > 245, black = r < 45 && g < 45 && b < 45, pink = r > 190 && b > 140 && g < r - 50 && b > g;
    if ((white || black || pink) && vis(el)) badBg.push((white ? 'oq ' : black ? 'qora ' : 'pushti ') + el.tagName + '.' + (el.className || '') + ' ' + getComputedStyle(el).backgroundColor);
  });
  out.badBg = badBg.slice(0, 6);
  out.font = getComputedStyle(document.body).fontFamily;
  out.scenes = Array.from(document.querySelectorAll('[data-scene]')).filter(vis).map(s => !!s.querySelector('svg[aria-hidden="true"]'));
  return out;
}
"""
ICONS: set[str] = set()
EMOJI = __import__("re").compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")


async def nq_check(page, label: str, phone: bool, errors: list, min_text: int = 10) -> dict:
    o = await page.evaluate(NUQTA_JS, phone)
    check(o["overflow"] <= 1, f"{label}: gorizontal siljish yo'q", str(o["overflow"]))
    check(not o["lowContrast"] and o["nText"] >= min_text, f"{label}: matn kontrasti >= 4,5:1 ({o['nText']} ta matn)", str(o["lowContrast"]))
    check(not o["badBg"], f"{label}: oq / qora / pushti fon yo'q", str(o["badBg"]))
    missing = sorted({i for i in o["icons"] if i not in ICONS})
    check(not missing, f"{label}: ikonlar faqat Lucide (icons.svg da bor)", str(missing))
    e = EMOJI.search(o["text"])
    check(not e, f"{label}: emoji yo'q", e and repr(o["text"][max(0, e.start() - 20):e.end() + 20]))
    check(not o["arabic"], f"{label}: arabcha matn <bdi dir=rtl lang=ar> ichida (Sakkal Majalla)", str(o["arabic"][:4]))
    check("Be Vietnam Pro" in o["font"], f"{label}: shrift Be Vietnam Pro", o["font"])
    if phone:
        check(not o["small"], f"{label}: bosiladigan joylar >= 44 px", str(o["small"][:6]))
    check(not errors, f"{label}: konsol xatolari yo'q", "; ".join(errors[:3]))
    errors.clear()
    return o


async def open_tab(s: Sess, tab: str, mobile: bool) -> None:
    cur = await s.page.evaluate("(document.querySelector('[data-tab][aria-current=\"page\"]') || {}).dataset?.tab || ''")
    if cur != tab:
        await goto_tab(s, tab, mobile)
    else:
        await s.page.wait_for_function("() => { const b = document.getElementById('body'); return b && !b.querySelector('.sk') && !b.classList.contains('busy'); }",
                                       timeout=15000)


async def test_nuqta(browser) -> None:
    """NUQTA UI: manzara aylanishi (o'z kaliti), kun/tun soatga qarab (ochiq turganda ham), Telegram ranglari,
    6 manzara x kun/tun, 390/1024 kenglik, kontrast, taqiqlangan fonlar, 44 px, fokus halqasi, harakat kamaytirilgan."""
    ICONS.update(__import__("re").findall(r'<symbol id="([a-z0-9-]+)"', (ROOT / "web" / "shared" / "icons.svg").read_text(encoding="utf-8")))
    # 1. har ochilganda keyingi manzara; talaba ilovasi / admin panel kalitlariga tegmaydi
    s = await session(browser, "admin", MOBILE, hour=10)
    p = s.page
    seen = []
    for i in range(7):
        if i:
            await p.reload(wait_until="domcontentloaded")
        else:
            await p.goto(BASE + "/staff/", wait_until="domcontentloaded")
        await p.wait_for_selector("#page", timeout=15000)
        seen.append(await p.evaluate("document.documentElement.dataset.v"))
    nxt = [NV[(NV.index(seen[i]) + 1) % 6] for i in range(6)] if all(v in NV for v in seen) else []
    check(seen[1:] == nxt and len(set(seen[:6])) == 6, "NUQTA: manzara har ochilganda keyingisi (6 ochilishda 6 xil)", str(seen))
    keys = await p.evaluate("[localStorage.getItem('nuqta.staff.manzara'), localStorage.getItem('nuqta.manzara'), localStorage.getItem('nuqta.admin.manzara')]")
    check(keys[0] == seen[-1] and keys[1] is None and keys[2] is None,
          "NUQTA: o'z kaliti nuqta.staff.manzara (talaba/admin aylanishiga ta'sir yo'q)", str(keys))
    check(await p.evaluate("document.documentElement.dataset.m") == "kun", "NUQTA: 10:00 -> kunduzgi")
    check(await p.locator(".brand .nq-sig").count() >= 1 and await p.locator(".logo").count() == 0, "NUQTA: belgi - uch romb nuqta (eski «ن» logotip yo'q)")
    # 2. ochiq turganda 19:00 -> tungi; fon, Telegram ranglari va manzara yangilanadi
    bg_kun = await p.evaluate("getComputedStyle(document.body).backgroundColor")
    sc_kun = await p.evaluate("(document.querySelector('.hero [data-scene]') || {}).innerHTML || ''")
    await p.evaluate("window.__setHour(19, 0); document.dispatchEvent(new Event('visibilitychange'))")
    await p.wait_for_function("() => document.documentElement.dataset.m === 'tun'", timeout=5000)
    await p.wait_for_timeout(700)
    bg_tun = await p.evaluate("getComputedStyle(document.body).backgroundColor")
    tok = await p.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()")
    c = await calls(p)
    sc_tun = await p.evaluate("(document.querySelector('.hero [data-scene]') || {}).innerHTML || ''")
    check(bg_tun != bg_kun and ["setHeaderColor", tok] in c and ["setBottomBarColor", tok] in c,
          "NUQTA: 19:00 da ochiq sahifa tungiga o'tdi (fon + Telegram sarlavha/pastki panel rangi)", f"{bg_kun} -> {bg_tun}, {tok}")
    meta = await p.evaluate("document.querySelector('meta[name=theme-color]').content")
    check(meta.upper() == tok.upper(), "NUQTA: <meta theme-color> = --bg", f"{meta} {tok}")
    check(sc_kun and sc_tun and sc_kun != sc_tun and "<circle" in sc_tun, "NUQTA: manzara tungi ko'rinishda qayta chizildi (oy)")
    await s.ctx.close()
    for hour, want in ((5, "tun"), (6, "kun"), (18, "kun"), (19, "tun"), (23, "tun")):
        s = await session(browser, "admin", MOBILE, hour=hour)
        await s.page.goto(BASE + "/staff/", wait_until="domcontentloaded")
        got = await s.page.evaluate("document.documentElement.dataset.m")
        check(got == want, f"NUQTA: soat {hour:02d}:00 -> {want}", str(got))
        await s.ctx.close()
    # 3. barcha bo'limlar: 390 (Telegram) va 1024, kunduzgi va tungi (CEO - 5 bo'lim)
    for vp, vn in ((MOBILE, "390"), ({"width": 1024, "height": 768}, "1024")):
        mobile = vp["width"] < 600
        for hour, m in ((11, "kun"), (22, "tun")):
            s = await session(browser, "ceo", vp, hour=hour, manzara="xattot")  # -> shom
            p = s.page
            await open_home(s)
            check(await p.evaluate("[document.documentElement.dataset.v, document.documentElement.dataset.m]") == ["shom", m],
                  f"NUQTA {vn}/{m}: shom/{m} ochildi")
            for t in TABS:
                await open_tab(s, t, mobile)
                o = await nq_check(p, f"NUQTA {vn}/shom/{m} {t}", mobile, s.errors)
                if t == "bugun":
                    check(o["scenes"] and all(o["scenes"]), f"NUQTA {vn}/{m}: manzara rasmi chizilgan (aria-hidden)", str(o["scenes"]))
                if t in ("bugun", "kurs") or (vn == "390" and t == "xodimlar"):
                    await shot(p, f"nuqta_{vn}_{m}_{t}", full=False)
            await s.ctx.close()
    # 4. 6 manzara x kun/tun: Bugun (telefon) + Kurs, O'quvchilar
    for v in NV:
        for hour, m in ((11, "kun"), (22, "tun")):
            s = await session(browser, "ceo", MOBILE, hour=hour, manzara=NV[(NV.index(v) - 1) % 6])
            p = s.page
            await open_home(s)
            got = await p.evaluate("[document.documentElement.dataset.v, document.documentElement.dataset.m]")
            check(got == [v, m], f"NUQTA: {v}/{m} ochildi", str(got))
            for t in ("bugun", "kurs", "oquvchilar"):
                await open_tab(s, t, True)
                await nq_check(p, f"NUQTA {v}/{m} {t}", True, s.errors)
            await s.ctx.close()
    # 5. kirish ekranlari (begona, Telegramsiz) kun/tun
    for role, nm in (("begona", "ruxsat yo'q"), (None, "Telegramsiz")):
        for hour, m in ((11, "kun"), (22, "tun")):
            s = await session(browser, role, MOBILE, hour=hour, manzara="sahro")  # -> voha
            await s.page.goto(BASE + "/staff/")
            await s.page.wait_for_selector(".gate .gate-card h1", timeout=10000)
            await s.page.wait_for_timeout(300)
            o = await nq_check(s.page, f"NUQTA: {nm} ekrani ({m})", True, s.errors, min_text=4)
            check(o["scenes"] and all(o["scenes"]), f"NUQTA: {nm} ekranida manzara ({m})", str(o["scenes"]))
            if m == "tun":
                await shot(s.page, f"nuqta_gate_{'begona' if role else 'brauzer'}_tun", full=False)
            await s.ctx.close()
    # 6. fokus halqasi (klaviatura) va harakat kamaytirilgan rejim
    s = await session(browser, "ceo", {"width": 1024, "height": 768}, hour=11, reduced=True)
    p = s.page
    await open_home(s)
    await p.wait_for_function("() => { const b = document.getElementById('body'); return b && !b.querySelector('.sk'); }", timeout=15000)
    rings = []
    for _ in range(4):
        await p.keyboard.press("Tab")
        rings.append(await p.evaluate("""(() => { const a = document.activeElement; const s = getComputedStyle(a);
            return [a.tagName + '.' + (a.className && a.className.baseVal === undefined ? a.className : ''), s.outlineStyle, parseFloat(s.outlineWidth)]; })()"""))
    check(all(r[1] == "solid" and r[2] >= 2 for r in rings), "NUQTA: Tab bilan fokus halqasi ko'rinadi (>= 2 px)", str(rings))
    tr = await p.evaluate("getComputedStyle(document.body).transitionDuration")
    check(all(float(x.strip().rstrip("s")) <= 0.001 for x in tr.split(",")), "NUQTA: prefers-reduced-motion -> o'tishlar o'chadi", tr)
    check(not s.errors, "NUQTA: fokus/harakat - konsol xatolari yo'q", "; ".join(s.errors[:3]))
    await s.ctx.close()


# ---------------------------------------------------------------- panellar
async def test_panels(browser, role: str, vp: dict, tag: str) -> None:
    mobile = vp["width"] < 600
    s = await session(browser, role, vp)
    p = s.page
    await open_home(s)
    store = await p.evaluate("JSON.parse(sessionStorage.getItem('noon_x'))")
    panels = store["panels"]
    for pn in panels:
        key = pn["key"]
        await goto_tab(s, "panellar", mobile)
        s.errors.clear()
        await p.click(f'.pcard[data-key="{key}"]')
        await p.wait_for_url("**/staff/p/**", timeout=15000)
        await p.wait_for_function("() => document.documentElement.dataset.noonAdapter", timeout=15000)
        await p.wait_for_timeout(500)
        ad = await p.evaluate("document.documentElement.dataset.noonAdapter")
        check(ad == key, f"{tag}/{key}: adapter ishladi", str(ad))
        q = await p.evaluate("location.search")
        check("t=" in q, f"{tag}/{key}: URL da ?t= token", q)
        opts = await p.evaluate("Array.from(document.querySelectorAll('#roleSel option')).map(o => [o.value, o.textContent, o.selected])")
        vals = [o[0] for o in opts]
        cur = await p.evaluate("JSON.parse(sessionStorage.getItem('noon_x'))")  # har kirishda token yangilanadi
        want = [x["url"] for x in cur["panels"]]
        check([x["key"] for x in cur["panels"]] == ROLE_PANELS[role] and vals == want,
              f"{tag}/{key}: rol menyusida faqat ruxsat etilgan panellar", str([o[1] for o in opts]))
        check(all(("t=" + cur["token"].replace("=", "%3D")) in v or ("t=" + cur["token"]) in v for v in vals),
              f"{tag}/{key}: menyu havolalarida joriy token")
        check(not any("Noon_ilova_demo" in v or "Rollar_demo" in v for v in vals), f"{tag}/{key}: demo/rollar havolalari olib tashlangan")
        sel = [o for o in opts if o[2]]
        mine = [x["url"] for x in cur["panels"] if x["key"] == key]
        check(bool(sel) and bool(mine) and sel[0][0] == mine[0], f"{tag}/{key}: joriy panel tanlangan", str(sel))
        hidden = await p.evaluate("(() => { const w = document.querySelector('.role-sw'); return !w || w.hidden || getComputedStyle(w).display === 'none'; })()")
        check(hidden == (len(panels) <= 1), f"{tag}/{key}: menyu {'yashirin (1 panel)' if len(panels) <= 1 else 'ko`rinadi'}", str(hidden))
        brand = await p.text_content("#side .brand b")
        check(brand == "Muhammadamin", f"{tag}/{key}: brend almashtirildi", str(brand))
        c = await calls(p)
        names = [x[0] for x in c]
        check("ready" in names and "expand" in names and "BackButton.show" in names, f"{tag}/{key}: ready/expand/BackButton.show")
        check(["setHeaderColor", "#EAF4EA"] in c, f"{tag}/{key}: header rangi #EAF4EA")
        if key == "lms":
            vis = await p.evaluate("Array.from(document.querySelectorAll('#side .nav-group')).filter(g => !g.hidden && getComputedStyle(g).display !== 'none').map(g => (g.querySelector('.ng-lab') || {}).textContent)")
            check(vis == ["LMS"], f"{tag}/{key}: faqat LMS guruhi ko'rinadi", str(vis))
            small = await p.text_content("#side .brand small")
            check(small == "LMS paneli", f"{tag}/{key}: brend osti 'LMS paneli'", str(small))
            cur = await p.evaluate("Panel.current")
            check(cur == LMS_IDS[0], f"{tag}/{key}: birinchi LMS ekrani ochildi", str(cur))
            await p.evaluate("Panel.go('pay')")
            cur2 = await p.evaluate("Panel.current")
            check(cur2 in LMS_IDS, f"{tag}/{key}: LMS dan tashqari ekran yopiq (pay)", str(cur2))
            await p.evaluate("Panel.go('bank')")
            check(await p.evaluate("Panel.current") == "bank", f"{tag}/{key}: LMS ichida o'tish (bank)")
        if key == "assistent":
            msw = await p.evaluate("(() => { const m = document.querySelector('.mode-sw'); return !m || m.hidden || getComputedStyle(m).display === 'none'; })()")
            check(msw, f"{tag}/{key}: Ustoz/Assistent almashtirgich yashirin")
            cur = await p.evaluate("Panel.current")
            check(cur.startswith("a-"), f"{tag}/{key}: assistent rejimi ochiq", str(cur))
            await p.evaluate("Panel.go('home')")
            check(await p.evaluate("Panel.current") == "a-home", f"{tag}/{key}: ustoz ekrani -> assistent ekraniga")
            await p.evaluate("Panel.go('live')")
            check((await p.evaluate("Panel.current")).startswith("a-"), f"{tag}/{key}: 'live' (faqat ustoz) yopiq")
            await p.evaluate("location.hash = '#grades'")
            await p.wait_for_timeout(200)
            check((await p.evaluate("Panel.current")).startswith("a-"), f"{tag}/{key}: #grades hash orqali ham yopiq")
        if key == "ustoz":
            msw = await p.evaluate("(() => { const m = document.querySelector('.mode-sw'); return !!m && !m.hidden && getComputedStyle(m).display !== 'none'; })()")
            check(msw, f"{tag}/{key}: ustozda rejim almashtirgich bor")
        ok, d = await no_overflow(p)
        check(ok, f"{tag}/{key}: gorizontal siljish yo'q", d)
        await shot(p, f"{tag}_panel_{key}", full=False)
        if mobile:
            # yon menyu: "Boshqaruvga qaytish" + "Chiqish"
            await p.click("[data-menu]")
            await p.wait_for_timeout(300)
            await shot(p, f"{tag}_panel_{key}_menyu", full=False)
            back = await p.locator("[data-noon-back]").count()
            check(back == 1, f"{tag}/{key}: 'Boshqaruvga qaytish' menyuda")
            await p.click(".side-foot .nav-item:not([data-noon-back])")
            c = await calls(p)
            check(["close"] in c, f"{tag}/{key}: 'Chiqish' -> tg.close()")
            toast = await p.locator(".toast").count()
            check(toast == 0, f"{tag}/{key}: 'Chiqish' demo toast chiqarmadi")
        check(not s.errors, f"{tag}/{key}: konsol xatolari yo'q", "; ".join(s.errors[:3]))
        # BackButton -> /staff/
        await p.evaluate("Telegram.WebApp.__emit('backButtonClicked')")
        await p.wait_for_url(BASE + "/staff/", timeout=10000)
        await p.wait_for_selector("#page", timeout=10000)
        cur_tab = await p.evaluate("(document.querySelector('[data-tab][aria-current=\"page\"]') || {}).dataset.tab")
        check(cur_tab == "panellar", f"{tag}/{key}: BackButton -> /staff/ (Panellar)", str(cur_tab))
    # rol menyusi orqali boshqa panelga o'tish (ceo)
    if role == "ceo":
        await goto_tab(s, "panellar", mobile)
        await p.click('.pcard[data-key="ceo"]')
        await p.wait_for_function("() => document.documentElement.dataset.noonAdapter", timeout=15000)
        cur = await p.evaluate("JSON.parse(sessionStorage.getItem('noon_x'))")
        target = [x for x in cur["panels"] if x["key"] == "lms"][0]["url"]
        await p.select_option("#roleSel", target)
        await p.wait_for_function("() => document.documentElement.dataset.noonAdapter === 'lms'", timeout=15000)
        check(True, f"{tag}: rol menyusi CEO -> LMS paneliga o'tkazdi")
    await s.ctx.close()


async def main_async(args) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await launch(p)
        for vp, vn in ((MOBILE, "mobil"), (DESKTOP, "desktop")):
            for role in ("ceo", "admin", "ustoz", "assistent", "begona"):
                print(f"== uy: {role} / {vn}", flush=True)
                await test_home(b, role, vp, f"{role}_{vn}")
        await test_no_telegram(b)
        print("== Ko'rinish: eski API va bo'sh holat", flush=True)
        await test_old_api(b)
        print("== NUQTA UI (manzara, kun/tun, kontrast)", flush=True)
        await test_nuqta(b)
        for vp, vn in ((MOBILE, "mobil"), (DESKTOP, "desktop")):
            for role in ("ceo", "admin", "ustoz", "assistent"):
                print(f"== panellar: {role} / {vn}", flush=True)
                await test_panels(b, role, vp, f"{role}_{vn}")
        print("== qo'shimcha", flush=True)
        await test_extras(b)
        await test_direct_panel(b)
        print("== xodimni chiqarish", flush=True)
        await test_removal(b)
        await b.close()
    bad = [n for ok, n in RESULTS if not ok]
    print(f"\nJAMI: {len(RESULTS)} tekshiruv, {len(RESULTS) - len(bad)} PASS, {len(bad)} FAIL")
    for n in bad:
        print("  FAIL", n)
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-server", action="store_true")
    args = ap.parse_args()
    proc = None
    if not args.no_server:
        proc = start_server()
    try:
        return asyncio.run(main_async(args))
    finally:
        if proc is not None and not args.keep:
            stop_server(proc)


if __name__ == "__main__":
    sys.exit(main())

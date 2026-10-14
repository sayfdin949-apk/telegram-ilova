# Demo boshqaruvi va interaktiv holatlar rasmi: demo paneli (1440 va 1366), telefon sahnasi, menyu, tasdiq oynasi,
# fokus tartibi (Tab), reduced-motion. Natija: ..\_tekshiruv\i_*.png
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
TEK = HERE.parent / "_tekshiruv"
DEMO = (HERE.parent / "demo.html").resolve().as_uri()


def launch(p):
    for ch in ("chrome", "msedge"):
        try:
            return p.chromium.launch(channel=ch)
        except Exception:  # noqa: BLE001
            continue
    return p.chromium.launch()


with sync_playwright() as p:
    br = launch(p)
    ctx = br.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(DEMO)
    page.evaluate("() => { DEMO.theme('sahro','kun'); DEMO.go('bosh'); }")
    page.wait_for_timeout(400)
    page.screenshot(path=str(TEK / "i_demo_1440.png"))
    page.set_viewport_size({"width": 1366, "height": 768})
    page.wait_for_timeout(400)
    page.screenshot(path=str(TEK / "i_demo_1366.png"))
    page.set_viewport_size({"width": 1440, "height": 900})
    # telefon sahnasi + menyu
    page.evaluate("() => { DEMO.setDev('tel'); DEMO.go('bosh'); }")
    page.wait_for_timeout(400)
    page.screenshot(path=str(TEK / "i_tel_sahna.png"))
    page.click("#menuB")
    page.wait_for_timeout(300)
    page.screenshot(path=str(TEK / "i_tel_menyu.png"))
    page.keyboard.press("Escape")
    # tasdiq oynasi
    page.evaluate("() => { DEMO.setDev('pc'); DEMO.go('funksiyalar'); }")
    page.wait_for_timeout(300)
    page.click('#fGroups li[data-k="reyting"] .sw')
    page.wait_for_timeout(300)
    page.screenshot(path=str(TEK / "i_dialog.png"))
    page.click("#dlgOk")
    page.wait_for_timeout(300)
    page.screenshot(path=str(TEK / "i_dialog_keyin.png"))
    # Tab tartibi (birinchi 40 qadam)
    page.evaluate("() => { DEMO.go('bosh'); window.scrollTo(0,0); }")
    page.wait_for_timeout(300)
    page.mouse.click(5, 300)
    order = []
    for _ in range(40):
        page.keyboard.press("Tab")
        order.append(page.evaluate("() => { const a = document.activeElement; const r = a.getBoundingClientRect(); return (a.getAttribute('aria-label') || a.textContent || a.tagName).trim().replace(/\\s+/g,' ').slice(0, 28) + ' @' + Math.round(r.top) ; }"))
    (TEK / "i_tab_tartibi.json").write_text(json.dumps(order, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(order))
    ctx.close()
    br.close()

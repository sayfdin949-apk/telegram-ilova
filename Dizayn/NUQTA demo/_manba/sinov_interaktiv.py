# demo.html ni internetsiz (offline) ochib, aylanish va boshqaruv tugmalarini sinaydi.
from playwright.sync_api import sync_playwright
import suratlar as s

D = s.TEK
with sync_playwright() as p:
    br = s.launch(p)
    ctx = br.new_context(viewport={"width": 1600, "height": 1000}, offline=True)
    pg = ctx.new_page()
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url) if not r.url.startswith(("file:", "data:")) else None)
    for i in range(3):
        pg.goto(s.DEMO.resolve().as_uri())
        pg.evaluate("document.fonts.ready.then(() => 1)")
        print("ochilish", i + 1, pg.evaluate("[document.documentElement.dataset.v, document.documentElement.dataset.m]"))
    print("shriftlar:", pg.evaluate("[...new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family))].join(', ')"))
    pg.screenshot(path=str(D / "desktop_ochilish.png"))
    pg.click(".dm-bar [data-set-kor='bitta']")
    pg.click(".dm-bar [data-go='duel']")
    pg.click(".dm-bar [data-set-m='tun']")
    pg.click(".dm-bar [data-set-v='shom']")
    pg.wait_for_timeout(300)
    pg.click(".dm-ph.on .qz-li >> nth=2")
    pg.wait_for_timeout(300)
    print("holat:", pg.evaluate("[document.body.dataset.kor, document.querySelector('.dm-ph.on').dataset.scr, document.documentElement.dataset.m, document.documentElement.dataset.v, document.body.dataset.duel]"))
    pg.screenshot(path=str(D / "desktop_bitta_duel_natija.png"))
    pg.click(".dm-ph.on .du-natija [data-go='bosh']")
    pg.wait_for_timeout(200)
    pg.click(".dm-ph.on .ap-nav [data-go='profil']")
    pg.click(".dm-ph.on .mz [data-set-v='qahva']")
    pg.click(".dm-ph.on .seg [data-set-m='kun']")
    pg.wait_for_timeout(300)
    print("profil orqali:", pg.evaluate("[document.querySelector('.dm-ph.on').dataset.scr, document.documentElement.dataset.v, document.documentElement.dataset.m]"))
    pg.screenshot(path=str(D / "desktop_profil_qahva_kun.png"))
    print("tashqi so'rovlar:", reqs)
    br.close()

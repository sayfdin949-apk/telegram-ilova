# Muhammadamin Telegram ilova — technical specification (single source of truth)

ROOT = `C:\Users\N.M\Desktop\MUHAMMAD AMIN\Telegram ilova`
Owner: Muhammad Amin (Arabic teacher). Brand shown in our UI and bot texts: **Muhammadamin** (owner change 02.10; was "Noon Academy" — course presentations keep their own "NOON AKADEMIYASI" text as course content, demo panels `web/staff/p/*` unchanged). All user-facing text: **Uzbek, Latin script**.

## 0. What we build

1. **Student bot ("talaba boti")** + **Student Mini App** (`web/app`): the real *Fonetika kursi* — 36 lessons as slide images rendered from the owner's PDFs, video lessons, the real lesson-8 test, XP/streak/daily goal/leaderboard. The student picks the UI **style** — `game` ("O'yinli", design C) or `glass` ("Shisha", design F) — and the **mode** — `light` ("Kunduzgi"), `dark` ("Tungi"), `auto` ("Avto", follows Telegram). 4 visual variants in total.
2. **Staff bot ("xodim boti")** + **Staff Mini App** (`web/staff`): role-gated (`ceo`, `admin`, `ustoz`, `assistent`). Real data (students, progress, course control, invites) + the three already-designed demo panels (CEO, Admin, LMS = Admin in LMS mode, Ustoz/Assistent).
3. **One Python process** `server/main.py`: aiohttp on `127.0.0.1:8790`, a cloudflared quick tunnel (public HTTPS URL, changes on every start), and both bots (python-telegram-bot **22.8**, long polling, JobQueue/APScheduler available). On start the bots' menu buttons are pointed at the new URL.

### Hard rules (owner's rules — never break)
- UI and bot texts: Uzbek Latin. **No emoji anywhere** (code, UI, bot messages). Icons: **Lucide only**.
- Arabic text always inside `<bdi dir="rtl" lang="ar">…</bdi>` (inline) or an element with `dir="rtl" lang="ar"`; font stack `"Sakkal Majalla","Noto Naskh Arabic",serif` (Noto Naskh is self-hosted).
- **Never retype, translate, "improve" or reorder course content** (lesson titles, topics, slide images, test text, answer explanations): copy verbatim from the sources listed in §2.
- No religious greetings/terms in UI or bot texts ("Salom", "Xush kelibsiz" — not "Assalomu alaykum").
- Secrets: bot tokens live **only** in `server/.env`, written **only** by `server/tokenlar.py` that the owner runs himself. Agents never create a real `.env`, never print/log tokens, set the `httpx` logger to WARNING (token is in request URLs).
- Do **not** touch `C:\Users\N.M\.claude\telegram-bot\` (another live bot of the owner). Do not add anything to Windows Startup. Do not kill processes you did not start (only processes whose command line contains ROOT).
- Every subprocess spawned from the server uses `creationflags=0x08000000` (CREATE_NO_WINDOW).

## 1. Folder layout and file ownership

```
ROOT\
  O'QI - ishga tushirish.txt          (server agent)  owner instructions, Uzbek
  1 - Tokenlarni kiritish.bat          (server agent)  -> python server\tokenlar.py
  2 - Botlarni ishga tushirish.bat     (server agent)  -> python server\boshqar.py start
  3 - Botlarni to'xtatish.bat          (server agent)  -> python server\boshqar.py stop
  4 - Holat.bat                        (server agent)  -> python server\boshqar.py holat
  server\  main.py config.py db.py auth.py web.py student_bot.py staff_bot.py tunnel.py
           tokenlar.py boshqar.py  bin\cloudflared.exe (already copied)
           videolar.json           (content agent creates; server reads)
  web\app\      index.html app.css app.js           (student-app agent)
  web\staff\    index.html staff.css staff.js adapter.js   (staff agent)
  web\staff\p\  CEO_paneli.html Admin_paneli.html Ustoz_paneli.html (already copied; built demo panels — do not rewrite their content; adapter is injected at serve time)
  web\content\  kurs.json  dars\NN\NNN.webp  dars\NN\thumb.webp  test\08.json  video\<id>.webp   (content agent)
  web\shared\   fonts\*.woff2 (Be Vietnam Pro + Noto Naskh already copied; content agent adds Nunito)  icons.svg (Lucide sprite)
  tools\        kontent.py ikonlar.py (content agent) · tg_mock.js sinov_initdata.py (given) · test_*.py (each agent, own prefix)
  data\         noon.db (runtime) sinov_*.db (tests) holat.json main.pid secret.key
  log\          server.log
  docs\SPEC.md (this file)
```
Only edit files you own. If you need something from another component, follow this spec; do not edit its files.

## 2. Content (sources → web/content)

Sources (read-only):
- Lesson PDFs: `C:\Users\N.M\Desktop\taqdimot\Fonetika kursi (36 dars)\PDF\NN-dars (Title).pdf` — 36 files, 573 pages; pages are 960×540 pt (16:9) except lesson 18 (A4 portrait, 8 pages).
- Schedule: `C:\Users\N.M\Desktop\taqdimot\Fonetika kursi (36 dars)\Dars jadvali.html` — 4 parts, per lesson: Dars, Mavzu, Kitob bet, Taqdimot va slaydlar.
- Lesson-8 test: `C:\Users\N.M\Desktop\taqdimot\O'quvchi materiallari (36 dars)\_namuna\08-dars\2-test.html` (questions) + `3-kalit.html` (answers + explanations).
- Video: `C:\Users\N.M\Desktop\videolar\Fonetika 2-dars - Sifatning davomi (motion).mp4` (1934 s, 113 MB, H.264 1080p, 0.47 Mbit/s) → lesson 2 (`d02`).
- Lesson recordings (owner change 02.10): `C:\Users\N.M\Desktop\videolar\siqilgan\N-dars_*.mp4` (H.264 1024×768 + audio, faststart). Titles from `SIQILGAN_NOMLAR` in `tools/kontent.py`: `2-dars_ipad.mp4` → `d02b` "Darsning to'liq yozuvi" (2312 s), `3-dars_ipad.mp4` → `d03` "Harflar: Roo, Zaa, Taa, Nuun, Yaa, Kaaf (to'liq yozuv)" (2044 s). A file whose ffmpeg `.log` has no final summary yet (still encoding) is skipped.

### kurs.json
```json
{
  "nomi": "Fonetika kursi", "brend": "Muhammadamin", "versiya": "2026-10-02",
  "jami_dars": 36, "jami_slayd": 573,
  "qismlar": [
    {"n": 1, "nomi": "Kirish va harflar", "darslar": [1,2,3,4,5,6,7]},
    {"n": 2, "nomi": "Harakatlar va yozuv", "darslar": [8,9,10,11,12,13,14,15,16,17,18]},
    {"n": 3, "nomi": "Fonetika qoidalari", "darslar": [19,20,21,22,23,24,25,26,27,28,29,30,31,32]},
    {"n": 4, "nomi": "O'qish matnlari", "darslar": [33,34,35,36]}
  ],
  "darslar": [
    {"n": 1, "qism": 1,
     "nomi": "Arab tiliga kirish",                       // from the PDF file name, verbatim (text inside parentheses)
     "mavzu": "Arab tiliga kirish: harf, tovush, maxrajlar", // "Mavzu" column of Dars jadvali, verbatim
     "kitob": "7–13",                                      // "Kitob, bet" column, verbatim ("" if none)
     "slaydlar": 33, "nisbat": "16:9",                     // page count; lesson 18 -> "a4"
     "rasm": "/content/dars/01/", "thumb": "/content/dars/01/thumb.webp",
     "pdf": "01-dars (Arab tiliga kirish).pdf",            // file name only (server maps to PDF dir)
     "video": null,                                        // = videolar[0] or null (kept for backward compatibility)
     "videolar": [],                                       // ALL videos of the lesson (readers use this)
     "test": null}
  ]
}
```
- Part names: take the Roman-numbered headings of Dars jadvali verbatim minus the numbering/range ("I. Kirish va harflar · 1–7-darslar" → "Kirish va harflar"; the two "III" headings merge into part 3 "Fonetika qoidalari").
- Video object: `{"id":"d02","nomi":"Sifatning davomi","davomiylik":1934,"poster":"/content/video/d02.webp","url":"/media/video/d02"}`. Lesson 2: `videolar = [d02, d02b]`, lesson 3: `[d03]`. ids: `d{NN}`, then `b`, `c`… if taken (motion videos first, then `siqilgan`). Duration from the mp4 `mvhd` atom. Progress/XP is per video id (+30 once per video).
- `test` for lesson 8: `"/content/test/08.json"`.
- Slides: `web/content/dars/NN/001.webp …` (3-digit, 1-based). 16:9 pages → 1280×720 WebP q≈80; lesson 18 → 1000 px wide. `thumb.webp` = page 1 at 480 px wide.
- Poster: frame at ~8 % of the video (OpenCV `cv2` is installed) → 1280×720 WebP (4:3 recordings: centre crop).
- **Scanned book pages** (A4 pages: `kitob_betlari` of lessons 3–7 and all pages of lesson 18, incl. its thumb): `tools/skaner_tozala.py`, called from `kontent.py` during rendering, removes the "Scanned with CamScanner" badge (bottom-right, filled with the surrounding paper colour) and a finger at the left edge (skin-colour blob, column-wise fill) — only in the app copies; source PDFs untouched. Holat signature `skaner` re-renders those lessons when the cleaner version changes.

### test/08.json
```json
{"dars": 8, "nomi": "Mad harflari — test", "savollar": [
  {"q": "Mad harflari qaysilar?", "opts": ["ب ت ث", "ا و ي", "ا ل م", "و ه ي"], "ok": 1,
   "izoh": "Mad harflari uchta: ا و ي . Boshqa variantlarda mad bo'lmaydigan harflar bor ( ب ت ث ل م ه )."}
]}
```
**Owner change (02.10): live HTML presentations.** `tools/taqdimot.py` (called at the end of `tools/kontent.py`) copies the 8 source decks to `web/content/taqdimot/<1..8>/index.html` in "student mode" and adds per lesson `"taqdimot": {"url", "from", "to"}` (1-based deck slide numbers from Dars jadvali), sets `"slaydlar" = to - from + 1` (sum 543; XP and the 80 % rule use this), and for lessons 3-7 `"kitob_betlari"` (scanned book page images; no XP). Lesson 18 has no deck and keeps the image viewer. Deck protocol: iframe `url?from=F&to=T&start=K`; parent -> deck `postMessage({noon:'next'|'prev'|'ping'})` / `{noon:'goto', n}`; deck -> parent `{noon:'slide', n, total, step, steps}` and `{noon:'end'}`. PDF slide images remain only as thumbnails, lesson 18 and book pages; the "PDF ni chatga yuborish" button was removed (server `/api/s/pdf` kept).

`ok` is the 0-based index of the right option, from the answer key. All strings verbatim. Options may mix Latin and Arabic ("بِي — «bii»"): the UI wraps Arabic runs in `<bdi>`.

### server/videolar.json (server-side only — contains local paths, never served)
`[{"id":"d02","dars":2,"nomi":"Sifatning davomi","fayl":"C:\\Users\\N.M\\Desktop\\videolar\\Fonetika 2-dars - Sifatning davomi (motion).mp4"}, {"id":"d02b","dars":2,…}, {"id":"d03","dars":3,…}]` — one entry per video, written by `kontent.py`.

### Fonts and icons
- `web/shared/fonts/`: Be Vietnam Pro 400–800 latin+latin-ext and Noto Naskh Arabic 400/700 (present); content agent adds **Nunito** 700–900 (variable, latin + latin-ext woff2 from Google Fonts css2 API) as `nunito-latin.woff2`, `nunito-latin-ext.woff2`, and writes `web/shared/fonts.css` with all `@font-face` rules (correct `unicode-range`).
- `web/shared/icons.svg`: Lucide sprite of `<symbol id="NAME" viewBox="0 0 24 24">` built by `tools/ikonlar.py` from `https://cdn.jsdelivr.net/npm/lucide-static@0.469.0/icons/NAME.svg` (cache in `tools/_lucide_cache/`). It scans `web/app/*.{html,js}` and `web/staff/*.{html,js}` for `ic('NAME')`, `ic("NAME")` and `icons.svg#NAME`, plus a base list. Usage everywhere: `<svg class="i" aria-hidden="true"><use href="/shared/icons.svg#NAME"/></svg>`. **Whoever adds icon names re-runs `python tools/ikonlar.py`.** Unknown icon names must fail loudly in the script.

## 3. HTTP routes (server/web.py)

| Route | What |
|---|---|
| `GET /` | 302 → `/app/` |
| `GET /app/`, `/app/{file}` | `web/app/` static |
| `GET /staff/`, `/staff/{file}` | `web/staff/` static (index, css, js, adapter.js) |
| `GET /staff/p/{name}` | demo panel HTML with injection (§6.3); requires `?t=` panel token valid for that panel; else 302 → `/staff/` |
| `GET /shared/{path}` | `web/shared/` static |
| `GET /content/{path}` | `web/content/` static |
| `GET /media/video/{id}` | streams the file from `server/videolar.json` with HTTP Range (aiohttp `FileResponse`), `Content-Type: video/mp4` |
| `/api/s/*` | student API (§4.1) |
| `/api/x/*` | staff API (§4.2) |

Headers: `X-Content-Type-Options: nosniff`; `Referrer-Policy: no-referrer`; html/js/css → `Cache-Control: no-cache` (ETag / Last-Modified revalidation); images/fonts/video → `max-age=604800`; API → `no-store`. No directory listing, no path traversal (resolve and check the path stays inside its root). Body limit 64 KB for API.

## 4. API contract (JSON; errors → `{"xato": "uzbek message"}`)

### 4.1 Student API — header `X-Init-Data: <Telegram.WebApp.initData>`
Validated with HMAC (key `WebAppData`, the **student** bot token), `auth_date` not older than 7 days; the user comes from `initData.user`. Failure → 401.

- `POST /api/s/me` `{}` → upserts user (names, username, photo_url, last_seen) and returns
```json
{"user": {"id": 1, "first_name": "Aziza", "last_name": "Karimova", "username": "aziza_k", "photo_url": null},
 "prefs": {"uslub": "game"|"glass"|null, "rejim": "auto"|"light"|"dark", "arab": "m"|"l", "eslatma": true},
 "stats": {"xp": 152, "streak": 3, "best_streak": 5, "today_xp": 24, "goal": 30,
           "week": [{"day": "2026-09-26", "xp": 0}, … 7 items, oldest first, last = today]},
 "progress": {"lessons": {"8": {"seen": [1,2,3], "done_at": null}},
              "videos": {"d02": {"pos": 312.5, "done_at": null}},
              "tests": {"8": {"best": 4, "last": 4, "total": 5, "tries": 2}}},
 "course": {"open": 36, "jami": 36, "available": [1, 2, 3, 4, 5, 6, 7, 8, 9]}}
```
- **Sequential unlock** (owner change 02.10): lesson n is available iff `n <= course.open` AND (`n == 1` OR lesson n−1 has `done_at`). `course.available` = sorted list of available lessons; it is also returned as `"course"` in every `/api/s/event` response, so the next lesson unlocks immediately after `lesson_done`.
- `POST /api/s/event` → `{"xp_added": n, "stats": {...}}` (and the changed progress item under `"item"`):
  - `{"type":"slide","dars":8,"idx":3}` — +1 XP the first time a slide is seen.
  - `{"type":"lesson_done","dars":8}` — requires `seen` ≥ ceil(0.8 × slides), else 400; +20 XP once.
  - `{"type":"video_pos","vid":"d02","pos":312.5}` — no XP.
  - `{"type":"video_done","vid":"d02"}` — +30 XP once.
  - `{"type":"test_done","dars":8,"answers":[1,2,1,2,2]}` — the **server** scores against `web/content/test/NN.json`; XP = 4 × (new_best − old_best) (+10 bonus if first-ever perfect); returns `{"correct": 4, "total": 5, ...}`.
  - Lessons beyond `course.open` → 403 "Bu dars hali ochilmagan. Ustoz ochganda ochiladi."; lesson whose predecessor is not done → 403 `{"xato": "Avval {n-1}-darsni tugating"}` (slide, lesson_done, test_done, video_pos/video_done of that lesson's videos, `/api/s/pdf`). Rate limit 120 events/min/user.
- `POST /api/s/prefs` `{"uslub","rejim","arab","eslatma"}` (any subset) → `{"ok": true}`.
- `GET /api/s/rating?davr=hafta|umumiy` → `{"top": [{"rank": 1, "name": "Aziza K.", "xp": 152, "streak": 3, "me": false}], "me": {"rank": 7, "xp": 40, "name": "…"}}`. Top 20. `hafta` = XP since Monday 00:00 Tashkent. Name = first_name + last-name initial.
- `POST /api/s/pdf` `{"dars": 8}` → the student bot sends that lesson's PDF to the user's chat (cache `file_id` in DB after the first upload); 1 per 20 s, 15 per day per user → `{"ok": true}`. In sinov mode → `{"ok": true, "sinov": true}` without sending.

Time zone: Asia/Tashkent = fixed UTC+05:00 (do not rely on tzdata). Streak: a day counts when it has ≥ 1 XP; consecutive days → streak + 1, gap → 1. Daily goal 30 XP.

### 4.2 Staff API — header `X-Init-Data` (validated with the **staff** bot token, max age 24 h) **or** `X-Staff-Token` (panel token)
The Telegram user must be in table `staff`, else 403 `{"xato": "Bu bo'lim faqat xodimlar uchun"}`.

- `POST /api/x/auth` → `{"user": {...}, "role": "ceo", "brend": "Muhammadamin", "token": "<panel token>", "panels": [{"key": "ceo", "nomi": "CEO paneli", "url": "/staff/p/CEO_paneli.html?t=…"}, …]}`
  - panels per role: `ceo` → ceo, admin, lms, ustoz · `admin` → admin, lms · `ustoz` → ustoz, lms · `assistent` → assistent.
  - keys → files: `ceo` CEO_paneli.html · `admin` Admin_paneli.html · `lms` Admin_paneli.html?rejim=lms · `ustoz` Ustoz_paneli.html · `assistent` Ustoz_paneli.html?rejim=assistent.
  - panel token = base64url(JSON `{"id","role","exp"}`) + "." + hex HMAC-SHA256 with `data/secret.key` (32 random bytes, created on first run); exp = now + 12 h.
- `GET /api/x/stats` → `{"students": 37, "active_today": 9, "active_7d": 21, "new_7d": 6, "lessons_done": 214, "videos_done": 18, "tests_done": 25, "avg_xp": 96, "styles": {"game": 20, "glass": 11, "none": 6}, "modes": {"light": 12, "dark": 9, "auto": 16}, "daily": [{"day": "2026-09-19", "active": 3, "xp": 120}, … 14 days], "recent": [{"name": "Aziza K.", "kind": "lesson_done", "ref": "8-dars", "at": "2026-10-02T14:05:00+05:00"}, … 20]}`
- `GET /api/x/students?q=` → `{"students": [{"id", "name", "username", "joined_at", "last_seen", "xp", "streak", "lessons_done", "videos_done", "uslub", "rejim"}]}` (≤ 500, newest activity first)
- `GET /api/x/course` → `{"open": 36, "lessons": [{"n": 8, "nomi": "...", "qism": 2, "slaydlar": 15, "video": false, "videolar": 0, "test": true, "done": 12, "started": 20, "test_avg": 3.8}]}`
- `POST /api/x/open` `{"n": 12}` (ceo, admin, ustoz; 1–36) → `{"ok": true, "open": 12}`
- `POST /api/x/invite` `{"role": "admin"|"ustoz"|"assistent"}` (ceo) → `{"link": "https://t.me/<staffbot>?start=t_<code>", "expires": "…"}` (single use, 48 h)
- `GET /api/x/staff` (ceo) → `{"staff": [{"id", "name", "username", "role", "added_at"}]}`; `POST /api/x/staff/remove` `{"id"}` (ceo; cannot remove self or the last ceo)

## 5. Student Mini App (`web/app`) — design and behaviour

Files: `index.html`, `app.css`, `app.js` (vanilla JS, no framework, no build step). `index.html` loads, in `<head>`, blocking: `https://telegram.org/js/telegram-web-app.js?59`, then `/shared/fonts.css`, `app.css`; `app.js` at end of body. Must also run in a normal browser without Telegram (preview mode: banner "Namuna rejimi", progress in localStorage, rating hidden).

### 5.1 Theming
`<html data-uslub="game|glass" data-rejim="light|dark">` (resolved; `auto` → `Telegram.WebApp.colorScheme`, listen to `themeChanged`). Every colour is a CSS custom property defined per combination. After any change call `tg.setHeaderColor`, `tg.setBackgroundColor`, and `tg.setBottomBarColor` (if `isVersionAtLeast('7.10')`) with that variant's header/background colour.

Reference design (owner approved these): `C:\Users\N.M\Desktop\MUHAMMAD AMIN\Ilova dizayni\Ilova_dizayni_asoslari.html` — section "Bitta ekran — 6 xil uslub", phones **C (O'yinli)** and **F (Shisha)**. Its CSS (lines ~317–397) is the source of truth for the light-game and dark-glass variants:

**game · light (C as approved)** — font Nunito 700/800/900 (Arabic Noto Naskh). bg `#FFFFFF`, text `#3C3C3C`, text-2 `#4B4B4B`, muted `#777777`, lines `#E5E5E5`/`#EFEFEF` (2 px borders). Green `#3CC14E` with 3D shadow `0 4px 0 #2A9A3A`; green soft `#E8F6EA` / line `#BEE6C3` / ink `#2E9E43`. Yellow (current node) `#FFC53D` shadow `#E0A21A`, ring `rgba(255,197,61,.28)`, bubble text `#E09A00`. Blue `#1CA7EC` (active nav: bg `#DDF4FF`, inset ring `#84D8FF`), gem fill `#9EDCFA`. Orange flame `#FF9600`. Red heart `#FF4B4B`. Locked `#E5E7EB` / shadow `#C9CDD3` / ink `#AFB4BC`. Big 3D buttons: solid colour + `box-shadow: 0 4px 0 <darker>`; pressed → translateY(4px), no shadow. Radius 14–16 px, nodes circular. Top stat bar: flag tile (Arabic letter `نُ`, green soft tile) · flame + streak · gem + XP · `book-check` + lessons done.
**game · dark (new, same identity)** — bg `#10191D`, surface `#17242A`, surface-2 `#1D2C33`, lines `#2B3B43`/`#22323A`, text `#EEF4F6`, text-2 `#C9D6DB`, muted `#8EA3AC`; green `#43C957` (shadow `#2E8E3C`, soft `rgba(67,201,87,.14)`, ink `#6BE07B`); yellow `#FFC53D` (shadow `#B9800C`); blue `#38B6F1` (nav active bg `rgba(56,182,241,.16)`, ring `rgba(56,182,241,.55)`); orange `#FF9F1A`; red `#FF5C5C`; locked `#26363E`/`#1A272D`/`#5E7480`. Header colour `#10191D`.
**glass · dark (F as approved)** — font Be Vietnam Pro. bg `#0B2A22` + `radial-gradient(60% 40% at 12% 18%, rgba(74,224,74,.55), transparent 70%), radial-gradient(55% 45% at 95% 42%, rgba(20,170,150,.6), transparent 70%), radial-gradient(70% 45% at 25% 98%, rgba(40,110,220,.45), transparent 70%), linear-gradient(160deg, #0E3B2C, #071A16)` fixed to the viewport. Glass: `rgba(255,255,255,.13)`, border `1px solid rgba(255,255,255,.26)`, `backdrop-filter: blur(16px)`, radius 20 px. Text `#FFFFFF`, text-2 `rgba(255,255,255,.85)`, muted `rgba(255,255,255,.72)`, kicker/accent `#B9F6CA`, ring `#9CF59A`. CTA: white pill, text `#0B2A22`. Floating glass bottom nav (radius 22 px, margin 12 px), active item `rgba(255,255,255,.2)`. Header colour `#0E3B2C`.
**glass · light (new)** — bg `#EAF6F0` + same three radial blobs at lower alpha (`rgba(106,239,90,.35)`, `rgba(20,170,150,.28)`, `rgba(40,110,220,.22)`) over `linear-gradient(160deg, #F3FBF6, #E3F2EC)`. Glass `rgba(255,255,255,.55)`, border `rgba(255,255,255,.8)`, shadow `0 8px 24px rgba(13,58,26,.08)`, blur 18 px. Text `#0D3A1A`, text-2 `#2F5A3A`, muted `#5A8060`, accent `#1A6A2A`, ring `#2EB82E`; CTA: `#0D3A1A` pill with white text. Header colour `#EEF8F2`.
Status colours keep icon + label (never colour alone). Contrast ≥ 4.5:1 for body text, ≥ 3:1 for large bold text, in all 4 variants.

The two styles differ in **layout**, not only colour: `game` = Duolingo-like path, chunky 3D buttons, playful mascot; `glass` = calm cards, progress rings, floating glass nav.

### 5.2 Telegram integration
`tg.ready(); tg.expand();` `disableVerticalSwipes()` (≥ 7.7) while the slide viewer or quiz is open, re-enable after. `BackButton` on every nested screen (also an in-app back control). `HapticFeedback` (`selectionChanged` on option pick, `impactOccurred('light')` on nav, `notificationOccurred('success'|'error')` on results). Prefs cached in `tg.CloudStorage` (keys `uslub`, `rejim`, `arab`) + `localStorage` fallback so the theme applies before the network answers, then synced via `/api/s/prefs`. Start parameters: query `?tab=darslar|video|reyting|profil` and `?dars=N` (do **not** use the URL hash for routing — Telegram puts `tgWebAppData` there). Use `var(--tg-viewport-stable-height, 100vh)` and safe-area insets for layout.

### 5.3 Screens
Bottom nav (5): **Bosh** (`house`), **Darslar** (`book-open`), **Video** (`circle-play`), **Reyting** (`trophy`), **Profil** (`user-round`). Nested (with back): Dars (slide viewer), Video player, Mashq (quiz), Natija (result), Onboarding.

1. **Onboarding** (first run, `prefs.uslub == null`): "Xush kelibsiz!" → "Ilova ko'rinishini tanlang": two large live mini-previews (CSS-rendered) "O'yinli — seriya, ball va yo'l xaritasi" / "Shisha — zamonaviy shisha kartalar" → then mode Kunduzgi / Tungi / Avto (Telegram bilan bir xil) → "Boshlash". Changeable later in Profil.
2. **Bosh** — `game`: stat bar; unit banner of the current part ("2-QISM · 8-DARS", part name, colour per part with a 3D shadow); zig-zag path of that part's lessons (states: done = green + check; current = big yellow + star + bubble "BOSHLASH"/"DAVOM ETISH"; open = white node with green border + number; locked = grey + lock); mascot (green circle with `نُ`) with a speech bubble tip; daily goal bar (today_xp / 30). `glass`: "Salom, {ism}" + title; avatar (Telegram photo or initials) → Profil; glass card with SVG ring = slides seen % of the current lesson, kicker "8-DARS", lesson name, CTA "Davom etish"; glass plan list (Slaydlar n/m · Video dars (32 daq) if any · Mashq (5 savol) if any); stats row (seriya, ball, darslar).
   Current lesson = lowest open lesson that is not done (or the last one opened).
   Lock states (all screens): a lesson not in `course.available` is locked (`lock` node / row). Reason text: beyond `course.open` → "Ustoz ochganda ochiladi"; otherwise "Avval {n-1}-darsni tugating" (row meta, node aria-label, toast on tap, `?dars=N` start param). Videos and the test of a locked lesson are locked too (video card grey + badge, toast). Glass plan list shows one row per video ("Video 1", "Video 2" when several).
3. **Darslar** — all 4 parts. `game`: full path, part banners, tap a node → Dars. `glass`: glass list grouped by part, each row: mini ring, "8-DARS", name, meta (slides · video icon · test icon), lock if beyond `course.open` ("Ustoz ochganda ochiladi").
4. **Dars** (slide viewer) — header: back, "8-dars", lesson name, counter "3 / 15", progress bar. Horizontal scroll-snap carousel of `<img loading="lazy" decoding="async">` (preload ±1), swipe, tap left/right thirds, thumbnail strip, "Kattalashtirish" (zoom overlay with 1×/2×/3× and pan). Each newly seen slide → `event slide` (debounced). On the last slide the primary button becomes "Darsni tugatish" → `lesson_done` → result card (+20 ball) → next steps: "Video dars" (if any), "Mashq" (if any), "Keyingi dars". Secondary: "PDF ni chatga yuborish" (`/api/s/pdf`, toast "PDF chatga yuborildi"). One-time hint: "Telefonni yotqizsangiz slaydlar kattaroq ko'rinadi". `game`: chunky 3D Oldingi/Keyingi buttons; `glass`: glass pills.
5. **Video** — list of ALL videos of all lessons (poster, title "2-dars · Sifatning davomi", duration "32 daq", watched/progress badge; locked: "Yopiq" / "Avval N-dars"). Lesson screen (deck / image viewer) has a "Video" pill (one video) or "Videolar · N" pill opening a sheet with the lesson's videos; the done sheet lists every video of the lesson; the player shows "Shu darsning boshqa videolari". Empty state text if none. Player: `<video controls playsinline preload="metadata" poster>`; resume from saved `pos` (if 10 s < pos < 95 %); `video_pos` every 15 s and on pause; at ≥ 90 % → `video_done` (+30). Button "Darsga o'tish".
6. **Mashq** (quiz, only lessons with `test`): top: close, progress bar, hearts (start 5, −1 per wrong, 0 → end with "Qayta boshlash"); kicker "1-SAVOL · 5 TADAN"; question; options in a 2×2 grid when all are short (≤ 14 chars), otherwise a list; "Tekshirish" disabled until a pick; bottom sheet: "To'g'ri javob!" / "Xato javob" + right answer + `izoh`; "Davom etish"; **Natija**: score, XP added (from server), mistakes with right answers, "Qayta urinish", "Darslarga qaytish". UX reference: the quiz in `C:\Users\N.M\Desktop\MUHAMMAD AMIN\Ilova dizayni\Noon_ilova_demo.html` (restyle it into C/F).
7. **Reyting** — segmented "Bu hafta / Umumiy"; top 3 podium (`game`: gold/silver/bronze medals; `glass`: glass podium), then the list; own row highlighted and pinned if outside top 20.
8. **Profil** — avatar, name, @username; stats (ball, seriya, eng uzun seriya, darslar n/36, videolar); 7-day dots; **Uslub** (two preview cards, selected one marked); **Rejim** segmented Kunduzgi / Tungi / Avto; **Arabcha matn** O'rta / Katta; **Kunlik eslatma** switch ("Har kuni 19:00 da bot eslatadi"); "Kurs haqida" (36 dars, 573 slayd); footer = `kurs.json` `brend` ("Muhammadamin").

Quality bar: no horizontal scroll at 360–430 px wide; tap targets ≥ 44 px; visible focus; `prefers-reduced-motion`; skeleton/loading and error states (network down → retry button, never a blank screen); all strings Uzbek; JS < 120 KB, CSS < 60 KB (unminified ok).

## 6. Staff Mini App (`web/staff`)

### 6.1 Home (`index.html`, `staff.css`, `staff.js`) — NUQTA UI since 05.10 (was NOON UI)
**05.10 (owner, "2 ha"): NUQTA UI**, the same visual language as the admin panel (§13) and the student app (§12); behaviour unchanged (auth incl. `X-Staff-Token` fallback, the five tabs, ustoz/assistent read-only open lessons, invite links, staff removal, error/deny screens, demo-panel cards + `noon_x`). Not in any bot menu (the admin panel replaced it), still served at `/staff/` for direct links. Tokens `/shared/nuqta-tokens.css`, scenes `/shared/nuqta-sahnalar.js`, Lucide `/shared/icons.svg`, Be Vietnam Pro (Arabic `'Sakkal Majalla','Noto Naskh Arabic'`). `index.html` sets `<html data-v data-m>` before the first paint: manzara rotates on **every open** (localStorage `nuqta.staff.manzara` — separate from `nuqta.manzara` / `nuqta.admin.manzara`), mode by the local clock 06:00–18:59 kun, else tun; re-checked every 60 s and on `visibilitychange`. Telegram `setHeaderColor` / `setBackgroundColor` / `setBottomBarColor` and `<meta theme-color>` = the current `--bg` token. One accent card per screen (`.tint`, the manzara `--hero` colour; in shom/tun `--soft → --bg` because the `--hero` gradient top is 4,2:1 with `--t1`), Bugun hero with the scene, KPI band (one card, 6 cells), the 14-day chart gets a one-sentence takeaway, «ث» three-rhombus mark instead of the old «ن» logo, lesson numbers in rhombi, bottom tab bar like the student app, sidebar (≥ 900 px) like the admin panel, 44 px tap targets, focus ring `--ink`, reduced motion. No white / black / pink backgrounds, text ≥ 4,5:1 (checked for all 6 manzara × kun/tun). Content unchanged, except (06.10, owner "1 ha") the obsolete "Uslub tanlovi" card and uslub chips, replaced by Ko'rinish — see the next paragraph.

**06.10 (owner, "1 ha"): Ko'rinish in the staff app.** Bugun: the old "Uslub tanlovi" card (O'yinli / Shisha / Tanlanmagan + rejim bars) is replaced by a **Ko'rinish** card with the admin panel's content (§13), fed by `/api/x/stats` `korinish` (§10.6; all 4 roles, period 14 days): one-sentence takeaway (most opened manzara(s) + night share and peak hour), "Qaysi manzara ko'p ochilgan" (6 rows in server order with a small scene thumbnail per manzara — `scenes()` draws each `[data-scene]` with the nearest `[data-v]`, so `.th[data-v]` thumbs use their own manzara and kun/tun —, "N kishi tanlagan" / "tanlaganlar yo'q", bar, sessions, %), "Manzara tanlovi" (O'zi tanlagan vs Har ochilganda almashadi, % + o'quvchi + split bar), "Kunduzgi va tungi" (% + ochilish + split bar), "Ilova ochilishlari soatlar bo'yicha" (24-bar chart, night hours 19:00–05:59 shaded, peak labelled, tap/hover/keyboard tooltip "N ochilish · HH:00–HH:59 · kunduzgi/tungi soat", focus starts at the peak hour) with a "Jadval" / "Grafik" toggle (`aria-pressed`, 24-row table Soat · Vaqt · Ochilishlar, only that part re-renders, state kept in `S.korTbl`). Phone: one column; ≥ 900 px: two columns (manzara list | the rest). Layout of Bugun: hero + KPI band, 14-day chart (full width), Ko'rinish, So'nggi faollik. Old server (no `korinish` in `/api/x/stats`): the card is simply not rendered (no error); no data in the period: the card shows "Ko'rinish ma'lumoti hali yo'q". O'quvchilar: the uslub chip is replaced by the student's latest **manzara chip** (`/api/x/students` `manzara`, `mavzu`): a rhombus in that manzara's `--a2`, the name, a sun/moon icon and "kunduzgi"/"tungi" (the word visible ≥ 900 px, screen-reader-only on phones); nothing when `manzara` is null or missing (old server); column header "Ko'rinish". Files before this change: `_sinov/staff/orig_korinish/`, server `_sinov/staff_korinish/orig/`. Tests: `tools/test_staff.py` (`check_korinish` for 4 roles × phone/desktop, chips vs API, `test_old_api`: old API + empty period), `tools/test_korinish.py`, `tools/test_admin_api.py`, `tools/test_server.py`. Old NOON files: `_sinov/staff/orig_nuqta/`, `Desktop\MUHAMMAD AMIN\Eski ishlarim\Telegram ilova - xodim sahifasi (NOON, 05.10.2026)\`. Tests: `tools/test_staff.py` (+ `test_nuqta`). Demo panels `web/staff/p/*` and `adapter.js` stay NOON (unchanged).

Previous NOON description (kept for reference): NOON design system (same as the demo panels): mesh-light bg `radial-gradient(#D7F1D2 → #E3F2E2 → #EAF4EA)`, white cards radius 16 px with 1 px line and soft shadow, one dark `deep` card per screen (`linear-gradient(145deg,#16551F,#08200F)`), lime CTA `linear-gradient(135deg,#6AEF5A,#3DCB36 55%,#2EB82E)` with text `#0A2A10`, text `#0D3A1A / #3A6040 / #5A8060`, 78×6 px lime bar under titles, Be Vietnam Pro, Lucide. Mobile-first (Telegram), also fine on desktop. Light only (set Telegram header/background `#EAF4EA`).
Flow: load → `POST /api/x/auth` with initData → 403 → friendly "Ruxsat yo'q" screen (+ "Kirish uchun CEO dan taklif havolasini oling"). OK → tabs (bottom nav on phone):
- **Bugun** — KPI tiles from `/api/x/stats` (O'quvchilar, Bugun faol, 7 kunda faol, Yangi (7 kun), Tugatilgan darslar, O'rtacha ball); 14-day activity bar chart (single series, hover/tap tooltip, table view); ~~"Uslub tanlovi" split (O'yinli / Shisha / tanlanmagan) and modes~~ Ko'rinish card (06.10, see above); "So'nggi faollik" list.
- **Kurs** — `deep` card "Ochiq darslar: N / 36" with − / + and "Saqlash" (`/api/x/open`; hidden for assistent); lessons grouped by the 4 parts: n, name, slides, video icon, test icon, "tugatgan: X", "boshlagan: Y", test avg.
- **O'quvchilar** — search; rows: name, @username, qo'shilgan, oxirgi faollik, darslar X/36, ball, seriya, ~~uslub chip~~ latest manzara chip (06.10).
- **Panellar** — cards for the role's demo panels (from `/api/x/auth` `panels`): "CEO paneli", "Admin paneli", "LMS paneli", "Ustoz paneli", "Assistent paneli"; subtitle "Dizayn namunasi · demo ma'lumotlar". Before navigating, store `panels` + `token` in `sessionStorage` (`noon_x`).
- **Xodimlar** (ceo only) — staff list with role chips, remove; "Taklif havolasi" per role → shows link + "Nusxalash" + "Telegram orqali yuborish" (`tg.openTelegramLink('https://t.me/share/url?url=' + link)`).

### 6.2 Brand
Show `brend` from `/api/x/auth` (config; default "Muhammadamin") — subtitle "Boshqaruv". Kurs tab shows "N video" when a lesson has several videos.

### 6.3 Demo panels (`web/staff/p/*.html` + `adapter.js`)
The server injects into the panel HTML at serve time: in `<head>` `<meta name="referrer" content="no-referrer">` and `<script src="https://telegram.org/js/telegram-web-app.js?59"></script>`; before `</body>` `<script src="/staff/adapter.js"></script>`. `adapter.js`:
- `tg.ready(); tg.expand();` header/background `#EAF4EA`; `BackButton.show()` → `location.href = '/staff/'`; "Chiqish" nav item → `tg.close()`.
- Reads token `t` from the query (keep in sessionStorage); rebuilds the role `<select id="roleSel">` with only the user's panels (from sessionStorage `noon_x`), values = panel URLs with `?t=`; removes options for `Noon_ilova_demo.html` / `Rollar_demo.html`.
- Brand: replace the sidebar brand title with `brend`.
- `?rejim=lms` on Admin_paneli.html: hide every sidebar nav group except the one labelled "LMS", brand subtitle "LMS paneli", go to the first LMS screen if the current screen is not in that group (`Panel.go(id)`; ids via `Panel.cfg.nav`).
- `?rejim=assistent` on Ustoz_paneli.html: open the assistant mode (`Panel.go('a-home')` or the panel's own mode switch) and hide the Ustoz/Assistent switch so the assistant cannot leave the mode.
The panels are self-contained builds (fonts, kit, Lucide inline) — never edit their content; all adaptations live in `adapter.js`.

## 7. Bots (python-telegram-bot 22.8, async)

Both bots run in `main.py` (manual lifecycle: `async with app:` → `start()` → `updater.start_polling(drop_pending_updates=True)`), plus the aiohttp server and tunnel in the same loop. Bot texts Uzbek, no emoji.

**Student bot**
- `/start [payload]` → upsert user → "Salom, {ism}!\n\nMuhammadamin fonetika kursiga xush kelibsiz. Bu yerda 36 ta dars slaydlari, video darslar va mashqlar bor.\n\nPastdagi tugma orqali darslarni oching." + inline `web_app` button "Darslarni ochish" (`{base}/app/`, payload `dars8` → `?dars=8`).
- `/darslar`, `/video` (→ `?tab=video`), `/yordam`.
- On start: `set_my_commands`, `set_chat_menu_button(MenuButtonWebApp("Darslar", WebAppInfo(base + "/app/")))`, `set_my_description`, `set_my_short_description`.
- Daily 19:00 (UTC+5) reminder to users with `eslatma` on, no XP today and last_seen ≤ 14 days ago: "Bugungi darsni davom ettiramizmi? Seriyangiz: {n} kun." + web_app button. Pace ~20 msg/s; ignore `Forbidden`.
- Provides `send_pdf(user_id, dars)` for the API (cache `file_id`).

**Staff bot**
- Pairing: if the `staff` table is empty, a 6-digit `ulash_kodi` is generated (saved in settings and `data/holat.json`). The owner sends `/start KOD` or just `KOD` → becomes `ceo`; the code is cleared.
- `/start t_<code>` → redeem invite (role, single use, 48 h) → welcome; notify CEOs.
- `/start` for staff → "Salom, {ism}! Rolingiz: {rol}." + web_app button "Boshqaruvni ochish" (`{base}/staff/`); non-staff → "Bu bot faqat Muhammadamin xodimlari uchun."
- `/taklif admin|ustoz|assistent` (ceo) → link; `/xodimlar` (ceo); `/ochiq [n]` (ceo, admin, ustoz) show/set; `/statistika` → short text summary.
- Menu button "Boshqaruv" → `{base}/staff/`. Daily 21:00 summary to CEOs (new students, active, lessons done).

## 8. Process, config, launchers

- `server/config.py`: ROOT paths, `PORT = 8790`, `BREND = "Muhammadamin"`, `PDF_DIR`, `TZ = timezone(timedelta(hours=5))`, `SINOV_TALABA_TOKEN = "1111111111:SINOVtalabaAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"`, `SINOV_XODIM_TOKEN = "2222222222:SINOVxodimBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"` (also in `tools/sinov_initdata.py`).
- `server/.env` keys: `TALABA_BOT_TOKEN`, `XODIM_BOT_TOKEN`.
- `python server/main.py` — production: requires `.env`; starts web, tunnel (`server/bin/cloudflared.exe tunnel --url http://127.0.0.1:8790 --no-autoupdate`, parse `https://*.trycloudflare.com` from stderr like `C:\Users\N.M\.claude\telegram-bot\panel.py`; before starting, kill only cloudflared processes whose executable path is under ROOT), both bots; writes `data/holat.json` `{"pid","boshlangan","url","talaba_bot","xodim_bot","ulash_kodi","xato"}`; single instance via `data/main.pid`; logs to `log/server.log` (rotating 2 MB × 3).
- `python server/main.py --sinov [--port 8791] [--db data/sinov_X.db] [--seed]` — no tunnel, no bots, sinov tokens; `--seed` fills the DB with staff 900001 ceo "Muhammad Amin", 900002 admin "Nodira Salimova", 900003 ustoz "Dilnoza Karimova", 900004 assistent "Bekzod Aliyev" and ~15 sample students (ids 800001–800015, deterministic names/progress over the last 14 days; 800001 = "Aziza Karimova" @aziza_k with uslub null). `/api/s/pdf` does not send in sinov.
- `server/tokenlar.py` — hidden input (`getpass`) of the two tokens, regex `^\d{6,12}:[A-Za-z0-9_-]{30,60}$`, `getMe` for each, they must be two different bots, confirm before overwriting an existing `.env`, never echo tokens, print the bots' @usernames.
- `server/boshqar.py start|stop|holat` — start: if not running, launch `pythonw main.py` detached and hidden, wait ≤ 90 s for a fresh `holat.json` (same pid, url set) and print: talabalar boti link, xodimlar boti link, Mini App URL, and if `ulash_kodi` is set: "Xodimlar botiga shu kodni yuboring: 123456". stop: kill processes whose command line contains ROOT and `main.py`, plus cloudflared under ROOT. holat: print status.
- `.bat` files: `@echo off`, `chcp 65001 >nul`, `cd /d "%~dp0"`, call python, `pause`.

### 8.1 Permanent server (VPS, Ubuntu 24.04) — added 03.10
- `server/.env` key `NOON_PUBLIC_URL=https://<domain>` → prod mode skips the tunnel and uses that URL (Caddy terminates HTTPS → 127.0.0.1:8790). `main.py` PidLock uses `fcntl.flock` on Linux; `videolar.json` `fayl` may be relative to ROOT (`video/d02.mp4`).
- Layout on the server: `/opt/noon/{server,web,video,deploy,data,log,backup,venv}`, system user `noon`, systemd unit `deploy/noon.service` (Restart=always), `/etc/cron.daily/noon-backup` (sqlite `.backup`, keeps 30 days), ufw: SSH/80/443.
- `tools/deploy.py`: `kalit` (ed25519 `~/.ssh/noon_vps`, no passwords), `sozla IP DOMEN [--user U]` (uploads package = server/*.py + web + videos + deploy, runs `deploy/setup.sh`; never sends .env/db), `kochir --tasdiq` (stops local bots, uploads DB snapshot + secret.key + .env with NOON_PUBLIC_URL, starts remote, verifies, rolls back to local on failure, writes `data/KOCHIRILGAN.txt`), `yangila` (content/code update), `holat`, `zaxira`.
- After migration `boshqar.py start` refuses to run locally while `data/KOCHIRILGAN.txt` exists (two pollers → 409 Conflict).

## 9. Testing conventions
- `tools/tg_mock.js` — Telegram WebApp mock (given). Playwright: `page.add_init_script(path=…)` after `page.add_init_script(script="window.__TG_MOCK = {...}")`; block `telegram.org` (`route.abort()`), so the mock is used.
- `tools/sinov_initdata.py` — `make(token, user, auth_date=None)` returns a signed initData string (given).
- Browser: Playwright with `channel="msedge"` (fallback `"chrome"`); there are no bundled browsers.
- Each agent uses its own port and DB (`--port`, `--db data/sinov_<agent>.db`) and stops its server at the end (only processes it started).
- Screenshots go to `ROOT\_sinov\<agent>\` (create it); look at them with Read.
- Sequential unlock in UI tests: `_sinov/integration/q.py` `unlock(u, upto, skip=())` writes lessons 1..upto−1 as done directly into the sinov DB (`NOON_DB`, default `data/sinov_integration.db`), avoiding the event rate limit. `_sinov/integration/unlock_video.py` covers lock states, multi-video screens (4 variants × 360/390/430) and Edge playback of every video.

## 10. Owner change 03.10 — Phase 1: analytics, real admin panel, feature switches, tests

Owner approved (03.10, "tasdiqlayman"): replace the demo panels with a **real admin panel** (Telegram + desktop browser), track the **whole student journey** (sessions, screens, button clicks, device type), let the **CEO switch features off**, show **test results per question**. Phase 2 (later): duels + friend invites. Phase 3: in-app guide → voice-over → promo video. All rules of §0 still apply (Uzbek Latin, no emoji, Lucide only, verbatim course content, never print tokens, do not touch production: port 8790, data/noon.db, server/.env, data/holat.json, data/main.pid).

### 10.1 Roles (owner-approved)
| Section key | Uzbek name | ceo | admin | ustoz | assistent |
|---|---|---|---|---|---|
| `bosh` | Bosh sahifa | yes | yes | – | – |
| `oquvchilar` | O'quvchilar (+ student card + journey) | yes | yes | read | – |
| `voronka` | Voronka | yes | yes | – | – |
| `tugmalar` | Tugmalar va ekranlar | yes | yes | – | – |
| `qurilmalar` | Qurilmalar | yes | yes | – | – |
| `kurs` | Kurs | yes (edit) | yes (edit) | read | – |
| `testlar` | Testlar | yes | yes | read | – |
| `xodimlar` | Xodimlar | yes | – | – | – |
| `funksiyalar` | Funksiyalar | yes | – | – | – |
| `jurnal` | Amallar jurnali | yes | yes | – | – |
`assistent` → admin panel 403 "Bu bo'lim sizga ochiq emas". **Ustoz can no longer change open lessons** (`OCHISH_ROLLARI = ("ceo","admin")`). The server enforces every row (403 `{"xato": "Bu bo'lim sizga ochiq emas"}`); the UI only hides.

### 10.2 Database additions (server/db.py; `CREATE TABLE IF NOT EXISTS`, existing data untouched)
```sql
CREATE TABLE sessions (id TEXT PRIMARY KEY,            -- client UUID, one per Mini App open
  user_id INTEGER NOT NULL, started_at TEXT NOT NULL, last_at TEXT NOT NULL, ended_at TEXT,
  platform TEXT, tg_version TEXT, os TEXT, device TEXT,  -- device: 'telefon'|'planshet'|'kompyuter'|'brauzer'|'nomalum'
  screen TEXT, scheme TEXT, uslub TEXT, rejim TEXT, ua TEXT,
  screens INTEGER NOT NULL DEFAULT 0, clicks INTEGER NOT NULL DEFAULT 0);
CREATE INDEX sessions_user ON sessions(user_id, started_at);  CREATE INDEX sessions_at ON sessions(started_at);
CREATE TABLE ui_events (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, user_id INTEGER NOT NULL,
  at TEXT NOT NULL, kind TEXT NOT NULL,                   -- 'screen'|'click'|'end'|'resume'
  name TEXT NOT NULL, ref TEXT, screen TEXT, dur_ms INTEGER);
CREATE INDEX ui_events_sess ON ui_events(session_id, id); CREATE INDEX ui_events_kind ON ui_events(kind, name, at);
CREATE INDEX ui_events_user ON ui_events(user_id, at);
CREATE TABLE test_answers (user_id INTEGER NOT NULL, dars INTEGER NOT NULL, try_no INTEGER NOT NULL, q INTEGER NOT NULL,
  pick INTEGER, ok INTEGER NOT NULL, at TEXT NOT NULL, PRIMARY KEY (user_id, dars, try_no, q));
CREATE TABLE audit (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, staff_id INTEGER NOT NULL,
  action TEXT NOT NULL, detail TEXT);                     -- detail = JSON
CREATE TABLE login_links (code TEXT PRIMARY KEY, staff_id INTEGER NOT NULL, created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL, used_at TEXT);
```
Feature switches live in `settings` key `features` (JSON). `test_done` writes one `test_answers` row per question (try_no = tests.tries after the update). Old tests have no per-question data — the UI says "Savollar bo'yicha natija 03.10 dan keyingi urinishlardan".

### 10.3 Feature switches (`config.FUNKSIYALAR`, ordered; default all `true`)
| key | nomi | effect when `false` |
|---|---|---|
| `reyting` | Reyting | student app hides the rating tab/cards; `GET /api/s/rating` → 403 |
| `video` | Video darslar | app hides the video tab and lesson video items; `/media/video/*` → 404 |
| `test` | Mini testlar | app hides "Mashq" items; `test_done` → 403 |
| `ball` | Ball, seriya va kunlik maqsad | app hides XP/streak/goal UI (server still counts) |
| `uslub` | Manzara tanlash (05.10; was "Uslub tanlash" / "Ko'rinish tanlash") | app hides the manzara picker, the manzara rotates on every launch; users without a style get `game` (old clients) |
| `eslatma` | Kunlik eslatma (19:00) | `student_bot.job_eslatma` sends nothing |
| `hisobot` | Kunlik hisobot (21:00) | `staff_bot.job_hisobot` sends nothing |
| `duel` | Duellar | phase 2 (reserved) |
| `taklif` | Do'st taklif qilish | phase 2 (reserved) |
| `qollanma` | Qo'llanma | phase 3 (reserved) |
403 text for switched-off features: `{"xato": "Bu funksiya hozircha o'chirilgan"}`.

### 10.4 Student API additions
- `/api/s/me` response gains `"features": {"reyting": true, ...}` (all keys of 10.3).
- `POST /api/s/track` (student auth) body:
  `{"sid": "<uuid4>", "device": {"platform": "android", "version": "8.0", "w": 412, "h": 915, "dpr": 2.6, "scheme": "light", "ua": "<navigator.userAgent ≤ 300>"}, "events": [{"t": 1759480000000, "k": "screen"|"click"|"end"|"resume", "n": "darslar", "r": "8", "s": "bosh", "d": 5300}]}`
  - `device` is required on the first call of a session (creates the `sessions` row; `uslub`/`rejim` copied from the user's prefs) and optional afterwards. ≤ 100 events per call, ≤ 30 calls/min/user (429), body ≤ 64 KB. `sid` must match `^[0-9a-f-]{36}$` and belong to the caller (else 400). `t` (client ms) is used if within ±10 min of server time, else server time. `n` ≤ 40 chars `[a-z0-9_-]`, `r` ≤ 40, `s` ≤ 40, `d` 0–86 400 000. Updates `last_at`, `screens`/`clicks` counters, `ended_at` on `end` (cleared on `resume`). → `{"ok": true}`.
  - Device classification (server, `db.classify_device`): platform `android` → os "Android", device `planshet` if min(w,h) ≥ 600 else `telefon`; `ios` → os "iOS", `planshet` if UA has "iPad" or min(w,h) ≥ 700 else `telefon`; `tdesktop` → `kompyuter`, os from UA (Windows/macOS/Linux, else "Kompyuter"); `macos` → `kompyuter`, "macOS"; `weba`/`webk`/`web` → `brauzer`, os from UA; anything else → `nomalum`. Human label `device_label`: "Android telefon", "Android planshet", "iPhone", "iPad", "Windows kompyuter", "Mac", "Linux kompyuter", "Telegram Web (brauzer)", "Noma'lum".
- **05.10 (NUQTA ko'rinishi):** `device` also carries `"manzara"` (`sahro|voha|shahar|qahva|xattot|shom` — shown on this launch), `"mavzu"` (`kun|tun` — actually applied) and `"aylan"` (bool — manzara rotates on every launch; also `true` when the `uslub` switch is off). Stored in `sessions.manzara TEXT, mavzu TEXT, aylan INTEGER` (added on startup by `Store.init` with a guarded `ALTER TABLE … ADD COLUMN`; rows before 05.10 stay NULL). An invalid value drops only that field (never 400). A later `device` updates `mavzu` (and `scheme`); `manzara`/`aylan` are only filled while NULL (session manzara = the one shown at launch; changes inside a session are the `set-manzara` / `set-aylanish` / `set-rejim` clicks).
- Student app (web/app) sends: a new `sid` (crypto.randomUUID) on every launch; `screen` on every screen change (`n` = screen key: tabs `bosh`,`darslar`,`video`,`reyting`,`profil`, nested `dars`,`kitob`,`player`,`mashq`,`natija`, sheets `sheet-<name>`, onboarding `ob-<step>`; `r` = lesson n / video id; `d` = ms spent on the previous screen); `click` for every `[data-act]` activation (`n` = data-act, `r` = data-n | data-v | data-i, `s` = current screen); `end` on `visibilitychange→hidden`/`pagehide` and `resume` when visible again. Queue + flush every 10 s, at 20 events, and on hide (`fetch(..., {keepalive: true})`). Tracking failures are silent and never block the UI. Respects `features` (hide switched-off UI).

### 10.5 Admin panel — `web/admin/` (index.html, admin.css, admin.js; vanilla, no build, no external CDNs)
- Served at `GET /admin/` and `/admin/{file}` (static, same headers as /staff). The **staff bot menu button and /start button now open `{base}/admin/`** (the demo panels are removed from the staff bot/menu; files stay on disk).
- Auth: inside Telegram → `X-Init-Data` (staff bot); in a browser → cookie. Staff bot command **`/kirish`** (roles ceo/admin/ustoz) creates a `login_links` code (`secrets.token_urlsafe(24)`, 10 min, single use) and replies with an inline URL button "Admin panelni ochish" → `GET /admin/kirish?k=CODE` → validates, marks used, sets cookie `noon_admin=<panel token>` (HttpOnly, SameSite=Lax, Path=/, Max-Age 43200, `Secure` when the request came over HTTPS / `X-Forwarded-Proto: https`) and 302 → `/admin/`; invalid/expired/used → small Uzbek HTML page "Havola eskirgan. Xodimlar botiga /kirish deb yozing." The API accepts the cookie as a third auth method; cookie-authenticated **POST** requests must carry `X-Requested-With: noon` (CSRF), else 403. `POST /api/x/logout` clears the cookie.
- Design: **NUQTA UI since 05.10 (§13)**; before that NOON UI (same visual language as `web/staff/p/Admin_paneli.html`: sidebar with groups, top bar, white 16px cards, lime .tbar). Be Vietnam Pro from `/shared/fonts.css`, Lucide sprite `/shared/icons.svg`. Desktop-first (≥ 1100 px sidebar), tablet, and phone/Telegram (≤ 640 px: drawer menu, stacked cards, tables become cards). Charts: inline SVG, single-series bars/lines, tooltips, accessible table fallback. Sidebar groups: **Boshqaruv** (Bosh sahifa, O'quvchilar, Voronka, Tugmalar, Qurilmalar), **O'quv jarayoni** (Kurs, Testlar), **Tizim** (Xodimlar, Funksiyalar, Amallar jurnali). Brand "Muhammadamin · Admin panel". Logout button in browser mode.

### 10.6 Staff API additions (all `GET` unless noted; role table 10.1)
- `GET /api/x/me` → `{"user": {...}, "role": "ceo", "sections": ["bosh", ...], "can_edit": {"kurs": true, "funksiyalar": true, "xodimlar": true}, "features": {...}, "brend": "Muhammadamin", "browser": true|false}`
- `GET /api/x/overview?days=14` → existing `/api/x/stats` fields + `"active_now"` (sessions with last_at ≤ 5 min ago), `"sessions_today"`, `"avg_session_min"` (today), `"devices": [{"label": "Android telefon", "users": 12}]` (top 5, by latest session per user, last 30 days), `"live": [{"name","screen_label","device_label","since"}]` (≤ 10 active now).
- `GET /api/x/students?q=` → existing fields + `"device_label"`, `"sessions"` (count), `"last_session_at"`; since 06.10 also `"manzara"`, `"mavzu"` (latest ko'rinish, null if unknown — §10.7).
- `GET /api/x/student?id=` → `{"user", "prefs", "stats": {xp, streak, best_streak}, "devices": [{"label","os","platform","tg_version","screen","last_at","sessions"}], "lessons": [{"n","nomi","seen","slaydlar","done_at","started_at"}], "tests": [{"dars","best","total","tries","last_answers": [{"q","pick","ok"}]}], "videos": [{"id","nomi","pos","davomiylik","done_at"}], "sessions": [{"id","started_at","dur_s","device_label","screens","clicks","ended": bool}] (last 50)}`
- `GET /api/x/session?id=` → `{"session": {...}, "user": {"id","name"}, "timeline": [{"at","kind","name","label","ref","screen","screen_label","dur_ms"}]}` (≤ 2000, chronological). Labels come from `server/yorliqlar.py` (`EKRAN_NOMI`, `TUGMA_NOMI` dicts of Uzbek labels for every screen key and every `data-act` used in web/app/app.js; unknown → the raw key).
- `GET /api/x/funnel?days=30` → `{"steps": [{"key","nomi","users"}]}` for users who joined in the period: `kirdi` (Ilovaga kirdi), `tanishuv` (Tanishuvni tugatdi; was `uslub` "Uslub tanladi" until 05.10), `d1_boshladi`, `d1_tugatdi`, `t1` (1-dars testini yechdi), `d2_boshladi`, `d5_tugatdi`, `d10_tugatdi`, `d20_tugatdi`, `d36_tugatdi`. Plus `"lessons": [{"n","started","done"}]` (all 36, all users).
  - **05.10 (owner, "1 ha"): `tanishuv` replaces `uslub`** — the NUQTA student app has no style choice and never sends `uslub`, so that step read 0 for new users. A user has finished the first-launch onboarding when he has a `ui_events` click `ob-done` ("Boshlash") or `ob-skip` ("O'tkazib yuborish") at any time, **or** (legacy: before tracking / NUQTA) `users.uslub IS NOT NULL`. Implementation (`Store.funnel`, `Store.TANISHUV_TUGMALAR`): one non-correlated `u.id IN (SELECT user_id FROM ui_events INDEXED BY ui_events_kind WHERE kind='click' AND name IN ('ob-done','ob-skip'))` — evaluated once, reads only those rows. The admin UI takes the label from `nomi` (no hard-coded keys). Caveat: while the `uslub` switch ("Manzara tanlash") is off, `/api/s/me` returns `uslub: "game"` for users without one, so the app skips the onboarding and such new users are not counted here. Seed: students who joined in the NUQTA days (`SEED_KORINISH_KUN`) get the NUQTA onboarding in their first session (`ob-salom` → `ob-korinish` [+ `set-manzara` for `SEED_MANZARA`, `set-rejim`] → `ob-qanday` → `ob-ball` → `ob-done`; `SEED_TANISHUV_SKIP` 800011, 800015 press `ob-skip` on `ob-qanday`), older join days keep the old flow (`ob-uslub`); 800001 and 800007 (legacy, no `uslub`) are not counted (seed: 13 of 15). Tests: `tools/test_admin_api.py` (unit with a temp DB + API vs DB), `_sinov/admin/test_admin_ui.py` (label).
- `GET /api/x/clicks?days=7` → `{"top": [{"name","label","screen","screen_label","count","users"}] (≤ 50), "screens": [{"name","label","views","users","avg_ms"}], "daily": [{"day","clicks","views"}]}`
- `GET /api/x/devices?days=30` → `{"users": N, "device": [{"key","label","users"}], "os": [...], "platform": [...], "tg_version": [...], "screen": [...] (top 10), "scheme": [...]}` — each user counted once by their latest session in the period.
- **05.10 — `korinish`** (replaces the obsolete "Uslub tanlovi" chart; `styles`/`modes` stay for old clients) in `GET /api/x/overview` (period = `days`, default 14), `GET /api/x/devices` (period = `days`, default 30) and, since 06.10, `GET /api/x/stats` (period = `days`, default 14; staff app, all 4 roles — see §10.7): `{"days", "since", "users", "manzara": [{"key","label","users","sessions"}], "tanlov": {"aylan","tanlangan"}, "mavzu": {"kun","tun"}}`. `manzara` always has the 6 keys (labels Sahro … Shom), sorted by sessions desc → users desc → app order. `sessions` and `mavzu` count sessions started in the period; `users`, `manzara[].users` and `tanlov` count each user once by the latest session in the period that has a manzara (ties: later insert). `since` = first session with a manzara (any period) or null. Session brief (`/api/x/session`, `student.sessions[]`) also returns `manzara`, `mavzu`, `aylan` (bool or null). Seed: sessions of the last 7 days carry ko'rinish (6 students in `SEED_MANZARA` fix a manzara after their first such session, the rest rotate; mavzu from rejim, `auto` by start hour), older ones NULL. Tests: `tools/test_korinish.py`.
- **05.10 — admin NUQTA additions (all additive; tests: `tools/test_korinish.py`, `tools/test_admin_api.py`):**
  - `korinish.soat`: 24 items `{"hour", "opens"}` (hour 0–23, Tashkent) — **all** sessions started in the period (also those without a manzara), from `substr(started_at, 12, 2)` (times are stored with `+05:00`). `korinish.manzara[].tanlagan` = users counted in `users` whose latest session had `aylan = 0` (chose this manzara themselves); Σ tanlagan = `tanlov.tanlangan`.
  - `/api/x/session` timeline items gain `ref_label` (`ref` stays raw): duel id (in `duels`, the session user is a participant) → rival `short_name` + " bilan" ("Kamola Y. bilan"); video id → "N-dars videosi" ("N-dars K-videosi" when the lesson has several videos); a digit `ref` on a `screen` event or on the clicks `lesson`, `quiz`, `kitob`, `vids`, `qz-retry` (`yorliqlar.DARS_REF_TUGMALAR`) → "N-dars"; anything else (option index of `pick`, tab names, …) → null.
  - `/api/x/clicks` `top[]` gains `ref_label` = `yorliqlar.qiymat_nomi(name, ref)` (tab → screen name, set-manzara → "Sahro", set-rejim → "Tungi", lesson → "8-dars"; null when no ref).
  - `/api/x/overview` gains `oldingi` `{"active_7d", "new_7d"}` (the previous week: 8–14 days ago, for the "+4 o'tgan haftaga nisbatan" KPI lines), `duels` `{"days", "total", "decided", "draws", "active", "expired"}` (duels created in the period; same definitions as `/api/x/duels`: decided = finished − draws) and its `recent` (≤ 20, newest first) now also contains finished duels: `{"name", "kind": "duel_done", "ref": "Kamola Y. bilan", "natija": "4:3", "result": "yutdi"|"yutqazdi"|"durrang", "duel_id", "at"}`. `/api/x/stats` (old /staff app) gets no duels (but see `korinish` below, 06.10).
  - Labels: `config.FUNKSIYALAR` `uslub` = "Manzara tanlash" (owner, 05.10); `yorliqlar` `ob-korinish` = "Tanishuv: manzara tanlash".
- `GET /api/x/tests` → `{"since": "<first test_answers.at or null>", "lessons": [{"dars","nomi","has_test","takers","attempts","avg_best","perfect","hardest": {"q","wrong_pct"}|null}]}`
- `GET /api/x/test?dars=n` → `{"dars","nomi","savollar": [verbatim test JSON questions + {"answers","wrong_pct","picks":[a,b,c,d]}], "students": [{"id","name","best","total","tries","updated_at"}]}`
- `GET /api/x/dropoff?dars=n` → `{"slaydlar": 15, "seen": [{"idx", "users"}]}` (how many users saw each slide).
- `GET /api/x/features` → `{"features": {...}, "meta": [{"key","nomi","tavsif","bosqich": 1|2|3}]}`; `POST /api/x/features` `{"key","on": bool}` (ceo) → `{"ok": true, "features": {...}}`.
- `GET /api/x/audit?limit=200` → `{"items": [{"at","staff_name","action","label","detail"}]}`. Written for: open lessons change, feature switch, invite created, staff removed, /kirish login.
- Existing `stats`, `course`, `open`, `invite`, `staff`, `staff/remove` stay (old /staff app keeps working).
- `seed()` (sinov only) also fills sessions/ui_events (≈ 3–8 sessions per sample student over 14 days, realistic screen/click sequences, mixed devices) and test_answers for the sample test takers, so the admin panel can be built and screenshotted against `--sinov --seed`.

### 10.7 Server implementation notes (server agent, 03.10 — clarifications, all backward compatible)
- **Auth order** for `/api/x/*`: `X-Init-Data` → `X-Staff-Token` → cookie `noon_admin`. Role always from the DB. Bad/expired cookie → 401 "Kirish muddati tugagan. Xodimlar botiga /kirish deb yozing." Cookie + non-GET without `X-Requested-With: noon` → 403. `POST /api/x/logout` needs that header too (no auth needed).
- **Sections**: new endpoints → 403 "Bu bo'lim sizga ochiq emas"; edit attempt on a read-only section (ustoz → `/api/x/open`) → 403 "Bu amal uchun ruxsatingiz yo'q". Mapping: overview=bosh · student, session=oquvchilar · funnel=voronka · clicks=tugmalar · devices=qurilmalar · tests, test=testlar · dropoff=kurs · features GET/POST=funksiyalar · audit=jurnal. `/api/x/me` → 403 for assistent; extra fields `rol_nomi`, `access` `{section: "edit"|"read"}`.
- Old endpoints `stats`, `course`, `students` stay open to all four roles (old `/staff` app, incl. assistent); `students` gains `device_label`, `sessions`, `last_session_at`.
- **06.10 (owner, "1 ha") — Ko'rinish for the staff app (§6.1), all additive, old fields (`styles`, `modes`, `uslub`, `rejim`) kept:** `GET /api/x/stats` accepts `?days=` (1–90, default 14; invalid → 400, same as overview) — it sets the `daily` length and the new **`korinish`** object = `Store.korinish_report(now, days)`, identical to `/api/x/overview` `korinish` for the same period (`days`, `since`, `users`, `manzara[6]` incl. `tanlagan`, `tanlov`, `mavzu`, `soat[24]`). Open to all four roles (ustoz/assistent included — no personal data). `GET /api/x/students` rows gain **`manzara`** and **`mavzu`** = the values of the user's latest session (by `started_at`, ties: later insert) whose `manzara` is one of the 6 keys; `mavzu` null unless `kun`/`tun`; both null when the user has no such session (pre-05.10 sessions). One extra correlated subquery per listed user (`sessions_user` index). Production picks this up only after a restart; the staff frontend tolerates the old API (card hidden, no chips). Tests: `tools/test_korinish.py` (stats for 4 roles = independent calculation, `?days=7`, students vs DB, old DB → empty / null), `tools/test_admin_api.py` (exact stats fields = old + `korinish`, stats = overview korinish, students exact fields + `manzara`/`mavzu` vs DB), `tools/test_server.py` (students exact fields, stats korinish shape).
- **Track**: `sid` lowercase UUID. Whole call 400 only for a malformed payload (bad `sid`, `events` not a list, > 100 events, `device` not an object, first call without `device`, foreign `sid`); a single invalid event is skipped and the rest stored → `{"ok": true, "skipped": n}`. `device` may come on every call (accepted). For a `screen` event the stored `screen` = the screen that was **left** (server derives it from the session's previous `screen` event; client `s` only used for the first one) and `dur_ms` = time on it — so the app should send `d` = ms on the previous screen. `click`: `screen` = `s` or current screen. `end`/`resume`: `n` optional (defaults to current screen). `r` may be a number (stored as text); `d` may be fractional (rounded). Extra platforms: `android_x` → Android, `unigram` → Windows kompyuter. `sessions.screen` = "WxH" (CSS px, first call); later `device` only updates `scheme`. `ui_events.at` has milliseconds; session times are whole seconds.
- `test_answers.q` is **1-based** (question number); `pick` is the 0-based option index (NULL = unanswered).
- Features: `uslub` off → `/api/s/me` returns `prefs.uslub = "game"` for users with none (DB untouched); `video` off → only `/media/video/*` 404.
- `/kirish`: code = `token_urlsafe(24)` (32 chars), 10 min, single use, ≤ 20 per hour per staff; sent only as an inline **URL** button (never in the text — a link preview must not consume it). Invalid/used/expired → 403 HTML page. Staff bot `/ochiq`: ustoz may view, only ceo/admin may set. `/kirish` in `/yordam` and bot commands for ceo/admin/ustoz.
- Audit actions + detail: `open {from,to[,via:"bot"]}`, `feature {key,on}`, `invite {role,expires[,via]}`, `staff_remove {id,name,role}`, `kirish {}`; items also carry `id`, `staff_id`, `action_nomi`; `label` = full Uzbek sentence (`yorliqlar.amal_matni`).
- Extra response fields: overview `live[]` also `session_id`, `user_id`, `screen`, `last_at`; `active_now` = distinct users with a non-ended session seen ≤ 5 min ago. devices: `days`, `labels` (device_label split). funnel: `days`, `since`, `joined`; `kirdi` = joined users with a session or an app visit (`days` row). test: `test_nomi`; each question also `n` (1-based) and `skipped`. dropoff: `dars`, `nomi`, `started`, `done`. student: `sessions_total`; `lessons` = all 36, `videos` = all course videos (+ `dars`).
- Extra indexes: `sessions_last(last_at)`, covering `ui_events_vaqt(kind, at, name, screen, user_id, dur_ms)`, `test_answers_dars(dars, q, pick, ok)`, `slides_dars(dars, idx)`.
- Seed extras: lesson 1–3 mini tests for students who finished them, 7 audit rows, 3 sessions "live now" (800001, 800003, 800011; live for ≈ 2.5 min after the server starts).

## 11. Owner change 03.10 — Phase 2: duels and friend invites (owner-approved: async duels, +50 invite bonus)

Feature switches `duel` and `taklif` (§10.3) now take effect: when off → endpoints 403 `{"xato": "Bu funksiya hozircha o'chirilgan"}`, app hides the UI, bot ignores `duel_`/`ref_` start parameters (plain welcome instead). Hard rule kept: **duel questions only come from lessons BOTH players have completed** (`lessons.done_at`) and that have a test (`web/content/test/NN.json`) — never untaught material. Question/option text verbatim.

### 11.1 Rules
- **Async duel, 5 questions, 15 s per question.** Mode `random` (server picks a rival: another student active in the last 7 days who shares ≥ 1 completed tested lesson, not already in an unfinished duel with the challenger; prefer recently active) or `friend` (challenger gets a share link; the friend accepts by opening it).
- Each player plays once; order does not matter. A duel expires 24 h after creation if not both finished (status `muddati_otdi`, no ball).
- Score: more correct answers wins; tie → smaller total time (sum of ms) wins; equal → `durrang`. Ball: winner **+15**, draw **+5** each, loser 0 (counted in `days` XP like other ball; `events.kind = 'duel_done'`, ref = duel id).
- Per answer `ms` > 15 000 or missing → wrong. Server records `started_at` per player at `start`; a `finish` later than `started_at + 5×15 s + 30 s` scores 0 correct (late). Questions are sent only at `start` (never with the answer key).
- Limits: ≤ 10 new duels/day/user, ≤ 3 unfinished outgoing duels; random pick never chooses the same rival twice within 24 h.
- **Friend invite bonus**: a new user who first arrives via `ref_<code>` is linked to the inviter; when the invitee completes **lesson 1** (`lesson_done` dars 1), both get **+50** ball once (`events.kind = 'taklif_bonus'`), and the student bot messages the inviter: "Do'stingiz {ism} 1-darsni tugatdi: sizga va unga +50 ball." Self-invite and already-existing users are ignored.

### 11.2 Database (CREATE TABLE IF NOT EXISTS)
```sql
CREATE TABLE duels (id TEXT PRIMARY KEY,                  -- short random id [a-z0-9]{10}
  a_id INTEGER NOT NULL, b_id INTEGER NOT NULL,           -- a = challenger (or inviter in friend mode), b = rival
  mode TEXT NOT NULL,                                     -- 'random'|'friend'
  lessons TEXT NOT NULL, questions TEXT NOT NULL,         -- JSON: lesson list; [{"dars":8,"q":3}] (1-based q)
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
  a_started TEXT, a_done TEXT, a_answers TEXT, a_correct INTEGER, a_ms INTEGER,
  b_started TEXT, b_done TEXT, b_answers TEXT, b_correct INTEGER, b_ms INTEGER,
  status TEXT NOT NULL,                                   -- 'faol'|'tugadi'|'muddati_otdi'
  winner_id INTEGER, finished_at TEXT);
CREATE INDEX duels_a ON duels(a_id, created_at); CREATE INDEX duels_b ON duels(b_id, created_at);
CREATE TABLE duel_invites (code TEXT PRIMARY KEY, from_id INTEGER NOT NULL, created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL, used_by INTEGER, duel_id TEXT);
CREATE TABLE ref_codes (user_id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE);   -- 8 chars [a-z0-9]
CREATE TABLE referrals (invitee_id INTEGER PRIMARY KEY, inviter_id INTEGER NOT NULL, at TEXT NOT NULL, rewarded_at TEXT);
```

### 11.3 Student API (student auth; all respect the switches)
- `GET /api/s/duels` → `{"can": true|false, "reason": null|"Duel uchun avval kamida bitta darsni va uning testini tugating", "stats": {"played","won","lost","draw"}, "items": [{"id","mode","rival": {"id","name"}|null, "me_role": "a"|"b", "status": "sizning_navbat"|"raqib_navbati"|"tugadi"|"muddati_otdi", "my": {"correct","ms"}|null, "their": {"correct","ms"}|null (null until BOTH finished), "result": "yutdi"|"yutqazdi"|"durrang"|null, "xp": 0|5|15, "created_at","expires_at"}]}` (last 30, unfinished first).
- `POST /api/s/duel/new` `{"mode": "random"}` → `{"duel": item}` or 409 `{"xato": "Hozircha mos raqib topilmadi. Do'stingizni chaqirib ko'ring."}`; rival gets a bot message "{ism} sizni duelga chaqirdi. 24 soat ichida javob bering." with a WebApp button "Duelni ochish" → `/app/?duel=<id>`.
- `POST /api/s/duel/new` `{"mode": "friend"}` → `{"code", "link": "https://t.me/<studentbot>?start=duel_<code>", "share_text": "Fonetika kursida duelga chaqiraman: 5 savol, har biriga 15 soniya.", "expires_at"}` (invite valid 24 h, single use).
- `POST /api/s/duel/accept` `{"code"}` → creates the duel (a = inviter, b = caller) using lessons both completed → `{"duel": item}`; errors: own code 400 "O'zingizni chaqira olmaysiz", used/expired 410 "Taklif eskirgan", no common lesson 409 "Duel uchun ikkalangiz ham kamida bitta darsni va uning testini tugatgan bo'lishingiz kerak". Inviter gets a bot message "{ism} duelni qabul qildi." (+ button) when the duel is created.
- `POST /api/s/duel/start` `{"id"}` → `{"id","sec":15,"questions":[{"q","opts"}]}` (5 items, no `ok`/`izoh`; idempotent until finish; 409 if already finished).
- `POST /api/s/duel/finish` `{"id","answers":[{"pick":0..3|null,"ms":0..60000}]}` (exactly 5) → `{"duel": item, "xp_added": n, "review": [{"q","opts","ok","pick","izoh"}]}` (review shown to the player after finishing). When the second player finishes, both get their ball and the first player gets a bot message with the result ("Duel natijasi: siz yutdingiz 4:3" / "yutqazdingiz" / "durrang").
- `GET /api/s/taklif` → `{"link": "https://t.me/<studentbot>?start=ref_<code>", "share_text": "Arab tili fonetikasini telefoningizda o'rganing — Muhammadamin fonetika kursi.", "bonus": 50, "earned": 100, "friends": [{"name","joined_at","done1": bool, "rewarded": bool}]}`.
- `/api/s/me` additionally returns `"duel_pending": n` (duels where it is the caller's turn) for a badge.
- Student bot `/start duel_<code>` → message "Duelga taklif" + WebApp button → `/app/?duel_kod=<code>`; `/start ref_<code>` → normal welcome; the referral is stored if the user is new (create the `users` row from the Telegram user if missing).

### 11.4 Student app (web/app)
- **Duellar** screen (`duellar`, reachable from a Bosh card "Duel" with the pending badge and from Profil): stats row, "Yangi duel" sheet with two choices (Tasodifiy raqib / Do'stni chaqirish → Telegram share via `Telegram.WebApp.openTelegramLink('https://t.me/share/url?url=…&text=…')` + copy link), list of duels with status pills. `?duel=<id>` opens that duel; `?duel_kod=<code>` calls accept then opens it.
- **Duel play** (`duel`, r = id): like the quiz screen but with a 15 s countdown ring per question; tapping an option locks it and moves on after ~0.6 s (no hearts); at 0 s the question counts as unanswered. Then **duel result** (`duel-natija`, r = id): my score vs rival (or "Raqib hali o'ynamadi — natija kelganda bot xabar beradi"), ball, review of answers with `izoh`.
- **Do'stlarni taklif qilish** screen (`taklif`, from Profil and a Bosh card): personal link, Share + Copy buttons, bonus explanation, friends list with status.
- New tracking names (§10.4 style): screens `duellar`, `duel`, `duel-natija`, `taklif`, sheet `sheet-duel-yangi`; clicks `duel-new`, `duel-random`, `duel-friend`, `duel-open`, `duel-start`, `duel-pick`, `duel-share`, `duel-copy`, `taklif-open`, `taklif-share`, `taklif-copy`. Hidden entirely when the switch is off.

### 11.5 Staff API (admin panel; sections `duellar` and `takliflar` visible to ceo, admin; read-only)
- `GET /api/x/duels?days=30` → `{"days","total","finished","expired","draws","players","daily":[{"day","created","finished"}],"top":[{"id","name","played","won"}],"recent":[{"id","at","a":{"id","name","correct"},"b":{...},"result","status"}]}`
- `GET /api/x/referrals` → `{"total","rewarded","top":[{"id","name","invited","rewarded"}],"recent":[{"at","inviter","invitee","rewarded"}]}`
- `GET /api/x/student?id=` additionally returns `"duels": {"played","won","lost","draw"}`, `"invited_by": {"id","name"}|null`, `"invited": n`.
- `seed()` adds sample duels (finished, active, expired) and referrals.

### 11.6 Server implementation notes (server agent, 04.10 — clarifications, all additive)
- **finish validation**: `answers` = exactly N items (N = the duel's question count, normally 5), each `{"pick": 0..3 | null, "ms": integer 0..60000 | null/absent}`; `1234.0` is accepted, fractional ms / bool / strings → 400 (send `Math.round`). Timeout = `{"pick": null, "ms": 15000}`.
- **Scoring**: right = `pick == ok` AND `ms <= 15000` (ms absent → wrong, counted as 15000). Total time = Σ min(ms, 15000). Late finish (server time > `started + 105 s`) → 0 right, 75000 ms, `my.late = true` (response also `"late": true`).
- **start**: idempotent until finish (same questions, `started_at` unchanged); response adds `started_at`, `deadline` (= started + 105 s), `left_ms`, and per question `n`, `dars` (no `ok`/`izoh`). Errors: 404 not a participant, 409 already played, 410 "Duel muddati o'tgan". **finish** errors: 409 "Avval duelni boshlang", 409 "Siz bu duelni allaqachon o'ynagansiz", 410 expired.
- **Expiry**: `expires_at = created + 24 h`. A player who started before expiry may still finish inside his 105 s window; the other player then sees `muddati_otdi` and cannot start (410). Status is computed on every read (lazy); JobQueue job `duel_muddat` (hourly, first run 60 s after start; `--sinov`: an asyncio loop, hourly) writes `status='muddati_otdi'`, `finished_at = expires_at`. No messages, no ball.
- **Item extra fields**: `finished_at`, `lessons` (lesson numbers of the questions), `n` (question count), `started` (caller started), `rival_done` (rival already played), `my.late`. `GET /api/s/duels` extra: `invites` (caller's open friend links `{code, link, created_at, expires_at}`), `pending`, `limits` `{today, daily, open, max_open}`, `rules` `{savollar, sec, xp_win, xp_draw, hours}`; order: `sizning_navbat`, `raqib_navbati`, then the rest, newest first.
- **New `GET /api/s/duel?id=<id>`** → `{"duel": item, "review": [...] | null}` (review only after the caller finished) — for `?duel=<id>` and for results on another device. Review item: `{"n","dars","q","opts","ok","pick","ms","izoh","togri"}` (texts verbatim).
- **accept**: idempotent for the same accepter (same duel, no second bot message); unknown code → 410 "Taklif eskirgan"; malformed → 400. Duel id and duel invite code: `[a-z0-9]{10}`; ref code `[a-z0-9]{8}`. Creating a friend link requires ≥ 1 completed tested lesson (409, text = `reason`).
- **Limits**: new duels/day = random duels + friend links created today (Tashkent) ≤ 10 → 429; unfinished outgoing = active duels where the caller is `a` + open (unused, unexpired) friend links ≤ 3 → 429.
- **Random rival**: `last_seen` within 7 days, `blocked = 0`, not the caller, shares ≥ 1 completed tested lesson, no active duel with the caller (either direction), no random duel between the pair (either direction) in the last 24 h. Of the 30 most recently seen candidates, the 5 least busy (active duels they still have to play) are shuffled and the first with ≥ 3 common questions is taken.
- **Ball**: `days` + `events`: `duel_done` (ref = duel id, `info` "my:their", xp 0/5/15, one row per player), `taklif_bonus` (ref = the other user's id, xp 50, one row per player).
- **Invite bonus**: paid in the `lesson_done` (dars 1) transaction when the referral is unrewarded and `taklif` is on; while off nothing is paid — a later `lesson_done` dars 1 after re-enabling pays it (still once). `xp_added` stays the lesson XP (20); extra field `"taklif_bonus": 50`; `stats` include it. Referral linking: only when `/start ref_<code>` created the user; self / unknown / already linked / `taklif` off → ignored.
- **Bot**: `/start duel_<code>` valid → "Duelga taklif…" + "Duelni ochish" (`?duel_kod=`); unknown / used by someone else / expired → "Bu duel taklifi eskirgan…" + "Darslarni ochish"; own code → short explanation; `duel` off → plain welcome. Transactional messages (sent regardless of `eslatma`, in background tasks, never in `--sinov`): challenge → rival, "… duelni qabul qildi." → inviter, result → first finisher ("Duel natijasi: siz yutdingiz 4:3\nRaqib: X.\nSizga +15 ball.", button "Natijani ko'rish"), bonus → inviter (button "Ilovani ochish" → `?tab=profil`). Forbidden / "chat not found" → `users.blocked = 1` (excluded from random picks until the next `/start`).
- `/api/s/me.duel_pending` = 0 while `duel` is off.
- **Staff**: sections `duellar`, `takliflar` (group "Faollik", between Testlar and Xodimlar). `/api/x/duels` extra: `since`, `active`, `modes` `{random, friend}`; `recent[]` = `{"id","at","mode","a":{"id","name","correct","ms","done"},"b":{…},"result":"a"|"b"|"durrang"|null,"winner_id","status","finished_at","expires_at","lessons"}` (full names). `/api/x/referrals`: `inviter` / `invitee` = `{"id","name"}`, extra `bonus`, `earned`, `rewarded_at`. Student card extra: `duels.active`, `duels.expired`, `invited_by.at` / `.rewarded`, `invited_rewarded`, `taklif_xp`.
- **yorliqlar**: screens `duellar`, `duel`, `duel-natija`, `taklif`, `sheet-duel-yangi`, `sheet-duel-chiqish`; clicks of §11.4 + `duel-quit`, `duel-retry`, `taklif-retry`.
- **Seed**: duels `seedduel01`–`seedduel10` (every state; `seedduel09` is `faol` in the DB but already expired → lazy), friend links `seedinv001`–`seedinv006` (`seedinv001` open, Dilshod), ref codes `sd800001` (Aziza), `sd800002` (Jahongir), `sd800005` (Dilshod), 5 referrals (4 rewarded). Seeded sessions contain duel / taklif screens and clicks.

## 12. Owner change 04–05.10 — NUQTA UI (student app)
- The student Mini App uses the NUQTA UI design system (owner-approved demo `Dizayn\NUQTA demo\demo.html`). The O'yinli/Shisha style choice is removed; Profil has "Ko'rinish": manzara (sahro, voha, shahar, qahva, xattot, shom; rotate on every launch or fixed) + rejim (light/dark/auto, auto = by clock 06:00–18:59 day). Choice stored in Telegram CloudStorage (nq_manzara, nq_aylan) with localStorage fallback; server pref `rejim` unchanged, `uslub` no longer sent.
- Fonts (owner rule 05.10): Latin — Be Vietnam Pro (headings and text); Arabic — 'Sakkal Majalla','Noto Naskh Arabic'.
- Feature switch `uslub` = "Manzara tanlash" (05.10, owner; earlier "Ko'rinish tanlash") (off → manzara picker hidden, rotation continues). Tracking: screen `ob-korinish` ("Tanishuv: manzara tanlash"); clicks `set-manzara` (r = manzara), `set-aylanish` (r = on/off).
- Old NOON app backed up: `_sinov\student-app\orig_nuqta\` and `Desktop\MUHAMMAD AMIN\Eski ishlarim\Telegram ilova - web app (NOON, 04.10.2026)\`. Tests: `_sinov\integration\nuqta_ui.py` (sandbox `_sinov\nuqta\root`), others updated to manzara × kun/tun.
- Admin panel: NUQTA UI since 05.10 (§13). Staff app (`web/staff`): NUQTA UI since 05.10 (owner "2 ha", §6.1); demo panels `web/staff/p/*` stay NOON.

## 13. Owner change 05.10 — Admin panel in NUQTA UI
- Owner approved ("tasdiqlayman", 05.10) the demo `Dizayn\NUQTA admin demo\demo.html` (source `_manba\demo.src.html`) including its content changes: the `uslub` switch shown as "Manzara tanlash"; readable names in the session timeline (`ref_label`, §10.6); a "Duellar" card on Bosh sahifa; a "So'nggi o'zgarishlar" card (feature changes from the audit log) on Funksiyalar; the new **Ko'rinish** card (replaces the obsolete "Uslub va rejim" game/glass card): manzara popularity with scene thumbnails and "N kishi tanlagan", o'zi tanlagan vs har ochilganda almashadi, kunduzgi vs tungi, 24-hour opens chart with the night hours (19:00–05:59) shaded. The Ko'rinish card is on Bosh sahifa (period = the 14/30-day switch) and Qurilmalar (period = 7/30/90).
- Files: `web/admin/index.html`, `admin.css`, `admin.js` (vanilla, no build, no CDN) + new shared `web/shared/nuqta-tokens.css` (the 6 manzara × kun/tun tokens, same values as `web/app/app.css` §1) + existing `/shared/nuqta-sahnalar.js` (scenes) and `/shared/icons.svg` (Lucide sprite; `tools/ikonlar.py` re-run).
- Theme: `index.html` sets `<html data-v data-m>` before the first paint: the manzara rotates on **every open** (Sahro → Voha → Shahar → Qahva → Xattot → Shom → …; localStorage key `nuqta.admin.manzara`, separate from the student app's `nuqta.manzara` so staff devices do not shift the students' rotation statistics); mode by the local clock 06:00–18:59 kun, otherwise tun ("oy nuri"), re-checked every 60 s and when the page becomes visible. Telegram `setHeaderColor` / `setBackgroundColor` / `setBottomBarColor` and `<meta theme-color>` = the current `--bg` token. Greeting by the clock (Xayrli tong/kun/kech/tun).
- Layout: sidebar 256 px (≥ 761 px), single-column rows ≤ 1180 px, phone/Telegram ≤ 760 px: off-canvas menu (focus trapped, `visibility:hidden` when closed), 44 px tap targets, wide tables become cards. Every chart has a one-sentence takeaway (`p.take`), a "Jadval" table toggle and tooltips; numbers use tabular figures. All behaviour of §10.5 kept (roles, auth incl. `/admin/kirish` cookie + CSRF header, routes/deep links, period switches, live refresh every 30 s, Telegram BackButton, read-only roles).
- Tests: `_sinov/admin/test_admin_ui.py` (3 roles × 1440/1024/390-Telegram, all sections and nested views, actions, auth screens; NUQTA: WCAG contrast ≥ 4,5:1 of every visible text, no white/black/pink backgrounds, manzara rotation across opens, kun/tun by a mocked clock incl. switching while open, all 6 manzara × kun/tun, focus ring, readable timeline names). Old NOON admin backed up: `_sinov/admin/orig_nuqta/`, `Desktop\MUHAMMAD AMIN\Eski ishlarim\Telegram ilova - admin panel (NOON, 05.10.2026)\`; server files before this change: `_sinov/admin_nuqta/orig/`.
- ~~Known, not changed (owner decision needed): Voronka step `uslub` ("Uslub tanladi") counts `users.uslub`, which the NUQTA student app no longer sets — for new users this step will read 0 and look like the biggest loss.~~ Resolved 05.10 (owner): step `tanishuv` "Tanishuvni tugatdi" (§10.6).

## Jonli harakat (12.10.2026) - web/app/app.js, app.css (16-bo'lim)
Faqat transform va opacity, kutubxonasiz. Oxirgi holat - asosiy uslub, "from" kadr - boshlang'ich; prefers-reduced-motion'da oxirgi holat darhol ko'rinadi.
1. To'g'ri javob (mashq): variant bosilganda "press", xato variant "nudge", belgi "pop", 3 ta romb sachrashi, xatoda yurak "lose", progress chizig'i scaleX bilan o'sadi (duel o'yinidagi .qz-bar o'zgarmagan), pastki oyna .28 s kechikadi.
2. Kun seriyasi: dars tugaganda seriya oshgan bo'lsa (mergeEv -> S.skFx) "Dars tugadi" oynasida qum ustidan chiqayotgan quyosh, raqam 3 -> 4 g'ildiragi va bugungi romb.
3. Darslar yo'li: dars tugagach Darslar ekrani birinchi ochilganda (S.pathFx) tugagan dars belgisi "pop", keyingi dars to'ldiriladi, halqa to'lqini, hisoblagich "bump".
4. Duel natijasi: ball 0 dan sanaladi (reduced bo'lmasa), g'olib ko'tariladi, toj pop, ball chipi pop, javoblar qatori ketma-ket (--i). Faqat birinchi ko'rinishda (S.du.cu / S.du.cr).
Sinov: _sinov/animatsiya/kadr.py (port 8794, alohida baza), kadrlar/ papkasida birinchi/o'rta/oxirgi kadrlar va reduced-* nusxalari.

/* ============================================================
   Muhammadamin — xodimlar Mini App (Boshqaruv)
   Vanilla JS, build yo'q. API: /api/x/* (SPEC 4.2). Dizayn: NUQTA UI (05.10.2026; admin panel bilan bir xil):
   manzara index.html da tanlanadi (har ochilganda keyingisi, nuqta.staff.manzara), kun/tun soatga qarab.
   Bo'limlar: Bugun · Kurs · O'quvchilar · Panellar · Xodimlar (faqat CEO)
   ============================================================ */
(function () {
  'use strict';

  /* ---------------- 0. Yordamchilar ---------------- */
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const ic = (n, cls) => '<svg class="i' + (cls ? ' ' + cls : '') + '" aria-hidden="true"><use href="/shared/icons.svg#' + n + '"/></svg>';
  const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ESC[c]);
  const AR_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+(?:[\s\u00A0\u200C\u200D]+[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+)*/g;
  /* matn: HTML xavfsiz + arabcha bo'laklar <bdi dir="rtl" lang="ar"> ichida */
  const txt = (s) => esc(s).replace(AR_RE, (m) => '<bdi dir="rtl" lang="ar">' + m + '</bdi>');
  const NB = '\u00A0';
  const num = (n) => { const v = Math.round(Number(n) || 0); return (v < 0 ? '-' : '') + String(Math.abs(v)).replace(/\B(?=(\d{3})+(?!\d))/g, NB); };
  const dec = (n) => (Math.round(Number(n) * 10) / 10).toString().replace('.', ',');
  const pct = (a, b) => (b > 0 ? Math.round((Number(a) || 0) / b * 100) : 0);
  const pad2 = (n) => String(n).padStart(2, '0');
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  /* vaqt: Toshkent = doimiy UTC+05:00 */
  const TZ_MS = 5 * 3600 * 1000;
  const MON = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek'];
  const MONF = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];
  const WD = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba'];
  const WDS = ['Yak', 'Du', 'Se', 'Chor', 'Pay', 'Ju', 'Sha'];
  const tk = (ms) => new Date(ms + TZ_MS);
  const dkey = (ms) => tk(ms).toISOString().slice(0, 10);
  const tsOf = (iso) => (iso ? Date.parse(iso) : NaN);
  function rel(iso) {
    const t = tsOf(iso);
    if (!isFinite(t)) return '—';
    const d = tk(t), now = Date.now(), k = dkey(t);
    const hm = pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes());
    if (k === dkey(now)) return 'bugun, ' + hm;
    if (k === dkey(now - 864e5)) return 'kecha, ' + hm;
    return d.getUTCDate() + '-' + MON[d.getUTCMonth()] + (d.getUTCFullYear() !== tk(now).getUTCFullYear() ? ' ' + d.getUTCFullYear() : '');
  }
  function dshort(iso) {
    const t = tsOf(iso);
    if (!isFinite(t)) return '—';
    const d = tk(t);
    return d.getUTCDate() + '-' + MON[d.getUTCMonth()] + (d.getUTCFullYear() !== tk(Date.now()).getUTCFullYear() ? ' ' + d.getUTCFullYear() : '');
  }
  function dtime(iso) {
    const t = tsOf(iso);
    if (!isFinite(t)) return '';
    const d = tk(t);
    return d.getUTCDate() + '-' + MON[d.getUTCMonth()] + ', ' + pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes());
  }
  function dayP(day) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(day || '');
    if (!m) return null;
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    return { d: +m[3], m: +m[2] - 1, y: +m[1], wd: d.getUTCDay(), key: m[0] };
  }
  const todayLong = () => { const d = tk(Date.now()); return d.getUTCDate() + '-' + MONF[d.getUTCMonth()] + ', ' + WD[d.getUTCDay()].toLowerCase(); };

  /* ---------------- 0b. NUQTA mavzusi: manzara (index.html da tanlangan), kun/tun, sahnalar ---------------- */
  const H = document.documentElement;
  const NV = ['sahro', 'voha', 'shahar', 'qahva', 'xattot', 'shom'];
  const modeAt = () => { const h = new Date().getHours(); return h >= 6 && h < 19 ? 'kun' : 'tun'; };
  if (NV.indexOf(H.getAttribute('data-v')) < 0) H.setAttribute('data-v', 'sahro');
  if (!/^(kun|tun)$/.test(H.getAttribute('data-m') || '')) H.setAttribute('data-m', modeAt());
  /* [data-scene] ichiga manzara (o'lcham yoki rejim o'zgarsa qayta chiziladi; bezak - aria-hidden).
     Manzara - eng yaqin [data-v] dan (Ko'rinish kartasidagi kichik rasmlar o'z manzarasini chizadi), aks holda sahifaniki. */
  function scenes(scope) {
    if (typeof window.scene !== 'function') return;
    const night = H.getAttribute('data-m') === 'tun';
    $$('[data-scene]', scope).forEach((el) => {
      const w = Math.round(el.clientWidth), h = Math.round(el.clientHeight);
      if (!w || !h) return;
      const hv = (el.closest('[data-v]') || H).getAttribute('data-v');
      const v = NV.indexOf(hv) >= 0 ? hv : 'sahro';
      const key = v + '|' + w + 'x' + h + '|' + (night ? 1 : 0);
      if (el._k === key) return;
      el._k = key;
      try { el.innerHTML = window.scene(v, w, h, { focus: el.getAttribute('data-focus') || undefined, night }); } catch (e) { /* manzarasiz ham ishlaydi */ }
    });
  }
  const token = (n) => (getComputedStyle(H).getPropertyValue(n) || '').trim();

  /* ---------------- 1. Telegram ---------------- */
  const tg = (window.Telegram && window.Telegram.WebApp) || null;
  const ver = (v) => { try { return !!(tg && tg.isVersionAtLeast && tg.isVersionAtLeast(v)); } catch (e) { return false; } };
  const initData = (() => { try { return (tg && tg.initData) || ''; } catch (e) { return ''; } })();
  const inTg = !!(tg && (initData || (tg.platform && tg.platform !== 'unknown')));
  const hap = {
    sel() { try { if (ver('6.1')) tg.HapticFeedback.selectionChanged(); } catch (e) { /* yo'q */ } },
    tap() { try { if (ver('6.1')) tg.HapticFeedback.impactOccurred('light'); } catch (e) { /* yo'q */ } },
    ok() { try { if (ver('6.1')) tg.HapticFeedback.notificationOccurred('success'); } catch (e) { /* yo'q */ } },
    err() { try { if (ver('6.1')) tg.HapticFeedback.notificationOccurred('error'); } catch (e) { /* yo'q */ } },
  };
  /* Telegram sarlavha / fon / pastki panel rangi va <meta theme-color> = joriy manzaraning --bg tokeni */
  function themeColors() {
    const bg = token('--bg');
    if (!/^#[0-9a-f]{6}$/i.test(bg)) return;
    const m = $('meta[name="theme-color"]');
    if (m) m.setAttribute('content', bg);
    if (!tg) return;
    try { if (ver('6.9')) tg.setHeaderColor(bg); } catch (e) { /* yo'q */ }
    try { if (ver('6.1')) tg.setBackgroundColor(bg); } catch (e) { /* yo'q */ }
    try { if (ver('7.10')) tg.setBottomBarColor(bg); } catch (e) { /* yo'q */ }
  }
  /* sahifa ochiq turganda soat 06:00 / 19:00 dan o'tsa - rejim almashadi (60 s taymer va sahifaga qaytganda) */
  function themeTick() {
    const m = modeAt();
    if (m === H.getAttribute('data-m')) return;
    H.setAttribute('data-m', m);
    scenes();
    themeColors();
  }
  function tgSetup() {
    if (tg) {
      try { tg.ready(); } catch (e) { /* yo'q */ }
      try { tg.expand(); } catch (e) { /* yo'q */ }
    }
    themeColors();
    if (!tg) return;
    try { if (ver('6.1')) { tg.BackButton.onClick(onBack); tg.BackButton.hide(); } } catch (e) { /* yo'q */ }
  }
  function backBtn(show) {
    try { if (ver('6.1')) { if (show) tg.BackButton.show(); else tg.BackButton.hide(); } } catch (e) { /* yo'q */ }
  }
  function closeApp() {
    try { if (inTg && tg.close) { tg.close(); return; } } catch (e) { /* yo'q */ }
    toast('Oynani yopish uchun Telegram ichida oching');
  }

  /* ---------------- 2. Holat, saqlash ---------------- */
  const SKEY = 'noon_x', TKEY = 'noon_x_tab';
  const ss = {
    get(k) { try { return JSON.parse(sessionStorage.getItem(k) || 'null'); } catch (e) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* xotira yopiq */ } },
  };
  const S = {
    user: null, role: '', brend: 'Muhammadamin', token: '', panels: [],
    tab: 'bugun', seq: 0, series: 'active', seg: 'all', q: '', shown: 150,
    openDraft: null, saving: false, invRole: 'ustoz', invite: null, sheet: false, partOpen: {}, korTbl: false,
  };
  const C = { stats: null, course: null, kurs: null, kursLoaded: false, tests: {}, students: null, staff: null };

  /* ---------------- 3. API ---------------- */
  async function api(path, body, tokenOnly) {
    const h = { Accept: 'application/json' };
    if (body !== undefined) h['Content-Type'] = 'application/json';
    const useInit = !!initData && !tokenOnly;
    if (useInit) h['X-Init-Data'] = initData;
    else if (S.token) h['X-Staff-Token'] = S.token;
    let r;
    try {
      r = await fetch(path, { method: body !== undefined ? 'POST' : 'GET', headers: h, body: body !== undefined ? JSON.stringify(body) : undefined, cache: 'no-store', credentials: 'same-origin' });
    } catch (e) {
      const err = new Error("Server bilan aloqa yo'q. Internetni tekshiring.");
      err.status = 0;
      throw err;
    }
    let data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (r.status === 401 && useInit && S.token) return api(path, body, true);
    if (!r.ok) {
      const err = new Error((data && data.xato) || (r.status >= 500 ? "Serverda xatolik. Birozdan keyin qayta urinib ko'ring." : 'Xato: ' + r.status));
      err.status = r.status;
      throw err;
    }
    return data || {};
  }
  async function getJSON(url) {
    const r = await fetch(url, { cache: 'no-cache', credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }

  /* ---------------- 4. Umumiy bo'laklar ---------------- */
  const ROLE = {
    ceo: { label: 'CEO', icon: () => ic('crown') },
    admin: { label: 'Admin', icon: () => ic('shield-check') },
    ustoz: { label: 'Ustoz', icon: () => ic('presentation') },
    assistent: { label: 'Assistent', icon: () => ic('headphones') },
  };
  const roleOf = (r) => ROLE[r] || { label: String(r || ''), icon: () => ic('user-round') };
  const roleChip = (r) => '<span class="role r-' + esc(r) + '">' + roleOf(r).icon() + esc(roleOf(r).label) + '</span>';
  const AVC = ['', ' c2', ' c3', ' c4', ' c5'];
  const hsh = (s) => { let h = 7; for (const ch of String(s)) h = (h * 31 + ch.codePointAt(0)) >>> 0; return h; };
  const initials = (name) => String(name || '').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => Array.from(w)[0]).join('').toUpperCase() || '?';
  function avatar(name, photo, cls) {
    const ph = photo && /^https:\/\//.test(String(photo)) ? '<img src="' + esc(photo) + '" alt="" referrerpolicy="no-referrer" loading="lazy" onerror="this.remove()">' : '';
    return '<span class="av' + AVC[hsh(name) % 5] + (cls ? ' ' + cls : '') + '" aria-hidden="true">' + txt(initials(name)) + ph + '</span>';
  }
  const SIG = '<span class="nq-sig" aria-hidden="true"><i></i><i></i><i></i></span>';
  const brandHTML = () => '<div class="brand">' + SIG + '<div><b>' + esc(S.brend) + '</b><small>Boshqaruv</small></div></div>';
  const fullName = (u) => [u && u.first_name, u && u.last_name].filter(Boolean).join(' ') || 'Xodim';
  const segBtn = (act, v, cur, label, icon) => '<button type="button" data-act="' + act + '" data-v="' + v + '" aria-pressed="' + (cur === v) + '">' + (icon || '') + label + '</button>';
  const kpi = (lab, val, icon, foot) => '<div class="kpi"><div class="k-lab">' + icon + '<span>' + lab + '</span></div><div class="k-val">' + val + '</div><div class="k-foot">' + foot + '</div></div>';
  const emptyBox = (icon, title, text) => '<div class="empty">' + icon + '<b>' + title + '</b>' + (text ? '<span>' + text + '</span>' : '') + '</div>';

  function toast(msg, err) {
    const box = $('#toasts');
    if (!box) return;
    const t = document.createElement('div');
    t.className = 'toast' + (err ? ' err' : '');
    t.innerHTML = (err ? ic('circle-alert') : ic('circle-check')) + '<span></span>';
    t.querySelector('span').textContent = msg;
    box.appendChild(t);
    while (box.children.length > 3) box.firstChild.remove();
    setTimeout(() => t.remove(), 2900);
  }

  /* ---------------- 5. Oyna (sheet) ---------------- */
  function sheet(html, label) {
    const root = $('#sheetRoot');
    root.innerHTML = '<div class="sheet-back" data-act="sheetBack"><div class="sheet" role="dialog" aria-modal="true" aria-label="' + esc(label) + '"><div class="grab" aria-hidden="true"></div>' + html + '</div></div>';
    S.sheet = true;
    backBtn(true);
    const f = root.querySelector('.sheet-act .btn');
    if (f) f.focus();
  }
  function closeSheet() {
    const root = $('#sheetRoot');
    if (root) root.innerHTML = '';
    S.sheet = false;
    backBtn(false);
  }
  function onBack() { if (S.sheet) closeSheet(); }

  /* ---------------- 6. Grafik: bitta seriyali ustunlar ---------------- */
  function niceScale(v) {
    if (!(v > 0)) return { top: 4, step: 1, n: 4 };
    let best = null;
    [3, 4, 5].forEach((n) => {
      const raw = v / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
      const step = Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p);
      const k = Math.ceil(v / step - 1e-9), top = k * step;
      if (!best || top < best.top || (top === best.top && k < best.n)) best = { top, step, n: k };
    });
    return best;
  }
  /* o: {values, labels, full, now, fmt, extra, aria} + ixtiyoriy (Ko'rinish soatlari): h - balandlik, compact - o'qsiz
     (faqat eng katta qiymat yozuvi), bands: [[a, b]] - fon bo'laklari (ustun indeksida), ticks: [[i, matn, anchor]] -
     pastki yozuvlar ustunlar chegarasida, start - fokusda birinchi ko'rsatiladigan ustun */
  let activeChart = null;
  const chartRO = {};   // har grafik joyiga (host id) bitta ResizeObserver
  function barChart(host, o) {
    if (!host) return;
    host.innerHTML = '<div class="chart"></div>';
    const box = host.firstChild;
    const tip = document.createElement('div');
    tip.className = 'tip';
    tip.hidden = true;
    let cur = -1, geo = null, lastW = 0;
    const n = o.values.length;
    const first = () => (o.start != null ? o.start : o.now != null ? o.now : n - 1);
    function draw() {
      const W = Math.max(240, Math.round(box.clientWidth || host.clientWidth || 320));
      lastW = W;
      const H = o.h || (W < 560 ? 200 : 240);
      const pad = o.compact ? { l: 2, r: 2, t: 22, b: 24 } : { l: 30, r: 6, t: 24, b: 26 };
      const pw = W - pad.l - pad.r, ph = H - pad.t - pad.b;
      const max = Math.max(0, ...o.values);
      const sc = o.compact ? { top: Math.max(1, max), step: 1, n: 0 } : niceScale(max);
      const slot = pw / Math.max(1, n);
      const bw = Math.max(4, Math.min(24, slot * 0.62));
      const Y = (v) => pad.t + ph - (v / sc.top) * ph;
      const X = (i) => pad.l + i * slot + slot / 2;
      let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" height="' + H + '" role="img" tabindex="0" aria-label="' + esc(o.aria) + '">';
      (o.bands || []).forEach((b) => {
        s += '<rect class="band" x="' + (pad.l + b[0] * slot).toFixed(2) + '" y="' + (pad.t - 6) + '" width="' + ((b[1] - b[0]) * slot).toFixed(2) + '" height="' + (ph + 6) + '" rx="5"/>';
      });
      for (let k = 0; k <= sc.n; k++) {
        const v = k * sc.step, y = Math.round(Y(v)) + 0.5;
        s += '<line class="' + (k ? 'grid-l' : 'base-l') + '" x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + y + '" y2="' + y + '"/>';
        if (!o.compact) s += '<text class="ax" x="' + (pad.l - 7) + '" y="' + (y + 4) + '" text-anchor="end">' + num(v) + '</text>';
      }
      s += '<rect class="hl" x="0" y="' + pad.t + '" width="' + slot.toFixed(2) + '" height="' + ph + '" rx="6" visibility="hidden"/>';
      const lab = new Set();
      let mi = 0;
      o.values.forEach((v, i) => { if (v >= o.values[mi]) mi = i; });
      if (max > 0) lab.add(mi);
      if (o.now != null && o.now >= 0) lab.add(o.now);
      o.values.forEach((v, i) => {
        if (!(v > 0)) return;
        const x = X(i) - bw / 2, y0 = Y(0), y1 = Y(v), r = Math.min(4, bw / 2, y0 - y1);
        const f = (q) => q.toFixed(2);
        s += '<path class="bar" data-b="' + i + '" d="M' + f(x) + ' ' + f(y0) + 'V' + f(y1 + r) + 'Q' + f(x) + ' ' + f(y1) + ' ' + f(x + r) + ' ' + f(y1) + 'H' + f(x + bw - r) + 'Q' + f(x + bw) + ' ' + f(y1) + ' ' + f(x + bw) + ' ' + f(y1 + r) + 'V' + f(y0) + 'Z"/>';
      });
      lab.forEach((i) => { s += '<text class="vl" x="' + X(i).toFixed(2) + '" y="' + (Y(o.values[i]) - 7).toFixed(2) + '" text-anchor="middle">' + num(o.values[i]) + '</text>'; });
      if (o.ticks) {
        o.ticks.forEach((t) => { s += '<text class="ax" x="' + (pad.l + t[0] * slot).toFixed(2) + '" y="' + (H - 7) + '" text-anchor="' + (t[2] || 'middle') + '">' + esc(t[1]) + '</text>'; });
      } else {
        const every = slot < 18 ? 2 : 1;
        o.labels.forEach((l, i) => {
          if (every > 1 && (n - 1 - i) % every && i !== o.now) return;
          s += '<text class="ax' + (i === o.now ? ' now' : '') + '" x="' + X(i).toFixed(2) + '" y="' + (H - 8) + '" text-anchor="middle">' + esc(l) + '</text>';
        });
      }
      o.values.forEach((v, i) => { s += '<rect class="hit" data-i="' + i + '" x="' + (pad.l + i * slot).toFixed(2) + '" y="' + pad.t + '" width="' + slot.toFixed(2) + '" height="' + (ph + pad.b) + '"/>'; });
      s += '</svg>';
      box.innerHTML = s;
      box.appendChild(tip);
      geo = { X, Y, slot, pad, W };
      if (cur >= 0) show(cur);
    }
    function show(i) {
      if (!geo || i < 0 || i >= n) return;
      cur = i;
      activeChart = api_;
      $$('.bar.on', box).forEach((b) => b.classList.remove('on'));
      const b = box.querySelector('.bar[data-b="' + i + '"]');
      if (b) b.classList.add('on');
      const hl = box.querySelector('.hl');
      if (hl) { hl.setAttribute('x', (geo.pad.l + i * geo.slot).toFixed(2)); hl.setAttribute('visibility', 'visible'); }
      tip.textContent = '';
      const v = document.createElement('b');
      v.textContent = o.fmt(o.values[i]);
      tip.appendChild(v);
      const d = document.createElement('div');
      d.textContent = o.full[i];
      tip.appendChild(d);
      if (o.extra) {
        const x = document.createElement('div');
        x.className = 't2';
        x.textContent = o.extra(i);
        tip.appendChild(x);
      }
      tip.hidden = false;
      const w = tip.offsetWidth;
      tip.style.left = clamp(geo.X(i), w / 2 + 2, geo.W - w / 2 - 2) + 'px';
      tip.style.top = Math.max(geo.Y(o.values[i]) - 4, geo.pad.t + 4) + 'px';
    }
    function hide() {
      cur = -1;
      tip.hidden = true;
      $$('.bar.on', box).forEach((b) => b.classList.remove('on'));
      const hl = box.querySelector('.hl');
      if (hl) hl.setAttribute('visibility', 'hidden');
      if (activeChart === api_) activeChart = null;
    }
    const api_ = { hide, box };
    const pick = (e) => { const h = e.target && e.target.closest ? e.target.closest('.hit') : null; if (h) show(+h.dataset.i); };
    box.addEventListener('pointermove', pick);
    box.addEventListener('pointerdown', pick);
    box.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') hide(); });
    box.addEventListener('keydown', (e) => {
      const k = e.key;
      if (k === 'ArrowRight' || k === 'ArrowLeft' || k === 'Home' || k === 'End') {
        e.preventDefault();
        const base = cur < 0 ? first() : cur;
        show(k === 'Home' ? 0 : k === 'End' ? n - 1 : clamp(base + (k === 'ArrowRight' ? 1 : -1), 0, n - 1));
      } else if (k === 'Escape') hide();
    });
    box.addEventListener('focusin', () => { if (cur < 0) show(first()); });
    box.addEventListener('focusout', hide);
    draw();
    const key = host.id || 'chart';
    if (chartRO[key]) { chartRO[key].disconnect(); delete chartRO[key]; }
    if ('ResizeObserver' in window) {
      chartRO[key] = new ResizeObserver(() => { const w = Math.round(box.clientWidth); if (w && w !== lastW) draw(); });
      chartRO[key].observe(box);
    }
  }
  document.addEventListener('pointerdown', (e) => {
    if (activeChart && !(e.target instanceof Element && activeChart.box.contains(e.target))) activeChart.hide();
  }, true);

  /* ---------------- 7. Karkas va bo'limlar ---------------- */
  const TABS = [
    { id: 'bugun', label: 'Bugun', icon: ic('layout-dashboard') },
    { id: 'kurs', label: 'Kurs', icon: ic('book-open') },
    { id: 'oquvchilar', label: "O'quvchilar", icon: ic('graduation-cap') },
    { id: 'panellar', label: 'Panellar', icon: ic('panels-top-left') },
    { id: 'xodimlar', label: 'Xodimlar', icon: ic('users-round'), ceo: true },
  ];
  const tabsFor = () => TABS.filter((t) => !t.ceo || S.role === 'ceo');

  function shell() {
    const tabs = tabsFor(), u = S.user || {}, name = fullName(u);
    const navBtn = (t, cls) => '<button type="button" class="' + cls + '" data-tab="' + t.id + '" aria-current="false">' +
      (cls === 'tab' ? '<span class="ti">' + t.icon + '</span>' : '<span class="ni">' + t.icon + '</span>') + '<span>' + esc(t.label) + '</span></button>';
    $('#app').innerHTML =
      '<div class="shell">' +
        '<aside class="side" aria-label="Asosiy menyu">' + brandHTML() +
          '<nav class="snav" aria-label="Bo\'limlar"><span class="ng-lab">Boshqaruv</span>' + tabs.map((t) => navBtn(t, 'nav-item')).join('') + '</nav>' +
          '<div class="side-sc" aria-hidden="true"><div data-scene data-focus="thumb"></div></div>' +
          '<div class="side-foot"><div class="me">' + avatar(name, u.photo_url) + '<div><b>' + txt(name) + '</b><small>' + esc(roleOf(S.role).label) + (u.username ? ' · @' + esc(u.username) : '') + '</small></div></div></div>' +
        '</aside>' +
        '<div class="main">' +
          '<header class="top">' + brandHTML() + '<div class="top-me">' + roleChip(S.role) + avatar(name, u.photo_url, 'sm') + '</div></header>' +
          '<main class="page" id="page" tabindex="-1"></main>' +
        '</div>' +
      '</div>' +
      '<nav class="tabbar" style="--tabs:' + tabs.length + '" aria-label="Bo\'limlar">' + tabs.map((t) => navBtn(t, 'tab')).join('') + '</nav>';
    document.title = 'Boshqaruv · ' + S.brend;
    scenes();
  }

  function go(id) {
    const tabs = tabsFor();
    if (!tabs.some((t) => t.id === id)) id = 'bugun';
    if (S.sheet) closeSheet();
    if (id !== S.tab) { const tb = $('#toasts'); if (tb) tb.innerHTML = ''; }
    S.tab = id;
    ss.set(TKEY, id);
    $$('[data-tab]').forEach((b) => b.setAttribute('aria-current', b.dataset.tab === id ? 'page' : 'false'));
    render(id, false);
    window.scrollTo(0, 0);
  }

  function headHTML(sc) {
    const h = sc.head();
    return '<div class="ph"><div class="ph-t">' + (h.crumb ? '<div class="crumb">' + h.crumb + '</div>' : '') + '<h1>' + h.title + '</h1>' + (h.sub ? '<p>' + h.sub + '</p>' : '') + '</div>' +
      (sc.load ? '<div class="ph-actions"><button type="button" class="ib" data-act="refresh" aria-label="Yangilash" title="Yangilash">' + ic('refresh-cw') + '</button></div>' : '') + '</div>';
  }

  function render(id, force, quiet) {
    const sc = SCREENS[id];
    const page = $('#page');
    if (!sc || !page) return;
    if (force && !sc.load) force = false;
    const seq = ++S.seq;
    const has = sc.ready();
    if (!force) {
      page.innerHTML = '<div id="ph">' + headHTML(sc) + '</div><div class="stack" id="body">' + (has ? sc.html() : sc.skel()) + '</div>';
      if (has && sc.mount) sc.mount();
      scenes(page);
      if (has || !sc.load) return;
    }
    const body = $('#body'), rb = $('[data-act="refresh"]');
    if (has && body) body.classList.add('busy');
    if (rb) rb.classList.add('spin');
    sc.load(force).then(() => {
      if (seq !== S.seq) return;
      const b = $('#body');
      if (!b) return;
      b.classList.remove('busy');
      $('#ph').innerHTML = headHTML(sc);
      b.innerHTML = sc.html();
      if (sc.mount) sc.mount();
      scenes(b);
      S.rebooted = false;
      if (force && !quiet) toast('Yangilandi');
    }).catch((e) => {
      if (seq !== S.seq) return;
      const b = $('#body'), r2 = $('[data-act="refresh"]');
      if (r2) r2.classList.remove('spin');
      if (!b) return;
      b.classList.remove('busy');
      /* kirish eskirgan yoki rol o'zgargan bo'lishi mumkin: bir marta qayta kirib ko'ramiz (boot o'zi kerakli ekranni ko'rsatadi) */
      if ((e.status === 401 || e.status === 403) && !S.rebooted) { S.rebooted = true; boot(); return; }
      if (has) { toast(e.message, true); hap.err(); return; }
      b.innerHTML = '<div class="card err-card" role="alert"><span class="gate-ic crit">' + ic('wifi-off') + '</span><b>Ma\'lumot yuklanmadi</b><p class="cap" style="margin:0">' + esc(e.message) + '</p><button type="button" class="btn" data-act="retry">' + ic('refresh-cw') + 'Qayta urinish</button></div>';
    });
  }

  /* --- skeletlar --- */
  const skLines = (n) => Array.from({ length: n }, (_, i) => '<span class="sk sk-line" style="width:' + (92 - i * 13) + '%"></span>').join('');
  const skCard = (h) => '<div class="card"><span class="sk" style="height:' + (h || 120) + 'px"></span></div>';

  /* ======================= BUGUN ======================= */
  const KIND = {
    lesson_done: { icon: () => ic('book-check'), cls: '', text: (r) => (r ? r + 'ni tugatdi' : 'Darsni tugatdi') },
    video_done: { icon: () => ic('circle-play'), cls: 'k-video', text: (r) => (r ? r + ' videosini ko\'rdi' : "Video darsni ko'rdi") },
    test_done: { icon: () => ic('list-checks'), cls: 'k-test', text: (r) => (r ? r + ' testini topshirdi' : 'Testni topshirdi') },
    joined: { icon: () => ic('user-plus'), cls: 'k-user', text: () => 'Botga qo\'shildi' },
  };
  KIND.new_user = KIND.joined;
  KIND.start = KIND.joined;
  KIND.lesson = KIND.lesson_done;
  KIND.video = KIND.video_done;
  KIND.test = KIND.test_done;

  /* grafik xulosasi (bitta gap): oxirgi 7 kun o'rtachasi undan oldingi 7 kun bilan solishtiriladi */
  function takeDaily(daily, xp) {
    const v = daily.map((d) => Number(xp ? d.xp : d.active) || 0);
    const h = Math.floor(v.length / 2);
    const avg = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
    const a = Math.round(avg(v.slice(0, h)) * 10) / 10, b = Math.round(avg(v.slice(h)) * 10) / 10;
    const what = xp ? 'kunlik ball' : "kunlik faol o'quvchilar", unit = xp ? '' : ' ta';
    const k = v.length - h;
    if (a === b) return 'Oxirgi ' + k + ' kunda ' + what + ' o\'rtacha ' + dec(b) + unit + ' — oldingi ' + h + ' kun bilan bir xil.';
    return 'Oxirgi ' + k + ' kunda ' + what + ' o\'rtacha ' + dec(a) + (xp ? ' dan ' : ' tadan ') + dec(b) + (xp ? ' ga ' : ' taga ') + (b > a ? "ko'tarildi." : 'tushdi.');
  }

  function htmlBugun() {
    const s = C.stats || {};
    const st = Number(s.students) || 0;
    const daily = Array.isArray(s.daily) ? s.daily : [];
    const tday = daily[daily.length - 1] || null;
    const actVals = daily.map((d) => Number(d.active) || 0);
    const avg = actVals.length ? actVals.reduce((a, b) => a + b, 0) / actVals.length : 0;
    let mi = -1;
    actVals.forEach((v, i) => { if (mi < 0 || v >= actVals[mi]) mi = i; });
    const mp = mi >= 0 ? dayP(daily[mi].day) : null;
    const p = pct(s.active_today, st);

    const hero = '<section class="tint hero" aria-labelledby="heroK">' +
      '<div data-scene data-focus="card" aria-hidden="true"></div>' +
      '<div class="kick" id="heroK">Bugun faol</div>' +
      '<div class="big">' + num(s.active_today) + '<small>/ ' + num(st) + ' o\'quvchi</small></div>' +
      '<div class="h-bar"><div class="dbar" role="img" aria-label="O\'quvchilarning ' + p + ' foizi bugun faol"><span style="width:' + clamp(p, 0, 100) + '%"></span></div><b>' + p + '%</b></div>' +
      '<p class="h-line">Bugun to\'plangan ball: <b>' + num(tday ? tday.xp : 0) + '</b></p>' +
      '<div class="dstats"><div><b>' + dec(avg) + '</b><span>kunlik o\'rtacha</span></div>' +
      '<div><b>' + num(mi >= 0 ? actVals[mi] : 0) + '<small>o\'quvchi</small></b><span>eng faol kun' + (mp ? ' · ' + mp.d + '-' + MON[mp.m] : '') + '</span></div></div>' +
    '</section>';

    const tiles =
      kpi("O'quvchilar", num(st), ic('users'), "Talabalar botiga kirganlar") +
      kpi('7 kunda faol', num(s.active_7d), ic('activity'), pct(s.active_7d, st) + "% o'quvchi") +
      kpi('Yangi (7 kun)', num(s.new_7d), ic('user-plus'), 'Botga yangi kirganlar') +
      kpi('Tugatilgan darslar', num(s.lessons_done), ic('book-check'), "Barcha o'quvchilar bo'yicha") +
      kpi("O'rtacha ball", num(s.avg_xp), ic('gem'), "Bir o'quvchiga") +
      kpi("Ko'rilgan videolar", num(s.videos_done), ic('circle-play'), 'Topshirilgan testlar: ' + num(s.tests_done));

    const first = daily.length ? dayP(daily[0].day) : null, last = daily.length ? dayP(daily[daily.length - 1].day) : null;
    const range = first && last ? first.d + '-' + MONF[first.m] + ' — ' + last.d + '-' + MONF[last.m] : '';
    const rows = daily.map((d, i) => {
      const q = dayP(d.day);
      return '<tr' + (i === daily.length - 1 ? ' class="now"' : '') + '><td>' + (q ? WDS[q.wd] + ', ' + q.d + '-' + MON[q.m] : esc(d.day)) + (i === daily.length - 1 ? ' (bugun)' : '') + '</td><td class="r">' + num(d.active) + '</td><td class="r">' + num(d.xp) + '</td></tr>';
    }).join('');
    const chart = '<section class="card" aria-labelledby="actH">' +
      '<div class="card-h"><div><h3 id="actH">14 kunlik faollik</h3><p class="sub">' + esc(range) + '</p></div>' +
      '<div class="seg" role="group" aria-label="Ko\'rsatkich">' + segBtn('series', 'active', S.series, "Faol o'quvchilar") + segBtn('series', 'xp', S.series, 'Ball') + '</div></div>' +
      (daily.length >= 2 ? '<p class="take">' + esc(takeDaily(daily, S.series === 'xp')) + '</p>' : '') +
      (daily.length ? '<div id="actChart"></div>' : emptyBox(ic('chart-column'), "Hali ma'lumot yo'q", "O'quvchilar dars ko'rgan sari grafik to'ladi.")) +
      '<p class="cap">' + (S.series === 'xp' ? "Har kuni barcha o'quvchilar to'plagan ball." : "Faol — shu kuni kamida 1 ball olgan o'quvchi.") + ' Ustunni bosing — aniq qiymat chiqadi.</p>' +
      (daily.length ? '<details class="dt"><summary>' + ic('table') + 'Jadval ko\'rinishi' + ic('chevron-down', 'chev') + '</summary><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Kun</th><th class="r">Faol o\'quvchilar</th><th class="r">Ball</th></tr></thead><tbody>' + rows + '</tbody></table></div></details>' : '') +
    '</section>';

    /* 06.10 (egasi, "1 ha"): eski "Uslub tanlovi" (O'yinli/Shisha) o'rniga Ko'rinish kartasi; eski server
       (stats da korinish yo'q) - karta ko'rsatilmaydi */
    const kor = s.korinish && typeof s.korinish === 'object' ? korCard(s.korinish) : '';

    const rec = Array.isArray(s.recent) ? s.recent : [];
    const feed = '<section class="card" aria-labelledby="recH"><div class="card-h"><div><h3 id="recH">So\'nggi faollik</h3><p class="sub">O\'quvchilarning oxirgi ' + (rec.length || 20) + ' ta natijasi</p></div></div>' +
      (rec.length ? '<ul class="feed">' + rec.map((r) => {
        const K = KIND[r.kind] || { icon: () => ic('activity'), cls: '', text: (x) => (x ? x : String(r.kind || '')) };
        const res = r.natija ? ' · ' + String(r.natija) : '';
        return '<li class="li"><span class="li-ic ' + K.cls + '">' + K.icon() + '</span><span class="li-t"><b>' + txt(r.name) + '</b><small>' + txt(K.text(r.ref ? String(r.ref) : '') + res) + '</small></span><time datetime="' + esc(r.at) + '">' + esc(rel(r.at)) + '</time></li>';
      }).join('') + '</ul>' : emptyBox(ic('activity'), "Hali faollik yo'q", "O'quvchilar darslarni boshlaganda shu yerda ko'rinadi.")) +
    '</section>';

    return '<div class="kpis">' + hero + '<div class="card kband">' + tiles + '</div></div>' + chart + kor + feed;
  }
  function mountBugun() {
    const s = C.stats || {};
    mountKor();
    const daily = Array.isArray(s.daily) ? s.daily : [];
    if (!daily.length) return;
    const xp = S.series === 'xp';
    const vals = daily.map((d) => Number(xp ? d.xp : d.active) || 0);
    const ps = daily.map((d) => dayP(d.day));
    const labels = ps.map((q, i) => (q ? String(q.d) : String(i + 1)));
    const full = ps.map((q, i) => (q ? WD[q.wd] + ', ' + q.d + '-' + MONF[q.m] : daily[i].day) + (i === daily.length - 1 ? ' · bugun' : ''));
    let mi = 0;
    vals.forEach((v, i) => { if (v >= vals[mi]) mi = i; });
    barChart($('#actChart'), {
      values: vals, labels, full, now: daily.length - 1,
      fmt: (v) => (xp ? num(v) + ' ball' : num(v) + " o'quvchi faol"),
      extra: (i) => (xp ? 'Faol: ' + num(daily[i].active) + " o'quvchi" : 'Ball: ' + num(daily[i].xp)),
      aria: '14 kunlik ' + (xp ? 'ball' : 'faollik') + ' grafigi: eng ko\'p ' + num(vals[mi]) + ' (' + full[mi] + '), bugun ' + num(vals[vals.length - 1]) + '. Barcha qiymatlar jadval ko\'rinishida.',
    });
  }
  const skelBugun = () => '<div class="kpis"><span class="sk sk-hero"></span><span class="sk sk-hero"></span></div>' + skCard(220) + '<div class="card">' + skLines(5) + '</div>';

  /* ---------- Ko'rinish kartasi (admin paneldagi bilan bir xil ma'no; /api/x/stats korinish, SPEC 10.6) ---------- */
  const MZN = { sahro: 'Sahro', voha: 'Voha', shahar: 'Shahar', qahva: 'Qahva', xattot: 'Xattot', shom: 'Shom' };
  const MAVZU_SOZ = { kun: 'kunduzgi', tun: 'tungi' };
  const isNight = (h) => h >= 19 || h < 6;
  const nOf = (v) => Math.max(0, Number(v) || 0);
  const soatOraliq = (h) => pad2(h) + ':00–' + pad2(h) + ':59';
  function dlong(iso) {
    const t = tsOf(iso);
    if (!isFinite(t)) return '';
    const d = tk(t);
    return d.getUTCDate() + '-' + MONF[d.getUTCMonth()];
  }
  /* 24 soat (0-23) bo'yicha ochilishlar; soat yo'q bo'lsa - nollar */
  function korSoat(k) {
    const by = {};
    (Array.isArray(k.soat) ? k.soat : []).forEach((x) => { if (x && x.hour >= 0 && x.hour < 24) by[Math.floor(x.hour)] = nOf(x.opens); });
    return Array.from({ length: 24 }, (_, h) => by[h] || 0);
  }
  const peakOf = (hours) => { let pk = 0; hours.forEach((v, h) => { if (v > hours[pk]) pk = h; }); return pk; };
  /* bitta gaplik xulosa: eng ko'p ochilgan manzara + tungi soatlar ulushi va eng qizg'in soat */
  function takeKor(mz, tot, hours, opens) {
    let a = '', b = '';
    if (tot && mz.length) {
      const top = mz.filter((m) => m.sessions === mz[0].sessions).map((m) => m.label);
      a = top.length > 1
        ? top.slice(0, -1).join(', ') + ' va ' + top[top.length - 1] + ' eng ko\'p ochilgan manzaralar (har biri ' + pct(mz[0].sessions, tot) + '%)'
        : top[0] + ' eng ko\'p ochilgan manzara (' + pct(mz[0].sessions, tot) + '%)';
    }
    if (opens) {
      const night = hours.reduce((x, v, h) => x + (isNight(h) ? v : 0), 0);
      const np = night / opens * 100;
      const share = np < 1 ? '1 foizdan kami' : np > 99 ? '99 foizdan ko\'pi' : Math.round(np) + ' foizi';
      b = (night === 0 ? 'ilova faqat kunduzgi soatlarda ochilgan' : night === opens ? 'ilova faqat tungi soatlarda (19:00–05:59) ochilgan'
        : 'ilova ochilishlarining ' + share + ' tungi soatlarda (19:00–05:59)') + ', eng qizg\'in soat — ' + pad2(peakOf(hours)) + ':00';
    }
    if (a && b) return a + '; ' + b + '.';
    if (a) return a + '.';
    return b ? b.charAt(0).toUpperCase() + b.slice(1) + '.' : '';
  }
  /* ulush chizig'i (bezak; raqamlar yonida yozilgan) */
  const split2 = (parts) => '<div class="split2" aria-hidden="true">' + parts.filter((p) => p[0] > 0).map((p) => '<i class="' + p[1] + '" style="flex:' + p[0] + ' 1 0"></i>').join('') + '</div>';
  const duoItem = (sw, icon, label, p, n, unit) => '<div><div class="dl"><span class="sw2 ' + sw + '" aria-hidden="true"></span>' + ic(icon) + '<span>' + label + '</span></div>' +
    '<div class="dv">' + p + '%<small>' + num(n) + ' ' + unit + '</small></div></div>';
  function korSoatHTML(hours, tbl) {
    if (tbl) {
      const pk = peakOf(hours);
      return '<div class="tbl-wrap sc" tabindex="0" role="region" aria-label="Ilova ochilishlari soatlar bo\'yicha, jadval"><table class="tbl"><thead><tr><th>Soat</th><th>Vaqt</th><th class="r">Ochilishlar</th></tr></thead><tbody>' +
        hours.map((v, h) => '<tr' + (h === pk && v > 0 ? ' class="now"' : '') + '><td>' + soatOraliq(h) + '</td><td>' + (isNight(h) ? 'Tungi' : 'Kunduzgi') + '</td><td class="r">' + num(v) + '</td></tr>').join('') +
        '</tbody></table></div>';
    }
    return '<div id="korChart"></div><p class="legend"><span class="sw0" aria-hidden="true"></span>Fon — tungi soatlar (19:00–05:59), ustun — shu soatdagi ochilishlar</p>';
  }
  const korTblBtn = (on) => '<button type="button" class="btn sm" data-act="korTbl" aria-pressed="' + on + '" aria-controls="korSoat">' + ic(on ? 'chart-column' : 'table') + (on ? 'Grafik' : 'Jadval') + '</button>';
  function korCard(k) {
    const mz = (Array.isArray(k.manzara) ? k.manzara : []).filter((m) => m && MZN[m.key]).map((m) => ({ key: m.key, label: m.label || MZN[m.key], sessions: nOf(m.sessions), tanlagan: nOf(m.tanlagan) }));
    const tot = mz.reduce((a, m) => a + m.sessions, 0), users = nOf(k.users), days = nOf(k.days) || 14;
    const hours = korSoat(k), opens = hours.reduce((a, v) => a + v, 0);
    const st = tsOf(k.since);
    const since = isFinite(st) && st > Date.now() - days * 864e5 ? ' · <span class="nowrap">' + esc(dlong(k.since)) + 'dan beri</span>' : '';
    const sub = 'Oxirgi ' + days + ' kun · ' + num(tot) + ' ochilish · ' + num(users) + ' o\'quvchi' + since;
    const head = '<div class="card-h"><div><h3 id="korH">Ko\'rinish</h3><p class="sub">' + sub + '</p></div></div>';
    if (!tot && !opens) {
      return '<section class="card korc" aria-labelledby="korH">' + head + emptyBox(ic('image'), "Ko'rinish ma'lumoti hali yo'q", "O'quvchilar ilovani ochganda qaysi manzara va qaysi rejimda ochilgani shu yerda chiqadi.") + '</section>';
    }
    const mmax = Math.max(1, ...mz.map((m) => m.sessions));
    const left = '<h4 class="ko-h">Qaysi manzara ko\'p ochilgan</h4>' + (tot
      ? '<ul class="mzl">' + mz.map((m) => '<li><span class="th" data-v="' + esc(m.key) + '" aria-hidden="true"><span data-scene data-focus="thumb"></span></span>' +
          '<span class="nm"><b>' + esc(m.label) + '</b><small>' + (m.tanlagan ? ic('pin') + num(m.tanlagan) + ' kishi tanlagan' : 'tanlaganlar yo\'q') + '</small></span>' +
          '<span class="hb" aria-hidden="true"><i' + (m.sessions ? '' : ' class="z"') + ' style="width:' + (m.sessions / mmax * 100).toFixed(1) + '%"></i></span>' +
          '<span class="c">' + num(m.sessions) + '<span class="sr"> ochilish</span></span><span class="p">' + pct(m.sessions, tot) + '%</span></li>').join('') + '</ul>'
      : emptyBox(ic('image'), 'Manzara hali yozilmagan', "Ilovaning yangi ko'rinishi ochilganda paydo bo'ladi."));
    const tn = k.tanlov || {}, ta = nOf(tn.tanlangan), ay = nOf(tn.aylan), tl = ta + ay;
    const mv = k.mavzu || {}, kun = nOf(mv.kun), tun = nOf(mv.tun), ml = kun + tun;
    let right = '';
    if (tl) {
      right += '<div class="ko-b"><h4 class="ko-h">Manzara tanlovi</h4><div class="duo">' +
        duoItem('', 'pin', "O'zi tanlagan", pct(ta, tl), ta, "o'quvchi") + duoItem('s', 'shuffle', 'Har ochilganda almashadi', pct(ay, tl), ay, "o'quvchi") + '</div>' +
        split2([[ta, ''], [ay, 's']]) + '</div>';
    }
    if (ml) {
      right += '<div class="ko-b"><h4 class="ko-h">Kunduzgi va tungi</h4><div class="duo">' +
        duoItem('c', 'sun', 'Kunduzgi', pct(kun, ml), kun, 'ochilish') + duoItem('', 'moon', 'Tungi', pct(tun, ml), tun, 'ochilish') + '</div>' +
        split2([[kun, 'c'], [tun, '']]) + '</div>';
    }
    right += '<div class="ko-b"><div class="ko-hh"><h4 class="ko-h">Ilova ochilishlari soatlar bo\'yicha</h4>' + (opens ? korTblBtn(!!S.korTbl) : '') + '</div>' +
      '<div id="korSoat">' + (opens ? korSoatHTML(hours, !!S.korTbl) : emptyBox(ic('clock'), 'Bu davrda ilova ochilmagan', '')) + '</div></div>';
    const take = takeKor(mz, tot, hours, opens);
    return '<section class="card flush korc" aria-labelledby="korH">' + head + (take ? '<p class="take">' + esc(take) + '</p>' : '') +
      '<div class="ko-g"><div>' + left + '</div><div>' + right + '</div></div></section>';
  }
  function mountKor() {
    const k = C.stats && C.stats.korinish;
    const host = $('#korChart');
    if (!k || !host) return;
    const hours = korSoat(k), opens = hours.reduce((a, v) => a + v, 0), pk = peakOf(hours);
    barChart(host, {
      values: hours, labels: hours.map((_, h) => pad2(h)), full: hours.map((_, h) => soatOraliq(h)), now: null, start: pk,
      h: 140, compact: true, bands: [[0, 6], [19, 24]],
      ticks: [[0, '00:00', 'start'], [6, '06:00'], [12, '12:00'], [19, '19:00'], [24, '24:00', 'end']],
      fmt: (v) => num(v) + ' ochilish', extra: (i) => (isNight(i) ? 'tungi soat' : 'kunduzgi soat'),
      aria: 'Ilova ochilishlari soatlar bo\'yicha: jami ' + num(opens) + ', eng ko\'p ' + num(hours[pk]) + ' (' + soatOraliq(pk) + '). Barcha qiymatlar jadval ko\'rinishida.',
    });
  }

  /* ======================= KURS ======================= */
  const canOpen = () => S.role === 'ceo' || S.role === 'admin';
  const courseTotal = () => (C.course && Number(C.course.jami)) || (C.course && C.course.lessons && C.course.lessons.length) || (C.kurs && C.kurs.jami_dars) || 36;
  function rangeTxt(a, b) { return a === b ? '<b>' + a + '</b>-dars' : '<b>' + a + '–' + b + '</b>-darslar'; }
  function ocNote(open, v, total) {
    if (v > open) return ic('lock-open') + '<span>Saqlansa ' + rangeTxt(open + 1, v) + ' o\'quvchilarga ochiladi.</span>';
    if (v < open) return ic('lock') + '<span>Saqlansa ' + rangeTxt(v + 1, open) + ' o\'quvchilarga yopiladi.</span>';
    if (open >= total) return ic('eye') + '<span>Barcha ' + total + ' dars o\'quvchilarga ochiq.</span>';
    return ic('eye') + '<span>O\'quvchilar ' + rangeTxt(1, open) + 'ni ko\'radi, qolganlari yopiq.</span>';
  }
  function htmlKurs() {
    const c = C.course || { open: 0, lessons: [] };
    const lessons = Array.isArray(c.lessons) ? c.lessons.slice().sort((a, b) => a.n - b.n) : [];
    const total = courseTotal(), open = Number(c.open) || 0;
    const v = S.openDraft == null ? open : S.openDraft;
    const edit = canOpen();
    const ctl = '<section class="tint" aria-labelledby="ocH">' +
      '<div class="kick" id="ocH">Ochiq darslar</div>' +
      '<div class="oc-row"><div class="oc-big" aria-live="polite"><span id="ocVal">' + v + '</span><small>/ ' + total + '</small></div>' +
      (edit ? '<div class="stepper" role="group" aria-label="Ochiq darslar soni"><button type="button" class="sb" data-act="ocDec" aria-label="Bitta kamaytirish"' + (v <= 1 ? ' disabled' : '') + '>' + ic('minus') + '</button><button type="button" class="sb" data-act="ocInc" aria-label="Bitta ko\'paytirish"' + (v >= total ? ' disabled' : '') + '>' + ic('plus') + '</button></div>' : '') +
      '</div>' +
      (edit
        ? '<input type="range" class="oc-range" id="ocRange" min="1" max="' + total + '" step="1" value="' + v + '" aria-label="Ochiq darslar soni">'
        : '<div class="dbar"><span id="ocBar" style="width:' + pct(v, total) + '%"></span></div>') +
      '<p class="oc-note" id="ocNote">' + ocNote(open, v, total) + '</p>' +
      (edit
        ? '<div class="oc-act"><button type="button" class="btn pri" data-act="ocSave" id="ocSave"' + (v === open ? ' disabled' : '') + '>' + ic('save') + 'Saqlash</button><button type="button" class="btn" data-act="ocReset" id="ocReset"' + (v === open ? ' hidden' : '') + '>' + ic('rotate-ccw') + 'Bekor qilish</button></div>'
        : '<div class="note" style="margin-top:14px">' + ic('lock') + '<span>Darslarni ochish CEO va adminga ruxsat etilgan. Siz faqat ko\'rasiz.</span></div>') +
    '</section>';

    let parts = Array.isArray(c.qismlar) && c.qismlar.length ? c.qismlar : C.kurs && Array.isArray(C.kurs.qismlar) ? C.kurs.qismlar : null;
    if (!parts) {
      const qs = Array.from(new Set(lessons.map((l) => l.qism))).sort((a, b) => a - b);
      parts = qs.map((q) => ({ n: q, nomi: q + '-qism', darslar: lessons.filter((l) => l.qism === q).map((l) => l.n) }));
    }
    const byN = {};
    lessons.forEach((l) => { byN[l.n] = l; });
    /* telefonda faqat "chegara" qismi ochiq turadi (oxirgi ochiq dars joylashgan qism; hammasi ochiq bo'lsa 1-qism) */
    const wide = window.matchMedia && window.matchMedia('(min-width: 900px)').matches;
    let focusPart = parts.length ? parts[0].n : null;
    if (open < total) parts.forEach((p) => { if ((p.darslar || []).includes(clamp(open, 1, total))) focusPart = p.n; });
    const partsHTML = parts.map((p) => {
      const ls = (p.darslar || []).map((n) => byN[n]).filter(Boolean);
      if (!ls.length) return '';
      const nOpen = ls.filter((l) => l.n <= open).length;
      const slides = ls.reduce((a, l) => a + (Number(l.slaydlar) || 0), 0);
      const done = ls.reduce((a, l) => a + (Number(l.done) || 0), 0);
      const st = nOpen === ls.length ? '<span class="pill good">' + ic('lock-open') + 'Ochiq</span>' : nOpen === 0 ? '<span class="pill mute">' + ic('lock') + 'Yopiq</span>' : '<span class="pill info">' + ic('lock-open') + nOpen + '/' + ls.length + ' ochiq</span>';
      const isOpen = S.partOpen[p.n] != null ? S.partOpen[p.n] : (wide || p.n === focusPart);
      return '<section class="card flush part' + (isOpen ? '' : ' shut') + '" aria-labelledby="q' + p.n + '">' +
        '<div class="part-h" data-act="part" data-v="' + p.n + '"><div class="part-t"><div class="kick">' + p.n + '-qism · ' + ls[0].n + '–' + ls[ls.length - 1].n + '-darslar</div><h3 id="q' + p.n + '">' + txt(p.nomi) + '</h3><p class="sub">' + ls.length + ' dars · ' + num(slides) + ' slayd · tugatgan: ' + num(done) + '</p></div>' +
        '<div class="part-r">' + st + '<button type="button" class="ib part-tg" aria-expanded="' + isOpen + '" aria-controls="pl' + p.n + '" aria-label="' + p.n + '-qism darslari">' + ic('chevron-down') + '</button></div></div>' +
        '<div class="part-l" id="pl' + p.n + '">' +
        '<div class="les-hd" aria-hidden="true"><span>№</span><span>Dars</span><span>Tugatgan</span><span>Boshlagan</span><span>Test o\'rt.</span><span>Holat</span></div>' +
        ls.map((l) => lesRow(l, open)).join('') + '</div></section>';
    }).join('');
    return ctl + '<div class="parts">' + (partsHTML || '<div class="card">' + emptyBox(ic('book-open'), "Darslar ro'yxati bo'sh", '') + '</div>') + '</div>';
  }
  function lesRow(l, open) {
    const locked = l.n > open;
    const meta = ['<span>' + ic('images') + num(l.slaydlar) + ' slayd</span>'];
    if (l.video) meta.push('<span>' + ic('circle-play') + (l.videolar > 1 ? l.videolar + ' video' : 'Video') + '</span>');
    if (l.test) meta.push('<span>' + ic('list-checks') + 'Test</span>');
    const tot = C.tests[l.n];
    const hasAvg = l.test && l.test_avg != null && isFinite(Number(l.test_avg));
    const avg = hasAvg ? dec(l.test_avg) + (tot ? ' / ' + tot : '') : '—';
    return '<div class="les' + (locked ? ' locked' : '') + '">' +
      '<span class="les-n" aria-hidden="true">' + l.n + '</span>' +
      '<div class="les-t"><b><span class="sr">' + l.n + '-dars: </span>' + txt(l.nomi) + '</b><div class="les-meta">' + meta.join('') + '</div></div>' +
      '<span class="les-p">' + (locked ? '<span class="pill mute">' + ic('lock') + 'Yopiq</span>' : '<span class="pill good">' + ic('lock-open') + 'Ochiq</span>') + '</span>' +
      '<div class="les-st">' +
        '<span>' + ic('book-check') + '<span class="lb">tugatgan: </span><b>' + num(l.done) + '</b></span>' +
        '<span>' + ic('book-open') + '<span class="lb">boshlagan: </span><b>' + num(l.started) + '</b></span>' +
        '<span' + (hasAvg ? '' : ' class="na"') + '>' + ic('target') + '<span class="lb">test o\'rtachasi: </span><b>' + avg + '</b></span>' +
      '</div></div>';
  }
  async function loadKurs(force) {
    const [c, k] = await Promise.all([
      api('/api/x/course'),
      C.kurs && !force ? Promise.resolve(C.kurs) : getJSON('/content/kurs.json').catch(() => null),
    ]);
    C.course = c;
    if (k) C.kurs = k;
    if (C.kurs && Array.isArray(C.kurs.darslar)) {
      const need = C.kurs.darslar.filter((d) => d.test && typeof d.test === 'string' && /^\/content\//.test(d.test) && !C.tests[d.n]);
      await Promise.all(need.map((d) => getJSON(d.test).then((t) => { if (t && Array.isArray(t.savollar)) C.tests[d.n] = t.savollar.length; }).catch(() => null)));
    }
    C.kursLoaded = true;
  }
  function ocUpdate() {
    const c = C.course;
    if (!c) return;
    const total = courseTotal(), open = Number(c.open) || 0, v = S.openDraft == null ? open : S.openDraft;
    const set = (id, fn) => { const el = document.getElementById(id); if (el) fn(el); };
    set('ocVal', (el) => { el.textContent = v; });
    set('ocBar', (el) => { el.style.width = pct(v, total) + '%'; });
    set('ocRange', (el) => { if (+el.value !== v) el.value = v; });
    set('ocNote', (el) => { el.innerHTML = ocNote(open, v, total); });
    set('ocSave', (el) => { el.disabled = v === open || S.saving; });
    set('ocReset', (el) => { el.hidden = v === open; });
    const dn = $('[data-act="ocDec"]'), up = $('[data-act="ocInc"]');
    if (dn) dn.disabled = v <= 1;
    if (up) up.disabled = v >= total;
  }
  function ocStep(d) {
    if (!C.course) return;
    const total = courseTotal(), open = Number(C.course.open) || 0;
    const cur = S.openDraft == null ? open : S.openDraft;
    const nv = clamp(cur + d, 1, total);
    if (nv === cur) return false;
    S.openDraft = nv === open ? null : nv;
    ocUpdate();
    hap.sel();
    return true;
  }
  const skelKurs = () => '<span class="sk sk-hero"></span>' + skCard(160) + skCard(160);

  /* ======================= O'QUVCHILAR ======================= */
  const SEGS = [
    { id: 'all', label: 'Hammasi', icon: () => ic('users') },
    { id: 'today', label: 'Bugun faol', icon: () => ic('activity') },
    { id: 'week', label: '7 kunda faol', icon: () => ic('calendar-check') },
    { id: 'idle', label: 'Faol emas', icon: () => ic('hourglass') },
  ];
  function segOf(s) {
    const t = tsOf(s.last_seen), now = Date.now();
    const o = { all: true, today: false, week: false, idle: true };
    if (isFinite(t)) {
      o.today = dkey(t) === dkey(now);
      o.week = now - t <= 7 * 864e5;
      o.idle = !o.week;
    }
    return o;
  }
  /* 06.10: eski uslub chipi (O'yinli/Shisha) o'rniga o'quvchining oxirgi ko'rinishi - manzara (+ kun/tun);
     noma'lum bo'lsa (05.10 gacha ochgan yoki eski server) - hech narsa */
  function korChip(s) {
    const m = MZN[s && s.manzara];
    if (!m) return '';
    const md = MAVZU_SOZ[s.mavzu];
    return '<span class="chipu" title="' + esc('Oxirgi ochilish: ' + m + (md ? ', ' + md : '')) + '"><i class="mzd" data-v="' + esc(s.manzara) + '" aria-hidden="true"></i>' + m +
      (md ? ic(s.mavzu === 'tun' ? 'moon' : 'sun', 'mdi') + '<small class="md">' + md + '</small>' : '') + '</span>';
  }
  function stuRow(s, total) {
    const name = s.name || 'Nomsiz';
    const u = s.username ? '@' + s.username : "username yo'q";
    return '<div class="stu">' + avatar(name) +
      '<div class="stu-n"><b>' + txt(name) + '</b><small>' + esc(u) + '<span class="m-join"> · qo\'shilgan ' + esc(dshort(s.joined_at)) + '</span></small></div>' +
      korChip(s) +
      '<div class="stu-x">' +
        '<span class="d-join"><span class="lb">qo\'shilgan: </span>' + esc(dshort(s.joined_at)) + '</span>' +
        '<span class="d-seen">' + ic('clock') + '<span class="lb">oxirgi faollik: </span>' + esc(rel(s.last_seen)) + '</span>' +
        '<span class="n-r">' + ic('book-check') + '<b>' + num(s.lessons_done) + '/' + total + '</b><span class="lb"> dars</span></span>' +
        '<span class="n-r">' + ic('gem') + '<b>' + num(s.xp) + '</b><span class="lb"> ball</span></span>' +
        '<span class="n-r">' + ic('flame') + '<b>' + num(s.streak) + '</b><span class="lb"> kun seriya</span></span>' +
      '</div></div>';
  }
  function stuCounts(list) {
    const o = { all: 0, today: 0, week: 0, idle: 0 };
    list.forEach((s) => { const g = segOf(s); Object.keys(o).forEach((k) => { if (g[k]) o[k]++; }); });
    return o;
  }
  function htmlQtiles(list) {
    const k = stuCounts(list);
    return SEGS.map((g) => '<button type="button" class="qt" data-act="seg" data-v="' + g.id + '" aria-pressed="' + (S.seg === g.id) + '"><b>' + num(k[g.id]) + '</b><span>' + g.icon() + g.label + '</span></button>').join('');
  }
  function htmlStuList(list) {
    const total = courseTotal();
    const rows = list.filter((s) => segOf(s)[S.seg]);
    if (!rows.length) {
      return S.q
        ? emptyBox(ic('search'), 'Hech kim topilmadi', '«' + esc(S.q) + '» bo\'yicha o\'quvchi yo\'q. Ismni yoki @username ni tekshiring.')
        : list.length ? emptyBox(ic('users'), "Bu filtrda o'quvchi yo'q", 'Boshqa filtrni tanlang.')
          : emptyBox(ic('users'), "Hali o'quvchi yo'q", "Talabalar boti orqali kirgan o'quvchilar shu yerda ko'rinadi.");
    }
    const shown = rows.slice(0, S.shown);
    return '<div class="rows-hd" aria-hidden="true"><span></span><span>O\'quvchi</span><span>Qo\'shilgan</span><span>Oxirgi faollik</span><span>Darslar</span><span>Ball</span><span>Seriya</span><span>Ko\'rinish</span></div>' +
      shown.map((s) => stuRow(s, total)).join('') +
      (rows.length > shown.length ? '<div class="more"><button type="button" class="btn sm" data-act="more">' + ic('chevron-down') + 'Yana ko\'rsatish (' + (rows.length - shown.length) + ')</button></div>' : '');
  }
  function htmlStudents() {
    const list = C.students || [];
    return '<section class="tint" aria-labelledby="stK"><div class="kick" id="stK">O\'quvchilar faolligi</div>' +
        '<h3 style="margin-top:6px">Kimlar darsni davom ettiryapti?</h3>' +
        '<div class="qtiles" id="qtiles" role="group" aria-label="Filtr">' + htmlQtiles(list) + '</div></section>' +
      '<div class="toolbar"><label class="search">' + ic('search') + '<span class="sr">Qidirish</span><input id="stuQ" type="search" inputmode="search" enterkeyhint="search" autocomplete="off" placeholder="Ism yoki @username" value="' + esc(S.q) + '"></label><span class="count" id="stuCount">' + num(list.filter((s) => segOf(s)[S.seg]).length) + ' ta</span></div>' +
      '<section class="card flush" aria-label="O\'quvchilar ro\'yxati"><div id="stuList">' + htmlStuList(list) + '</div></section>';
  }
  function refreshStudents() {
    const list = C.students || [];
    const q = $('#qtiles'), l = $('#stuList'), c = $('#stuCount');
    if (q) q.innerHTML = htmlQtiles(list);
    if (l) l.innerHTML = htmlStuList(list);
    if (c) c.textContent = num(list.filter((s) => segOf(s)[S.seg]).length) + ' ta';
  }
  async function loadStudents() {
    if (!C.course) { try { C.course = await api('/api/x/course'); } catch (e) { /* jami dars soni 36 deb olinadi */ } }
    const d = await api('/api/x/students?q=' + encodeURIComponent(S.q));
    C.students = Array.isArray(d.students) ? d.students : [];
  }
  let qTimer = null, qSeq = 0;
  function onSearch(v) {
    clearTimeout(qTimer);
    qTimer = setTimeout(async () => {
      S.q = v.trim();
      S.shown = 150;
      const my = ++qSeq;
      const l = $('#stuList');
      if (l) l.parentElement.classList.add('busy');
      try {
        const d = await api('/api/x/students?q=' + encodeURIComponent(S.q));
        if (my !== qSeq) return;
        C.students = Array.isArray(d.students) ? d.students : [];
        refreshStudents();
      } catch (e) {
        if (my === qSeq) { toast(e.message, true); hap.err(); }
      } finally {
        const l2 = $('#stuList');
        if (l2 && my === qSeq) l2.parentElement.classList.remove('busy');
      }
    }, 300);
  }
  const skelStudents = () => '<span class="sk sk-hero" style="height:170px"></span><span class="sk" style="height:46px"></span><div class="card">' + skLines(6) + '</div>';

  /* ======================= PANELLAR ======================= */
  const PANEL = {
    ceo: { icon: () => ic('crown'), desc: "Moliya, o'sish, guruhlar va o'quv natijalari bir sahifada.", tags: ["Umumiy ko'rinish", 'Moliya', 'AI xulosa'] },
    admin: { icon: () => ic('shield-check'), desc: "Qabul, to'lovlar, guruhlar va davomat — kundalik boshqaruv.", tags: ['Qabul', "To'lovlar", 'Davomat'] },
    lms: { icon: () => ic('library'), desc: 'Kurslar, dars konstruktori, test banki va sertifikatlar.', tags: ['Kurslar', 'Test banki', 'Imtihonlar'] },
    ustoz: { icon: () => ic('presentation'), desc: 'Jonli dars, vazifalar, audio tekshiruv va guruh chati.', tags: ['Jonli dars', 'Tekshiruv', 'Baholar jurnali'] },
    assistent: { icon: () => ic('headphones'), desc: "Talaffuz tekshiruvi, o'quvchilar va guruh chati — cheklangan menyu.", tags: ['Tekshiruv', "O'quvchilar", 'Guruh chati'] },
  };
  const safeUrl = (u) => typeof u === 'string' && /^\/staff\/p\/[A-Za-z_]+\.html(\?|$)/.test(u);
  function htmlPanels() {
    const ps = (S.panels || []).filter((p) => p && safeUrl(p.url));
    if (!ps.length) return '<div class="card">' + emptyBox(ic('panels-top-left'), "Panel yo'q", 'Rolingiz uchun panel biriktirilmagan.') + '</div>';
    const cards = ps.map((p, i) => {
      const P = PANEL[p.key] || { icon: () => ic('layout-dashboard'), desc: '', tags: [] };
      const lead = i === 0;
      return '<a class="pcard ' + (lead ? 'tint' : 'card') + '" href="' + esc(p.url) + '" data-act="panel" data-key="' + esc(p.key) + '" aria-label="' + esc((p.nomi || '') + ' — panelni ochish') + '">' +
        '<div class="p-top"><span class="pi">' + P.icon() + '</span><div><h3>' + esc(p.nomi) + '</h3><span class="p-sub">Dizayn namunasi · demo ma\'lumotlar</span></div></div>' +
        (P.desc ? '<p>' + P.desc + '</p>' : '') +
        (P.tags.length ? '<div class="p-list">' + P.tags.map((t) => '<span>' + esc(t) + '</span>').join('') + '</div>' : '') +
        '<span class="btn sm ' + (lead ? 'pri ' : '') + 'p-cta"><span class="p-lb">Panelni ochish</span>' + ic('arrow-right') + '</span>' +
      '</a>';
    }).join('');
    return '<div class="pgrid">' + cards + '</div>' +
      '<div class="note">' + ic('info') + '<span>Panel ichida yuqoridagi «Panel» menyusi orqali boshqa panelga o\'tasiz. Bu yerga qaytish uchun Telegram\'dagi «Orqaga» tugmasini bosing.</span></div>';
  }
  function saveStore() {
    ss.set(SKEY, {
      token: S.token, panels: S.panels, brend: S.brend, role: S.role,
      user: S.user ? { id: S.user.id, first_name: S.user.first_name, last_name: S.user.last_name, username: S.user.username } : null,
      at: Date.now(),
    });
  }

  /* ======================= XODIMLAR ======================= */
  function invOut() {
    const v = S.invite;
    if (!v) return '';
    return '<div class="inv-out" id="invOut"><div class="kick" style="margin-bottom:8px">' + esc(roleOf(v.role).label) + ' uchun havola</div>' +
      '<code class="inv-link" id="invLink">' + esc(v.link) + '</code>' +
      '<p class="inv-meta">' + ic('hourglass') + '<span>Bir martalik' + (v.expires ? ' · ' + esc(dtime(v.expires)) + ' gacha amal qiladi' : ' · 48 soat amal qiladi') + '</span></p>' +
      '<div class="inv-btns"><button type="button" class="btn" data-act="invCopy">' + ic('copy') + 'Nusxalash</button><button type="button" class="btn" data-act="invShare">' + ic('send') + 'Telegram orqali yuborish</button></div></div>';
  }
  function htmlInvite() {
    return '<section class="tint" aria-labelledby="invH" id="invCard"><div class="kick">Taklif havolasi</div>' +
      '<h3 id="invH" style="margin-top:6px">Jamoaga xodim qo\'shish</h3>' +
      '<p class="dm" style="margin-top:4px;font-size:14px">Rolni tanlang va havolani xodimga yuboring. U havolani ochib, xodimlar botida «Start» ni bossa — jamoaga qo\'shiladi.</p>' +
      '<div class="inv-row"><div class="inv-roles" role="radiogroup" aria-label="Rol">' + ['admin', 'ustoz', 'assistent'].map((r) => '<button type="button" role="radio" aria-checked="' + (S.invRole === r) + '" data-act="invRole" data-v="' + r + '">' + ROLE[r].icon() + ROLE[r].label + '</button>').join('') + '</div>' +
      '<button type="button" class="btn pri block" data-act="invMake" id="invMake">' + ic('link') + esc(ROLE[S.invRole].label) + ' uchun havola yaratish</button></div>' +
      invOut() + '</section>';
  }
  function staffRow(x, ceoCount) {
    const self = S.user && String(x.id) === String(S.user.id);
    const lastCeo = x.role === 'ceo' && ceoCount <= 1;
    const act = self ? '' : lastCeo
      ? '<span class="pill mute" title="Oxirgi CEO ni chiqarib bo\'lmaydi">' + ic('lock') + 'Oxirgi CEO</span>'
      : '<button type="button" class="btn sm danger" data-act="rm" data-id="' + esc(x.id) + '">' + ic('user-x') + 'Chiqarish</button>';
    return '<div class="srow">' + avatar(x.name) +
      '<div class="srow-n"><b><span>' + txt(x.name || 'Nomsiz') + '</span>' + (self ? '<span class="you">Siz</span>' : '') + '</b><small>' + esc(x.username ? '@' + x.username : "username yo'q") + '</small></div>' +
      '<div class="act">' + act + '</div>' +
      '<div class="srow-x">' + roleChip(x.role) + '<span class="added">qo\'shilgan ' + esc(dshort(x.added_at)) + '</span></div></div>';
  }
  function htmlStaff() {
    const list = (C.staff || []).slice();
    const order = { ceo: 0, admin: 1, ustoz: 2, assistent: 3 };
    list.sort((a, b) => (order[a.role] ?? 9) - (order[b.role] ?? 9) || String(a.name).localeCompare(String(b.name)));
    const ceoCount = list.filter((x) => x.role === 'ceo').length;
    const cnt = {};
    list.forEach((x) => { cnt[x.role] = (cnt[x.role] || 0) + 1; });
    const sub = ['ceo', 'admin', 'ustoz', 'assistent'].filter((r) => cnt[r]).map((r) => cnt[r] + ' ' + roleOf(r).label.toLowerCase().replace('ceo', 'CEO')).join(' · ');
    return htmlInvite() +
      '<section class="card flush" aria-labelledby="stH"><div class="card-h"><div><h3 id="stH">Jamoa</h3><p class="sub">' + list.length + ' xodim' + (sub ? ' · ' + esc(sub) : '') + '</p></div></div>' +
      '<div id="staffList">' + (list.length ? list.map((x) => staffRow(x, ceoCount)).join('') : emptyBox(ic('users-round'), "Xodim yo'q", '')) + '</div></section>' +
      '<div class="note">' + ic('info') + '<span>O\'zingizni va oxirgi CEO ni chiqarib bo\'lmaydi. Chiqarilgan xodim qaytishi uchun yangi taklif havolasi kerak.</span></div>';
  }
  const skelStaff = () => '<span class="sk sk-hero" style="height:250px"></span><div class="card">' + skLines(5) + '</div>';

  async function copyText(t) {
    try {
      if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(t); return true; }
    } catch (e) { /* zaxira usul */ }
    try {
      const ta = document.createElement('textarea');
      ta.value = t;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch (e) { return false; }
  }

  /* ---------------- 8. Bo'limlar jadvali ---------------- */
  const SCREENS = {
    bugun: {
      head: () => ({ crumb: esc(todayLong()), title: 'Salom, ' + txt((S.user && S.user.first_name) || 'xodim'), sub: "Bugungi faollik, kurs natijalari va o'quvchilar tanlovi — real ma'lumotlar." }),
      ready: () => !!C.stats, load: async () => { C.stats = await api('/api/x/stats'); }, skel: skelBugun, html: htmlBugun, mount: mountBugun,
    },
    kurs: {
      head: () => ({
        crumb: esc((C.kurs && C.kurs.nomi) || 'Fonetika kursi') + ' · ' + courseTotal() + ' dars' + (C.kurs && C.kurs.jami_slayd ? ' · ' + num(C.kurs.jami_slayd) + ' slayd' : ''),
        title: 'Kurs', sub: "Darslarni o'quvchilarga bosqichma-bosqich oching va har darsning natijasini kuzating.",
      }),
      ready: () => !!(C.course && C.kursLoaded), load: loadKurs, skel: skelKurs, html: htmlKurs, mount: null,
    },
    oquvchilar: {
      head: () => ({ crumb: 'Talabalar boti', title: "O'quvchilar", sub: "Botga kirgan o'quvchilar: faollik, darslar, ball va ilovani oxirgi marta qaysi manzarada ochgani." }),
      ready: () => !!C.students, load: loadStudents, skel: skelStudents, html: htmlStudents, mount: null,
    },
    panellar: {
      head: () => ({ crumb: "Dizayn namunasi · demo ma'lumotlar", title: 'Panellar', sub: "Rolingiz uchun ochiq panellar. Ulardagi ism va raqamlar namunaviy; haqiqiy ma'lumotlar Bugun, Kurs va O'quvchilar bo'limlarida." }),
      ready: () => true, load: null, skel: () => '', html: htmlPanels, mount: null,
    },
    xodimlar: {
      head: () => ({ crumb: 'Faqat CEO', title: 'Xodimlar', sub: "Jamoa a'zolari va taklif havolalari. Havola bir marta ishlaydi va 48 soat amal qiladi." }),
      ready: () => !!C.staff, load: async () => { C.staff = (await api('/api/x/staff')).staff || []; }, skel: skelStaff, html: htmlStaff, mount: null,
    },
  };

  /* ---------------- 9. Amallar ---------------- */
  let held = false, holdT = null, holdI = null;
  const stopHold = () => { clearTimeout(holdT); clearInterval(holdI); holdT = holdI = null; };
  const A = {
    refresh() { if (S.tab === 'kurs') S.openDraft = null; render(S.tab, true); },
    retry() { render(S.tab, false); },
    series(el) { if (S.series === el.dataset.v) return; S.series = el.dataset.v; hap.sel(); const b = $('#body'); if (b) { b.innerHTML = htmlBugun(); mountBugun(); scenes(b); } },
    /* Ko'rinish: soatlar grafigi <-> jadval (faqat shu bo'lak qayta chiziladi) */
    korTbl(el) {
      const k = C.stats && C.stats.korinish, box = $('#korSoat');
      if (!k || !box) return;
      S.korTbl = !S.korTbl;
      hap.sel();
      box.innerHTML = korSoatHTML(korSoat(k), S.korTbl);
      el.outerHTML = korTblBtn(S.korTbl);
      if (!S.korTbl) mountKor();
      const nb = $('[data-act="korTbl"]');
      if (nb) nb.focus();
    },
    ocInc() { if (held) { held = false; return; } ocStep(1); },
    ocDec() { if (held) { held = false; return; } ocStep(-1); },
    ocReset() { S.openDraft = null; ocUpdate(); hap.sel(); },
    async ocSave() {
      if (S.saving || S.openDraft == null || !C.course) return;
      const n = S.openDraft;
      S.saving = true;
      const b = $('#ocSave');
      if (b) { b.disabled = true; b.innerHTML = ic('loader-circle') + 'Saqlanmoqda'; }
      try {
        const r = await api('/api/x/open', { n });
        C.course.open = Number(r.open) || n;
        S.openDraft = null;
        S.saving = false;
        hap.ok();
        toast('Saqlandi: ' + C.course.open + ' ta dars ochiq');
        const body = $('#body');
        if (body && S.tab === 'kurs') body.innerHTML = htmlKurs();
      } catch (e) {
        S.saving = false;
        hap.err();
        toast(e.message, true);
        if (b) b.innerHTML = ic('save') + 'Saqlash';
        ocUpdate();
      }
    },
    part(el) {
      const sec = el.closest('.part');
      if (!sec) return;
      const open = sec.classList.contains('shut');
      sec.classList.toggle('shut', !open);
      S.partOpen[Number(el.dataset.v)] = open;
      const b = sec.querySelector('.part-tg');
      if (b) b.setAttribute('aria-expanded', String(open));
      hap.sel();
    },
    seg(el) { S.seg = el.dataset.v; S.shown = 150; hap.sel(); refreshStudents(); },
    more() { S.shown += 300; refreshStudents(); },
    panel(el, e) {
      e.preventDefault();
      const p = (S.panels || []).find((x) => x.key === el.dataset.key);
      if (!p || !safeUrl(p.url)) { toast('Panel havolasi topilmadi', true); return; }
      saveStore();
      hap.tap();
      el.classList.add('going');
      const lb = el.querySelector('.p-lb');
      if (lb) lb.textContent = 'Ochilmoqda…';
      location.href = p.url;
    },
    invRole(el) { S.invRole = el.dataset.v; hap.sel(); $$('[data-act="invRole"]').forEach((b) => b.setAttribute('aria-checked', String(b === el))); const m = $('#invMake'); if (m) m.innerHTML = ic('link') + esc(ROLE[S.invRole].label) + ' uchun havola yaratish'; },
    async invMake(el) {
      if (el.disabled) return;
      el.disabled = true;
      const role = S.invRole;
      el.innerHTML = ic('loader-circle') + 'Yaratilmoqda';
      try {
        const r = await api('/api/x/invite', { role });
        S.invite = { role, link: String(r.link || ''), expires: r.expires || '' };
        hap.ok();
        const card = $('#invCard');
        if (card) card.outerHTML = htmlInvite();
        toast(roleOf(role).label + ' uchun taklif havolasi tayyor');
      } catch (e) {
        hap.err();
        toast(e.message, true);
        el.disabled = false;
        el.innerHTML = ic('link') + esc(roleOf(role).label) + ' uchun havola yaratish';
      }
    },
    async invCopy() {
      if (!S.invite) return;
      const ok = await copyText(S.invite.link);
      if (ok) { hap.ok(); toast('Havola nusxalandi'); return; }
      const c = $('#invLink');
      if (c) { const r = document.createRange(); r.selectNodeContents(c); const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); }
      toast("Nusxalab bo'lmadi: havolani bosib turib nusxalang", true);
    },
    invShare() {
      if (!S.invite) return;
      const url = 'https://t.me/share/url?url=' + encodeURIComponent(S.invite.link) + '&text=' + encodeURIComponent(S.brend + ' xodimlar botiga taklif: ' + roleOf(S.invite.role).label.toLowerCase().replace('ceo', 'CEO'));
      hap.tap();
      try { if (inTg && ver('6.1')) { tg.openTelegramLink(url); return; } } catch (e) { /* zaxira */ }
      window.open(url, '_blank', 'noopener');
    },
    rm(el) {
      const x = (C.staff || []).find((s) => String(s.id) === el.dataset.id);
      if (!x) return;
      hap.tap();
      sheet('<h3>Xodimni chiqarish</h3><p>Xodim jamoadan chiqariladi va boshqaruv paneliga kira olmaydi. Qaytarish uchun yangi taklif havolasi kerak bo\'ladi.</p>' +
        '<div class="who">' + avatar(x.name) + '<div><b>' + txt(x.name || 'Nomsiz') + '</b><small>' + esc(roleOf(x.role).label) + (x.username ? ' · @' + esc(x.username) : '') + '</small></div></div>' +
        '<div class="sheet-act"><button type="button" class="btn" data-act="sheetClose">Bekor qilish</button><button type="button" class="btn danger fill" data-act="rmYes" data-id="' + esc(x.id) + '">' + ic('user-x') + 'Chiqarish</button></div>', 'Xodimni chiqarish');
    },
    async rmYes(el) {
      if (el.disabled) return;
      el.disabled = true;
      const id = el.dataset.id;
      const x = (C.staff || []).find((s) => String(s.id) === id);
      try {
        await api('/api/x/staff/remove', { id: isFinite(Number(id)) ? Number(id) : id });
        closeSheet();
        hap.ok();
        toast((x ? x.name : 'Xodim') + ' jamoadan chiqarildi');
        C.staff = (C.staff || []).filter((s) => String(s.id) !== id);
        if (S.tab === 'xodimlar') render('xodimlar', true, true);
      } catch (e) {
        el.disabled = false;
        hap.err();
        closeSheet();
        toast(e.message, true);
      }
    },
    sheetClose() { closeSheet(); },
    sheetBack(el, e) { if (e.target === el) closeSheet(); },
    close() { closeApp(); },
    boot() { boot(); },
  };

  document.addEventListener('click', (e) => {
    const t = e.target instanceof Element ? e.target : null;
    if (!t) return;
    const tab = t.closest('[data-tab]');
    if (tab) {
      if (tab.dataset.tab !== S.tab) { hap.sel(); go(tab.dataset.tab); } else window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    const a = t.closest('[data-act]');
    if (a && A[a.dataset.act]) A[a.dataset.act](a, e);
  });
  document.addEventListener('input', (e) => {
    const t = e.target;
    if (t && t.id === 'stuQ') onSearch(t.value);
    else if (t && t.id === 'ocRange' && C.course) {
      const open = Number(C.course.open) || 0, v = clamp(Number(t.value) || 1, 1, courseTotal());
      const before = S.openDraft == null ? open : S.openDraft;
      S.openDraft = v === open ? null : v;
      if (v !== before) hap.sel();
      ocUpdate();
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && S.sheet) closeSheet();
  });
  /* matn kiritilayotganda (telefon klaviaturasi) pastki panelni yashirish */
  const coarse = () => { try { return window.matchMedia('(pointer: coarse)').matches; } catch (e) { return false; } };
  /* Android'da klaviatura "Orqaga" bilan yopilsa input fokusda qoladi: shuning uchun fokus + ko'rinadigan balandlik
     kamayganini birga tekshiramiz (aks holda pastki panel yo'qolib qolardi). */
  const isField = (el) => el instanceof Element && el.matches('input[type="search"], input[type="text"], textarea') && coarse();
  const vpH = () => Math.round((window.visualViewport && window.visualViewport.height) || window.innerHeight || 0);
  let baseH = vpH();
  function kbCheck() {
    const h = vpH();
    const focused = isField(document.activeElement);
    if (!focused || h > baseH) baseH = Math.max(h, focused ? baseH : 0);
    document.body.classList.toggle('kb', focused && h < baseH * 0.8);
  }
  document.addEventListener('focusin', () => setTimeout(kbCheck, 350));
  document.addEventListener('focusout', () => setTimeout(kbCheck, 0));
  window.addEventListener('resize', kbCheck);
  try { if (window.visualViewport) window.visualViewport.addEventListener('resize', kbCheck); } catch (e) { /* yo'q */ }
  try { if (tg && tg.onEvent) tg.onEvent('viewportChanged', kbCheck); } catch (e) { /* yo'q */ }
  document.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target && e.target.id === 'stuQ') e.target.blur(); });
  document.addEventListener('pointerdown', (e) => {
    const b = e.target instanceof Element ? e.target.closest('.sb') : null;
    if (!b || b.disabled) return;
    held = false;
    stopHold();
    const d = b.dataset.act === 'ocInc' ? 1 : -1;
    holdT = setTimeout(() => { held = true; holdI = setInterval(() => { if (ocStep(d) === false) stopHold(); }, 85); }, 420);
  });
  ['pointerup', 'pointercancel', 'dragstart'].forEach((ev) => document.addEventListener(ev, stopHold));
  document.addEventListener('pointerout', (e) => { if (e.target instanceof Element && e.target.closest('.sb') && holdT) stopHold(); });

  /* ---------------- 10. Ruxsat / xato ekranlari ---------------- */
  function gate(kind, msg) {
    const G = {
      deny: { icon: ic('shield-x'), cls: 'crit', title: "Ruxsat yo'q", lines: ["Bu bo'lim faqat " + esc(S.brend) + ' xodimlari uchun.', 'Kirish uchun CEO dan taklif havolasini oling.'], btn: inTg ? '<button type="button" class="btn" data-act="close">' + ic('x') + 'Yopish</button>' : '' },
      auth: { icon: ic('log-in'), cls: '', title: 'Telegram orqali oching', lines: ['Boshqaruv paneli xodimlar boti ichida ishlaydi.', 'Botdagi «Boshqaruvni ochish» tugmasini bosing.'], btn: inTg ? '<button type="button" class="btn" data-act="close">' + ic('x') + 'Yopish</button>' : '' },
      net: { icon: ic('wifi-off'), cls: 'crit', title: "Aloqa yo'q", lines: [esc(msg || "Server bilan bog'lanib bo'lmadi."), "Internetni tekshirib, qayta urinib ko'ring."], btn: '<button type="button" class="btn pri" data-act="boot">' + ic('refresh-cw') + 'Qayta urinish</button>' },
    }[kind];
    closeSheet();
    $('#app').innerHTML = gateWrap('<div class="card gate-card" role="alert"><span class="gate-ic ' + G.cls + '">' + G.icon + '</span><h1>' + G.title + '</h1>' +
      G.lines.map((l) => '<p>' + l + '</p>').join('') + G.btn + '</div>');
    scenes();
    if (kind === 'deny') hap.err();
  }
  /* kirish ekrani karkasi: belgi + karta, pastda manzara */
  const gateWrap = (inner, busy) => '<div class="gate"' + (busy ? ' aria-busy="true"' : '') + '><div class="gate-box">' + brandHTML() + inner + '</div>' +
    '<div class="gate-sc" aria-hidden="true"><div data-scene data-focus="full"></div></div></div>';

  /* ---------------- 11. Ishga tushirish ---------------- */
  function initialTab() {
    let q = '';
    try { q = new URLSearchParams(location.search).get('tab') || ''; } catch (e) { q = ''; }
    const saved = ss.get(TKEY);
    const ids = tabsFor().map((t) => t.id);
    if (q && ids.includes(q)) return q;
    if (saved && ids.includes(saved)) return saved;
    return 'bugun';
  }
  async function boot() {
    const st = ss.get(SKEY);
    if (st && st.token && !S.token) S.token = String(st.token);
    if (!initData && !S.token) { gate('auth'); return; }
    const app = $('#app');
    if (app && !app.querySelector('.gate')) { app.innerHTML = gateWrap('<div class="card gate-card">' + skLines(3) + '<p class="sr" role="status">Yuklanmoqda</p></div>', true); scenes(); }
    let a;
    try {
      a = await api('/api/x/auth', {});
    } catch (e) {
      if (e.status === 403) { gate('deny'); return; }
      if (e.status === 401) { gate('auth'); return; }
      gate('net', e.message);
      return;
    }
    S.user = a.user || {};
    S.role = String(a.role || '');
    S.brend = a.brend || 'Muhammadamin';
    S.token = a.token || S.token;
    S.panels = Array.isArray(a.panels) ? a.panels : [];
    saveStore();
    shell();
    go(initialTab());
  }

  /* manzara: o'lcham o'zgarsa qayta chiziladi; kun/tun soatga qarab (ochiq turganda ham) */
  let rsT = null;
  window.addEventListener('resize', () => { clearTimeout(rsT); rsT = setTimeout(() => scenes(), 160); });
  setInterval(themeTick, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) themeTick(); });

  tgSetup();
  scenes();
  boot();
})();

/* Muhammadamin - admin panel (vanilla JS, build bosqichisiz). SPEC 10.5-10.7, 11.5, 13. Ko'rinish: NUQTA UI (05.10.2026,
   egasi tasdiqlagan demo: Dizayn\NUQTA admin demo). 1 yordamchilar · 2 format · 3 NUQTA mavzusi · 4 Telegram va API ·
   5 komponentlar · 6 grafiklar · 7 karkas va router · 8 ekranlar · 9 harakatlar · 10 ishga tushirish. */
/* ikonlar: layout-dashboard users-round filter mouse-pointer-click smartphone book-open list-checks user-cog toggle-right history */
/* ikonlar: house circle-play trophy user-round presentation book-open-text monitor-play award medal layers sparkles circle-alert */
/* ikonlar: loader-circle panels-top-left panel-bottom calendar-range tablet monitor globe circle-help arrow-left chevron-right */
/* ikonlar: chevron-left chevron-down chevron-up flag zoom-in settings circle-dot check rotate-ccw crown shield graduation-cap */
/* ikonlar: user-check gem image bell send swords user-plus book-marked lock-open user-x log-in log-out book-check calendar-check */
/* ikonlar: calendar-days activity timer x sun moon sun-moon clock circle-check circle-x circle-pause triangle-alert ban flame play */
/* ikonlar: percent eye lock chart-bar chart-column trending-down trending-up toggle-left search footprints scale hourglass pin */
/* ikonlar: shuffle info table refresh-cw menu arrow-up arrow-down arrow-up-down minus plus save link copy at-sign calendar circle route */
(function () {
  'use strict';

  /* ================= 1. Yordamchilar ================= */
  const D = document, W = window, H = D.documentElement;
  const $ = (s, r) => (r || D).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || D).querySelectorAll(s));
  const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ESC[c]);
  const ARC = '؀-ۿݐ-ݿࡰ-ࣿﭐ-﷿ﹰ-﻿';
  const AR_RUN = new RegExp('[' + ARC + ']+(?:[\\s\\u00A0]+[' + ARC + ']+)*', 'g');
  /* Matn: HTML uchun xavfsiz; arabcha bo'laklar <bdi dir="rtl" lang="ar"> ichida (matn o'zgartirilmaydi) */
  const T = (s) => esc(s).replace(AR_RUN, (m) => '<bdi dir="rtl" lang="ar" class="ar">' + m + '</bdi>');
  const ic = (n, c) => '<svg class="i' + (c ? ' ' + c : '') + '" aria-hidden="true" focusable="false"><use href="/shared/icons.svg#' + n + '"/></svg>';
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const sum = (arr, f) => (arr || []).reduce((a, x) => a + (+f(x) || 0), 0);
  const uniq = (arr) => arr.filter((x, i) => x && arr.indexOf(x) === i);
  let uid = 0;
  const nid = (p) => (p || 'h') + (++uid);

  /* ================= 2. Format: raqam, sana, vaqt ================= */
  const NB = ' ', TH = ' ', DASH = '–';
  function num(v, d) {
    if (v == null || v === '' || !isFinite(+v)) return DASH;
    v = +v;
    const neg = v < 0;
    v = Math.abs(v);
    const s = d ? v.toFixed(d) : String(Math.round(v));
    const k = s.indexOf('.');
    let a = k < 0 ? s : s.slice(0, k);
    const b = k < 0 ? '' : s.slice(k + 1).replace(/0+$/, '');
    a = a.replace(/\B(?=(\d{3})+(?!\d))/g, TH);
    return (neg ? '−' : '') + a + (b ? ',' + b : '');
  }
  const pc = (a, b) => (b > 0 ? Math.round((a * 100) / b) : 0);
  const OY = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek'];
  const OYL = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];
  const KUN = ['yakshanba', 'dushanba', 'seshanba', 'chorshanba', 'payshanba', 'juma', 'shanba'];
  const KUNQ = ['Ya', 'Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh'];
  const TZMS = 5 * 3600 * 1000;  // Toshkent = UTC+05:00
  function ms(iso) {
    if (iso == null || iso === '') return NaN;
    if (typeof iso === 'number') return iso;
    const s = String(iso);
    return Date.parse(/^\d{4}-\d\d-\d\d$/.test(s) ? s + 'T00:00:00+05:00' : s);
  }
  function tz(iso) { const t = ms(iso); return isNaN(t) ? null : new Date(t + TZMS); }
  const p2 = (n) => (n < 10 ? '0' : '') + n;
  const hm = (d) => p2(d.getUTCHours()) + ':' + p2(d.getUTCMinutes());
  function hms(iso) { const d = tz(iso); return d ? hm(d) + ':' + p2(d.getUTCSeconds()) : DASH; }
  function hmi(iso) { const d = tz(iso); return d ? hm(d) : DASH; }
  function dday(iso) { const d = tz(iso); return d ? d.getUTCDate() + '-' + OY[d.getUTCMonth()] : DASH; }
  function dlong(iso) { const d = tz(iso); return d ? d.getUTCDate() + '-' + OYL[d.getUTCMonth()] : DASH; }
  function dfull(iso) { const d = tz(iso); return d ? d.getUTCDate() + '-' + OYL[d.getUTCMonth()] + ', ' + KUN[d.getUTCDay()] : DASH; }
  function dt(iso) { const d = tz(iso); return d ? d.getUTCDate() + '-' + OY[d.getUTCMonth()] + ', ' + hm(d) : DASH; }
  const dayNo = (d) => Math.floor(d.getTime() / 86400000);
  function rel(iso) {
    const t = ms(iso);
    if (isNaN(t)) return DASH;
    const diff = Date.now() - t;
    if (diff < 60e3 && diff > -120e3) return 'hozirgina';
    if (diff > 0 && diff < 3600e3) return Math.floor(diff / 60e3) + NB + 'daq oldin';
    const d = tz(t), dd = dayNo(tz(Date.now())) - dayNo(d);
    if (dd === 0) return 'bugun, ' + hm(d);
    if (dd === 1) return 'kecha, ' + hm(d);
    return dt(t);
  }
  function dur(v) {
    if (v == null || !isFinite(v)) return DASH;
    const sec = Math.max(0, v / 1000);
    if (sec < 10) return num(Math.round(sec * 10) / 10, 1) + NB + 's';
    let s = Math.round(sec);
    if (s < 60) return s + NB + 's';
    const m = Math.floor(s / 60);
    s %= 60;
    if (m < 60) return m + NB + 'daq' + (s ? ' ' + s + NB + 's' : '');
    const h = Math.floor(m / 60), mm = m % 60;
    return h + NB + 'soat' + (mm ? ' ' + mm + NB + 'daq' : '');
  }
  const todayLong = () => dfull(Date.now());
  function initials(name) {
    const p = String(name || '').trim().split(/\s+/).filter(Boolean);
    if (!p.length) return '?';
    return (p[0].charAt(0) + (p[1] ? p[1].charAt(0) : '')).toUpperCase();
  }
  const fullName = (u) => (((u && u.first_name) || '') + ' ' + ((u && u.last_name) || '')).trim() || (u && u.name) || ('ID ' + ((u && u.id) || ''));

  const REJIM = { light: 'Kunduzgi', dark: 'Tungi', auto: 'Avto' };
  const ARAB = { m: "O'rta", l: 'Katta' };
  const SCHEME = { light: 'Kunduzgi', dark: 'Tungi' };
  const MAVZU = { kun: 'Kunduzgi', tun: 'Tungi' };
  const PLAT = { android: 'Android', android_x: 'Android X', ios: 'iOS', tdesktop: 'Telegram Desktop', macos: 'Telegram macOS',
    weba: 'Telegram Web A', webk: 'Telegram Web K', web: 'Telegram Web', unigram: 'Unigram' };
  const ROLE = { ceo: ['CEO', 'crown', 'hl'], admin: ['Admin', 'shield', ''], ustoz: ['Ustoz', 'graduation-cap', ''], assistent: ['Assistent', 'user-check', 'line'] };
  function devIc(x) {
    x = String(x || '').toLowerCase();
    if (/planshet|ipad|tablet/.test(x)) return 'tablet';
    if (/telefon|iphone/.test(x)) return 'smartphone';
    if (/brauzer|web/.test(x)) return 'globe';
    if (/kompyuter|mac|windows|linux|desktop/.test(x)) return 'monitor';
    return 'circle-help';
  }
  const scrSize = (s) => (s ? String(s).replace('x', NB + '×' + NB) : DASH);

  /* ================= 3. NUQTA mavzusi: manzara (index.html da tanlangan), kun/tun, sahnalar ================= */
  const NV = ['sahro', 'voha', 'shahar', 'qahva', 'xattot', 'shom'];
  const NVN = { sahro: 'Sahro', voha: 'Voha', shahar: 'Shahar', qahva: 'Qahva', xattot: 'Xattot', shom: 'Shom' };
  const modeAt = (d) => { const h = (d || new Date()).getHours(); return h >= 6 && h < 19 ? 'kun' : 'tun'; };
  function greet() {
    const h = new Date().getHours();
    return h < 5 ? 'Xayrli tun' : h < 11 ? 'Xayrli tong' : h < 18 ? 'Xayrli kun' : h < 22 ? 'Xayrli kech' : 'Xayrli tun';
  }
  if (NV.indexOf(H.getAttribute('data-v')) < 0) H.setAttribute('data-v', 'sahro');
  if (!/^(kun|tun)$/.test(H.getAttribute('data-m') || '')) H.setAttribute('data-m', modeAt());
  /* [data-scene] ichiga manzara (o'lcham yoki rejim o'zgarsa qayta chiziladi). Manzara - eng yaqin [data-v] (masalan kichik rasmlar) */
  function scenes(scope) {
    if (typeof W.scene !== 'function') return;
    const night = H.getAttribute('data-m') === 'tun';
    $$('[data-scene]', scope || D).forEach((el) => {
      const w = Math.round(el.clientWidth), h = Math.round(el.clientHeight);
      if (!w || !h) return;
      const host = el.closest('[data-v]') || H;
      const v = NV.indexOf(host.getAttribute('data-v')) >= 0 ? host.getAttribute('data-v') : 'sahro';
      const key = v + '|' + w + 'x' + h + '|' + (night ? 1 : 0);
      if (el._k === key) return;
      el._k = key;
      try { el.innerHTML = W.scene(v, w, h, { focus: el.getAttribute('data-focus') || undefined, night }); } catch (e) { /* manzarasiz ham ishlaydi */ }
    });
  }
  const token = (n) => (getComputedStyle(H).getPropertyValue(n) || '').trim();
  function themeColors() {
    const bg = token('--bg');
    const m = $('meta[name="theme-color"]');
    if (m && /^#[0-9a-f]{6}$/i.test(bg)) m.setAttribute('content', bg);
    tgColors(bg);
  }
  function themeTick() {
    const m = modeAt();
    if (m === H.getAttribute('data-m')) return;
    H.setAttribute('data-m', m);
    scenes();
    themeColors();
    $$('[data-nq="salom"]').forEach((e) => { e.textContent = greet(); });
    drawCharts();
  }

  /* ================= 4. Telegram va API ================= */
  const tg = W.Telegram && W.Telegram.WebApp;
  const INIT = (tg && tg.initData) || '';
  const inTg = !!INIT;
  const ver = (v) => { try { return !!(inTg && tg.isVersionAtLeast && tg.isVersionAtLeast(v)); } catch (e) { return false; } };
  function tgColors(bg) {
    if (!inTg || !/^#[0-9a-f]{6}$/i.test(bg || '')) return;
    try { if (ver('6.9')) tg.setHeaderColor(bg); } catch (e) { /* yo'q */ }
    try { if (ver('6.1')) tg.setBackgroundColor(bg); } catch (e) { /* yo'q */ }
    try { if (ver('7.10')) tg.setBottomBarColor(bg); } catch (e) { /* yo'q */ }
  }
  function tgInit() {
    if (!inTg) return;
    try { tg.ready(); } catch (e) { /* yo'q */ }
    try { tg.expand(); } catch (e) { /* yo'q */ }
    try { if (ver('6.1')) { tg.BackButton.onClick(goBack); tg.BackButton.hide(); } } catch (e) { /* yo'q */ }
  }
  function tgBack(show) { if (!ver('6.1')) return; try { if (show) tg.BackButton.show(); else tg.BackButton.hide(); } catch (e) { /* yo'q */ } }
  function haptic(k) {
    if (!ver('6.1')) return;
    try {
      if (k === 'ok') tg.HapticFeedback.notificationOccurred('success');
      else if (k === 'err') tg.HapticFeedback.notificationOccurred('error');
      else tg.HapticFeedback.selectionChanged();
    } catch (e) { /* yo'q */ }
  }

  const S = {
    me: null, cache: new Map(), view: 0, stack: [], timers: [], charts: {}, sessUser: {}, jami: 36, gated: false, route: null, rib: null,
    ui: { bdays: 14, bmetric: 'active', fdays: 30, lmetric: 'done', cdays: 7, cmetric: 'clicks', ddays: 30, wdays: 30, wmetric: 'created',
      sq: '', ssort: 'last', sdir: -1, tf: null, tlClicks: true, jf: 'all', openDraft: null, more: {}, tbl: {} },
  };
  function ApiErr(status, msg, data) { const e = new Error(msg); e.status = status; e.data = data; e.api = true; return e; }
  async function api(path, o) {
    o = o || {};
    const method = o.method || 'GET';
    if (method === 'GET' && !o.fresh) {
      const c = S.cache.get(path);
      if (c && Date.now() - c.t < 30000) return c.d;
    }
    const h = { Accept: 'application/json' };
    if (INIT) h['X-Init-Data'] = INIT;
    if (method !== 'GET') { h['Content-Type'] = 'application/json'; h['X-Requested-With'] = 'noon'; }
    let r, d = null;
    try {
      r = await fetch(path, { method, headers: h, body: o.body != null ? JSON.stringify(o.body) : undefined, credentials: 'same-origin', cache: 'no-store' });
    } catch (e) {
      throw ApiErr(0, "Server bilan aloqa yo'q. Internetni tekshirib, qayta urinib ko'ring.");
    }
    try { d = await r.json(); } catch (e) { d = null; }
    if (!r.ok) {
      const msg = (d && d.xato) || ('Server javob bermadi (' + r.status + ')');
      if (r.status === 401 && !o.quiet) gate(401, msg, d);
      throw ApiErr(r.status, msg, d);
    }
    if (method === 'GET') { S.cache.set(path, { t: Date.now(), d }); S.updAt = Date.now(); }
    else S.cache.clear();
    return d;
  }
  const has = (sec) => !!(S.me && SEC[sec] && S.me.sections.indexOf(sec) >= 0);
  const canEditKurs = () => !!(S.me && S.me.can_edit && S.me.can_edit.kurs && S.me.access.kurs === 'edit');
  const alive = (tk) => tk === S.view && !S.gated;

  /* ================= 5. Komponentlar ================= */
  function crumbHtml(c) {
    if (!c) return '';
    if (typeof c === 'string') return '<div class="crumb">' + c + '</div>';
    return '<nav class="crumb" aria-label="Yo\'l">' + c.map((x, i) => (i ? ic('chevron-right') : '') +
      (x[0] ? '<a href="' + esc(x[0]) + '">' + x[1] + '</a>' : '<span aria-current="page">' + x[1] + '</span>')).join('') + '</nav>';
  }
  function ph(o) {
    return '<header class="ph"><div class="pt">' + crumbHtml(o.crumb) + '<h1 tabindex="-1">' + o.title + '</h1>' + (o.text ? '<p>' + o.text + '</p>' : '') + '</div>' +
      (o.acts ? '<div class="acts">' + o.acts + '</div>' : '') + '</header>';
  }
  function card(o) {
    const hid = nid('h-');
    const head = (o.title || o.acts) ? '<div class="card-h"><div>' + (o.title ? '<h2 id="' + hid + '">' + o.title + '</h2>' : '') +
      (o.sub ? '<p class="sub"' + (o.subId ? ' id="' + o.subId + '"' : '') + '>' + o.sub + '</p>' : '') + '</div>' + (o.acts ? '<div class="acts">' + o.acts + '</div>' : '') + '</div>' : '';
    return '<section class="card' + (o.cls ? ' ' + o.cls : '') + '"' + (o.id ? ' id="' + o.id + '"' : '') + (o.attrs || '') + (o.title ? ' aria-labelledby="' + hid + '"' : '') + '>' +
      head + (o.take ? '<p class="take">' + o.take + '</p>' : '') + (o.flush ? o.body : '<div class="card-b">' + o.body + '</div>') + '</section>';
  }
  /* KPI tasmasi: [{l, i, v, u, f, up:[delta, text], live, href, id, tx}] */
  function kband(items, cols, cls) {
    return '<div class="card kband' + (cls ? ' ' + cls : '') + '" style="--c:' + (cols || 4) + '">' + items.map((k) => {
      const tag = k.href ? 'a' : 'div';
      let foot = k.f || '';
      if (k.up) {
        const dlt = k.up[0];
        foot = dlt > 0 ? '<span class="up">' + ic('trending-up') + '+' + num(dlt) + ' ' + k.up[1] + '</span>'
          : dlt < 0 ? '<span class="up dn">' + ic('trending-down') + num(dlt) + ' ' + k.up[1] + '</span>'
            : '<span class="up eq">O\'tgan haftadagidek</span>';
      }
      return '<' + tag + ' class="kb"' + (k.href ? ' href="' + k.href + '"' : '') + (k.id ? ' id="' + k.id + '"' : '') + '>' +
        '<div class="l">' + ic(k.i) + '<span>' + k.l + '</span>' + (k.live ? '<span class="live"><span class="pulse" aria-hidden="true"></span>jonli</span>' : '') + '</div>' +
        '<div class="v' + (k.tx ? ' tx' : '') + '"><span class="kv">' + k.v + '</span>' + (k.u ? '<small>' + k.u + '</small>' : '') + '</div>' +
        (foot ? '<div class="f">' + foot + '</div>' : '') + '</' + tag + '>';
    }).join('') + '</div>';
  }
  function seg(key, opts, cur, label) {
    return '<div class="seg" role="group" aria-label="' + esc(label) + '">' + opts.map((o) =>
      '<button type="button" data-act="seg" data-k="' + key + '" data-v="' + o[0] + '" aria-pressed="' + (String(o[0]) === String(cur)) + '">' + o[1] + '</button>').join('') + '</div>';
  }
  function chips(key, opts, cur, label) {
    return '<div class="chips" role="group" aria-label="' + esc(label) + '">' + opts.map((o) =>
      '<button type="button" class="chip" data-act="seg" data-k="' + key + '" data-v="' + o[0] + '" aria-pressed="' + (String(o[0]) === String(cur)) + '">' + o[1] + '</button>').join('') + '</div>';
  }
  function empty(title, text) {
    return '<div class="empty"><b>' + title + '</b>' + (text ? '<p>' + text + '</p>' : '') + '</div>';
  }
  function pill(cls, icon, text) { return '<span class="pill' + (cls ? ' ' + cls : '') + '">' + (icon ? ic(icon) : '') + text + '</span>'; }
  const dia = (icon, cls) => '<span class="dia' + (cls ? ' ' + cls : '') + '" aria-hidden="true">' + ic(icon) + '</span>';
  function hbar(v, max) {
    const w = max > 0 ? clamp((v * 100) / max, 0, 100) : 0;
    return '<span class="hb" aria-hidden="true"><i' + (w ? '' : ' class="z"') + ' style="width:' + w.toFixed(1) + '%"></i></span>';
  }
  const ibar = (v, max, label, wide) => '<span class="ib' + (wide ? ' w' : '') + '">' + hbar(v, max) + '<b>' + label + '</b></span>';
  function who(name, sub, href, av) {
    const inner = '<span class="ava op" aria-hidden="true">' + esc(av || initials(name)) + '</span><span class="wt"><b>' + esc(name) + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</span>';
    return href ? '<a class="who2" href="' + href + '">' + inner + '</a>' : '<div class="who2">' + inner + '</div>';
  }
  /* cols: [{k, l, r, lead, sort, ml, cls}]; rows: [{c:{}, href, cls, group}]; o: {cards, id, caption, sort, more, all} */
  function table(cols, rows, o) {
    o = o || {};
    let h = '<div class="tw"><table class="dt' + (o.cards === false ? '' : ' cards') + (o.all ? ' all' : '') + '"' + (o.id ? ' id="' + o.id + '"' : '') + '>' +
      (o.caption ? '<caption class="sr">' + o.caption + '</caption>' : '') + '<thead><tr>';
    cols.forEach((c) => {
      const sorted = o.sort && o.sort.k === c.k;
      const cl = [c.r ? 'r' : '', c.cls || ''].join(' ').trim();
      h += '<th scope="col"' + (cl ? ' class="' + cl + '"' : '') + (sorted ? ' aria-sort="' + (o.sort.dir > 0 ? 'ascending' : 'descending') + '"' : '') + '>' +
        (c.sort ? '<button type="button" data-act="sort" data-k="' + c.k + '">' + c.l + (sorted ? (o.sort.dir > 0 ? ic('arrow-up') : ic('arrow-down')) : ic('arrow-up-down')) + '</button>' : c.l) + '</th>';
    });
    h += '</tr></thead><tbody>';
    let n = 0;
    rows.forEach((r) => {
      if (r.group) { h += '<tr class="grp"><td colspan="' + cols.length + '">' + r.group + '</td></tr>'; return; }
      const cls = ((r.href ? 'go ' : '') + (r.cls || '') + (o.more != null && n >= o.more ? ' more' : '')).trim();
      n++;
      h += '<tr' + (cls ? ' class="' + cls + '"' : '') + (r.href ? ' data-href="' + esc(r.href) + '"' : '') + '>';
      cols.forEach((c) => {
        const v = r.c[c.k];
        const cl = [c.lead ? 'lead' : c.r ? 'r' : '', c.cls || ''].join(' ').trim();
        h += '<td data-k="' + c.k + '" data-l="' + esc(c.ml || c.l) + '"' + (cl ? ' class="' + cl + '"' : '') + '>' + (v == null ? '' : v) + '</td>';
      });
      h += '</tr>';
    });
    return h + '</tbody></table></div>';
  }
  function moreBtn(id, total, shown) {
    if (total <= shown) return '';
    const open = !!S.ui.more[id];
    return '<div class="tfoot"><button type="button" class="btn ghost sm" data-act="more" data-for="' + id + '" aria-expanded="' + open + '">' +
      ic(open ? 'chevron-up' : 'chevron-down') + '<span>' + (open ? 'Qisqartirish' : 'Yana ' + (total - shown) + ' tasi') + '</span></button></div>';
  }
  /* bar ro'yxati: [{ic, l, v, sub}] */
  function barList(items, o) {
    o = o || {};
    if (!items || !items.length || !sum(items, (x) => x.v)) return empty(o.et || "Hali ma'lumot yo'q", o.ex || '');
    const total = o.total != null ? o.total : sum(items, (x) => x.v);
    const max = Math.max(1, ...items.map((x) => x.v || 0));
    const noic = !items.some((x) => x.ic);
    return '<ul class="bl' + (noic ? ' noic' : '') + (o.nopct ? ' np' : '') + (o.cls ? ' ' + o.cls : '') + '">' + items.map((x) =>
      '<li>' + (noic ? '' : x.ic ? ic(x.ic) : '<span></span>') + '<span class="n">' + x.l + (x.sub ? '<small>' + x.sub + '</small>' : '') + '</span>' +
      '<span class="c">' + (o.fmt ? o.fmt(x.v) : num(x.v)) + '</span>' + (o.nopct ? '' : '<span class="p">' + pc(x.v, total) + '%</span>') +
      hbar(x.v || 0, max) + '</li>').join('') + '</ul>';
  }
  function skeleton(kind) {
    let h = '<div class="ph" aria-hidden="true"><div class="pt"><span class="sk sk-line" style="width:140px"></span><span class="sk sk-h"></span>' +
      '<span class="sk sk-line" style="width:60%;margin-top:12px"></span></div></div>';
    if (kind !== 'plain') h += '<span class="sk sk-band" aria-hidden="true"></span>';
    return h + '<div class="row" aria-hidden="true"><span class="sk sk-big c8"></span><span class="sk sk-big c4"></span></div><p class="sr" role="status">Yuklanmoqda</p>';
  }
  function errBox(e) {
    const msg = e && e.api ? e.message : "Sahifani ko'rsatishda kutilmagan xato yuz berdi.";
    return '<div class="errbox" role="alert">' + dia('circle-alert', 'bad') + '<b>Ma\'lumotni yuklab bo\'lmadi</b><p>' + esc(msg) + '</p>' +
      '<button type="button" class="btn pri" data-act="retry">' + ic('refresh-cw') + '<span>Qayta urinish</span></button></div>';
  }
  function toast(text, err) {
    const box = $('#toasts');
    if (!box) return;
    const el = D.createElement('div');
    el.className = 'toast' + (err ? ' err' : '');
    el.innerHTML = ic(err ? 'circle-alert' : 'circle-check') + '<span>' + esc(text) + '</span>';
    box.appendChild(el);
    setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 220); }, 3200);
  }
  let dlgClose = null;
  function confirmDlg(o) {
    return new Promise((res) => {
      const root = $('#dlgRoot');
      const prev = D.activeElement;
      root.innerHTML = '<div class="dlg-bg" data-dlg="bg"><div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="dlgT" aria-describedby="dlgP">' +
        dia(o.icon || 'triangle-alert') + '<h2 id="dlgT">' + o.title + '</h2><p id="dlgP">' + o.text + '</p>' + (o.text2 ? '<p>' + o.text2 + '</p>' : '') +
        '<div class="d-acts"><button type="button" class="btn ghost" data-dlg="no">Bekor qilish</button>' +
        '<button type="button" class="btn ' + (o.cls || 'bad') + '" data-dlg="yes">' + (o.okIc ? ic(o.okIc) : '') + o.ok + '</button></div></div></div>';
      const bg = root.firstChild;
      const key = (e) => {
        if (e.key === 'Escape') { e.preventDefault(); close(false); }
        else if (e.key === 'Tab') {
          const f = $$('button', bg);
          const i = f.indexOf(D.activeElement);
          e.preventDefault();
          f[(i + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus();
        }
      };
      function close(v) {
        dlgClose = null;
        D.removeEventListener('keydown', key, true);
        root.innerHTML = '';
        try { if (prev && prev.focus) prev.focus(); } catch (e) { /* yo'q */ }
        res(v);
      }
      dlgClose = () => close(false);
      bg.addEventListener('click', (e) => {
        const a = e.target.closest('[data-dlg]');
        if (!a) return;
        if (a.dataset.dlg === 'yes') close(true);
        else if (a.dataset.dlg === 'no' || e.target === bg) close(false);
      });
      D.addEventListener('keydown', key, true);
      $('[data-dlg="no"]', bg).focus();
    });
  }

  /* ================= 6. Grafiklar (inline SVG, bitta seriya; har grafikda xulosa gapi va jadval ko'rinishi) ================= */
  function niceTop(max) {
    if (max <= 0) return { top: 1, step: 1 };
    const raw = max / 3, p = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = Math.max(1, [1, 2, 5, 10].map((x) => x * p).find((x) => x >= raw));
    return { top: Math.ceil(max / step) * step, step };
  }
  function barPath(x, y, w, h, r) {
    r = Math.min(r, w / 2, h);
    const f = (n) => n.toFixed(1);
    return 'M' + f(x) + ',' + f(y + h) + 'V' + f(y + r) + 'Q' + f(x) + ',' + f(y) + ' ' + f(x + r) + ',' + f(y) + 'H' + f(x + w - r) +
      'Q' + f(x + w) + ',' + f(y) + ' ' + f(x + w) + ',' + f(y + r) + 'V' + f(y + h) + 'Z';
  }
  /* o: {data:[{x, full, v, hl, extra}], vlab, unit, h, bw, xw, aria, cols:[xHead, vHead], empty:[title, text]} */
  function colChart(id, o) {
    o.kind = o.kind || 'col';
    S.charts[id] = o;
    const tot = sum(o.data, (d) => d.v);
    if (!o.data.length || !tot) {
      S.charts[id] = null;
      return empty((o.empty && o.empty[0]) || "Hali ma'lumot yo'q", (o.empty && o.empty[1]) || '');
    }
    const on = !!S.ui.tbl[id];
    const rows = o.data.map((d) => '<tr><td>' + esc(d.full || d.x) + '</td><td class="r">' + num(d.v) + '</td></tr>').join('');
    return '<figure class="ch" id="' + id + '" style="margin:0"><div class="plot" style="height:' + (o.h || 220) + 'px"' + (on ? ' hidden' : '') + '></div>' +
      '<div class="tbl"' + (on ? '' : ' hidden') + '><table class="dt"><caption class="sr">' + esc(o.aria) + '</caption><thead><tr><th scope="col">' + esc(o.cols[0]) + '</th><th scope="col" class="r">' + esc(o.cols[1]) + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<figcaption class="sr">' + esc(o.aria) + '</figcaption></figure>';
  }
  const tblBtn = (id) => (S.charts[id] ? '<button type="button" class="btn ghost sm" data-act="tbl" data-for="' + id + '" aria-pressed="' + !!S.ui.tbl[id] + '">' +
    ic(S.ui.tbl[id] ? 'chart-column' : 'table') + '<span>' + (S.ui.tbl[id] ? 'Grafik' : 'Jadval') + '</span></button>' : '');
  function drawChart(fig) {
    const o = S.charts[fig.id];
    if (!o) return;
    const plot = $('.plot', fig);
    if (!plot || plot.hidden) return;
    const cw = Math.floor(plot.clientWidth || fig.clientWidth || 0);
    if (cw < 40) return;
    fig._w = cw;
    const Wd = Math.max(240, cw);
    if (o.kind === 'hour') { drawHour(plot, o, Wd); return; }
    const Ht = o.h || 220, L = 40, R = 4, Tp = 22, B = 28, pw = Wd - L - R, phh = Ht - Tp - B;
    const vals = o.data.map((d) => d.v || 0), n = vals.length, max = Math.max(...vals);
    const tk = niceTop(max);
    const band = pw / n, bw = Math.min(o.bw || 34, Math.max(3, band * 0.62));
    const y = (v) => Tp + phh - (v / tk.top) * phh;
    let s = '<svg width="' + Wd + '" height="' + Ht + '" viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img" aria-label="' + esc(o.aria) + '">';
    for (let v = 0; v <= tk.top + 1e-9; v += tk.step) {
      const yy = Math.round(y(v)) + 0.5;
      s += '<line class="' + (v ? 'g' : 'bl0') + '" x1="' + L + '" x2="' + (Wd - R) + '" y1="' + yy + '" y2="' + yy + '"/><text x="' + (L - 10) + '" y="' + (yy + 4) + '" text-anchor="end">' + num(v) + '</text>';
    }
    vals.forEach((v, i) => {
      const x = L + i * band + (band - bw) / 2, yv = y(v), hh = Tp + phh - yv;
      if (hh > 0.5) s += '<path class="b' + (o.data[i].hl ? ' hl' : '') + '" data-i="' + i + '" d="' + barPath(x, yv, bw, hh, 3) + '"/>';
    });
    const imax = vals.indexOf(max);
    [imax, n - 1].filter((v, i, a) => a.indexOf(v) === i && vals[v] > 0).forEach((i) => {
      s += '<text class="vl" x="' + (L + i * band + band / 2).toFixed(1) + '" y="' + (y(vals[i]) - 7).toFixed(1) + '" text-anchor="middle">' + num(vals[i]) + '</text>';
    });
    const k = Math.max(1, Math.ceil((n * (o.xw || 52)) / pw));
    o.data.forEach((d, i) => { if ((n - 1 - i) % k) return; s += '<text x="' + (L + i * band + band / 2).toFixed(1) + '" y="' + (Ht - 8) + '" text-anchor="middle">' + esc(d.x) + '</text>'; });
    vals.forEach((v, i) => { s += '<rect class="hit" data-i="' + i + '" x="' + (L + i * band).toFixed(1) + '" y="' + Tp + '" width="' + Math.max(1, band).toFixed(1) + '" height="' + phh + '"/>'; });
    plot.innerHTML = s + '</svg>';
  }
  /* soatlar grafigi (Ko'rinish kartasi): 24 ustun, tungi soatlar (19:00-05:59) fonda */
  function drawHour(plot, o, Wd) {
    const Ht = o.h || 120, L = 2, R = 2, Tp = 18, B = 24, pw = Wd - L - R, phh = Ht - Tp - B;
    const vals = o.data.map((d) => d.v || 0), band = pw / 24, bw = Math.max(3, band * 0.64), max = Math.max(1, ...vals), imax = vals.indexOf(Math.max(...vals));
    const y = (v) => Tp + phh - (v / max) * (phh - 2);
    let s = '<svg width="' + Wd + '" height="' + Ht + '" viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img" aria-label="' + esc(o.aria) + '">';
    s += '<rect class="band" x="' + L + '" y="' + (Tp - 4) + '" width="' + (band * 6).toFixed(1) + '" height="' + (phh + 4) + '" rx="4"/>' +
      '<rect class="band" x="' + (L + band * 19).toFixed(1) + '" y="' + (Tp - 4) + '" width="' + (band * 5).toFixed(1) + '" height="' + (phh + 4) + '" rx="4"/>';
    s += '<line class="bl0" x1="' + L + '" x2="' + (Wd - R) + '" y1="' + (Tp + phh + 0.5) + '" y2="' + (Tp + phh + 0.5) + '"/>';
    vals.forEach((v, i) => {
      const x = L + i * band + (band - bw) / 2, yv = y(v), hh = Tp + phh - yv;
      if (v > 0) s += '<path class="b" data-i="' + i + '" d="' + barPath(x, yv, bw, hh, 2) + '"/>';
    });
    if (vals[imax] > 0) s += '<text class="vl" x="' + (L + imax * band + band / 2).toFixed(1) + '" y="' + (y(vals[imax]) - 6).toFixed(1) + '" text-anchor="middle">' + num(vals[imax]) + '</text>';
    [[0, '00:00', 'start'], [6, '06:00', 'middle'], [12, '12:00', 'middle'], [19, '19:00', 'middle'], [24, '24:00', 'end']].forEach((a) => {
      s += '<text x="' + (L + a[0] * band).toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="' + a[2] + '">' + a[1] + '</text>';
    });
    vals.forEach((v, i) => { s += '<rect class="hit" data-i="' + i + '" x="' + (L + i * band).toFixed(1) + '" y="' + Tp + '" width="' + band.toFixed(1) + '" height="' + phh + '"/>'; });
    plot.innerHTML = s + '</svg>';
  }
  let RO = null;
  function drawCharts() {
    Object.keys(S.charts).forEach((id) => {
      const fig = D.getElementById(id);
      if (!fig || !S.charts[id]) { delete S.charts[id]; return; }
      drawChart(fig);
      if (RO) RO.observe(fig);
    });
    drawRibbon();
  }
  if (W.ResizeObserver) {
    RO = new ResizeObserver((ents) => {
      ents.forEach((en) => {
        const fig = en.target;
        if (!D.body.contains(fig)) { RO.unobserve(fig); return; }
        const w = Math.floor(($('.plot', fig) || fig).clientWidth);
        if (w && w !== fig._w) drawChart(fig);
      });
    });
  }
  const tip = () => $('#tip');
  let tipTimer = 0;
  function showTip(hit, ev) {
    const fig = hit.closest('.ch');
    const o = fig && S.charts[fig.id];
    if (!o) return;
    const i = +hit.getAttribute('data-i'), d = o.data[i];
    if (!d) return;
    $$('.b', fig).forEach((b) => b.classList.toggle('dim', +b.getAttribute('data-i') !== i));
    const t = tip();
    t.innerHTML = o.kind === 'hour'
      ? num(d.v) + ' ochilish<small>' + p2(i) + ':00–' + p2(i) + ':59 · ' + (i >= 6 && i < 19 ? 'kunduzgi' : 'tungi') + ' soat</small>'
      : esc(o.vlab) + ': ' + num(d.v) + '<small>' + esc(d.full || d.x) + '</small>' + (d.extra ? '<small>' + d.extra + '</small>' : '');
    t.hidden = false;
    const r = hit.getBoundingClientRect();
    const bar = $('.b[data-i="' + i + '"]', fig);
    const br = bar ? bar.getBoundingClientRect() : r;
    const x = ev && ev.pointerType === 'mouse' ? ev.clientX : r.left + r.width / 2;
    const y = Math.min(br.top, r.bottom - 8);
    const tw = t.offsetWidth, th = t.offsetHeight;
    t.style.left = clamp(x - tw / 2, 8, W.innerWidth - tw - 8) + 'px';
    t.style.top = (y - th - 10 < 8 ? Math.min(W.innerHeight - th - 8, r.bottom + 10) : y - th - 10) + 'px';
    clearTimeout(tipTimer);
    if (ev && ev.pointerType !== 'mouse') tipTimer = setTimeout(hideTip, 3500);
  }
  function hideTip() {
    const t = tip();
    if (t) t.hidden = true;
    $$('.ch .b.dim').forEach((b) => b.classList.remove('dim'));
  }
  /* Safar: vaqt lentasi (har bo'lak - bitta ekran, eni o'tgan vaqtga teng) */
  function drawRibbon() {
    const rib = $('#rib');
    if (!rib || !S.rib) return;
    const Wd = rib.clientWidth;
    if (!Wd || rib._w === Wd) return;
    rib._w = Wd;
    const parts = S.rib.parts, total = Math.max(1, sum(parts, (p) => p.d));
    rib.innerHTML = parts.map((p) => {
      const w = (p.d / total) * Wd;
      return '<span class="' + (p.out ? 'out' : '') + '" style="flex-grow:' + Math.max(1, Math.round(p.d)) + '" title="' + esc(p.title) + '">' + (!p.out && w > 76 ? '<b>' + esc(p.label) + '</b>' : '') + '</span>';
    }).join('');
    const st = S.rib.start, en = S.rib.end, span = Math.max(1, en - st);
    const steps = [60e3, 120e3, 300e3, 600e3, 900e3, 1800e3, 3600e3, 7200e3, 14400e3];
    const maxL = Wd < 500 ? 3 : 5;
    const step = steps.find((x) => span / x <= maxL) || steps[steps.length - 1];
    let ax = '<span style="left:0">' + hmi(st) + '</span>';
    for (let t = Math.ceil((st + 1) / step) * step; t < en; t += step) {
      const p = (t - st) / span;
      if (p * Wd > 56 && (1 - p) * Wd > 84) ax += '<span style="left:' + (p * 100).toFixed(2) + '%">' + hmi(t) + '</span>';
    }
    ax += '<span style="left:100%">' + hms(en) + '</span>';
    $('#ribAx').innerHTML = ax;
  }

  /* ================= 7. Karkas va router ================= */
  const SEC = {
    bosh: { nomi: 'Bosh sahifa', ic: 'layout-dashboard', g: 0 },
    oquvchilar: { nomi: "O'quvchilar", ic: 'users-round', g: 0 },
    voronka: { nomi: 'Voronka', ic: 'filter', g: 0 },
    tugmalar: { nomi: 'Tugmalar va ekranlar', ic: 'mouse-pointer-click', g: 0 },
    qurilmalar: { nomi: 'Qurilmalar', ic: 'smartphone', g: 0 },
    kurs: { nomi: 'Kurs', ic: 'book-open', g: 1 },
    testlar: { nomi: 'Testlar', ic: 'list-checks', g: 1 },
    duellar: { nomi: 'Duellar', ic: 'swords', g: 2 },
    takliflar: { nomi: "Do'st takliflari", ic: 'user-plus', g: 2 },
    xodimlar: { nomi: 'Xodimlar', ic: 'user-cog', g: 3 },
    funksiyalar: { nomi: 'Funksiyalar', ic: 'toggle-right', g: 3 },
    jurnal: { nomi: 'Amallar jurnali', ic: 'history', g: 3 },
  };
  const GROUPS = ['Boshqaruv', "O'quv jarayoni", 'Faollik', 'Tizim'];
  const ROUTES = {
    bosh: { sec: 'bosh', v: vBosh },
    oquvchilar: { sec: 'oquvchilar', v: vOquvchilar },
    oquvchi: { sec: 'oquvchilar', v: vOquvchi, arg: /^\d{1,15}$/, need: true },
    sessiya: { sec: 'oquvchilar', v: vSessiya, arg: /^[0-9a-f-]{36}$/, need: true },
    voronka: { sec: 'voronka', v: vVoronka },
    tugmalar: { sec: 'tugmalar', v: vTugmalar },
    qurilmalar: { sec: 'qurilmalar', v: vQurilmalar },
    kurs: { sec: 'kurs', v: vKurs, arg: /^\d{1,3}$/ },
    testlar: { sec: 'testlar', v: vTestlar },
    test: { sec: 'testlar', v: vTest, arg: /^\d{1,3}$/, need: true },
    duellar: { sec: 'duellar', v: vDuellar },
    takliflar: { sec: 'takliflar', v: vTakliflar },
    xodimlar: { sec: 'xodimlar', v: vXodimlar },
    funksiyalar: { sec: 'funksiyalar', v: vFunksiyalar },
    jurnal: { sec: 'jurnal', v: vJurnal },
  };
  const defaultSec = () => ((S.me && S.me.sections.filter((k) => SEC[k])) || [])[0] || 'bosh';
  function parseHash() {
    let h = location.hash.replace(/^#\/?/, '');
    try { h = decodeURIComponent(h); } catch (e) { /* xom */ }
    const k = h.indexOf('/');
    const name = k < 0 ? h : h.slice(0, k), arg = k < 0 ? '' : h.slice(k + 1);
    const def = Object.prototype.hasOwnProperty.call(ROUTES, name) ? ROUTES[name] : null;
    if (!def) return null;
    if (arg && !(def.arg && def.arg.test(arg))) return null;
    if (def.need && !arg) return null;
    return { name, arg, def, nested: !!arg, hash: '#' + name + (arg ? '/' + arg : '') };
  }
  function parentOf(r) {
    if (r.name === 'oquvchi') return '#oquvchilar';
    if (r.name === 'sessiya') return S.sessUser[r.arg] ? '#oquvchi/' + S.sessUser[r.arg] : '#oquvchilar';
    if (r.name === 'kurs') return '#kurs';
    if (r.name === 'test') return '#testlar';
    return '#' + defaultSec();
  }
  function goBack() {
    if (dlgClose) { dlgClose(); return; }
    const sh = $('#shell');
    if (sh && sh.classList.contains('open')) { menu(false); return; }
    const r = parseHash();
    if (S.stack.length > 1) { history.back(); return; }
    location.hash = r ? parentOf(r) : '#' + defaultSec();
  }
  const sig = '<span class="nq-sig" aria-hidden="true"><i></i><i></i><i></i></span>';
  function shell() {
    const me = S.me, name = fullName(me.user);
    let nav = '';
    GROUPS.forEach((g, gi) => {
      const items = Object.keys(SEC).filter((k) => SEC[k].g === gi && me.sections.indexOf(k) >= 0);
      if (!items.length) return;
      nav += '<div class="ng">' + esc(g) + '</div>' + items.map((k) =>
        '<a class="ni" href="#' + k + '" data-sec="' + k + '">' + ic(SEC[k].ic) + '<span>' + esc(SEC[k].nomi) + '</span>' +
        (me.access[k] === 'read' ? '<span class="bdg">ko\'rish</span>' : '') + '</a>').join('');
    });
    const brand = esc(me.brend || 'Muhammadamin');
    const rol = esc(me.rol_nomi || me.role);
    return '<div class="ap" id="shell">' +
      '<aside class="side" id="side" aria-label="Bo\'limlar">' +
      '<div class="side-top"><a class="brand" href="#' + defaultSec() + '">' + sig + '<span><b>' + brand + '</b><small>Admin panel</small></span></a>' +
      '<button type="button" class="ibtn side-x" data-act="menu-close" aria-label="Menyuni yopish">' + ic('x') + '</button></div>' +
      '<nav class="nav" aria-label="Bo\'limlar">' + nav + '</nav>' +
      '<div class="me"><span class="ava" aria-hidden="true">' + esc(initials(name)) + '</span><span><b>' + esc(name) + '</b><small>' + rol + (inTg ? ' · Telegram' : ' · brauzer') + '</small></span>' +
      (me.browser ? '<button type="button" class="ibtn" data-act="logout" aria-label="Chiqish" title="Chiqish">' + ic('log-out') + '</button>' : '') + '</div>' +
      '<div class="side-sc" aria-hidden="true"><div data-scene data-focus="card"></div></div>' +
      '</aside><div class="scrim" data-act="menu-close"></div>' +
      '<div class="main"><header class="top">' +
      '<button type="button" class="ibtn menu-b" data-act="menu" aria-label="Menyu" aria-controls="side" aria-expanded="false">' + ic('menu') + '</button>' +
      '<button type="button" class="ibtn back-b" data-act="back" aria-label="Orqaga">' + ic('arrow-left') + '</button>' +
      '<span class="top-t" id="topT"></span>' +
      (has('oquvchilar') ? '<form class="search" role="search" data-form="tsearch">' + ic('search') + '<label class="sr" for="tq">O\'quvchi qidirish</label>' +
        '<input id="tq" type="search" placeholder="O\'quvchi qidirish: ism yoki @username" autocomplete="off" spellcheck="false" enterkeyhint="search"><kbd aria-hidden="true">/</kbd></form>' : '') +
      '<div class="r"><span class="upd tab" id="upd"></span><button type="button" class="ibtn" data-act="refresh" aria-label="Yangilash" title="Yangilash">' + ic('refresh-cw') + '</button>' +
      '<span class="who" title="' + esc(name) + '"><span class="ava" aria-hidden="true">' + esc(initials(name)) + '</span><span class="rl">' + rol + '</span><span class="sr">' + esc(name) + ', ' + rol + '</span></span></div>' +
      '</header><main class="pg" id="page" tabindex="-1"></main></div></div>';
  }
  function menu(open) {
    const sh = $('#shell');
    if (!sh) return;
    const was = sh.classList.contains('open');
    sh.classList.toggle('open', open);
    const b = $('.menu-b', sh);
    if (b) b.setAttribute('aria-expanded', String(open));
    if (open) { scenes($('#side')); const a = $('.ni[aria-current="page"]', sh) || $('.ni', sh); if (a) a.focus(); }
    else if (was && b && W.innerWidth <= 760 && $('#side').contains(D.activeElement)) b.focus();
  }
  function setChrome(r, allowed) {
    $$('.ni').forEach((a) => { if (allowed && a.dataset.sec === r.def.sec) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    const sh = $('#shell');
    const nested = allowed && r.nested;
    sh.classList.toggle('nested', nested);
    tgBack(nested);
  }
  function setTitle(t) {
    const tt = $('#topT');
    if (tt) tt.textContent = t;
    D.title = t + ' · Muhammadamin · Admin panel';
  }
  function setUpd() {
    const u = $('#upd');
    if (u && S.updAt) u.textContent = 'Yangilangan ' + hmi(S.updAt);
  }
  function clearTimers() { S.timers.forEach((t) => clearInterval(t)); S.timers = []; }
  function onHash() {
    if (!S.me || S.gated) return;
    const h = location.hash, st = S.stack;
    if (st.length > 1 && st[st.length - 2] === h) st.pop();
    else if (st[st.length - 1] !== h) st.push(h);
    if (st.length > 60) st.shift();
    render();
  }
  async function render(soft) {
    if (!S.me || S.gated) return;
    const r = parseHash();
    if (!r) {
      const d = '#' + defaultSec();
      history.replaceState(null, '', d);
      S.stack = [d];
      return render();
    }
    clearTimers();
    hideTip();
    menu(false);
    D.body.removeAttribute('data-ready');
    S.route = r;
    const allowed = has(r.def.sec);
    setChrome(r, allowed);
    const tk = ++S.view;
    const page = $('#page');
    if (!allowed) {
      setTitle("Ruxsat yo'q");
      S.charts = {};
      S.rib = null;
      page.innerHTML = blocked();
      D.body.setAttribute('data-ready', r.hash);
      W.scrollTo(0, 0);
      return;
    }
    setTitle(SEC[r.def.sec].nomi);
    let skT = 0;
    if (soft) skT = setTimeout(() => { if (tk === S.view) page.innerHTML = skeleton(); }, 180);
    else { S.charts = {}; S.rib = null; page.innerHTML = skeleton(r.nested ? 'plain' : ''); W.scrollTo(0, 0); }
    try {
      await r.def.v(r, tk, soft);
    } catch (e) {
      if (!alive(tk)) return;
      if (e && e.status === 401) return;
      if (!(e && e.api)) console.error(e);
      page.innerHTML = errBox(e);
      D.body.setAttribute('data-ready', r.hash);
    } finally {
      clearTimeout(skT);
    }
  }
  /* sahifa mazmunini qo'yish (faqat shu ko'rinish hali joriy bo'lsa) */
  function put(tk, html) {
    if (!alive(tk)) return false;
    const page = $('#page');
    page.innerHTML = html;
    drawCharts();
    scenes(page);
    setUpd();
    D.body.setAttribute('data-ready', S.route ? S.route.hash : '');  /* sinov uchun: ko'rinish tayyor */
    return true;
  }
  function blocked() {
    return '<div class="errbox" role="alert">' + dia('lock', 'off') + '<b>Bu bo\'lim sizga ochiq emas</b>' +
      '<p>Rolingiz (' + esc(S.me.rol_nomi || S.me.role) + ') bu bo\'limni ko\'ra olmaydi. Kerak bo\'lsa, CEO dan ruxsat so\'rang.</p>' +
      '<a class="btn pri" href="#' + defaultSec() + '">' + ic('arrow-left') + '<span>Asosiy bo\'limga o\'tish</span></a></div>';
  }
  function gate(code, msg, data, after) {
    S.gated = true;
    clearTimers();
    tgBack(false);
    const bot = data && (data.bot || data.xodim_bot);
    const brand = '<div class="brand">' + sig + '<span><b>' + esc((S.me && S.me.brend) || 'Muhammadamin') + '</b><small>Admin panel</small></span></div>';
    const botA = bot ? '<a href="https://t.me/' + esc(bot) + '" target="_blank" rel="noopener">@' + esc(bot) + '</a>' : '';
    let h;
    if (code === 401 && !inTg) {
      h = dia('log-in') +
        (after ? '<h1>Siz admin paneldan chiqdingiz</h1>' : '<h1>Kirish uchun xodimlar botiga <span class="code">/kirish</span> deb yozing</h1>') +
        (after ? '<p>Kirish uchun xodimlar botiga <span class="code">/kirish</span> deb yozing.</p>' :
          '<p>Admin panel brauzerda bir martalik havola orqali ochiladi.' + (msg && /muddati/.test(msg) ? ' Oldingi kirish muddati tugagan.' : '') + '</p>') +
        '<ol class="steps"><li><b>1</b><span>Telegramda xodimlar botini oching' + (botA ? ': ' + botA : '') + '.</span></li>' +
        '<li><b>2</b><span><span class="code">/kirish</span> deb yozing.</span></li>' +
        '<li><b>3</b><span>«Admin panelni ochish» tugmasini bosing. Havola 10 daqiqa amal qiladi va bir marta ishlaydi.</span></li></ol>' +
        '<div class="acts"><button type="button" class="btn pri" data-act="reload">' + ic('refresh-cw') + '<span>Qayta tekshirish</span></button></div>';
    } else if (code === 401) {
      h = dia('log-in') + '<h1>Kirish tasdiqlanmadi</h1><p>' + esc(msg || 'Boshqaruvni xodimlar boti orqali qayta oching.') + '</p>' +
        '<div class="acts"><button type="button" class="btn pri" data-act="reload">' + ic('refresh-cw') + '<span>Qayta urinish</span></button></div>';
    } else if (code === 403) {
      const generic = "Bu bo'lim sizga ochiq emas";
      h = dia('lock', 'off') + '<h1>' + generic + '</h1>' +
        '<p>' + (msg && msg !== generic ? esc(msg) + '. ' : '') + 'Admin panel CEO, admin va ustozlar uchun. Sizning ishlaringiz xodimlar botida.</p>' +
        (!inTg ? '<div class="acts"><button type="button" class="btn sec" data-act="logout">' + ic('log-out') + '<span>Boshqa akkaunt bilan kirish</span></button></div>' : '');
    } else {
      h = dia('circle-alert', 'bad') + '<h1>Server bilan aloqa yo\'q</h1><p>' + esc(msg || "Internetni tekshirib, qayta urinib ko'ring.") + '</p>' +
        '<div class="acts"><button type="button" class="btn pri" data-act="reload">' + ic('refresh-cw') + '<span>Qayta urinish</span></button></div>';
    }
    $('#app').innerHTML = '<div class="gate"><div class="gate-box">' + brand + '<div class="card gate-card" role="alert">' + h + '</div></div>' +
      '<div class="gate-sc" aria-hidden="true"><div data-scene data-focus="full"></div></div></div>';
    scenes($('#app'));
    D.title = 'Kirish · Muhammadamin · Admin panel';
  }

  /* ================= 8. Ekranlar ================= */
  const MZ = (k) => NVN[k] || '';
  const offNote = (key, nomi) => (S.me && S.me.features && S.me.features[key] === false
    ? '<div class="note warn" role="status">' + ic('triangle-alert') + '<span><b>«' + esc(nomi) + '» funksiyasi hozir o\'chirilgan:</b> o\'quvchilar ilovada bu bo\'limni ko\'rmaydi.' +
      (has('funksiyalar') ? ' <a href="#funksiyalar">Funksiyalar</a> bo\'limida yoqish mumkin.' : '') + '</span></div>' : '');
  const stuLink = (p) => (p && p.id && has('oquvchilar') ? '#oquvchi/' + p.id : '');

  /* ---------- 8.1 Bosh sahifa ---------- */
  const KIND = {
    lesson_done: ['book-check', (x) => esc(x.ref) + 'ni tugatdi'],
    test_done: ['list-checks', (x) => esc(x.ref) + ' testini yechdi'],
    video_done: ['circle-play', (x) => esc(x.ref) + ' videosini ko\'rdi'],
    duel_done: ['swords', (x) => ({ yutdi: 'Duelda yutdi', yutqazdi: 'Duelda yutqazdi', durrang: 'Duelda durrang' }[x.result] || 'Duel tugadi') + (x.ref ? ' · ' + esc(x.ref) : '')],
  };
  function liveHtml(d) {
    const live = d.live || [];
    const list = live.length ? '<ul class="lv">' + live.map((x) => {
      const inner = '<span class="ava op" aria-hidden="true">' + esc(initials(x.name)) + '</span><span><b>' + esc(x.name) + '</b><small>' + esc(x.screen_label || x.screen || DASH) + ' · ' + esc(x.device_label || DASH) + '</small></span>' +
        '<span class="r">' + (x.since ? '<b>' + dur(Date.now() - ms(x.since)) + '</b><small>' + hmi(x.since) + ' dan</small>' : '') + '</span>';
      return '<li>' + (x.session_id && has('oquvchilar') ? '<a class="li" href="#sessiya/' + esc(x.session_id) + '">' + inner + '</a>' : '<div class="li">' + inner + '</div>') + '</li>';
    }).join('') + '</ul>' : empty('Hozir hech kim ilovada emas', "O'quvchi ilovani ochishi bilan shu yerda paydo bo'ladi.");
    return list + '<div class="lv-f">' + ic('refresh-cw') + '<span class="tab">Har 30 soniyada yangilanadi · oxirgisi ' + hms(Date.now()) + '</span></div>';
  }
  function heroText(d) {
    const old = d.oldingi || {};
    let s = d.active_today ? 'Bugun ' + num(d.active_today) + ' o\'quvchi ilovaga kirdi' : 'Bugun hali hech kim ilovaga kirmadi';
    s += d.active_now ? ', hozir ilovada — ' + num(d.active_now) + ' kishi.' : '.';
    if (old.active_7d != null) {
      const dl = (d.active_7d || 0) - old.active_7d;
      s += dl > 0 ? ' Oxirgi 7 kunda faol o\'quvchilar o\'tgan haftadagidan ' + num(dl) + ' taga ko\'p.'
        : dl < 0 ? ' Oxirgi 7 kunda faol o\'quvchilar o\'tgan haftadagidan ' + num(-dl) + ' taga kam.'
          : ' Oxirgi 7 kunda faol o\'quvchilar o\'tgan haftadagidek.';
    }
    return s;
  }
  function takeDaily(daily, met) {
    if (daily.length < 14) return '';
    const last = daily.slice(-7), prev = daily.slice(-14, -7);
    if (met === 'xp') {
      const a = sum(last, (x) => x.xp), b = sum(prev, (x) => x.xp);
      if (!a && !b) return '';
      if (!b) return 'Oxirgi 7 kunda ' + num(a) + ' ball to\'plandi.';
      const ch = Math.round(((a - b) * 100) / b);
      return 'Oxirgi 7 kunda ' + num(a) + ' ball to\'plandi — ' + (ch > 0 ? 'oldingi 7 kundagidan ' + ch + '% ko\'p.' : ch < 0 ? 'oldingi 7 kundagidan ' + (-ch) + '% kam.' : 'oldingi 7 kundagidek.');
    }
    const a = sum(last, (x) => x.active) / 7, b = sum(prev, (x) => x.active) / 7;
    if (!a && !b) return '';
    const fa = num(a, 1), fb = num(b, 1);
    if (fa === fb) return 'Oxirgi 7 kunda kunlik faol o\'quvchilar o\'rtacha ' + fa + ' ta — oldingi haftadagidek.';
    return 'Oxirgi 7 kunda kunlik faol o\'quvchilar o\'rtacha ' + fb + ' tadan ' + fa + ' taga ' + (a > b ? 'ko\'tarildi.' : 'tushdi.');
  }
  /* "Eng ko'p bosish 3-oktabrda bo'ldi — 218 ta; kunlik o'rtacha 150 ta." */
  function takeMax(data, pre, post, unit, jami) {
    const tot = sum(data, (x) => x.v);
    if (!tot) return '';
    let mi = 0;
    data.forEach((x, i) => { if (x.v > data[mi].v) mi = i; });
    const avg = tot / data.length;
    return pre + ' ' + dlong(data[mi].day) + 'da ' + post + ' — ' + num(data[mi].v) + NB + unit + '; ' +
      (jami ? 'davr bo\'yicha jami ' + num(tot) : 'kunlik o\'rtacha ' + num(avg, avg >= 10 ? 0 : 1)) + NB + unit + '.';
  }
  /* Ko'rinish kartasi (Bosh sahifa va Qurilmalar): manzaralar, tanlov, kun/tun, soatlar */
  function korinishCard(k, chartId, cls) {
    k = k || {};
    const mz = k.manzara || [], tot = sum(mz, (x) => x.sessions), users = k.users || 0;
    const hours = (k.soat || []).map((x) => ({ x: p2(x.hour) + ':00', v: x.opens || 0 }));
    const opens = sum(hours, (x) => x.v);
    const since = k.since && ms(k.since) > Date.now() - (k.days || 14) * 864e5 ? ' · ' + dlong(k.since) + 'dan beri' : '';
    const sub = 'Oxirgi ' + (k.days || 14) + ' kun · ' + num(tot) + ' ochilish · ' + num(users) + ' o\'quvchi' + since;
    const acts = has('funksiyalar') ? '<a class="link" href="#funksiyalar">Manzara tanlash funksiyasi' + ic('chevron-right') + '</a>' : '';
    let take = '';
    if (tot) { const t0 = mz[0]; take += esc(t0.label) + ' eng ko\'p ochilgan — ochilishlarning ' + pc(t0.sessions, tot) + ' foizi.'; }
    if (opens) {
      const night = sum(hours.filter((x, i) => i >= 19 || i < 6), (x) => x.v);
      let pk = 0;
      hours.forEach((x, i) => { if (x.v > hours[pk].v) pk = i; });
      const np = pc(night, opens);
      take += (take ? ' ' : '') + (night === 0 ? 'Ilova faqat kunduzgi soatlarda ochilgan' : night === opens ? 'Ilova faqat tungi soatlarda (19:00–05:59) ochilgan'
        : 'Ilova ochilishlarining ' + (np || 1) + ' foizi tungi soatlarda (19:00–05:59)') + ', eng qizg\'in soat — ' + p2(pk) + ':00.';
    }
    if (!tot && !opens) return card({ title: "Ko'rinish", sub, acts, cls: 'korc' + (cls ? ' ' + cls : ''), body: empty("Ko'rinish ma'lumoti hali yo'q", "O'quvchilar ilovani ochganda qaysi manzara va qaysi rejimda ochilgani shu yerda chiqadi.") });
    const mmax = Math.max(1, ...mz.map((x) => x.sessions));
    const left = tot ? '<h3>Qaysi manzara ko\'p ochilgan</h3><ul class="mzl">' + mz.map((m) =>
      '<li><span class="th" data-v="' + esc(m.key) + '" aria-hidden="true"><span data-scene data-focus="thumb"></span></span>' +
      '<span class="nm"><b>' + esc(m.label) + '</b><small>' + (m.tanlagan ? ic('pin') + num(m.tanlagan) + ' kishi tanlagan' : 'tanlaganlar yo\'q') + '</small></span>' +
      hbar(m.sessions, mmax) + '<span class="c">' + num(m.sessions) + '</span><span class="p">' + pc(m.sessions, tot) + '%</span></li>').join('') + '</ul>'
      : '<h3>Qaysi manzara ko\'p ochilgan</h3>' + empty('Manzara hali yozilmagan', 'Ilovaning yangi ko\'rinishi ochilganda paydo bo\'ladi.');
    const tn = k.tanlov || {}, tl = (tn.tanlangan || 0) + (tn.aylan || 0);
    const mv = k.mavzu || {}, ml = (mv.kun || 0) + (mv.tun || 0);
    let right = '';
    if (tl) {
      right += '<h3>Manzara tanlovi</h3><div class="duo">' +
        '<div><div class="dl"><span class="sw2" aria-hidden="true"></span>' + ic('pin') + 'O\'zi tanlagan</div><div class="dv">' + pc(tn.tanlangan, tl) + '%<small>' + num(tn.tanlangan) + ' o\'quvchi</small></div></div>' +
        '<div><div class="dl"><span class="sw2 s" aria-hidden="true"></span>' + ic('shuffle') + 'Har ochilganda almashadi</div><div class="dv">' + pc(tn.aylan, tl) + '%<small>' + num(tn.aylan) + ' o\'quvchi</small></div></div></div>' +
        '<div class="split" aria-hidden="true"><i style="flex:' + (tn.tanlangan || 0) + '"></i><i style="flex:' + (tn.aylan || 0) + '"></i></div><div class="gap"></div>';
    }
    if (ml) {
      right += '<h3>Kunduzgi va tungi</h3><div class="duo">' +
        '<div><div class="dl">' + ic('sun') + 'Kunduzgi</div><div class="dv">' + pc(mv.kun, ml) + '%<small>' + num(mv.kun) + ' ochilish</small></div></div>' +
        '<div><div class="dl">' + ic('moon') + 'Tungi</div><div class="dv">' + pc(mv.tun, ml) + '%<small>' + num(mv.tun) + ' ochilish</small></div></div></div>';
    }
    right += (ml ? '' : '<h3>Ilova ochilishlari soatlar bo\'yicha</h3>') + '<div style="margin-top:12px">' + colChart(chartId, { kind: 'hour', data: hours, h: 120, aria: 'Ilova ochilishlari soatlar bo\'yicha, jami ' + opens,
      cols: ['Soat', 'Ochilishlar'], empty: ["Bu davrda ilova ochilmagan", ''] }) + '</div>' +
      (opens ? '<div class="legend"><span class="sw0" aria-hidden="true"></span>Fon — tungi soatlar (19:00–05:59), ustun — soatdagi ochilishlar</div>' : '');
    return card({ title: "Ko'rinish", sub, acts, take, cls: 'korc' + (cls ? ' ' + cls : ''), flush: true, body: '<div class="ko-g"><div>' + left + '</div><div>' + right + '</div></div>' });
  }
  async function vBosh(r, tk) {
    const days = S.ui.bdays;
    const d = await api('/api/x/overview?days=' + days);
    if (!alive(tk)) return;
    const old = d.oldingi || {};
    const k = [
      { l: "O'quvchilar", v: num(d.students), i: 'users-round', f: "Jami ro'yxatdan o'tgan", href: has('oquvchilar') ? '#oquvchilar' : '' },
      { l: 'Hozir ilovada', v: num(d.active_now), i: 'activity', f: 'Oxirgi 5 daqiqada', live: true, id: 'kNow' },
      { l: 'Bugun faol', v: num(d.active_today), i: 'calendar-check', f: pc(d.active_today, d.students) + '% o\'quvchilar' },
      { l: '7 kunda faol', v: num(d.active_7d), i: 'calendar-days', up: old.active_7d != null ? [(d.active_7d || 0) - old.active_7d, 'o\'tgan haftaga nisbatan'] : null, f: pc(d.active_7d, d.students) + '% o\'quvchilar' },
      { l: 'Yangi (7 kun)', v: num(d.new_7d), i: 'user-plus', up: old.new_7d != null ? [(d.new_7d || 0) - old.new_7d, 'o\'tgan haftaga nisbatan'] : null, f: "So'nggi 7 kunda qo'shilgan" },
      { l: 'Bugungi sessiyalar', v: num(d.sessions_today), i: 'smartphone', f: 'Ilova bugun necha marta ochilgan' },
      { l: "O'rtacha sessiya", v: num(d.avg_session_min, 1), u: 'daq', i: 'timer', f: 'Bugungi sessiyalar bo\'yicha' },
      { l: 'Tugatilgan darslar', v: num(d.lessons_done), i: 'book-check', f: num(d.tests_done) + ' test · ' + num(d.videos_done) + ' video', href: has('kurs') ? '#kurs' : '' },
    ];
    const met = S.ui.bmetric;
    const daily = d.daily || [];
    const chart = colChart('chBosh', {
      data: daily.map((x) => ({ x: dday(x.day), full: dfull(x.day), v: met === 'xp' ? x.xp : x.active, extra: met === 'xp' ? 'Faol: ' + num(x.active) + ' kishi' : 'Ball: ' + num(x.xp) })),
      vlab: met === 'xp' ? 'Ball' : "Faol o'quvchilar", cols: ['Kun', met === 'xp' ? 'Ball' : "Faol o'quvchilar"], aria: 'Kunlik faollik, oxirgi ' + days + ' kun: ' + (met === 'xp' ? 'ball' : "faol o'quvchilar"),
      h: 232, bw: days > 20 ? 16 : 30, xw: 52, empty: ['Hali faollik yo\'q', 'O\'quvchilar darslarni ochishi bilan grafik to\'ladi.'],
    });
    const recent = (d.recent || []).slice(0, 10);
    const recentH = recent.length ? table([{ k: 'n', l: "O'quvchi" }, { k: 'a', l: 'Harakat' }, { k: 'r', l: 'Natija', r: true }, { k: 't', l: 'Qachon', r: true }],
      recent.map((x) => { const kd = KIND[x.kind] || ['activity', (q) => esc(q.ref)]; return { c: { n: '<b>' + esc(x.name) + '</b>', a: '<span class="act">' + ic(kd[0]) + '<span>' + kd[1](x) + '</span></span>', r: x.natija ? esc(x.natija) : '<span class="mu">' + DASH + '</span>', t: '<span class="mu nowrap">' + rel(x.at) + '</span>' } }; }),
      { cards: false, id: 'recTbl', caption: "So'nggi faollik" })
      : '<div class="card-b">' + empty("Hali faollik yo'q", "O'quvchilar dars tugatganda, test yechganda, video ko'rganda yoki duel o'ynaganda shu yerda chiqadi.") + '</div>';
    const devTot = sum(d.devices, (x) => x.users);
    const devs = (d.devices || []).map((x) => ({ l: esc(x.label), v: x.users, ic: devIc(x.label) }));
    const du = d.duels || {};
    const duelH = barList([{ l: "G'olib aniqlangan", v: du.decided || 0, ic: 'trophy' }, { l: 'Durrang', v: du.draws || 0, ic: 'scale' },
      { l: 'Davom etmoqda', v: du.active || 0, ic: 'hourglass' }, { l: "Muddati o'tgan", v: du.expired || 0, ic: 'clock' }], { total: du.total, et: "Bu davrda duel bo'lmagan", ex: "O'quvchilar ilovadagi Duellar bo'limidan bellashuv boshlaydi." });
    const name = fullName(S.me.user);
    const html = '<section class="hero" aria-labelledby="hBosh"><div data-scene data-focus="hero" aria-hidden="true"></div><div class="hx">' +
      '<div class="kick">Bosh sahifa · ' + esc(todayLong()) + '</div><h1 id="hBosh" tabindex="-1"><span data-nq="salom">' + greet() + '</span>, ' + esc(name) + '</h1><p>' + heroText(d) + '</p></div></section>' +
      kband(k, 4, 'kpis') +
      '<div class="row st">' +
      card({ cls: 'c8', title: 'Kunlik faollik', sub: 'Oxirgi ' + days + ' kun · ' + (met === 'xp' ? "to'plangan ball" : "faol o'quvchilar, kishi"),
        acts: seg('bmetric', [['active', "Faol o'quvchilar"], ['xp', 'Ball']], met, "Ko'rsatkich") + seg('bdays', [[14, '14 kun'], [30, '30 kun']], days, 'Davr') + tblBtn('chBosh'),
        take: takeDaily(daily, met), body: chart }) +
      '<section class="card c4 livec" id="liveBox" aria-labelledby="hLive" aria-live="polite"><div class="card-h"><div><h2 id="hLive">Hozir ilovada</h2><p class="sub">Oxirgi 5 daqiqada faol · ismni bosing, safari ochiladi</p></div>' +
      '<div class="acts"><span class="live"><span class="pulse" aria-hidden="true"></span>jonli</span></div></div><div id="liveBody" class="livec" style="flex:1">' + liveHtml(d) + '</div></section></div>' +
      '<div class="row st">' + korinishCard(d.korinish, 'chSoat', 'c8') +
      card({ cls: 'c4', title: 'Qurilmalar', sub: "Oxirgi 30 kun · har o'quvchi bir marta", acts: has('qurilmalar') ? '<a class="link" href="#qurilmalar">Batafsil' + ic('chevron-right') + '</a>' : '',
        body: barList(devs, { total: devTot, et: "Hali qurilma ma'lumoti yo'q", ex: "O'quvchilar ilovani ochganda paydo bo'ladi." }) }) + '</div>' +
      '<div class="row st">' + card({ cls: 'c8', title: "So'nggi faollik", sub: 'Darslar, testlar, videolar va duellar', flush: true, body: recentH }) +
      card({ cls: 'c4', title: 'Duellar', sub: 'Oxirgi ' + (du.days || days) + ' kun · ' + num(du.total || 0) + ' ta duel' + (S.me.features && S.me.features.duel === false ? ' · funksiya o\'chirilgan' : ''),
        acts: has('duellar') ? '<a class="link" href="#duellar">Batafsil' + ic('chevron-right') + '</a>' : '', body: duelH }) + '</div>';
    if (!put(tk, html)) return;
    S.timers.push(setInterval(async () => {
      try {
        const n = await api('/api/x/overview?days=' + days, { fresh: true });
        if (!alive(tk)) return;
        const lb = $('#liveBody'), kv = $('#kNow .kv');
        if (lb) lb.innerHTML = liveHtml(n);
        if (kv) kv.textContent = num(n.active_now);
        setUpd();
      } catch (e) { /* jim: keyingi safar */ }
    }, 30000));
  }

  /* ---------- 8.2 O'quvchilar ---------- */
  const SORTS = {
    last: ['Oxirgi faollik', (s) => ms(s.last_seen) || 0, -1],
    xp: ['Ball', (s) => s.xp || 0, -1],
    lessons: ['Darslar', (s) => s.lessons_done || 0, -1],
    sessions: ['Sessiyalar', (s) => s.sessions || 0, -1],
    joined: ["Qo'shilgan sana", (s) => ms(s.joined_at) || 0, -1],
    name: ['Ism', (s) => String(s.name || '').toLowerCase(), 1],
    device: ['Qurilma', (s) => String(s.device_label || 'zzz').toLowerCase(), 1],
  };
  function studentsTable(list) {
    const k = S.ui.ssort, dir = S.ui.sdir, f = SORTS[k][1];
    list.sort((a, b) => { const x = f(a), y = f(b); return x < y ? -dir : x > y ? dir : 0; });
    if (!list.length) return '<div class="card-b">' + empty(S.ui.sq ? 'Hech kim topilmadi' : "Hali o'quvchi yo'q", S.ui.sq ? "Boshqa ism yoki @username bilan qidirib ko'ring." : "O'quvchilar talabalar botiga /start yozganda shu yerda paydo bo'ladi.") + '</div>';
    const jami = S.jami || 36;
    const cols = [
      { k: 'name', l: "O'quvchi", lead: true, sort: true }, { k: 'device', l: 'Qurilma', sort: true, cls: 'hide-t' }, { k: 'lessons', l: 'Darslar', sort: true },
      { k: 'xp', l: 'Ball', r: true, sort: true }, { k: 'streak', l: 'Seriya', r: true, cls: 'hide-t' }, { k: 'sessions', l: 'Sessiyalar', r: true, sort: true },
      { k: 'joined', l: "Qo'shilgan", sort: true, cls: 'hide-t' }, { k: 'last', l: 'Oxirgi faollik', sort: true },
    ];
    const rows = list.map((s) => ({
      href: '#oquvchi/' + s.id,
      c: {
        name: who(s.name || ('ID ' + s.id), s.username ? '@' + esc(s.username) : 'ID ' + s.id, '#oquvchi/' + s.id),
        device: s.device_label ? '<span class="ic1">' + ic(devIc(s.device_label)) + esc(s.device_label) + '</span>' : '<span class="mu">Ma\'lumot yo\'q</span>',
        lessons: ibar(s.lessons_done || 0, jami, num(s.lessons_done || 0) + '/' + jami, true),
        xp: '<b class="num">' + num(s.xp) + '</b>', streak: num(s.streak) + NB + 'kun', sessions: num(s.sessions || 0),
        joined: '<span class="nowrap">' + dday(s.joined_at) + '</span>', last: '<span class="nowrap">' + rel(s.last_seen) + '</span>',
      },
    }));
    return table(cols, rows, { sort: { k, dir }, caption: "O'quvchilar ro'yxati" });
  }
  let sqTimer = 0;
  async function refreshStudents() {
    const box = $('#stuBody'), cnt = $('#stuCnt');
    if (!box) return;
    const tk = S.view;
    try {
      const q = S.ui.sq.trim();
      const d = await api('/api/x/students' + (q ? '?q=' + encodeURIComponent(q) : ''));
      if (!alive(tk)) return;
      box.innerHTML = studentsTable(d.students.slice());
      if (cnt) cnt.textContent = num(d.students.length) + ' ta o\'quvchi' + (q ? ' topildi' : '') + (d.students.length >= 500 ? ' (eng faol 500 tasi)' : '');
    } catch (e) {
      if (alive(tk) && e.status !== 401) box.innerHTML = errBox(e);
    }
  }
  async function vOquvchilar(r, tk) {
    const q = S.ui.sq.trim();
    const d = await api('/api/x/students' + (q ? '?q=' + encodeURIComponent(q) : ''));
    if (!alive(tk)) return;
    const sortSel = '<label class="sr" for="ssort">Saralash</label><span class="sel"><select id="ssort">' + Object.keys(SORTS).map((k) =>
      '<option value="' + k + '"' + (k === S.ui.ssort ? ' selected' : '') + '>Saralash: ' + esc(SORTS[k][0]) + '</option>').join('') + '</select>' + ic('chevron-down') + '</span>';
    const html = ph({ crumb: 'Boshqaruv', title: "O'quvchilar", text: "Har bir o'quvchining qurilmasi, darslari va ilovadagi safari. Qatorni bosing, to'liq karta ochiladi." }) +
      '<section class="card" aria-labelledby="hStu"><div class="card-h"><div><h2 id="hStu">O\'quvchilar ro\'yxati</h2><p class="sub" id="stuCnt">' + num(d.students.length) + ' ta o\'quvchi' + (q ? ' topildi' : '') + '</p></div></div>' +
      '<div class="toolbar"><div class="field">' + ic('search') + '<label class="sr" for="sq">O\'quvchi qidirish</label><input id="sq" type="search" placeholder="Ism yoki @username" value="' + esc(S.ui.sq) + '" autocomplete="off" spellcheck="false" enterkeyhint="search"></div>' + sortSel + '</div>' +
      '<div id="stuBody" class="cbody" style="margin-top:14px">' + studentsTable(d.students.slice()) + '</div></section>';
    put(tk, html);
  }

  /* ---------- 8.3 O'quvchi kartasi ---------- */
  const isLive = (s) => !s.ended && Date.now() - ms(s.last_at) < 5 * 60e3;
  function sessState(s) {
    if (isLive(s)) return '<span class="live"><span class="pulse" aria-hidden="true"></span>Hozir ilovada</span>';
    if (!s.ended) return pill('warn', 'circle-alert', 'Signal uzilgan');
    return pill('', 'log-out', 'Yakunlangan');
  }
  const korText = (s) => (s && s.manzara ? '<span class="ic1">' + ic(s.mavzu === 'tun' ? 'moon' : 'sun') + esc(MZ(s.manzara)) + (s.aylan === false ? ' ' + ic('pin') : '') + '</span>' : '<span class="mu">' + DASH + '</span>');
  async function vOquvchi(r, tk) {
    const d = await api('/api/x/student?id=' + r.arg);
    if (!alive(tk)) return;
    const u = d.user || {}, name = u.name || fullName(u);
    setTitle(name);
    const sess = d.sessions || [];
    sess.forEach((s) => { S.sessUser[s.id] = u.id; });
    const liveS = sess.find(isLive);
    const lessons = d.lessons || [], jami = lessons.length || S.jami || 36;
    const doneN = lessons.filter((l) => l.done_at).length, startN = lessons.filter((l) => !l.done_at && l.seen > 0).length;
    const st = d.stats || {}, pr = d.prefs || {};
    const vids = d.videos || [], vdone = vids.filter((v) => v.done_at).length;
    const head = '<header class="ph"><div class="pt">' + crumbHtml([['#oquvchilar', "O'quvchilar"], [null, 'Karta']]) +
      '<div class="prof" style="margin-top:10px"><span class="ava xl" aria-hidden="true">' + esc(initials(name)) + '</span><div><h1 tabindex="-1" style="margin-top:0">' + esc(name) + '</h1>' +
      '<div class="meta">' + (u.username ? '<span class="tag">' + ic('at-sign') + esc(u.username) + '</span>' : '') + '<span class="tag">ID ' + esc(u.id) + '</span>' +
      '<span class="tag">' + ic('calendar') + 'Qo\'shilgan: ' + dday(u.joined_at) + '</span><span class="tag">' + ic('clock') + 'Oxirgi faollik: ' + rel(u.last_seen) + '</span>' +
      (liveS ? '<span class="live"><span class="pulse" aria-hidden="true"></span>Hozir ilovada</span>' : '') + (u.blocked ? pill('bad', 'ban', 'Botni bloklagan') : '') + '</div></div></div></div>' +
      (sess.length ? '<div class="acts"><a class="btn pri" href="#sessiya/' + esc(sess[0].id) + '">' + ic('footprints') + '<span>Oxirgi safarni ko\'rish</span></a></div>' : '') + '</header>';
    const kp = kband([
      { l: 'Ball', v: num(st.xp), i: 'gem', f: 'Bugun: +' + num(st.today_xp || 0) },
      { l: 'Seriya', v: num(st.streak), u: 'kun', i: 'flame', f: 'Eng uzun: ' + num(st.best_streak) + NB + 'kun' },
      { l: 'Tugatgan darslar', v: num(doneN), u: '/ ' + jami, i: 'book-check', f: num(startN) + ' ta dars boshlangan' },
      { l: 'Sessiyalar', v: num(d.sessions_total != null ? d.sessions_total : sess.length), i: 'smartphone', f: sess.length ? 'Oxirgisi: ' + rel(sess[0].started_at) : "Hali sessiya yo'q" },
    ], 4, 'kpis');
    const sessH = sess.length ? table([
      { k: 'at', l: 'Boshlandi · qurilma', lead: true }, { k: 'dur', l: 'Davomiyligi' }, { k: 'ko', l: "Ko'rinish" },
      { k: 'sc', l: 'Ekran · bosish', ml: 'Ekranlar va bosishlar' }, { k: 'st', l: 'Holat' },
    ], sess.map((s) => ({
      href: '#sessiya/' + s.id,
      c: {
        at: '<span class="c2"><a class="nm nowrap" href="#sessiya/' + esc(s.id) + '">' + dt(s.started_at) + '</a><small>' + ic(devIc(s.device_label)) + esc(s.device_label || DASH) + '</small></span>',
        dur: '<span class="nowrap">' + dur((s.dur_s || 0) * 1000) + '</span>', ko: korText(s),
        sc: '<span class="nowrap">' + num(s.screens) + ' · ' + num(s.clicks) + '</span>', st: sessState(s),
      },
    })), { caption: 'Sessiyalar' }) + ((d.sessions_total || 0) > sess.length ? '<p class="sub" style="padding:10px 20px 14px;font-size:12px;color:var(--t2)">Jami ' + num(d.sessions_total) + ' ta sessiya, oxirgi ' + sess.length + ' tasi ko\'rsatilgan.</p>' : '')
      : '<div class="card-b">' + empty("Hali sessiya yo'q", "O'quvchi ilovani ochganda har bir kirishi shu yerda safar bo'lib chiqadi.") + '</div>';
    const devH = (d.devices || []).length ? '<ul class="lst">' + d.devices.map((x) => '<li>' + dia(devIc(x.label), 'sm s') + '<span class="lt"><b>' + esc(x.label || DASH) + '</b><small>' +
      esc(uniq([x.os, PLAT[x.platform] || x.platform, x.tg_version ? 'Telegram ' + x.tg_version : '', x.screen ? scrSize(x.screen) : '']).join(' · ')) + '</small></span>' +
      '<span class="lr"><b>' + num(x.sessions) + ' sessiya</b>' + rel(x.last_at) + '</span></li>').join('') + '</ul>' : '<div class="card-b">' + empty("Qurilma ma'lumoti yo'q", '') + '</div>';
    const lastK = sess.find((s) => s.manzara);
    const prefH = '<dl class="kv"><dt>Manzara</dt><dd>' + (lastK ? esc(MZ(lastK.manzara)) + '<small>' + (lastK.aylan === false ? 'o\'zi tanlagan' : 'har ochilganda almashadi') + '</small>' : DASH) + '</dd>' +
      '<dt>Rejim</dt><dd>' + esc(REJIM[pr.rejim] || DASH) + (pr.rejim === 'auto' ? '<small>vaqtga qarab</small>' : '') + '</dd><dt>Arabcha matn</dt><dd>' + esc(ARAB[pr.arab] || DASH) + '</dd>' +
      '<dt>Kunlik eslatma</dt><dd>' + (pr.eslatma ? 'Yoqilgan' : "O'chirilgan") + '</dd></dl>';
    const wk = st.week || [], wmax = Math.max(1, ...wk.map((w) => w.xp || 0));
    const weekH = wk.length ? '<div class="blk" style="margin-top:18px"><h3>Oxirgi 7 kunlik ball</h3><div class="weekbars" role="img" aria-label="Oxirgi 7 kunlik ball: ' + wk.map((w) => num(w.xp)).join(', ') + '">' +
      wk.map((w) => '<div title="' + esc(dday(w.day) + ': ' + num(w.xp) + ' ball') + '"><i' + (w.xp ? '' : ' class="z"') + ' style="height:' + Math.max(3, Math.round((w.xp * 100) / wmax)) + '%"></i><small>' + KUNQ[tz(w.day).getUTCDay()] + '</small></div>').join('') + '</div></div>' : '';
    const du = d.duels, ib = d.invited_by;
    const socialH = (du || d.invited != null || ib) ? card({ title: 'Duellar va takliflar', body:
      (du ? '<div class="blk"><h3>Duellar</h3><dl class="kv"><dt>O\'ynagan</dt><dd>' + num(du.played) + ' ta</dd>' +
        '<dt>Natija</dt><dd>' + num(du.won) + ' g\'alaba · ' + num(du.lost) + ' mag\'lubiyat · ' + num(du.draw) + ' durrang</dd>' +
        '<dt>Davom etmoqda</dt><dd>' + num(du.active || 0) + '</dd><dt>Muddati o\'tgan</dt><dd>' + num(du.expired || 0) + '</dd></dl></div>' : '') +
      '<div class="blk"><h3>Takliflar</h3><dl class="kv">' +
      '<dt>Taklif qilgan</dt><dd>' + num(d.invited || 0) + ' ta do\'st' + (d.invited_rewarded != null ? '<small>' + num(d.invited_rewarded) + ' tasi bonus olgan</small>' : '') + '</dd>' +
      '<dt>Taklif bonusi</dt><dd>' + (d.taklif_xp ? '+' + num(d.taklif_xp) + ' ball' : DASH) + '</dd>' +
      '<dt>Kim taklif qilgan</dt><dd>' + (ib ? (has('oquvchilar') ? '<a class="nm" href="#oquvchi/' + esc(ib.id) + '">' + esc(ib.name) + '</a>' : esc(ib.name)) +
        '<small>' + (ib.at ? dday(ib.at) + ' · ' : '') + (ib.rewarded ? 'bonus berilgan' : '1-darsni kutmoqda') + '</small>' : "O'zi kelgan") + '</dd></dl></div>' }) : '';
    const lgrid = lessons.length ? '<div class="lgrid">' + lessons.map((l) => {
      const p = l.slaydlar ? clamp(Math.round((l.seen * 100) / l.slaydlar), 0, 100) : 0;
      const cls = l.done_at ? 'done' : l.seen > 0 ? 'part' : '';
      const tip2 = l.n + '-dars · ' + (l.nomi || '') + ' · ' + num(l.seen) + '/' + num(l.slaydlar) + ' slayd' + (l.done_at ? ' · tugatilgan ' + dday(l.done_at) : l.started_at ? ' · boshlangan ' + dday(l.started_at) : ' · boshlanmagan');
      const inner = l.n + (l.done_at ? ic('check') : l.seen > 0 ? '<small>' + p + '%</small>' : '') + (cls === 'part' ? '<span class="lp" style="width:' + p + '%"></span>' : '');
      return has('kurs') ? '<a class="lc ' + cls + '" href="#kurs/' + l.n + '" title="' + esc(tip2) + '" aria-label="' + esc(tip2) + '">' + inner + '</a>' : '<div class="lc ' + cls + '" title="' + esc(tip2) + '">' + inner + '</div>';
    }).join('') + '</div><div class="legend2"><span><i class="d"></i>Tugatgan: ' + doneN + '</span><span><i class="p"></i>Boshlagan: ' + startN + '</span><span><i></i>Boshlanmagan: ' + (jami - doneN - startN) + '</span></div>'
      : empty("Darslar ma'lumoti yo'q", '');
    const tests = d.tests || [];
    const testH = tests.length ? '<ul class="lst">' + tests.map((t) => {
      const ok = t.total && t.best === t.total, ratio = t.best / (t.total || 1);
      const ans = t.last_answers || [];
      return '<li style="align-items:flex-start">' + dia('list-checks', 'sm s') + '<span class="lt"><b>' + esc(t.dars) + '-dars testi ' + pill(ok ? 'ok' : ratio >= 0.6 ? '' : 'warn', ok ? 'circle-check' : '', num(t.best) + '/' + num(t.total)) + '</b>' +
        '<small>' + num(t.tries) + ' urinish · oxirgisi ' + dt(t.updated_at) + '</small>' +
        (ans.length ? '<div class="qa" aria-label="Oxirgi urinish javoblari">' + ans.map((a) => '<span class="' + (a.pick == null ? 'sk0' : a.ok ? 'ok' : 'no') + '" title="' + esc(a.q + '-savol: ' + (a.pick == null ? 'javobsiz' : 'ABCDEFGH'.charAt(a.pick) + ' variant, ' + (a.ok ? "to'g'ri" : "noto'g'ri"))) + '">' +
          ic(a.pick == null ? 'circle' : a.ok ? 'check' : 'x') + a.q + '-savol' + (a.pick == null ? '' : ' · ' + 'ABCDEFGH'.charAt(a.pick)) + '</span>').join('') + '</div>' :
          '<small style="margin-top:6px">Savollar bo\'yicha natija 03.10 dan keyingi urinishlardan</small>') + '</span>' +
        (has('testlar') ? '<span class="lr"><a class="link" href="#test/' + esc(t.dars) + '">Tahlil' + ic('chevron-right') + '</a></span>' : '') + '</li>';
    }).join('') + '</ul>' : '<div class="card-b">' + empty("Hali test yechmagan", '') + '</div>';
    const vidH = vids.length ? '<ul class="lst">' + vids.map((v) => {
      const p = v.davomiylik ? clamp(Math.round(((v.pos || 0) * 100) / v.davomiylik), 0, 100) : 0;
      return '<li style="align-items:flex-start">' + dia(v.done_at ? 'circle-check' : 'circle-play', 'sm ' + (v.done_at ? 'ok' : 's')) + '<span class="lt"><b>' + esc(v.dars) + '-dars · ' + T(v.nomi) + '</b><small>' +
        (v.done_at ? "Ko'rilgan · " + dday(v.done_at) : v.pos > 0 ? dur(v.pos * 1000) + ' / ' + dur(v.davomiylik * 1000) + ' (' + p + '%)' : 'Boshlanmagan · ' + dur(v.davomiylik * 1000)) + '</small>' +
        '<span class="vbar" aria-hidden="true"><i style="width:' + (v.done_at ? 100 : p) + '%"></i></span></span>' + (v.done_at ? '<span class="lr">' + pill('ok', 'check', "Ko'rilgan") + '</span>' : '') + '</li>';
    }).join('') + '</ul>' : '<div class="card-b">' + empty("Kursda hali video yo'q", '') + '</div>';
    const html = head + kp +
      '<div class="row">' + card({ cls: 'c8', title: 'Ilovadagi safarlar', sub: 'Har bir kirish: qaysi ekranlar ochilgan, qaysi tugmalar bosilgan', flush: true, body: '<div style="margin-top:14px">' + sessH + '</div>' }) +
      '<div class="c4 stack">' + card({ title: 'Qurilmalar', flush: true, body: '<div style="margin-top:6px">' + devH + '</div>' }) + card({ title: 'Sozlamalar', sub: 'Ilovadagi ko\'rinish va eslatma', body: prefH + weekH }) + '</div></div>' +
      card({ cls: 'mb', title: 'Darslar', sub: num(doneN) + ' / ' + jami + ' tugatilgan' + (has('kurs') ? ' · katakni bosing, dars bo\'yicha slaydlar tahlili ochiladi' : ''), body: lgrid }) +
      '<div class="row">' + card({ cls: 'c6', title: 'Testlar', sub: 'Oxirgi urinishdagi har bir savol', flush: true, body: '<div style="margin-top:6px">' + testH + '</div>' }) +
      '<div class="c6 stack">' + card({ title: 'Videolar', sub: num(vdone) + ' / ' + vids.length + " ko'rilgan", flush: true, body: '<div style="margin-top:6px">' + vidH + '</div>' }) + socialH + '</div></div>';
    put(tk, html);
  }

  /* ---------- 8.4 Sessiya safari (timeline) ---------- */
  const SCR_IC = { bosh: 'house', darslar: 'book-open', video: 'circle-play', reyting: 'trophy', profil: 'user-round', dars: 'presentation', kitob: 'book-open-text',
    player: 'monitor-play', mashq: 'list-checks', natija: 'medal', xato: 'circle-alert', yuklanmoqda: 'loader-circle', qollanma: 'book-marked',
    duellar: 'swords', duel: 'swords', 'duel-natija': 'medal', taklif: 'user-plus', 'ob-korinish': 'image', 'ob-rejim': 'sun-moon', 'ob-3': 'sun-moon' };
  const scrIc = (n) => SCR_IC[n] || (/^sheet-/.test(n || '') ? 'layers' : /^ob-/.test(n || '') ? 'sparkles' : 'panels-top-left');
  const CLK_IC = { back: 'arrow-left', 'tg-back': 'arrow-left', lesson: 'book-open', video: 'circle-play', vids: 'circle-play', quiz: 'list-checks', pick: 'mouse-pointer-click',
    'qz-check': 'check', 'qz-next': 'chevron-right', 'qz-restart': 'rotate-ccw', 'qz-retry': 'rotate-ccw', 'test-retry': 'rotate-ccw', retry: 'rotate-ccw',
    'vw-next': 'chevron-right', 'dk-next': 'chevron-right', 'vw-prev': 'chevron-left', 'dk-prev': 'chevron-left', 'vw-finish': 'flag', 'dk-finish': 'flag',
    'vw-zoom': 'zoom-in', 'zm-s': 'zoom-in', davr: 'calendar-range', tab: 'panel-bottom', kitob: 'book-open-text', 'sheet-close': 'x', 'sheet-bg': 'x',
    'duel-start': 'play', 'duel-pick': 'mouse-pointer-click', 'taklif-share': 'send', 'duel-share': 'send', 'set-manzara': 'image', 'set-aylanish': 'shuffle',
    'set-rejim': 'sun-moon', 'set-esl': 'bell', 'qollanma-open': 'book-marked' };
  const clkIc = (n) => CLK_IC[n] || (/^duel-/.test(n || '') ? 'swords' : /^taklif-/.test(n || '') ? 'user-plus' : /^(set-|ob-)/.test(n || '') ? 'settings' : 'mouse-pointer-click');
  /* ref uchun o'qiladigan nom: server ref_label (duel -> "Kamola Y. bilan", video -> "2-dars videosi"); xom id ko'rsatilmaydi */
  function refName(e) {
    if (e.ref_label) return e.ref_label;
    const r = e.ref;
    if (r == null || r === '') return '';
    if (/^\d+$/.test(r) && e.kind === 'screen') return r + '-dars';
    return '';
  }
  function clickText(e) {
    let t = esc(e.label || e.name);
    if ((e.name === 'pick' || e.name === 'duel-pick') && /^\d$/.test(e.ref || '')) t += ': ' + 'ABCDEFGH'.charAt(+e.ref) + ' variant';
    else if (e.ref_label && String(e.label || '').indexOf(':') < 0) t += ': ' + esc(e.ref_label);
    return t;
  }
  function journey(s, tl) {
    const out = [];
    let cur = null, lastEnd = null;
    const close = (t, dms) => { if (cur && cur.dur == null) cur.dur = dms != null ? dms : Math.max(0, t - cur.t); };
    tl.forEach((e) => {
      const t = ms(e.at);
      if (e.kind === 'screen') {
        if (cur && !cur.closed) close(t, cur.cont ? null : e.dur_ms);
        cur = { k: 'visit', name: e.name, label: e.label || e.name, tag: refName(e), t, at: e.at, clicks: [] };
        out.push(cur);
      } else if (e.kind === 'click') {
        if (!cur || cur.closed) { cur = { k: 'visit', name: e.screen, label: e.screen_label || e.screen || 'Ekran', tag: '', t, at: e.at, clicks: [], implicit: true }; out.push(cur); }
        cur.clicks.push(e);
      } else if (e.kind === 'end') {
        if (cur && !cur.closed) { close(t, cur.cont ? null : e.dur_ms); cur.closed = true; }
        lastEnd = { k: 'end', t, at: e.at };
        out.push(lastEnd);
      } else if (e.kind === 'resume') {
        out.push({ k: 'resume', t, at: e.at, away: lastEnd ? t - lastEnd.t : null });
        cur = { k: 'visit', name: e.screen || e.name, label: e.screen_label || e.screen || e.name || 'Ekran', tag: '', t, at: e.at, clicks: [], cont: true };
        out.push(cur);
        lastEnd = null;
      }
    });
    if (cur && !cur.closed && cur.dur == null) { cur.dur = Math.max(0, ms(s.last_at) - cur.t); cur.open = true; }
    return out;
  }
  function groupClicks(cl) {
    const g = [];
    cl.forEach((e) => {
      const txt = clickText(e), last = g[g.length - 1];
      if (last && last.txt === txt) { last.n++; last.lastAt = e.at; } else g.push({ txt, n: 1, at: e.at, lastAt: e.at, name: e.name });
    });
    return g;
  }
  const tlItem = (cls, time, icon, body) => '<li class="' + cls + '"><time class="tt">' + time + '</time><span class="tn" aria-hidden="true">' + ic(icon) + '</span><div class="tb">' + body + '</div></li>';
  function timelineHtml(s, items, live) {
    const visits = items.filter((x) => x.k === 'visit');
    const maxDur = Math.max(1, ...visits.map((v) => v.dur || 0));
    const kor = s.manzara ? ' · manzara: ' + MZ(s.manzara) : '';
    let h = '<ol class="tl' + (S.ui.tlClicks ? '' : ' hide') + '">' + tlItem('k-start', hms(s.started_at), 'log-in', '<div class="th2"><b>Ilovaga kirdi</b></div><div class="tsub">' +
      esc(uniq([s.device_label, s.tg_version ? 'Telegram ' + s.tg_version : PLAT[s.platform] || s.platform]).join(' · ') + kor) + '</div>');
    items.forEach((it) => {
      if (it.k === 'visit') {
        const nowHere = it.open && live;
        let b = '<div class="th2"><b>' + esc(it.label) + '</b>' + (it.tag ? '<span class="tag">' + esc(it.tag) + '</span>' : '') +
          '<span class="tdur' + (nowHere ? ' now' : '') + '">' + ic('clock') + dur(it.dur) + (nowHere ? ' · hozir shu yerda' : '') + '</span></div>';
        const sub = [];
        if (it.cont) sub.push('Ilovaga qaytgach shu ekranda davom etdi');
        sub.push(it.clicks.length ? num(it.clicks.length) + ' ta bosish' : 'Tugma bosilmadi');
        b += '<div class="tsub">' + sub.join(' · ') + '</div><div class="tbar" aria-hidden="true"><i style="width:' + Math.max(1, Math.round(((it.dur || 0) * 100) / maxDur)) + '%"></i></div>';
        if (it.clicks.length) {
          b += '<ul class="tc" aria-label="Bosilgan tugmalar">' + groupClicks(it.clicks).map((g) => '<li><time>' + hms(g.at) + '</time>' + ic(clkIc(g.name)) +
            '<span>' + g.txt + (g.n > 1 ? '<span class="x">' + g.n + ' marta</span><small>' + hms(g.lastAt) + ' gacha</small>' : '') + '</span></li>').join('') + '</ul>';
        }
        h += tlItem('k-visit', hms(it.at), scrIc(it.name), b);
      } else if (it.k === 'end') {
        h += tlItem('k-end', hms(it.at), 'log-out', '<div class="th2"><b>Ilovadan chiqdi</b></div><div class="tsub">Ilova yopildi yoki fonga o\'tdi</div>');
      } else if (it.k === 'resume') {
        h += tlItem('k-resume', hms(it.at), 'rotate-ccw', '<div class="th2"><b>Ilovaga qaytdi</b></div>' + (it.away != null ? '<div class="tgap">' + dur(it.away) + ' tashqarida bo\'ldi</div>' : ''));
      }
    });
    const last = items[items.length - 1];
    if (live) {
      h += tlItem('k-live', hms(s.last_at), 'activity', '<div class="th2"><b>Hozir ilovada</b><span class="live"><span class="pulse" aria-hidden="true"></span>jonli</span></div><div class="tsub">Oxirgi harakat: ' + hms(s.last_at) + '. Sahifa har 30 soniyada yangilanadi.</div>');
    } else if (s.ended && !(last && last.k === 'end')) {
      h += tlItem('k-end', hms(s.ended_at), 'log-out', '<div class="th2"><b>Ilovadan chiqdi</b></div>');
    } else if (!s.ended) {
      h += tlItem('k-end', hms(s.last_at), 'log-out', '<div class="th2"><b>Ilovadan chiqdi</b></div><div class="tsub">Aniq vaqt noma\'lum: oxirgi signal ' + hms(s.last_at) + ' da keldi (ilova to\'satdan yopilgan yoki internet uzilgan).</div>');
    }
    return h + '</ol>';
  }
  function pathHtml(items, live) {
    const arr = '<span class="pa" aria-hidden="true">' + ic('chevron-right') + '</span>';
    const parts = ['<span class="pc st">' + ic('log-in') + 'Kirdi</span>'];
    items.forEach((it) => {
      if (it.k === 'visit') parts.push('<span class="pc">' + ic(scrIc(it.name)) + esc(it.label) + (it.tag ? ' <small>' + esc(it.tag) + '</small>' : '') + ' <small>' + dur(it.dur) + '</small></span>');
      else if (it.k === 'end') parts.push('<span class="pc en">' + ic('log-out') + 'Chiqdi</span>');
      else if (it.k === 'resume') parts.push('<span class="pc">' + ic('rotate-ccw') + 'Qaytdi</span>');
    });
    if (live) parts.push('<span class="pc now"><span class="pulse" aria-hidden="true"></span>Hozir shu yerda</span>');
    else if (!items.length || items[items.length - 1].k !== 'end') parts.push('<span class="pc en">' + ic('log-out') + 'Chiqdi</span>');
    const shown = parts.length > 44 ? parts.slice(0, 40).concat(['<span class="pc"><small>yana ' + (parts.length - 41) + ' qadam</small></span>', parts[parts.length - 1]]) : parts;
    return '<div class="path">' + shown.map((p, i) => (i < shown.length - 1 ? '<span class="pgr">' + p + arr + '</span>' : p)).join('') + '</div>';
  }
  async function vSessiya(r, tk, soft) {
    const d = await api('/api/x/session?id=' + r.arg, soft === 'live' ? { fresh: true } : {});
    if (!alive(tk)) return;
    const s = d.session || {}, u = d.user || {}, tl = d.timeline || [];
    S.sessUser[r.arg] = u.id;
    const live = isLive(s);
    const items = journey(s, tl);
    const visits = items.filter((x) => x.k === 'visit');
    const clicksN = sum(visits, (v) => v.clicks.length);
    const byScr = {};
    visits.forEach((v) => { const k = v.label; byScr[k] = byScr[k] || { l: esc(k), v: 0, ic: scrIc(v.name) }; byScr[k].v += v.dur || 0; });
    const spentTot = sum(visits, (v) => v.dur || 0);
    const agg = Object.keys(byScr).map((k) => byScr[k]).sort((a, b) => b.v - a.v);
    const spent = agg.slice(0, 5).concat(agg.length > 5 ? [{ l: 'Boshqa ' + (agg.length - 5) + ' ekran', ic: 'layers', v: sum(agg.slice(5), (x) => x.v) }] : []);
    const nm = u.name || ('ID ' + u.id);
    setTitle('Ilovadagi safar');
    const endAt = live ? Date.now() : ms(s.ended ? s.ended_at : s.last_at);
    /* vaqt lentasi: ekranlar + ilovadan tashqarida o'tgan vaqt */
    const parts = [];
    items.forEach((it) => {
      if (it.k === 'visit') parts.push({ d: Math.max(0, it.dur || 0), label: it.label, title: hms(it.at) + ' · ' + it.label + ' · ' + dur(it.dur) });
      else if (it.k === 'resume' && it.away) parts.push({ d: it.away, out: true, title: dur(it.away) + ' ilovadan tashqarida' });
    });
    S.rib = parts.length ? { parts, start: ms(s.started_at), end: Math.max(endAt, ms(s.started_at) + 1000) } : null;
    const chip = live ? '<span class="live"><span class="pulse" aria-hidden="true"></span>Hozir ilovada</span>' : s.ended ? pill('', 'log-out', 'Sessiya tugagan') : pill('warn', 'circle-alert', 'Signal uzilgan');
    const sumCard = '<section class="card c8 sumc" aria-labelledby="hSum"><div class="sm-h"><span class="ava lg" aria-hidden="true">' + esc(initials(nm)) + '</span><div><h2 id="hSum">' + esc(nm) + '</h2>' +
      '<p>' + esc(dfull(s.started_at)) + ' · ' + esc(uniq([s.device_label, s.tg_version ? 'Telegram ' + s.tg_version : '']).join(' · ')) + '</p></div>' + chip + '</div>' +
      '<div class="sm-m"><div><div class="v">' + hms(s.started_at) + '</div><div class="l">Kirdi</div></div>' +
      '<div><div class="v">' + (live ? '<span class="pulse" aria-hidden="true"></span>Hozir' : hms(s.ended ? s.ended_at : s.last_at)) + '</div><div class="l">' + (live ? 'Ilovada' : 'Chiqdi') + '</div></div>' +
      '<div><div class="v">' + dur((s.dur_s || 0) * 1000) + '</div><div class="l">Ilovada bo\'ldi</div></div>' +
      '<div><div class="v">' + num(visits.length) + '</div><div class="l">Ekran ochildi</div></div>' +
      '<div><div class="v">' + num(clicksN || s.clicks) + '</div><div class="l">Tugma bosildi</div></div></div>' +
      (S.rib ? '<div class="rib-w"><div class="hd"><span class="kick">Vaqt lentasi</span><span>Har bo\'lak — bitta ekran, eni o\'tgan vaqtga teng</span></div>' +
        '<div class="rib" id="rib" aria-hidden="true"></div><div class="rib-ax" id="ribAx" aria-hidden="true"></div></div>' : '') + '</section>';
    const korDd = s.manzara ? esc(MZ(s.manzara)) + (s.aylan == null ? '' : '<small class="in"> · ' + (s.aylan === false ? 'o\'zi tanlagan' : 'almashib turadi') + '</small>') : DASH + '<small>05.10 gacha yozilmagan</small>';
    const rejDd = s.mavzu ? esc(MAVZU[s.mavzu]) + (s.rejim ? '<small class="in"> · ' + (s.rejim === 'auto' ? 'avto' : 'o\'zi tanlagan') + '</small>' : '') : esc(REJIM[s.rejim] || DASH);
    const devCard = card({ cls: 'c4', title: "Qurilma va ko'rinish", sub: 'Shu sessiya bo\'yicha', body: '<dl class="kv"><dt>Qurilma</dt><dd>' + esc(s.device_label || DASH) + '</dd><dt>Tizim</dt><dd>' + esc(s.os || DASH) + '</dd>' +
      '<dt>Telegram</dt><dd>' + esc((PLAT[s.platform] || s.platform || DASH) + (s.tg_version ? ' · ' + s.tg_version : '')) + '</dd><dt>Ekran</dt><dd class="tab">' + scrSize(s.screen) + '</dd>' +
      '<dt>Telegram mavzusi</dt><dd>' + esc(SCHEME[s.scheme] || DASH) + '</dd><dt>Manzara</dt><dd>' + korDd + '</dd><dt>Rejim</dt><dd>' + rejDd + '</dd></dl>' +
      (s.ua ? '<details class="ua"><summary>Brauzer ma\'lumoti</summary><p>' + esc(s.ua) + '</p></details>' : '') });
    const head = ph({ crumb: [['#oquvchilar', "O'quvchilar"], ['#oquvchi/' + esc(u.id), esc(nm)], [null, 'Safar']], title: 'Ilovadagi safar',
      text: "Ilovaga kirgandan chiqqunigacha: qaysi ekranlar ochilgan, har birida qancha vaqt o'tgan va qaysi tugmalar bosilgan.",
      acts: '<a class="btn sec" href="#oquvchi/' + esc(u.id) + '">' + ic('user-round') + '<span>O\'quvchi kartasi</span></a>' });
    const tlCard = card({ cls: 'c8', title: 'Qadamma-qadam', sub: 'Vaqt Toshkent bo\'yicha · o\'ngdagi son — shu ekranda o\'tgan vaqt',
      acts: tl.length ? '<button type="button" class="chip tg" data-act="tl-clicks" aria-pressed="' + S.ui.tlClicks + '">' + ic('mouse-pointer-click') + 'Tugmalarni ko\'rsatish</button>' : '',
      body: tl.length ? timelineHtml(s, items, live) : empty("Bu sessiyada qadamlar yozilmagan", "Ilova ochilgan, lekin ekran yoki tugma ma'lumoti kelmagan.") });
    const side = '<div class="c4 stack stk">' + card({ title: "Vaqt qayerda o'tdi", sub: 'Ekranlar bo\'yicha, jami ' + dur(spentTot), body: barList(spent, { total: spentTot, fmt: dur, et: "Ma'lumot yo'q" }) }) +
      card({ title: "Yo'l xaritasi", sub: 'Ekranlar ketma-ketligi', body: pathHtml(items, live) }) + '</div>';
    const html = head + '<div class="row st">' + sumCard + devCard + '</div><div class="row">' + tlCard + side + '</div>';
    if (!put(tk, html)) return;
    if (live) S.timers.push(setInterval(() => { if (alive(tk)) liveRefresh(); }, 30000));
  }
  async function liveRefresh() {
    const y = W.scrollY;
    await render('live');
    W.scrollTo(0, y);
  }

  /* ---------- 8.5 Voronka ---------- */
  async function vVoronka(r, tk) {
    const days = S.ui.fdays;
    const d = await api('/api/x/funnel?days=' + days);
    if (!alive(tk)) return;
    const steps = d.steps || [], first = steps.length ? steps[0].users : 0;
    const max = Math.max(1, ...steps.map((x) => x.users || 0));
    let big = null;
    for (let i = 1; i < steps.length; i++) {
      const drop = steps[i - 1].users - steps[i].users;
      if (drop > 0 && (!big || drop > big.drop)) big = { i, drop, pct: pc(drop, steps[i - 1].users) };
    }
    let fun = '';
    steps.forEach((x, i) => {
      if (i > 0) {
        const drop = steps[i - 1].users - x.users, p = pc(drop, steps[i - 1].users);
        fun += '<li class="drop"><span aria-hidden="true"></span><span>' + (drop > 0
          ? pill(p >= 30 ? 'bad' : p >= 15 ? 'warn' : '', 'trending-down', '−' + num(drop) + ' kishi (' + p + '%)' + (big && big.i === i ? " · eng katta yo'qotish" : ''))
          : '<span class="dp">' + ic('arrow-down') + 'yo\'qotish yo\'q</span>') + '</span></li>';
      }
      fun += '<li' + (x.users ? '' : ' class="fz"') + '><span class="fn">' + (i + 1) + '</span><span class="fl"><b>' + esc(x.nomi) + '</b><small>boshidan ' + pc(x.users, first) + '%</small></span>' +
        '<span class="ft" aria-hidden="true"><i style="width:' + (x.users ? Math.max(1, (x.users * 100) / max) : 0).toFixed(1) + '%"></i></span><span class="fv">' + num(x.users) + '<small>kishi</small></span></li>';
    });
    const lm = S.ui.lmetric;
    const lessons = d.lessons || [];
    const chart = colChart('chLes', { data: lessons.map((l) => ({ x: String(l.n), full: l.n + '-dars · ' + (l.nomi || ''), v: lm === 'started' ? l.started : l.done,
      extra: 'Boshlagan: ' + num(l.started) + ' · Tugatgan: ' + num(l.done) + (l.started ? ' (' + pc(l.done, l.started) + '%)' : '') })),
    vlab: lm === 'started' ? 'Boshlagan' : 'Tugatgan', cols: ['Dars', lm === 'started' ? 'Boshlagan' : 'Tugatgan'], aria: "Har bir dars bo'yicha o'quvchilar soni", xw: 26, bw: 18, h: 240,
    empty: ['Hali hech kim dars boshlamagan', ''] });
    const key = lm === 'started' ? 'started' : 'done';
    const l1 = lessons[0], far = lessons.filter((l) => l[key] > 0).pop();
    const takeL = l1 && far ? '1-darsni ' + num(l1[key]) + ' kishi ' + (key === 'done' ? 'tugatgan' : 'boshlagan') + '; eng uzoq ' + (key === 'done' ? 'tugatilgan' : 'boshlangan') + ' dars — ' + far.n + '-dars (' + num(far[key]) + ' kishi).' : '';
    const pick = steps.filter((x) => ['kirdi', 'd1_tugatdi', 'd5_tugatdi', 'd36_tugatdi'].indexOf(x.key) >= 0);
    const summary = '<section class="card mb" aria-labelledby="hFun0"><div class="openc"><div class="kick">' + days + ' kun · ' + num(d.joined || 0) + ' ta yangi o\'quvchi</div>' +
      (big ? '<h2 id="hFun0">Eng katta yo\'qotish: ' + esc(steps[big.i - 1].nomi) + ' → ' + esc(steps[big.i].nomi) + '</h2><p>' + num(big.drop) + ' kishi (' + big.pct + '%) shu bosqichda to\'xtagan. Shu joyni yaxshilash eng ko\'p foyda beradi.</p>'
        : '<h2 id="hFun0">Yo\'qotish yo\'q</h2><p>Barcha bosqichlarda o\'quvchilar soni kamaymagan.</p>') + '</div>' +
      '<div class="sm-m" style="--c:' + pick.length + '">' + pick.map((x) => '<div><div class="v">' + num(x.users) + ' <small style="font-size:12px;color:var(--t2)">' + pc(x.users, first) + '%</small></div><div class="l">' + esc(x.nomi) + '</div></div>').join('') + '</div></section>';
    const html = ph({ crumb: 'Boshqaruv', title: 'Voronka', text: "O'quvchi ilovaga kirgandan kursni tugatguncha qaysi bosqichda to'xtayotganini ko'rsatadi. Davrda qo'shilgan o'quvchilar hisoblanadi.",
      acts: seg('fdays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) +
      (d.joined ? summary + card({ cls: 'mb', title: "O'quvchi yo'li", sub: dday(d.since) + ' dan beri qo\'shilgan ' + num(d.joined) + ' kishi', body: '<ol class="fun">' + fun + '</ol>' })
        : card({ cls: 'mb', title: "O'quvchi yo'li", body: empty("Bu davrda yangi o'quvchi qo'shilmagan", "Davrni uzaytirib ko'ring.") })) +
      card({ title: "Darslar bo'yicha", sub: "Barcha o'quvchilar, " + lessons.length + ' dars · ustunni bosing yoki ustiga olib boring', acts: seg('lmetric', [['done', 'Tugatgan'], ['started', 'Boshlagan']], lm, "Ko'rsatkich") + tblBtn('chLes'), take: S.charts.chLes ? takeL : '', body: chart });
    put(tk, html);
  }

  /* ---------- 8.6 Tugmalar va ekranlar ---------- */
  async function vTugmalar(r, tk) {
    const days = S.ui.cdays;
    const d = await api('/api/x/clicks?days=' + days);
    if (!alive(tk)) return;
    const top = d.top || [], scr = d.screens || [], daily = d.daily || [];
    const totC = sum(daily, (x) => x.clicks), totV = sum(daily, (x) => x.views);
    const longS = scr.reduce((a, b) => ((b.avg_ms || 0) > ((a && a.avg_ms) || 0) ? b : a), null);
    const tmax = Math.max(1, ...top.map((x) => x.count));
    const topH = top.length ? table([{ k: 'n', l: '#', cls: 'rk' }, { k: 'b', l: 'Tugma' }, { k: 'c', l: 'Bosishlar', r: true }, { k: 'u', l: "O'quvchi", r: true }],
      top.map((x, i) => ({ c: { n: i + 1, b: '<span class="c2"><b>' + esc(x.label) + '</b><small>' + ic(scrIc(x.screen)) + esc(x.screen_label || x.screen || DASH) + '</small></span>', c: ibar(x.count, tmax, num(x.count)), u: num(x.users) } })),
      { cards: false, id: 'topTbl', caption: "Eng ko'p bosilgan tugmalar", more: 12, all: !!S.ui.more.topTbl }) + moreBtn('topTbl', top.length, 12)
      : '<div class="card-b">' + empty("Bu davrda tugma bosilmagan", "O'quvchilar ilovadan foydalanganda shu yerda eng ko'p bosilgan tugmalar chiqadi.") + '</div>';
    const smax = Math.max(1, ...scr.map((x) => x.views));
    const scrH = scr.length ? table([{ k: 'e', l: 'Ekran' }, { k: 'v', l: 'Ochilish', r: true }, { k: 'u', l: "O'quvchi", r: true, cls: 'hide-m' }, { k: 't', l: "O'rtacha vaqt", r: true }],
      scr.map((x) => ({ c: { e: '<span class="ic1">' + ic(scrIc(x.name)) + '<b>' + esc(x.label) + '</b></span>', v: ibar(x.views, smax, num(x.views)), u: num(x.users), t: '<span class="nowrap">' + dur(x.avg_ms) + '</span>' } })),
      { cards: false, id: 'scrTbl', caption: 'Ekranlar', more: 12, all: !!S.ui.more.scrTbl }) + moreBtn('scrTbl', scr.length, 12)
      : '<div class="card-b">' + empty("Bu davrda ekran ochilmagan", '') + '</div>';
    const cm = S.ui.cmetric;
    const cdata = daily.map((x) => ({ day: x.day, x: dday(x.day), full: dfull(x.day), v: cm === 'views' ? x.views : x.clicks, extra: cm === 'views' ? 'Bosishlar: ' + num(x.clicks) : 'Ekran ochilishi: ' + num(x.views) }));
    const chart = colChart('chClk', { data: cdata, vlab: cm === 'views' ? 'Ekran ochilishi' : 'Bosishlar', cols: ['Kun', cm === 'views' ? 'Ekran ochilishi' : 'Bosishlar'],
      aria: 'Kunlik faollik, ' + days + ' kun: ' + (cm === 'views' ? 'ekran ochilishlari' : 'tugma bosishlar'), h: 220, bw: days > 20 ? (days > 60 ? 8 : 16) : 44, xw: 52, empty: ["Bu davrda ma'lumot yo'q", ''] });
    const range = daily.length ? dlong(daily[0].day) + ' – ' + dlong(daily[daily.length - 1].day) : '';
    const html = ph({ crumb: 'Boshqaruv', title: 'Tugmalar va ekranlar', text: "O'quvchilar ilovada qaysi tugmalarni ko'p bosadi va qaysi ekranlarda ko'p vaqt o'tkazadi.",
      acts: seg('cdays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) +
      kband([
        { l: 'Tugma bosishlar', v: num(totC), i: 'mouse-pointer-click', f: days + ' kunda · kuniga o\'rtacha ' + num(totC / Math.max(1, days)) },
        { l: 'Ekran ochilishlari', v: num(totV), i: 'layers', f: days + ' kunda · kuniga o\'rtacha ' + num(totV / Math.max(1, days)) },
        { l: "Eng ko'p bosilgan", v: top.length ? esc(top[0].label) : DASH, tx: true, i: 'trophy', f: top.length ? num(top[0].count) + ' marta · ' + esc(top[0].screen_label || '') : '' },
        { l: 'Eng uzoq qolinadigan ekran', v: longS ? esc(longS.label) : DASH, tx: true, i: 'timer', f: longS ? "O'rtacha " + dur(longS.avg_ms) : '' },
      ], 4, 'kpis') +
      card({ cls: 'mb', title: 'Kunlik faollik', sub: range + ' · ' + (cm === 'views' ? 'ekran ochilishlari' : 'tugma bosishlar'),
        acts: seg('cmetric', [['clicks', 'Bosishlar'], ['views', 'Ekran ochilishi']], cm, "Ko'rsatkich") + tblBtn('chClk'),
        take: cm === 'views' ? takeMax(cdata, 'Ekranlar eng ko\'p', 'ochildi', 'marta') : takeMax(cdata, 'Eng ko\'p bosish', 'bo\'ldi', 'ta'), body: chart }) +
      '<div class="row">' + card({ cls: 'c6', title: "Eng ko'p bosilgan tugmalar", sub: 'Jami ' + num(top.length) + ' ta tugma · reyting bosishlar soni bo\'yicha', flush: true, body: topH }) +
      card({ cls: 'c6', title: 'Ekranlar', sub: "Ochilishlar va o'rtacha vaqt · " + num(scr.length) + ' ta ekran', flush: true, body: scrH }) + '</div>';
    put(tk, html);
  }

  /* ---------- 8.7 Qurilmalar ---------- */
  async function vQurilmalar(r, tk) {
    const days = S.ui.ddays;
    const d = await api('/api/x/devices?days=' + days);
    if (!alive(tk)) return;
    const N = d.users || 0;
    const dv = {};
    (d.device || []).forEach((x) => { dv[x.key] = x; });
    const tiles = [['telefon', 'Telefon', 'smartphone'], ['planshet', 'Planshet', 'tablet'], ['kompyuter', 'Kompyuter', 'monitor'], ['brauzer', 'Brauzer (Telegram Web)', 'globe']].map((t) =>
      ({ l: t[1], v: num(dv[t[0]] ? dv[t[0]].users : 0), i: t[2], f: pc(dv[t[0]] ? dv[t[0]].users : 0, N) + "% o'quvchilar" }));
    const L = (arr, icf, cls) => barList((arr || []).map((x) => ({ l: esc(x.label), v: x.users, ic: icf ? icf(x) : '' })), { total: N, et: "Ma'lumot yo'q", cls });
    const topL = (d.labels || [])[0];
    const kv1 = (arr, t) => { const x = (arr || [])[0]; return x ? '<dt>' + t + '</dt><dd>' + esc(x.label) + '<small>' + pc(x.users, N) + '% o\'quvchi</small></dd>' : ''; };
    const html = ph({ crumb: 'Boshqaruv', title: 'Qurilmalar', text: "O'quvchilar ilovani qaysi qurilmada ochadi. Har bir o'quvchi davrdagi oxirgi sessiyasi bo'yicha bir marta sanaladi.",
      acts: seg('ddays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) +
      (N ? kband(tiles, 4, 'kpis') +
        '<div class="row st">' + card({ cls: 'c5', title: 'Ko\'pchilik: ' + esc(topL ? topL.label : DASH), sub: days + ' kun · ' + num(N) + " ta o'quvchi",
          take: topL ? num(topL.users) + ' kishi (' + pc(topL.users, N) + '%). Darslar va slaydlar shu qurilmada yaxshi ko\'rinishini tekshiring.' : '',
          body: '<dl class="kv">' + kv1(d.os, 'Operatsion tizim') + kv1(d.platform, 'Telegram ilovasi') + kv1(d.tg_version, 'Telegram versiyasi') + kv1(d.screen, 'Ekran') + kv1(d.scheme, 'Telegram mavzusi') + '</dl>' }) +
        card({ cls: 'c7', title: 'Qurilma turlari', sub: 'Model guruhlari', body: L(d.labels, (x) => devIc(x.label)) }) + '</div>' +
        '<div class="row st">' + card({ cls: 'c4', title: 'Operatsion tizim', body: L(d.os) }) + card({ cls: 'c4', title: 'Telegram ilovasi', sub: 'Platforma', body: L(d.platform) }) +
        card({ cls: 'c4', title: 'Telegram versiyasi va mavzusi', body: '<div class="blk">' + L(d.tg_version) + '</div><div class="blk"><h3>Rang sxemasi</h3>' + L(d.scheme, (x) => (x.key === 'dark' ? 'moon' : 'sun')) + '</div>' }) + '</div>' +
        card({ cls: 'mb', title: "Ekran o'lchami", sub: "Eng ko'p uchraydigan 10 tasi, CSS piksel (eni × bo'yi)", body: L(d.screen, null, 'two') }) +
        korinishCard(d.korinish, 'chSoatQ', 'mb')
        : card({ body: empty("Bu davrda qurilma ma'lumoti yo'q", "O'quvchilar ilovani ochganda qurilmasi avtomatik aniqlanadi.") }));
    put(tk, html);
  }

  /* ---------- 8.8 Kurs ---------- */
  async function vKurs(r, tk, soft) {
    if (r.arg) return vDropoff(r, tk);
    const d = await api('/api/x/course', soft === 'fresh' ? { fresh: true } : {});
    if (!alive(tk)) return;
    S.jami = d.jami || 36;
    if (S.ui.openDraft == null || soft !== 'keep') S.ui.openDraft = d.open;
    const edit = canEditKurs();
    const ls = d.lessons || [];
    const byN = {};
    ls.forEach((l) => { byN[l.n] = l; });
    const parts = (d.qismlar && d.qismlar.length) ? d.qismlar : [{ n: 1, nomi: '', darslar: ls.map((l) => l.n) }];
    const rows = [];
    parts.forEach((p) => {
      rows.push({ group: p.n + '-qism' + (p.nomi ? ' · ' + T(p.nomi) : '') });
      p.darslar.forEach((n) => {
        const l = byN[n];
        if (!l) return;
        const closed = n > d.open;
        rows.push({
          href: '#kurs/' + n, cls: closed ? 'dim' : '',
          c: {
            n: '<span class="c2"><a class="nm" href="#kurs/' + n + '">' + n + '-dars' + (closed ? ' ' + pill('line', 'lock', 'Yopiq') : '') + '</a><small>' + T(l.nomi) + '</small></span>',
            sl: num(l.slaydlar),
            m: (l.video || l.test) ? '<span class="mats">' + (l.video ? '<span class="tag">' + ic('circle-play') + num(l.videolar) + ' video</span>' : '') +
              (l.test ? '<span class="tag">' + ic('list-checks') + 'test</span>' : '') + '</span>' : '<span class="mu">' + DASH + '</span>',
            st: num(l.started), dn: num(l.done), pr: l.started ? ibar(l.done, l.started, pc(l.done, l.started) + '%', true) : '<span class="mu">' + DASH + '</span>',
            ta: l.test_avg != null ? num(l.test_avg, 1) : '<span class="mu">' + DASH + '</span>',
          },
        });
      });
    });
    const draft = S.ui.openDraft;
    const ctl = edit ? '<div class="openctl"><button type="button" class="ibtn" data-act="open-dec" aria-label="Bittaga kamaytirish"' + (draft <= 1 ? ' disabled' : '') + '>' + ic('minus') + '</button>' +
      '<span class="ov" id="openV" aria-live="polite">' + draft + '<small> / ' + S.jami + '</small></span>' +
      '<button type="button" class="ibtn" data-act="open-inc" aria-label="Bittaga oshirish"' + (draft >= S.jami ? ' disabled' : '') + '>' + ic('plus') + '</button>' +
      '<button type="button" class="btn pri" data-act="open-save"' + (draft === d.open ? ' disabled' : '') + '>' + ic('save') + '<span>Saqlash</span></button>' +
      (draft !== d.open ? '<button type="button" class="btn ghost" data-act="open-reset">Bekor qilish</button>' : '') + '</div>'
      : '<div class="openctl"><span class="ov">' + d.open + '<small> / ' + S.jami + '</small></span>' + pill('', 'eye', "Faqat ko'rish: CEO va admin o'zgartiradi") + '</div>';
    const html = ph({ crumb: "O'quv jarayoni", title: 'Kurs', text: "Fonetika kursining " + S.jami + " darsi: nechta o'quvchi boshlagan va tugatgan. Darsni bosing, slaydlar bo'yicha qayerda to'xtashganini ko'rasiz." }) +
      '<div class="row st"><section class="card c7" data-open="' + d.open + '" aria-labelledby="hOpen"><div class="openc"><div class="kick">Ochiq darslar</div><h2 id="hOpen">O\'quvchilarga ochiq: ' + d.open + ' / ' + S.jami + ' dars</h2>' +
      '<p>Darslar ketma-ket ochiladi: har bir dars oldingisi tugatilgach ochiladi. Bu son eng ko\'pi bilan nechta dars ochiq bo\'lishini belgilaydi.</p>' + ctl +
      '<div class="blk"><h3>Qismlar bo\'yicha tugatilgan darslar</h3>' +
      barList(parts.map((p) => ({ l: p.n + '-qism' + (p.nomi ? ' · ' + T(p.nomi) : ''), v: sum(p.darslar, (n) => (byN[n] ? byN[n].done : 0)) })), { et: "Hali tugatilgan dars yo'q" }) + '</div></div></section>' +
      '<div class="c5">' + kband([
        { l: 'Slaydlar', v: num(sum(ls, (l) => l.slaydlar)), i: 'presentation', f: S.jami + ' dars' },
        { l: 'Videolar', v: num(sum(ls, (l) => l.videolar)), i: 'circle-play', f: num(ls.filter((l) => l.video).length) + ' ta darsda' },
        { l: 'Testlar', v: num(ls.filter((l) => l.test).length), i: 'list-checks', f: 'Darslardagi mashqlar' },
        { l: 'Tugatishlar', v: num(sum(ls, (l) => l.done)), i: 'book-check', f: 'Jami tugatilgan darslar' },
      ], 2, 'kpis') + '</div></div>' +
      card({ title: 'Darslar', sub: parts.length + ' qism, ' + S.jami + ' dars', flush: true, body: '<div style="margin-top:14px">' + table([
        { k: 'n', l: 'Dars', lead: true }, { k: 'sl', l: 'Slaydlar', r: true }, { k: 'm', l: 'Materiallar', cls: 'hide-t' }, { k: 'st', l: 'Boshlagan', r: true }, { k: 'dn', l: 'Tugatgan', r: true },
        { k: 'pr', l: 'Tugatish ulushi' }, { k: 'ta', l: 'Test o\'rtacha', r: true }], rows, { caption: 'Darslar' }) + '</div>' });
    put(tk, html);
  }
  async function vDropoff(r, tk) {
    const n = +r.arg;
    const d = await api('/api/x/dropoff?dars=' + n);
    if (!alive(tk)) return;
    setTitle(n + '-dars · slaydlar');
    const seen = d.seen || [];
    const base = d.started || (seen[0] ? seen[0].users : 0);
    let big = null;
    for (let i = 1; i < seen.length; i++) {
      const drop = seen[i - 1].users - seen[i].users;
      if (drop > 0 && (!big || drop > big.drop)) big = { i: i - 1, drop };
    }
    const data = seen.map((x, i) => ({ x: String(x.idx), full: x.idx + '-slayd', v: x.users, hl: big && big.i === i, extra: pc(x.users, base) + '% boshlaganlardan' + (big && big.i === i ? ' · keyingi slaydga ' + num(big.drop) + ' kishi o\'tmagan' : '') }));
    const chart = colChart('chDrop', { data, vlab: "Ko'rgan", cols: ['Slayd', "Ko'rgan o'quvchilar"], aria: n + '-dars slaydlari bo\'yicha o\'quvchilar', xw: 26, bw: 22, h: 250,
      empty: ['Hali hech kim bu darsni boshlamagan', 'O\'quvchilar slaydlarni ko\'rishi bilan grafik paydo bo\'ladi.'] });
    const jami = S.jami || 36;
    const nav = (n > 1 ? '<a class="btn ghost sm" href="#kurs/' + (n - 1) + '">' + ic('chevron-left') + '<span>' + (n - 1) + '-dars</span></a>' : '') +
      (n < jami ? '<a class="btn ghost sm" href="#kurs/' + (n + 1) + '"><span>' + (n + 1) + '-dars</span>' + ic('chevron-right') + '</a>' : '') +
      (has('testlar') ? '<a class="btn sec sm" href="#test/' + n + '">' + ic('list-checks') + '<span>Test natijalari</span></a>' : '');
    const lastS = seen[seen.length - 1];
    const html = ph({ crumb: [['#kurs', 'Kurs'], [null, n + '-dars']], title: n + '-dars · ' + T(d.nomi), text: "Har bir slaydni nechta o'quvchi ko'rgani. Ustunlar keskin pasaygan joy: o'quvchilar shu slayddan keyin to'xtab qolgan.", acts: nav }) +
      kband([{ l: 'Slaydlar', v: num(d.slaydlar), i: 'presentation' }, { l: 'Boshlagan', v: num(d.started), i: 'play' },
        { l: 'Tugatgan', v: num(d.done), i: 'book-check' }, { l: 'Tugatish ulushi', v: pc(d.done, d.started) + '%', i: 'percent', f: 'Boshlaganlardan' }], 4, 'kpis') +
      (big ? '<div class="note warn">' + ic('triangle-alert') + '<span><b>Eng ko\'p shu yerda to\'xtashgan:</b> ' + (big.i + 1) + '-slayddan keyin ' + num(big.drop) + ' kishi (' + pc(big.drop, seen[big.i].users) + '%) keyingi slaydga o\'tmagan. Grafikda ajratilgan ustun.</span></div>' : '') +
      card({ title: "Slaydlar bo'yicha", sub: num(d.slaydlar) + ' slayd · kishi', acts: tblBtn('chDrop'), take: S.charts.chDrop && lastS ? num(base) + ' kishi boshlagan, oxirgi (' + lastS.idx + '-) slaydni ' + num(lastS.users) + ' kishi ko\'rgan.' : '', body: chart });
    put(tk, html);
  }

  /* ---------- 8.9 Testlar ---------- */
  const NOTE_03 = "Savollar bo'yicha natija 03.10 dan keyingi urinishlardan";
  const hardPill = (h) => pill(h.wrong_pct >= 50 ? 'bad' : h.wrong_pct >= 30 ? 'warn' : 'ok', h.wrong_pct >= 50 ? 'circle-x' : h.wrong_pct >= 30 ? 'circle-alert' : 'circle-check', h.q + '-savol · ' + h.wrong_pct + '% xato');
  async function vTestlar(r, tk) {
    const d = await api('/api/x/tests');
    if (!alive(tk)) return;
    const ls = d.lessons || [];
    const withT = ls.filter((l) => l.has_test), taken = withT.filter((l) => l.takers > 0);
    if (S.ui.tf == null) S.ui.tf = taken.length ? 'taken' : 'all';
    const list = S.ui.tf === 'taken' ? taken : ls;
    const att = sum(withT, (l) => l.attempts), perf = sum(withT, (l) => l.perfect), tk2 = sum(withT, (l) => l.takers);
    const avg = tk2 ? sum(taken, (l) => (l.avg_best || 0) * l.takers) / tk2 : null;
    const rows = list.map((l) => ({
      href: l.has_test ? '#test/' + l.dars : '', cls: l.takers ? '' : 'dim',
      c: {
        d: '<span class="c2">' + (l.has_test ? '<a class="nm" href="#test/' + l.dars + '">' + l.dars + '-dars</a>' : '<span class="nm">' + l.dars + '-dars</span>') + '<small>' + T(l.nomi) + '</small></span>',
        t: l.has_test ? num(l.takers) : '<span class="mu">Test yo\'q</span>', a: l.has_test ? num(l.attempts) : '',
        b: l.avg_best != null ? '<b>' + num(l.avg_best, 1) + '</b>' : '<span class="mu">' + DASH + '</span>', p: l.has_test ? num(l.perfect) : '',
        h: l.hardest ? hardPill(l.hardest) : (l.takers ? '<span class="mu">' + DASH + '</span>' : '<span class="mu">Hali yechilmagan</span>'),
      },
    }));
    const html = ph({ crumb: "O'quv jarayoni", title: 'Testlar', text: "Har bir dars testi bo'yicha natijalar. Qatorni bosing, har bir savol va variantlar tahlili ochiladi." }) +
      kband([{ l: 'Testli darslar', v: num(withT.length), i: 'list-checks', f: num(taken.length) + ' tasi yechilgan' },
        { l: 'Urinishlar', v: num(att), i: 'rotate-ccw', f: 'Barcha testlar bo\'yicha' },
        { l: "O'rtacha eng yaxshi natija", v: avg != null ? num(avg, 1) : DASH, u: avg != null ? 'ball' : '', i: 'award', f: '5 savollik testlarda' },
        { l: "A'lo natijalar", v: num(perf), i: 'trophy', f: 'Hamma savolga to\'g\'ri javob' }], 4, 'kpis') +
      (att ? '<div class="note">' + ic('info') + '<span>' + NOTE_03 + (d.since ? ' (birinchi yozuv: ' + dt(d.since) + ')' : '') + '. Eski urinishlarda faqat umumiy ball bor.</span></div>' : '') +
      card({ title: "Darslar bo'yicha", sub: num(list.length) + ' ta dars', flush: true,
        acts: chips('tf', [['taken', 'Yechilganlar (' + taken.length + ')'], ['all', 'Hammasi (' + ls.length + ')']], S.ui.tf, 'Saralash'),
        body: list.length ? '<div style="margin-top:14px">' + table([{ k: 'd', l: 'Dars', lead: true }, { k: 't', l: 'Yechganlar', r: true }, { k: 'a', l: 'Urinishlar', r: true }, { k: 'b', l: "O'rtacha eng yaxshi", r: true },
          { k: 'p', l: "A'lo", r: true }, { k: 'h', l: 'Eng qiyin savol' }], rows, { caption: 'Testlar' }) + '</div>' : '<div class="card-b">' + empty("Hali test yechilmagan", "O'quvchilar mashq qilganda natijalar shu yerda chiqadi.") + '</div>' });
    put(tk, html);
  }
  async function vTest(r, tk) {
    const n = +r.arg;
    const d = await api('/api/x/test?dars=' + n);
    if (!alive(tk)) return;
    setTitle(n + '-dars testi');
    const qs = d.savollar || [], st = d.students || [];
    const total = qs.length;
    const avg = st.length ? sum(st, (x) => x.best) / st.length : null;
    const perf = st.filter((x) => x.total && x.best === x.total).length;
    const anyAns = qs.some((q) => q.answers > 0);
    const qh = qs.map((q, i) => {
      const ans = q.answers || 0, picks = q.picks || [];
      const wp = q.wrong_pct;
      return '<section class="card qcard" aria-label="' + (q.n || i + 1) + '-savol"><div class="qh"><span class="qn">' + (q.n || i + 1) + '-savol</span>' +
        (ans ? pill(wp >= 50 ? 'bad' : wp >= 30 ? 'warn' : 'ok', wp >= 50 ? 'circle-x' : wp >= 30 ? 'circle-alert' : 'circle-check', wp + '% xato') : pill('', '', "Javoblar yo'q")) +
        '<span class="sp"></span><span class="tag">' + num(ans) + ' javob</span>' + (q.skipped ? '<span class="tag">' + num(q.skipped) + ' javobsiz</span>' : '') + '</div>' +
        '<p class="qq">' + T(q.q) + '</p><ol class="opts">' + (q.opts || []).map((o, j) => {
          const c = picks[j] || 0, p = pc(c, ans), ok = j === q.ok;
          return '<li' + (ok ? ' class="ok"' : '') + '><span class="ob" style="width:' + p + '%" aria-hidden="true"></span><span class="ol">' + 'ABCDEFGH'.charAt(j) + '</span>' +
            '<span class="ot">' + T(o) + (ok ? '<span class="okp">' + pill('ok', 'check', "To'g'ri javob") + '</span>' : '') + '</span>' +
            '<span class="oc">' + num(c) + NB + 'ta<small>' + p + '%</small></span></li>';
        }).join('') + '</ol>' + (q.izoh ? '<div class="izoh"><b>Izoh:</b> ' + T(q.izoh) + '</div>' : '') + '</section>';
    }).join('');
    const jami = S.jami || 36;
    const nav = (n > 1 ? '<a class="btn ghost sm" href="#test/' + (n - 1) + '">' + ic('chevron-left') + '<span>' + (n - 1) + '-dars</span></a>' : '') +
      (n < jami ? '<a class="btn ghost sm" href="#test/' + (n + 1) + '"><span>' + (n + 1) + '-dars</span>' + ic('chevron-right') + '</a>' : '') +
      (has('kurs') ? '<a class="btn sec sm" href="#kurs/' + n + '">' + ic('presentation') + '<span>Slaydlar tahlili</span></a>' : '');
    const stH = st.length ? table([{ k: 'n', l: "O'quvchi", lead: true }, { k: 'b', l: 'Eng yaxshi natija' }, { k: 't', l: 'Urinishlar', r: true }, { k: 'u', l: 'Oxirgi urinish' }],
      st.map((x) => ({ href: has('oquvchilar') ? '#oquvchi/' + x.id : '', c: { n: who(x.name, '', has('oquvchilar') ? '#oquvchi/' + x.id : ''), b: ibar(x.best, x.total || total || 5, num(x.best) + '/' + num(x.total || total), true), t: num(x.tries), u: '<span class="nowrap">' + dt(x.updated_at) + '</span>' } })), { caption: 'Natijalar' })
      : '<div class="card-b">' + empty("Bu testni hali hech kim yechmagan", '') + '</div>';
    const html = ph({ crumb: [['#testlar', 'Testlar'], [null, n + '-dars']], title: n + '-dars testi', text: T(d.test_nomi || '') + (d.nomi ? ' · ' + T(d.nomi) : ''), acts: nav }) +
      kband([{ l: 'Yechganlar', v: num(st.length), i: 'users-round' }, { l: "O'rtacha eng yaxshi", v: avg != null ? num(avg, 1) : DASH, u: avg != null ? '/ ' + total : '', i: 'award' },
        { l: "A'lo natija", v: num(perf), i: 'trophy', f: 'Hamma savolga to\'g\'ri' }, { l: 'Savollar', v: num(total), i: 'circle-help' }], 4, 'kpis') +
      (!anyAns ? '<div class="note">' + ic('info') + '<span>' + NOTE_03 + '.</span></div>' : '') +
      (qs.length ? '<div class="qgrid">' + qh + '</div>' : card({ cls: 'mb', body: empty("Bu darsda test yo'q", '') })) +
      card({ title: "O'quvchilar natijasi", sub: num(st.length) + ' kishi', flush: true, body: '<div style="margin-top:14px">' + stH + '</div>' });
    put(tk, html);
  }

  /* ---------- 8.10 Duellar va do'st takliflari (SPEC 11.5, faqat ko'rish) ---------- */
  const DSTAT = { faol: ['', 'hourglass', 'Davom etmoqda'], tugadi: ['ok', 'circle-check', 'Tugadi'], muddati_otdi: ['line', 'clock', "Muddati o'tgan"] };
  function duelSide(p, win) {
    if (!p) return DASH;
    const sc = p.done ? '<small>' + num(p.correct) + ' to\'g\'ri · ' + dur(p.ms) + '</small>' : '<small>hali o\'ynamagan</small>';
    const nm = esc(p.name || ('ID ' + p.id));
    const l = stuLink(p);
    return '<span class="c2">' + (l ? '<a class="nm" href="' + l + '">' + nm + '</a>' : '<span class="nm">' + nm + '</span>') + sc.replace('<small>', '<small>' + (win ? ic('trophy') + 'G\'olib · ' : '')) + '</span>';
  }
  async function vDuellar(r, tk) {
    const days = S.ui.wdays;
    const d = await api('/api/x/duels?days=' + days);
    if (!alive(tk)) return;
    const recent = d.recent || [], top = d.top || [], daily = d.daily || [], mo = d.modes || {};
    const dm = S.ui.wmetric;
    const cdata = daily.map((x) => ({ day: x.day, x: dday(x.day), full: dfull(x.day), v: dm === 'finished' ? x.finished : x.created, extra: dm === 'finished' ? 'Boshlangan: ' + num(x.created) : 'Tugagan: ' + num(x.finished) }));
    const chart = colChart('chDuel', { data: cdata, vlab: dm === 'finished' ? 'Tugagan duellar' : 'Boshlangan duellar', cols: ['Kun', dm === 'finished' ? 'Tugagan' : 'Boshlangan'],
      aria: 'Kunlik duellar, ' + days + ' kun', h: 296, bw: days > 20 ? (days > 60 ? 8 : 16) : 34, xw: 52, empty: ["Bu davrda duel bo'lmagan", ''] });
    const wmax = Math.max(1, ...top.map((x) => x.played || 0));
    const topH = top.length ? table([{ k: 'n', l: '#', cls: 'rk' }, { k: 'p', l: "O'yinchi" }, { k: 'pl', l: "O'yinlar", r: true }, { k: 'w', l: "G'alaba", r: true }],
      top.map((x, i) => ({ href: stuLink(x), c: { n: i + 1, p: stuLink(x) ? '<a class="nm" href="' + stuLink(x) + '">' + esc(x.name) + '</a>' : '<span class="nm">' + esc(x.name) + '</span>',
        pl: ibar(x.played, wmax, num(x.played)), w: num(x.won) + ' <span class="mu">(' + pc(x.won, x.played) + '%)</span>' } })), { cards: false, caption: "Eng faol o'yinchilar" })
      : '<div class="card-b">' + empty("Hali tugagan duel yo'q", '') + '</div>';
    const stH = barList([{ l: "G'olib aniqlangan", v: Math.max(0, (d.finished || 0) - (d.draws || 0)), ic: 'trophy' }, { l: 'Durrang', v: d.draws || 0, ic: 'scale' },
      { l: 'Davom etmoqda', v: d.active || 0, ic: 'hourglass' }, { l: "Muddati o'tgan", v: d.expired || 0, ic: 'clock' }], { total: d.total, et: "Hali duel yo'q" });
    const modeH = barList([{ l: 'Tasodifiy raqib', v: mo.random || 0, ic: 'shuffle' }, { l: "Do'st bilan", v: mo.friend || 0, ic: 'user-plus' }], { et: "Hali duel yo'q" });
    const rows = recent.map((x) => {
      const st = DSTAT[x.status] || ['', '', esc(x.status)];
      const fin = x.status === 'tugadi';
      const res = fin ? (x.result === 'durrang' ? pill('', 'scale', 'Durrang') : '<b class="num nowrap">' + num(x.a && x.a.correct) + ' : ' + num(x.b && x.b.correct) + '</b>') : '<span class="mu">' + DASH + '</span>';
      return { c: {
        at: '<span class="c2"><b class="nowrap" style="font-weight:600">' + dt(x.at) + '</b><small>' + ic(x.mode === 'friend' ? 'user-plus' : 'shuffle') + (x.mode === 'friend' ? "Do'st bilan" : 'Tasodifiy raqib') + '</small></span>',
        a: duelSide(x.a, fin && x.result === 'a'), res, b: duelSide(x.b, fin && x.result === 'b'),
        st: '<span class="c2">' + pill(st[0], st[1], st[2]) + (x.status === 'faol' && x.expires_at ? '<small>' + dt(x.expires_at) + ' gacha</small>' : '') + '</span>',
        ls: (x.lessons || []).length ? '<span class="mu">' + x.lessons.join(', ') + (x.lessons.length > 1 ? '-darslar' : '-dars') + '</span>' : DASH,
      } };
    });
    const html = ph({ crumb: 'Faollik', title: 'Duellar', text: "O'quvchilar o'rtasidagi bellashuvlar: 5 savol, har biriga 15 soniya. Savollar faqat ikkala o'quvchi tugatgan darslardan olinadi.",
      acts: seg('wdays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) + offNote('duel', 'Duellar') +
      kband([{ l: 'Jami duellar', v: num(d.total), i: 'swords', f: 'Oxirgi ' + days + ' kunda boshlangan' },
        { l: 'Tugagan', v: num(d.finished), i: 'circle-check', f: pc(d.finished, d.total) + '% duellar' },
        { l: "Muddati o'tgan", v: num(d.expired || 0), i: 'clock', f: '24 soatda o\'ynalmagan' },
        { l: 'Davom etmoqda', v: num(d.active || 0), i: 'hourglass', f: 'Ikkinchi o\'yinchi kutilmoqda' },
        { l: 'Durrang', v: num(d.draws || 0), i: 'scale', f: 'Bir xil natija va vaqt' },
        { l: "O'yinchilar", v: num(d.players || 0), i: 'users-round', f: "Duelda qatnashgan o'quvchilar" }], 3, 'kpis') +
      '<div class="row st">' + card({ cls: 'c8', title: 'Kunlik duellar', sub: 'Oxirgi ' + days + ' kun',
        acts: seg('wmetric', [['created', 'Boshlangan'], ['finished', 'Tugagan']], dm, "Ko'rsatkich") + tblBtn('chDuel'),
        take: takeMax(cdata, 'Eng ko\'p duel', dm === 'finished' ? 'tugagan' : 'boshlangan', 'ta', true), body: chart }) +
      '<div class="c4 stack">' + card({ title: 'Duel turi', sub: 'Raqib qanday tanlangan', body: modeH }) + card({ title: 'Duellar holati', body: stH }) + '</div></div>' +
      card({ cls: 'mb', title: "Eng faol o'yinchilar", sub: "Tugagan duellar bo'yicha", flush: true, body: '<div style="margin-top:14px">' + topH + '</div>' }) +
      card({ title: "So'nggi duellar", sub: num(recent.length) + ' ta', flush: true, id: 'duelRecent', body: rows.length ? '<div style="margin-top:14px">' + table([{ k: 'at', l: 'Vaqt' }, { k: 'a', l: 'Chaqirgan', lead: true }, { k: 'res', l: 'Hisob' },
        { k: 'b', l: 'Raqib' }, { k: 'st', l: 'Holat' }, { k: 'ls', l: 'Savollar', cls: 'hide-t' }], rows, { caption: "So'nggi duellar" }) + '</div>' : '<div class="card-b">' + empty("Bu davrda duel bo'lmagan", "O'quvchilar ilovadagi Duellar bo'limidan bellashuv boshlaydi.") + '</div>' });
    put(tk, html);
  }
  async function vTakliflar(r, tk) {
    const d = await api('/api/x/referrals');
    if (!alive(tk)) return;
    const recent = d.recent || [], top = d.top || [];
    const bonus = d.bonus || 50;
    const topH = top.length ? '<ul class="lst">' + top.map((x, i) => '<li><span class="rank">' + (i + 1) + '</span>' +
      '<span class="lt"><b>' + (stuLink(x) ? '<a class="nm" href="' + stuLink(x) + '" style="text-decoration:none">' + esc(x.name) + '</a>' : esc(x.name)) + '</b><small>' + num(x.invited) + ' ta do\'st · ' + num(x.rewarded) + ' tasi 1-darsni tugatgan</small></span>' +
      '<span class="lr"><b>+' + num(x.rewarded * bonus) + '</b>ball</span></li>').join('') + '</ul>' : '<div class="card-b">' + empty("Hali hech kim do'st taklif qilmagan", '') + '</div>';
    const who2 = (p) => { if (!p) return DASH; const l = stuLink(p); return l ? '<a class="nm" href="' + l + '">' + esc(p.name) + '</a>' : '<span class="nm">' + esc(p.name) + '</span>'; };
    const rows = recent.map((x) => ({ c: {
      at: '<span class="nowrap">' + dt(x.at) + '</span>', a: who2(x.inviter), b: who2(x.invitee),
      st: x.rewarded ? '<span class="c2">' + pill('ok', 'circle-check', 'Bonus berildi') + (x.rewarded_at ? '<small>' + dt(x.rewarded_at) + '</small>' : '') + '</span>' : pill('', 'hourglass', '1-darsni kutmoqda'),
    } }));
    const html = ph({ crumb: 'Faollik', title: "Do'st takliflari", text: "O'quvchi shaxsiy havola orqali do'stini taklif qiladi. Do'sti 1-darsni tugatganda ikkalasiga +" + num(bonus) + ' ball beriladi.' }) + offNote('taklif', "Do'st taklif qilish") +
      kband([{ l: 'Taklif bilan kelganlar', v: num(d.total), i: 'user-plus', f: 'Jami' },
        { l: 'Bonus olganlar', v: num(d.rewarded), i: 'circle-check', f: pc(d.rewarded, d.total) + '% 1-darsni tugatgan' },
        { l: 'Kutilmoqda', v: num((d.total || 0) - (d.rewarded || 0)), i: 'hourglass', f: '1-darsni hali tugatmagan' },
        { l: 'Berilgan ball', v: num(d.earned || 0), i: 'gem', f: 'Taklif qilgan va kelganga +' + num(bonus) + ' dan' }], 4, 'kpis') +
      '<div class="row">' + card({ cls: 'c8', title: "So'nggi takliflar", sub: num(recent.length) + ' ta', flush: true, body: rows.length ? '<div style="margin-top:14px">' + table([{ k: 'b', l: 'Kelgan o\'quvchi', lead: true }, { k: 'a', l: 'Taklif qilgan' }, { k: 'at', l: 'Kelgan vaqti' }, { k: 'st', l: 'Holat' }], rows, { caption: "So'nggi takliflar" }) + '</div>'
        : '<div class="card-b">' + empty("Hali taklif yo'q", "O'quvchilar Profil bo'limidagi havolani do'stlariga yuborganda shu yerda chiqadi.") + '</div>' }) +
      card({ cls: 'c4', title: 'Eng faol taklif qiluvchilar', flush: true, body: '<div style="margin-top:6px">' + topH + '</div>' }) + '</div>';
    put(tk, html);
  }

  /* ---------- 8.11 Xodimlar ---------- */
  async function vXodimlar(r, tk, soft) {
    const d = await api('/api/x/staff', soft === 'fresh' ? { fresh: true } : {});
    if (!alive(tk)) return;
    const list = d.staff || [];
    const ceos = list.filter((x) => x.role === 'ceo').length;
    const edit = S.me.can_edit && S.me.can_edit.xodimlar;
    const items = list.length ? '<ul class="lst">' + list.map((x) => {
      const ro = ROLE[x.role] || [x.role, 'user-round', ''];
      const me = x.id === S.me.user.id;
      const canRm = edit && !me && !(x.role === 'ceo' && ceos <= 1);
      return '<li><span class="ava op" aria-hidden="true">' + esc(initials(x.name)) + '</span><span class="lt"><b>' + esc(x.name) + (me ? ' <span class="tag">Siz</span>' : '') + '</b><small>' +
        (x.username ? '@' + esc(x.username) + ' · ' : '') + "Qo'shilgan: " + dday(x.added_at) + '</small></span><span class="lr" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end">' + pill(ro[2], ro[1], esc(ro[0])) +
        (canRm ? '<button type="button" class="btn badl sm" data-act="rm-staff" data-id="' + x.id + '" data-name="' + esc(x.name) + '" data-role="' + esc(ro[0]) + '">' + ic('user-x') + '<span>Chiqarish</span></button>' : '') + '</span></li>';
    }).join('') + '</ul>' : '<div class="card-b">' + empty("Xodimlar yo'q", '') + '</div>';
    const inv = edit ? '<section class="card inv" aria-labelledby="hInv"><div class="kick">Taklif havolasi</div><h2 id="hInv" style="margin-top:4px">Yangi xodim qo\'shish</h2><p>Rolni tanlang va havolani xodimga yuboring. Havola bir marta ishlaydi va 48 soat amal qiladi.</p>' +
      '<div class="irow"><label class="sr" for="invRole">Rol</label><span class="sel"><select id="invRole"><option value="admin">Admin</option><option value="ustoz">Ustoz</option><option value="assistent">Assistent</option></select>' + ic('chevron-down') + '</span>' +
      '<button type="button" class="btn pri" data-act="invite">' + ic('link') + '<span>Havola yaratish</span></button></div><div id="invOut"></div></section>' : '';
    const roles = '<ul class="roles"><li>' + pill('hl', 'crown', 'CEO') + '<span>Hamma bo\'limlar: statistika, kurs, xodimlar, funksiyalar.</span></li>' +
      '<li>' + pill('', 'shield', 'Admin') + '<span>Statistika, o\'quvchilar, voronka, kurs (ochiq darslar), testlar, duellar, jurnal.</span></li>' +
      '<li>' + pill('', 'graduation-cap', 'Ustoz') + '<span>O\'quvchilar, kurs va testlar: faqat ko\'rish.</span></li>' +
      '<li>' + pill('line', 'user-check', 'Assistent') + '<span>Admin panelga kirmaydi, faqat xodimlar boti.</span></li></ul>';
    const html = ph({ crumb: 'Tizim', title: 'Xodimlar', text: "Admin panel va xodimlar botiga kira oladigan jamoa. Yangi xodim faqat taklif havolasi orqali qo'shiladi." }) +
      '<div class="row">' + card({ cls: 'c8', title: 'Jamoa', sub: num(list.length) + ' ta xodim', flush: true, body: '<div style="margin-top:6px">' + items + '</div>' }) +
      '<div class="c4 stack">' + inv + card({ title: 'Rollar', sub: 'Kim nimani ko\'radi', body: roles }) + '</div></div>';
    put(tk, html);
  }

  /* ---------- 8.12 Funksiyalar ---------- */
  const TAYYOR_BOSQICH = 3;  /* 1-, 2- va 3-bosqich (qo'llanma) funksiyalari ishlayapti (SPEC 10-11) */
  const FEAT_IC = { reyting: 'trophy', video: 'circle-play', test: 'list-checks', ball: 'gem', uslub: 'image', eslatma: 'bell', hisobot: 'send', duel: 'swords', taklif: 'user-plus', qollanma: 'book-marked' };
  const BOT_FEAT = ['eslatma', 'hisobot'];
  function featItem(m, on, feats, edit) {
    const soon = m.bosqich > TAYYOR_BOSQICH;
    const note = m.key === 'reyting' && feats.ball === false && on ? '<p class="fnote note warn" style="padding:8px 10px">' + ic('triangle-alert') + '<span>«Ball» o\'chirilgani uchun ilovada Reyting ham ko\'rinmaydi.</span></p>' : '';
    const stt = soon ? '<span class="stt soon">' + ic('clock') + m.bosqich + '-bosqichda</span>' : on ? '<span class="stt on">' + ic('circle-check') + 'Ishlayapti</span>' : '<span class="stt off">' + ic('circle-pause') + "O'chirilgan</span>";
    return '<li data-feat="' + esc(m.key) + '" class="' + (on && !soon ? '' : 'off') + '">' + dia(FEAT_IC[m.key] || 'toggle-right') + '<div class="ft"><b>' + esc(m.nomi) + '</b><p>' + esc(m.tavsif) + '</p></div>' + stt +
      '<button type="button" class="sw" role="switch" aria-checked="' + on + '" data-act="feat" data-k="' + esc(m.key) + '" aria-label="' + esc(m.nomi) + '"' + (edit && !soon ? '' : ' disabled') + '><span class="trk" aria-hidden="true"></span></button>' + note + '</li>';
  }
  async function vFunksiyalar(r, tk, soft) {
    const fresh = soft === 'fresh' ? { fresh: true } : {};
    const [d, au] = await Promise.all([api('/api/x/features', fresh), has('jurnal') ? api('/api/x/audit?limit=200', fresh).catch(() => null) : Promise.resolve(null)]);
    if (!alive(tk)) return;
    S.feat = d;
    const f = d.features || {}, meta = d.meta || [];
    const edit = !!(S.me.can_edit && S.me.can_edit.funksiyalar);
    const later = meta.filter((m) => m.bosqich > TAYYOR_BOSQICH);
    const app = meta.filter((m) => m.bosqich <= TAYYOR_BOSQICH && BOT_FEAT.indexOf(m.key) < 0), bots = meta.filter((m) => m.bosqich <= TAYYOR_BOSQICH && BOT_FEAT.indexOf(m.key) >= 0);
    const off = meta.filter((m) => m.bosqich <= TAYYOR_BOSQICH && f[m.key] === false);
    const group = (title, list, sub) => (list.length ? '<section class="card" aria-label="' + esc(title) + '"><div class="grp-h"><h2>' + esc(title) + '</h2><span class="sub">' + sub + '</span></div><ul class="fl">' +
      list.map((m) => featItem(m, f[m.key] !== false, f, edit)).join('') + '</ul></section>' : '');
    const nomi = {};
    meta.forEach((m) => { nomi[m.key] = m.nomi; });
    const chg = ((au && au.items) || []).filter((x) => x.action === 'feature' && x.detail && x.detail.key).slice(0, 6);
    const chgH = chg.length ? '<ol class="chg">' + chg.map((x, i) => '<li' + (i ? '' : ' class="new"') + '><span class="d" aria-hidden="true"></span><div><b>«' + esc(nomi[x.detail.key] || x.detail.key) + '» ' + (x.detail.on ? 'yoqildi' : "o'chirildi") + '</b>' +
      '<small>' + esc(x.staff_name || ('ID ' + x.staff_id)) + ' · ' + rel(x.at) + '</small></div></li>').join('') + '</ol>' : empty("Hali o'zgarish yo'q", 'Funksiya yoqilsa yoki o\'chirilsa shu yerda qayd etiladi.');
    const html = ph({ crumb: 'Tizim', title: 'Funksiyalar', text: "O'quvchilar ilovasi va botlardagi imkoniyatlarni yoqish va o'chirish. Server darhol amal qiladi, o'quvchi ilovani qayta ochganda ko'rinish ham yangilanadi." }) +
      (off.length ? '<div class="note warn" id="offNote" role="status">' + ic('triangle-alert') + '<span><b>Diqqat:</b> hozir ' + off.length + ' ta funksiya o\'chirilgan — ' + off.map((m) => '«' + esc(m.nomi) + '»').join(', ') + '.</span></div>' : '') +
      '<div class="row"><div class="c8 stack">' + group("O'quvchilar ilovasi", app, app.length + ' ta funksiya') + group('Botlar', bots, bots.length + ' ta funksiya') + group('Keyingi bosqichlar', later, 'tayyor emas') + '</div>' +
      '<div class="c4 stack">' + (au ? card({ title: "So'nggi o'zgarishlar", sub: 'Amallar jurnalidan', acts: '<a class="link" href="#jurnal">Jurnal' + ic('chevron-right') + '</a>', body: chgH }) : '') +
      '<div class="note">' + ic('info') + '<span>' + (edit ? 'O\'chirishdan oldin tasdiq so\'raladi. Yoqish darhol amalga oshadi; o\'quvchi ilovani qayta ochganda o\'zgarishni ko\'radi.' : 'Funksiyalarni faqat CEO yoqadi va o\'chiradi.') + '</span></div></div></div>';
    put(tk, html);
  }
  async function toggleFeat(btn) {
    const k = btn.dataset.k, on = btn.getAttribute('aria-checked') !== 'true';
    const m = ((S.feat && S.feat.meta) || []).find((x) => x.key === k) || { nomi: k, tavsif: '' };
    if (!on) {
      const ok = await confirmDlg({ title: '«' + esc(m.nomi) + '» o\'chirilsinmi?', text: esc(m.tavsif), text2: 'O\'quvchilar uchun bu imkoniyat darhol yopiladi, keyin istalgan vaqtda qayta yoqish mumkin.',
        ok: "O'chirish", okIc: 'toggle-left', icon: FEAT_IC[k] || 'toggle-left' });
      if (!ok) return;
    }
    const li = btn.closest('li');
    const setSw = (v) => {
      btn.setAttribute('aria-checked', String(v));
      if (!li) return;
      li.classList.toggle('off', !v);
      const st = $('.stt', li);
      if (st) { st.className = 'stt ' + (v ? 'on' : 'off'); st.innerHTML = v ? ic('circle-check') + 'Ishlayapti' : ic('circle-pause') + "O'chirilgan"; }
    };
    setSw(on);
    btn.disabled = true;
    btn.classList.add('busy');
    try {
      const res = await api('/api/x/features', { method: 'POST', body: { key: k, on } });
      if (S.feat) S.feat.features = res.features;
      if (S.me) S.me.features = res.features;
      toast('«' + m.nomi + '» ' + (on ? 'yoqildi' : "o'chirildi"));
      haptic('ok');
      if (S.route && S.route.name === 'funksiyalar') render('fresh');
    } catch (e) {
      setSw(!on);
      btn.disabled = false;
      btn.classList.remove('busy');
      if (e.status !== 401) { toast((e && e.message) || "O'zgarish saqlanmadi", true); haptic('err'); }
    }
  }

  /* ---------- 8.13 Amallar jurnali ---------- */
  const ACT_IC = { open: 'lock-open', feature: 'toggle-right', invite: 'user-plus', staff_remove: 'user-x', kirish: 'log-in' };
  async function vJurnal(r, tk) {
    const d = await api('/api/x/audit?limit=200');
    if (!alive(tk)) return;
    const items = d.items || [];
    const kinds = [];
    items.forEach((x) => { if (kinds.indexOf(x.action) < 0) kinds.push(x.action); });
    if (S.ui.jf !== 'all' && kinds.indexOf(S.ui.jf) < 0) S.ui.jf = 'all';
    const list = S.ui.jf === 'all' ? items : items.filter((x) => x.action === S.ui.jf);
    const names = {};
    items.forEach((x) => { names[x.action] = x.action_nomi || x.action; });
    const body = list.length ? '<div style="margin-top:14px">' + table([{ k: 'a', l: 'Amal', lead: true }, { k: 'w', l: 'Xodim' }, { k: 't', l: 'Vaqt' }],
      list.map((x) => ({ c: { a: '<span class="who2">' + dia(ACT_IC[x.action] || 'history', 'sm') + '<span class="wt"><b>' + esc(x.label) + '</b><small>' + esc(x.action_nomi || '') + '</small></span></span>',
        w: esc(x.staff_name || ('ID ' + x.staff_id)), t: '<span class="nowrap">' + dt(x.at) + '</span>' } })), { caption: 'Amallar jurnali' }) + '</div>'
      : '<div class="card-b">' + empty("Hali amal yozilmagan", "Ochiq darslar, funksiyalar, takliflar va kirishlar shu yerda qayd etiladi.") + '</div>';
    const html = ph({ crumb: 'Tizim', title: 'Amallar jurnali', text: "Xodimlar admin panel va bot orqali nimani o'zgartirgani: ochiq darslar, funksiyalar, takliflar, kirishlar." }) +
      card({ title: "So'nggi amallar", sub: num(list.length) + ' ta yozuv', flush: true,
        acts: kinds.length > 1 ? chips('jf', [['all', 'Hammasi']].concat(kinds.map((k) => [k, esc(names[k])])), S.ui.jf, 'Amal turi') : '', body });
    put(tk, html);
  }

  /* ================= 9. Harakatlar ================= */
  async function logout() {
    try { await api('/api/x/logout', { method: 'POST', body: {}, quiet: true }); } catch (e) { /* baribir chiqamiz */ }
    S.cache.clear();
    gate(401, '', null, true);
  }
  async function openSave(btn) {
    const n = S.ui.openDraft;
    btn.disabled = true;
    try {
      const res = await api('/api/x/open', { method: 'POST', body: { n } });
      S.ui.openDraft = res.open;
      toast('Ochiq darslar: ' + res.open + ' / ' + S.jami);
      haptic('ok');
      render('fresh');
    } catch (e) {
      btn.disabled = false;
      if (e.status !== 401) { toast(e.message, true); haptic('err'); }
    }
  }
  async function invite(btn) {
    const role = ($('#invRole') || {}).value || 'admin';
    btn.disabled = true;
    const out = $('#invOut');
    try {
      const res = await api('/api/x/invite', { method: 'POST', body: { role } });
      const rn = (ROLE[role] || [role])[0];
      out.innerHTML = '<div class="linkbox"><label class="sr" for="invLink">' + esc(rn) + ' uchun havola</label><input id="invLink" readonly value="' + esc(res.link) + '">' +
        '<button type="button" class="btn pri" data-act="copy">' + ic('copy') + '<span>Nusxalash</span></button>' +
        (inTg ? '<button type="button" class="btn sec" data-act="share">' + ic('send') + '<span>Telegram orqali yuborish</span></button>' : '') + '</div>' +
        '<p>' + esc(rn) + ' uchun · ' + esc(dt(res.expires)) + ' gacha amal qiladi · bir martalik</p>';
      toast('Havola tayyor');
      haptic('ok');
    } catch (e) {
      if (e.status !== 401) { toast(e.message, true); haptic('err'); }
    } finally {
      btn.disabled = false;
    }
  }
  async function copyLink() {
    const inp = $('#invLink');
    if (!inp) return;
    let ok = false;
    try { if (navigator.clipboard && W.isSecureContext) { await navigator.clipboard.writeText(inp.value); ok = true; } } catch (e) { ok = false; }
    if (!ok) { try { inp.select(); ok = D.execCommand('copy'); } catch (e) { ok = false; } }
    if (ok) toast('Havola nusxalandi'); else { inp.select(); toast('Havolani belgilab, qo\'lda nusxalang', true); }
  }
  async function rmStaff(btn) {
    const ok = await confirmDlg({ title: 'Xodimni chiqarish', text: esc(btn.dataset.name) + ' (' + esc(btn.dataset.role) + ') xodimlar ro\'yxatidan chiqariladi. U admin panel va xodimlar botidan foydalana olmaydi.', ok: 'Chiqarish', okIc: 'user-x', icon: 'user-x' });
    if (!ok) return;
    try {
      await api('/api/x/staff/remove', { method: 'POST', body: { id: +btn.dataset.id } });
      toast('Xodim chiqarildi');
      haptic('ok');
      render('fresh');
    } catch (e) {
      if (e.status !== 401) { toast(e.message, true); haptic('err'); }
    }
  }
  function onClick(e) {
    const a = e.target.closest('[data-act]');
    if (a) {
      const act = a.dataset.act;
      switch (act) {
        case 'menu': menu(!$('#shell').classList.contains('open')); break;
        case 'menu-close': menu(false); break;
        case 'back': goBack(); break;
        case 'refresh':
          S.cache.clear();
          a.classList.add('spin');
          render(true).then(() => { setTimeout(() => a.classList.remove('spin'), 300); });
          break;
        case 'reload': location.reload(); break;
        case 'retry': S.cache.clear(); render(); break;
        case 'logout': logout(); break;
        case 'seg': {
          const k = a.dataset.k, v = a.dataset.v;
          S.ui[k] = /^\d+$/.test(v) ? +v : v;
          haptic();
          render(true);
          break;
        }
        case 'tbl': {
          const id = a.dataset.for, fig = D.getElementById(id);
          if (!fig) break;
          const on = a.getAttribute('aria-pressed') !== 'true';
          S.ui.tbl[id] = on;
          a.setAttribute('aria-pressed', String(on));
          a.innerHTML = ic(on ? 'chart-column' : 'table') + '<span>' + (on ? 'Grafik' : 'Jadval') + '</span>';
          $('.tbl', fig).hidden = !on;
          $('.plot', fig).hidden = on;
          hideTip();
          if (!on) { fig._w = 0; drawChart(fig); }
          break;
        }
        case 'more': {
          const id = a.dataset.for, tb = D.getElementById(id);
          if (!tb) break;
          const open = !tb.classList.contains('all');
          S.ui.more[id] = open;
          tb.classList.toggle('all', open);
          a.setAttribute('aria-expanded', String(open));
          const n = $$('tr.more', tb).length;
          a.innerHTML = ic(open ? 'chevron-up' : 'chevron-down') + '<span>' + (open ? 'Qisqartirish' : 'Yana ' + n + ' tasi') + '</span>';
          break;
        }
        case 'sort': {
          const k = a.dataset.k;
          if (S.ui.ssort === k) S.ui.sdir = -S.ui.sdir; else { S.ui.ssort = k; S.ui.sdir = SORTS[k][2]; }
          const sel = $('#ssort');
          if (sel) sel.value = k;
          refreshStudents();
          break;
        }
        case 'tl-clicks': {
          S.ui.tlClicks = !S.ui.tlClicks;
          a.setAttribute('aria-pressed', String(S.ui.tlClicks));
          const tl = $('.tl');
          if (tl) tl.classList.toggle('hide', !S.ui.tlClicks);
          break;
        }
        case 'feat': if (!a.disabled) toggleFeat(a); break;
        case 'open-dec': case 'open-inc':
          S.ui.openDraft = clamp((S.ui.openDraft || 1) + (act === 'open-inc' ? 1 : -1), 1, S.jami || 36);
          haptic();
          render('keep').then(() => { const b = $('[data-act="' + act + '"]'); if (b && !b.disabled) b.focus(); });
          break;
        case 'open-reset': S.ui.openDraft = null; render(true); break;
        case 'open-save': openSave(a); break;
        case 'invite': invite(a); break;
        case 'copy': copyLink(); break;
        case 'share': {
          const inp = $('#invLink');
          if (inp) { try { tg.openTelegramLink('https://t.me/share/url?url=' + encodeURIComponent(inp.value)); } catch (er) { copyLink(); } }
          break;
        }
        case 'rm-staff': rmStaff(a); break;
        default: break;
      }
      return;
    }
    const tr = e.target.closest('tr.go[data-href]');
    if (tr && tr.dataset.href && !e.target.closest('a,button,input,select,label')) location.hash = tr.dataset.href;
    if (!e.target.closest('.ch')) hideTip();
  }

  /* ================= 10. Ishga tushirish ================= */
  function bindGlobal() {
    D.addEventListener('click', onClick);
    D.addEventListener('submit', (e) => {
      const f = e.target.closest('[data-form="tsearch"]');
      if (!f) return;
      e.preventDefault();
      const inp = $('#tq');
      S.ui.sq = ((inp || {}).value || '').trim();
      if (inp) { inp.blur(); inp.value = ''; }
      if (location.hash === '#oquvchilar') render(true); else location.hash = '#oquvchilar';
    });
    D.addEventListener('input', (e) => {
      if (e.target.id !== 'sq') return;
      clearTimeout(sqTimer);
      const v = e.target.value;
      sqTimer = setTimeout(() => { S.ui.sq = v.trim(); refreshStudents(); }, 300);
    });
    D.addEventListener('change', (e) => {
      if (e.target.id === 'ssort') { S.ui.ssort = e.target.value; S.ui.sdir = SORTS[e.target.value][2]; refreshStudents(); }
    });
    D.addEventListener('keydown', (e) => {
      const sh = $('#shell');
      const open = sh && sh.classList.contains('open');
      if (e.key === 'Escape' && !dlgClose) {
        if (open) { menu(false); const b = $('.menu-b'); if (b) b.focus(); }
        hideTip();
      }
      if (e.key === 'Tab' && open && W.innerWidth <= 760) {
        const f = $$('#side a, #side button').filter((x) => x.offsetParent !== null), act = D.activeElement;
        if (f.length && e.shiftKey && act === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (f.length && !e.shiftKey && act === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
      }
      if (e.key === '/' && !dlgClose && !/INPUT|SELECT|TEXTAREA/.test((D.activeElement || {}).tagName || '') && $('#tq') && $('#tq').offsetParent) { e.preventDefault(); $('#tq').focus(); }
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('tr.go[data-href]')) { e.preventDefault(); location.hash = e.target.dataset.href; }
    });
    D.addEventListener('pointerover', (e) => {
      const h = e.target.closest && e.target.closest('.ch .hit');
      if (h) showTip(h, e);
    });
    D.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse') return;
      const h = e.target.closest && e.target.closest('.ch .hit');
      if (h) showTip(h, e);
    });
    D.addEventListener('pointerout', (e) => {
      if (e.pointerType !== 'mouse') return;
      const h = e.target.closest && e.target.closest('.ch .hit');
      const to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.ch .hit');
      if (h && !to) hideTip();
    });
    W.addEventListener('scroll', () => { if (!$('#tip').hidden) hideTip(); }, { passive: true });
    W.addEventListener('hashchange', onHash);
    let rt = 0;
    W.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { scenes(); const rib = $('#rib'); if (rib) rib._w = 0; drawRibbon(); }, 160); });
    setInterval(themeTick, 60000);
    D.addEventListener('visibilitychange', () => { if (!D.hidden) themeTick(); });
  }
  async function boot() {
    tgInit();
    themeColors();
    scenes();
    bindGlobal();
    try {
      S.me = await api('/api/x/me', { fresh: true });
    } catch (e) {
      if (e.status === 401) return;
      gate(e.status === 403 ? 403 : 0, e.message, e.data);
      return;
    }
    S.gated = false;
    $('#app').innerHTML = shell();
    scenes($('#side'));
    if (!parseHash()) history.replaceState(null, '', '#' + defaultSec());
    S.stack = [location.hash];
    render();
    if (D.fonts && D.fonts.ready) D.fonts.ready.then(() => { Object.keys(S.charts).forEach((id) => { const f = D.getElementById(id); if (f) f._w = 0; }); drawCharts(); });
  }
  boot();
})();

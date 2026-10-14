/* Muhammadamin - admin panel (vanilla JS, build bosqichisiz). SPEC 10.5-10.7.
   1 yordamchilar · 2 format · 3 Telegram va API · 4 komponentlar · 5 grafiklar · 6 karkas va router ·
   7 ekranlar · 8 harakatlar · 9 ishga tushirish. */
/* ikonlar: layout-dashboard users-round filter mouse-pointer-click smartphone book-open list-checks user-cog toggle-right history */
/* ikonlar: house circle-play trophy user-round presentation book-open-text monitor-play award layers sparkles circle-alert loader-circle panels-top-left */
/* ikonlar: tablet monitor globe circle-help arrow-left chevron-right chevron-left flag zoom-in settings circle-dot check rotate-ccw */
/* ikonlar: crown shield graduation-cap user-check gem palette bell send swords user-plus book-marked lock-open user-x log-in log-out */
/* ikonlar: book-check calendar-check calendar-days activity timer x sun moon sun-moon clock circle-check circle-x triangle-alert ban */
/* ikonlar: flame play percent eye lock chart-bar chart-column trending-down toggle-left search footprints scale hourglass */
(function () {
  'use strict';

  /* ================= 1. Yordamchilar ================= */
  const D = document, W = window;
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
  const sum = (arr, f) => arr.reduce((a, x) => a + (+f(x) || 0), 0);
  const uniq = (arr) => arr.filter((x, i) => x && arr.indexOf(x) === i);

  /* ================= 2. Format: raqam, sana, vaqt ================= */
  const NB = ' ';           // ingichka bo'shliq: 12 345
  const DASH = '–';
  function num(v, d) {
    if (v == null || v === '' || !isFinite(+v)) return DASH;
    v = +v;
    const neg = v < 0;
    v = Math.abs(v);
    const s = d ? v.toFixed(d) : String(Math.round(v));
    const k = s.indexOf('.');
    let a = k < 0 ? s : s.slice(0, k);
    const b = k < 0 ? '' : s.slice(k + 1).replace(/0+$/, '');
    a = a.replace(/\B(?=(\d{3})+(?!\d))/g, NB);
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
  function dday(iso) { const d = tz(iso); return d ? d.getUTCDate() + '-' + OY[d.getUTCMonth()] : DASH; }
  function dt(iso) { const d = tz(iso); return d ? d.getUTCDate() + '-' + OY[d.getUTCMonth()] + ', ' + hm(d) : DASH; }
  const dayNo = (d) => Math.floor(d.getTime() / 86400000);
  function rel(iso) {
    const t = ms(iso);
    if (isNaN(t)) return DASH;
    const diff = Date.now() - t;
    if (diff < 60e3 && diff > -120e3) return 'hozirgina';
    if (diff > 0 && diff < 3600e3) return Math.floor(diff / 60e3) + ' daq oldin';
    const d = tz(t), dd = dayNo(tz(Date.now())) - dayNo(d);
    if (dd === 0) return 'bugun, ' + hm(d);
    if (dd === 1) return 'kecha, ' + hm(d);
    return dt(t);
  }
  function dur(v) {
    if (v == null || !isFinite(v)) return DASH;
    const sec = Math.max(0, v / 1000);
    if (sec < 10) return num(Math.round(sec * 10) / 10, 1) + ' s';
    let s = Math.round(sec);
    if (s < 60) return s + ' s';
    const m = Math.floor(s / 60);
    s %= 60;
    if (m < 60) return m + ' daq' + (s ? ' ' + s + ' s' : '');
    const h = Math.floor(m / 60), mm = m % 60;
    return h + ' soat' + (mm ? ' ' + mm + ' daq' : '');
  }
  function todayLong() { const d = tz(Date.now()); return d.getUTCDate() + '-' + OYL[d.getUTCMonth()] + ', ' + KUN[d.getUTCDay()]; }
  function initials(name) {
    const p = String(name || '').trim().split(/\s+/).filter(Boolean);
    if (!p.length) return '?';
    return (p[0].charAt(0) + (p[1] ? p[1].charAt(0) : '')).toUpperCase();
  }

  const USLUB = { game: "O'yinli", glass: 'Shisha' };
  const REJIM = { light: 'Kunduzgi', dark: 'Tungi', auto: 'Avto' };
  const ARAB = { m: "O'rta", l: 'Katta' };
  const SCHEME = { light: 'Kunduzgi', dark: 'Tungi' };
  const PLAT = { android: 'Android', android_x: 'Android X', ios: 'iOS', tdesktop: 'Telegram Desktop', macos: 'Telegram macOS',
    weba: 'Telegram Web A', webk: 'Telegram Web K', web: 'Telegram Web', unigram: 'Unigram' };
  const ROLE = { ceo: ['CEO', 'crown', 'good'], admin: ['Admin', 'shield', 'info'], ustoz: ['Ustoz', 'graduation-cap', 'warn'], assistent: ['Assistent', 'user-check', 'mute'] };
  function devIc(x) {
    x = String(x || '').toLowerCase();
    if (/planshet|ipad|tablet/.test(x)) return 'tablet';
    if (/telefon|iphone/.test(x)) return 'smartphone';
    if (/brauzer|web/.test(x)) return 'globe';
    if (/kompyuter|mac|windows|linux|desktop/.test(x)) return 'monitor';
    return 'circle-help';
  }
  const scrSize = (s) => (s ? String(s).replace('x', ' x ') : DASH);

  /* ================= 3. Telegram va API ================= */
  const tg = W.Telegram && W.Telegram.WebApp;
  const INIT = (tg && tg.initData) || '';
  const inTg = !!INIT;
  const ver = (v) => { try { return !!(inTg && tg.isVersionAtLeast && tg.isVersionAtLeast(v)); } catch (e) { return false; } };
  function tgInit() {
    if (!inTg) return;
    try { tg.ready(); } catch (e) { /* yo'q */ }
    try { tg.expand(); } catch (e) { /* yo'q */ }
    try { if (ver('6.9')) tg.setHeaderColor((function(){try{return getComputedStyle(document.documentElement).getPropertyValue('--nq-bg').trim()||'#E8DABA'}catch(e){return '#E8DABA'}})()); } catch (e) { /* yo'q */ }
    try { if (ver('6.1')) tg.setBackgroundColor((function(){try{return getComputedStyle(document.documentElement).getPropertyValue('--nq-bg').trim()||'#E8DABA'}catch(e){return '#E8DABA'}})()); } catch (e) { /* yo'q */ }
    try { if (ver('7.10')) tg.setBottomBarColor((function(){try{return getComputedStyle(document.documentElement).getPropertyValue('--nq-bg').trim()||'#E8DABA'}catch(e){return '#E8DABA'}})()); } catch (e) { /* yo'q */ }
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
    me: null, cache: new Map(), view: 0, stack: [], timers: [], charts: {}, sessUser: {}, jami: 36, gated: false, route: null,
    ui: { bdays: 14, bmetric: 'active', fdays: 30, lmetric: 'done', cdays: 7, cmetric: 'clicks', cAll: false, ddays: 30,
      sq: '', ssort: 'last', sdir: -1, tf: null, tlClicks: true, jf: 'all', openDraft: null, chart: {} },
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
      const msg = (d && d.xato) || ('Server xatosi (' + r.status + ')');
      if (r.status === 401 && !o.quiet) gate(401, msg, d);
      throw ApiErr(r.status, msg, d);
    }
    if (method === 'GET') S.cache.set(path, { t: Date.now(), d });
    else S.cache.clear();
    return d;
  }
  const has = (sec) => !!(S.me && SEC[sec] && S.me.sections.indexOf(sec) >= 0);
  const canEditKurs = () => !!(S.me && S.me.can_edit && S.me.can_edit.kurs && S.me.access.kurs === 'edit');
  const alive = (tk) => tk === S.view && !S.gated;

  /* ================= 4. Komponentlar ================= */
  function ph(o) {
    return '<header class="ph"><div class="pt">' + (o.crumb ? '<div class="crumb">' + o.crumb + '</div>' : '') +
      '<h1 tabindex="-1">' + o.title + '</h1><div class="tbar"></div>' + (o.text ? '<p>' + o.text + '</p>' : '') + '</div>' +
      (o.acts ? '<div class="ph-acts">' + o.acts + '</div>' : '') + '</header>';
  }
  function card(o) {
    const head = (o.title || o.acts) ? '<div class="card-h"><div class="ch-t">' + (o.title ? '<h2>' + o.title + '</h2>' : '') +
      (o.sub ? '<p class="sub">' + o.sub + '</p>' : '') + '</div>' + (o.acts ? '<div class="ch-a">' + o.acts + '</div>' : '') + '</div>' : '';
    return '<section class="card' + (o.flush ? ' flush' : '') + (o.cls ? ' ' + o.cls : '') + '"' + (o.id ? ' id="' + o.id + '"' : '') + '>' +
      head + (o.flush && o.pad ? '<div class="card-b">' + o.body + '</div>' : o.body) + '</section>';
  }
  function kpi(o) {
    const tag = o.href ? 'a' : 'div';
    return '<' + tag + ' class="card kpi' + (o.live ? ' live' : '') + '"' + (o.href ? ' href="' + o.href + '"' : '') + (o.id ? ' id="' + o.id + '"' : '') + '>' +
      '<div class="k-top"><span class="k-lab">' + (o.live ? '<span class="pulse" aria-hidden="true"></span> ' : '') + o.lab + '</span><span class="k-ic">' + ic(o.ic) + '</span></div>' +
      '<div class="k-val"><span class="kv-n">' + o.val + '</span>' + (o.unit ? '<small>' + o.unit + '</small>' : '') + '</div>' +
      (o.foot ? '<div class="k-foot">' + o.foot + '</div>' : '') + '</' + tag + '>';
  }
  function seg(key, opts, cur, label) {
    return '<div class="seg" role="group" aria-label="' + esc(label) + '">' + opts.map((o) =>
      '<button type="button" data-act="seg" data-k="' + key + '" data-v="' + o[0] + '" aria-pressed="' + (String(o[0]) === String(cur)) + '">' + o[1] + '</button>').join('') + '</div>';
  }
  function chips(key, opts, cur, label) {
    return '<div class="chips" role="group" aria-label="' + esc(label) + '">' + opts.map((o) =>
      '<button type="button" class="chip" data-act="seg" data-k="' + key + '" data-v="' + o[0] + '" aria-pressed="' + (String(o[0]) === String(cur)) + '">' + o[1] + '</button>').join('') + '</div>';
  }
  function empty(icon, title, text) {
    return '<div class="empty"><span class="e-ic">' + ic(icon) + '</span><b>' + title + '</b>' + (text ? '<p>' + text + '</p>' : '') + '</div>';
  }
  function pill(cls, icon, text) { return '<span class="pill ' + (cls || '') + '">' + (icon ? ic(icon) : '') + text + '</span>'; }
  function mbar(v, max, label) {
    const w = max > 0 ? clamp((v * 100) / max, 0, 100) : 0;
    return '<div class="mbar"><span class="tr" aria-hidden="true"><i style="width:' + w.toFixed(1) + '%"></i></span><b>' + label + '</b></div>';
  }
  function who(name, sub, href, av) {
    const inner = '<span class="av" aria-hidden="true">' + esc(av || initials(name)) + '</span><span class="wt"><b>' + esc(name) + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</span>';
    return href ? '<a class="who" href="' + href + '">' + inner + '</a>' : '<div class="who">' + inner + '</div>';
  }
  function table(cols, rows, o) {
    o = o || {};
    let h = '<div class="tbl-wrap"><table class="tbl' + (o.cards === false ? '' : ' cards') + '">' + (o.caption ? '<caption class="sr">' + o.caption + '</caption>' : '') + '<thead><tr>';
    cols.forEach((c) => {
      const sorted = o.sort && o.sort.k === c.k;
      h += '<th scope="col"' + (c.r ? ' class="r"' : '') + (sorted ? ' aria-sort="' + (o.sort.dir > 0 ? 'ascending' : 'descending') + '"' : '') + '>' +
        (c.sort ? '<button type="button" data-act="sort" data-k="' + c.k + '">' + c.l + (sorted ? (o.sort.dir > 0 ? ic('arrow-up') : ic('arrow-down')) : ic('arrow-up-down')) + '</button>' : c.l) + '</th>';
    });
    h += '</tr></thead><tbody>';
    rows.forEach((r) => {
      if (r.group) { h += '<tr class="grp"><td colspan="' + cols.length + '">' + r.group + '</td></tr>'; return; }
      const cls = (r.href ? 'go ' : '') + (r.cls || '');
      h += '<tr' + (cls.trim() ? ' class="' + cls.trim() + '"' : '') + (r.href ? ' data-href="' + esc(r.href) + '"' : '') + '>';
      cols.forEach((c) => {
        const v = r.c[c.k];
        h += '<td data-l="' + esc(c.ml || c.l) + '"' + (c.lead ? ' class="lead"' : c.r ? ' class="r"' : '') + '>' + (v == null ? '' : v) + '</td>';
      });
      h += '</tr>';
    });
    return h + '</tbody></table></div>';
  }
  function barList(items, o) {
    o = o || {};
    if (!items || !items.length || !sum(items, (x) => x.v)) return empty(o.eic || 'chart-bar', o.et || "Hali ma'lumot yo'q", o.ex || '');
    const total = o.total != null ? o.total : sum(items, (x) => x.v);
    const max = Math.max(1, ...items.map((x) => x.v || 0));
    return '<ul class="bl">' + items.map((x, i) =>
      '<li' + (i === 0 && !o.flat ? ' class="top1"' : '') + '><span class="bl-l">' + (x.ic ? ic(x.ic) : '') + '<span>' + x.l + '</span>' + (x.sub ? '<small>' + x.sub + '</small>' : '') + '</span>' +
      '<span class="bl-v">' + (o.fmt ? o.fmt(x.v) : num(x.v)) + (o.nopct ? '' : '<small>' + pc(x.v, total) + '%</small>') + '</span>' +
      '<span class="bl-t" aria-hidden="true"><i style="width:' + (x.v ? Math.max(1, (x.v * 100) / max) : 0).toFixed(1) + '%"></i></span></li>').join('') + '</ul>';
  }
  function skeleton(kind) {
    let h = '<div class="ph" aria-hidden="true"><div class="pt"><span class="sk sk-line" style="width:140px"></span><span class="sk sk-h"></span>' +
      '<div class="tbar" style="margin:12px 0 10px"></div><span class="sk sk-line" style="width:60%"></span></div></div>';
    if (kind !== 'plain') h += '<div class="grid g-4 kpis" aria-hidden="true">' + '<span class="sk sk-card"></span>'.repeat(4) + '</div>';
    return h + '<div class="grid g-2-1" aria-hidden="true"><span class="sk sk-big"></span><span class="sk sk-big"></span></div><p class="sr" role="status">Yuklanmoqda</p>';
  }
  function errBox(e) {
    const msg = e && e.api ? e.message : "Sahifani ko'rsatishda kutilmagan xato yuz berdi.";
    return '<div class="errbox" role="alert"><span class="e-ic">' + ic('circle-alert') + '</span><b>Ma\'lumotni yuklab bo\'lmadi</b><p>' + esc(msg) + '</p>' +
      '<button type="button" class="btn pri" data-act="retry">' + ic('refresh-cw') + '<span>Qayta urinish</span></button></div>';
  }
  function toast(text, err) {
    const box = $('#toasts');
    if (!box) return;
    const el = D.createElement('div');
    el.className = 'toast' + (err ? ' err' : '');
    el.innerHTML = ic(err ? 'circle-alert' : 'circle-check') + '<span>' + esc(text) + '</span>';
    box.appendChild(el);
    setTimeout(() => { el.remove(); }, 3400);
  }
  let dlgClose = null;
  function confirmDlg(o) {
    return new Promise((res) => {
      const root = $('#dlgRoot');
      const prev = D.activeElement;
      root.innerHTML = '<div class="dlg-bg" data-dlg="bg"><div class="dlg" role="alertdialog" aria-modal="true" aria-labelledby="dlgT" aria-describedby="dlgP">' +
        '<div class="d-ic">' + ic(o.icon || 'triangle-alert') + '</div><h2 id="dlgT">' + o.title + '</h2><p id="dlgP">' + o.text + '</p>' +
        '<div class="d-acts"><button type="button" class="btn" data-dlg="no">Bekor qilish</button>' +
        '<button type="button" class="btn ' + (o.cls || 'danger solid') + '" data-dlg="yes">' + o.ok + '</button></div></div></div>';
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

  /* ================= 5. Grafiklar (inline SVG, bitta seriya) ================= */
  function niceTicks(max) {
    if (max <= 4) return { top: Math.max(1, Math.ceil(max)), step: 1 };
    const raw = max / 4, mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
    const step = Math.max(1, (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * mag);
    return { top: Math.ceil(max / step) * step, step };
  }
  function barPath(x, y, w, h, r) {
    r = Math.min(r, w / 2, h);
    return 'M' + x.toFixed(1) + ',' + (y + h).toFixed(1) + 'V' + (y + r).toFixed(1) + 'Q' + x.toFixed(1) + ',' + y.toFixed(1) + ' ' + (x + r).toFixed(1) + ',' + y.toFixed(1) +
      'H' + (x + w - r).toFixed(1) + 'Q' + (x + w).toFixed(1) + ',' + y.toFixed(1) + ' ' + (x + w).toFixed(1) + ',' + (y + r).toFixed(1) + 'V' + (y + h).toFixed(1) + 'Z';
  }
  /* o: {data:[{x, full, v, hl, extra}], yl, xl, vlab, h, aria, cols:[xHead, vHead], empty:[title, text]} */
  function colChart(id, o) {
    S.charts[id] = o;
    const tot = sum(o.data, (d) => d.v);
    if (!o.data.length || !tot) {
      S.charts[id] = null;
      return empty(o.eic || 'chart-column', (o.empty && o.empty[0]) || "Hali ma'lumot yo'q", (o.empty && o.empty[1]) || '');
    }
    const rows = o.data.map((d) => '<tr><td>' + esc(d.full || d.x) + '</td><td class="r num">' + num(d.v) + '</td></tr>').join('');
    return '<figure class="chart" id="' + id + '" style="margin:0"><div class="chart-cap"><span>' + esc(o.yl) + '</span></div>' +
      '<div class="ch-plot" style="height:' + (o.h || 220) + 'px"></div><div class="chart-x">' + esc(o.xl) + '</div>' +
      '<div class="chart-tbl" hidden><table class="tbl"><thead><tr><th scope="col">' + esc(o.cols[0]) + '</th><th scope="col" class="r">' + esc(o.cols[1]) + '</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<figcaption class="sr">' + esc(o.aria) + '</figcaption></figure>';
  }
  const tblBtn = (id) => '<button type="button" class="btn sm" data-act="tbl" data-for="' + id + '" aria-pressed="false">' + ic('table') + '<span>Jadval</span></button>';
  function drawChart(fig) {
    const o = S.charts[fig.id];
    if (!o) return;
    const plot = $('.ch-plot', fig);
    const Wd = Math.floor(plot.clientWidth || fig.clientWidth || 600);
    if (Wd < 40) return;
    fig._w = Wd;
    const Ht = o.h || 220, pL = 42, pR = 6, pT = 22, pB = 26;
    const data = o.data, n = data.length;
    const max = Math.max(1, ...data.map((d) => d.v || 0));
    const tk = niceTicks(max);
    const pw = Wd - pL - pR, phh = Ht - pT - pB, band = pw / n, bw = Math.min(24, Math.max(3, band * 0.64));
    let s = '<svg width="' + Wd + '" height="' + Ht + '" viewBox="0 0 ' + Wd + ' ' + Ht + '" role="img" aria-label="' + esc(o.aria) + '">';
    for (let t = 0; t <= tk.top + 1e-9; t += tk.step) {
      const y = pT + phh - (t / tk.top) * phh;
      if (t > 0) s += '<line class="gl" x1="' + pL + '" x2="' + (Wd - pR) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>';
      s += '<text class="ax" x="' + (pL - 8) + '" y="' + (y + 4).toFixed(1) + '" text-anchor="end">' + num(t) + '</text>';
    }
    s += '<line class="bl0" x1="' + pL + '" x2="' + (Wd - pR) + '" y1="' + (pT + phh) + '" y2="' + (pT + phh) + '"/>';
    const lw = o.xw || 40;
    const every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(pw / lw))));
    let mi = 0;
    data.forEach((d, i) => { if ((d.v || 0) > (data[mi].v || 0)) mi = i; });
    data.forEach((d, i) => {
      const cx = pL + band * i + band / 2;
      const hh = d.v > 0 ? Math.max(2, (d.v / tk.top) * phh) : 0;
      if (hh > 0) s += '<path class="bar' + (d.hl ? ' hl' : '') + '" data-i="' + i + '" d="' + barPath(cx - bw / 2, pT + phh - hh, bw, hh, 4) + '"/>';
      if ((n - 1 - i) % every === 0) s += '<text class="ax" x="' + cx.toFixed(1) + '" y="' + (Ht - 8) + '" text-anchor="middle">' + esc(d.x) + '</text>';
      if (i === mi && d.v > 0) s += '<text class="vl" x="' + cx.toFixed(1) + '" y="' + (pT + phh - hh - 6).toFixed(1) + '" text-anchor="middle">' + num(d.v) + '</text>';
    });
    data.forEach((d, i) => {
      s += '<rect class="hit" data-i="' + i + '" x="' + (pL + band * i).toFixed(1) + '" y="' + pT + '" width="' + Math.max(1, band).toFixed(1) + '" height="' + phh + '"/>';
    });
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
  }
  if (W.ResizeObserver) {
    RO = new ResizeObserver((ents) => {
      ents.forEach((en) => {
        const fig = en.target;
        if (!D.body.contains(fig)) { RO.unobserve(fig); return; }
        const w = Math.floor(($('.ch-plot', fig) || fig).clientWidth);
        if (w && w !== fig._w) drawChart(fig);
      });
    });
  }
  const tip = () => $('#tip');
  let tipTimer = 0;
  function showTip(hit, ev) {
    const fig = hit.closest('.chart');
    const o = fig && S.charts[fig.id];
    if (!o) return;
    const i = +hit.getAttribute('data-i'), d = o.data[i];
    if (!d) return;
    $$('.bar.on', fig).forEach((b) => b.classList.remove('on'));
    const bar = $('.bar[data-i="' + i + '"]', fig);
    if (bar) bar.classList.add('on');
    const t = tip();
    t.innerHTML = '<b>' + esc(d.full || d.x) + '</b><span class="tv">' + esc(o.vlab) + ': ' + num(d.v) + '</span>' + (d.extra ? '<br>' + d.extra : '');
    t.hidden = false;
    const r = hit.getBoundingClientRect();
    const br = bar ? bar.getBoundingClientRect() : r;
    const x = ev && ev.pointerType === 'mouse' ? ev.clientX : r.left + r.width / 2;
    const y = br.top;
    const tw = t.offsetWidth, th = t.offsetHeight;
    t.style.left = clamp(x - tw / 2, 8, W.innerWidth - tw - 8) + 'px';
    t.style.top = (y - th - 10 < 8 ? Math.min(W.innerHeight - th - 8, r.bottom + 10) : y - th - 10) + 'px';
    clearTimeout(tipTimer);
    if (ev && ev.pointerType !== 'mouse') tipTimer = setTimeout(hideTip, 3500);
  }
  function hideTip() {
    const t = tip();
    if (t) t.hidden = true;
    $$('.chart .bar.on').forEach((b) => b.classList.remove('on'));
  }

  /* ================= 6. Karkas va router ================= */
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
  function shell() {
    const me = S.me, name = ((me.user.first_name || '') + ' ' + (me.user.last_name || '')).trim() || ('ID ' + me.user.id);
    let nav = '';
    GROUPS.forEach((g, gi) => {
      const items = Object.keys(SEC).filter((k) => SEC[k].g === gi && me.sections.indexOf(k) >= 0);
      if (!items.length) return;
      nav += '<div class="ng"><div class="ng-lab">' + esc(g) + '</div>' + items.map((k) =>
        '<a class="ni" href="#' + k + '" data-sec="' + k + '" title="' + esc(SEC[k].nomi) + '"><span class="nic">' + ic(SEC[k].ic) + '</span><span class="nl">' + esc(SEC[k].nomi) + '</span>' +
        (me.access[k] === 'read' ? '<span class="ro">ko\'rish</span>' : '') + '</a>').join('') + '</div>';
    });
    const brand = esc(me.brend || 'Muhammadamin');
    const logo = '<span class="logo" dir="rtl" lang="ar" aria-hidden="true">ن</span>';
    return '<div class="shell" id="shell">' +
      '<aside class="side" id="side" aria-label="Asosiy menyu">' +
      '<a class="brand" href="#' + defaultSec() + '">' + logo + '<span class="bt"><b>' + brand + '</b><small>Admin panel</small></span></a>' +
      '<button type="button" class="ib side-x" data-act="menu-close" aria-label="Menyuni yopish">' + ic('x') + '</button>' +
      '<nav class="nav" aria-label="Bo\'limlar">' + nav + '</nav>' +
      '<div class="side-foot"><div class="me" title="' + esc(name) + '"><span class="av" aria-hidden="true">' + esc(initials(name)) + '</span><span class="mt"><b>' + esc(name) + '</b><small>' + esc(me.rol_nomi || me.role) + (inTg ? ' · Telegram' : ' · brauzer') + '</small></span></div>' +
      (me.browser ? '<button type="button" class="btn" data-act="logout" title="Chiqish">' + ic('log-out') + '<span>Chiqish</span></button>' : '') + '</div>' +
      '</aside><div class="scrim" data-act="menu-close"></div>' +
      '<div class="main"><header class="top">' +
      '<button type="button" class="ib menu-btn" data-act="menu" aria-label="Menyu" aria-controls="side" aria-expanded="false">' + ic('menu') + '</button>' +
      '<button type="button" class="ib back-btn" data-act="back" aria-label="Orqaga">' + ic('arrow-left') + '</button>' +
      '<a class="tb-brand" href="#' + defaultSec() + '">' + logo + '<span class="bt"><b>' + brand + '</b><small>Admin panel</small></span></a>' +
      '<div class="tb-title" id="tbTitle"></div>' +
      (has('oquvchilar') ? '<form class="tsearch" role="search" data-form="tsearch">' + ic('search') + '<label class="sr" for="tq">O\'quvchi qidirish</label>' +
        '<input id="tq" type="search" placeholder="O\'quvchi qidirish: ism yoki @username" autocomplete="off" enterkeyhint="search"></form>' : '') +
      '<div class="top-acts"><button type="button" class="ib" data-act="refresh" aria-label="Yangilash" title="Yangilash">' + ic('refresh-cw') + '</button>' +
      '<span class="who-chip" title="' + esc(name) + '"><span class="av" aria-hidden="true">' + esc(initials(name)) + '</span><span class="wn">' + esc(me.rol_nomi || me.role) + '</span></span></div>' +
      '</header><main class="page" id="page" tabindex="-1"></main></div></div>';
  }
  function menu(open) {
    const sh = $('#shell');
    if (!sh) return;
    sh.classList.toggle('open', open);
    const b = $('.menu-btn', sh);
    if (b) b.setAttribute('aria-expanded', String(open));
    if (open) { const a = $('.ni[aria-current="page"]', sh) || $('.ni', sh); if (a) a.focus(); }
  }
  function setChrome(r, allowed) {
    $$('.ni').forEach((a) => { if (allowed && a.dataset.sec === r.def.sec) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    const sh = $('#shell');
    const nested = allowed && r.nested;
    sh.classList.toggle('nested', nested);
    tgBack(nested);
  }
  function setTitle(t) {
    const tt = $('#tbTitle');
    if (tt) tt.textContent = t;
    D.title = t + ' · Muhammadamin · Admin panel';
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
      page.innerHTML = blocked();
      D.body.setAttribute('data-ready', r.hash);
      W.scrollTo(0, 0);
      return;
    }
    setTitle(SEC[r.def.sec].nomi);
    let skT = 0;
    if (soft) skT = setTimeout(() => { if (tk === S.view) page.innerHTML = skeleton(); }, 180);
    else { S.charts = {}; page.innerHTML = skeleton(r.nested ? 'plain' : ''); W.scrollTo(0, 0); }
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
    D.body.setAttribute('data-ready', S.route ? S.route.hash : '');  /* sinov uchun: ko'rinish tayyor */
    return true;
  }
  function blocked() {
    return '<div class="errbox" role="alert"><span class="e-ic">' + ic('lock') + '</span><b>Bu bo\'lim sizga ochiq emas</b>' +
      '<p>Rolingiz (' + esc(S.me.rol_nomi || S.me.role) + ') bu bo\'limni ko\'ra olmaydi. Kerak bo\'lsa, CEO dan ruxsat so\'rang.</p>' +
      '<a class="btn pri" href="#' + defaultSec() + '">' + ic('arrow-left') + '<span>Asosiy bo\'limga o\'tish</span></a></div>';
  }
  function gate(code, msg, data, after) {
    S.gated = true;
    clearTimers();
    tgBack(false);
    const bot = data && (data.bot || data.xodim_bot);
    const brand = '<div class="brand"><span class="logo" dir="rtl" lang="ar" aria-hidden="true">ن</span><span class="bt"><b>' + esc((S.me && S.me.brend) || 'Muhammadamin') + '</b><small>Admin panel</small></span></div>';
    const botA = bot ? '<a href="https://t.me/' + esc(bot) + '" target="_blank" rel="noopener">@' + esc(bot) + '</a>' : '';
    let h;
    if (code === 401 && !inTg) {
      h = '<span class="gate-ic">' + ic('log-in') + '</span>' +
        (after ? '<h1>Siz admin paneldan chiqdingiz</h1>' : '<h1>Kirish uchun xodimlar botiga <span class="code">/kirish</span> deb yozing</h1>') + '<div class="tbar"></div>' +
        (after ? '<p>Kirish uchun xodimlar botiga <span class="code">/kirish</span> deb yozing.</p>' :
          '<p>Admin panel brauzerda bir martalik havola orqali ochiladi.' + (msg && /muddati/.test(msg) ? ' Oldingi kirish muddati tugagan.' : '') + '</p>') +
        '<ol class="steps"><li><b>1</b><span>Telegramda xodimlar botini oching' + (botA ? ': ' + botA : '') + '.</span></li>' +
        '<li><b>2</b><span><span class="code">/kirish</span> deb yozing.</span></li>' +
        '<li><b>3</b><span>"Admin panelni ochish" tugmasini bosing. Havola 10 daqiqa amal qiladi va bir marta ishlaydi.</span></li></ol>' +
        '<div class="acts"><button type="button" class="btn pri" data-act="reload">' + ic('refresh-cw') + '<span>Qayta tekshirish</span></button></div>';
    } else if (code === 401) {
      h = '<span class="gate-ic">' + ic('log-in') + '</span><h1>Kirish tasdiqlanmadi</h1><div class="tbar"></div><p>' + esc(msg || 'Boshqaruvni xodimlar boti orqali qayta oching.') + '</p>' +
        '<div class="acts"><button type="button" class="btn pri" data-act="reload">' + ic('refresh-cw') + '<span>Qayta urinish</span></button></div>';
    } else if (code === 403) {
      const generic = "Bu bo'lim sizga ochiq emas";
      h = '<span class="gate-ic crit">' + ic('lock') + '</span><h1>' + generic + '</h1><div class="tbar"></div>' +
        '<p>' + (msg && msg !== generic ? esc(msg) + '. ' : '') + 'Admin panel CEO, admin va ustozlar uchun. Sizning ishlaringiz xodimlar botida.</p>' +
        (!inTg ? '<div class="acts"><button type="button" class="btn" data-act="logout">' + ic('log-out') + '<span>Boshqa akkaunt bilan kirish</span></button></div>' : '');
    } else {
      h = '<span class="gate-ic crit">' + ic('circle-alert') + '</span><h1>Server bilan aloqa yo\'q</h1><div class="tbar"></div><p>' + esc(msg || "Internetni tekshirib, qayta urinib ko'ring.") + '</p>' +
        '<div class="acts"><button type="button" class="btn pri" data-act="reload">' + ic('refresh-cw') + '<span>Qayta urinish</span></button></div>';
    }
    $('#app').innerHTML = '<div class="gate"><div class="gate-box">' + brand + '<div class="card" role="alert">' + h + '</div></div></div>';
    D.title = 'Kirish · Muhammadamin · Admin panel';
  }

  /* ================= 7. Ekranlar ================= */
  /* ---------- 7.1 Bosh sahifa ---------- */
  const KIND = {
    lesson_done: ['book-check', (r) => esc(r) + 'ni tugatdi'],
    test_done: ['list-checks', (r) => esc(r) + ' testini yechdi'],
    video_done: ['circle-play', (r) => esc(r) + ' videosini ko\'rdi'],
  };
  function liveHtml(d) {
    const live = d.live || [];
    const body = live.length ? '<ul class="list live-list">' + live.map((x) => {
      const inner = '<span class="li-ic">' + ic(devIc(x.device_label)) + '</span><span class="li-t"><b>' + esc(x.name) + '</b><small>' + esc(x.screen_label || x.screen || DASH) + ' · ' + esc(x.device_label || DASH) + '</small></span>' +
        (x.since ? '<span class="li-r">' + hm(tz(x.since)) + ' dan<br>' + dur(Date.now() - ms(x.since)) + '</span>' : '');
      return '<li>' + (x.session_id && has('oquvchilar') ? '<a class="li-a" href="#sessiya/' + esc(x.session_id) + '">' + inner + '</a>' : inner) + '</li>';
    }).join('') + '</ul>' : empty('moon', 'Hozir hech kim ilovada emas', "O'quvchi ilovani ochishi bilan shu yerda paydo bo'ladi.");
    return '<div class="kick">Jonli · har 30 soniyada yangilanadi</div><h2 style="display:flex;align-items:center;gap:10px;margin-top:6px"><span class="pulse" aria-hidden="true"></span>Hozir ilovada: ' + num(d.active_now) + '</h2>' +
      '<p class="sub" style="margin:0 0 6px">Oxirgi 5 daqiqada faol bo\'lganlar. Ismni bosing, safarini ko\'rasiz.</p>' + body +
      '<p class="sub" style="margin:10px 0 0;font-size:12px">Yangilangan: ' + hms(Date.now()) + '</p>';
  }
  async function vBosh(r, tk) {
    const days = S.ui.bdays;
    const d = await api('/api/x/overview?days=' + days);
    if (!alive(tk)) return;
    const k = [
      { lab: "O'quvchilar", val: num(d.students), ic: 'users-round', foot: "Jami ro'yxatdan o'tganlar", href: has('oquvchilar') ? '#oquvchilar' : '' },
      { lab: 'Hozir ilovada', val: num(d.active_now), ic: 'activity', foot: 'Oxirgi 5 daqiqada', live: true, id: 'kNow' },
      { lab: 'Bugun faol', val: num(d.active_today), ic: 'calendar-check', foot: pc(d.active_today, d.students) + '% o\'quvchilar' },
      { lab: '7 kunda faol', val: num(d.active_7d), ic: 'calendar-days', foot: pc(d.active_7d, d.students) + '% o\'quvchilar' },
      { lab: 'Yangi (7 kun)', val: num(d.new_7d), ic: 'user-plus', foot: "So'nggi 7 kunda qo'shilgan" },
      { lab: 'Bugungi sessiyalar', val: num(d.sessions_today), ic: 'smartphone', foot: 'Ilova bugun necha marta ochilgan' },
      { lab: "O'rtacha sessiya", val: num(d.avg_session_min, 1), unit: 'daq', ic: 'timer', foot: 'Bugungi sessiyalar bo\'yicha' },
      { lab: 'Tugatilgan darslar', val: num(d.lessons_done), ic: 'book-check', foot: num(d.tests_done) + ' test · ' + num(d.videos_done) + ' video', href: has('kurs') ? '#kurs' : '' },
    ];
    const met = S.ui.bmetric;
    const daily = (d.daily || []).map((x) => ({ x: dday(x.day), full: dday(x.day) + ', ' + KUN[tz(x.day).getUTCDay()], v: met === 'xp' ? x.xp : x.active,
      extra: met === 'xp' ? 'Faol: ' + num(x.active) + ' kishi' : 'Ball: ' + num(x.xp) }));
    const chart = colChart('chBosh', {
      data: daily, yl: met === 'xp' ? "To'plangan ball" : "Faol o'quvchilar, kishi", xl: 'Kun', vlab: met === 'xp' ? 'Ball' : "Faol o'quvchilar",
      cols: ['Kun', met === 'xp' ? 'Ball' : "Faol o'quvchilar"], aria: 'Kunlik faollik, oxirgi ' + days + ' kun', xw: 46,
      empty: ['Hali faollik yo\'q', 'O\'quvchilar darslarni ochishi bilan grafik to\'ladi.'],
    });
    const recent = (d.recent || []).slice(0, 12);
    const recentH = recent.length ? '<ul class="list">' + recent.map((x) => {
      const kd = KIND[x.kind] || ['activity', (q) => esc(q)];
      return '<li><span class="li-ic">' + ic(kd[0]) + '</span><span class="li-t"><b>' + esc(x.name) + '</b><small>' + kd[1](x.ref) + (x.natija ? ' · ' + esc(x.natija) : '') + '</small></span><span class="li-r">' + rel(x.at) + '</span></li>';
    }).join('') + '</ul>' : empty('history', "Hali faollik yo'q", "O'quvchilar dars tugatganda, test yechganda yoki video ko'rganda shu yerda chiqadi.");
    const devs = (d.devices || []).map((x) => ({ l: esc(x.label), v: x.users, ic: devIc(x.label) }));
    const st = d.styles || {}, mo = d.modes || {};
    const styleH = barList([{ l: "O'yinli", v: st.game || 0, ic: 'gem' }, { l: 'Shisha', v: st.glass || 0, ic: 'layers' }, { l: 'Tanlanmagan', v: st.none || 0, ic: 'circle-help' }], { flat: true, et: "Hali tanlov yo'q" });
    const stH = barList([{ l: "G'olib aniqlangan", v: Math.max(0, (d.finished || 0) - (d.draws || 0)), ic: 'trophy' }, { l: 'Durrang', v: d.draws || 0, ic: 'scale' },
      { l: 'Faol', v: d.active || 0, ic: 'hourglass' }, { l: "Muddati o'tgan", v: d.expired || 0, ic: 'clock' }], { flat: true, et: "Hali duel yo'q" });
    const modeH = barList([{ l: 'Kunduzgi', v: mo.light || 0, ic: 'sun' }, { l: 'Tungi', v: mo.dark || 0, ic: 'moon' }, { l: 'Avto', v: mo.auto || 0, ic: 'sun-moon' }], { flat: true, et: "Hali tanlov yo'q" });
    const html = ph({ crumb: 'Boshqaruv · ' + esc(todayLong()), title: 'Bosh sahifa', text: "O'quvchilar ilovasidagi faollik: kim hozir ilovada, bugun va so'nggi kunlarda nima bo'ldi." }) +
      '<div class="grid g-4 kpis">' + k.map(kpi).join('') + '</div>' +
      '<div class="grid g-2-1">' +
      card({ title: 'Kunlik faollik', sub: 'Oxirgi ' + days + ' kun', acts: seg('bmetric', [['active', "Faol o'quvchilar"], ['xp', 'Ball']], met, "Ko'rsatkich") + seg('bdays', [[14, '14 kun'], [30, '30 kun']], days, 'Davr') + (S.charts.chBosh ? tblBtn('chBosh') : ''), body: chart }) +
      '<section class="deep" id="liveBox" aria-live="polite">' + liveHtml(d) + '</section></div>' +
      '<div class="grid g-2-1">' +
      card({ title: "So'nggi faollik", sub: 'Darslar, testlar va videolar', body: recentH }) +
      '<div class="stack">' + card({ title: 'Qurilmalar', sub: "Oxirgi 30 kun, har o'quvchi bir marta", acts: has('qurilmalar') ? '<a class="link" href="#qurilmalar">Batafsil' + ic('chevron-right') + '</a>' : '', body: barList(devs, { et: "Hali qurilma ma'lumoti yo'q", ex: "O'quvchilar ilovani ochganda paydo bo'ladi." }) }) +
      card({ title: 'Uslub va rejim', sub: "O'quvchilar tanlovi", body: '<div class="kick" style="margin-bottom:8px">Uslub</div>' + styleH + '<div class="kick" style="margin:16px 0 8px">Rejim</div>' + modeH }) + '</div></div>';
    if (!put(tk, html)) return;
    S.timers.push(setInterval(async () => {
      try {
        const n = await api('/api/x/overview?days=' + days, { fresh: true });
        if (!alive(tk)) return;
        const lb = $('#liveBox'), kv = $('#kNow .kv-n');
        if (lb) lb.innerHTML = liveHtml(n);
        if (kv) kv.textContent = num(n.active_now);
      } catch (e) { /* jim: keyingi safar */ }
    }, 30000));
  }

  /* ---------- 7.2 O'quvchilar ---------- */
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
    if (!list.length) return empty('search', S.ui.sq ? 'Hech kim topilmadi' : "Hali o'quvchi yo'q", S.ui.sq ? "Boshqa ism yoki @username bilan qidirib ko'ring." : "O'quvchilar talabalar botiga /start yozganda shu yerda paydo bo'ladi.");
    const jami = S.jami || 36;
    const cols = [
      { k: 'name', l: "O'quvchi", lead: true, sort: true }, { k: 'device', l: 'Qurilma', sort: true }, { k: 'lessons', l: 'Darslar', sort: true },
      { k: 'xp', l: 'Ball', r: true, sort: true }, { k: 'streak', l: 'Seriya', r: true }, { k: 'sessions', l: 'Sessiyalar', r: true, sort: true },
      { k: 'joined', l: "Qo'shilgan", sort: true }, { k: 'last', l: 'Oxirgi faollik', sort: true },
    ];
    const rows = list.map((s) => ({
      href: '#oquvchi/' + s.id,
      c: {
        name: who(s.name || ('ID ' + s.id), s.username ? '@' + esc(s.username) : 'ID ' + s.id, '#oquvchi/' + s.id),
        device: s.device_label ? '<span class="tag">' + ic(devIc(s.device_label)) + esc(s.device_label) + '</span>' : '<span class="muted">Ma\'lumot yo\'q</span>',
        lessons: mbar(s.lessons_done || 0, jami, num(s.lessons_done || 0) + '/' + jami),
        xp: '<b class="num">' + num(s.xp) + '</b>', streak: num(s.streak) + ' kun', sessions: num(s.sessions || 0),
        joined: dday(s.joined_at), last: rel(s.last_seen),
      },
    }));
    return table(cols, rows, { sort: { k, dir }, caption: "O'quvchilar ro'yxati" });
  }
  let sqTimer = 0;
  async function refreshStudents(fetchNew) {
    const box = $('#stuBody'), cnt = $('#stuCnt');
    if (!box) return;
    const tk = S.view;
    try {
      const q = S.ui.sq.trim();
      const d = await api('/api/x/students' + (q ? '?q=' + encodeURIComponent(q) : ''), fetchNew ? {} : {});
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
    const sortSel = '<label class="sr" for="ssort">Saralash</label><select class="sel" id="ssort" data-change="ssort">' + Object.keys(SORTS).map((k) =>
      '<option value="' + k + '"' + (k === S.ui.ssort ? ' selected' : '') + '>Saralash: ' + esc(SORTS[k][0]) + '</option>').join('') + '</select>';
    const html = ph({ crumb: 'Boshqaruv', title: "O'quvchilar", text: "Har bir o'quvchining qurilmasi, darslari va ilovadagi safari. Qatorni bosing, to'liq karta ochiladi." }) +
      '<section class="card flush"><div class="card-h"><div class="ch-t"><h2>O\'quvchilar ro\'yxati</h2><p class="sub" id="stuCnt">' + num(d.students.length) + ' ta o\'quvchi' + (q ? ' topildi' : '') + '</p></div></div>' +
      '<div class="card-b"><div class="toolbar" style="margin-bottom:14px"><div class="field">' + ic('search') + '<label class="sr" for="sq">O\'quvchi qidirish</label><input id="sq" type="search" placeholder="Ism yoki @username" value="' + esc(S.ui.sq) + '" autocomplete="off" enterkeyhint="search"></div>' + sortSel + '</div></div>' +
      '<div id="stuBody">' + studentsTable(d.students.slice()) + '</div></section>';
    put(tk, html);
  }

  /* ---------- 7.3 O'quvchi kartasi ---------- */
  function sessState(s) {
    if (!s.ended && Date.now() - ms(s.last_at) < 5 * 60e3) return pill('good', '', '<span class="pulse" aria-hidden="true"></span> Hozir ilovada');
    if (!s.ended) return pill('warn', 'circle-alert', 'Signal uzilgan');
    return pill('mute', 'log-out', 'Yakunlangan');
  }
  async function vOquvchi(r, tk) {
    const d = await api('/api/x/student?id=' + r.arg);
    if (!alive(tk)) return;
    const u = d.user || {}, name = u.name || ((u.first_name || '') + ' ' + (u.last_name || '')).trim() || ('ID ' + u.id);
    setTitle(name);
    const sess = d.sessions || [];
    sess.forEach((s) => { S.sessUser[s.id] = u.id; });
    const liveS = sess.find((s) => !s.ended && Date.now() - ms(s.last_at) < 5 * 60e3);
    const lessons = d.lessons || [], jami = lessons.length || S.jami || 36;
    const doneN = lessons.filter((l) => l.done_at).length, startN = lessons.filter((l) => !l.done_at && l.seen > 0).length;
    const st = d.stats || {}, pr = d.prefs || {};
    const vids = d.videos || [], vdone = vids.filter((v) => v.done_at).length;
    const head = '<header class="ph"><div class="pt"><div class="crumb"><a href="#oquvchilar">O\'quvchilar</a> · Karta</div>' +
      '<div class="prof"><span class="av lg" aria-hidden="true">' + esc(initials(name)) + '</span><div class="pt"><h1 tabindex="-1">' + esc(name) + '</h1>' +
      '<div class="meta">' + (u.username ? '<span class="tag">' + ic('at-sign') + esc(u.username) + '</span>' : '') + '<span class="tag">ID ' + esc(u.id) + '</span>' +
      '<span class="tag">' + ic('calendar') + 'Qo\'shilgan: ' + dday(u.joined_at) + '</span><span class="tag">' + ic('clock') + 'Oxirgi faollik: ' + rel(u.last_seen) + '</span>' +
      (liveS ? pill('good', '', '<span class="pulse" aria-hidden="true"></span> Hozir ilovada') : '') + (u.blocked ? pill('crit', 'ban', 'Botni bloklagan') : '') + '</div></div></div></div>' +
      (sess.length ? '<div class="ph-acts"><a class="btn pri" href="#sessiya/' + esc(sess[0].id) + '">' + ic('footprints') + '<span>Oxirgi safarni ko\'rish</span></a></div>' : '') + '</header>';
    const kp = '<div class="grid g-4 kpis">' +
      kpi({ lab: 'Ball', val: num(st.xp), ic: 'gem', foot: 'Bugun: +' + num(st.today_xp || 0) }) +
      kpi({ lab: 'Seriya', val: num(st.streak), unit: 'kun', ic: 'flame', foot: 'Eng uzun: ' + num(st.best_streak) + ' kun' }) +
      kpi({ lab: 'Tugatgan darslar', val: num(doneN), unit: '/ ' + jami, ic: 'book-check', foot: num(startN) + ' ta dars boshlangan' }) +
      kpi({ lab: 'Sessiyalar', val: num(d.sessions_total != null ? d.sessions_total : sess.length), ic: 'smartphone', foot: sess.length ? 'Oxirgisi: ' + rel(sess[0].started_at) : "Hali sessiya yo'q" }) + '</div>';
    /* sessiyalar */
    const sessH = sess.length ? table([
      { k: 'at', l: 'Boshlandi', lead: true }, { k: 'dur', l: 'Davomiyligi' }, { k: 'dev', l: 'Qurilma' }, { k: 'sc', l: 'Ekran · bosish', ml: 'Ekranlar va bosishlar' }, { k: 'st', l: 'Holat' },
    ], sess.map((s) => ({
      href: '#sessiya/' + s.id,
      c: {
        at: '<a class="nm nowrap" href="#sessiya/' + esc(s.id) + '">' + dt(s.started_at) + '</a>', dur: '<span class="nowrap">' + dur((s.dur_s || 0) * 1000) + '</span>',
        dev: '<span class="tag">' + ic(devIc(s.device_label)) + esc(s.device_label || DASH) + '</span>',
        sc: '<span class="nowrap">' + num(s.screens) + ' · ' + num(s.clicks) + '</span>', st: sessState(s),
      },
    })), { caption: 'Sessiyalar' }) + ((d.sessions_total || 0) > sess.length ? '<p class="sub" style="padding:10px 20px;margin:0;font-size:12.5px;color:var(--ink-3)">Jami ' + num(d.sessions_total) + ' ta sessiya, oxirgi ' + sess.length + ' tasi ko\'rsatilgan.</p>' : '')
      : '<div style="padding:0 20px 18px">' + empty('footprints', "Hali sessiya yo'q", "O'quvchi ilovani ochganda har bir kirishi shu yerda safar bo'lib chiqadi.") + '</div>';
    /* qurilmalar */
    const devH = (d.devices || []).length ? '<ul class="list">' + d.devices.map((x) => '<li><span class="li-ic">' + ic(devIc(x.label)) + '</span><span class="li-t"><b>' + esc(x.label || DASH) + '</b><small>' +
      esc(uniq([x.os, PLAT[x.platform] || x.platform, x.tg_version ? 'Telegram ' + x.tg_version : '', x.screen ? scrSize(x.screen) : '']).join(' · ')) + '</small></span>' +
      '<span class="li-r">' + num(x.sessions) + ' sessiya<br>' + rel(x.last_at) + '</span></li>').join('') + '</ul>' : empty('smartphone', "Qurilma ma'lumoti yo'q", '');
    const prefH = '<dl class="kv"><dt>Uslub</dt><dd>' + esc(USLUB[pr.uslub] || 'Tanlanmagan') + '</dd><dt>Rejim</dt><dd>' + esc(REJIM[pr.rejim] || DASH) + '</dd><dt>Arabcha matn</dt><dd>' + esc(ARAB[pr.arab] || DASH) + '</dd>' +
      '<dt>Kunlik eslatma</dt><dd>' + (pr.eslatma ? 'Yoqilgan' : "O'chirilgan") + '</dd></dl>';
    const wk = st.week || [], wmax = Math.max(1, ...wk.map((w) => w.xp || 0));
    const weekH = wk.length ? '<div class="weekbars" role="img" aria-label="Oxirgi 7 kunlik ball">' + wk.map((w) => '<div title="' + esc(dday(w.day) + ': ' + num(w.xp) + ' ball') + '"><i' + (w.xp ? '' : ' class="z"') + ' style="height:' + Math.max(3, Math.round((w.xp * 100) / wmax)) + '%"></i><small>' + KUNQ[tz(w.day).getUTCDay()] + '</small></div>').join('') + '</div>' : '';
    /* duellar va takliflar (SPEC 11.5) */
    const du = d.duels, ib = d.invited_by;
    const socialH = (du || d.invited != null || ib) ? card({ title: 'Duellar va takliflar', body:
      (du ? '<div class="kick" style="margin-bottom:8px">Duellar</div><dl class="kv"><dt>O\'ynagan</dt><dd>' + num(du.played) + ' ta</dd>' +
        '<dt>Natija</dt><dd>' + num(du.won) + ' g\'alaba · ' + num(du.lost) + ' mag\'lubiyat · ' + num(du.draw) + ' durrang</dd>' +
        '<dt>Faol</dt><dd>' + num(du.active || 0) + '</dd><dt>Muddati o\'tgan</dt><dd>' + num(du.expired || 0) + '</dd></dl>' : '') +
      '<div class="kick" style="margin:' + (du ? '16px' : '0') + ' 0 8px">Takliflar</div><dl class="kv">' +
      '<dt>Taklif qilgan</dt><dd>' + num(d.invited || 0) + ' ta do\'st' + (d.invited_rewarded != null ? ' (' + num(d.invited_rewarded) + ' tasi bonus olgan)' : '') + '</dd>' +
      '<dt>Taklif bonusi</dt><dd>' + (d.taklif_xp ? '+' + num(d.taklif_xp) + ' ball' : DASH) + '</dd>' +
      '<dt>Kim taklif qilgan</dt><dd>' + (ib ? (has('oquvchilar') ? '<a class="nm" href="#oquvchi/' + esc(ib.id) + '">' + esc(ib.name) + '</a>' : esc(ib.name)) +
        (ib.at ? ' · ' + dday(ib.at) : '') + (ib.rewarded ? ' · bonus berilgan' : ' · 1-darsni kutmoqda') : "O'zi kelgan") + '</dd></dl>' }) : '';
    /* darslar to'ri */
    const lgrid = lessons.length ? '<div class="lgrid">' + lessons.map((l) => {
      const p = l.slaydlar ? clamp(Math.round((l.seen * 100) / l.slaydlar), 0, 100) : 0;
      const cls = l.done_at ? 'done' : l.seen > 0 ? 'part' : '';
      const tip = l.n + '-dars · ' + (l.nomi || '') + ' · ' + num(l.seen) + '/' + num(l.slaydlar) + ' slayd' + (l.done_at ? ' · tugatilgan ' + dday(l.done_at) : l.started_at ? ' · boshlangan ' + dday(l.started_at) : '');
      const inner = l.n + (l.done_at ? ic('check') : l.seen > 0 ? '<small>' + p + '%</small>' : '') + (cls === 'part' ? '<span class="lp" style="width:' + p + '%"></span>' : '');
      return has('kurs') ? '<a class="lc ' + cls + '" href="#kurs/' + l.n + '" title="' + esc(tip) + '" aria-label="' + esc(tip) + '">' + inner + '</a>' : '<div class="lc ' + cls + '" title="' + esc(tip) + '">' + inner + '</div>';
    }).join('') + '</div><div class="legend" style="margin-top:14px"><span>' + ic('circle-check') + 'Tugatgan: ' + doneN + '</span><span>' + ic('circle-dot') + 'Boshlagan: ' + startN + '</span><span>' + ic('circle') + 'Boshlanmagan: ' + (jami - doneN - startN) + '</span></div>' : empty('book-open', "Darslar ma'lumoti yo'q", '');
    /* testlar */
    const tests = d.tests || [];
    const testH = tests.length ? '<ul class="list">' + tests.map((t) => {
      const ok = t.total && t.best === t.total;
      const ans = (t.last_answers || []);
      return '<li style="align-items:flex-start"><span class="li-ic">' + ic('list-checks') + '</span><span class="li-t"><b>' + esc(t.dars) + '-dars testi ' + pill(ok ? 'good' : t.best / (t.total || 1) >= 0.6 ? 'info' : 'warn', '', num(t.best) + '/' + num(t.total)) + '</b>' +
        '<small>' + num(t.tries) + ' urinish · oxirgisi ' + dt(t.updated_at) + '</small>' +
        (ans.length ? '<div class="qa" style="margin-top:8px" aria-label="Oxirgi urinish javoblari">' + ans.map((a) => '<span class="' + (a.pick == null ? 'sk0' : a.ok ? 'ok' : 'no') + '" title="' + esc(a.q + '-savol: ' + (a.pick == null ? 'javobsiz' : 'ABCDEFGH'.charAt(a.pick) + ' variant, ' + (a.ok ? "to'g'ri" : 'xato'))) + '">' +
          ic(a.pick == null ? 'circle' : a.ok ? 'check' : 'x') + a.q + '-savol' + (a.pick == null ? '' : ' · ' + 'ABCDEFGH'.charAt(a.pick)) + '</span>').join('') + '</div>' :
          '<small style="margin-top:6px">Savollar bo\'yicha natija 03.10 dan keyingi urinishlardan</small>') + '</span>' +
        (has('testlar') ? '<span class="li-r"><a class="link" href="#test/' + esc(t.dars) + '">Tahlil' + ic('chevron-right') + '</a></span>' : '') + '</li>';
    }).join('') + '</ul>' : empty('list-checks', "Hali test yechmagan", '');
    /* videolar */
    const vidH = vids.length ? '<ul class="list">' + vids.map((v) => {
      const p = v.davomiylik ? clamp(Math.round(((v.pos || 0) * 100) / v.davomiylik), 0, 100) : 0;
      return '<li style="align-items:flex-start"><span class="li-ic">' + ic('circle-play') + '</span><span class="li-t"><b>' + esc(v.dars) + '-dars · ' + T(v.nomi) + '</b><small>' +
        (v.done_at ? "Ko'rilgan · " + dday(v.done_at) : v.pos > 0 ? dur(v.pos * 1000) + ' / ' + dur(v.davomiylik * 1000) + ' (' + p + '%)' : 'Boshlanmagan · ' + dur(v.davomiylik * 1000)) + '</small>' +
        '<div class="vbar" aria-hidden="true"><i style="width:' + (v.done_at ? 100 : p) + '%"></i></div></span><span class="li-r">' + (v.done_at ? pill('good', 'check', "Ko'rilgan") : '') + '</span></li>';
    }).join('') + '</ul>' : empty('circle-play', "Kursda hali video yo'q", '');
    const html = head + kp +
      '<div class="grid g-2-1" style="align-items:start">' + card({ title: 'Ilovadagi safarlar', sub: "Har bir kirish: qaysi ekranlar ochilgan, qaysi tugmalar bosilgan", flush: true, body: sessH }) +
      '<div class="stack">' + card({ title: 'Qurilmalar', body: devH }) + card({ title: 'Sozlamalar', body: prefH + (weekH ? '<div class="kick" style="margin:16px 0 8px">Oxirgi 7 kunlik ball</div>' + weekH : '') }) + '</div></div>' +
      card({ title: 'Darslar', sub: num(doneN) + ' / ' + jami + ' tugatilgan' + (has('kurs') ? ". Katakni bosing, dars bo'yicha slaydlar tahlili ochiladi." : ''), body: lgrid }) +
      '<div class="grid g-2" style="align-items:start">' + card({ title: 'Testlar', sub: 'Oxirgi urinishdagi har bir savol', body: testH }) + '<div class="stack">' + card({ title: 'Videolar', sub: num(vdone) + ' / ' + vids.length + " ko'rilgan", body: vidH }) + socialH + '</div></div>';
    put(tk, html);
  }

  /* ---------- 7.4 Sessiya safari (timeline) ---------- */
  const SCR_IC = { bosh: 'house', darslar: 'book-open', video: 'circle-play', reyting: 'trophy', profil: 'user-round', dars: 'presentation', kitob: 'book-open-text',
    player: 'monitor-play', mashq: 'list-checks', natija: 'award', xato: 'circle-alert', yuklanmoqda: 'loader-circle',
    duellar: 'swords', duel: 'swords', 'duel-natija': 'award', taklif: 'user-plus' };
  const scrIc = (n) => SCR_IC[n] || (/^sheet-/.test(n || '') ? 'layers' : /^ob-/.test(n || '') ? 'sparkles' : 'panels-top-left');
  const CLK_IC = { back: 'arrow-left', 'tg-back': 'arrow-left', lesson: 'book-open', video: 'circle-play', vids: 'circle-play', quiz: 'list-checks', pick: 'circle-dot',
    'qz-check': 'check', 'qz-next': 'chevron-right', 'qz-restart': 'rotate-ccw', 'qz-retry': 'rotate-ccw', 'test-retry': 'rotate-ccw', retry: 'rotate-ccw',
    'vw-next': 'chevron-right', 'dk-next': 'chevron-right', 'vw-prev': 'chevron-left', 'dk-prev': 'chevron-left', 'vw-finish': 'flag', 'dk-finish': 'flag',
    'vw-zoom': 'zoom-in', 'zm-s': 'zoom-in', davr: 'trophy', tab: 'panels-top-left', kitob: 'book-open-text' };
  const clkIc = (n) => CLK_IC[n] || (/^duel-/.test(n || '') ? 'swords' : /^taklif-/.test(n || '') ? 'user-plus' : /^(set-|ob-)/.test(n || '') ? 'settings' : 'mouse-pointer-click');
  function refText(name, ref) {
    if (ref == null || ref === '') return '';
    if (/^\d+$/.test(ref)) return ref + '-dars';
    if (name === 'player') return 'Video ' + ref;
    return ref;
  }
  function clickText(e) {
    let t = esc(e.label || e.name);
    if ((e.name === 'pick' || e.name === 'duel-pick') && /^\d$/.test(e.ref || '')) t += ': ' + 'ABCDEFGH'.charAt(+e.ref) + ' variant';
    else if (e.ref != null && e.ref !== '' && String(e.label || '').indexOf(':') < 0) t += ' <span class="tag ref">' + esc(e.ref) + '</span>';
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
        cur = { k: 'visit', name: e.name, label: e.label || e.name, ref: e.ref, t, clicks: [] };
        out.push(cur);
      } else if (e.kind === 'click') {
        if (!cur || cur.closed) { cur = { k: 'visit', name: e.screen, label: e.screen_label || e.screen || 'Ekran', t, clicks: [], implicit: true }; out.push(cur); }
        cur.clicks.push(e);
      } else if (e.kind === 'end') {
        if (cur && !cur.closed) { close(t, cur.cont ? null : e.dur_ms); cur.closed = true; }
        lastEnd = { k: 'end', t, at: e.at };
        out.push(lastEnd);
      } else if (e.kind === 'resume') {
        out.push({ k: 'resume', t, at: e.at, away: lastEnd ? t - lastEnd.t : null });
        cur = { k: 'visit', name: e.screen || e.name, label: e.screen_label || e.screen || e.name || 'Ekran', ref: null, t, clicks: [], cont: true };
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
  function tlItem(cls, time, icon, body) {
    return '<li class="' + cls + '"><div class="t-time">' + time + '</div><div class="t-node">' + ic(icon) + '</div><div class="t-body">' + body + '</div></li>';
  }
  function timelineHtml(s, items, live) {
    const visits = items.filter((x) => x.k === 'visit');
    const maxDur = Math.max(1, ...visits.map((v) => v.dur || 0));
    let h = '<ol class="tl">' + tlItem('k-start', hms(s.started_at), 'log-in', '<div class="t-head"><b>Ilovaga kirdi</b></div><div class="t-sub">' +
      esc(uniq([s.device_label, PLAT[s.platform] || s.platform, s.tg_version ? 'Telegram ' + s.tg_version : '']).join(' · ')) + '</div>');
    items.forEach((it) => {
      if (it.k === 'visit') {
        const rt = refText(it.name, it.ref);
        const nowHere = it.open && live;
        let b = '<div class="t-head"><b>' + esc(it.label) + '</b>' + (rt ? '<span class="tag">' + esc(rt) + '</span>' : '') +
          '<span class="pill t-dur ' + (nowHere ? 'good' : 'mute') + '">' + ic('clock') + (nowHere ? dur(it.dur) + ' · hozir shu yerda' : dur(it.dur)) + '</span></div>';
        const sub = [];
        if (it.cont) sub.push('Ilovaga qaytgach shu ekranda davom etdi');
        if (it.clicks.length) sub.push(num(it.clicks.length) + ' ta bosish');
        else sub.push('Tugma bosilmadi');
        b += '<div class="t-sub">' + sub.join(' · ') + '</div><div class="t-db" aria-hidden="true"><i style="width:' + Math.max(1, Math.round(((it.dur || 0) * 100) / maxDur)) + '%"></i></div>';
        if (S.ui.tlClicks && it.clicks.length) {
          b += '<ul class="t-clicks" aria-label="Bosilgan tugmalar">' + groupClicks(it.clicks).map((g) => '<li><time>' + hms(g.at) + '</time>' + ic(clkIc(g.name)) +
            '<span>' + g.txt + (g.n > 1 ? '<span class="x">' + g.n + ' marta</span> <small class="muted">' + hms(g.lastAt) + ' gacha</small>' : '') + '</span></li>').join('') + '</ul>';
        }
        h += tlItem('k-visit', hms(it.t), scrIc(it.name), b);
      } else if (it.k === 'end') {
        h += tlItem('k-end', hms(it.at), 'log-out', '<div class="t-head"><b>Ilovadan chiqdi</b></div><div class="t-sub">Ilova yopildi yoki fonga o\'tdi</div>');
      } else if (it.k === 'resume') {
        h += tlItem('k-resume', hms(it.at), 'rotate-ccw', '<div class="t-head"><b>Ilovaga qaytdi</b></div>' + (it.away != null ? '<div class="t-gap">' + dur(it.away) + ' tashqarida bo\'ldi</div>' : ''));
      }
    });
    const last = items[items.length - 1];
    if (live) {
      h += tlItem('k-live', hms(s.last_at), 'activity', '<div class="t-head"><b>Hozir ilovada</b>' + pill('good', '', '<span class="pulse" aria-hidden="true"></span> jonli') + '</div><div class="t-sub">Oxirgi harakat: ' + hms(s.last_at) + '. Sahifa har 30 soniyada yangilanadi.</div>');
    } else if (s.ended && !(last && last.k === 'end')) {
      h += tlItem('k-end', hms(s.ended_at), 'log-out', '<div class="t-head"><b>Ilovadan chiqdi</b></div>');
    } else if (!s.ended) {
      h += tlItem('k-end', hms(s.last_at), 'log-out', '<div class="t-head"><b>Ilovadan chiqdi</b></div><div class="t-sub">Aniq vaqt noma\'lum: oxirgi signal ' + hms(s.last_at) + ' da keldi (ilova to\'satdan yopilgan yoki internet uzilgan).</div>');
    }
    return h + '</ol>';
  }
  function pathHtml(items, live) {
    const parts = [];
    items.forEach((it) => {
      if (it.k === 'visit') parts.push('<span class="pc">' + ic(scrIc(it.name)) + esc(it.label) + (it.ref ? ' <small>' + esc(refText(it.name, it.ref)) + '</small>' : '') + ' <small>' + dur(it.dur) + '</small></span>');
      else if (it.k === 'end') parts.push('<span class="pc end">' + ic('log-out') + 'Chiqdi</span>');
      else if (it.k === 'resume') parts.push('<span class="pc">' + ic('rotate-ccw') + 'Qaytdi</span>');
    });
    if (live) parts.push('<span class="pc now"><span class="pulse" aria-hidden="true"></span> Hozir shu yerda</span>');
    else if (!items.length || items[items.length - 1].k !== 'end') parts.push('<span class="pc end">' + ic('log-out') + 'Chiqdi</span>');
    const shown = parts.length > 44 ? parts.slice(0, 40).concat(['<span class="pc"><small>yana ' + (parts.length - 41) + ' qadam</small></span>', parts[parts.length - 1]]) : parts;
    return '<div class="path">' + shown.join('<span class="pa" aria-hidden="true">' + ic('chevron-right') + '</span>') + '</div>';
  }
  async function vSessiya(r, tk, soft) {
    const d = await api('/api/x/session?id=' + r.arg, soft === 'live' ? { fresh: true } : {});
    if (!alive(tk)) return;
    const s = d.session || {}, u = d.user || {}, tl = d.timeline || [];
    S.sessUser[r.arg] = u.id;
    const live = !s.ended && Date.now() - ms(s.last_at) < 5 * 60e3;
    const items = journey(s, tl);
    const visits = items.filter((x) => x.k === 'visit');
    const longest = visits.reduce((a, b) => ((b.dur || 0) > ((a && a.dur) || 0) ? b : a), null);
    const clicksN = sum(visits, (v) => v.clicks.length);
    const byScr = {};
    visits.forEach((v) => { const k = v.label; byScr[k] = byScr[k] || { l: esc(k), v: 0, ic: scrIc(v.name) }; byScr[k].v += v.dur || 0; });
    const spentTot = sum(visits, (v) => v.dur || 0);
    const spent = Object.keys(byScr).map((k) => byScr[k]).sort((a, b) => b.v - a.v).slice(0, 3)
      .map((x) => ({ l: x.l, ic: x.ic, v: x.v }));
    setTitle((u.name || 'O\'quvchi') + ' · safar');
    const summary = '<section class="deep"><div class="kick">O\'quvchi safari · ' + esc(dt(s.started_at)) + '</div>' +
      '<h2 style="margin-top:6px">' + esc(u.name || ('ID ' + u.id)) + '</h2><p class="sub" style="margin:0">' + esc(uniq([s.device_label, s.os, PLAT[s.platform] || s.platform]).join(' · ')) + '</p>' +
      '<div class="sum-grid"><div><div class="sv">' + hms(s.started_at) + '</div><div class="sl">Kirdi</div></div>' +
      '<div><div class="sv">' + dur((s.dur_s || 0) * 1000) + '</div><div class="sl">Ilovada bo\'ldi</div></div>' +
      '<div><div class="sv">' + num(visits.length) + '</div><div class="sl">Ekran ochildi</div></div>' +
      '<div><div class="sv">' + num(clicksN || s.clicks) + '</div><div class="sl">Tugma bosildi</div></div>' +
      '<div><div class="sv">' + (live ? '<span class="pulse" aria-hidden="true"></span> Hozir' : hms(s.ended ? s.ended_at : s.last_at)) + '</div><div class="sl">' + (live ? 'Ilovada' : 'Chiqdi') + '</div></div>' +
      (longest ? '<div><div class="sv" style="font-size:16px">' + esc(longest.label) + '</div><div class="sl">Eng uzoq: ' + dur(longest.dur) + '</div></div>' : '') + '</div>' +
      (spent.length ? '<div class="kick" style="margin:18px 0 10px">Vaqt qayerda o\'tdi</div>' + barList(spent, { total: spentTot, fmt: dur }) : '') + '</section>';
    const devCard = card({ title: 'Qurilma', body: '<dl class="kv"><dt>Qurilma</dt><dd>' + esc(s.device_label || DASH) + '</dd><dt>Tizim</dt><dd>' + esc(s.os || DASH) + '</dd>' +
      '<dt>Telegram</dt><dd>' + esc((PLAT[s.platform] || s.platform || DASH) + (s.tg_version ? ' · ' + s.tg_version : '')) + '</dd><dt>Ekran</dt><dd>' + esc(scrSize(s.screen)) + '</dd>' +
      '<dt>Telegram mavzusi</dt><dd>' + esc(SCHEME[s.scheme] || DASH) + '</dd><dt>Uslub</dt><dd>' + esc(USLUB[s.uslub] || 'Tanlanmagan') + '</dd><dt>Rejim</dt><dd>' + esc(REJIM[s.rejim] || DASH) + '</dd></dl>' +
      (s.ua ? '<p class="sub wrap-any" style="margin:12px 0 0;font-size:11.5px;color:var(--ink-3)">' + esc(s.ua) + '</p>' : '') });
    const head = ph({ crumb: '<a href="#oquvchilar">O\'quvchilar</a> · <a href="#oquvchi/' + esc(u.id) + '">' + esc(u.name || u.id) + '</a> · Safar', title: 'Ilovadagi safar',
      text: "Ilovaga kirgandan chiqqunigacha: qaysi ekranlar ochilgan, har birida qancha vaqt o'tgan va qaysi tugmalar bosilgan.",
      acts: '<a class="btn" href="#oquvchi/' + esc(u.id) + '">' + ic('user-round') + '<span>O\'quvchi kartasi</span></a>' });
    const tlCard = card({ title: 'Qadamma-qadam', sub: 'Vaqt Toshkent bo\'yicha · ekran yonidagi son: shu ekranda o\'tgan vaqt',
      acts: '<button type="button" class="chip" data-act="tl-clicks" aria-pressed="' + S.ui.tlClicks + '">' + ic('mouse-pointer-click') + 'Tugmalarni ko\'rsatish</button>',
      body: tl.length ? timelineHtml(s, items, live) : empty('footprints', "Bu sessiyada qadamlar yozilmagan", "Ilova ochilgan, lekin ekran yoki tugma ma'lumoti kelmagan.") });
    const html = head + '<div class="grid g-2-1">' + summary + devCard + '</div>' +
      card({ title: "Yo'l xaritasi", sub: 'Ekranlar ketma-ketligi', body: pathHtml(items, live) }) + tlCard;
    if (!put(tk, html)) return;
    if (live) {
      S.timers.push(setInterval(() => { if (alive(tk)) liveRefresh(); }, 30000));
    }
  }
  async function liveRefresh() {
    const y = W.scrollY;
    await render('live');
    W.scrollTo(0, y);
  }

  /* ---------- 7.5 Voronka ---------- */
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
        if (drop > 0) {
          const cls = p >= 30 ? 'crit' : p >= 15 ? 'warn' : 'mute';
          fun += '<li class="drop">' + pill(cls, 'trending-down', '−' + num(drop) + ' kishi (' + p + '%)' + (big && big.i === i ? " · eng katta yo'qotish" : '')) + '</li>';
        } else fun += '<li class="drop"><span class="dp">' + ic('arrow-down') + 'yo\'qotish yo\'q</span></li>';
      }
      fun += '<li' + (x.users ? '' : ' class="fz"') + '><span class="fn">' + (i + 1) + '</span><span class="fl"><b>' + esc(x.nomi) + '</b><small>boshidan ' + pc(x.users, first) + '%</small></span>' +
        '<span class="ft" aria-hidden="true"><i style="width:' + (x.users ? Math.max(1, (x.users * 100) / max) : 0).toFixed(1) + '%"></i></span><span class="fv">' + num(x.users) + '<small>kishi</small></span></li>';
    });
    const lm = S.ui.lmetric;
    const lessons = (d.lessons || []).map((l) => ({ x: String(l.n), full: l.n + '-dars · ' + (l.nomi || ''), v: lm === 'started' ? l.started : l.done,
      extra: 'Boshlagan: ' + num(l.started) + ' · Tugatgan: ' + num(l.done) + (l.started ? ' (' + pc(l.done, l.started) + '%)' : '') }));
    const chart = colChart('chLes', { data: lessons, yl: lm === 'started' ? 'Boshlagan o\'quvchilar, kishi' : 'Tugatgan o\'quvchilar, kishi', xl: 'Dars raqami', vlab: lm === 'started' ? 'Boshlagan' : 'Tugatgan',
      cols: ['Dars', lm === 'started' ? 'Boshlagan' : 'Tugatgan'], aria: "Har bir dars bo'yicha o'quvchilar soni", xw: 26, h: 240, empty: ['Hali hech kim dars boshlamagan', ''] });
    const summary = '<section class="deep"><div class="kick">' + days + ' kun · ' + num(d.joined || 0) + ' ta yangi o\'quvchi</div>' +
      (big ? '<h2 style="margin-top:6px">Eng katta yo\'qotish: ' + esc(steps[big.i - 1].nomi) + ' → ' + esc(steps[big.i].nomi) + '</h2><p class="sub" style="margin:0">' + num(big.drop) + ' kishi (' + big.pct + '%) shu bosqichda to\'xtagan. Shu joyni yaxshilash eng ko\'p foyda beradi.</p>'
        : '<h2 style="margin-top:6px">Yo\'qotish yo\'q</h2><p class="sub" style="margin:0">Barcha bosqichlarda o\'quvchilar soni kamaymagan.</p>') +
      '<div class="sum-grid">' + steps.filter((x) => ['kirdi', 'd1_tugatdi', 'd5_tugatdi', 'd36_tugatdi'].indexOf(x.key) >= 0).map((x) =>
        '<div><div class="sv">' + num(x.users) + ' <small style="font-size:13px;color:var(--nq-t2)">' + pc(x.users, first) + '%</small></div><div class="sl">' + esc(x.nomi) + '</div></div>').join('') + '</div></section>';
    const html = ph({ crumb: 'Boshqaruv', title: 'Voronka', text: "O'quvchi ilovaga kirgandan kursni tugatguncha qaysi bosqichda to'xtayotganini ko'rsatadi. Davrda qo'shilgan o'quvchilar hisoblanadi.",
      acts: seg('fdays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) +
      (d.joined ? summary + card({ title: "O'quvchi yo'li", sub: dday(d.since) + ' dan beri qo\'shilgan ' + num(d.joined) + ' kishi', body: '<ol class="fun">' + fun + '</ol>' })
        : card({ title: "O'quvchi yo'li", body: empty('filter', "Bu davrda yangi o'quvchi qo'shilmagan", "Davrni uzaytirib ko'ring.") })) +
      card({ title: "Darslar bo'yicha", sub: "Barcha o'quvchilar, 36 dars. Ustunni bosing yoki ustiga olib boring.", acts: seg('lmetric', [['done', 'Tugatgan'], ['started', 'Boshlagan']], lm, "Ko'rsatkich") + (S.charts.chLes ? tblBtn('chLes') : ''), body: chart });
    put(tk, html);
  }

  /* ---------- 7.6 Tugmalar va ekranlar ---------- */
  async function vTugmalar(r, tk) {
    const days = S.ui.cdays;
    const d = await api('/api/x/clicks?days=' + days);
    if (!alive(tk)) return;
    const top = d.top || [], scr = d.screens || [], daily = d.daily || [];
    const totC = sum(daily, (x) => x.clicks), totV = sum(daily, (x) => x.views);
    const longS = scr.reduce((a, b) => ((b.avg_ms || 0) > ((a && a.avg_ms) || 0) ? b : a), null);
    const tmax = Math.max(1, ...top.map((x) => x.count));
    const shown = S.ui.cAll ? top : top.slice(0, 12);
    const topH = top.length ? table([{ k: 'n', l: '#' }, { k: 'b', l: 'Tugma', lead: true }, { k: 'c', l: 'Bosishlar' }, { k: 'u', l: "O'quvchilar", r: true }],
      shown.map((x, i) => ({ c: { n: '<span class="rank' + (i === 0 ? ' r1' : '') + '">' + (i + 1) + '</span>', b: '<span class="nm">' + esc(x.label) + '</span><span class="sm">' + ic(scrIc(x.screen)) + ' ' + esc(x.screen_label || x.screen || DASH) + '</span>', c: mbar(x.count, tmax, num(x.count)), u: num(x.users) } })), { caption: "Eng ko'p bosilgan tugmalar" }) +
      (top.length > 12 ? '<div class="more" style="padding:0 0 16px"><button type="button" class="btn sm" data-act="more">' + ic(S.ui.cAll ? 'chevron-up' : 'chevron-down') + '<span>' + (S.ui.cAll ? 'Kamroq ko\'rsatish' : 'Hammasini ko\'rsatish (' + top.length + ')') + '</span></button></div>' : '')
      : '<div style="padding:0 20px 18px">' + empty('mouse-pointer-click', "Bu davrda tugma bosilmagan", "O'quvchilar ilovadan foydalanganda shu yerda eng ko'p bosilgan tugmalar chiqadi.") + '</div>';
    const smax = Math.max(1, ...scr.map((x) => x.views));
    const scrH = scr.length ? table([{ k: 'e', l: 'Ekran', lead: true }, { k: 'v', l: 'Ochilishlar' }, { k: 'u', l: "O'quvchilar", r: true }, { k: 't', l: "O'rtacha vaqt", r: true }],
      scr.map((x) => ({ c: { e: '<span class="nm">' + ic(scrIc(x.name)) + ' ' + esc(x.label) + '</span>', v: mbar(x.views, smax, num(x.views)), u: num(x.users), t: dur(x.avg_ms) } })), { caption: 'Ekranlar' })
      : '<div style="padding:0 20px 18px">' + empty('panels-top-left', "Bu davrda ekran ochilmagan", '') + '</div>';
    const cm = S.ui.cmetric;
    const chart = colChart('chClk', { data: daily.map((x) => ({ x: dday(x.day), full: dday(x.day) + ', ' + KUN[tz(x.day).getUTCDay()], v: cm === 'views' ? x.views : x.clicks, extra: cm === 'views' ? 'Bosishlar: ' + num(x.clicks) : 'Ekran ochilishi: ' + num(x.views) })),
      yl: cm === 'views' ? 'Ekran ochilishlari' : 'Tugma bosishlar', xl: 'Kun', vlab: cm === 'views' ? 'Ekran ochilishi' : 'Bosishlar', cols: ['Kun', cm === 'views' ? 'Ekran ochilishi' : 'Bosishlar'], aria: 'Kunlik bosishlar', xw: 46,
      empty: ["Bu davrda ma'lumot yo'q", ''] });
    const html = ph({ crumb: 'Boshqaruv', title: 'Tugmalar va ekranlar', text: "O'quvchilar ilovada qaysi tugmalarni ko'p bosadi va qaysi ekranlarda ko'p vaqt o'tkazadi.",
      acts: seg('cdays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) +
      '<div class="grid g-4 kpis">' + kpi({ lab: 'Tugma bosishlar', val: num(totC), ic: 'mouse-pointer-click', foot: 'Oxirgi ' + days + ' kun' }) +
      kpi({ lab: 'Ekran ochilishlari', val: num(totV), ic: 'panels-top-left', foot: 'Oxirgi ' + days + ' kun' }) +
      kpi({ lab: "Eng ko'p bosilgan", val: top.length ? '<span style="font-size:19px">' + esc(top[0].label) + '</span>' : DASH, ic: 'trophy', foot: top.length ? num(top[0].count) + ' marta · ' + esc(top[0].screen_label || '') : '' }) +
      kpi({ lab: "Eng uzoq qolinadigan ekran", val: longS ? '<span style="font-size:19px">' + esc(longS.label) + '</span>' : DASH, ic: 'timer', foot: longS ? "O'rtacha " + dur(longS.avg_ms) : '' }) + '</div>' +
      '<div class="grid g-2">' + card({ title: "Eng ko'p bosilgan tugmalar", sub: num(top.length) + ' ta tugma', flush: true, body: topH }) + card({ title: 'Ekranlar', sub: "Ochilishlar va o'rtacha vaqt", flush: true, body: scrH }) + '</div>' +
      card({ title: 'Kunlik faollik', sub: 'Oxirgi ' + days + ' kun', acts: seg('cmetric', [['clicks', 'Bosishlar'], ['views', 'Ekran ochilishi']], cm, "Ko'rsatkich") + (S.charts.chClk ? tblBtn('chClk') : ''), body: chart });
    put(tk, html);
  }

  /* ---------- 7.7 Qurilmalar ---------- */
  async function vQurilmalar(r, tk) {
    const days = S.ui.ddays;
    const d = await api('/api/x/devices?days=' + days);
    if (!alive(tk)) return;
    const N = d.users || 0;
    const dv = {};
    (d.device || []).forEach((x) => { dv[x.key] = x; });
    const tiles = [['telefon', 'Telefon', 'smartphone'], ['planshet', 'Planshet', 'tablet'], ['kompyuter', 'Kompyuter', 'monitor'], ['brauzer', 'Brauzer (Telegram Web)', 'globe']].map((t) =>
      kpi({ lab: t[1], val: num(dv[t[0]] ? dv[t[0]].users : 0), ic: t[2], foot: pc(dv[t[0]] ? dv[t[0]].users : 0, N) + "% o'quvchilar" })).join('');
    const L = (arr, icf) => barList((arr || []).map((x) => ({ l: esc(x.label), v: x.users, ic: icf ? icf(x) : '' })), { total: N, et: "Ma'lumot yo'q" });
    const topL = (d.labels || [])[0];
    const sv1 = (arr, pre) => { const x = (arr || [])[0]; return x ? '<div><div class="sv">' + pc(x.users, N) + '%</div><div class="sl">' + esc(pre + x.label) + '</div></div>' : ''; };
    const html = ph({ crumb: 'Boshqaruv', title: 'Qurilmalar', text: "O'quvchilar ilovani qaysi qurilmada ochadi. Har bir o'quvchi davrdagi oxirgi sessiyasi bo'yicha bir marta sanaladi.",
      acts: seg('ddays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) +
      (N ? '<div class="grid g-4 kpis">' + tiles + '</div>' +
        '<div class="grid g-2-1"><section class="deep fill"><div class="kick">' + days + ' kun · ' + num(N) + " ta o'quvchi</div><h2 style=\"margin-top:6px\">Ko'pchilik: " + esc(topL ? topL.label : DASH) + '</h2>' +
        '<p class="sub" style="margin:0">' + (topL ? num(topL.users) + ' kishi (' + pc(topL.users, N) + '%). Darslar va slaydlar shu qurilmada yaxshi ko\'rinishini tekshiring.' : '') + '</p>' +
        '<div class="sum-grid">' + (d.os || []).slice(0, 3).map((x) => '<div><div class="sv">' + pc(x.users, N) + '%</div><div class="sl">' + esc(x.label) + '</div></div>').join('') +
        sv1(d.tg_version, 'Telegram ') + sv1(d.screen, 'Ekran ') + sv1(d.scheme, 'Mavzu: ') + '</div></section>' +
        card({ title: 'Qurilma turlari', sub: 'Model guruhlari', body: L(d.labels, (x) => devIc(x.label)) }) + '</div>' +
        '<div class="grid g-3">' + card({ title: 'Operatsion tizim', body: L(d.os) }) + card({ title: 'Telegram ilovasi', sub: 'Platforma', body: L(d.platform) }) +
        card({ title: 'Telegram versiyasi va mavzusi', body: L(d.tg_version) + '<div class="kick" style="margin:16px 0 8px">Rang sxemasi</div>' + L(d.scheme, (x) => (x.key === 'dark' ? 'moon' : 'sun')) }) + '</div>' +
        card({ title: "Ekran o'lchami", sub: "Eng ko'p uchraydigan 10 tasi, CSS piksel (eni x bo'yi)", body: L(d.screen).replace('<ul class="bl">', '<ul class="bl two">') })
        : card({ body: empty('smartphone', "Bu davrda qurilma ma'lumoti yo'q", "O'quvchilar ilovani ochganda qurilmasi avtomatik aniqlanadi.") }));
    put(tk, html);
  }

  /* ---------- 7.8 Kurs ---------- */
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
            n: '<a class="nm" href="#kurs/' + n + '">' + n + '-dars</a><span class="sm">' + T(l.nomi) + '</span>' + (closed ? ' ' + pill('mute', 'lock', 'Yopiq') : ''),
            sl: num(l.slaydlar),
            m: (l.video || l.test) ? '<span class="mats">' + (l.video ? '<span class="tag" title="' + num(l.videolar) + ' video">' + ic('circle-play') + num(l.videolar) + ' video</span>' : '') +
              (l.test ? '<span class="tag" title="Mini test">' + ic('list-checks') + 'test</span>' : '') + '</span>' : '<span class="muted">' + DASH + '</span>',
            st: num(l.started), dn: num(l.done), pr: l.started ? mbar(l.done, l.started, pc(l.done, l.started) + '%') : '<span class="muted">' + DASH + '</span>',
            ta: l.test_avg != null ? num(l.test_avg, 1) : '<span class="muted">' + DASH + '</span>',
          },
        });
      });
    });
    const draft = S.ui.openDraft;
    const ctl = edit ? '<div class="openctl"><button type="button" class="ib" data-act="open-dec" aria-label="Bittaga kamaytirish"' + (draft <= 1 ? ' disabled' : '') + '>' + ic('minus') + '</button>' +
      '<span class="ov" id="openV" aria-live="polite">' + draft + '<small> / ' + S.jami + '</small></span>' +
      '<button type="button" class="ib" data-act="open-inc" aria-label="Bittaga oshirish"' + (draft >= S.jami ? ' disabled' : '') + '>' + ic('plus') + '</button>' +
      '<button type="button" class="btn pri" data-act="open-save"' + (draft === d.open ? ' disabled' : '') + '>' + ic('save') + '<span>Saqlash</span></button>' +
      (draft !== d.open ? '<button type="button" class="btn on-deep" data-act="open-reset">Bekor qilish</button>' : '') + '</div>'
      : '<div class="openctl"><span class="ov">' + d.open + '<small> / ' + S.jami + '</small></span>' + pill('dark', 'eye', "Faqat ko'rish: CEO va admin o'zgartiradi") + '</div>';
    const html = ph({ crumb: "O'quv jarayoni", title: 'Kurs', text: "Fonetika kursining 36 darsi: nechta o'quvchi boshlagan va tugatgan. Darsni bosing, slaydlar bo'yicha qayerda to'xtashganini ko'rasiz." }) +
      '<div class="grid g-2-1"><section class="deep" data-open="' + d.open + '"><div class="kick">Ochiq darslar</div><h2 style="margin-top:6px">O\'quvchilarga ochiq: ' + d.open + ' / ' + S.jami + ' dars</h2>' +
      '<p class="sub" style="margin:0">Darslar ketma-ket ochiladi: har bir dars oldingisi tugatilgach ochiladi. Bu son eng ko\'pi bilan nechta dars ochiq bo\'lishini belgilaydi.</p>' + ctl +
      '<div class="kick" style="margin:20px 0 10px">Qismlar bo\'yicha tugatilgan darslar</div>' +
      barList(parts.map((p) => ({ l: p.n + '-qism' + (p.nomi ? ' · ' + T(p.nomi) : ''), v: sum(p.darslar, (n) => (byN[n] ? byN[n].done : 0)) })), { et: "Hali tugatilgan dars yo'q", flat: true }) + '</section>' +
      '<div class="grid g-2 kpis">' + kpi({ lab: 'Slaydlar', val: num(sum(ls, (l) => l.slaydlar)), ic: 'presentation', foot: S.jami + ' dars' }) +
      kpi({ lab: 'Videolar', val: num(sum(ls, (l) => l.videolar)), ic: 'circle-play', foot: num(ls.filter((l) => l.video).length) + ' ta darsda' }) +
      kpi({ lab: 'Testlar', val: num(ls.filter((l) => l.test).length), ic: 'list-checks', foot: 'Darslardagi mashqlar' }) +
      kpi({ lab: 'Tugatishlar', val: num(sum(ls, (l) => l.done)), ic: 'book-check', foot: 'Jami tugatilgan darslar' }) + '</div></div>' +
      card({ title: 'Darslar', sub: '4 qism, ' + S.jami + ' dars', flush: true, body: table([
        { k: 'n', l: 'Dars', lead: true }, { k: 'sl', l: 'Slaydlar', r: true }, { k: 'm', l: 'Materiallar' }, { k: 'st', l: 'Boshlagan', r: true }, { k: 'dn', l: 'Tugatgan', r: true },
        { k: 'pr', l: 'Tugatish ulushi' }, { k: 'ta', l: 'Test o\'rtacha', r: true }], rows, { caption: 'Darslar' }) });
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
    const data = seen.map((x, i) => ({ x: String(x.idx), full: x.idx + '-slayd', v: x.users, hl: big && big.i === i, extra: pc(x.users, base) + '% boshlaganlardan' + (big && big.i === i ? '<br>Keyingi slaydga ' + num(big.drop) + ' kishi o\'tmagan' : '') }));
    const chart = colChart('chDrop', { data, yl: "Ko'rgan o'quvchilar, kishi", xl: 'Slayd raqami', vlab: "Ko'rgan", cols: ['Slayd', "Ko'rgan o'quvchilar"], aria: n + '-dars slaydlari bo\'yicha o\'quvchilar', xw: 26, h: 250,
      empty: ['Hali hech kim bu darsni boshlamagan', 'O\'quvchilar slaydlarni ko\'rishi bilan grafik paydo bo\'ladi.'] });
    const jami = S.jami || 36;
    const nav = (n > 1 ? '<a class="btn sm" href="#kurs/' + (n - 1) + '">' + ic('chevron-left') + '<span>' + (n - 1) + '-dars</span></a>' : '') +
      (n < jami ? '<a class="btn sm" href="#kurs/' + (n + 1) + '"><span>' + (n + 1) + '-dars</span>' + ic('chevron-right') + '</a>' : '') +
      (has('testlar') ? '<a class="btn sm" href="#test/' + n + '">' + ic('list-checks') + '<span>Test natijalari</span></a>' : '');
    const html = ph({ crumb: '<a href="#kurs">Kurs</a> · ' + n + '-dars', title: n + '-dars · ' + T(d.nomi), text: "Har bir slaydni nechta o'quvchi ko'rgani. Ustunlar keskin pasaygan joy: o'quvchilar shu slayddan keyin to'xtab qolgan.", acts: nav }) +
      '<div class="grid g-4 kpis">' + kpi({ lab: 'Slaydlar', val: num(d.slaydlar), ic: 'presentation' }) + kpi({ lab: 'Boshlagan', val: num(d.started), ic: 'play' }) +
      kpi({ lab: 'Tugatgan', val: num(d.done), ic: 'book-check' }) + kpi({ lab: 'Tugatish ulushi', val: pc(d.done, d.started) + '%', ic: 'percent', foot: 'Boshlaganlardan' }) + '</div>' +
      (big ? '<div class="note warn">' + ic('triangle-alert') + '<span>Eng ko\'p shu yerda to\'xtashgan: ' + (big.i + 1) + '-slayddan keyin ' + num(big.drop) + ' kishi (' + pc(big.drop, seen[big.i].users) + '%) keyingi slaydga o\'tmagan. Grafikda sariq ustun.</span></div>' : '') +
      card({ title: "Slaydlar bo'yicha", sub: num(d.slaydlar) + ' slayd', acts: S.charts.chDrop ? tblBtn('chDrop') : '', body: chart });
    put(tk, html);
  }

  /* ---------- 7.9 Testlar ---------- */
  const NOTE_03 = "Savollar bo'yicha natija 03.10 dan keyingi urinishlardan";
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
        d: (l.has_test ? '<a class="nm" href="#test/' + l.dars + '">' + l.dars + '-dars</a>' : '<span class="nm">' + l.dars + '-dars</span>') + '<span class="sm">' + T(l.nomi) + '</span>',
        t: l.has_test ? num(l.takers) : '<span class="muted">Test yo\'q</span>', a: l.has_test ? num(l.attempts) : '',
        b: l.avg_best != null ? '<b>' + num(l.avg_best, 1) + '</b>' : '<span class="muted">' + DASH + '</span>', p: l.has_test ? num(l.perfect) : '',
        h: l.hardest ? pill(l.hardest.wrong_pct >= 50 ? 'crit' : l.hardest.wrong_pct >= 30 ? 'warn' : 'good', l.hardest.wrong_pct >= 30 ? 'circle-x' : 'circle-check', l.hardest.q + '-savol · ' + l.hardest.wrong_pct + '% xato') : (l.takers ? '<span class="muted">' + DASH + '</span>' : '<span class="muted">Hali yechilmagan</span>'),
      },
    }));
    const html = ph({ crumb: "O'quv jarayoni", title: 'Testlar', text: "Har bir dars testi bo'yicha natijalar. Qatorni bosing, har bir savol va variantlar tahlili ochiladi." }) +
      '<div class="grid g-4 kpis">' + kpi({ lab: 'Testli darslar', val: num(withT.length), ic: 'list-checks', foot: num(taken.length) + ' tasi yechilgan' }) +
      kpi({ lab: 'Urinishlar', val: num(att), ic: 'rotate-ccw', foot: 'Barcha testlar bo\'yicha' }) +
      kpi({ lab: "O'rtacha eng yaxshi natija", val: avg != null ? num(avg, 1) : DASH, unit: avg != null ? 'ball' : '', ic: 'award', foot: '5 savollik testlarda' }) +
      kpi({ lab: "A'lo natijalar", val: num(perf), ic: 'trophy', foot: 'Hamma savolga to\'g\'ri javob' }) + '</div>' +
      (att ? '<div class="note">' + ic('info') + '<span>' + NOTE_03 + (d.since ? ' (birinchi yozuv: ' + dt(d.since) + ')' : '') + '. Eski urinishlarda faqat umumiy ball bor.</span></div>' : '') +
      card({ title: "Darslar bo'yicha", sub: num(list.length) + ' ta dars', flush: true,
        acts: chips('tf', [['taken', 'Yechilganlar (' + taken.length + ')'], ['all', 'Hammasi (' + ls.length + ')']], S.ui.tf, 'Saralash'),
        body: list.length ? table([{ k: 'd', l: 'Dars', lead: true }, { k: 't', l: 'Yechganlar', r: true }, { k: 'a', l: 'Urinishlar', r: true }, { k: 'b', l: "O'rtacha eng yaxshi", r: true },
          { k: 'p', l: "A'lo", r: true }, { k: 'h', l: 'Eng qiyin savol' }], rows, { caption: 'Testlar' }) : '<div style="padding:0 20px 18px">' + empty('list-checks', "Hali test yechilmagan", "O'quvchilar mashq qilganda natijalar shu yerda chiqadi.") + '</div>' });
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
      const cls = wp == null || !ans ? 'mute' : wp >= 50 ? 'crit' : wp >= 30 ? 'warn' : 'good';
      return '<section class="card qcard"><div class="qh"><span class="qn">' + (q.n || i + 1) + '-savol</span>' +
        (ans ? pill(cls, cls === 'good' ? 'circle-check' : 'circle-x', wp + '% xato') : pill('mute', '', "Javoblar yo'q")) +
        '<span class="spacer"></span><span class="tag">' + num(ans) + ' javob</span>' + (q.skipped ? '<span class="tag">' + num(q.skipped) + ' javobsiz</span>' : '') + '</div>' +
        '<p class="qq">' + T(q.q) + '</p><ol class="opts">' + (q.opts || []).map((o, j) => {
          const c = picks[j] || 0, p = pc(c, ans), ok = j === q.ok;
          return '<li' + (ok ? ' class="ok"' : '') + '><span class="ob" style="width:' + p + '%" aria-hidden="true"></span><span class="ol">' + 'ABCDEFGH'.charAt(j) + '</span>' +
            '<span class="ot">' + T(o) + (ok ? ' <span class="okp">' + pill('good', 'check', "To'g'ri javob") + '</span>' : '') + '</span>' +
            '<span class="oc">' + num(c) + ' ta<small>' + p + '%</small></span></li>';
        }).join('') + '</ol>' + (q.izoh ? '<div class="izoh"><b>Izoh:</b> ' + T(q.izoh) + '</div>' : '') + '</section>';
    }).join('');
    const jami = S.jami || 36;
    const nav = (n > 1 ? '<a class="btn sm" href="#test/' + (n - 1) + '">' + ic('chevron-left') + '<span>' + (n - 1) + '-dars</span></a>' : '') +
      (n < jami ? '<a class="btn sm" href="#test/' + (n + 1) + '"><span>' + (n + 1) + '-dars</span>' + ic('chevron-right') + '</a>' : '') +
      (has('kurs') ? '<a class="btn sm" href="#kurs/' + n + '">' + ic('presentation') + '<span>Slaydlar tahlili</span></a>' : '');
    const stH = st.length ? table([{ k: 'n', l: "O'quvchi", lead: true }, { k: 'b', l: 'Eng yaxshi natija' }, { k: 't', l: 'Urinishlar', r: true }, { k: 'u', l: 'Oxirgi urinish' }],
      st.map((x) => ({ href: has('oquvchilar') ? '#oquvchi/' + x.id : '', c: { n: who(x.name, '', has('oquvchilar') ? '#oquvchi/' + x.id : ''), b: mbar(x.best, x.total || total || 5, num(x.best) + '/' + num(x.total || total)), t: num(x.tries), u: dt(x.updated_at) } })), { caption: 'Natijalar' })
      : '<div style="padding:0 20px 18px">' + empty('users-round', "Bu testni hali hech kim yechmagan", '') + '</div>';
    const html = ph({ crumb: '<a href="#testlar">Testlar</a> · ' + n + '-dars', title: n + '-dars testi', text: T(d.test_nomi || '') + (d.nomi ? ' · ' + T(d.nomi) : ''), acts: nav }) +
      '<div class="grid g-4 kpis">' + kpi({ lab: 'Yechganlar', val: num(st.length), ic: 'users-round' }) + kpi({ lab: "O'rtacha eng yaxshi", val: avg != null ? num(avg, 1) : DASH, unit: avg != null ? '/ ' + total : '', ic: 'award' }) +
      kpi({ lab: "A'lo natija", val: num(perf), ic: 'trophy', foot: 'Hamma savolga to\'g\'ri' }) + kpi({ lab: 'Savollar', val: num(total), ic: 'circle-help' }) + '</div>' +
      (!anyAns ? '<div class="note">' + ic('info') + '<span>' + NOTE_03 + '.</span></div>' : '') +
      (qs.length ? '<div class="grid g-2">' + qh + '</div>' : card({ body: empty('list-checks', "Bu darsda test yo'q", '') })) +
      card({ title: "O'quvchilar natijasi", sub: num(st.length) + ' kishi', flush: true, body: stH });
    put(tk, html);
  }

  /* ---------- 7.10 Duellar va do'st takliflari (SPEC 11.5, faqat ko'rish) ---------- */
  const offNote = (key, nomi) => (S.me && S.me.features && S.me.features[key] === false
    ? '<div class="note warn">' + ic('triangle-alert') + '<span>"' + esc(nomi) + '" funksiyasi hozir o\'chirilgan: o\'quvchilar ilovada bu bo\'limni ko\'rmaydi.' + (has('funksiyalar') ? ' <a href="#funksiyalar">Funksiyalar</a> bo\'limida yoqish mumkin.' : '') + '</span></div>' : '');
  const stuLink = (p) => (p && p.id && has('oquvchilar') ? '#oquvchi/' + p.id : '');
  const DSTAT = { faol: ['info', 'hourglass', 'Faol'], tugadi: ['good', 'circle-check', 'Tugadi'], muddati_otdi: ['mute', 'clock', "Muddati o'tgan"] };
  function duelSide(p, win) {
    if (!p) return DASH;
    const sc = p.done ? '<span class="sm">' + num(p.correct) + ' to\'g\'ri · ' + dur(p.ms) + '</span>' : '<span class="sm">hali o\'ynamagan</span>';
    const nm = esc(p.name || ('ID ' + p.id));
    const l = stuLink(p);
    return '<span class="nm">' + (win ? ic('trophy') + ' ' : '') + (l ? '<a class="nm" href="' + l + '">' + nm + '</a>' : nm) + '</span>' + sc;
  }
  async function vDuellar(r, tk) {
    const days = S.ui.wdays || 30;
    const d = await api('/api/x/duels?days=' + days);
    if (!alive(tk)) return;
    const recent = d.recent || [], top = d.top || [], daily = d.daily || [], mo = d.modes || {};
    const dm = S.ui.wmetric || 'created';
    const chart = colChart('chDuel', { data: daily.map((x) => ({ x: dday(x.day), full: dday(x.day) + ', ' + KUN[tz(x.day).getUTCDay()], v: dm === 'finished' ? x.finished : x.created,
      extra: dm === 'finished' ? 'Boshlangan: ' + num(x.created) : 'Tugagan: ' + num(x.finished) })), yl: dm === 'finished' ? 'Tugagan duellar' : 'Boshlangan duellar', xl: 'Kun',
      vlab: dm === 'finished' ? 'Tugagan' : 'Boshlangan', cols: ['Kun', dm === 'finished' ? 'Tugagan' : 'Boshlangan'], aria: 'Kunlik duellar', xw: 46, empty: ["Bu davrda duel bo'lmagan", ''] });
    const wmax = Math.max(1, ...top.map((x) => x.played || 0));
    const topH = top.length ? table([{ k: 'n', l: '#' }, { k: 'p', l: "O'yinchi", lead: true }, { k: 'pl', l: "O'yinlar" }, { k: 'w', l: "G'alaba", r: true }],
      top.map((x, i) => ({ href: stuLink(x), c: { n: '<span class="rank' + (i === 0 ? ' r1' : '') + '">' + (i + 1) + '</span>',
        p: stuLink(x) ? '<a class="nm" href="' + stuLink(x) + '">' + esc(x.name) + '</a>' : '<span class="nm">' + esc(x.name) + '</span>',
        pl: mbar(x.played, wmax, num(x.played)), w: num(x.won) + ' <span class="muted">(' + pc(x.won, x.played) + '%)</span>' } })), { caption: "Eng faol o'yinchilar" })
      : '<div style="padding:0 20px 18px">' + empty('trophy', "Hali tugagan duel yo'q", '') + '</div>';
    const stH = barList([{ l: "G'olib aniqlangan", v: Math.max(0, (d.finished || 0) - (d.draws || 0)), ic: 'trophy' }, { l: 'Durrang', v: d.draws || 0, ic: 'scale' },
      { l: 'Faol', v: d.active || 0, ic: 'hourglass' }, { l: "Muddati o'tgan", v: d.expired || 0, ic: 'clock' }], { flat: true, et: "Hali duel yo'q" });
    const modeH = barList([{ l: 'Tasodifiy raqib', v: mo.random || 0, ic: 'swords' }, { l: "Do'st bilan", v: mo.friend || 0, ic: 'user-plus' }], { flat: true, et: "Hali duel yo'q" });
    const rows = recent.map((x) => {
      const st = DSTAT[x.status] || ['mute', '', esc(x.status)];
      const fin = x.status === 'tugadi';
      const res = fin ? (x.result === 'durrang' ? pill('warn', '', 'Durrang') : '<b class="num">' + num(x.a && x.a.correct) + ' : ' + num(x.b && x.b.correct) + '</b>') : '<span class="muted">' + DASH + '</span>';
      return { c: {
        at: '<span class="nowrap">' + dt(x.at) + '</span><span class="sm">' + (x.mode === 'friend' ? "Do'st bilan" : 'Tasodifiy raqib') + '</span>',
        a: duelSide(x.a, fin && x.result === 'a'), res, b: duelSide(x.b, fin && x.result === 'b'),
        st: pill(st[0], st[1], st[2]) + (x.status === 'faol' && x.expires_at ? '<span class="sm">' + dt(x.expires_at) + ' gacha</span>' : ''),
        ls: (x.lessons || []).length ? '<span class="sm" style="font-size:13px;color:var(--ink-2)">' + x.lessons.join(', ') + (x.lessons.length > 1 ? '-darslar' : '-dars') + '</span>' : DASH,
      } };
    });
    const html = ph({ crumb: 'Faollik', title: 'Duellar', text: "O'quvchilar o'rtasidagi bellashuvlar: 5 savol, har biriga 15 soniya. Savollar faqat ikkala o'quvchi tugatgan darslardan olinadi.",
      acts: seg('wdays', [[7, '7 kun'], [30, '30 kun'], [90, '90 kun']], days, 'Davr') }) + offNote('duel', 'Duellar') +
      '<div class="grid g-3 kpis">' + kpi({ lab: 'Jami duellar', val: num(d.total), ic: 'swords', foot: 'Oxirgi ' + days + ' kunda boshlangan' }) +
      kpi({ lab: 'Tugagan', val: num(d.finished), ic: 'circle-check', foot: pc(d.finished, d.total) + '% duellar' }) +
      kpi({ lab: "Muddati o'tgan", val: num(d.expired || 0), ic: 'clock', foot: '24 soatda o\'ynalmagan' }) +
      kpi({ lab: 'Faol', val: num(d.active || 0), ic: 'hourglass', foot: 'Ikkinchi o\'yinchi kutilmoqda' }) +
      kpi({ lab: 'Durrang', val: num(d.draws || 0), ic: 'scale', foot: 'Bir xil natija va vaqt' }) +
      kpi({ lab: "O'yinchilar", val: num(d.players || 0), ic: 'users-round', foot: "Duelda qatnashgan o'quvchilar" }) + '</div>' +
      '<div class="grid g-2-1">' + card({ title: 'Kunlik duellar', sub: 'Oxirgi ' + days + ' kun',
        acts: seg('wmetric', [['created', 'Boshlangan'], ['finished', 'Tugagan']], dm, "Ko'rsatkich") + (S.charts.chDuel ? tblBtn('chDuel') : ''), body: chart }) +
      '<div class="stack">' + card({ title: 'Duel turi', sub: 'Raqib qanday tanlangan', body: modeH }) + card({ title: 'Duellar holati', body: stH }) + '</div></div>' +
      card({ title: "Eng faol o'yinchilar", sub: "Tugagan duellar bo'yicha", flush: true, body: topH }) +
      card({ title: "So'nggi duellar", sub: num(recent.length) + ' ta', flush: true, id: 'duelRecent', body: rows.length ? table([{ k: 'at', l: 'Vaqt' }, { k: 'a', l: 'Chaqirgan', lead: true }, { k: 'res', l: 'Hisob' },
        { k: 'b', l: 'Raqib' }, { k: 'st', l: 'Holat' }, { k: 'ls', l: 'Savollar' }], rows, { caption: "So'nggi duellar" }) : '<div style="padding:0 20px 18px">' + empty('swords', "Bu davrda duel bo'lmagan", "O'quvchilar ilovadagi Duellar bo'limidan bellashuv boshlaydi.") + '</div>' });
    put(tk, html);
  }
  async function vTakliflar(r, tk) {
    const d = await api('/api/x/referrals');
    if (!alive(tk)) return;
    const recent = d.recent || [], top = d.top || [];
    const bonus = d.bonus || 50;
    const topH = top.length ? '<ul class="list">' + top.map((x, i) => '<li><span class="rank' + (i === 0 ? ' r1' : '') + '">' + (i + 1) + '</span>' +
      '<span class="li-t"><b>' + (stuLink(x) ? '<a class="nm" href="' + stuLink(x) + '" style="text-decoration:none">' + esc(x.name) + '</a>' : esc(x.name)) + '</b><small>' + num(x.invited) + ' ta do\'st · ' + num(x.rewarded) + ' tasi 1-darsni tugatgan</small></span>' +
      '<span class="li-r">+' + num(x.rewarded * bonus) + '<br>ball</span></li>').join('') + '</ul>' : empty('user-plus', "Hali hech kim do'st taklif qilmagan", '');
    const who2 = (p) => { if (!p) return DASH; const l = stuLink(p); return l ? '<a class="nm" href="' + l + '">' + esc(p.name) + '</a>' : '<span class="nm">' + esc(p.name) + '</span>'; };
    const rows = recent.map((x) => ({ c: {
      at: '<span class="nowrap">' + dt(x.at) + '</span>', a: who2(x.inviter), b: who2(x.invitee),
      st: x.rewarded ? pill('good', 'circle-check', 'Bonus berildi') + (x.rewarded_at ? '<span class="sm">' + dt(x.rewarded_at) + '</span>' : '') : pill('warn', 'hourglass', '1-darsni kutmoqda'),
    } }));
    const html = ph({ crumb: 'Faollik', title: "Do'st takliflari", text: "O'quvchi shaxsiy havola orqali do'stini taklif qiladi. Do'sti 1-darsni tugatganda ikkalasiga +" + num(bonus) + ' ball beriladi.' }) + offNote('taklif', "Do'st taklif qilish") +
      '<div class="grid g-4 kpis">' + kpi({ lab: 'Taklif bilan kelganlar', val: num(d.total), ic: 'user-plus', foot: 'Jami' }) +
      kpi({ lab: 'Bonus olganlar', val: num(d.rewarded), ic: 'circle-check', foot: pc(d.rewarded, d.total) + '% 1-darsni tugatgan' }) +
      kpi({ lab: 'Kutilmoqda', val: num((d.total || 0) - (d.rewarded || 0)), ic: 'hourglass', foot: '1-darsni hali tugatmagan' }) +
      kpi({ lab: 'Berilgan ball', val: num(d.earned || 0), ic: 'gem', foot: "Taklif qilgan va kelganga +" + num(bonus) + ' dan' }) + '</div>' +
      '<div class="grid g-2-1">' + card({ title: "So'nggi takliflar", sub: num(recent.length) + ' ta', flush: true, body: rows.length ? table([{ k: 'b', l: 'Kelgan o\'quvchi', lead: true }, { k: 'a', l: 'Taklif qilgan' }, { k: 'at', l: 'Kelgan vaqti' }, { k: 'st', l: 'Holat' }], rows, { caption: "So'nggi takliflar" })
        : '<div style="padding:0 20px 18px">' + empty('user-plus', "Hali taklif yo'q", "O'quvchilar Profil bo'limidagi havolani do'stlariga yuborganda shu yerda chiqadi.") + '</div>' }) +
      card({ title: 'Eng faol taklif qiluvchilar', body: topH }) + '</div>';
    put(tk, html);
  }

  /* ---------- 7.11 Xodimlar ---------- */
  async function vXodimlar(r, tk, soft) {
    const d = await api('/api/x/staff', soft === 'fresh' ? { fresh: true } : {});
    if (!alive(tk)) return;
    const list = d.staff || [];
    const ceos = list.filter((x) => x.role === 'ceo').length;
    const edit = S.me.can_edit && S.me.can_edit.xodimlar;
    const items = list.length ? '<ul class="list">' + list.map((x) => {
      const ro = ROLE[x.role] || [x.role, 'user-round', 'mute'];
      const me = x.id === S.me.user.id;
      const canRm = edit && !me && !(x.role === 'ceo' && ceos <= 1);
      return '<li><span class="av" aria-hidden="true">' + esc(initials(x.name)) + '</span><span class="li-t"><b>' + esc(x.name) + (me ? ' <span class="tag">Siz</span>' : '') + '</b><small>' +
        (x.username ? '@' + esc(x.username) + ' · ' : '') + "Qo'shilgan: " + dday(x.added_at) + '</small></span><span class="li-r" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end">' + pill(ro[2], ro[1], esc(ro[0])) +
        (canRm ? '<button type="button" class="btn sm danger" data-act="rm-staff" data-id="' + x.id + '" data-name="' + esc(x.name) + '" data-role="' + esc(ro[0]) + '">' + ic('user-x') + '<span>Chiqarish</span></button>' : '') + '</span></li>';
    }).join('') + '</ul>' : empty('users-round', "Xodimlar yo'q", '');
    const inv = edit ? '<section class="deep inv"><div class="kick">Taklif havolasi</div><h2>Yangi xodim qo\'shish</h2><p class="sub" style="margin:0">Rolni tanlang va havolani xodimga yuboring. Havola bir marta ishlaydi va 48 soat amal qiladi.</p>' +
      '<div class="row"><label class="sr" for="invRole">Rol</label><select class="sel" id="invRole"><option value="admin">Admin</option><option value="ustoz">Ustoz</option><option value="assistent">Assistent</option></select>' +
      '<button type="button" class="btn pri" data-act="invite">' + ic('link') + '<span>Havola yaratish</span></button></div><div id="invOut"></div></section>' : '';
    const roles = '<ul class="roles"><li>' + pill('good', 'crown', 'CEO') + '<span>Hamma bo\'limlar: statistika, kurs, xodimlar, funksiyalar.</span></li>' +
      '<li>' + pill('info', 'shield', 'Admin') + '<span>Statistika, o\'quvchilar, voronka, kurs (ochiq darslar), testlar, jurnal.</span></li>' +
      '<li>' + pill('warn', 'graduation-cap', 'Ustoz') + '<span>O\'quvchilar, kurs va testlar: faqat ko\'rish.</span></li>' +
      '<li>' + pill('mute', 'user-check', 'Assistent') + '<span>Admin panelga kirmaydi, faqat xodimlar boti.</span></li></ul>';
    const html = ph({ crumb: 'Tizim', title: 'Xodimlar', text: "Admin panel va xodimlar botiga kira oladigan jamoa. Yangi xodim faqat taklif havolasi orqali qo'shiladi." }) +
      '<div class="grid g-2-1" style="align-items:start">' + card({ title: 'Jamoa', sub: num(list.length) + ' ta xodim', body: items }) + '<div class="stack">' + inv + card({ title: 'Rollar', sub: 'Kim nimani ko\'radi', body: roles }) + '</div></div>';
    put(tk, html);
  }

  /* ---------- 7.12 Funksiyalar ---------- */
  const TAYYOR_BOSQICH = 3;  /* 1-, 2- va 3-bosqich (qo'llanma) funksiyalari ishlayapti (SPEC 10-11) */
  const FEAT_IC = { reyting: 'trophy', video: 'circle-play', test: 'list-checks', ball: 'gem', uslub: 'palette', eslatma: 'bell', hisobot: 'send', duel: 'swords', taklif: 'user-plus', qollanma: 'book-marked' };
  function featCard(m, on, feats, edit) {
    const note = m.key === 'reyting' && feats.ball === false && on ? '<div class="note warn" style="font-size:12.5px">' + ic('triangle-alert') + '<span>"Ball" o\'chirilgani uchun ilovada Reyting ham ko\'rinmaydi.</span></div>' : '';
    return '<section class="card feat' + (on ? '' : ' off') + '" data-feat="' + esc(m.key) + '"><div class="fh"><span class="fic">' + ic(FEAT_IC[m.key] || 'toggle-right') + '</span><div class="ft"><b>' + esc(m.nomi) + '</b><p>' + esc(m.tavsif) + '</p></div></div>' + note +
      '<div class="ff">' + (m.bosqich > TAYYOR_BOSQICH ? pill('info', 'clock', 'Tez orada · ' + m.bosqich + '-bosqich') : on ? pill('good', 'circle-check', 'Ishlayapti') : pill('mute', 'ban', "O'chirilgan")) +
      '<button type="button" class="sw" role="switch" aria-checked="' + on + '" data-act="feat" data-k="' + esc(m.key) + '" aria-label="' + esc(m.nomi) + '"' + (edit ? '' : ' disabled') + '><span class="trk" aria-hidden="true"></span><span class="swl">' + (on ? 'Yoqilgan' : "O'chirilgan") + '</span></button></div></section>';
  }
  async function vFunksiyalar(r, tk, soft) {
    const d = await api('/api/x/features', soft === 'fresh' ? { fresh: true } : {});
    if (!alive(tk)) return;
    S.feat = d;
    const f = d.features || {}, meta = d.meta || [];
    const edit = !!(S.me.can_edit && S.me.can_edit.funksiyalar);
    const now = meta.filter((m) => m.bosqich <= TAYYOR_BOSQICH), later = meta.filter((m) => m.bosqich > TAYYOR_BOSQICH);
    const offN = now.filter((m) => f[m.key] === false).length;
    const html = ph({ crumb: 'Tizim', title: 'Funksiyalar', text: "O'quvchilar ilovasi va botlardagi imkoniyatlarni yoqish va o'chirish. Server darhol amal qiladi, o'quvchi ilovani qayta ochganda ko'rinishi ham yangilanadi." }) +
      (offN ? '<div class="note warn">' + ic('triangle-alert') + '<span>Hozir ' + offN + ' ta funksiya o\'chirilgan.</span></div>' : '') +
      '<h2 class="kick" style="margin:0">Hozirgi funksiyalar</h2><div class="grid g-3">' + now.map((m) => featCard(m, f[m.key] !== false, f, edit)).join('') + '</div>' +
      (later.length ? '<h2 class="kick" style="margin:8px 0 0">Keyingi bosqichlar</h2><div class="grid g-3">' + later.map((m) => featCard(m, f[m.key] !== false, f, edit)).join('') + '</div>' : '');
    put(tk, html);
  }
  async function toggleFeat(btn) {
    const k = btn.dataset.k, on = btn.getAttribute('aria-checked') !== 'true';
    const m = ((S.feat && S.feat.meta) || []).find((x) => x.key === k) || { nomi: k, tavsif: '' };
    if (!on) {
      const ok = await confirmDlg({ title: '"' + esc(m.nomi) + '" o\'chirilsinmi?', text: esc(m.tavsif) + ' O\'quvchilar uchun bu imkoniyat darhol yopiladi, keyin istalgan vaqtda qayta yoqish mumkin.', ok: "O'chirish", icon: 'toggle-left' });
      if (!ok) return;
    }
    const setSw = (v) => {
      btn.setAttribute('aria-checked', String(v));
      const l = $('.swl', btn);
      if (l) l.textContent = v ? 'Yoqilgan' : "O'chirilgan";
      const c = btn.closest('.feat');
      if (c) c.classList.toggle('off', !v);
    };
    setSw(on);
    btn.disabled = true;
    try {
      const res = await api('/api/x/features', { method: 'POST', body: { key: k, on } });
      if (S.feat) S.feat.features = res.features;
      if (S.me) S.me.features = res.features;
      toast(m.nomi + (on ? ' yoqildi' : " o'chirildi"));
      haptic('ok');
      if (S.route && S.route.name === 'funksiyalar') render('fresh');
    } catch (e) {
      setSw(!on);
      btn.disabled = false;
      if (e.status !== 401) { toast((e && e.message) || "O'zgarish saqlanmadi", true); haptic('err'); }
    }
  }

  /* ---------- 7.13 Amallar jurnali ---------- */
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
    const body = list.length ? table([{ k: 'a', l: 'Amal', lead: true }, { k: 'w', l: 'Xodim' }, { k: 't', l: 'Vaqt' }],
      list.map((x) => ({ c: { a: '<div class="who"><span class="av" style="border-radius:11px">' + ic(ACT_IC[x.action] || 'history') + '</span><span class="wt"><b>' + esc(x.label) + '</b><small>' + esc(x.action_nomi || '') + '</small></span></div>',
        w: esc(x.staff_name || ('ID ' + x.staff_id)), t: dt(x.at) } })), { caption: 'Amallar jurnali' })
      : '<div style="padding:0 20px 18px">' + empty('history', "Hali amal yozilmagan", "Ochiq darslar, funksiyalar, takliflar va kirishlar shu yerda qayd etiladi.") + '</div>';
    const html = ph({ crumb: 'Tizim', title: 'Amallar jurnali', text: "Xodimlar admin panel va bot orqali nimani o'zgartirgani: ochiq darslar, funksiyalar, takliflar, kirishlar." }) +
      card({ title: "So'nggi amallar", sub: num(list.length) + ' ta yozuv', flush: true,
        acts: kinds.length > 1 ? chips('jf', [['all', 'Hammasi']].concat(kinds.map((k) => [k, esc(names[k])])), S.ui.jf, 'Amal turi') : '', body });
    put(tk, html);
  }

  /* ================= 8. Harakatlar ================= */
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
      out.innerHTML = '<div class="linkbox" style="margin-top:4px"><label class="sr" for="invLink">' + esc(rn) + ' uchun havola</label><input id="invLink" readonly value="' + esc(res.link) + '">' +
        '<button type="button" class="btn pri" data-act="copy">' + ic('copy') + '<span>Nusxalash</span></button>' +
        (inTg ? '<button type="button" class="btn on-deep" data-act="share">' + ic('send') + '<span>Telegram orqali yuborish</span></button>' : '') + '</div>' +
        '<p class="sub" style="margin:8px 0 0;font-size:12.5px">' + esc(rn) + ' uchun · ' + esc(dt(res.expires)) + ' gacha amal qiladi · bir martalik</p>';
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
    const ok = await confirmDlg({ title: 'Xodimni chiqarish', text: esc(btn.dataset.name) + ' (' + esc(btn.dataset.role) + ') xodimlar ro\'yxatidan chiqariladi. U admin panel va xodimlar botidan foydalana olmaydi.', ok: 'Chiqarish', icon: 'user-x' });
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
          const fig = D.getElementById(a.dataset.for);
          if (!fig) break;
          const on = a.getAttribute('aria-pressed') !== 'true';
          a.setAttribute('aria-pressed', String(on));
          $('span', a).textContent = on ? 'Grafik' : 'Jadval';
          $('.chart-tbl', fig).hidden = !on;
          $('.ch-plot', fig).hidden = on;
          $('.chart-cap', fig).hidden = on;
          $('.chart-x', fig).hidden = on;
          if (!on) drawChart(fig);
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
        case 'tl-clicks': S.ui.tlClicks = !S.ui.tlClicks; render(true); break;
        case 'more': S.ui.cAll = !S.ui.cAll; render(true); break;
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
    if (!e.target.closest('.chart')) hideTip();
  }

  /* ================= 9. Ishga tushirish ================= */
  function bindGlobal() {
    D.addEventListener('click', onClick);
    D.addEventListener('submit', (e) => {
      const f = e.target.closest('[data-form="tsearch"]');
      if (!f) return;
      e.preventDefault();
      const v = ($('#tq') || {}).value || '';
      S.ui.sq = v.trim();
      const inp = $('#tq');
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
      if (e.key === 'Escape' && !dlgClose) {
        const sh = $('#shell');
        if (sh && sh.classList.contains('open')) { menu(false); const b = $('.menu-btn'); if (b) b.focus(); }
        hideTip();
      }
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('tr.go[data-href]')) { e.preventDefault(); location.hash = e.target.dataset.href; }
    });
    D.addEventListener('pointerover', (e) => {
      const h = e.target.closest && e.target.closest('.chart .hit');
      if (h) showTip(h, e);
    });
    D.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse') return;
      const h = e.target.closest && e.target.closest('.chart .hit');
      if (h) showTip(h, e);
    });
    D.addEventListener('pointerout', (e) => {
      if (e.pointerType !== 'mouse') return;
      const h = e.target.closest && e.target.closest('.chart .hit');
      const to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.chart .hit');
      if (h && !to) hideTip();
    });
    W.addEventListener('scroll', () => { if (!$('#tip').hidden) hideTip(); }, { passive: true });
    W.addEventListener('hashchange', onHash);
  }
  async function boot() {
    tgInit();
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
    if (!parseHash()) history.replaceState(null, '', '#' + defaultSec());
    S.stack = [location.hash];
    render();
  }
  boot();
})();

/* Muhammadamin - talaba Mini App (vanilla JS, build bosqichisiz). Ko'rinish: NUQTA UI (04.10.2026).
   Bo'limlar: 1 yordamchilar · 2 Telegram · 3 saqlash · 4 holat, NUQTA mavzusi, sozlamalar · 5 API va navbat ·
   5b kuzatuv (sessiya, ekranlar, tugmalar) · 6 namuna rejimi · 7 ma'lumot va funksiyalar · 8 router · 9 ekranlar ·
   9b duellar va do'st taklifi · 9c qo'llanma · 10 harakatlar · 11 ishga tushirish.
   Manzaralar: /shared/nuqta-sahnalar.js (window.scene); bo'lmasa ilova manzarasiz ishlaydi.
   Ikonlar e'loni (tools/ikonlar.py uchun) keyingi qatorda. */
/* ikonlar: loader-circle minimize maximize image sun moon clock */
(function () {
  'use strict';

  /* ================= 1. Yordamchilar ================= */
  const D = document, H = D.documentElement, W = window;
  const $ = (s, r) => (r || D).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || D).querySelectorAll(s));
  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ESC[c]);
  const ARC = '؀-ۿݐ-ݿࡰ-ࣿﭐ-﷿ﹰ-﻿';
  const AR_RUN = new RegExp('[' + ARC + ']+(?:[\\s\\u00A0]+[' + ARC + ']+)*', 'g');
  const bdi = (s) => '<bdi dir="rtl" lang="ar" class="ar">' + s + '</bdi>';
  /* Matn: HTML uchun xavfsiz, arabcha bo'laklar <bdi dir="rtl" lang="ar"> ichida */
  const T = (s) => esc(s).replace(AR_RUN, (m) => bdi(m));
  /* Ikonlar: /shared/icons.svg sprite. Yuklangach hujjat ichiga joylanadi (href="#nom"), shunda har qayta
     chizishda sprite qayta so'ralmaydi va aloqa uzilganda ham ikonlar ko'rinadi. */
  let SPR = '/shared/icons.svg';
  const ic = (n, c) => '<svg class="i' + (c ? ' ' + c : '') + '" aria-hidden="true" focusable="false"><use href="' + SPR + '#' + n + '"/></svg>';
  async function inlineSprite() {
    try {
      const r = await fetch(SPR, { credentials: 'same-origin' });
      if (!r.ok) return;
      const t = await r.text(), m = /<svg\b[^>]*>([\s\S]*)<\/svg>\s*$/.exec(t);
      if (!m || m[1].indexOf('<symbol') < 0) return;
      const box = D.createElement('div');
      box.setAttribute('aria-hidden', 'true');
      box.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
      box.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" focusable="false">' + m[1] + '</svg>';
      D.body.insertBefore(box, D.body.firstChild);
      SPR = '';
      $$('use').forEach((u) => { const h = u.getAttribute('href') || ''; const k = h.indexOf('#'); if (k > 0) u.setAttribute('href', h.slice(k)); });
    } catch (e) { /* tashqi sprite bilan davom etiladi */ }
  }
  const num = (n) => String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const mins = (s) => Math.max(1, Math.round((s || 0) / 60));
  const mmss = (s) => { s = Math.max(0, Math.round(s || 0)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  const ini = (name) => {
    const p = String(name || '').replace(/[^\p{L}\s]/gu, '').trim().split(/\s+/).filter(Boolean);
    return ((p[0] ? p[0][0] : '?') + (p[1] ? p[1][0] : '')).toUpperCase();
  };
  const reduced = () => { try { return W.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } };
  const WD = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'];
  const wdOf = (iso) => { const p = String(iso).split('-').map(Number); return WD[(new Date(Date.UTC(p[0], p[1] - 1, p[2])).getUTCDay() + 6) % 7]; };
  const todayIso = () => new Date(Date.now() + 5 * 36e5).toISOString().slice(0, 10);
  const isoAdd = (iso, k) => { const p = iso.split('-').map(Number); return new Date(Date.UTC(p[0], p[1] - 1, p[2] + k)).toISOString().slice(0, 10); };
  const pad3 = (i) => String(i).padStart(3, '0');
  const uniq = (a) => Array.from(new Set(a)).sort((x, y) => x - y);
  const sr = (s) => '<span class="sr">' + s + '</span>';
  /* NUQTA bloklari: romb ikon, manzara joyi, ث belgisi */
  const dia = (icon, c) => `<span class="dia${c ? ' ' + c : ''}" aria-hidden="true">${icon}</span>`;
  const scn = (focus, v) => `<div class="sc" data-scene="${v || ''}" data-focus="${focus || 'card'}" aria-hidden="true"></div>`;
  const band = () => `<div class="band" aria-hidden="true">${scn('card')}</div>`;
  const sig = () => '<span class="nq-sig" aria-hidden="true"><i></i><i></i><i></i></span>';

  /* ================= 2. Telegram ================= */
  const tg = (W.Telegram && W.Telegram.WebApp) || null;
  const tgv = (v) => { try { return !!(tg && tg.isVersionAtLeast && tg.isVersionAtLeast(v)); } catch (e) { return false; } };
  const INIT = (tg && tg.initData) || '';
  const PREVIEW = !INIT;
  const TGU = (!PREVIEW && tg.initDataUnsafe && tg.initDataUnsafe.user) || null;
  function hap(kind, arg) {
    if (!tgv('6.1') || !tg.HapticFeedback) return;
    try {
      if (kind === 'sel') tg.HapticFeedback.selectionChanged();
      else if (kind === 'imp') tg.HapticFeedback.impactOccurred(arg || 'light');
      else tg.HapticFeedback.notificationOccurred(arg || 'success');
    } catch (e) { /* jim */ }
  }
  let bbOn = null;
  function backBtn(on) {
    if (!tgv('6.1') || bbOn === on) return;
    bbOn = on;
    try { if (on) tg.BackButton.show(); else tg.BackButton.hide(); } catch (e) { /* jim */ }
  }
  let swOn = null;
  function swipes(on) {
    if (!tgv('7.7') || swOn === on) return;
    swOn = on;
    try { if (on) tg.enableVerticalSwipes(); else tg.disableVerticalSwipes(); } catch (e) { /* jim */ }
  }
  /* Telegram sarlavha / fon / pastki panel ranglari - faol manzara tokenlaridan (--bg, --card) */
  const HEX = /^#[0-9a-f]{6}$/i;
  function tgColors() {
    let bg = '', card = '';
    try { const cs = W.getComputedStyle(H); bg = cs.getPropertyValue('--bg').trim(); card = cs.getPropertyValue('--card').trim(); } catch (e) { /* jim */ }
    if (!HEX.test(bg)) return;
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', bg);
    if (!tg) return;
    try {
      if (tgv('6.9')) tg.setHeaderColor(bg);
      if (tgv('6.1')) tg.setBackgroundColor(bg);
      if (tgv('7.10')) tg.setBottomBarColor(HEX.test(card) ? card : bg);
    } catch (e) { /* jim */ }
  }

  /* ================= 3. Saqlash ================= */
  const ls = {
    get(k, d) { try { const v = W.localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { W.localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* xotira yopiq */ } },
  };
  const raw = {
    get(k) { try { return W.localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { W.localStorage.setItem(k, v); } catch (e) { /* jim */ } },
  };
  const UID = (TGU && TGU.id) || 0;
  const KP = 'noon_prefs_' + UID, KL = 'noon_last_' + UID, KO = 'noon_out_' + UID, KHINT = 'noon_hint_rot', KDEMO = 'noon_demo';
  /* NUQTA: KNQ = {v: tanlangan manzara | null, a: 1 aylanadi / 0 tanlangan, x: 1 "uslub" funksiyasi o'chiq};
     KOB - tanishuv o'tilgan; 'nuqta.manzara' - aylanish ko'rsatkichi (qurilma bo'yicha, NUQTA qoidasi) */
  const KNQ = 'noon_nq_' + UID, KOB = 'noon_ob_' + UID, KROT = 'nuqta.manzara';
  const cloud = {
    ok: () => !!(tgv('6.9') && tg.CloudStorage),
    get(keys) {
      return new Promise((res) => {
        if (!cloud.ok()) { res(null); return; }
        let done = false;
        const fin = (v) => { if (!done) { done = true; res(v); } };
        try { tg.CloudStorage.getItems(keys, (err, v) => fin(err ? null : v)); } catch (e) { fin(null); }
        setTimeout(() => fin(null), 3000);
      });
    },
    set(k, v) { if (!cloud.ok()) return; try { tg.CloudStorage.setItem(k, String(v)); } catch (e) { /* jim */ } },
  };

  /* ================= 4. Holat, NUQTA mavzusi, sozlamalar ================= */
  const S = {
    phase: 'boot', err: null, K: null, me: null,
    prefs: { uslub: null, rejim: 'auto', arab: 'm', eslatma: true },
    stack: [{ s: 'bosh' }], ob: 0, qOpen: null,
    tests: {}, testErr: {}, quiz: null, result: null, zoom: null,
    rating: { davr: 'hafta', hafta: null, umumiy: null, at: {}, err: null, busy: false },
    du: { d: null, at: 0, err: null, busy: null, note: null, items: {}, fin: {}, rev: {}, gt: {}, gl: {}, gerr: {}, cu: {}, cr: {}, inv: null, kod: '', sh: {} },
    tk: { d: null, at: 0, err: null, busy: false },
  };
  const QS = new URLSearchParams(W.location.search);
  const qid = (v) => (/^[A-Za-z0-9_-]{3,64}$/.test(v || '') ? v : '');
  const START = { tab: QS.get('tab'), dars: parseInt(QS.get('dars'), 10) || 0, duel: qid(QS.get('duel')), kod: qid(QS.get('duel_kod')) };
  (function () {
    const sp = tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param;
    if (!sp) return;
    const m = /^dars(\d{1,2})$/.exec(sp);
    if (m) START.dars = +m[1];
    else if (/^(darslar|video|reyting|profil)$/.test(sp)) START.tab = sp;
  })();
  /* Manzaralar va rejim. Avto: 06:00-18:59 kunduzgi (kun), qolgani tungi (tun, "oy nuri") */
  const V = ['sahro', 'voha', 'shahar', 'qahva', 'xattot', 'shom'];
  const VN = { sahro: 'Sahro', voha: 'Voha', shahar: 'Shahar', qahva: 'Qahva', xattot: 'Xattot', shom: 'Shom' };
  const modeAt = () => { const h = new Date().getHours(); return h >= 6 && h < 19 ? 'kun' : 'tun'; };
  const mOf = (r) => (r === 'light' ? 'kun' : r === 'dark' ? 'tun' : modeAt());
  const rejimNow = () => S.prefs.rejim || 'auto';
  const greet = () => { const h = new Date().getHours(); return h < 5 ? 'Xayrli tun' : h < 11 ? 'Xayrli tong' : h < 18 ? 'Xayrli kun' : h < 22 ? 'Xayrli kech' : 'Xayrli tun'; };
  /* NQ.v - shu ochilishdagi manzara (index.html dagi skript birinchi chizishdan oldin tanlaydi) */
  const NQ = { v: V.indexOf(H.getAttribute('data-v')) >= 0 ? H.getAttribute('data-v') : 'sahro', a: true, f: null, x: false };
  (function () { const n = ls.get(KNQ, {}) || {}; NQ.a = n.a !== 0; NQ.f = V.indexOf(n.v) >= 0 ? n.v : null; NQ.x = n.x === 1; })();
  const nqSave = () => ls.set(KNQ, { v: NQ.f, a: NQ.a ? 1 : 0, x: NQ.x ? 1 : 0 });
  function nextV() {
    const k = V.indexOf(raw.get(KROT)), v = V[k < 0 ? 0 : (k + 1) % V.length];
    raw.set(KROT, v);
    return v;
  }
  let thKey = '';
  function applyTheme(force) {
    const m = mOf(rejimNow()), a = S.prefs.arab === 'l' ? 'l' : 'm', k = NQ.v + m;
    H.setAttribute('data-v', NQ.v);
    H.setAttribute('data-m', m);
    H.setAttribute('data-arab', a);
    if (k === thKey && !force) return;
    thKey = k;
    tgColors();
    paintScenes(D);
  }
  /* Manzaralar: [data-scene] konteynerlari o'lchamiga qarab SVG bilan to'ldiriladi (kalit o'zgarmasa qayta chizilmaydi) */
  function paintScenes(root) {
    if (typeof W.scene !== 'function') return;
    const night = H.getAttribute('data-m') === 'tun';
    $$('[data-scene]', root || D).forEach((el) => {
      const w = Math.round(el.clientWidth), h = Math.round(el.clientHeight);
      if (!w || !h) return;
      let v = el.getAttribute('data-scene');
      if (V.indexOf(v) < 0) { const p = el.parentNode && el.parentNode.closest ? el.parentNode.closest('[data-v]') : null; v = (p && p.getAttribute('data-v')) || NQ.v; }
      if (V.indexOf(v) < 0) v = NQ.v;
      const key = v + '|' + w + '|' + h + '|' + night;
      if (el._k === key) return;
      el._k = key;
      try { el.innerHTML = W.scene(v, w, h, { focus: el.getAttribute('data-focus') || 'card', night }); } catch (e) { el.innerHTML = ''; }
    });
  }
  /* Profil/tanishuv: manzarani tanlash (aylanish o'chadi) va "Har ochilganda almashsin" */
  function setManzara(v) {
    if (V.indexOf(v) < 0) return;
    NQ.v = v; NQ.f = v; NQ.a = false;
    nqSave();
    raw.set(KROT, v);
    cloud.set('nq_manzara', v); cloud.set('nq_aylan', '0');
    applyTheme();
  }
  function setAylan(on) {
    NQ.a = on;
    if (!on) NQ.f = NQ.v;
    nqSave();
    raw.set(KROT, NQ.v);
    cloud.set('nq_aylan', on ? '1' : '0'); cloud.set('nq_manzara', NQ.v);
  }
  /* "uslub" funksiyasi (Ko'rinish tanlash) o'chiq bo'lsa: tanlov e'tiborga olinmaydi, manzara har ochilganda almashadi */
  function nqFeat() {
    const off = !feat('uslub');
    if (off === NQ.x) return;
    NQ.x = off;
    nqSave();
    if (off && !NQ.a) { NQ.v = nextV(); applyTheme(); } else if (!off && !NQ.a && NQ.f && NQ.f !== NQ.v) { NQ.v = NQ.f; applyTheme(); }
  }
  /* CloudStorage dagi tanlov (boshqa qurilmada qilingan bo'lishi mumkin) */
  function nqCloud(c) {
    const a = c.nq_aylan === '0' ? false : c.nq_aylan === '1' ? true : null, m = V.indexOf(c.nq_manzara) >= 0 ? c.nq_manzara : null;
    if (a === false && m) {
      const ch = NQ.a || NQ.f !== m;
      NQ.a = false; NQ.f = m;
      if (ch) nqSave();
      if (!NQ.x && NQ.v !== m) { NQ.v = m; raw.set(KROT, m); applyTheme(); if (S.phase === 'ready') render('same'); }
    } else if (a === true && !NQ.a) { NQ.a = true; nqSave(); }
  }
  let prefsQ = {}, prefsT = 0, prefsTry = 0;
  function savePrefsLocal() {
    ls.set(KP, { uslub: S.prefs.uslub, rejim: S.prefs.rejim, arab: S.prefs.arab, eslatma: S.prefs.eslatma });
  }
  function setPrefs(patch) {
    Object.assign(S.prefs, patch);
    savePrefsLocal();
    ['rejim', 'arab'].forEach((k) => { if (k in patch && patch[k] != null) cloud.set(k, patch[k]); });
    applyTheme();
    if (PREVIEW) return;
    Object.assign(prefsQ, patch);
    clearTimeout(prefsT);
    prefsT = setTimeout(syncPrefs, 300);
  }
  async function syncPrefs() {
    const body = prefsQ;
    if (!Object.keys(body).length) return;
    prefsQ = {};
    try { await api('/api/s/prefs', body); prefsTry = 0; } catch (e) {
      prefsQ = Object.assign({}, body, prefsQ);
      if (++prefsTry <= 3) { clearTimeout(prefsT); prefsT = setTimeout(syncPrefs, 4000 * prefsTry); }
    }
  }

  /* ================= 5. API va hodisalar navbati ================= */
  class ApiErr extends Error { constructor(st, msg) { super(msg); this.st = st; } }
  const NET_MSG = "Internet aloqasi yo'q yoki server javob bermayapti.";
  function errText(st) {
    if (st === 401) return 'Kirish tasdiqlanmadi. Ilovani Telegram ichidan qayta oching.';
    if (st === 403) return 'Bu dars hali yopiq. Ustoz ochganda ochiladi.';
    if (st === 404) return 'Material topilmadi.';
    if (st === 429) return "Juda ko'p so'rov yuborildi. Birozdan keyin urinib ko'ring.";
    if (st >= 500) return "Serverda vaqtinchalik xatolik. Birozdan keyin urinib ko'ring.";
    return "So'rov bajarilmadi.";
  }
  async function req(url, o) {
    const tries = o.retries == null ? 2 : o.retries;
    let last = null;
    for (let a = 0; a <= tries; a++) {
      if (a) await sleep(450 * Math.pow(2, a - 1));
      const ctl = typeof AbortController === 'function' ? new AbortController() : null;
      const tm = setTimeout(() => { if (ctl) ctl.abort(); }, o.timeout || 15000);
      try {
        const h = { Accept: 'application/json' };
        if (o.body !== undefined) h['Content-Type'] = 'application/json';
        if (o.auth) h['X-Init-Data'] = INIT;
        const r = await fetch(url, {
          method: o.method || 'GET', headers: h, body: o.body !== undefined ? JSON.stringify(o.body) : undefined,
          signal: ctl ? ctl.signal : undefined, cache: o.cache || 'no-store', credentials: 'same-origin',
        });
        clearTimeout(tm);
        let data = null;
        try { data = await r.json(); } catch (e) { data = null; }
        if (r.ok && data) return data;
        const st = r.ok ? 500 : r.status;
        last = new ApiErr(st, (data && data.xato) || errText(st));
        if (st < 500) throw last;
      } catch (e) {
        clearTimeout(tm);
        if (e instanceof ApiErr && e.st < 500) throw e;
        if (!(e instanceof ApiErr)) last = new ApiErr(0, NET_MSG);
      }
    }
    throw last || new ApiErr(0, NET_MSG);
  }
  const api = (path, body) => req(path, { method: body === undefined ? 'GET' : 'POST', body, auth: true });
  const getJSON = (url) => req(url, { cache: 'no-cache' });
  const sendEv = (ev) => (PREVIEW ? demoEvent(ev) : api('/api/s/event', ev));

  /* Server javobini mahalliy holatga qo'shish */
  function mergeEv(ev, r) {
    if (!r || !S.me) return;
    if (r.stats) {
      const o = +(S.me.stats && S.me.stats.streak) || 0, nw = +r.stats.streak || 0;
      if (nw > o) S.skFx = [S.skFx ? S.skFx[0] : o, nw];
      S.me.stats = Object.assign({}, S.me.stats, r.stats);
    }
    if (r.course && Array.isArray(r.course.available)) S.me.course = Object.assign({}, S.me.course, r.course);
    const pr = S.me.progress, it = r.item;
    if (!it) return;
    if (ev.type === 'slide' || ev.type === 'lesson_done') {
      const k = String(ev.dars), c = pr.lessons[k] || { seen: [], done_at: null };
      pr.lessons[k] = Object.assign({}, c, it, { seen: uniq((c.seen || []).concat(it.seen || [])) });
    } else if (ev.type === 'video_pos' || ev.type === 'video_done') {
      const c = pr.videos[ev.vid] || {};
      pr.videos[ev.vid] = Object.assign({}, c, it, { done_at: it.done_at || c.done_at || null });
    } else if (ev.type === 'test_done') pr.tests[String(ev.dars)] = Object.assign({}, it);
  }

  /* Slayd va video holati navbati: tarmoq uzilsa ham yo'qolmaydi (localStorage) */
  const OB = { q: (ls.get(KO, []) || []).filter((e) => e && e.type), busy: false, t: 0, warned: false, retry: 0 };
  function enqueue(ev) {
    if (ev.type === 'video_pos') OB.q = OB.q.filter((x) => !(x.type === 'video_pos' && x.vid === ev.vid));
    OB.q.push(ev);
    ls.set(KO, OB.q);
    clearTimeout(OB.t);
    OB.t = setTimeout(flush, 500);
  }
  async function flush() {
    if (OB.busy) return false;
    if (!OB.q.length) return true;
    if (!S.me) return false;
    OB.busy = true;
    let ok = true;
    while (OB.q.length) {
      const ev = OB.q[0];
      try {
        mergeEv(ev, await sendEv(ev));
      } catch (e) {
        if (!e.st || e.st >= 500 || e.st === 429) {
          ok = false;
          if (!OB.warned) { OB.warned = true; toast("Aloqa yo'q. Natijalar keyinroq yuboriladi.", 'err'); }
          clearTimeout(OB.t);
          OB.t = setTimeout(flush, Math.min(60000, 5000 * ++OB.retry));
          break;
        }
        /* 4xx: hodisa yaroqsiz - navbatdan olib tashlanadi */
      }
      OB.q.shift();
      ls.set(KO, OB.q);
    }
    OB.busy = false;
    if (ok) { OB.warned = false; OB.retry = 0; updStats(); }
    return ok;
  }

  /* ================= 5b. Kuzatuv: sessiya, ekranlar, tugmalar (SPEC 10.4) =================
     Faqat Telegram ichida (initData bor) va server "features" qaytarganda. Har ochilishda yangi sid. Hodisalar: screen (ekran almashdi; s - oldingi
     ekran, d - oldingi ekranda ko'rinib turgan ms), click ([data-act]), end (ilova yashirildi), resume (qaytdi; d -
     yo'q bo'lgan ms). Navbat 10 s da, 20 ta hodisada va yashirilganda (keepalive) yuboriladi, bir so'rovda <= 100 ta.
     Xatolar jim: paket ikki marta yuborilmasa tashlanadi, kutish 10 s dan 5 daqiqagacha ortadi. */
  function newSid() {
    try { if (W.crypto && typeof W.crypto.randomUUID === 'function') return W.crypto.randomUUID().toLowerCase(); } catch (e) { /* zaxira */ }
    const b = new Uint8Array(16);
    try { W.crypto.getRandomValues(b); } catch (e) { for (let i = 0; i < 16; i++) b[i] = Math.floor(Math.random() * 256); }
    b[6] = (b[6] & 15) | 64; b[8] = (b[8] & 63) | 128;
    const h = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
    return h.slice(0, 8) + '-' + h.slice(8, 12) + '-' + h.slice(12, 16) + '-' + h.slice(16, 20) + '-' + h.slice(20);
  }
  /* on: /api/s/me javobida "features" bo'lsa yoqiladi (yangi server; eski serverda /api/s/track yo'q - so'rov yuborilmaydi) */
  const TR = { on: false, sid: PREVIEW ? '' : newSid(), q: [], dev: false, fails: 0, bad: 0, wait: 0, dead: false, cur: null, ref: '', at: 0, acc: 0, hidden: false, hidAt: 0, kick: false };
  /* Ko'rinish (SPEC 10.4): manzara - shu ochilishdagi manzara, mavzu - amalda qo'llangan kun/tun,
     aylan - manzara har ochilganda almashadimi ("uslub" funksiyasi o'chiq bo'lsa ham almashadi) */
  function trDevice() {
    const sc = W.screen || {}, nv = W.navigator || {};
    return {
      platform: String((tg && tg.platform) || 'unknown').slice(0, 20), version: String((tg && tg.version) || '').slice(0, 12),
      w: Math.round(sc.width || W.innerWidth || 0), h: Math.round(sc.height || W.innerHeight || 0),
      dpr: Math.round((W.devicePixelRatio || 1) * 100) / 100, scheme: tg && tg.colorScheme === 'dark' ? 'dark' : 'light',
      ua: String(nv.userAgent || '').slice(0, 300),
      manzara: NQ.v, mavzu: H.getAttribute('data-m') === 'tun' ? 'tun' : 'kun', aylan: !!(NQ.a || NQ.x),
    };
  }
  const trKey = (v) => String(v == null ? '' : v).toLowerCase().replace(/[^a-z0-9_-]+/g, '-').slice(0, 40);
  function trPush(k, n, r, s, d) {
    if (!TR.on || TR.dead) return;
    const e = { t: Date.now(), k, n: trKey(n) || k };
    if (r != null && r !== '') e.r = String(r).slice(0, 40);
    if (s) e.s = String(s).slice(0, 40);
    if (d != null) e.d = clamp(Math.round(d), 0, 864e5);
    TR.q.push(e);
    if (TR.q.length > 400) TR.q.splice(0, TR.q.length - 400);
    if (TR.q.length >= 20) trFlush();
  }
  /* Hozirgi ekran: [kalit, havola]. Ochiq varaq (sheet-*) va kattalashtirish ekran ustida turadi. */
  function trWhere() {
    if (S.phase !== 'ready') return null;
    if (S.ob) return ['ob-' + obStep(), ''];
    const st = topS() || { s: 'bosh' }, r = st.s === 'player' ? st.vid : st.id != null ? st.id : st.n;
    if (S.zoom) return ['sheet-zoom', r];
    const sh = $('#ovl .scrim');
    if (sh) return [sh.getAttribute('data-name') || 'sheet', sh.getAttribute('data-r') || r];
    return [st.s, r];
  }
  const trDur = (now) => TR.acc + (TR.hidden ? 0 : now - TR.at);
  function trSync() {
    TR.kick = false;
    if (!TR.on) return;
    const w = trWhere();
    if (!w) return;
    const n = w[0], r = w[1] == null ? '' : String(w[1]);
    if (n === TR.cur && r === TR.ref) return;
    const now = Date.now(), prev = TR.cur;
    trPush('screen', n, r, prev, prev ? trDur(now) : null);
    TR.cur = n; TR.ref = r; TR.at = now; TR.acc = 0;
  }
  /* Ekran o'zgarishi joriy amal tugagach (mikrotopshiriqda) bir marta yoziladi - oraliq holatlar yozilmaydi */
  function trKick() {
    if (!TR.on || TR.kick) return;
    TR.kick = true;
    Promise.resolve().then(trSync);
  }
  function trClick(e) {
    if (!TR.on) return;
    const b = e.target && e.target.closest ? e.target.closest('[data-act]') : null;
    if (!b || b.disabled) return;
    const a = b.getAttribute('data-act');
    if (a === 'sheet-bg' && e.target !== b) return;
    trSync();
    trPush('click', a, b.getAttribute('data-n') || b.getAttribute('data-v') || b.getAttribute('data-i'), TR.cur);
  }
  function trHide() {
    if (!TR.on || TR.hidden) return;
    trSync();
    const now = Date.now();
    TR.acc = trDur(now); TR.hidden = true; TR.hidAt = now;
    if (TR.cur) trPush('end', TR.cur, TR.ref, TR.cur, TR.acc);
    for (let k = 0; k < 4 && TR.q.length; k++) trFlush(true);
  }
  function trShow() {
    if (!TR.on || !TR.hidden) return;
    const now = Date.now();
    TR.hidden = false; TR.at = now;
    if (TR.cur) trPush('resume', TR.cur, TR.ref, TR.cur, now - TR.hidAt);
  }
  async function trFlush(hide) {
    if (!TR.on || TR.dead || !TR.q.length || !S.me) return;
    if (hide !== true && Date.now() < TR.wait) return;
    const batch = TR.q.splice(0, 100), body = { sid: TR.sid, events: batch };
    if (!TR.dev) body.device = trDevice();
    let st = 0;
    try {
      const r = await fetch('/api/s/track', {
        method: 'POST', keepalive: true, credentials: 'same-origin', cache: 'no-store',
        headers: { 'Content-Type': 'application/json', 'X-Init-Data': INIT }, body: JSON.stringify(body),
      });
      st = r.status;
    } catch (e) { st = 0; }
    if (st >= 200 && st < 300) {
      TR.dev = true; TR.fails = 0; TR.bad = 0; TR.wait = 0;
      if (TR.q.length >= 20) trFlush();
      return;
    }
    /* Server kuzatuvni qabul qilmaydi (eski server, kirish yoki funksiya yopiq) - shu sessiyada to'xtatiladi */
    if (st === 401 || st === 403 || st === 404 || st === 405) { TR.dead = true; TR.q = []; return; }
    if (st === 400 || st === 413) return;
    TR.bad += 1;
    TR.wait = Date.now() + Math.min(3e5, 1e4 * Math.pow(2, TR.bad - 1));
    if (TR.fails < 1) { TR.fails = 1; TR.q = batch.concat(TR.q).slice(-400); } else TR.fails = 0;
  }

  /* ================= 6. Namuna rejimi (Telegramsiz brauzerda) ================= */
  const demo = {
    d: null,
    load() {
      if (!this.d) {
        const v = ls.get(KDEMO, null) || {};
        this.d = { days: v.days || {}, lessons: v.lessons || {}, videos: v.videos || {}, tests: v.tests || {} };
      }
      return this.d;
    },
    save() { ls.set(KDEMO, this.d); },
  };
  function demoStats() {
    const d = demo.load(), t = todayIso(), days = d.days;
    let streak = 0, x = days[t] > 0 ? t : isoAdd(t, -1);
    while (days[x] > 0) { streak += 1; x = isoAdd(x, -1); }
    let best = 0, run = 0, prev = null;
    Object.keys(days).filter((k) => days[k] > 0).sort().forEach((k) => {
      run = prev && isoAdd(prev, 1) === k ? run + 1 : 1; best = Math.max(best, run); prev = k;
    });
    const week = [];
    for (let i = 6; i >= 0; i--) { const k = isoAdd(t, -i); week.push({ day: k, xp: days[k] || 0 }); }
    return { xp: Object.keys(days).reduce((a, k) => a + (days[k] || 0), 0), streak, best_streak: Math.max(best, streak), today_xp: days[t] || 0, goal: 30, week };
  }
  function demoMe() {
    const d = demo.load(), copy = (o) => JSON.parse(JSON.stringify(o));
    return {
      user: { id: 0, first_name: 'Mehmon', last_name: '', username: '', photo_url: null },
      prefs: Object.assign({ uslub: null, rejim: 'auto', arab: 'm', eslatma: true }, ls.get(KP, {}) || {}),
      stats: demoStats(), progress: { lessons: copy(d.lessons), videos: copy(d.videos), tests: copy(d.tests) },
      course: { open: (S.K && S.K.jami_dars) || 36 },
    };
  }
  async function demoEvent(ev) {
    const d = demo.load(), out = {};
    let xp = 0;
    if (ev.type === 'slide' || ev.type === 'lesson_done') {
      const k = String(ev.dars), it = d.lessons[k] || (d.lessons[k] = { seen: [], done_at: null });
      if (ev.type === 'slide') {
        if (it.seen.indexOf(ev.idx) < 0) { it.seen.push(ev.idx); it.seen.sort((a, b) => a - b); xp = 1; }
      } else {
        const need = Math.ceil(0.8 * L(ev.dars).slaydlar);
        if (it.seen.length < need) throw new ApiErr(400, `Darsni tugatish uchun kamida ${need} ta slaydni ko'ring (hozir ${it.seen.length} ta).`);
        if (!it.done_at) { it.done_at = new Date().toISOString(); xp = 20; }
      }
      out.item = { seen: it.seen.slice(), done_at: it.done_at };
    } else if (ev.type === 'video_pos' || ev.type === 'video_done') {
      const it = d.videos[ev.vid] || (d.videos[ev.vid] = { pos: 0, done_at: null });
      if (ev.pos != null) it.pos = ev.pos;
      if (ev.type === 'video_done' && !it.done_at) { it.done_at = new Date().toISOString(); xp = 30; }
      out.item = { pos: it.pos, done_at: it.done_at };
    } else if (ev.type === 'test_done') {
      const t = S.tests[ev.dars], total = t.savollar.length;
      const correct = t.savollar.reduce((a, q, i) => a + (q.ok === ev.answers[i] ? 1 : 0), 0);
      const k = String(ev.dars), it = d.tests[k] || (d.tests[k] = { best: 0, last: 0, total, tries: 0 });
      const old = it.best;
      it.best = Math.max(old, correct); it.last = correct; it.total = total; it.tries += 1;
      xp = 4 * (it.best - old);
      if (correct === total && !it.perfect) { it.perfect = true; xp += 10; }
      Object.assign(out, { correct, total, item: { best: it.best, last: it.last, total, tries: it.tries } });
    }
    if (xp) { const t = todayIso(); d.days[t] = (d.days[t] || 0) + xp; }
    demo.save();
    return Object.assign(out, { xp_added: xp, stats: demoStats() });
  }

  /* ================= 7. Ma'lumot ================= */
  let LM = {};
  const L = (n) => LM[n];
  function indexK() { LM = {}; (S.K.darslar || []).forEach((d) => { LM[d.n] = d; }); }
  const P = () => S.me.progress;
  const lp = (n) => P().lessons[String(n)] || { seen: [], done_at: null };
  const isDone = (n) => !!lp(n).done_at;
  const seenN = (n) => (lp(n).seen || []).length;
  const totalN = () => S.K.jami_dars || (S.K.darslar || []).length || 36;
  const openN = () => clamp(+((S.me && S.me.course && S.me.course.open) || 0), 0, totalN());
  const pctL = (n) => (isDone(n) ? 100 : Math.min(100, Math.round(100 * seenN(n) / Math.max(1, L(n).slaydlar))));
  const doneCount = () => S.K.darslar.filter((d) => isDone(d.n)).length;
  const vp = (id) => P().videos[id] || { pos: 0, done_at: null };
  const tp = (n) => P().tests[String(n)] || null;
  /* Funksiyalar (SPEC 10.3): /api/s/me "features". Kalit yoki obyektning o'zi bo'lmasa - yoqilgan (eski server bilan ham
     ishlaydi). Reyting ball bo'yicha, shuning uchun "ball" o'chsa reyting ham yashiriladi. "uslub" = Ko'rinish tanlash (manzara). */
  const feat = (k) => { const f = S.me && S.me.features; return !f || typeof f !== 'object' || f[k] !== false; };
  const ballOn = () => feat('ball');
  const rateOn = () => !PREVIEW && feat('reyting') && feat('ball');
  const testOf = (d) => (d && d.test && feat('test') ? d.test : null);
  const tabOn = (k) => (k === 'video' ? feat('video') : k === 'reyting' ? rateOn() : TABS.indexOf(k) >= 0);
  /* Duel va taklif (SPEC 11) server bilan ishlaydi: namuna rejimida yo'q. 2-bosqich serveri /api/s/me da "duel_pending"
     qaytaradi; u yo'q bo'lsa (eski server, endpointlar hali yo'q) bu bo'limlar ko'rsatilmaydi. */
  const p2 = () => !PREVIEW && !!S.me && S.me.duel_pending != null;
  const duelOn = () => p2() && feat('duel');
  const taklifOn = () => p2() && feat('taklif');
  const qgOn = () => feat('qollanma');
  const scrOn = (s) => (s === 'video' || s === 'player' ? feat('video') : s === 'mashq' || s === 'natija' ? feat('test') : s === 'reyting' ? rateOn()
    : s === 'duellar' || s === 'duel' || s === 'duel-natija' ? duelOn() : s === 'taklif' ? taklifOn() : s === 'qollanma' ? qgOn() : true);
  /* Tanishuv: salom -> ko'rinish (manzara + rejim) [-> qanday -> ball, qo'llanma yoqilgan bo'lsa] */
  const obSteps = () => ['salom', 'korinish'].concat(qgOn() ? ['qanday'].concat(obLines('ball').length ? ['ball'] : []) : []);
  const obStep = () => obSteps()[S.ob - 1] || 'salom';
  /* Darsning barcha videolari ("videolar"; eski kurs.json da faqat "video"); "video" funksiyasi o'chsa - hech biri */
  const vidsOf = (d) => (!feat('video') ? [] : d && Array.isArray(d.videolar) ? d.videolar.filter((v) => v && v.id) : d && d.video ? [d.video] : []);
  const allVids = () => S.K.darslar.reduce((a, d) => a.concat(vidsOf(d).map((v) => ({ d, v }))), []);
  /* video id -> { d: dars, v: video } */
  const vidOf = (id) => allVids().find((x) => x.v.id === id) || null;
  /* Ketma-ket ochilish: dars ochiq <=> ustoz ochgan (n <= open) VA (n == 1 yoki oldingi dars tugatilgan).
     Ro'yxat serverdan (course.available) keladi va har hodisa javobida yangilanadi. */
  function avail(n) {
    const c = S.me && S.me.course;
    if (c && Array.isArray(c.available)) return c.available.indexOf(n) >= 0;
    return n <= openN() && (n === 1 || isDone(n - 1));
  }
  const lockMsg = (n) => (n > openN() ? 'Ustoz ochganda ochiladi' : `Avval ${n - 1}-darsni tugating`);
  function denyLesson(n) { toast(lockMsg(n)); hap('not', 'error'); }
  const qismOf = (n) => S.K.qismlar.find((q) => q.darslar.indexOf(n) >= 0) || S.K.qismlar[0];
  /* Joriy dars: eng kichik ochiq va tugatilmagan dars (hammasi tugagan bo'lsa - oxirgi ochilgani) */
  function curN() {
    const o = openN();
    for (let n = 1; n <= o; n++) if (L(n) && !isDone(n)) return n;
    const last = +ls.get(KL, 0) || 0;
    return last && last <= o && L(last) ? last : Math.max(1, Math.min(o, totalN()));
  }
  const stOf = (n, c) => (!avail(n) ? 'lock' : isDone(n) ? 'done' : n === c ? 'cur' : 'open');
  function resumeIdx(n) {
    const d = L(n), it = lp(n), N = d.slaydlar;
    if (it.done_at) return 1;
    const seen = new Set(it.seen || []);
    for (let i = 1; i <= N; i++) if (!seen.has(i)) return i;
    return N;
  }
  const userName = () => { const u = (S.me && S.me.user) || {}; return [u.first_name, u.last_name].filter(Boolean).join(' ') || "O'quvchi"; };
  const firstName = () => { const u = (S.me && S.me.user) || {}; return u.first_name || "O'quvchi"; };
  const photo = () => { const u = (S.me && S.me.user) || {}; return u.photo_url || (TGU && TGU.photo_url) || null; };
  function normalizeMe(me) {
    me = me || {};
    me.user = me.user || {};
    me.stats = Object.assign({ xp: 0, streak: 0, best_streak: 0, today_xp: 0, goal: 30, week: [] }, me.stats || {});
    const p = me.progress = me.progress || {};
    p.lessons = p.lessons || {}; p.videos = p.videos || {}; p.tests = p.tests || {};
    me.course = me.course || {};
    if (me.course.open == null) me.course.open = totalN();
    return me;
  }
  function weekOf(s) {
    if (s.week && s.week.length) return s.week.slice(-7);
    const t = todayIso(), w = [];
    for (let i = 6; i >= 0; i--) w.push({ day: isoAdd(t, -i), xp: 0 });
    return w;
  }
  function updStats() {
    if (!S.me || S.ob) return;
    const s = S.me.stats, g = s.goal || 30;
    $$('[data-stat="xp"]').forEach((e) => { e.textContent = num(s.xp); });
    $$('[data-stat="streak"]').forEach((e) => { e.textContent = s.streak || 0; });
    $$('[data-stat="today"]').forEach((e) => { e.textContent = (s.today_xp || 0) + ' / ' + g + ' ball'; });
    $$('[data-goal] .prog i').forEach((e) => { e.style.width = Math.min(100, Math.round(100 * (s.today_xp || 0) / g)) + '%'; });
  }

  /* ================= 8. Router ================= */
  const TABS = ['bosh', 'darslar', 'video', 'reyting', 'profil'];
  const scrMem = {};
  let cur = null;
  const topS = () => S.stack[S.stack.length - 1];
  function leaveCur() {
    if (!cur) return;
    if (cur.def.tab) scrMem[cur.st.s] = W.scrollY;
    if (cur.def.leave) { try { cur.def.leave(cur.st); } catch (e) { /* jim */ } }
    cur = null;
  }
  function go(s, p, how) {
    how = how || 'push';
    closeZoom(true);
    closeSheet(true);
    hideToast();
    leaveCur();
    const st = Object.assign({ s }, p || {});
    if (how === 'tab') S.stack = [st];
    else if (how === 'replace') S.stack[S.stack.length - 1] = st;
    else S.stack.push(st);
    render(how);
  }
  function back() {
    if (S.zoom) { closeZoom(); return; }
    if (sheetOpen()) { closeSheet(); return; }
    if (DK && DK.fs) { dkFs(false); return; }
    if (S.ob > 1) { S.ob -= 1; hap('imp', 'light'); renderOb(true); return; }
    if (S.ob || S.phase !== 'ready') return;
    if (DU && DU.phase === 'play' && topS() && topS().s === 'duel') { duAskQuit(); return; }
    if (S.stack.length > 1) { leaveCur(); S.stack.pop(); render('pop'); hap('imp', 'light'); }
  }
  const fkey = (x) => (x.getAttribute('data-act') || '') + '|' + (x.getAttribute('data-i') || x.getAttribute('data-v') || x.getAttribute('data-n') || '');
  function render(how) {
    if (S.ob) { renderOb(); return; }
    if (S.phase !== 'ready') return;
    /* O'chirilgan bo'limga (havola, eski holat) tushilsa - Bosh sahifa */
    if (!topS() || !scrOn(topS().s)) { S.stack = [{ s: 'bosh' }]; how = 'tab'; }
    const st = topS(), def = SCR[st.s] || SCR.bosh;
    if (how === 'same' && cur && cur.st === st && def.live) return;
    const box = $('#scr'), y = W.scrollY, ae = D.activeElement;
    const kb = !!(ae && ae !== D.body && ae.getAttribute && (box.contains(ae) || $('#nav').contains(ae) || $('#ovl').contains(ae)));
    const fk = kb && ae.hasAttribute('data-act') ? fkey(ae) : '';
    const anim = how === 'same' || how === 'none' || reduced() ? '' : (def.full || how === 'tab') ? 'enter-tab' : how === 'pop' ? 'enter-pop' : 'enter-push';
    box.className = 'scr scr-' + st.s;
    box.innerHTML = def.html(st);
    if (anim) { void box.offsetWidth; box.classList.add(anim); }
    cur = { st, def };
    renderNav(def.tab ? st.s : null);
    backBtn(!def.tab);
    swipes(!def.noSwipe);
    H.classList.toggle('lock', !!def.full);
    paintScenes(box);
    W.scrollTo(0, how === 'same' ? y : how === 'pop' ? (scrMem[st.s] || 0) : 0);
    if (def.mount) def.mount(st, box, how);
    trKick();
    if (!kb) return;
    let t = null;
    if (how === 'same' && fk) t = $$('[data-act]', box).find((x) => fkey(x) === fk && !x.disabled) || null;
    if (!t && how !== 'same') { t = $('h1', box); if (t) t.setAttribute('tabindex', '-1'); }
    if (t) { try { t.focus({ preventScroll: true }); } catch (e) { /* jim */ } }
  }
  const NAVL = [['bosh', 'Bosh'], ['darslar', 'Darslar'], ['video', 'Video'], ['reyting', 'Reyting'], ['profil', 'Profil']];
  const navIc = (k) => (k === 'bosh' ? ic('house') : k === 'darslar' ? ic('book-open') : k === 'video' ? ic('circle-play') : k === 'reyting' ? ic('trophy') : ic('user-round'));
  const navInner = (active) => NAVL.filter((x) => tabOn(x[0])).map(([k, l]) =>
    `<button type="button" class="nb" data-act="tab" data-v="${k}"${k === active ? ' aria-current="page"' : ''}><span class="ni">${navIc(k)}</span><span>${l}</span></button>`).join('');
  function renderNav(active) {
    const n = $('#nav');
    if (!active) { n.hidden = true; n.innerHTML = ''; return; }
    n.hidden = false;
    n.innerHTML = navInner(active);
  }
  let toastT = 0;
  /* Ekran almashganda eski xabar yangi ekrandagi tugmalarni yopib qolmasin */
  function hideToast() { const t = $('#toast'); clearTimeout(toastT); if (t) t.classList.remove('on'); }
  function toast(msg, kind) {
    const t = $('#toast');
    if (!t) return;
    t.innerHTML = (kind === 'ok' ? ic('circle-check') : kind === 'err' ? ic('circle-alert') : ic('info')) + '<span>' + T(msg) + '</span>';
    t.classList.toggle('low', !!$('#nav').hidden);
    t.classList.add('on');
    clearTimeout(toastT);
    toastT = setTimeout(() => t.classList.remove('on'), 2800);
  }
  const sheetOpen = () => !!$('#ovl .scrim');
  /* name - kuzatuvdagi ekran kaliti (sheet-<name>), r - havola (dars raqami) */
  function openSheet(html, label, name, r) {
    closeSheet(true);
    $('#ovl').insertAdjacentHTML('beforeend', `<div class="scrim" data-act="sheet-bg" data-name="sheet-${esc(name || 'oyna')}" data-r="${esc(r == null ? '' : r)}"><div class="sheet" role="dialog" aria-modal="true" aria-label="${esc(label)}">${html}</div></div>`);
    backBtn(true);
    const f = $('#ovl .sheet button');
    if (f) { try { f.focus({ preventScroll: true }); } catch (e) { /* jim */ } }
    trKick();
  }
  function closeSheet(silent) {
    const s = $('#ovl .scrim');
    if (!s) return;
    s.remove();
    if (!silent && cur) backBtn(!cur.def.tab);
    trKick();
  }
  function busy(b, on) {
    if (!b) return;
    const u = $('use', b);
    if (on) {
      b.classList.add('busy'); b.setAttribute('aria-busy', 'true'); b.disabled = true;
      if (u) { b._u = u.getAttribute('href'); u.setAttribute('href', SPR + '#loader-circle'); }
    } else {
      b.classList.remove('busy'); b.removeAttribute('aria-busy'); b.disabled = false;
      if (u && b._u) u.setAttribute('href', b._u);
    }
  }
  function renderSkeleton() {
    const box = $('#scr');
    const sk = (h, w, r) => `<div class="skel" style="height:${h}px${w ? ';width:' + w : ''}${r ? ';border-radius:' + r : ''}"></div>`;
    box.className = 'scr';
    box.innerHTML = `<div class="page" role="status" aria-label="Yuklanmoqda"><div class="ap-top" aria-hidden="true">${sk(26, '48%')}${sk(44, '44px', '50%')}</div>${sk(232, '', '20px')}${sk(66, '', '16px')}${sk(70, '', '16px')}<div class="hc2">${sk(112, '', '16px')}${sk(112, '', '16px')}</div></div>`;
    renderNav(null);
  }
  const emptyHtml = (icon, h, p, wb) => `<div class="empty${wb ? ' wb' : ''}">${dia(ic(icon), 'big lk')}<h2>${h}</h2>${p ? `<p>${p}</p>` : ''}${wb ? band() : ''}</div>`;
  const loadHtml = (h, p) => `<div class="empty" role="status">${dia(ic('loader-circle', 'spin'), 'big')}<h2>${h}</h2>${p ? `<p>${p}</p>` : ''}</div>`;
  function errBlock(e, act, wb) {
    const st = e && e.st;
    const title = st === 401 ? 'Kirish tasdiqlanmadi' : !st ? "Aloqa yo'q" : 'Xatolik yuz berdi';
    return `<div class="err${wb ? ' wb' : ''}" role="alert">${dia(!st ? ic('wifi-off') : ic('triangle-alert'), 'big lk')}<h2>${title}</h2><p>${T((e && e.message) || NET_MSG)}</p><button type="button" class="btn auto" data-act="${act}">${ic('refresh-cw')}Qayta urinish</button>${wb ? band() : ''}</div>`;
  }
  function renderError() {
    const box = $('#scr');
    box.className = 'scr';
    box.innerHTML = `<div class="full-err">${errBlock(S.err, 'retry', true)}</div>`;
    cur = null;
    renderNav(null); backBtn(false); swipes(true); H.classList.remove('lock');
    paintScenes(box);
  }

  /* ---- Tanishuv: salom -> ko'rinish -> qanday -> ball ---- */
  const MODES = [['light', 'Kunduzgi', "Yorug' qum ranglari"], ['dark', 'Tungi', "Oy nuri: yumshoq, ko'zni charchatmaydi"], ['auto', 'Avto', '06:00–18:59 kunduzgi, qolgani tungi']];
  const modeIc = (k) => (k === 'light' ? ic('sun') : k === 'dark' ? ic('moon') : ic('clock'));
  const dots = (k) => `<div class="dots" aria-hidden="true">${obSteps().map((x, i) => `<i${i + 1 === k ? ' class="on"' : ''}></i>`).join('')}</div>`;
  /* Pastki qism: nuqtalar + "Davom etish" (oxirgi qadamda "Boshlash") [+ "O'tkazib yuborish"] */
  const obFoot = (k, skip) => `<div class="ob-foot">${dots(k)}${k < obSteps().length ? `<button type="button" class="btn" data-act="ob-next">Davom etish${ic('arrow-right')}</button>`
    : `<button type="button" class="btn" data-act="ob-done">Boshlash${ic('arrow-right')}</button>`}${skip ? `<button type="button" class="ob-skip" data-act="ob-skip">O'tkazib yuborish</button>` : ''}</div>`;
  /* Manzara tanlovi (Profil va tanishuv): 6 ta kichik manzara; data-i - manzara kaliti */
  const thumbs = (big) => `<div class="mz${big ? ' big' : ''}" role="group" aria-label="Manzara">${V.map((v) => `<button type="button" data-act="set-manzara" data-i="${v}" aria-pressed="${v === NQ.v}"><span class="th" data-v="${v}">${scn('thumb', v)}</span>${VN[v]}</button>`).join('')}</div>`;
  const aylSw = () => `<button type="button" class="sw" role="switch" aria-checked="${NQ.a}" data-act="set-aylanish" data-v="${NQ.a ? 'off' : 'on'}" aria-label="Har ochilganda almashsin"><span></span></button>`;
  const mzRow = () => `<div class="set-r">${dia(ic('image'))}<span class="st"><b>Manzara</b><small>${NQ.a ? 'Har ochilganda almashsin' : 'Tanlangan: ' + VN[NQ.v] + '. Almashishi uchun yoqing'}</small></span>${aylSw()}</div>`;
  /* Qo'llanma qadamlari (B1 "qanday", B2 "ball"): katta ikon + atrofida qatorlar ikonlari, sarlavha, raqamlangan qatorlar */
  function obX(k, key) {
    const x = OBX[key], lines = obLines(key);
    return `<section class="ob ob-x"><div class="ob-main">
      <div class="ob-ill" aria-hidden="true"><span class="dia ob-bm">${ic(x[1])}</span>${lines.map((l, j) => `<span class="dia ob-sat s${j + 1}">${ic(l[0])}</span>`).join('')}</div>
      <h1 class="ob-h">${T(x[0])}</h1>
      <ol class="card tk-steps ob-ls">${lines.map((l, j) => `<li><span aria-hidden="true">${j + 1}</span>${T(l[1])}</li>`).join('')}</ol></div>
      ${obFoot(k, true)}</section>`;
  }
  function ob1(k) {
    const K = S.K, nv = allVids().length, vOn = feat('video'), tOn = feat('test'), bOn = ballOn();
    const what = ['darslar'].concat(vOn ? ['video'] : [], tOn ? ['mashqlar'] : []);
    const wt = what.length < 2 ? 'barcha darslar' : what.slice(0, -1).join(', ') + ' va ' + what[what.length - 1];
    const ex = tOn && bOn ? 'Mashqlar, ball va kunlik seriya' : tOn ? 'Mashqlar' : bOn ? 'Ball va kunlik seriya' : '';
    return `<section class="ob ob-salom"><div class="ob-main">
      <span class="brand ob-brand">${sig()}<span>${T(K.brend || 'Muhammadamin')}</span></span>
      <div class="hero-c ob-hero">${scn('full')}</div>
      <div class="kick">Salom, ${T(firstName())}!</div>
      <h1 class="ob-h">Xush kelibsiz!</h1>
      <p class="ob-p">${T(K.brend || 'Muhammadamin')} fonetika kursi endi Telegram ichida: ${wt} bir joyda.</p>
      <ul class="card ob-feat">
        <li>${dia(ic('presentation'))}<span>${totalN()} dars · ${num(K.jami_slayd)} slayd</span></li>
        ${vOn ? `<li>${dia(ic('circle-play'))}<span>Video darslar${nv ? ' · ' + nv + ' ta' : ''}</span></li>` : ''}
        ${ex ? `<li>${dia(ic('list-checks'))}<span>${ex}</span></li>` : ''}
      </ul></div>
      ${obFoot(k)}</section>`;
  }
  function obKr(k) {
    const r = rejimNow();
    return `<section class="ob ob-kr"><div class="ob-main">
      <h1 class="ob-h">Ilova ko'rinishini tanlang</h1>
      <p class="ob-p">Keyinroq Profil bo'limida o'zgartirish mumkin.</p>
      ${feat('uslub') ? `<div class="card">${mzRow()}${thumbs(true)}</div>` : ''}
      <div class="ob-modes" role="group" aria-label="Rejim">${MODES.map(([m, l, s]) => `<button type="button" class="mode" data-act="set-rejim" data-v="${m}" aria-pressed="${r === m}">${dia(modeIc(m))}<span class="mt">${l}<small>${s}</small></span><span class="mk">${ic('check')}</span></button>`).join('')}</div></div>
      ${obFoot(k)}</section>`;
  }
  let obShown = 0;
  function renderOb(nav) {
    const box = $('#scr'), same = obShown === S.ob && !nav, step = obStep();
    box.className = 'scr scr-ob';
    box.innerHTML = step === 'salom' ? ob1(S.ob) : step === 'korinish' ? obKr(S.ob) : obX(S.ob, step);
    if (!same && !reduced()) { void box.offsetWidth; box.classList.add(nav ? 'enter-pop' : 'enter-push'); }
    obShown = S.ob;
    cur = null;
    renderNav(null); backBtn(S.ob > 1); swipes(true); H.classList.remove('lock');
    if (!same) W.scrollTo(0, 0);
    paintScenes(box);
    trKick();
  }
  function startOb() {
    S.ob = 1;
    applyTheme();
    renderOb();
  }
  /* Tanishuv o'tildi: qurilmada va Telegram bulutida (boshqa qurilmada qayta so'ralmaydi). Serverga uslub yuborilmaydi. */
  function obMark() { ls.set(KOB, true); cloud.set('nq_ob', '1'); }

  /* ================= 9. Ekranlar ================= */
  const demoBar = () => (PREVIEW ? `<div class="demo" role="note">${ic('info')}<span><b>Namuna rejimi</b> — natijalar faqat shu qurilmada saqlanadi.</span></div>` : '');
  function avatarInner() {
    const ph = photo(), i2 = esc(ini(userName()));
    return ph ? `<img src="${esc(ph)}" alt="" referrerpolicy="no-referrer" data-ini="${i2}">` : i2;
  }
  const prog = (pct, label, max, now) => `<span class="prog"${label ? ` role="progressbar" aria-label="${label}" aria-valuemin="0" aria-valuemax="${max}" aria-valuenow="${now}"` : ''}><i style="width:${clamp(pct, 0, 100)}%"></i></span>`;
  /* Sahnali sarlavha kartasi (Duellar, Taklif, Qo'llanma, natijalar) */
  function heroCard(icon, kick, title, text, cls, h) {
    const t = h || 'h2';
    return `<section class="hero-c du-hero${cls ? ' ' + cls : ''}">${scn('card')}<div class="hx">${dia(icon, 'cta big')}${kick ? `<div class="kick">${kick}</div>` : ''}<${t}>${title}</${t}>${text ? `<p class="du-lead">${text}</p>` : ''}</div></section>`;
  }

  /* ---- Bosh ---- */
  function goalHtml(s) {
    const g = s.goal || 30, x = s.today_xp || 0, ok = x >= g, p = Math.min(100, Math.round(100 * x / g));
    return `<section class="card ap-goal${ok ? ' ok' : ''}" data-goal aria-label="Kunlik maqsad">${dia(ok ? ic('circle-check') : ic('zap'), ok ? 'ok' : '')}<div class="gb"><div class="gh"><b>Kunlik maqsad</b><span data-stat="today">${x} / ${g} ball</span></div>${prog(p, 'Kunlik maqsad', g, Math.min(x, g))}</div></section>`;
  }
  function boshHtml() {
    const c = curN(), d = L(c), q = qismOf(c), s = S.me.stats, b = ballOn();
    const seen = seenN(c), N = d.slaydlar, dn = isDone(c), ok = avail(c), shown = dn ? N : Math.min(seen, N);
    const cta = !ok ? 'Yopiq' : dn ? 'Takrorlash' : seen ? 'Davom etish' : 'Boshlash';
    const vs = vidsOf(d), t = testOf(d) ? S.tests[c] : null, tt = tp(c);
    const plan = vs.map((v, k) => { const vd = vp(v.id).done_at; return `<button type="button" class="ap-row" data-act="video" data-v="${esc(v.id)}">${dia(ic(vd ? 'circle-check' : 'circle-play'), vd ? 'ok' : '')}<span class="rt"><b>${vs.length > 1 ? `Video ${k + 1}` : 'Video dars'}</b><small>${T(v.nomi)} · ${mins(v.davomiylik)} daq</small></span>${ic('chevron-right')}</button>`; }).join('')
      + (testOf(d) ? `<button type="button" class="ap-row" data-act="quiz" data-n="${c}">${dia(ic(tt && tt.total && tt.best >= tt.total ? 'circle-check' : 'list-checks'), tt && tt.total && tt.best >= tt.total ? 'ok' : '')}<span class="rt"><b>Mashq</b><small>${t ? t.savollar.length + ' savol' : 'Test'}${tt && tt.tries ? ` · eng yaxshi natija ${tt.best}/${tt.total || (t ? t.savollar.length : 5)}` : ''}</small></span>${ic('chevron-right')}</button>` : '');
    const sts = (b ? [['profil', 'flame', `<b data-stat="streak">${s.streak || 0}</b>`, 'kun seriya'], [rateOn() ? 'reyting' : 'profil', 'gem', `<b data-stat="xp">${num(s.xp)}</b>`, 'ball']] : [])
      .concat([['darslar', 'book-check', `<b>${doneCount()}/${totalN()}</b>`, 'darslar']]);
    return `<div class="page bo">
      <header class="ap-top"><span class="brand">${sig()}<span>${T(S.K.brend || 'Muhammadamin')}</span></span><button type="button" class="ava" data-act="tab" data-v="profil" aria-label="Profil">${avatarInner()}</button></header>
      ${demoBar()}<h1 class="sr">Bosh sahifa</h1>
      <section class="hero-c ap-hero" aria-label="Joriy dars">${scn('card')}<div class="hx">
        <div class="hi">${greet()}, ${T(firstName())}</div>
        <div class="kick">${q.n}-qism · ${c}-dars</div>
        <h2>${T(d.nomi)}</h2>
        <div class="pr">${prog(Math.round(100 * shown / Math.max(1, N)), "Ko'rilgan slaydlar", N, shown)}<span>${shown} / ${N}</span></div>
        <button type="button" class="btn auto" data-act="lesson" data-n="${c}">${ic(!ok ? 'lock' : dn ? 'rotate-ccw' : 'play')}${cta}</button>
        ${ok ? '' : `<p class="note">${lockMsg(c)}</p>`}</div></section>
      ${plan ? `<section class="card ap-plan" aria-label="Dars rejasi">${plan}</section>` : ''}
      <div class="card ap-stats${sts.length < 2 ? ' one' : ''}" style="--n:${sts.length}">${sts.map(([v, i, val, l]) => `<button type="button" data-act="tab" data-v="${v}"><span class="si">${ic(i)}</span>${val}<small>${l}</small></button>`).join('')}</div>
      ${b ? goalHtml(s) : ''}${homeCards()}${qgLink()}</div>`;
  }

  /* ---- Darslar: joriy qism sahnali banner bilan ochiq, qolganlari qatorda (bosilsa ochiladi) ---- */
  function lsRow(n, c) {
    const d = L(n), st = stOf(n, c), nv = vidsOf(d).length, seen = seenN(n);
    const meta = st === 'lock' ? `<span>${ic('lock')}${lockMsg(n)}</span>`
      : `<span>${d.slaydlar} slayd</span>${nv ? `<span>${ic('circle-play')}${nv > 1 ? nv + ' video' : 'video'}</span>` : ''}${testOf(d) ? `<span>${ic('list-checks')}mashq</span>` : ''}`;
    const fx = S.pathFx, jd = fx && n === fx.from && st === 'done' ? ' jd' : '', jc = fx && st === 'cur' && n !== fx.from ? ' jc' : '';
    const nd = st === 'done' ? ic('check') : st === 'cur' ? ic('play') : st === 'lock' ? ic('lock') : `<b>${n}</b>`;
    return `<button type="button" class="ls ${st}${jd}${jc}" data-act="lesson" data-n="${n}"${st === 'lock' ? ' aria-disabled="true"' : ''}><span class="nd" aria-hidden="true">${nd}</span><span class="tx"><small>${n}-dars${st === 'done' ? ' · tugatilgan' : st === 'cur' ? ' · joriy' : ''}</small><b>${T(d.nomi)}</b><span class="m">${meta}</span></span>${st === 'cur' ? `<span class="go" aria-hidden="true">${isDone(n) ? 'Takrorlash' : seen ? 'Davom' : 'Boshlash'}</span>` : ''}</button>`;
  }
  function darslarHtml() {
    const c = curN(), cq = qismOf(c);
    if (!S.qOpen) S.qOpen = new Set();
    let h = `<div class="page dl"><header class="ap-head"><h1 class="h1">Darslar</h1><span class="chip${S.pathFx ? ' bump' : ''}">${ic('book-check')}${doneCount()} / ${totalN()}</span></header><p class="ap-sub">${T(S.K.nomi)} · ${totalN()} dars · ${S.K.qismlar.length} qism</p>${demoBar()}`;
    S.K.qismlar.forEach((q) => {
      const list = q.darslar.filter((n) => L(n)), dn = list.filter(isDone).length, isCur = q.n === cq.n, open = isCur || S.qOpen.has(q.n);
      const all = list.length > 0 && dn === list.length, lk = !all && list.every((n) => !avail(n)), pct = list.length ? Math.round(100 * dn / list.length) : 0;
      if (isCur) h += `<section class="hero-c qism" aria-label="${q.n}-qism">${scn('card')}<div class="hx"><div class="kick">${q.n}-qism · ${list.length} dars</div><h2>${T(q.nomi)}</h2><div class="pr">${prog(pct)}<span>${dn} / ${list.length}${sr(' tugatilgan')}</span></div></div></section>`;
      else h += `<button type="button" class="card qrow${all ? ' ok' : lk ? ' lk' : ''}" data-act="qism" data-n="${q.n}" aria-expanded="${open}" aria-controls="qp${q.n}">${dia(ic(all ? 'circle-check' : lk ? 'lock' : 'book-open'), all ? 'ok' : lk ? 'lk' : '')}<span class="rt"><small>${q.n}-qism · ${list.length} dars</small><b>${T(q.nomi)}</b></span><span class="cnt">${dn} / ${list.length}${sr(' tugatilgan')}</span>${ic('chevron-down', 'qch')}</button>`;
      if (open) h += `<div class="path" id="qp${q.n}">${list.map((n) => lsRow(n, c)).join('')}</div>`;
    });
    return h + '</div>';
  }
  function mountDarslar(st, box, how) {
    if (S.pathFx) S.pathFx = null;
    if (how === 'pop' || how === 'same') return;
    const el = $('.ls.cur', box);
    if (!el) return;
    const y = el.getBoundingClientRect().top + W.scrollY - W.innerHeight * 0.38;
    if (y > 80) W.scrollTo(0, y);
  }

  /* ---- Video ro'yxati ---- */
  function vCard(x) {
    const d = x.d, v = x.v, p = vp(v.id), lock = !avail(d.n);
    const pct = p.done_at ? 100 : Math.min(100, Math.round(100 * (p.pos || 0) / Math.max(1, v.davomiylik)));
    const badge = lock ? `<span class="badge">${ic('lock')}${d.n > openN() ? 'Yopiq' : `Avval ${d.n - 1}-dars`}</span>`
      : p.done_at ? `<span class="badge ok">${ic('circle-check')}Ko'rildi</span>`
        : pct > 0 ? `<span class="badge go">${ic('clock')}${pct}% ko'rildi</span>`
          : `<span class="badge new">${ic('circle-dot')}Yangi</span>`;
    return `<button type="button" class="card vcard${lock ? ' lock' : ''}" data-act="video" data-v="${esc(v.id)}"${lock ? ' aria-disabled="true"' : ''}><span class="vc-po"><img src="${esc(vq(v.poster))}" alt="" loading="lazy" decoding="async">${lock ? '' : `<span class="vc-play">${ic('play')}</span>`}<span class="vc-dur">${mins(v.davomiylik)} daq</span>${pct > 0 ? `<span class="vc-bar"><i style="width:${pct}%"></i></span>` : ''}</span><span class="vc-b"><span><b>${d.n}-dars · ${T(v.nomi)}</b><small>${T(d.nomi)}</small></span>${badge}</span></button>`;
  }
  function videoHtml() {
    const list = allVids(), sub = list.length ? list.length + ' ta video dars' : "Hozircha video yo'q";
    return `<div class="page vd"><header class="ap-head"><h1 class="h1">Video darslar</h1></header><p class="ap-sub">${sub}</p>${demoBar()}`
      + (list.length ? `<div class="vlist">${list.map(vCard).join('')}</div>` : emptyHtml('film', "Hozircha video darslar yo'q", "Ustoz video qo'shganda shu yerda paydo bo'ladi.", true)) + '</div>';
  }

  /* ---- Dars: slayd ko'rgich ---- */
  let VW = null;
  /* Rasm manzillariga kurs versiyasi qo'shiladi: kontent qayta qurilganda 7 kunlik kesh chetlab o'tiladi */
  const vq = (u) => { const v = S.K && S.K.versiya; return v && u && u.indexOf('?') < 0 ? u + '?v=' + encodeURIComponent(v) : u; };
  const slideUrl = (d, i) => vq(d.rasm + pad3(i) + '.webp');
  /* Rasm ko'rgich sahifalari. Oddiy rejim (taqdimotsiz dars, masalan 18-dars): 1..slaydlar rasmlari (ball va 80% qoidasi
     shular bo'yicha), keyin kitob betlari (bo'lsa). Kitob rejimi (book): faqat kitob_betlari - ball berilmaydi.
     p = tik (A4) sahifa; bet = kitob beti raqami. */
  const kitobOf = (d) => (Array.isArray(d.kitob_betlari) ? d.kitob_betlari.filter((u) => typeof u === 'string' && u) : []);
  function pagesOf(d, book) {
    const N = book ? 0 : d.slaydlar, all = d.nisbat === 'a4', out = [];
    for (let i = 1; i <= N; i++) out.push({ i, url: slideUrl(d, i), p: all, book: false, bet: 0 });
    const b0 = parseInt(String(d.kitob || ''), 10) || 0;
    kitobOf(d).forEach((u, k) => out.push({ i: N + k + 1, url: vq(u), p: true, book: true, bet: b0 ? b0 + k : 0 }));
    return out;
  }
  const notFound = () => `${topbar('Topilmadi', '')}${emptyHtml('circle-help', 'Material topilmadi', "Bu bo'lim hozircha mavjud emas.", true)}`;
  function topbar(title, kick) {
    return `<header class="tb"><button type="button" class="tb-back" data-act="back" aria-label="Orqaga">${ic('arrow-left')}</button><div class="tb-t">${kick ? `<div class="tb-k">${kick}</div>` : ''}<h1 class="tb-h">${title}</h1></div></header>`;
  }
  function viewerHtml(st) {
    const d = L(st.n), book = st.s === 'kitob';
    if (!d || (book && !kitobOf(d).length)) return notFound();
    const N = book ? 0 : d.slaydlar, a4 = d.nisbat === 'a4', seen = new Set(lp(st.n).seen || []), pages = pagesOf(d, book);
    let sl = '', th = '';
    pages.forEach((pg) => {
      const i = pg.i, u = esc(pg.url), nm = pg.book ? (pg.bet ? `Kitob, ${pg.bet}-bet` : 'Kitob sahifasi') : `${i}-slayd`;
      sl += `<figure class="vw-sl${pg.p ? ' p' : ''}" data-i="${i}"><div class="fr">${pg.book ? `<span class="vw-bk">${ic('book-open')}${nm}</span>` : ''}<img alt="${nm}" decoding="async" loading="lazy" data-src="${u}" width="${pg.p ? 1000 : 1280}" height="${pg.p ? 1414 : 720}"></div></figure>`;
      th += `<button type="button" class="vw-th${pg.p ? ' p' : ''}${pg.book ? ' bk' : ''}${!pg.book && seen.has(i) ? ' seen' : ''}" data-act="vw-go" data-i="${i}" aria-label="${nm}"><img alt="" loading="lazy" decoding="async" src="${u}"><span class="tn">${pg.book ? (pg.bet || ic('book-open')) : i}</span><span class="ts">${ic('check')}</span></button>`;
    });
    return `<div class="vw${a4 || book ? ' a4' : ''}${book ? ' bk' : ''}">
      <header class="tb"><button type="button" class="tb-back" data-act="back" aria-label="Orqaga">${ic('arrow-left')}</button>
        <div class="tb-t"><div class="tb-k">${st.n}-dars${book ? ' · kitob betlari' : ''}</div><h1 class="tb-h">${T(d.nomi)}</h1></div>
        <span class="vw-cnt" aria-live="polite" aria-atomic="true">${cntText(pages[0], N)}</span></header>
      <div class="vw-bar" aria-hidden="true"><span></span></div>
      <div class="vw-stage"><div class="vw-track" tabindex="0" role="region" aria-roledescription="karusel" aria-label="${book ? 'Kitob betlari' : 'Slaydlar'}">${sl}</div></div>
      <div class="vw-thumbs" role="group" aria-label="${book ? "Kitob betlari ro'yxati" : "Slaydlar ro'yxati"}">${th}</div>
      <div class="vw-tools">${book ? '' : vidPill(d)}<button type="button" class="pill" data-act="vw-zoom">${ic('zoom-in')}<span>Kattalashtirish</span></button></div>
      <div class="vw-nav"><button type="button" class="btn sec vw-prev" data-act="vw-prev" aria-label="${book ? 'Oldingi bet' : 'Oldingi slayd'}">${ic('chevron-left')}<span class="lbl">Oldingi</span></button><button type="button" class="btn vw-next" data-act="vw-next"><span class="lbl">Keyingi</span>${ic('chevron-right')}</button></div></div>`;
  }
  const cntText = (pg, N) => (!pg ? '0 / 0' : pg.book ? (pg.bet ? pg.bet + '-bet' : 'Kitob') : pg.i + ' / ' + N);
  function mountViewer(st, box) {
    const d = L(st.n);
    if (!d) return;
    ls.set(KL, st.n);
    if (testOf(d) && !S.tests[st.n]) loadTest(st.n);
    const book = st.s === 'kitob', root = $('.vw', box);
    if (!root) return;
    const track = $('.vw-track', root), pages = pagesOf(d, book);
    VW = { n: st.n, N: book ? 0 : d.slaydlar, T: Math.max(1, pages.length), pages, i: 0, target: 0, root, track, t: 0, hintT: 0, book, st };
    const start = clamp(st.i || (book ? 1 : resumeIdx(st.n)), 1, VW.T);
    requestAnimationFrame(() => {
      if (!VW || VW.root !== root) return;
      track.scrollLeft = (start - 1) * track.clientWidth;
      settle(true);
    });
    track.addEventListener('scroll', onVwScroll, { passive: true });
    if ('onscrollend' in W) track.addEventListener('scrollend', () => settle());
    track.addEventListener('click', onVwTap);
    root.addEventListener('error', onImgErr, true);
    W.addEventListener('resize', onVwResize);
    if (!book && d.nisbat !== 'a4' && !ls.get(KHINT, false)) {
      ls.set(KHINT, true);
      $('.vw-stage', root).insertAdjacentHTML('beforeend', `<div class="vw-hint" role="note">${ic('smartphone')}<span>Telefonni yotqizsangiz slaydlar kattaroq ko'rinadi</span><button type="button" data-act="hint-ok">Tushunarli</button></div>`);
      VW.hintT = setTimeout(hideHint, 9000);
    }
  }
  function onVwScroll() { if (!VW) return; clearTimeout(VW.t); VW.t = setTimeout(settle, 120); }
  function settle(force) {
    if (!VW) return;
    const w = VW.track.clientWidth || 1, i = clamp(Math.round(VW.track.scrollLeft / w) + 1, 1, VW.T);
    VW.target = 0;
    if (i === VW.i && !force) return;
    if (VW.i && i !== VW.i) hideHint();
    VW.i = i;
    if (VW.book) VW.st.i = i;
    vwUI();
    preload(i);
    if (i <= VW.N) markSeen(VW.n, i);
  }
  function preload(i) {
    for (let k = i - 1; k <= i + 1; k++) {
      const img = $(`.vw-sl[data-i="${k}"] img`, VW.root);
      if (img && !img.getAttribute('src')) { img.loading = 'eager'; img.src = img.getAttribute('data-src'); }
    }
  }
  function vwUI() {
    const r = VW.root, i = VW.i, N = VW.T;
    $('.vw-cnt', r).textContent = cntText(VW.pages[i - 1], VW.N);
    $('.vw-bar span', r).style.width = (100 * i / N).toFixed(2) + '%';
    let th = null;
    $$('.vw-th', r).forEach((b) => {
      if (+b.getAttribute('data-i') === i) { b.setAttribute('aria-current', 'true'); th = b; } else b.removeAttribute('aria-current');
    });
    if (th) thumbTo(th);
    const prev = $('.vw-prev', r), next = $('.vw-next', r), last = i >= N, fin = VW.book ? 'back' : 'vw-finish';
    prev.disabled = i <= 1;
    if (last !== (next.getAttribute('data-act') === fin)) {
      next.setAttribute('data-act', last ? fin : 'vw-next');
      if (VW.book) {
        next.innerHTML = last ? `<span class="lbl">Darsga qaytish</span>${ic('presentation')}` : `<span class="lbl">Keyingi</span>${ic('chevron-right')}`;
        next.setAttribute('aria-label', last ? 'Darsga qaytish' : 'Keyingi bet');
      } else {
        next.innerHTML = last ? `<span class="lbl">Darsni tugatish</span>${ic('flag')}` : `<span class="lbl">Keyingi</span>${ic('chevron-right')}`;
        next.setAttribute('aria-label', last ? 'Darsni tugatish' : 'Keyingi slayd');
      }
    }
  }
  function thumbTo(th) {
    const s = th.parentNode, left = Math.max(0, th.offsetLeft - (s.clientWidth - th.offsetWidth) / 2);
    try { s.scrollTo({ left, behavior: reduced() ? 'auto' : 'smooth' }); } catch (e) { s.scrollLeft = left; }
  }
  function vwGo(i) {
    if (!VW) return;
    i = clamp(i, 1, VW.T);
    VW.target = i;
    hideHint();
    const left = (i - 1) * VW.track.clientWidth;
    const dist = Math.abs(VW.track.scrollLeft - left);
    if (dist < 2) { settle(); return; }
    /* Uzoq sakrash (eskiz orqali) - darhol, oraliq slaydlar ko'rilgan deb hisoblanmaydi */
    const far = dist > 1.5 * VW.track.clientWidth;
    try { VW.track.scrollTo({ left, behavior: reduced() || far ? 'auto' : 'smooth' }); } catch (e) { VW.track.scrollLeft = left; }
    if (far) settle();
  }
  const vwStep = (k) => { if (VW) vwGo((VW.target || VW.i) + k); };
  function onVwTap(e) {
    if (!VW) return;
    const bad = e.target.closest && e.target.closest('.fr.bad');
    if (bad) { retryImg(bad); return; }
    const r = VW.track.getBoundingClientRect(), x = e.clientX - r.left;
    if (x < r.width / 3) vwStep(-1); else if (x > r.width * 2 / 3) vwStep(1);
  }
  function onImgErr(e) {
    const img = e.target;
    if (!img || img.tagName !== 'IMG') return;
    if (img.closest('.vw-th')) { img.classList.add('bad'); return; }
    const fr = img.closest('.fr');
    if (fr) { fr.classList.add('bad'); fr.setAttribute('data-msg', 'Slayd yuklanmadi. Qayta urinish uchun bosing'); }
  }
  function retryImg(fr) {
    const img = $('img', fr);
    if (!img) return;
    fr.classList.remove('bad');
    img.src = img.getAttribute('data-src') + '?r=' + Date.now();
  }
  function onVwResize() {
    if (!VW) return;
    requestAnimationFrame(() => { if (VW) VW.track.scrollLeft = (VW.i - 1) * VW.track.clientWidth; });
    if (S.zoom) sizeZoom();
  }
  function hideHint() {
    if (!VW) return;
    clearTimeout(VW.hintT);
    const h = $('.vw-hint', VW.root);
    if (h) h.remove();
  }
  function leaveViewer() {
    if (VW) { clearTimeout(VW.t); clearTimeout(VW.hintT); }
    W.removeEventListener('resize', onVwResize);
    VW = null;
    closeZoom(true);
    flush();
  }
  function markSeen(n, i) {
    const pr = P(), k = String(n), it = pr.lessons[k] || (pr.lessons[k] = { seen: [], done_at: null });
    if (!it.seen) it.seen = [];
    if (it.seen.indexOf(i) >= 0) return;
    it.seen.push(i);
    it.seen.sort((a, b) => a - b);
    const th = VW && $(`.vw-th[data-i="${i}"]`, VW.root);
    if (th) th.classList.add('seen');
    enqueue({ type: 'slide', dars: n, idx: i });
  }
  function vwFinish(btn) { if (VW && !VW.book) finishLesson(VW.n, btn); }
  /* Darsni tugatish (rasm ko'rgich ham, jonli taqdimot ham): 80% qoidasi, navbatdagi slayd hodisalari, lesson_done */
  let finBusy = false;
  async function finishLesson(n, btn) {
    const d = L(n);
    if (!d || finBusy) return;
    const need = Math.ceil(0.8 * d.slaydlar), seen = seenN(n);
    if (seen < need) {
      toast(`Darsni tugatish uchun kamida ${need} ta slaydni ko'ring (hozir ${seen} ta).`, 'err');
      hap('not', 'error');
      return;
    }
    finBusy = true;
    busy(btn, true);
    try {
      await flush();
      if (OB.q.some((x) => x.type === 'slide' && x.dars === n)) throw new ApiErr(0, NET_MSG);
      const ev = { type: 'lesson_done', dars: n }, r = await sendEv(ev);
      mergeEv(ev, r);
      S.pathFx = { from: n, t: Date.now() };
      hap('not', 'success');
      if (DK && DK.fs) dkFs(false);
      showDone(n, r.xp_added || 0, +r.taklif_bonus || 0, S.skFx || null);
      S.skFx = null;
    } catch (e) {
      toast(e.message || NET_MSG, 'err');
      hap('not', 'error');
    }
    finBusy = false;
    busy(btn, false);
  }

  /* ---- Dars: jonli HTML taqdimot (iframe) ----
     iframe: taqdimot.url?from=F&to=T&start=K. Taqdimot o'zi bosish (chap 18% - orqaga) va surishni boshqaradi.
     Ota oyna -> taqdimot: {noon:'next'|'prev'|'ping'} yoki {noon:'goto', n}. Taqdimot -> ota oyna:
     {noon:'slide', n, total, step, steps} har o'zgarishda, {noon:'end'} oxirgi slayddan o'tishga urinilganda. */
  /* Dars ekranidagi video tugmasi: bitta video - to'g'ridan-to'g'ri pleyer, bir nechta - ro'yxat oynasi */
  function vidPill(d) {
    const vs = vidsOf(d);
    if (!vs.length) return '';
    if (vs.length === 1) return `<button type="button" class="pill" data-act="video" data-v="${esc(vs[0].id)}">${ic('circle-play')}<span>Video</span></button>`;
    return `<button type="button" class="pill" data-act="vids" data-n="${d.n}" aria-label="Videolar: ${vs.length} ta">${ic('circle-play')}<span>Videolar · ${vs.length}</span></button>`;
  }
  function vidItems(d, how) {
    return vidsOf(d).map((v) => { const p = vp(v.id); return `<button type="button" class="nx-i" data-act="video" data-v="${esc(v.id)}"${how ? ` data-how="${how}"` : ''}>${dia(p.done_at ? ic('circle-check') : ic('circle-play'), p.done_at ? 'ok' : '')}<span><b>${T(v.nomi)}</b><small>${mins(v.davomiylik)} daq${p.done_at ? " · ko'rildi" : ''}</small></span>${ic('chevron-right')}</button>`; }).join('');
  }
  function showVids(n) {
    const d = L(n);
    if (!d || !vidsOf(d).length) return;
    openSheet(`<div class="ld-card vids-card"><h2>${n}-dars videolari</h2><div class="nx">${vidItems(d)}</div><button type="button" class="btn sec" data-act="sheet-close">Yopish</button></div>`, `${n}-dars videolari`, 'videolar', n);
  }

  let DK = null;
  const deckSrc = (d, k) => { const t = d.taqdimot; return t.url + '?from=' + t.from + '&to=' + t.to + '&start=' + k; };
  function deckHtml(st) {
    const d = L(st.n);
    if (!d) return notFound();
    const N = d.slaydlar, kb = kitobOf(d).length, fsI = ic('maximize'), cnt = `<span data-dk-cnt>1 / ${N}</span>`;
    return `<div class="vw dk">
      <header class="tb"><button type="button" class="tb-back" data-act="back" aria-label="Orqaga">${ic('arrow-left')}</button>
        <div class="tb-t"><div class="tb-k">${st.n}-dars</div><h1 class="tb-h">${T(d.nomi)}</h1></div>
        <span class="vw-cnt" aria-live="polite" aria-atomic="true">${cnt}</span></header>
      <div class="vw-bar" aria-hidden="true"><span style="width:0%"></span></div>
      <div class="vw-stage dk-stage">
        <iframe class="dk-fr" title="${st.n}-dars taqdimoti" allow="fullscreen" allowfullscreen referrerpolicy="no-referrer"></iframe>
        <div class="dk-load" role="status"><span class="dk-spin">${ic('loader-circle', 'spin')}</span><b>Taqdimot yuklanmoqda</b></div>
        <div class="dk-ov"><button type="button" class="dk-ob" data-act="back" aria-label="Orqaga">${ic('arrow-left')}</button><span class="dk-oc">${cnt}</span><button type="button" class="dk-ob dk-fsb" data-act="dk-fs" aria-label="To'liq ekran">${fsI}</button></div>
        <button type="button" class="btn dk-fin" data-act="dk-finish" hidden><span class="lbl">Darsni tugatish</span>${ic('flag')}</button>
      </div>
      <div class="vw-tools">${vidPill(d)}${kb ? `<button type="button" class="pill" data-act="kitob" data-n="${st.n}">${ic('book-open')}<span>Kitob betlari</span></button>` : ''}<button type="button" class="pill dk-fsb" data-act="dk-fs" aria-label="To'liq ekran">${fsI}<span>To'liq ekran</span></button></div>
      <div class="vw-nav"><button type="button" class="btn sec vw-prev" data-act="dk-prev" aria-label="Oldingi" disabled>${ic('chevron-left')}<span class="lbl">Oldingi</span></button><button type="button" class="btn vw-next" data-act="dk-next" aria-label="Keyingi"><span class="lbl">Keyingi</span>${ic('chevron-right')}</button></div></div>`;
  }
  function mountDeck(st, box) {
    const d = L(st.n), root = $('.vw.dk', box);
    if (!d || !root) return;
    ls.set(KL, st.n);
    if (testOf(d) && !S.tests[st.n]) loadTest(st.n);
    const fr = $('.dk-fr', root), N = d.slaydlar, start = clamp(st.i || resumeIdx(st.n), 1, N);
    DK = { n: st.n, N, st, root, fr, cur: 0, step: 0, steps: 1, last: false, fs: false, tgfs: false, ok: false, loadT: 0, hintT: 0 };
    W.addEventListener('message', onDeckMsg);
    fr.addEventListener('load', () => { if (DK && DK.fr === fr) post({ noon: 'ping' }); });
    dkLoad(start);
    if (!ls.get(KHINT, false)) {
      ls.set(KHINT, true);
      $('.dk-stage', root).insertAdjacentHTML('beforeend', `<div class="vw-hint" role="note">${ic('smartphone')}<span>Telefonni yotqizsangiz slaydlar kattaroq ko'rinadi</span><button type="button" data-act="hint-ok">Tushunarli</button></div>`);
      DK.hintT = setTimeout(dkHint, 9000);
    }
  }
  function dkLoad(k) {
    if (!DK) return;
    const ld = $('.dk-load', DK.root);
    DK.ok = false;
    ld.classList.remove('gone', 'bad');
    ld.innerHTML = `<span class="dk-spin">${ic('loader-circle', 'spin')}</span><b>Taqdimot yuklanmoqda</b>`;
    DK.fr.src = deckSrc(L(DK.n), k);
    clearTimeout(DK.loadT);
    DK.loadT = setTimeout(() => {
      if (!DK || DK.ok) return;
      ld.classList.add('bad');
      ld.innerHTML = `<span class="dk-spin">${ic('wifi-off')}</span><b>Taqdimot yuklanmadi</b><small>Internet aloqasini tekshiring.</small><button type="button" class="btn" data-act="dk-reload">${ic('refresh-cw')}Qayta urinish</button>`;
    }, 25000);
  }
  function post(m) { try { if (DK && DK.fr.contentWindow) DK.fr.contentWindow.postMessage(m, W.location.origin); } catch (e) { /* jim */ } }
  function onDeckMsg(e) {
    if (!DK || e.source !== DK.fr.contentWindow || e.origin !== W.location.origin) return;
    const m = e.data || {};
    if (m.noon === 'slide') {
      const n = clamp(m.n | 0, 0, DK.N);
      if (n < 1) return;
      if (!DK.ok) { DK.ok = true; clearTimeout(DK.loadT); $('.dk-load', DK.root).classList.add('gone'); }
      if (DK.cur && n !== DK.cur) dkHint();
      DK.cur = n; DK.st.i = n;
      DK.step = Math.max(0, m.step | 0); DK.steps = Math.max(1, m.steps | 0);
      dkUI();
      markSeen(DK.n, n);
    } else if (m.noon === 'end') {
      dkFinish($('.vw-next', DK.root));
    }
  }
  function dkUI() {
    const r = DK.root, n = DK.cur, N = DK.N, last = n >= N && DK.step >= DK.steps - 1;
    $$('[data-dk-cnt]', r).forEach((x) => { x.textContent = n + ' / ' + N; });
    $('.vw-bar span', r).style.width = (100 * n / N).toFixed(2) + '%';
    $('.vw-prev', r).disabled = n <= 1 && DK.step <= 0;
    $('.dk-fin', r).hidden = !last;
    if (last === DK.last) return;
    DK.last = last;
    const next = $('.vw-next', r);
    next.setAttribute('data-act', last ? 'dk-finish' : 'dk-next');
    next.setAttribute('aria-label', last ? 'Darsni tugatish' : 'Keyingi');
    next.innerHTML = last ? `<span class="lbl">Darsni tugatish</span>${ic('flag')}` : `<span class="lbl">Keyingi</span>${ic('chevron-right')}`;
  }
  function dkStep(k) { if (!DK || !DK.ok) return; dkHint(); post({ noon: k > 0 ? 'next' : 'prev' }); }
  function dkFinish(btn) { if (DK) finishLesson(DK.n, btn); }
  function dkHint() {
    if (!DK) return;
    clearTimeout(DK.hintT);
    const h = $('.vw-hint', DK.root);
    if (h) h.remove();
  }
  /* To'liq ekran: Telegram 8.0+ da requestFullscreen, oddiy brauzerda Fullscreen API (+ yotiq holat); bo'lmasa ham
     ilova ichida sarlavha va tugmalar yashirilib, taqdimot butun ekranni egallaydi */
  function dkFs(on) {
    if (!DK) return;
    if (on === undefined) on = !DK.fs;
    if (on === DK.fs) return;
    DK.fs = on;
    DK.root.classList.toggle('fs', on);
    $$('.dk-fsb', DK.root).forEach((b) => {
      b.setAttribute('aria-label', on ? "To'liq ekrandan chiqish" : "To'liq ekran");
      const u = $('use', b);
      if (u) u.setAttribute('href', SPR + '#' + (on ? 'minimize' : 'maximize'));
      const s = $('span', b);
      if (s) s.textContent = on ? 'Kichraytirish' : "To'liq ekran";
    });
    if (on) {
      if (tgv('8.0') && tg.requestFullscreen) {
        try { tg.requestFullscreen(); DK.tgfs = true; } catch (e) { DK.tgfs = false; }
      } else {
        const el = D.documentElement, rq = el.requestFullscreen || el.webkitRequestFullscreen;
        if (rq) {
          try {
            const p = rq.call(el);
            const lock = () => { try { const o = W.screen && W.screen.orientation; if (o && o.lock) o.lock('landscape').catch(() => {}); } catch (e) { /* jim */ } };
            if (p && p.then) p.then(lock).catch(() => {}); else lock();
          } catch (e) { /* jim */ }
        }
      }
    } else {
      if (DK.tgfs && tg && tg.isFullscreen) { try { tg.exitFullscreen(); } catch (e) { /* jim */ } }
      DK.tgfs = false;
      if (D.fullscreenElement && D.exitFullscreen) {
        try { const o = W.screen && W.screen.orientation; if (o && o.unlock) o.unlock(); } catch (e) { /* jim */ }
        try { D.exitFullscreen().catch(() => {}); } catch (e) { /* jim */ }
      }
    }
    hap('imp', 'light');
  }
  function onTgFs() { if (DK && DK.fs && DK.tgfs && !tg.isFullscreen) dkFs(false); }
  function onDocFs() { if (DK && DK.fs && !DK.tgfs && !D.fullscreenElement && !D.webkitFullscreenElement) dkFs(false); }
  function leaveDeck() {
    if (!DK) return;
    if (DK.fs) dkFs(false);
    clearTimeout(DK.loadT); clearTimeout(DK.hintT);
    W.removeEventListener('message', onDeckMsg);
    try { DK.fr.src = 'about:blank'; } catch (e) { /* jim */ }
    DK = null;
    flush();
  }
  function streakFx(a, b) {
    const dn = '<path class="sk-d1" d="M0 70 Q40 44 80 62 T160 58 T240 64 V90 H0Z"/><path class="sk-d2" d="M0 80 Q50 62 100 76 T200 72 T240 78 V90 H0Z"/>';
    const wk = [0, 1, 2, 3, 4, 5, 6].map((i) => `<i class="${i === 6 ? 'td' : i >= 7 - b ? 'on' : ''}"></i>`).join('');
    return `<div class="sk" role="img" aria-label="Kun seriyasi ${b} kunga yetdi"><svg viewBox="0 0 240 90" aria-hidden="true"><circle class="sk-sun" cx="120" cy="52" r="22"/>${dn}</svg><div class="sk-n"><span class="sk-od" aria-hidden="true"><b>${a}</b><b>${b}</b></span><span class="sk-l">kun seriya</span></div><div class="sk-w" aria-hidden="true">${wk}</div></div>`;
  }
  function showDone(n, xp, tb, sk) {
    const d = L(n), nx = L(n + 1), t = S.tests[n];
    const item = (act, attrs, icon, title, sub, dis, c) => `<button type="button" class="nx-i" data-act="${act}" ${attrs}${dis ? ' aria-disabled="true"' : ''}>${dia(icon, c)}<span><b>${title}</b><small>${sub}</small></span>${dis ? ic('lock') : ic('chevron-right')}</button>`;
    let nxt = '';
    vidsOf(d).forEach((v) => { nxt += item('video', `data-v="${esc(v.id)}" data-how="replace"`, ic('circle-play'), 'Video dars', `${T(v.nomi)} · ${mins(v.davomiylik)} daq`); });
    if (testOf(d)) nxt += item('quiz', `data-n="${n}" data-how="replace"`, ic('list-checks'), 'Mashq', t ? t.savollar.length + ' savol' : 'Test');
    if (nx) { const ok = avail(nx.n); nxt += item('lesson', `data-n="${nx.n}" data-how="replace"`, ok ? ic('arrow-right') : ic('lock'), 'Keyingi dars', ok ? `${nx.n}-dars · ${T(nx.nomi)}` : lockMsg(nx.n), !ok, ok ? 'cta' : 'lk'); }
    openSheet(`<div class="ld-card">
      <span class="dia cta big ld-badge" aria-hidden="true">${ic('trophy')}</span>
      <h2>Dars tugadi!</h2>
      <p>${n}-dars · ${T(d.nomi)}</p>
      ${sk ? streakFx(sk[0], sk[1]) : ''}
      ${xp > 0 ? (ballOn() ? `<span class="xp-pill">${ic('gem')}+${xp} ball</span>` : '') : '<p class="muted">Bu dars avval tugatilgan.</p>'}
      ${tb > 0 && ballOn() ? `<span class="xp-pill tkb">${ic('gift')}+${tb} ball · taklif bonusi</span>` : ''}
      ${nxt ? `<div class="nx">${nxt}</div>` : ''}
      <button type="button" class="btn sec" data-act="tab" data-v="darslar">Darslarga qaytish</button></div>`, 'Dars tugadi', 'tugadi', n);
  }

  /* ---- Kattalashtirish (1x / 2x / 3x, surish) ---- */
  function openZoom() {
    if (!VW || S.zoom) return;
    const i = VW.i || 1, pg = VW.pages[i - 1];
    if (!pg) return;
    S.zoom = { s: 1, a4: pg.p };
    $('#ovl').insertAdjacentHTML('beforeend', `<div class="zm" role="dialog" aria-modal="true" aria-label="Slaydni kattalashtirish"><div class="zm-top"><span class="zm-t">${esc(cntText(pg, VW.N))}</span><div class="seg" role="group" aria-label="Kattalashtirish darajasi">${[1, 2, 3].map((k) => `<button type="button" data-act="zm-s" data-v="${k}" aria-pressed="${k === 1}">${k}×</button>`).join('')}</div><button type="button" class="zm-x" data-act="zm-close" aria-label="Yopish">${ic('x')}</button></div><div class="zm-wrap"><img src="${esc(pg.url)}" alt="${esc($('img', $(`.vw-sl[data-i="${i}"]`, VW.root)).alt)}" draggable="false"></div><div class="zm-tip">Kattalashtirilgan slaydni barmoq bilan suring</div></div>`);
    const wrap = $('#ovl .zm-wrap');
    sizeZoom();
    wrap.addEventListener('pointerdown', zmDown);
    wrap.addEventListener('dblclick', () => setZoom(S.zoom && S.zoom.s > 1 ? 1 : 2));
    const x = $('#ovl .zm-x');
    try { x.focus({ preventScroll: true }); } catch (e) { /* jim */ }
    trKick();
  }
  function sizeZoom() {
    const wrap = $('#ovl .zm-wrap'), img = wrap && $('img', wrap);
    if (!img || !S.zoom) return;
    const s = S.zoom.s, w0 = wrap.clientWidth, h0 = wrap.clientHeight, ar = S.zoom.a4 ? 1000 / 1414 : 16 / 9;
    let bw = w0, bh = w0 / ar;
    if (bh > h0) { bh = h0; bw = h0 * ar; }
    const cx = (wrap.scrollLeft + w0 / 2) / Math.max(1, wrap.scrollWidth), cy = (wrap.scrollTop + h0 / 2) / Math.max(1, wrap.scrollHeight);
    img.style.width = Math.round(bw * s) + 'px';
    img.style.height = Math.round(bh * s) + 'px';
    wrap.scrollLeft = cx * wrap.scrollWidth - w0 / 2;
    wrap.scrollTop = cy * wrap.scrollHeight - h0 / 2;
  }
  function setZoom(k) {
    if (!S.zoom) return;
    S.zoom.s = clamp(k, 1, 3);
    $$('#ovl .zm .seg button').forEach((b) => b.setAttribute('aria-pressed', String(+b.getAttribute('data-v') === S.zoom.s)));
    sizeZoom();
    hap('sel');
  }
  let zmDrag = null;
  function zmDown(e) {
    if (e.pointerType !== 'mouse') return;
    const wrap = e.currentTarget;
    zmDrag = { x: e.clientX, y: e.clientY, l: wrap.scrollLeft, t: wrap.scrollTop, wrap };
    const mv = (ev) => { if (!zmDrag) return; zmDrag.wrap.scrollLeft = zmDrag.l - (ev.clientX - zmDrag.x); zmDrag.wrap.scrollTop = zmDrag.t - (ev.clientY - zmDrag.y); };
    const up = () => { zmDrag = null; W.removeEventListener('pointermove', mv); W.removeEventListener('pointerup', up); };
    W.addEventListener('pointermove', mv);
    W.addEventListener('pointerup', up);
    e.preventDefault();
  }
  function closeZoom(silent) {
    const z = $('#ovl .zm');
    S.zoom = null;
    if (!z) return;
    z.remove();
    trKick();
    if (!silent && VW) { const b = $('[data-act="vw-zoom"]', VW.root); if (b) { try { b.focus({ preventScroll: true }); } catch (e) { /* jim */ } } }
  }

  /* ---- Video pleyer ---- */
  let PL = null;
  function vpStatus(x) {
    const v = x.v, p = vp(v.id), pct = p.done_at ? 100 : Math.min(100, Math.round(100 * (p.pos || 0) / Math.max(1, v.davomiylik)));
    const bar = `<span class="vp-bar"><i style="width:${pct}%"></i></span>`;
    if (!ballOn()) return `${dia(p.done_at ? ic('circle-check') : ic('circle-play'), p.done_at ? 'ok' : '')}<span><b>${p.done_at ? "Video ko'rildi" : "Ko'rish jarayoni"}</b><small>${p.done_at ? "Istalgan payt qayta ko'rish mumkin." : "Videoning 90% ini ko'rsangiz, ko'rilgan deb belgilanadi."}</small>${bar}</span>`;
    return `${dia(p.done_at ? ic('circle-check') : ic('gem'), p.done_at ? 'ok' : '')}<span><b>${p.done_at ? "Video ko'rildi" : '+30 ball'}</b><small>${p.done_at ? "Ball qo'shilgan. Istalgan payt qayta ko'rish mumkin." : "Videoning 90% ini ko'rsangiz ball olasiz."}</small>${bar}</span>`;
  }
  function playerHtml(st) {
    const x = vidOf(st.vid);
    if (!x) return notFound();
    const d = x.d, v = x.v, vs = vidsOf(d), others = vs.filter((o) => o.id !== v.id);
    const k = vs.length > 1 ? ` (${vs.indexOf(v) + 1}/${vs.length})` : '';
    return `${topbar(T(v.nomi), d.n + '-dars · video' + k)}
      <div class="vp"><div class="vp-box"><video controls playsinline webkit-playsinline preload="metadata" poster="${esc(vq(v.poster))}" src="${esc(v.url)}" aria-label="${d.n}-dars videosi: ${esc(v.nomi)}"></video></div>
      <div><h2 class="vp-h">${d.n}-dars · ${T(v.nomi)}</h2><p class="vp-m">${T(d.nomi)} · ${mins(v.davomiylik)} daqiqa</p></div>
      <div class="card vp-st" aria-live="polite">${vpStatus(x)}</div>
      <button type="button" class="btn" data-act="lesson" data-n="${d.n}">${ic('presentation')}Darsga o'tish</button>
      ${others.length ? `<section class="vp-more"><h2 class="sec-h">Shu darsning boshqa videolari</h2><div class="nx">${others.map((o) => { const p = vp(o.id); return `<button type="button" class="nx-i" data-act="video" data-v="${esc(o.id)}" data-how="replace">${dia(p.done_at ? ic('circle-check') : ic('circle-play'), p.done_at ? 'ok' : '')}<span><b>${T(o.nomi)}</b><small>${mins(o.davomiylik)} daq${p.done_at ? " · ko'rildi" : ''}</small></span>${ic('chevron-right')}</button>`; }).join('')}</div></section>` : ''}</div>`;
  }
  function mountPlayer(st, box) {
    const x = vidOf(st.vid), v = $('video', box);
    if (!x || !v) return;
    const it = vp(x.v.id);
    PL = { v, d: x, id: x.v.id, last: Date.now(), sent: +it.pos || 0, done: !!it.done_at, box };
    v.addEventListener('loadedmetadata', () => {
      const dur = v.duration || x.v.davomiylik, pos = +it.pos || 0;
      if (pos > 10 && pos < 0.95 * dur) { try { v.currentTime = pos; } catch (e) { /* jim */ } }
    });
    v.addEventListener('timeupdate', onPlTime);
    v.addEventListener('pause', () => savePos(true));
    v.addEventListener('ended', () => savePos(true));
    v.addEventListener('error', () => { if (v.error && PL && PL.v === v) toast("Videoni yuklab bo'lmadi. Internetni tekshiring.", 'err'); });
  }
  function onPlTime() {
    if (!PL) return;
    const v = PL.v, t = v.currentTime || 0, dur = v.duration || PL.d.v.davomiylik;
    const pr = P().videos[PL.id] || (P().videos[PL.id] = { pos: 0, done_at: null });
    if (t > 0) pr.pos = t;
    const bar = $('.vp-bar i', PL.box);
    if (bar && !pr.done_at) bar.style.width = Math.min(100, Math.round(100 * t / Math.max(1, dur))) + '%';
    if (Date.now() - PL.last >= 15000) savePos();
    if (!PL.done && dur && t >= 0.9 * dur) { PL.done = true; videoDone(); }
  }
  function savePos(force) {
    if (!PL || PL.v.readyState < 1) return;
    const t = PL.v.currentTime || 0;
    PL.last = Date.now();
    if (t < 1 && PL.sent > 10) return;
    if (Math.abs(t - PL.sent) < (force ? 0.5 : 1)) return;
    PL.sent = t;
    enqueue({ type: 'video_pos', vid: PL.id, pos: Math.round(t * 10) / 10 });
  }
  async function videoDone() {
    const p = PL;
    if (!p) return;
    const ev = { type: 'video_done', vid: p.id };
    try {
      const r = await sendEv(ev);
      mergeEv(ev, r);
      if (r.xp_added) { toast(ballOn() ? `Video ko'rildi: +${r.xp_added} ball` : "Video ko'rildi", 'ok'); hap('not', 'success'); }
      if (PL === p) { const s = $('.vp-st', p.box); if (s) s.innerHTML = vpStatus(p.d); }
    } catch (e) { if (PL === p) p.done = false; }
  }
  function leavePlayer() {
    if (!PL) return;
    savePos(true);
    try { PL.v.pause(); } catch (e) { /* jim */ }
    PL = null;
    flush();
  }

  /* ---- Mashq ---- */
  const newQuiz = (n) => ({ n, i: 0, pick: null, done: false, hearts: 5, correct: 0, answers: [], wrong: [], t0: Date.now(), over: false, sending: false });
  function startQuiz(n, how) {
    const d = L(n);
    if (!d || !testOf(d)) return;
    if (!avail(n)) { denyLesson(n); return; }
    S.quiz = newQuiz(n);
    hap('imp', 'light');
    go('mashq', { n }, how);
    if (!S.tests[n]) loadTest(n);
  }
  async function loadTest(n) {
    const d = L(n), u = testOf(d);
    if (!u) return;
    S.testErr[n] = null;
    try { S.tests[n] = await getJSON(u); } catch (e) { S.testErr[n] = e; }
    const t = topS();
    if (S.phase !== 'ready' || S.ob || !t) return;
    if (t.s === 'mashq' && t.n === n) { if (S.quiz) S.quiz.t0 = Date.now(); render('same'); }
    else if (t.s === 'bosh' && S.stack.length === 1) render('same');
  }
  function quizTop(q, total, answered, fx) {
    fx = fx || {};
    return `<div class="qz-top"><button type="button" class="qz-x" data-act="back" aria-label="Mashqdan chiqish">${ic('x')}</button>
      <div class="qz-bar sx${fx.grow ? ' grow' : ''}" role="progressbar" aria-label="Mashq jarayoni" aria-valuemin="0" aria-valuemax="${total}" aria-valuenow="${answered}"><span style="--p:${(answered / Math.max(1, total)).toFixed(3)};--p0:${(fx.p0 || 0).toFixed(3)}"></span></div>
      <span class="qz-h${fx.lose ? ' lose' : ''}" aria-label="${q.hearts} ta yurak qoldi">${ic('heart')}<b>${q.hearts}</b></span></div>`;
  }
  function quizHtml(st) {
    const t = S.tests[st.n], err = S.testErr[st.n];
    let q = S.quiz;
    if (!q || q.n !== st.n) q = S.quiz = newQuiz(st.n);
    if (!t) {
      return `<div class="qz">${quizTop(q, 1, 0)}<div class="qz-body">${err ? errBlock(err, 'test-retry') : loadHtml('Mashq yuklanmoqda')}</div></div>`;
    }
    const total = t.savollar.length;
    if (q.over) {
      return `<div class="qz">${quizTop(q, total, q.i + 1)}<div class="qz-end">${dia(ic('heart-crack'), 'big lk')}<h1>Yuraklar tugadi</h1><p>Mavzuni yana bir bor ko'rib chiqing va qaytadan urinib ko'ring.</p><div class="acts"><button type="button" class="btn" data-act="qz-restart">${ic('rotate-ccw')}Qayta boshlash</button><button type="button" class="btn sec" data-act="lesson" data-n="${q.n}" data-how="replace">Darsga qaytish</button></div></div>${band()}</div>`;
    }
    const Q = t.savollar[q.i], answered = q.i + (q.done ? 1 : 0);
    const grid = Q.opts.every((o) => String(o).length <= 14);
    const opts = Q.opts.map((o, k) => {
      let cls = 'qz-o', badge = '', extra = '';
      if (q.done) {
        if (k === Q.ok) { const hit = q.pick === Q.ok; cls += hit ? ' right' : ' right hintr'; badge = `<span class="qz-b ok">${ic('check')}</span>${hit ? '<span class="qz-burst" aria-hidden="true"><i></i><i></i><i></i></span>' : ''}`; extra = sr(" — to'g'ri javob"); }
        else if (k === q.pick) { cls += ' wrong'; badge = `<span class="qz-b no">${ic('x')}</span>`; extra = sr(' — sizning javobingiz, xato'); }
        else cls += ' dim';
      } else if (k === q.pick) cls += ' sel';
      return `<button type="button" class="${cls}" data-act="pick" data-i="${k}" aria-pressed="${k === q.pick}"${q.done ? ' disabled' : ''}><span class="qz-ol" aria-hidden="true">${'ABCD'.charAt(k) || k + 1}</span><span class="qz-ot">${T(o)}</span>${extra}${badge}</button>`;
    }).join('');
    let foot;
    if (!q.done) foot = `<div class="qz-foot"><button type="button" class="btn" data-act="qz-check"${q.pick == null ? ' disabled' : ''}>Tekshirish</button></div>`;
    else {
      const ok = q.pick === Q.ok;
      foot = `<div class="qz-sheet ${ok ? 'ok' : 'bad'}" role="status"><div class="qz-sh-h"><span class="qz-sh-ic">${ok ? ic('check') : ic('x')}</span>${ok ? "To'g'ri javob!" : 'Xato javob'}</div>${ok ? '' : `<p class="qz-ans">To'g'ri javob: ${T(Q.opts[Q.ok])}</p>`}${Q.izoh ? `<p class="qz-iz">${T(Q.izoh)}</p>` : ''}<button type="button" class="btn${ok ? '' : ' bad'}" data-act="qz-next">Davom etish</button></div>`;
    }
    return `<div class="qz">${quizTop(q, total, answered, { grow: q.done, lose: q.done && q.pick !== Q.ok, p0: q.i / Math.max(1, total) })}<div class="qz-body"><div class="kick">${q.i + 1}-savol · ${total} tadan · ${q.n}-dars</div><h1 class="qz-q">${T(Q.q)}</h1><div class="qz-opts ${grid ? 'grid' : 'list'}" role="group" aria-label="Javob variantlari">${opts}</div></div>${foot}</div>`;
  }
  function qzPick(i) {
    const q = S.quiz;
    if (!q || q.done || q.over) return;
    q.pick = i;
    hap('sel');
    render('same');
  }
  function qzCheck() {
    const q = S.quiz, t = q && S.tests[q.n];
    if (!q || !t || q.pick == null || q.done) return;
    const Q = t.savollar[q.i];
    q.done = true;
    q.answers[q.i] = q.pick;
    if (q.pick === Q.ok) { q.correct += 1; hap('not', 'success'); }
    else { q.hearts = Math.max(0, q.hearts - 1); q.wrong.push(q.i); hap('not', 'error'); }
    render('same');
  }
  function qzNext(btn) {
    const q = S.quiz, t = q && S.tests[q.n];
    if (!q || !t) return;
    if (q.i >= t.savollar.length - 1) { finishQuiz(btn); return; }
    if (q.hearts <= 0) { q.over = true; hap('not', 'error'); render('same'); return; }
    q.i += 1; q.pick = null; q.done = false;
    render('same');
    W.scrollTo(0, 0);
  }
  async function finishQuiz(btn) {
    const q = S.quiz, t = q && S.tests[q.n];
    if (!q || !t || q.sending) return;
    q.sending = true;
    busy(btn, true);
    try {
      const ev = { type: 'test_done', dars: q.n, answers: q.answers.slice() }, r = await sendEv(ev);
      mergeEv(ev, r);
      const total = r.total || t.savollar.length, correct = r.correct != null ? r.correct : q.correct;
      S.result = { n: q.n, correct, total, xp: r.xp_added || 0, sec: Math.round((Date.now() - q.t0) / 1000), answers: q.answers.slice(), wrong: q.wrong.slice() };
      S.quiz = null;
      hap('not', correct * 2 >= total ? 'success' : 'error');
      go('natija', { n: S.result.n }, 'replace');
    } catch (e) {
      q.sending = false;
      busy(btn, false);
      toast(e.message || NET_MSG, 'err');
      hap('not', 'error');
    }
  }

  /* ---- Natija ---- */
  function resultHtml(st) {
    const r = S.result;
    if (!r || r.n !== st.n) return notFound();
    const t = S.tests[r.n], d = L(r.n), total = r.total || 1, pct = Math.round(100 * r.correct / total), perfect = r.correct >= total;
    const title = perfect ? "A'lo natija!" : pct >= 60 ? 'Yaxshi natija!' : "Yana bir urinib ko'ring";
    const best = tp(r.n);
    const mis = r.wrong.map((i) => {
      const Q = t.savollar[i];
      return `<div class="rs-row"><div class="rs-q"><small>${i + 1}-savol</small>${T(Q.q)}</div><div class="rs-a">Sizning javobingiz: ${T(Q.opts[r.answers[i]])}</div><div class="rs-r">To'g'ri javob: ${T(Q.opts[Q.ok])}</div></div>`;
    }).join('');
    const b = ballOn();
    let note = '';
    if (b && r.xp === 0 && !perfect) note = 'Ball faqat yangi eng yaxshi natija uchun beriladi.' + (best ? ` Eng yaxshi natijangiz: ${best.best}/${best.total || total}.` : '');
    else if (best && best.tries > 1) note = `Eng yaxshi natijangiz: ${best.best}/${best.total || total}.`;
    return `<div class="rs">${heroCard(pct >= 60 ? ic('trophy') : ic('target'), r.n + '-dars · mashq', title, `${T((t && t.nomi) || d.nomi)}`, 'rs-hero', 'h1')}
      <div class="rs-stats" style="--n:${b ? 3 : 2}"><div class="card rs-st ok"><span>To'g'ri</span><b>${r.correct}/${total}</b></div>${b ? `<div class="card rs-st xp"><span>Ball</span><b>+${r.xp}</b></div>` : ''}<div class="card rs-st tm"><span>Vaqt</span><b>${mmss(r.sec)}</b></div></div>
      ${note ? `<p class="rs-note">${note}</p>` : ''}
      ${mis ? `<section class="card rs-mis"><h2>${ic('rotate-ccw')}Xatolar: ${r.wrong.length} ta</h2>${mis}</section>` : `<div class="card rs-perfect">${dia(ic('badge-check'), 'ok')}<span>Hammasi to'g'ri. Mavzuni yaxshi o'zlashtirdingiz.</span></div>`}
      <div class="rs-acts"><button type="button" class="btn sec" data-act="qz-retry" data-n="${r.n}">${ic('refresh-cw')}Qayta urinish</button><button type="button" class="btn" data-act="tab" data-v="darslar">Darslarga qaytish</button></div></div>`;
  }

  /* ---- Reyting ---- */
  function rkRow(r) {
    return `<div class="rk${r.me ? ' me' : ''}"><span class="rk-n">${r.rank}</span><span class="ava" aria-hidden="true">${esc(ini(r.name))}</span><span class="rk-t"><b>${T(r.name)}${r.me ? ' (siz)' : ''}</b><small>${ic('flame')}${r.streak || 0} kun seriya</small></span><span class="rk-x">${num(r.xp)}<small> ball</small></span></div>`;
  }
  function podium(top) {
    const slot = (r, k) => (r ? `<div class="pd r${k}${r.me ? ' me' : ''}"><div class="pd-ava">${k === 1 ? `<span class="crown">${ic('crown')}</span>` : ''}${esc(ini(r.name))}</div><div class="pd-n">${T(r.name)}${r.me ? ' (siz)' : ''}</div><div class="pd-x">${num(r.xp)} ball</div><div class="pd-b">${k}${sr("-o'rin")}</div></div>` : '<div class="pd"></div>');
    return `<div class="pod">${slot(top[1], 2)}${slot(top[0], 1)}${slot(top[2], 3)}</div>`;
  }
  const rkSkel = () => `<div role="status" aria-label="Yuklanmoqda"><div class="pod">${[96, 124, 80].map((hh) => `<div class="pd"><div class="skel" style="width:58px;height:58px;border-radius:50%"></div><div class="skel" style="width:70%;height:14px"></div><div class="skel" style="width:100%;height:${hh}px"></div></div>`).join('')}</div><div class="skel" style="height:240px;border-radius:16px;margin-top:12px"></div></div>`;
  function reytingHtml() {
    const R = S.rating, data = R[R.davr];
    const sub = R.davr === 'hafta' ? "Dushanbadan beri to'plangan ballar" : "Barcha vaqt davomida to'plangan ballar";
    let h = `<div class="page rt"><header class="ap-head"><h1 class="h1">Reyting</h1></header><p class="ap-sub">${sub}</p>`;
    h += `<div class="seg" role="tablist" aria-label="Davr"><button type="button" role="tab" data-act="davr" data-v="hafta" aria-selected="${R.davr === 'hafta'}">Bu hafta</button><button type="button" role="tab" data-act="davr" data-v="umumiy" aria-selected="${R.davr === 'umumiy'}">Umumiy</button></div>`;
    if (!data) h += R.err ? `<div class="card rk-err">${errBlock(R.err, 'rating-retry')}</div>` : rkSkel();
    else if (!data.top || !data.top.length) h += emptyHtml('trophy', "Hali hech kim ball to'plamagan", "Slaydlarni ko'ring, mashq qiling va birinchi bo'ling!", true);
    else {
      const top = data.top, rest = top.slice(3), mine = top.some((r) => r.me);
      h += podium(top.slice(0, 3));
      if (rest.length) h += `<div class="card rk-list">${rest.map(rkRow).join('')}</div>`;
      if (!mine && data.me) h += `<div class="card rk-pin">${rkRow({ rank: data.me.rank, name: data.me.name || 'Siz', xp: data.me.xp, streak: data.me.streak, me: true })}</div>`;
      h += `<p class="rk-note">${ic('info')}<span>${R.davr === 'hafta' ? 'Haftalik reyting har dushanba 00:00 da yangilanadi.' : "Umumiy reyting barcha to'plangan ballar bo'yicha."} Ball slaydlar, darslar, video va mashqlar uchun beriladi.</span></p>`;
    }
    return h + '</div>';
  }
  function mountReyting() {
    const R = S.rating, d = R.davr;
    if (!rateOn() || R.err) return;
    if (!R[d] || Date.now() - (R.at[d] || 0) > 60000) loadRating(d);
  }
  async function loadRating(d) {
    const R = S.rating;
    if (R.busy === d) return;
    R.busy = d;
    R.err = null;
    try { R[d] = await api('/api/s/rating?davr=' + d); R.at[d] = Date.now(); } catch (e) { if (!R[d]) R.err = e; }
    R.busy = false;
    const t = topS();
    if (t && t.s === 'reyting' && !S.ob && R.davr === d) render('same');
  }

  /* ---- Profil ---- */
  function profilHtml() {
    const u = S.me.user || {}, s = S.me.stats, week = weekOf(s);
    const vids = allVids(), vDone = vids.filter((x) => vp(x.v.id).done_at).length;
    const tests = S.K.darslar.filter((d) => testOf(d));
    const active = week.filter((w) => w.xp > 0).length, r = rejimNow(), a = S.prefs.arab === 'l' ? 'l' : 'm';
    const b = ballOn(), vOn = feat('video'), tOn = feat('test');
    /* Statistika: o'chirilgan funksiyalar yashiriladi; 1-3 ta - bir qator, 4 - 2x2, 5 - 3+2, 6 - 3x2 */
    const sts = (b ? [['gem', `<b data-stat="xp">${num(s.xp)}</b>`, 'ball'], ['flame', `<b data-stat="streak">${s.streak || 0}</b>`, 'kun seriya'],
      ['medal', `<b>${s.best_streak || 0}</b>`, 'eng uzun seriya']] : [])
      .concat([['book-check', `<b>${doneCount()}/${totalN()}</b>`, 'darslar']])
      .concat(vOn ? [['circle-play', `<b>${vDone}/${vids.length}</b>`, 'videolar']] : [])
      .concat(tOn ? [['list-checks', `<b>${tests.filter((d) => { const x = tp(d.n); return x && x.tries > 0; }).length}/${tests.length}</b>`, 'mashqlar']] : []);
    const about = [vOn ? 'Video darslar: ' + vids.length : '', tOn ? 'Mashqlar: ' + tests.length : ''].filter(Boolean).join(' · ');
    const days = week.map((w, i) => {
      const on = w.xp > 0, today = i === week.length - 1;
      return `<div class="day${on ? ' on' : ''}${today ? ' today' : ''}"><span class="dt">${on ? ic('check') : ''}</span>${wdOf(w.day)}${sr(on ? ' — ' + w.xp + ' ball' : " — faollik yo'q")}</div>`;
    }).join('');
    return `<div class="page pf">${demoBar()}
      <div class="pf-head"><span class="ava pf-ava">${avatarInner()}</span><div><h1 class="pf-name">${T(userName())}</h1><small class="pf-user">${u.username ? '@' + esc(u.username) : PREVIEW ? 'Namuna foydalanuvchi' : 'Telegram foydalanuvchisi'}</small></div></div>
      <div class="card pf-stats n${sts.length}">${sts.map((x) => `<div class="pf-st"><span class="si">${ic(x[0])}</span>${x[1]}<small>${x[2]}</small></div>`).join('')}</div>
      ${b ? `<div class="card wk"><div class="wk-h"><b>So'nggi 7 kun</b><small>${active} / 7 kun faol</small></div><div class="days">${days}</div></div>` : ''}
      ${pfSocial()}
      <h2 class="sec-h">Ko'rinish</h2>
      <div class="card set">
        ${feat('uslub') ? `${mzRow()}${thumbs(false)}<div class="set-sep"></div>` : ''}
        <div class="set-r">${dia(ic('sun-moon'))}<span class="st"><b>Rejim</b><small>Avto: 06:00–18:59 kunduzgi, qolgani tungi</small></span></div>
        <div class="seg" role="group" aria-label="Rejim">${MODES.map(([k, l]) => `<button type="button" data-act="set-rejim" data-v="${k}" aria-pressed="${r === k}">${modeIc(k)}${l}</button>`).join('')}</div>
        <div class="set-sep"></div>
        <div class="set-r">${dia(ic('type'))}<span class="st"><b>Arabcha matn</b><small>${tOn ? "Mashq va izohlardagi arabcha yozuv o'lchami" : "Ilovadagi arabcha yozuv o'lchami"}</small></span><span class="ar-sample">${bdi('بَ بِ بُ')}</span></div>
        <div class="seg" role="group" aria-label="Arabcha matn o'lchami"><button type="button" data-act="set-arab" data-v="m" aria-pressed="${a === 'm'}">O'rta</button><button type="button" data-act="set-arab" data-v="l" aria-pressed="${a === 'l'}">Katta</button></div>
      </div>
      ${feat('eslatma') ? `<h2 class="sec-h">Eslatma</h2>
      <div class="card set"><div class="set-r">${dia(ic('bell'))}<span class="st"><b>Kunlik eslatma</b><small>Har kuni 19:00 da bot eslatadi</small></span><button type="button" class="sw" role="switch" aria-checked="${S.prefs.eslatma !== false}" data-act="set-esl" aria-label="Kunlik eslatma"><span></span></button></div></div>` : ''}
      ${qgOn() ? `<h2 class="sec-h">Yordam</h2>
      <div class="card set"><button type="button" class="set-r pf-qg" data-act="qollanma-open">${dia(ic('book-open'))}<span class="st"><b>Qo'llanma</b><small>Ilovadan foydalanish qo'llanmasi</small></span>${ic('chevron-right')}</button></div>` : ''}
      <h2 class="sec-h">Kurs haqida</h2>
      <div class="card about">${dia(ic('graduation-cap'))}<span><b>${T(S.K.nomi)}</b><small>${totalN()} dars · ${num(S.K.jami_slayd)} slayd · ${S.K.qismlar.length} qism</small>${about ? `<small>${about}</small>` : ''}</span></div>
      <div class="foot">${sig()}${T(S.K.brend || 'Muhammadamin')}</div></div>`;
  }

  /* ================= 9b. Duellar va do'st taklifi (SPEC 11.4) =================
     Ekranlar: duellar (ro'yxat), duel (r = id: tanishuv -> 5 savol x 15 s -> yuborish), duel-natija (r = id), taklif.
     API: GET /api/s/duels, GET /api/s/duel?id=, POST /api/s/duel/{new,accept,start,finish}, GET /api/s/taklif (SPEC 11.3, 11.6).
     Javoblar tahlili (review): finish javobidan yoki GET /api/s/duel dan. Vaqt: performance.now(), har savolga alohida;
     start javobidagi left_ms butun duel uchun chegara (qayta ochilganda). */
  const RU = () => Object.assign({ savollar: 5, sec: 15, xp_win: 15, xp_draw: 5, hours: 24 }, (S.du.d && S.du.d.rules) || {});
  const MON = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek'];
  const tsOf = (iso) => { const t = Date.parse(iso || ''); return isNaN(t) ? 0 : t; };
  /* Toshkent vaqti: "Bugun, 14:05" / "Kecha, 09:30" / "2-okt, 18:00" (noT - soatsiz) */
  function whenTxt(iso, noT) {
    const t = tsOf(iso);
    if (!t) return '';
    const s = new Date(t + 5 * 36e5).toISOString(), k = s.slice(0, 10), td = todayIso(), p = k.split('-').map(Number);
    return (k === td ? 'Bugun' : k === isoAdd(td, -1) ? 'Kecha' : p[2] + '-' + MON[p[1] - 1]) + (noT ? '' : ', ' + s.slice(11, 16));
  }
  function leftTxt(iso) {
    const ms = tsOf(iso) - Date.now();
    if (ms <= 0) return '';
    return ms >= 36e5 ? Math.floor(ms / 36e5) + ' soat qoldi' : Math.max(1, Math.ceil(ms / 6e4)) + ' daqiqa qoldi';
  }
  const secTxt = (ms) => (Math.round((+ms || 0) / 100) / 10).toFixed(1).replace('.', ',') + ' s';
  const rvName = (it) => (it && it.rival && it.rival.name) || 'Raqib';
  const skb = (h, r) => `<div class="skel" style="height:${h}px;border-radius:${r || '16px'}"></div>`;
  function duPill(it) {
    const sc = it.my && it.their ? ` ${+it.my.correct || 0}:${+it.their.correct || 0}` : '';
    const x = it.status === 'sizning_navbat' ? ['turn', ic('play'), 'Sizning navbatingiz']
      : it.status === 'raqib_navbati' ? ['wait', ic('hourglass'), 'Raqib navbati']
        : it.status === 'muddati_otdi' ? ['exp', ic('clock'), "Muddati o'tdi"]
          : it.result === 'yutdi' ? ['won', ic('trophy'), 'Yutdingiz' + sc]
            : it.result === 'yutqazdi' ? ['lost', ic('circle-x'), 'Yutqazdingiz' + sc] : ['draw', ic('equal'), 'Durrang' + sc];
    return `<span class="dpill ${x[0]}">${x[1]}${x[2]}</span>`;
  }
  const duNote = (n) => `<div class="du-note ${n.k}" role="${n.k === 'err' ? 'alert' : 'status'}">${n.k === 'load' ? ic('loader-circle', 'spin') : ic('circle-alert')}<span>${T(n.t)}</span></div>`;

  /* ---- Ma'lumot ---- */
  function duPend() { const d = S.du.d; if (d && S.me) S.me.duel_pending = d.items.filter((x) => x.status === 'sizning_navbat').length; }
  /* Bitta duel: {duel, review|null} (review - faqat o'zim o'ynagandan keyin) */
  async function duGet(id) {
    const r = await api('/api/s/duel?id=' + encodeURIComponent(id));
    if (r.duel && r.duel.id) duPut(r.duel);
    if (Array.isArray(r.review) && r.review.length) S.du.rev[id] = r.review;
    S.du.gt[id] = Date.now();
    return r;
  }
  function duPut(it) {
    if (!it || !it.id) return;
    const Z = S.du, d = Z.d;
    Z.items[it.id] = it;
    if (!d) return;
    const k = d.items.findIndex((x) => x.id === it.id);
    if (k >= 0) d.items[k] = it; else d.items.unshift(it);
    duPend();
  }
  function duLoad() {
    const Z = S.du;
    if (Z.busy) return Z.busy;
    Z.busy = (async () => {
      try {
        const r = await api('/api/s/duels');
        r.items = (Array.isArray(r.items) ? r.items : []).filter((x) => x && x.id);
        r.stats = Object.assign({ played: 0, won: 0, lost: 0, draw: 0 }, r.stats || {});
        Z.d = r; Z.at = Date.now(); Z.err = null;
        r.items.forEach((x) => { Z.items[x.id] = x; });
        /* Ochiq do'st havolasi (invites) qayta ishlatiladi; ishlatilgan/eskirgan havola ulashilmaydi (bir martalik) */
        const inv = Array.isArray(r.invites) ? r.invites.filter((x) => x && x.link) : [];
        if (Z.inv && !inv.some((x) => x.link === Z.inv.link)) Z.inv = null;
        if (!Z.inv && inv.length) Z.inv = inv[0];
        duPend();
        if (S.me && r.pending != null) S.me.duel_pending = +r.pending || 0;
      } catch (e) { if (!Z.d) Z.err = e; }
      Z.busy = null;
      const t = topS();
      if (S.phase === 'ready' && !S.ob && t && (t.s === 'duellar' || t.s === 'duel-natija')) render('same');
    })();
    return Z.busy;
  }

  /* ---- Bosh va Profil kirish nuqtalari ---- */
  function homeCards() {
    const dOn = duelOn(), tOn = taklifOn();
    if (!dOn && !tOn) return '';
    const n = +((S.me && S.me.duel_pending) || 0);
    const a = dOn ? `<button type="button" class="card hc d" data-act="duel-open" aria-label="Duel${n ? ': ' + n + ' ta duel navbatingizni kutmoqda' : ''}">${dia(ic('swords'))}${n ? `<span class="hc-n" aria-hidden="true">${n}</span>` : ''}<span class="hc-t"><b>Duel</b><small>${n ? n + ' ta duel kutmoqda' : "Do'st bilan bellashuv"}</small></span></button>` : '';
    const t = tOn ? `<button type="button" class="card hc t" data-act="taklif-open">${dia(ic('gift'))}<span class="hc-t"><b>Taklif qilish</b><small>${ballOn() ? '+50 ball bonus' : "Birga o'rganing"}</small></span></button>` : '';
    return `<div class="hc2${dOn && tOn ? '' : ' one'}">${a}${t}</div>`;
  }
  function pfSocial() {
    const dOn = duelOn(), tOn = taklifOn(), n = +((S.me && S.me.duel_pending) || 0);
    if (!dOn && !tOn) return '';
    return `<h2 class="sec-h">Do'stlar bilan</h2><div class="card set">${dOn ? `<button type="button" class="set-r pf-go" data-act="duel-open">${dia(ic('swords'))}<span class="st"><b>Duellar</b><small>${RU().savollar} savol, har biriga ${RU().sec} soniya</small></span>${n ? `<span class="hc-n" aria-label="${n} ta duel kutmoqda">${n}</span>` : ''}${ic('chevron-right')}</button>` : ''}${tOn ? `<button type="button" class="set-r pf-go" data-act="taklif-open">${dia(ic('gift'))}<span class="st"><b>Do'stlarni taklif qilish</b><small>${ballOn() ? "Ikkalangizga +50 ball" : 'Shaxsiy havolangiz'}</small></span>${ic('chevron-right')}</button>` : ''}</div>`;
  }
  function openDuellar(rep) {
    if (!duelOn()) return;
    const k = S.stack.map((x) => x.s).lastIndexOf('duellar');
    if (k === S.stack.length - 1) return;
    hap('imp', 'light');
    if (k >= 0) { closeSheet(true); hideToast(); leaveCur(); S.stack.length = k + 1; render('pop'); return; }
    go('duellar', null, rep ? 'replace' : 'push');
  }
  function openDuel(id) {
    if (!duelOn() || !id) return;
    const it = S.du.items[id], keep = DU && DU.id === id && DU.phase === 'err';
    hap('imp', 'light');
    go(it && it.status !== 'sizning_navbat' && !keep ? 'duel-natija' : 'duel', { id });
  }

  /* ---- Duellar ro'yxati ---- */
  function duRow(it) {
    const nm = rvName(it), act = it.status === 'sizning_navbat' || it.status === 'raqib_navbati';
    const meta = [it.mode === 'friend' ? "Do'st" : 'Tasodifiy', (act && leftTxt(it.expires_at)) || whenTxt(it.created_at)].filter(Boolean).join(' · ');
    return `<button type="button" class="du-row${it.status === 'sizning_navbat' ? ' turn' : ''}" data-act="duel-open" data-v="${esc(it.id)}"><span class="ava" aria-hidden="true">${esc(ini(nm))}</span><span class="du-rt"><b>${T(nm)}</b>${duPill(it)}<small>${it.mode === 'friend' ? ic('users') : ic('shuffle')}${esc(meta)}</small></span>${ic('chevron-right')}</button>`;
  }
  function duellarHtml() {
    const Z = S.du, d = Z.d;
    let h = topbar('Duellar', 'Bellashuv') + '<div class="du">' + (Z.note ? duNote(Z.note) : '');
    if (!d) return h + (Z.err ? `<div class="card du-ec">${errBlock(Z.err, 'duel-retry')}</div>` : `<div class="du-sk" role="status" aria-label="Yuklanmoqda">${skb(168, '20px')}${skb(84)}${skb(230)}</div>`) + '</div>';
    const s = d.stats, it = d.items;
    const cta = d.can === false
      ? `<div class="du-why" role="note">${ic('lock')}<span>${T(d.reason || 'Duel uchun avval kamida bitta darsni va uning testini tugating')}</span></div><button type="button" class="btn sec" data-act="tab" data-v="darslar">${ic('book-open')}Darslarga o'tish</button>`
      : `<button type="button" class="btn" data-act="duel-new">${ic('swords')}Yangi duel</button>`;
    h += heroCard(ic('swords'), `${RU().savollar} savol · ${RU().sec} soniya`, 'Bilimingizni sinang', 'Savollar faqat ikkalangiz tugatgan darslardan olinadi.') + cta;
    h += `<div class="du-stats" role="group" aria-label="Duel natijalari">${[['played', ic('swords'), "o'ynalgan"], ['won', ic('trophy'), 'yutgan'], ['lost', ic('circle-x'), 'yutqazgan'], ['draw', ic('equal'), 'durrang']]
      .map(([k, i, l]) => `<div class="card du-st ${k}">${i}<b>${num(s[k])}</b><small>${l}</small></div>`).join('')}</div>`;
    h += `<h2 class="sec-h">So'nggi duellar${it.length ? `<small>${it.length} ta</small>` : ''}</h2>`;
    h += it.length ? `<div class="card du-list">${it.map(duRow).join('')}</div>`
      : `<div class="card du-empty">${emptyHtml('swords', "Hali duel o'ynamadingiz", d.can === false ? "Darslarni tugatganingizdan keyin duel o'ynay olasiz." : "Tasodifiy raqib yoki do'stingiz bilan birinchi duelni boshlang.", true)}</div>`;
    return h + '</div>';
  }
  function mountDuellar() {
    const Z = S.du;
    if (Z.kod) duAccept();
    if (!Z.err && Date.now() - Z.at > 15000) duLoad();
  }
  /* ?duel_kod=<kod> - do'stning taklifini qabul qilish, keyin duel tanishuvi */
  async function duAccept() {
    const Z = S.du, code = Z.kod;
    Z.kod = '';
    if (!code) return;
    Z.note = { k: 'load', t: 'Duel taklifi qabul qilinmoqda' };
    render('same');
    try {
      const r = await api('/api/s/duel/accept', { code });  /* server tomonda idempotent - qayta urinish xavfsiz */
      if (!r.duel || !r.duel.id) throw new ApiErr(500, "So'rov bajarilmadi.");
      Z.note = null; Z.at = 0;
      duPut(r.duel);
      hap('not', 'success');
      if (topS().s === 'duellar') go('duel', { id: r.duel.id });
    } catch (e) {
      Z.note = { k: 'err', t: e.message || NET_MSG };
      hap('not', 'error');
      if (topS().s === 'duellar') render('same');
    }
  }

  /* ---- "Yangi duel" oynasi: tasodifiy raqib yoki do'stni chaqirish (havola, ulashish, nusxa) ---- */
  const invOk = () => { const v = S.du.inv; return v && v.link && tsOf(v.expires_at) > Date.now() + 6e4 ? v : null; };
  function duSheet() {
    const sh = S.du.sh || {}, v = invOk(), lim = S.du.d && S.du.d.limits;
    if (sh.friend && v) {
      return `<span class="dia cta big ld-badge" aria-hidden="true">${ic('user-plus')}</span><h2>Do'stingizni chaqiring</h2><p>Havolani yuboring: do'stingiz uni ochib, duelni qabul qiladi. Keyin ikkalangiz ham o'ynaysiz.</p>
        <div class="du-link"><span class="du-lt" dir="ltr">${esc(v.link)}</span></div>
        <button type="button" class="btn" data-act="duel-share">${ic('share-2')}Ulashish</button><button type="button" class="btn sec" data-act="duel-copy">${ic('copy')}Nusxa olish</button>
        <p class="du-fine">${ic('clock')}<span>Havola ${RU().hours} soat amal qiladi va bir marta ishlatiladi.</span></p>`;
    }
    return `<span class="dia cta big ld-badge" aria-hidden="true">${ic('swords')}</span><h2>Yangi duel</h2><p>Raqibni tanlang: ${RU().savollar} savol, har biriga ${RU().sec} soniya.</p>
      ${sh.err ? `<div class="du-shx" role="alert">${ic('circle-alert')}<span>${T(sh.err)}</span></div>` : ''}
      <div class="nx"><button type="button" class="nx-i" data-act="duel-random">${dia(ic('shuffle'))}<span><b>Tasodifiy raqib</b><small>Faol o'quvchilardan biri</small></span>${ic('chevron-right')}</button>
      <button type="button" class="nx-i" data-act="duel-friend">${dia(ic('user-plus'))}<span><b>Do'stni chaqirish</b><small>Telegram orqali havola yuboring</small></span>${ic('chevron-right')}</button></div>
      ${lim ? `<p class="du-fine">${ic('calendar')}<span>Bugun: ${+lim.today || 0} / ${+lim.daily || 0} ta duel</span></p>` : ''}
      <button type="button" class="btn sec" data-act="sheet-close">Yopish</button>`;
  }
  const duShare = () => `Fonetika kursida duelga chaqiraman: ${RU().savollar} savol, har biriga ${RU().sec} soniya.`;
  function duNewSheet() {
    if (!duelOn()) return;
    S.du.sh = {};
    hap('imp', 'light');
    openSheet(`<div class="ld-card du-sh">${duSheet()}</div>`, 'Yangi duel', 'duel-yangi');
  }
  function duSheetUpd() {
    const s = $('#ovl .du-sh');
    if (!s) return false;
    s.innerHTML = duSheet();
    const f = $('button', s);
    if (f) { try { f.focus({ preventScroll: true }); } catch (e) { /* jim */ } }
    return true;
  }
  let duBusy = false;
  async function duNew(mode, b) {
    if (duBusy) return;
    const Z = S.du;
    if (mode === 'friend' && invOk()) { Z.sh = { friend: true }; duSheetUpd(); return; }
    duBusy = true;
    busy(b, true);
    try {
      const r = await req('/api/s/duel/new', { method: 'POST', body: { mode }, auth: true, retries: 0 });
      if (mode === 'friend') {
        if (!r.link) throw new ApiErr(500, "So'rov bajarilmadi.");
        Z.inv = r; Z.sh = { friend: true };
        hap('not', 'success');
        duSheetUpd();
      } else {
        if (!r.duel || !r.duel.id) throw new ApiErr(500, "So'rov bajarilmadi.");
        duPut(r.duel); Z.at = 0;
        hap('not', 'success');
        go('duel', { id: r.duel.id }, topS().s === 'duellar' ? 'push' : 'replace');
      }
    } catch (e) {
      busy(b, false);
      Z.sh = { err: e.message || NET_MSG };
      hap('not', 'error');
      if (!duSheetUpd()) toast(Z.sh.err, 'err');
    }
    duBusy = false;
  }
  function shareLink(link, text) {
    if (!link) return;
    const u = 'https://t.me/share/url?url=' + encodeURIComponent(link) + (text ? '&text=' + encodeURIComponent(text) : '');
    hap('imp', 'light');
    try { if (tg && tg.openTelegramLink) { tg.openTelegramLink(u); return; } } catch (e) { /* zaxira */ }
    try { W.open(u, '_blank', 'noopener'); } catch (e) { /* jim */ }
  }
  async function copyLink(link, b) {
    if (!link) return;
    let ok = false;
    try { if (W.navigator.clipboard && W.isSecureContext) { await W.navigator.clipboard.writeText(link); ok = true; } } catch (e) { ok = false; }
    if (!ok) {
      try {
        const ta = D.createElement('textarea');
        ta.value = link; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0';
        D.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, link.length);
        ok = D.execCommand('copy');
        ta.remove();
      } catch (e) { ok = false; }
      if (b) { try { b.focus({ preventScroll: true }); } catch (e) { /* jim */ } }
    }
    if (ok) { toast('Havola nusxalandi', 'ok'); hap('not', 'success'); return; }
    /* Nusxa olib bo'lmadi: havola matni belgilanadi - foydalanuvchi o'zi nusxalaydi */
    const el = $$('.du-lt').pop();
    if (el) { try { const r = D.createRange(); r.selectNodeContents(el); const s = W.getSelection(); s.removeAllRanges(); s.addRange(r); } catch (e) { /* jim */ } }
    toast("Havolani belgilab, nusxa oling", 'err');
  }

  /* ---- Duel o'yini: tanishuv -> savollar (15 s halqa) -> yuborish ---- */
  let DU = null, clOn = null;
  const DR = 52, DSW = 5, DRR = (DR - DSW) / 2, DLEN = 2 * Math.PI * DRR;
  const newDu = (id) => {
    const it = S.du.items[id];
    return { id, phase: !it ? 'find' : it.status === 'sizning_navbat' ? 'intro' : 'done', gdl: Infinity, qs: [], i: 0, ans: [], lock: false, qi: -1, qt0: 0, dl: 0, raf: 0, tm: 0, nx: 0, sec: 15, err: null, el: null, ls: -1, red: false };
  };
  function closing(on) {
    if (!tgv('6.2') || clOn === on) return;
    clOn = on;
    try { if (on) tg.enableClosingConfirmation(); else tg.disableClosingConfirmation(); } catch (e) { /* jim */ }
  }
  function duStop(u) { if (u) { cancelAnimationFrame(u.raf); clearTimeout(u.tm); clearTimeout(u.nx); } }
  const duHere = (u) => { const t = topS(); return DU === u && S.phase === 'ready' && !!t && t.s === 'duel' && t.id === u.id; };
  const duTimerHtml = (u) => `<span class="du-tmr" role="timer" aria-label="Qolgan vaqt: ${u.sec} soniya"><svg width="${DR}" height="${DR}" viewBox="0 0 ${DR} ${DR}" aria-hidden="true"><circle class="rt" cx="${DR / 2}" cy="${DR / 2}" r="${DRR}" fill="none" stroke-width="${DSW}"/><circle class="rf" cx="${DR / 2}" cy="${DR / 2}" r="${DRR}" fill="none" stroke-width="${DSW}" stroke-linecap="round" stroke-dasharray="${DLEN.toFixed(2)}" stroke-dashoffset="0" transform="rotate(-90 ${DR / 2} ${DR / 2})"/></svg><b aria-hidden="true">${u.sec}</b></span>`;
  function duelHtml(st) {
    if (!DU || DU.id !== st.id) { duStop(DU); DU = newDu(st.id); }
    const u = DU, it = S.du.items[u.id];
    const top = (lbl, mid) => `<div class="qz-top"><button type="button" class="qz-x" data-act="back" aria-label="${lbl}">${ic('x')}</button>${mid || '<div class="du-tt">Duel</div>'}</div>`;
    const wait = (t, p) => `<div class="qz">${top('Orqaga')}${loadHtml(t, p)}</div>`;
    if (u.phase === 'find' || u.phase === 'done') return wait('Duel yuklanmoqda');
    if (u.phase === 'err') return `<div class="qz">${top('Orqaga')}<div class="qz-body">${errBlock(u.err, 'duel-retry')}</div></div>`;
    if (u.phase === 'send') return wait('Natija yuborilmoqda', 'Bir oz kuting.');
    if (u.phase === 'intro' || u.phase === 'load') {
      const nm = rvName(it), left = it ? leftTxt(it.expires_at) : '', ld = u.phase === 'load', R = RU(), re = !!(it && it.started);
      return `<div class="qz du-iq">${top('Orqaga')}<div class="du-intro">${band()}
        <div class="du-vs2" aria-hidden="true"><span class="ava me">${avatarInner()}</span><span class="du-vsx">${ic('swords')}</span><span class="ava">${esc(ini(nm))}</span></div>
        <div class="kick">${it && it.mode === 'friend' ? "Do'st bilan duel" : 'Duel'}</div><h1 class="du-ih">Siz va ${T(nm)}</h1>
        ${left ? `<p class="du-left">${ic('clock')}${left}</p>` : ''}${it && it.rival_done ? `<p class="du-left">${ic('circle-check')}${T(nm)} allaqachon o'ynadi</p>` : ''}
        <ul class="card du-facts"><li>${dia(ic('list-checks'))}<span><b>${R.savollar} savol</b><small>Ikkalangiz tugatgan darslar testlaridan</small></span></li>
        <li>${dia(ic('timer'))}<span><b>Har biriga ${R.sec} soniya</b><small>Javobni bossangiz, keyingi savolga o'tadi</small></span></li>
        <li>${dia(ic('trophy'))}<span><b>Ko'proq to'g'ri javob yutadi</b><small>Teng bo'lsa, tezroq javob bergan${ballOn() ? `. G'olibga +${R.xp_win} ball, durrangda +${R.xp_draw}` : ''}</small></span></li></ul>
        <p class="du-warn">${ic('info')}<span>${re ? "Duel avval boshlangan: vaqt to'xtamaydi, qolgan savollarga tezroq javob bering." : 'Boshlaganingizdan keyin chiqib ketsangiz, qolgan savollar javobsiz hisoblanadi.'}</span></p></div>
        <div class="qz-foot"><button type="button" class="btn" data-act="duel-start" data-v="${esc(u.id)}"${ld ? ' disabled aria-busy="true"' : ''}>${ld ? ic('loader-circle', 'spin') : ic('play')}${re ? 'Davom etish' : 'Boshlash'}</button></div></div>`;
    }
    const n = u.qs.length, i = Math.min(u.i, n - 1), Q = u.qs[i], done = u.ans.filter(Boolean).length;
    const bar = `<div class="qz-bar" role="progressbar" aria-label="Duel jarayoni" aria-valuemin="0" aria-valuemax="${n}" aria-valuenow="${done}"><span style="width:${(100 * done / n).toFixed(1)}%"></span></div>${duTimerHtml(u)}`;
    const grid = Q.opts.every((o) => String(o).length <= 14);
    const opts = Q.opts.map((o, k) => `<button type="button" class="qz-o" data-act="duel-pick" data-i="${k}" aria-pressed="false"><span class="qz-ol" aria-hidden="true">${'ABCD'.charAt(k) || k + 1}</span><span class="qz-ot">${T(o)}</span></button>`).join('');
    const who = it ? `<div class="du-who">${ic('swords')}<span>${T(rvName(it))} bilan · ${it.mode === 'friend' ? "do'st dueli" : 'tasodifiy duel'}</span></div>` : '';
    return `<div class="qz du-q">${top('Dueldan chiqish', bar)}<div class="qz-body du-in">${band()}${who}<div class="kick">${i + 1}-savol · ${n} tadan${Q.dars ? ' · ' + (+Q.dars) + '-dars' : ''}</div><h1 class="qz-q">${T(Q.q)}</h1><div class="qz-opts ${grid ? 'grid' : 'list'}" role="group" aria-label="Javob variantlari">${opts}</div><p class="du-to" role="status" hidden>${ic('timer')}Vaqt tugadi</p></div></div>`;
  }
  function mountDuel(st, box) {
    const u = DU;
    if (!u || u.id !== st.id) return;
    if (u.phase === 'find') { duFind(u); return; }
    if (u.phase === 'done') { DU = null; go('duel-natija', { id: u.id }, 'replace'); if (u.msg) toast(u.msg, 'err'); return; }
    if (u.phase !== 'play') return;
    if (u.qi !== u.i) { u.qi = u.i; u.lock = false; u.qt0 = performance.now(); u.dl = Math.min(u.qt0 + u.sec * 1000, u.gdl); u.red = reduced(); }
    const tm = $('.du-tmr', box);
    u.el = tm ? { box: tm, rf: $('.rf', tm), b: $('b', tm) } : null;
    u.ls = -1;
    duTick(u);
  }
  /* ?duel=<id> yoki noma'lum holat: GET /api/s/duel, keyin navbat bo'yicha o'yin (tanishuv) yoki natija */
  async function duFind(u) {
    let err = null;
    try { await duGet(u.id); } catch (e) { err = e; }
    if (!duHere(u)) return;
    const it = S.du.items[u.id];
    if (!it) {
      S.du.note = { k: 'err', t: err && err.st !== 404 ? err.message || NET_MSG : "Duel topilmadi. U muddati ancha oldin tugagan bo'lishi mumkin." };
      DU = null;
      openDuellar(true);
      return;
    }
    u.phase = it.status === 'sizning_navbat' ? 'intro' : 'done';
    render('same');
  }
  /* Halqa: rAF bilan silliq; yashirin oynada rAF to'xtaydi - zaxira taymer vaqt tugashini baribir ushlaydi */
  function duTick(u) {
    duStop(u);
    const step = () => {
      if (DU !== u || u.phase !== 'play' || u.lock) return false;
      const left = u.dl - performance.now();
      duRing(u, left);
      if (left <= 0) { duPick(null); return false; }
      return true;
    };
    const fr = () => { if (step()) u.raf = requestAnimationFrame(fr); };
    const bk = () => { if (step()) u.tm = setTimeout(bk, clamp(u.dl - performance.now() + 10, 20, 1000)); };
    fr();
    u.tm = setTimeout(bk, 250);
  }
  function duRing(u, left) {
    const e = u.el;
    if (!e || !e.rf) return;
    const s = clamp(Math.ceil(left / 1000), 0, u.sec), f = u.red ? s / u.sec : clamp(left / (u.sec * 1000), 0, 1);
    e.rf.style.strokeDashoffset = (DLEN * (1 - f)).toFixed(2);
    if (s === u.ls) return;
    u.ls = s;
    e.b.textContent = s;
    e.box.classList.toggle('low', s <= 5);
    e.box.setAttribute('aria-label', 'Qolgan vaqt: ' + s + ' soniya');
  }
  /* Javob (k) yoki vaqt tugashi (k = null): qulflanadi, qisqa belgi, ~0.6 s dan keyin keyingi savol */
  function duPick(k) {
    const u = DU;
    if (!u || u.phase !== 'play' || u.lock || !u.qs[u.i]) return;
    const t = performance.now(), to = k == null || !(k >= 0 && k < u.qs[u.i].opts.length), full = u.sec * 1000;
    u.lock = true;
    duStop(u);
    u.ans[u.i] = { pick: to ? null : k, ms: to ? full : clamp(Math.round(t - u.qt0), 0, full) };
    if (duHere(u)) {
      const box = $('#scr');
      $$('.qz-o', box).forEach((o) => {
        const me = !to && +o.getAttribute('data-i') === k;
        o.disabled = true;
        o.classList.add(me ? 'sel' : 'dim');
        if (me) o.setAttribute('aria-pressed', 'true');
      });
      const bar = $('.qz-bar', box), done = u.ans.filter(Boolean).length;
      if (bar) { bar.setAttribute('aria-valuenow', done); $('span', bar).style.width = (100 * done / u.qs.length).toFixed(1) + '%'; }
      if (to) { duRing(u, 0); const p = $('.du-to', box); if (p) p.hidden = false; }
    }
    hap(to ? 'not' : 'sel', to ? 'error' : undefined);
    u.nx = setTimeout(() => duNext(u), to ? 900 : 600);
  }
  function duNext(u) {
    if (DU !== u || u.phase !== 'play') return;
    if (u.i >= u.qs.length - 1 || performance.now() >= u.gdl) { duFinish(u); return; }
    u.i += 1;
    if (duHere(u)) { render('same'); W.scrollTo(0, 0); } else duTick(u);
  }
  async function duStart(b) {
    const u = DU;
    if (!u || u.phase !== 'intro') return;
    u.phase = 'load';
    busy(b, true);
    try {
      const r = await api('/api/s/duel/start', { id: u.id });
      const qs = (Array.isArray(r.questions) ? r.questions : []).filter((q) => q && q.q != null && Array.isArray(q.opts) && q.opts.length);
      if (!qs.length) throw new ApiErr(500, 'Savollar yuklanmadi.');
      if (DU !== u) return;
      /* left_ms - butun duel uchun qolgan vaqt (start idempotent: qayta ochilganda kamroq); 1.5 s zaxira tarmoq uchun */
      const sec = clamp(+r.sec || 15, 5, 60), left = r.left_ms == null ? null : Math.max(0, +r.left_ms || 0);
      Object.assign(u, { qs, sec, i: 0, qi: -1, ans: [], lock: false, phase: 'play', gdl: left == null ? Infinity : performance.now() + left - 1500 });
      if (left != null && left < 2500) { duFinish(u); return; }
      if (left != null && left < sec * 1000 * qs.length) toast(`Duel avval boshlangan. Qolgan vaqt: ${Math.round(left / 1000)} soniya`);
      closing(true);
      hap('imp', 'medium');
    } catch (e) {
      if (DU !== u) return;
      /* 409 - allaqachon o'ynalgan, 410 - muddati o'tgan, 404 - topilmadi: holat qayta so'raladi (natija yoki Duellar) */
      if (e.st === 404 || e.st === 409 || e.st === 410) { if (e.st === 410) u.msg = e.message; u.phase = 'find'; S.du.at = 0; } else { u.phase = 'intro'; toast(e.message || NET_MSG, 'err'); hap('not', 'error'); }
    }
    if (duHere(u)) render('same');
  }
  function duAskQuit() {
    openSheet(`<div class="ld-card du-sh"><span class="dia big lk ld-badge" aria-hidden="true">${ic('log-out')}</span><h2>Dueldan chiqasizmi?</h2><p>Qolgan savollar javobsiz hisoblanadi va natija shu holatda yuboriladi.</p><button type="button" class="btn" data-act="sheet-close">Davom etish</button><button type="button" class="btn sec du-quit" data-act="duel-quit">${ic('log-out')}Chiqish</button></div>`, 'Dueldan chiqish', 'duel-chiqish', DU.id);
  }
  function duQuit() {
    const u = DU;
    closeSheet(true);
    if (!u || u.phase !== 'play') return;
    if (!u.lock) { u.lock = true; u.ans[u.i] = { pick: null, ms: u.sec * 1000 }; }
    duFinish(u);
  }
  function duFill(u) {
    const n = u.qs.length;
    for (let k = 0; k < n; k++) if (!u.ans[k]) u.ans[k] = { pick: null, ms: u.sec * 1000 };
    u.ans.length = n;
    return u.ans;
  }
  async function duFinish(u) {
    if (!u || u.phase === 'send') return;
    duFill(u);
    u.phase = 'send'; u.lock = true;
    duStop(u); closing(false);
    if (duHere(u)) render('same');
    try {
      const r = await req('/api/s/duel/finish', { method: 'POST', body: { id: u.id, answers: u.ans }, auth: true });
      if (r.duel) duPut(r.duel);
      S.du.at = 0;
      if (Array.isArray(r.review) && r.review.length) S.du.rev[u.id] = r.review;
      S.du.gt[u.id] = Date.now();
      const xp = +r.xp_added || 0;
      S.du.fin[u.id] = { xp };
      if (xp && S.me) { const s = S.me.stats; s.xp = (s.xp || 0) + xp; s.today_xp = (s.today_xp || 0) + xp; updStats(); }
      hap('not', r.duel && r.duel.result === 'yutqazdi' ? 'error' : 'success');
      const h = duHere(u);
      if (DU === u) DU = null;
      if (h) go('duel-natija', { id: u.id }, 'replace'); else toast('Duel natijasi yuborildi', 'ok');
    } catch (e) {
      if (e.st === 409 || e.st === 410) {
        S.du.at = 0;
        try { await duGet(u.id); } catch (x) { /* natija ekrani o'zi qayta so'raydi */ }
        const h = duHere(u);
        if (DU === u) DU = null;
        if (h) go('duel-natija', { id: u.id }, 'replace');
        return;
      }
      u.phase = 'err'; u.err = e;
      if (duHere(u)) render('same'); else toast(e.message || NET_MSG, 'err');
    }
  }
  function leaveDuel() {
    const u = DU;
    if (!u) return;
    duStop(u); closing(false);
    if (u.phase === 'play') { duFinish(u); return; }
    if (u.phase !== 'send' && u.phase !== 'err') DU = null;
  }
  /* Ilova yopilsa (pagehide) o'yin o'rtasida: qolgan savollar javobsiz, keepalive bilan yuboriladi */
  function duBeacon() {
    const u = DU;
    if (!u || u.phase !== 'play' || PREVIEW) return;
    try {
      W.fetch('/api/s/duel/finish', { method: 'POST', keepalive: true, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-Init-Data': INIT }, body: JSON.stringify({ id: u.id, answers: duFill(u) }) });
      u.phase = 'send'; duStop(u);
    } catch (e) { /* jim */ }
  }

  /* ---- Duel natijasi ---- */
  function duResHtml(st) {
    const Z = S.du, it = Z.items[st.id];
    if (!it) {
      const ge = Z.gerr[st.id];
      const body = !ge ? loadHtml('Natija yuklanmoqda')
        : ge.st === 404 ? emptyHtml('circle-help', 'Duel topilmadi', "Bu duel mavjud emas yoki siz unda qatnashmagansiz.", true) : errBlock(ge, 'duel-retry');
      return topbar('Duel natijasi', 'Duel') + `<div class="du">${body}</div>`;
    }
    const nm = rvName(it), my = it.my, th = it.their, rev = Z.rev[it.id] || null, N = +it.n || (rev && rev.length) || RU().savollar;
    const k = it.status === 'tugadi' ? (it.result === 'yutdi' ? 'won' : it.result === 'yutqazdi' ? 'lost' : 'draw') : it.status === 'muddati_otdi' ? 'exp' : 'wait';
    const hd = { won: ['Yutdingiz!', ic('trophy')], lost: ['Yutqazdingiz', ic('target')], draw: ['Durrang', ic('equal')], exp: ["Muddati o'tdi", ic('clock')], wait: ['Natija kutilmoqda', ic('hourglass')] }[k];
    const fin = Z.fin[it.id], xp = fin ? fin.xp : +it.xp || 0;
    const fxc = !Z.cu[it.id] || Date.now() - Z.cu[it.id] < 1500, side = (me, name, sc, ava, win) => `<div class="du-p${win ? ' win' : ''}">${win ? `<span class="du-crown">${ic('crown')}</span>` : ''}<span class="ava${me ? ' me' : ' op'}">${ava}</span><b>${name}${win ? sr(" - g'olib") : ''}</b><span class="du-sc">${sc ? `<em data-to="${+sc.correct || 0}">${+sc.correct || 0}</em><small>/${N}</small>` : '?'}</span><small>${sc ? secTxt(sc.ms) : me ? "o'ynalmadi" : k === 'wait' ? "hali o'ynamadi" : "o'ynamadi"}</small></div>`;
    let note = '';
    if (my && my.late) note = "Javoblar kech yuborildi, shuning uchun hisoblanmadi. ";
    if (k === 'wait') note += "Raqib hali o'ynamadi — natija kelganda bot xabar beradi.";
    else if (k === 'exp') note += my ? `Raqib ${RU().hours} soat ichida o'ynamadi. Bu duel uchun ball berilmaydi.` : `Duel ${RU().hours} soat ichida o'ynalmadi.`;
    else if (my && th && my.correct === th.correct && k !== 'draw') note = "To'g'ri javoblar teng — tezroq javob bergan yutdi.";
    const rows = rev ? rev.map((r, i) => {
      const none = r.pick == null, good = typeof r.togri === 'boolean' ? r.togri : !none && r.pick === r.ok;
      const meta = [+r.dars ? r.dars + '-dars' : '', !none && r.ms != null ? secTxt(r.ms) : ''].filter(Boolean).join(' · ');
      return `<div class="rs-row" style="--i:${i}"><div class="rs-q"><small>${i + 1}-savol · <span class="du-rk ${good ? 'ok' : 'no'}">${good ? ic('check') : ic('x')}${good ? "to'g'ri" : none ? 'javob berilmadi' : 'xato'}</span>${meta ? `<span class="du-rm"> · ${esc(meta)}</span>` : ''}</small>${T(r.q)}</div>${none ? '' : `<div class="${good ? 'rs-r' : 'rs-a'}">Sizning javobingiz: ${T((r.opts || [])[r.pick])}</div>`}${good ? '' : `<div class="rs-r">To'g'ri javob: ${T((r.opts || [])[r.ok])}</div>`}${r.izoh ? `<p class="du-iz">${T(r.izoh)}</p>` : ''}</div>`;
    }).join('') : '';
    const canNew = !Z.d || Z.d.can !== false;
    return `<div class="rs du-res${fxc ? ' fx' : ''}${rows && !Z.cr[it.id] ? ' rfx' : ''}">${heroCard(hd[1], '', hd[0], `${T(nm)} bilan · ${it.mode === 'friend' ? "do'st dueli" : 'tasodifiy duel'}`, 'rs-hero du-rh ' + k, 'h1')}
      <div class="card du-vs">${side(true, 'Siz', my, avatarInner(), k === 'won')}<span class="du-x" aria-hidden="true">${ic('swords')}</span>${side(false, T(nm), th, esc(ini(nm)), k === 'lost')}</div>
      ${ballOn() && xp > 0 ? `<span class="xp-pill">${ic('gem')}+${xp} ball</span>` : ''}
      ${note ? `<p class="rs-note du-nt">${note}</p>` : ''}
      ${rows ? `<section class="card rs-mis du-rev"><h2>${ic('list-checks')}Javoblaringiz</h2>${rows}</section>` : my && (Z.gl[it.id] || (!Z.gerr[it.id] && !Z.gt[it.id])) ? `<div class="du-sk" role="status" aria-label="Javoblar yuklanmoqda">${skb(220)}</div>` : ''}
      <div class="rs-acts${canNew ? '' : ' one'}">${canNew ? `<button type="button" class="btn sec" data-act="duel-new">${ic('swords')}Yangi duel</button>` : ''}<button type="button" class="btn" data-act="duel-open">Duellarga qaytish</button></div></div>`;
  }
  function mountDuelRes(st) {
    const Z = S.du, id = st.id, it = Z.items[id];
    if (Z.rev[id]) Z.cr[id] = 1;
    if (it && (!Z.cu[id] || Date.now() - Z.cu[id] < 1500)) {
      if (!Z.cu[id]) Z.cu[id] = Date.now();
      if (!reduced()) $$('.du-res .du-sc em[data-to]').forEach((e) => {
        const to = +e.dataset.to || 0, t0 = performance.now(), dur = 700;
        if (!to) return;
        e.textContent = '0';
        (function tick(t) {
          const k = Math.min(1, (t - t0) / dur), v = Math.round(to * (1 - Math.pow(1 - k, 3)));
          e.textContent = v;
          if (k < 1) W.requestAnimationFrame(tick);
        })(t0);
      });
    }
    if (Z.gerr[id] || Z.gl[id] || Date.now() - (Z.gt[id] || 0) < 15000) return;
    if (!it || (it.my && !Z.rev[id]) || it.status === 'raqib_navbati') duRes(id);
  }
  async function duRes(id) {
    const Z = S.du;
    Z.gl[id] = true;
    try { await duGet(id); } catch (e) { Z.gerr[id] = e; }
    Z.gl[id] = false;
    const t = topS();
    if (S.phase === 'ready' && !S.ob && t && t.s === 'duel-natija' && t.id === id) render('same');
  }

  /* ---- Do'stlarni taklif qilish ---- */
  async function tkLoad() {
    const Z = S.tk;
    if (Z.busy) return;
    Z.busy = true;
    try {
      const r = await api('/api/s/taklif');
      r.friends = Array.isArray(r.friends) ? r.friends.filter(Boolean) : [];
      Z.d = r; Z.at = Date.now(); Z.err = null;
    } catch (e) { if (!Z.d) Z.err = e; }
    Z.busy = false;
    const t = topS();
    if (S.phase === 'ready' && !S.ob && t && t.s === 'taklif') render('same');
  }
  function taklifHtml() {
    const Z = S.tk, d = Z.d, b = ballOn();
    let h = topbar("Do'stlarni taklif qilish", 'Taklif') + '<div class="du tk">';
    if (!d) return h + (Z.err ? `<div class="card du-ec">${errBlock(Z.err, 'taklif-retry')}</div>` : `<div class="du-sk" role="status" aria-label="Yuklanmoqda">${skb(168, '20px')}${skb(170)}${skb(160)}</div>`) + '</div>';
    const bon = +d.bonus || 50, fr = d.friends, dn = Math.max(fr.filter((f) => f.done1 || f.rewarded).length, +d.rewarded || 0), tot = d.invited != null ? +d.invited || 0 : fr.length;
    h += heroCard(ic('gift'), b ? 'Taklif bonusi' : 'Birga o\'rganamiz', b ? `+${bon} ball` : "Do'stlaringizni taklif qiling", b ? "Do'stingiz 1-darsni tugatganda sizga ham, unga ham." : "Shaxsiy havolangizni do'stlaringizga yuboring.", 'tk-ban');
    h += `<section class="card tk-link"><h2 class="tk-h">Shaxsiy havolangiz</h2><div class="du-link"><span class="du-lt" dir="ltr">${esc(d.link || '')}</span></div><button type="button" class="btn" data-act="taklif-share">${ic('share-2')}Ulashish</button><button type="button" class="btn sec" data-act="taklif-copy">${ic('copy')}Nusxa olish</button></section>`;
    const sts = [['fr', ic('users'), tot, "qo'shilgan"], ['d1', ic('book-check'), dn, '1-darsni tugatgan']].concat(b ? [['xp', ic('gem'), '+' + num(d.earned || 0), 'ball topildi']] : []);
    h += `<div class="du-stats" style="--n:${sts.length}">${sts.map((x) => `<div class="card du-st ${x[0]}">${x[1]}<b>${x[2]}</b><small>${x[3]}</small></div>`).join('')}</div>`;
    h += `<h2 class="sec-h">Qanday ishlaydi</h2><ol class="card tk-steps"><li><span>1</span>Havolani do'stingizga yuboring</li><li><span>2</span>Do'stingiz bot orqali kursga qo'shiladi</li><li><span>3</span>${b ? `U 1-darsni tugatganda ikkalangizga +${bon} ball` : "Darslarni birga o'tasiz"}</li></ol>`;
    h += `<h2 class="sec-h">Do'stlaringiz${fr.length ? `<small>${fr.length} ta</small>` : ''}</h2>`;
    h += fr.length ? `<div class="card du-list">${fr.map((f) => {
      const done = f.done1 || f.rewarded;
      return `<div class="du-row tk-row"><span class="ava" aria-hidden="true">${esc(ini(f.name))}</span><span class="du-rt"><b>${T(f.name || "Do'st")}</b>${done ? `<span class="dpill won">${ic('circle-check')}1-darsni tugatdi${b && f.rewarded ? ` +${bon}` : ''}</span>` : `<span class="dpill wait">${ic('user-check')}Qo'shildi</span>`}${f.joined_at ? `<small>${ic('calendar')}${esc(whenTxt(f.joined_at, true))}</small>` : ''}</span></div>`;
    }).join('')}</div>` : `<div class="card du-empty">${emptyHtml('users', "Hali hech kim qo'shilmadi", "Havolani yuboring — qo'shilgan do'stlaringiz shu yerda ko'rinadi.", true)}</div>`;
    return h + '</div>';
  }

  /* ================= 9c. Qo'llanma (3-bosqich) =================
     Matnlar egasi tasdiqlagan loyihadan so'zma-so'z (Qo'llanmalar/Ilova qo'llanmasi va video ssenariysi - loyiha.html, A1-A10, B1-B2).
     O'chirilgan funksiya haqidagi bo'lim/qator ko'rsatilmaydi; data-i - bo'limning doimiy raqami (1..10). Ro'yxat: [sarlavha, ikon, matn, shart]. */
  /* ikonlar: send house footprints presentation list-checks circle-play trophy swords gift settings book-open-text lock-open gem */
  const QG = [
    ['Ilovani ochish', 'send', "@FonetikaOquvchilar_bot ga kiring va «Darslarni ochish» tugmasini bosing. Hech narsa yuklab olish shart emas — ilova Telegram ichida ochiladi. Botdagi buyruqlar: /darslar, /video, /yordam."],
    ['Bosh sahifa', 'house', "Bu yerda keyingi darsingiz, kunlik maqsad va seriyangiz turadi. Kunlik maqsad — 30 ball. Har kuni kamida bitta ball olsangiz, seriya o'sadi; bir kun o'tkazib yuborsangiz, qaytadan boshlanadi."],
    ['Darslar — zinapoya', 'footprints', "36 dars to'rt qismga bo'lingan. Darslar zinapoyaga o'xshaydi: har pog'onaga avvalgisidan o'tib chiqiladi. Bitta darsni tugatsangiz, keyingisi ochiladi. Qulf belgisi bor dars hali yopiq."],
    ['Dars ichida', 'presentation', "Dars — jonli taqdimot. Keyingi slaydga o'tish uchun ekranni o'ngdan chapga suring yoki o'q tugmasini bosing. Slaydlarning kamida 80 foizini ko'rsangiz, dars tugaydi. Ba'zi darslarda «Kitob betlari» ham bor — darslikning o'sha sahifalari."],
    ['Mashq — mini test', 'list-checks', "Har dars tugagach, shu mavzu bo'yicha 5 savollik mashq ochiladi. Javobni tanlab «Tekshirish»ni bosing: to'g'ri javob va qisqa izoh chiqadi. Beshta yurak — besh imkoniyat; yuraklar tugasa, mavzuni yana bir ko'rib, qaytadan urinasiz.", () => feat('test')],
    ['Video darslar', 'circle-play', "Video darslar alohida bo'limda va dars sahifasida turadi. Qayerda to'xtagan bo'lsangiz, keyingi safar o'sha joydan davom etadi. Oxirigacha ko'rilgan video +30 ball beradi.", () => feat('video')],
    ['Ball va reyting', 'trophy', "Har yangi slayd — 1 ball, tugatilgan dars — 20, oxirigacha ko'rilgan video — 30, testdagi har to'g'ri javob — 4 ball (birinchi marta hammasi to'g'ri bo'lsa yana 10). Reytingda haftalik va umumiy natijalar ko'rinadi; hafta dushanba kuni yangilanadi.", () => ballOn()],
    ['Duel', 'swords', "Duel — bilim bellashuvi. Do'stingizni yoki tasodifiy raqibni chaqiring: 5 savol, har biriga 15 soniya. Savollar faqat ikkalangiz ham tugatgan darslardan olinadi. Ko'p to'g'ri javob bergan yutadi, teng bo'lsa — tezroq javob bergan. G'olibga 15 ball, durrangda har biriga 5 ball. Raqib 24 soat ichida javob beradi; natija tayyor bo'lganda bot xabar yuboradi.", () => duelOn()],
    ["Do'stlarni taklif qilish", 'gift', "Profil yoki Bosh sahifadagi «Taklif qilish» bo'limida shaxsiy havolangiz bor. Uni do'stingizga yuboring. Do'stingiz birinchi darsni tugatsa, sizga ham, unga ham 50 ball beriladi.", () => taklifOn()],
    ['Profil va sozlamalar', 'settings', "Profilda ilova ko'rinishini (o'yinli yoki shisha uslub), rejimni (kunduzgi, tungi yoki Telegram bilan bir xil) va arabcha matn o'lchamini o'zgartirasiz. Har kuni soat 19:00 da kichik eslatma keladi — xohlasangiz, shu yerda o'chirib qo'yasiz."],
  ];
  /* Tanishuvning qo'shimcha qadamlari: [sarlavha, katta ikon, [[ikon, qator, shart], ...]] - qatorlar raqami ko'rinadiganlar bo'yicha */
  const OBX = {
    qanday: ["Qanday o'qiladi", 'book-open-text', [['presentation', "Darsni oching va slaydlarni ko'ring."], ['list-checks', 'Dars oxirida 5 savollik mashqni yeching.', () => feat('test')], ['lock-open', 'Darslar ketma-ket ochiladi — har kuni bittadan.']]],
    ball: ["Ball, duel va do'stlar", 'trophy', [['gem', 'Kuniga 30 ball — kunlik maqsad.', () => ballOn()], ['swords', "Duelda do'stingiz bilan bellashing.", () => duelOn()], ['gift', "Do'st taklif qiling — ikkalangizga 50 ball.", () => taklifOn()]]],
  };
  const obLines = (k) => OBX[k][2].filter((x) => !x[2] || x[2]());
  const qgVis = () => QG.map((x, k) => [k + 1, x]).filter((p) => !p[1][3] || p[1][3]());
  let QO = new Set([1]);
  function qollanmaHtml() {
    const vis = qgVis();
    const it = vis.map(([i, x]) => {
      const on = QO.has(i);
      return `<section class="qg-it${on ? ' on' : ''}"><h2><button type="button" class="qg-b" id="qg-b${i}" data-act="qollanma-bolim" data-i="${i}" aria-expanded="${on}" aria-controls="qg-p${i}"><span class="dia qg-ic" aria-hidden="true">${ic(x[1])}</span><span class="qg-t">${T(x[0])}</span>${ic('chevron-down', 'qg-ch')}</button></h2><div class="qg-p" id="qg-p${i}" role="region" aria-labelledby="qg-b${i}"${on ? '' : ' hidden'}><p>${T(x[2])}</p></div></section>`;
    }).join('');
    return topbar("Qo'llanma", 'Yordam') + `<div class="du qg">${heroCard(ic('book-open'), vis.length + " ta bo'lim", "Ilovadan foydalanish qo'llanmasi", '', 'qg-ban')}<div class="card qg-list">${it}</div></div>`;
  }
  /* Bo'limni ochish/yopish: qayta chizilmaydi (fokus va aylantirish joyida qoladi) */
  function qgToggle(b) {
    const i = +A(b, 'data-i'), on = b.getAttribute('aria-expanded') !== 'true', p = D.getElementById('qg-p' + i), s = b.closest('.qg-it');
    if (on) QO.add(i); else QO.delete(i);
    b.setAttribute('aria-expanded', String(on));
    if (p) p.hidden = !on;
    if (s) s.classList.toggle('on', on);
    hap('sel');
  }
  const qgLink = () => (qgOn() ? `<button type="button" class="card qg-link" data-act="qollanma-open">${dia(ic('book-open'))}<span class="qg-t"><b>Qo'llanma</b><small>Ilovadan foydalanish qo'llanmasi</small></span>${ic('chevron-right', 'qg-ch')}</button>` : '');

  /* ================= 10. Ekranlar jadvali va harakatlar ================= */
  const SCR = {
    bosh: { tab: true, html: boshHtml },
    darslar: { tab: true, html: darslarHtml, mount: mountDarslar },
    video: { tab: true, html: videoHtml },
    reyting: { tab: true, html: reytingHtml, mount: mountReyting },
    profil: { tab: true, html: profilHtml },
    dars: {
      html: (st) => (L(st.n) && L(st.n).taqdimot ? deckHtml(st) : viewerHtml(st)),
      mount: (st, box) => (L(st.n) && L(st.n).taqdimot ? mountDeck(st, box) : mountViewer(st, box)),
      leave: () => { leaveDeck(); leaveViewer(); }, noSwipe: true, full: true, live: true,
    },
    kitob: { html: viewerHtml, mount: mountViewer, leave: leaveViewer, noSwipe: true, full: true, live: true },
    player: { html: playerHtml, mount: mountPlayer, leave: leavePlayer, live: true },
    mashq: { html: quizHtml, noSwipe: true },
    natija: { html: resultHtml },
    duellar: { html: duellarHtml, mount: mountDuellar, leave: () => { S.du.note = null; } },
    duel: { html: duelHtml, mount: mountDuel, leave: leaveDuel, noSwipe: true },
    'duel-natija': { html: duResHtml, mount: mountDuelRes, leave: (st) => { delete S.du.gerr[st.id]; delete S.du.cu[st.id]; delete S.du.cr[st.id]; } },
    taklif: { html: taklifHtml, mount: () => { const Z = S.tk; if (!Z.err && Date.now() - Z.at > 30000) tkLoad(); } },
    qollanma: { html: qollanmaHtml },
  };
  function openLesson(n, how) {
    const d = L(n);
    if (!d) return;
    if (!avail(n)) { denyLesson(n); return; }
    hap('imp', 'light');
    go('dars', { n }, how);
  }
  const A = (b, k) => b.getAttribute(k);
  const ACT = {
    tab(b) {
      let v = A(b, 'data-v');
      if (S.ob || S.phase !== 'ready' || !SCR[v] || !SCR[v].tab) return;
      if (!tabOn(v)) v = 'bosh';
      closeSheet(true);
      hap('imp', 'light');
      if (S.stack.length === 1 && topS().s === v) { W.scrollTo({ top: 0, behavior: reduced() ? 'auto' : 'smooth' }); return; }
      go(v, null, 'tab');
    },
    back() { back(); },
    lesson(b) { closeSheet(true); openLesson(+A(b, 'data-n'), A(b, 'data-how')); },
    video(b) {
      closeSheet(true);
      const id = A(b, 'data-v'), x = vidOf(id);
      if (!x) return;
      if (!avail(x.d.n)) { denyLesson(x.d.n); return; }
      hap('imp', 'light');
      go('player', { vid: id }, A(b, 'data-how'));
    },
    vids(b) { showVids(+A(b, 'data-n')); },
    /* Darslar: qismni ochish/yopish (joriy qism doim ochiq) */
    qism(b) {
      const n = +A(b, 'data-n');
      if (!S.qOpen) S.qOpen = new Set();
      if (S.qOpen.has(n)) S.qOpen.delete(n); else S.qOpen.add(n);
      hap('sel');
      render('same');
    },
    'sheet-close'() { closeSheet(); },
    quiz(b) { closeSheet(true); startQuiz(+A(b, 'data-n'), A(b, 'data-how')); },
    pick(b) { qzPick(+A(b, 'data-i')); },
    'qz-check'() { qzCheck(); },
    'qz-next'(b) { qzNext(b); },
    'qz-restart'() { if (S.quiz) { S.quiz = newQuiz(S.quiz.n); render('same'); W.scrollTo(0, 0); } },
    'qz-retry'(b) { startQuiz(+A(b, 'data-n'), 'replace'); },
    'test-retry'() { const t = topS(); if (t && t.n) { S.testErr[t.n] = null; render('same'); loadTest(t.n); } },
    'vw-prev'() { vwStep(-1); },
    'vw-next'() { vwStep(1); },
    'vw-go'(b) { vwGo(+A(b, 'data-i')); },
    'vw-finish'(b) { vwFinish(b); },
    'vw-zoom'() { openZoom(); },
    'zm-s'(b) { setZoom(+A(b, 'data-v')); },
    'zm-close'() { closeZoom(); },
    'hint-ok'() { hideHint(); dkHint(); },
    'dk-prev'() { dkStep(-1); },
    'dk-next'() { dkStep(1); },
    'dk-finish'(b) { dkFinish(b); },
    'dk-fs'() { dkFs(); },
    'dk-reload'() { if (DK) dkLoad(DK.st.i || resumeIdx(DK.n)); },
    kitob(b) {
      const n = +A(b, 'data-n'), d = L(n);
      if (!d || !kitobOf(d).length) return;
      hap('imp', 'light');
      go('kitob', { n });
    },
    davr(b) {
      const v = A(b, 'data-v');
      if (S.rating.davr === v) return;
      S.rating.davr = v; S.rating.err = null;
      hap('sel');
      render('same');
    },
    'rating-retry'() { S.rating.err = null; render('same'); },
    /* Ko'rinish: manzara (data-i), aylanish (data-v = yangi holat on/off), rejim, arabcha matn */
    'set-manzara'(b) {
      const v = A(b, 'data-i');
      if (!feat('uslub') || V.indexOf(v) < 0 || (v === NQ.v && !NQ.a)) return;
      hap('sel');
      setManzara(v);
      render('same');
    },
    'set-aylanish'(b) {
      if (!feat('uslub')) return;
      const on = A(b, 'data-v') === 'on';
      hap('sel');
      setAylan(on);
      render('same');
      toast(on ? 'Manzara har ochilganda almashadi' : 'Manzara: ' + VN[NQ.v], 'ok');
    },
    'set-rejim'(b) { const v = A(b, 'data-v'); if (v === S.prefs.rejim) return; hap('sel'); setPrefs({ rejim: v }); render('same'); },
    'set-arab'(b) { const v = A(b, 'data-v'); if (v === S.prefs.arab) return; hap('sel'); setPrefs({ arab: v }); render('same'); },
    'set-esl'(b) {
      const on = S.prefs.eslatma === false;
      hap('sel');
      setPrefs({ eslatma: on });
      b.setAttribute('aria-checked', String(on));
      toast(on ? 'Kunlik eslatma yoqildi' : "Kunlik eslatma o'chirildi", 'ok');
    },
    'ob-next'() { if (S.ob && S.ob < obSteps().length) { S.ob += 1; hap('imp', 'light'); renderOb(); } },
    'ob-done'() {
      if (!S.ob) return;
      S.ob = 0; obShown = 0;
      hap('not', 'success');
      obMark();
      route();
    },
    'ob-skip'() { ACT['ob-done'](); },
    /* Qo'llanma (3-bosqich): har ochilishda birinchi bo'lim ochiq */
    'qollanma-open'() { if (!qgOn()) return; closeSheet(true); hap('imp', 'light'); QO = new Set([1]); if (topS().s !== 'qollanma') go('qollanma'); },
    'qollanma-bolim'(b) { qgToggle(b); },
    retry() { load(); },
    'sheet-bg'(b, e) { if (e.target === b) closeSheet(); },
    /* Duel va taklif (SPEC 11.4). duel-open: data-v = duel id (o'yin yoki natija); bo'lmasa - Duellar ekrani */
    'duel-open'(b) { closeSheet(true); const id = A(b, 'data-v'); if (id) openDuel(id); else openDuellar(); },
    'duel-new'() { duNewSheet(); },
    'duel-random'(b) { duNew('random', b); },
    'duel-friend'(b) { duNew('friend', b); },
    'duel-share'() { const v = invOk(); if (v) shareLink(v.link, v.share_text || duShare()); },
    'duel-copy'(b) { const v = invOk(); if (v) copyLink(v.link, b); },
    'duel-start'(b) { duStart(b); },
    'duel-pick'(b) { duPick(+A(b, 'data-i')); },
    'duel-quit'() { duQuit(); },
    'duel-retry'() {
      const t = topS();
      if (t && t.s === 'duel' && DU && DU.phase === 'err') { DU.phase = 'play'; duFinish(DU); return; }
      if (t && t.s === 'duel-natija') { delete S.du.gerr[t.id]; S.du.gt[t.id] = 0; }
      S.du.err = null;
      render('same');
    },
    'taklif-open'() { if (!taklifOn()) return; closeSheet(true); hap('imp', 'light'); if (topS().s !== 'taklif') go('taklif'); },
    'taklif-share'() { const d = S.tk.d; if (d) shareLink(d.link, d.share_text); },
    'taklif-copy'(b) { const d = S.tk.d; if (d) copyLink(d.link, b); },
    'taklif-retry'() { S.tk.err = null; render('same'); },
  };
  /* Kuzatuv: bitta umumiy tutuvchi (capture) - harakat bajarilishidan oldin, joriy ekran bilan yoziladi */
  D.addEventListener('click', trClick, true);
  D.addEventListener('click', (e) => {
    const b = e.target && e.target.closest ? e.target.closest('[data-act]') : null;
    if (!b || b.disabled) return;
    const f = ACT[b.getAttribute('data-act')];
    if (f) f(b, e);
  });
  D.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (S.zoom || sheetOpen() || (DK && DK.fs) || S.ob > 1 || (S.phase === 'ready' && S.stack.length > 1)) { e.preventDefault(); back(); }
      return;
    }
    if (DK && !sheetOpen() && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      e.preventDefault();
      dkStep(e.key === 'ArrowLeft' ? -1 : 1);
      return;
    }
    if (VW && !S.zoom && !sheetOpen() && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      e.preventDefault();
      vwStep(e.key === 'ArrowLeft' ? -1 : 1);
    }
  });

  /* ================= 11. Ishga tushirish ================= */
  /* Telegram bulutidagi sozlamalar: rejim va arabcha matn (server javobidan oldin), manzara tanlovi, tanishuv belgisi */
  let CLP = Promise.resolve(null);
  function cloudPrefs() {
    CLP = cloud.get(['rejim', 'arab', 'nq_manzara', 'nq_aylan', 'nq_ob']);
    CLP.then((v) => {
      if (!v) return;
      if (v.nq_ob === '1') ls.set(KOB, true);
      nqCloud(v);
      if (S.phase !== 'boot') return;
      const p = {};
      if (v.rejim === 'auto' || v.rejim === 'light' || v.rejim === 'dark') p.rejim = v.rejim;
      if (v.arab === 'm' || v.arab === 'l') p.arab = v.arab;
      if (!Object.keys(p).length) return;
      Object.assign(S.prefs, p);
      savePrefsLocal();
      applyTheme();
    });
  }
  /* Server sozlamalari asosiy (rejim, arab, eslatma). "uslub" serverda eski qiymati bilan qoladi: u bo'lsa -
     foydalanuvchi tanishuvni avval o'tgan (ilova endi uslub yubormaydi). */
  function mergePrefs(sp) {
    sp = sp || {};
    const loc = ls.get(KP, {}) || {};
    S.prefs = { uslub: sp.uslub || null, rejim: sp.rejim || loc.rejim || 'auto', arab: sp.arab || loc.arab || 'm', eslatma: sp.eslatma !== false };
    savePrefsLocal();
    applyTheme();
  }
  function route() {
    let tab = START.tab;
    if (!tab || TABS.indexOf(tab) < 0 || !tabOn(tab)) tab = 'bosh';
    const n = START.dars, du = START.duel, kod = START.kod;
    START.tab = null; START.dars = 0; START.duel = ''; START.kod = '';
    S.stack = [{ s: tab }];
    if (n && L(n)) {
      if (avail(n)) S.stack.push({ s: 'dars', n });
      else setTimeout(() => toast(lockMsg(n)), 400);
    } else if ((du || kod) && duelOn()) {
      /* ?duel=<id> - o'sha duel (navbatim bo'lsa o'yin, aks holda natija); ?duel_kod=<kod> - taklifni qabul qilish */
      S.stack = [{ s: 'bosh' }, { s: 'duellar' }];
      if (du) S.stack.push({ s: 'duel', id: du }); else S.du.kod = kod;
    }
    cur = null;
    render('tab');
  }
  function prefetch() { const c = curN(), d = L(c); if (testOf(d) && !S.tests[c]) loadTest(c); }
  async function load() {
    S.phase = 'boot';
    S.err = null;
    renderSkeleton();
    let res;
    try {
      res = await Promise.all([getJSON('/content/kurs.json'), PREVIEW ? null : api('/api/s/me', {}), SPR ? inlineSprite() : null]);
      if (!res[0] || !Array.isArray(res[0].darslar) || !res[0].darslar.length) throw new ApiErr(500, "Kurs ma'lumotlari topilmadi.");
    } catch (e) {
      S.phase = 'error';
      S.err = e instanceof ApiErr ? e : new ApiErr(0, NET_MSG);
      renderError();
      return;
    }
    S.K = res[0];
    indexK();
    if (!Array.isArray(S.K.qismlar) || !S.K.qismlar.length) S.K.qismlar = [{ n: 1, nomi: S.K.nomi || 'Darslar', darslar: S.K.darslar.map((d) => d.n) }];
    S.me = normalizeMe(PREVIEW ? demoMe() : res[1]);
    TR.on = !PREVIEW && !!S.me.features && typeof S.me.features === 'object';
    if (!TR.on) TR.q = [];
    mergePrefs(S.me.prefs);
    nqFeat();
    /* Tanishuv: serverda uslub yo'q va qurilmada/bulutda tanishuv belgisi yo'q bo'lsa */
    let ob = !S.prefs.uslub && !ls.get(KOB, false);
    if (ob) { const c = await CLP; if (c && c.nq_ob === '1') { ls.set(KOB, true); ob = false; } }
    S.phase = 'ready';
    prefetch();
    flush();
    if (ob) startOb(); else route();
  }
  function boot() {
    try { if (tg) { tg.ready(); tg.expand(); } } catch (e) { /* jim */ }
    S.prefs = Object.assign(S.prefs, ls.get(KP, {}) || {});
    applyTheme(true);
    if (tgv('6.1')) { try { tg.BackButton.onClick(() => { trSync(); trPush('click', 'tg-back', '', TR.cur); back(); }); } catch (e) { /* jim */ } }
    if (tg && tg.onEvent) {
      try { tg.onEvent('fullscreenChanged', onTgFs); } catch (e) { /* jim */ }
      /* Telegram 8.0+: ilova yig'ilganda / qayta ochilganda (visibilitychange bo'lmasligi mumkin) */
      try { tg.onEvent('deactivated', trHide); tg.onEvent('activated', trShow); } catch (e) { /* jim */ }
    }
    D.addEventListener('fullscreenchange', onDocFs);
    D.addEventListener('webkitfullscreenchange', onDocFs);
    W.addEventListener('online', () => { flush(); });
    D.addEventListener('visibilitychange', () => {
      if (D.visibilityState === 'hidden') { if (PL) savePos(true); flush(); trHide(); } else { trShow(); applyTheme(); }
    });
    W.addEventListener('pagehide', () => { duBeacon(); trHide(); });
    W.addEventListener('pageshow', (e) => { if (e.persisted) trShow(); });
    if (!PREVIEW) setInterval(() => trFlush(), 1e4);
    /* Avto rejim: soat 06:00 va 19:00 da ochiq ilova ham almashadi */
    setInterval(() => { if (rejimNow() === 'auto') applyTheme(); }, 6e4);
    let rzT = 0;
    W.addEventListener('resize', () => { clearTimeout(rzT); rzT = setTimeout(() => paintScenes(D), 150); });
    D.addEventListener('error', (e) => {
      const t = e.target;
      if (t && t.tagName === 'IMG' && t.getAttribute('data-ini')) t.replaceWith(D.createTextNode(t.getAttribute('data-ini')));
    }, true);
    cloudPrefs();
    load();
  }
  boot();
})();

/* ============================================================
   Muhammadamin — demo panellar adapteri
   Server /staff/p/*.html ga </body> oldidan ulaydi (SPEC 6.3). Panel fayllari o'zgarmaydi.
   - Telegram: ready/expand, ranglar #EAF4EA, BackButton -> /staff/, "Chiqish" -> close
   - ?t= token sessionStorage (noon_x) da saqlanadi; rol menyusi faqat foydalanuvchi panellari
   - brend nomi; ?rejim=lms (Admin_paneli: faqat LMS guruhi), ?rejim=assistent (Ustoz_paneli: qulflangan)
   Hech qachon xato tashlamaydi: har bir qadam try/catch ichida.
   ============================================================ */
(function () {
  'use strict';
  if (window.__noonAdapter) return;
  window.__noonAdapter = true;

  var KEY = 'noon_x';
  var BG = '#EAF4EA';
  var HOME = '/staff/';
  var FILES = { ceo: 'CEO_paneli.html', admin: 'Admin_paneli.html', lms: 'Admin_paneli.html', ustoz: 'Ustoz_paneli.html', assistent: 'Ustoz_paneli.html' };
  var NAMES = { ceo: 'CEO paneli', admin: 'Admin paneli', lms: 'LMS paneli', ustoz: 'Ustoz paneli', assistent: 'Assistent paneli' };
  var ROLE_PANELS = { ceo: ['ceo', 'admin', 'lms', 'ustoz'], admin: ['admin', 'lms'], ustoz: ['ustoz', 'lms'], assistent: ['assistent'] };
  var URL_OK = /^\/staff\/p\/[A-Za-z_]+\.html(\?|$)/;

  function safe(fn) { try { return fn(); } catch (e) { return undefined; } }

  /* ---------- muhit ---------- */
  var tg = safe(function () { return window.Telegram && window.Telegram.WebApp; }) || null;
  function ver(v) { return !!safe(function () { return tg && tg.isVersionAtLeast && tg.isVersionAtLeast(v); }); }
  var inTg = !!safe(function () { return tg && (tg.initData || (tg.platform && tg.platform !== 'unknown')); });
  var qs = safe(function () { return new URLSearchParams(location.search); }) || null;
  function q(name) { return (qs && safe(function () { return qs.get(name); })) || ''; }
  var file = safe(function () { return decodeURIComponent(location.pathname.split('/').pop() || ''); }) || '';
  var rejim = q('rejim').toLowerCase();
  var tq = q('t');

  /* ---------- token va saqlangan ma'lumot ---------- */
  function readStore() { return safe(function () { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); }) || {}; }
  function writeStore(v) { safe(function () { sessionStorage.setItem(KEY, JSON.stringify(v)); }); }
  var st = readStore();
  if (tq && st.token !== tq) { st.token = tq; writeStore(st); }
  var token = tq || st.token || '';

  function tokenRole(t) {
    return safe(function () {
      var p = String(t).split('.')[0].replace(/-/g, '+').replace(/_/g, '/');
      while (p.length % 4) p += '=';
      var j = JSON.parse(atob(p));
      return j && typeof j.role === 'string' ? j.role : '';
    }) || '';
  }
  var role = tokenRole(token) || st.role || '';
  function keys() {
    var ps = Array.isArray(st.panels) ? st.panels : [];
    var k = ps.map(function (p) { return p && p.key; }).filter(Boolean);
    return k.length ? k : (ROLE_PANELS[role] || []);
  }
  var K = keys();
  var isCeo = /^CEO_paneli\.html$/i.test(file);
  var isAdmin = /^Admin_paneli\.html$/i.test(file);
  var isUstoz = /^Ustoz_paneli\.html$/i.test(file);
  /* rejim: URL dagi ?rejim= yoki rolning o'zi (ustozda "admin" yo'q -> LMS; assistentda "ustoz" yo'q -> assistent) */
  var lms = isAdmin && (rejim === 'lms' || (K.length > 0 && K.indexOf('admin') < 0 && K.indexOf('lms') >= 0));
  var asst = isUstoz && (rejim === 'assistent' || (K.length > 0 && K.indexOf('ustoz') < 0 && K.indexOf('assistent') >= 0));
  var curKey = isCeo ? 'ceo' : isAdmin ? (lms ? 'lms' : 'admin') : isUstoz ? (asst ? 'assistent' : 'ustoz') : '';

  function toast(m) { safe(function () { window.Panel.toast(m); }); }
  function goHome() {
    safe(function () { if (ver('6.1')) tg.BackButton.hide(); });
    location.href = HOME;
  }

  /* ---------- 1. Telegram ---------- */
  function tgSetup() {
    if (!tg) return;
    safe(function () { tg.ready(); });
    safe(function () { tg.expand(); });
    safe(function () { if (ver('6.9')) tg.setHeaderColor(BG); });
    safe(function () { if (ver('6.1')) tg.setBackgroundColor(BG); });
    safe(function () { if (ver('7.10')) tg.setBottomBarColor(BG); });
    safe(function () { if (ver('6.1')) { tg.BackButton.onClick(goHome); tg.BackButton.show(); } });
  }

  /* ---------- 2. Uslub qo'shimchalari ---------- */
  function injectStyle() {
    if (document.getElementById('noon-adapter-css')) return;
    var css = '' +
      '.side-foot .nav-item[data-noon-back] .ni{color:var(--acc,#1A6A2A)}' +
      '.toasts{bottom:calc(24px + env(safe-area-inset-bottom,0px))}' +
      (asst ? '.mode-sw{display:none!important}' : '');
    var s = document.createElement('style');
    s.id = 'noon-adapter-css';
    s.textContent = css;
    (document.head || document.documentElement).appendChild(s);
  }

  /* ---------- 3. Brend ---------- */
  function brand() {
    var b = document.querySelector('#side .brand b') || document.querySelector('.brand b');
    if (b) b.textContent = st.brend || 'Muhammadamin';
    if (lms) {
      var sm = document.querySelector('#side .brand small');
      if (sm) sm.textContent = 'LMS paneli';
    }
  }

  /* ---------- 4. Rol (panel) menyusi ---------- */
  function shortName(p) { return String((p && (p.nomi || NAMES[p.key])) || '').replace(/\s+paneli$/i, '') || 'Panel'; }
  function panelList() {
    var ps = Array.isArray(st.panels) ? st.panels.filter(function (p) { return p && typeof p.url === 'string' && URL_OK.test(p.url); }) : [];
    if (!ps.length && token) {
      ps = (ROLE_PANELS[role] || []).map(function (k) {
        var extra = k === 'lms' ? 'rejim=lms&' : k === 'assistent' ? 'rejim=assistent&' : '';
        return { key: k, nomi: NAMES[k], url: '/staff/p/' + FILES[k] + '?' + extra + 't=' + encodeURIComponent(token) };
      });
    }
    return ps.filter(function (p) { return !/Noon_ilova_demo|Rollar_demo/i.test(p.url); });
  }
  function roleSelect() {
    var sel = document.getElementById('roleSel');
    if (!sel) return;
    var ps = panelList();
    while (sel.firstChild) sel.removeChild(sel.firstChild);
    var found = false;
    ps.forEach(function (p) {
      var o = document.createElement('option');
      o.value = p.url;
      o.textContent = shortName(p);
      if (p.key === curKey && !found) { o.selected = true; found = true; }
      sel.appendChild(o);
    });
    if (!found && curKey) {
      var o = document.createElement('option');
      o.value = location.pathname + location.search;
      o.textContent = shortName({ key: curKey });
      o.selected = true;
      sel.insertBefore(o, sel.firstChild);
    }
    sel.setAttribute('aria-label', 'Panelni almashtirish');
    var wrap = sel.closest ? sel.closest('.role-sw') : null;
    if (wrap) {
      var lab = wrap.querySelector('.rs-lab');
      if (lab) lab.textContent = 'Panel:';
      wrap.hidden = sel.options.length <= 1;
    }
  }

  /* ---------- 5. "Chiqish" va "Boshqaruvga qaytish" ---------- */
  function exitItem() {
    window.addEventListener('click', function (e) {
      var t = e.target && e.target.closest ? e.target.closest('.side-foot .nav-item') : null;
      if (!t || t.hasAttribute('data-noon-back')) return;
      if ((t.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase() !== 'chiqish') return;
      e.preventDefault();
      e.stopPropagation();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      if (inTg && tg && tg.close) safe(function () { tg.close(); });
      else goHome();
    }, true);
  }
  function backItem() {
    var foot = document.querySelector('#side .side-foot');
    if (!foot || foot.querySelector('[data-noon-back]')) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'nav-item';
    b.setAttribute('data-noon-back', '');
    b.innerHTML = '<span class="ni"><i data-lucide="arrow-left"></i></span><span>Boshqaruvga qaytish</span>';
    b.addEventListener('click', function (e) { e.preventDefault(); goHome(); });
    var items = foot.querySelectorAll('.nav-item');
    var exit = null;
    for (var i = 0; i < items.length; i++) if (/chiqish/i.test(items[i].textContent || '')) exit = items[i];
    if (exit) foot.insertBefore(b, exit); else foot.appendChild(b);
  }

  /* ---------- 6. LMS rejimi (Admin_paneli.html?rejim=lms) ---------- */
  function lmsMode() {
    var P = window.Panel, cfg = P && P.cfg;
    if (!cfg || !Array.isArray(cfg.nav) || typeof P.go !== 'function') return;
    var norm = function (s) { return String(s || '').replace(/\s+/g, ' ').trim().toLowerCase(); };
    var g = null;
    cfg.nav.forEach(function (x) { if (!g && x && norm(x.group) === 'lms') g = x; });
    if (!g || !g.items || !g.items.length) return;
    var ids = g.items.map(function (i) { return i.id; });
    var other = {};
    cfg.nav.forEach(function (x) { if (x !== g) (x.items || []).forEach(function (i) { other[i.id] = true; }); });
    var groups = document.querySelectorAll('#side .nav-group');
    for (var i = 0; i < groups.length; i++) {
      var lab = groups[i].querySelector('.ng-lab');
      if (!lab || norm(lab.textContent) !== 'lms') groups[i].hidden = true;
    }
    cfg.roleName = 'LMS paneli';
    safe(function () { document.title = String(document.title).replace(/Admin paneli\s*$/, 'LMS paneli'); });
    if (Array.isArray(cfg.notifications)) {
      cfg.notifications = cfg.notifications.filter(function (n) { return !n || !n.go || ids.indexOf(n.go) >= 0; });
      if (!cfg.notifications.length) { var d = document.querySelector('[data-bell] .dot'); if (d) d.remove(); }
    }
    var orig = P.go, first = ids[0], lastOk = null;
    var hiddenOn = function () {
      var on = document.querySelector('#side .nav-item.on[data-go]');
      var grp = on && on.closest ? on.closest('.nav-group') : null;
      return !!(grp && grp.hidden);
    };
    P.go = function (id, noAnim) {
      if (other[id]) { toast("LMS panelida bu bo'lim yo'q"); return undefined; }
      var r = orig.apply(P, arguments);
      if (hiddenOn()) {
        orig.call(P, lastOk || first, true);
        toast("LMS panelida bu bo'lim yo'q");
      } else lastOk = P.current;
      return r;
    };
    var cur = P.current;
    if (!cur || other[cur] || (ids.indexOf(cur) < 0 && hiddenOn())) P.go(first, true);
    else lastOk = cur;
  }

  /* ---------- 7. Assistent rejimi (Ustoz_paneli.html?rejim=assistent) ---------- */
  function asstMode() {
    var P = window.Panel, cfg = P && P.cfg;
    if (!P || !cfg || !cfg.screens || typeof P.go !== 'function') return;
    var isA = function (id) { return /^a-/.test(String(id || '')); };
    var orig = P.go;
    P.go = function (id, noAnim) {
      if (!isA(id)) {
        var alt = 'a-' + id;
        if (cfg.screens[alt]) id = alt;
        else { toast("Assistent rejimida bu bo'lim yopiq"); return undefined; }
      }
      return orig.call(P, id, noAnim);
    };
    window.addEventListener('click', function (e) {
      var b = e.target && e.target.closest ? e.target.closest('.mode-sw button, [data-act="mode"]') : null;
      if (b && b.getAttribute('data-mode') !== 'asst') {
        e.preventDefault();
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      }
    }, true);
    if (!isA(P.current)) P.go('a-home', true);
    var sw = document.querySelectorAll('.mode-sw');
    for (var i = 0; i < sw.length; i++) { sw[i].hidden = true; sw[i].setAttribute('aria-hidden', 'true'); }
  }

  /* ---------- 8. noon_x bo'lmasa: token bilan panellar ro'yxatini olish ---------- */
  function refreshStore() {
    if (Array.isArray(st.panels) && st.panels.length) return;
    var h = { 'Content-Type': 'application/json' };
    if (token) h['X-Staff-Token'] = token;
    else if (tg && tg.initData) h['X-Init-Data'] = tg.initData;
    else return;
    safe(function () {
      fetch('/api/x/auth', { method: 'POST', headers: h, body: '{}', cache: 'no-store', credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (a) {
          if (!a || !Array.isArray(a.panels)) return;
          st.token = a.token || token;
          st.panels = a.panels;
          st.brend = a.brend || st.brend;
          st.role = a.role || st.role;
          writeStore(st);
          safe(brand);
          safe(roleSelect);
        })
        .catch(function () { /* jim */ });
    });
  }

  /* ---------- ishga tushirish: panel tayyor bo'lgach ---------- */
  function adapt() {
    safe(injectStyle);
    safe(brand);
    safe(roleSelect);
    safe(exitItem);
    safe(backItem);
    if (lms) safe(lmsMode);
    if (asst) safe(asstMode);
    safe(function () { if (window.Panel && window.Panel.icons) window.Panel.icons(); });
    safe(refreshStore);
    safe(function () { document.documentElement.setAttribute('data-noon-adapter', curKey || 'ok'); });
  }
  function whenReady(cb) {
    var n = 0;
    var ready = function () { return !!(window.Panel && window.Panel.cfg && document.getElementById('side')); };
    (function wait() {
      if (ready() || n++ > 200) { safe(cb); return; }
      setTimeout(wait, 25);
    })();
  }

  safe(tgSetup);
  whenReady(adapt);
})();

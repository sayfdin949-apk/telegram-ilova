/* Telegram WebApp soxta obyekti — FAQAT sinov uchun (Playwright: page.add_init_script).
   Oldin window.__TG_MOCK = { initData, user, colorScheme: 'light'|'dark', version: '8.0', platform } berish mumkin.
   Haqiqiy telegram-web-app.js so'rovini sinovda bloklang (route.abort), aks holda u bu obyektni almashtiradi.
   Chaqiruvlar window.Telegram.WebApp.__calls da yig'iladi (sinovda tekshirish uchun). */
(function () {
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.__mock) return;
  const cfg = window.__TG_MOCK || {};
  const listeners = {};
  const store = Object.assign({}, cfg.cloud || {});
  const calls = [];
  const rec = (name, ...args) => calls.push([name, ...args]);
  const scheme = cfg.colorScheme === 'dark' ? 'dark' : 'light';
  const themeParams = scheme === 'dark'
    ? { bg_color: '#17212b', text_color: '#f5f5f5', hint_color: '#708499', link_color: '#6ab3f3', button_color: '#5288c1', button_text_color: '#ffffff', secondary_bg_color: '#232e3c' }
    : { bg_color: '#ffffff', text_color: '#000000', hint_color: '#999999', link_color: '#2481cc', button_color: '#2481cc', button_text_color: '#ffffff', secondary_bg_color: '#efeff3' };
  const version = String(cfg.version || '8.0');
  const cmp = (a, b) => {
    const pa = String(a).split('.').map(Number), pb = String(b).split('.').map(Number);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const x = pa[i] || 0, y = pb[i] || 0;
      if (x !== y) return x > y ? 1 : -1;
    }
    return 0;
  };
  const emit = (ev, ...args) => (listeners[ev] || []).slice().forEach((f) => { try { f(...args); } catch (e) { console.error(e); } });
  const on = (ev, f) => { (listeners[ev] = listeners[ev] || []).push(f); };
  const off = (ev, f) => { listeners[ev] = (listeners[ev] || []).filter((x) => x !== f); };
  const button = (name) => ({
    text: '', color: '#2481cc', textColor: '#ffffff', isVisible: false, isActive: true, isProgressVisible: false,
    setText(t) { this.text = t; rec(name + '.setText', t); return this; },
    show() { this.isVisible = true; rec(name + '.show'); return this; },
    hide() { this.isVisible = false; rec(name + '.hide'); return this; },
    enable() { this.isActive = true; return this; }, disable() { this.isActive = false; return this; },
    showProgress() { this.isProgressVisible = true; return this; }, hideProgress() { this.isProgressVisible = false; return this; },
    setParams(p) { Object.assign(this, p || {}); rec(name + '.setParams', p); return this; },
    onClick(f) { on(name + 'Clicked', f); return this; }, offClick(f) { off(name + 'Clicked', f); return this; },
  });
  const WebApp = {
    __mock: true, __calls: calls, __store: store,
    __emit: emit,
    initData: cfg.initData || '',
    initDataUnsafe: cfg.initData ? { user: cfg.user || null, auth_date: Math.floor(Date.now() / 1000) } : {},
    version, platform: cfg.platform || 'android', colorScheme: scheme, themeParams,
    isExpanded: true, viewportHeight: window.innerHeight, viewportStableHeight: window.innerHeight,
    isFullscreen: false, isVerticalSwipesEnabled: true, isClosingConfirmationEnabled: false,
    headerColor: themeParams.bg_color, backgroundColor: themeParams.bg_color, bottomBarColor: themeParams.bg_color,
    safeAreaInset: { top: 0, bottom: 0, left: 0, right: 0 }, contentSafeAreaInset: { top: 0, bottom: 0, left: 0, right: 0 },
    isVersionAtLeast(v) { return cmp(version, v) >= 0; },
    ready() { rec('ready'); }, expand() { rec('expand'); }, close() { rec('close'); },
    setHeaderColor(c) { this.headerColor = c; rec('setHeaderColor', c); },
    setBackgroundColor(c) { this.backgroundColor = c; rec('setBackgroundColor', c); },
    setBottomBarColor(c) { this.bottomBarColor = c; rec('setBottomBarColor', c); },
    enableVerticalSwipes() { this.isVerticalSwipesEnabled = true; rec('enableVerticalSwipes'); },
    disableVerticalSwipes() { this.isVerticalSwipesEnabled = false; rec('disableVerticalSwipes'); },
    enableClosingConfirmation() { this.isClosingConfirmationEnabled = true; }, disableClosingConfirmation() { this.isClosingConfirmationEnabled = false; },
    requestFullscreen() { this.isFullscreen = true; rec('requestFullscreen'); emit('fullscreenChanged'); },
    exitFullscreen() { this.isFullscreen = false; rec('exitFullscreen'); emit('fullscreenChanged'); },
    lockOrientation() { rec('lockOrientation'); }, unlockOrientation() { rec('unlockOrientation'); },
    onEvent: on, offEvent: off,
    sendData(d) { rec('sendData', d); },
    openLink(u, o) { rec('openLink', u, o); }, openTelegramLink(u) { rec('openTelegramLink', u); },
    openInvoice(u, cb) { rec('openInvoice', u); cb && cb('cancelled'); },
    showAlert(m, cb) { rec('showAlert', m); cb && setTimeout(cb, 0); },
    showConfirm(m, cb) { rec('showConfirm', m); cb && setTimeout(() => cb(true), 0); },
    showPopup(p, cb) { rec('showPopup', p); cb && setTimeout(() => cb((p && p.buttons && p.buttons[0] && p.buttons[0].id) || 'ok'), 0); },
    readTextFromClipboard(cb) { cb && cb(''); },
    downloadFile(p, cb) { rec('downloadFile', p); cb && setTimeout(() => cb(true), 0); },
    shareToStory() {}, switchInlineQuery(q) { rec('switchInlineQuery', q); },
    BackButton: {
      isVisible: false,
      show() { this.isVisible = true; rec('BackButton.show'); return this; },
      hide() { this.isVisible = false; rec('BackButton.hide'); return this; },
      onClick(f) { on('backButtonClicked', f); return this; }, offClick(f) { off('backButtonClicked', f); return this; },
    },
    MainButton: button('mainButton'), SecondaryButton: button('secondaryButton'),
    SettingsButton: { isVisible: false, show() { this.isVisible = true; return this; }, hide() { this.isVisible = false; return this; }, onClick(f) { on('settingsButtonClicked', f); return this; }, offClick(f) { off('settingsButtonClicked', f); return this; } },
    HapticFeedback: {
      impactOccurred(s) { rec('haptic.impact', s); return this; },
      notificationOccurred(s) { rec('haptic.notification', s); return this; },
      selectionChanged() { rec('haptic.selection'); return this; },
    },
    CloudStorage: {
      setItem(k, v, cb) { store[k] = String(v); rec('cloud.set', k, String(v)); cb && setTimeout(() => cb(null, true), 0); },
      getItem(k, cb) { cb && setTimeout(() => cb(null, k in store ? store[k] : ''), 0); },
      getItems(ks, cb) { const o = {}; ks.forEach((k) => { o[k] = k in store ? store[k] : ''; }); cb && setTimeout(() => cb(null, o), 0); },
      removeItem(k, cb) { delete store[k]; cb && setTimeout(() => cb(null, true), 0); },
      removeItems(ks, cb) { ks.forEach((k) => delete store[k]); cb && setTimeout(() => cb(null, true), 0); },
      getKeys(cb) { cb && setTimeout(() => cb(null, Object.keys(store)), 0); },
    },
  };
  /* sinovda: WebApp.__emit('backButtonClicked') — orqaga tugmasini bosish; __setScheme('dark') — Telegram mavzusi o'zgarishi */
  WebApp.__setScheme = (s) => { WebApp.colorScheme = s === 'dark' ? 'dark' : 'light'; emit('themeChanged'); };
  window.Telegram = { WebApp };
})();

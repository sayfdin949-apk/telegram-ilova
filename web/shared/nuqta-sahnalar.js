/* NUQTA UI manzaralari (nuqta-ui skill: assets/nuqta-sahnalar.js nusxasi; arabcha <text> ga dir/lang qo'shilgan). Talaba ilovasi: /shared/nuqta-sahnalar.js */
/* NUQTA — orqa fon sahnalari (SVG).
   scene(nom, w, h, {s, focus, night}) -> <svg> qatori.
   Qoidalar: faqat och/o'rta tonlar, qora yo'q, pushti yo'q; diniy belgi yo'q (masjid, minora, hilol, chiroq).
   Tunda: quyosh o'rniga to'lin oy (hilol EMAS), yulduzlar, yonib turgan derazalar, ranglar oy nurida xiralashadi. */
(function (G) {
  const R = n => Math.round(n * 10) / 10;
  let NIGHT = false;
  const h2r = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const r2h = a => '#' + a.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('').toUpperCase();
  const mix = (a, b, t) => { const A = h2r(a), B = h2r(b); return r2h(A.map((v, i) => v + (B[i] - v) * t)); };
  const K = hex => NIGHT ? mix(hex, '#56607E', .34) : hex;      // tunda oy nuri tusi
  const MOON = '#F1E8CC', STAR = '#F4EDD6', GLOW = '#EEC26A';
  function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  const diamond = (cx, cy, r, c, op = 1) =>
    `<polygon points="${R(cx)},${R(cy - r)} ${R(cx + r)},${R(cy)} ${R(cx)},${R(cy + r)} ${R(cx - r)},${R(cy)}" fill="${c}" opacity="${op}"/>`;
  const circle = (cx, cy, r, c, op = 1) => `<circle cx="${R(cx)}" cy="${R(cy)}" r="${R(r)}" fill="${c}" opacity="${op}"/>`;
  function stars(w, h, top, n, seed) {
    const rnd = rng(seed); let o = '';
    for (let i = 0; i < n; i++) {
      const x = rnd() * w, y = rnd() * h * top, r = .8 + rnd() * 1.6;
      o += i % 5 === 0 ? diamond(x, y, r * 1.9, STAR, .9) : circle(x, y, r, STAR, .55 + rnd() * .4);
    }
    return o;
  }
  /* kunduz — quyosh; tun — to'lin oy (hilol emas) + yorug'lik halqasi */
  function orb(cx, cy, r, dayC) {
    if (!NIGHT) return circle(cx, cy, r, dayC);
    return circle(cx, cy, r * 1.7, MOON, .16) + circle(cx, cy, r * 1.3, MOON, .22) + circle(cx, cy, r * .82, MOON);
  }

  function duneCoords(w, h, t) { return [[0, h * (t + .06)], [w * .22, h * (t - .1)], [w * .42, h * (t + .18)], [w * .62, h * t]]; }
  function duneY(w, h, t, x) {
    const [p0, p1, p2, p3] = duneCoords(w, h, t); let best = p0[1], bd = 1e9;
    for (let i = 0; i <= 120; i++) {
      const u = i / 120, v = 1 - u;
      const bx = v * v * v * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u * u * u * p3[0];
      const by = v * v * v * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u * u * u * p3[1];
      if (Math.abs(bx - x) < bd) { bd = Math.abs(bx - x); best = by; }
    }
    return best;
  }
  function dunes(w, h, t, cols) {
    const P = (a, b, c, d, e, f) => `M0 ${R(h * a)} C ${R(w * .22)} ${R(h * b)}, ${R(w * .42)} ${R(h * c)}, ${R(w * .62)} ${R(h * d)} S ${R(w * .9)} ${R(h * e)}, ${w} ${R(h * f)} L ${w} ${h} L 0 ${h} Z`;
    return [
      `<path d="${P(t + .06, t - .1, t + .18, t, t - .08, t + .02)}" fill="${K(cols[0])}"/>`,
      `<path d="${P(t + .22, t + .12, t + .32, t + .2, t + .12, t + .22)}" fill="${K(cols[1])}"/>`,
      `<path d="${P(t + .36, t + .3, t + .44, t + .34, t + .28, t + .36)}" fill="${K(cols[2])}"/>`];
  }

  const CAMEL = "M14 30 C18 18 26 14 34 12 C38 6 44 4 48 8 C52 12 56 20 60 22 C66 24 70 18 72 10 C73 6 78 4 84 6 C88 7 89 10 86 11 C82 12 78 12 76 14 C74 20 72 28 66 34 C64 38 63 40 62 42 L63 68 L59 68 L58 46 L56 46 L56 68 L52 68 L52 44 C46 44 34 44 28 42 L28 68 L24 68 L22 46 L20 46 L19 68 L15 68 L16 40 C13 38 12 34 14 30 Z";
  function camel(x, y, s, c) {
    c = K(c);
    return `<g transform="translate(${R(x)} ${R(y - 68 * s)}) scale(${s}) translate(-50 0)"><path d="${CAMEL}" fill="${c}"/><path d="M14 31 C9 35 9 41 11 46" stroke="${c}" stroke-width="2.4" fill="none" stroke-linecap="round"/></g>`;
  }
  function caravan(w, h, t, x0, s, c, n = 3, gap = 66) {
    let o = '';
    for (let i = 0; i < n; i++) { const x = x0 + i * gap * s; o += camel(x, duneY(w, h, t, x) + 3 * s, s * (1 - i * .06), c); }
    return o;
  }
  function palm(x, y, s, tc, lc, dc) {
    tc = K(tc); lc = K(lc); dc = dc && K(dc);
    const H = 150 * s, tx = x + 16 * s, ty = y - H;
    let o = `<path d="M${R(x - 6 * s)} ${R(y)} C ${R(x - 4 * s)} ${R(y - H * .5)}, ${R(tx - 6 * s)} ${R(ty + H * .25)}, ${R(tx - 3 * s)} ${R(ty)} L ${R(tx + 3 * s)} ${R(ty)} C ${R(tx)} ${R(ty + H * .25)}, ${R(x + 6 * s)} ${R(y - H * .5)}, ${R(x + 7 * s)} ${R(y)} Z" fill="${tc}"/>`;
    for (let i = 1; i < 10; i++) {
      const u = i / 10, yy = y - H * u, xx = x + (tx - x) * u * u;
      o += `<path d="M${R(xx - 5 * s)} ${R(yy)} q ${R(5 * s)} ${R(3 * s)} ${R(10 * s)} 0" stroke="${lc}" stroke-width="${R(1.4 * s)}" fill="none" opacity=".35"/>`;
    }
    if (dc) for (let i = 0; i < 5; i++) o += circle(tx - 6 * s + i * 3 * s, ty + 8 * s + (i % 2) * 4 * s, 3.4 * s, dc);
    for (const a of [-172, -148, -120, -95, -62, -34, -8]) {
      const len = (a === -95 ? 50 : 76) * s, rad = a * Math.PI / 180;
      const ex = tx + Math.cos(rad) * len, ey = ty + Math.sin(rad) * len + len * .45;
      const mx = (tx + ex) / 2, my = (ty + ey) / 2 - len * .32;
      const d = Math.hypot(ex - tx, ey - ty) || 1, nx = -(ey - ty) / d, ny = (ex - tx) / d, wv = 10 * s;
      o += `<path d="M${R(tx)} ${R(ty)} Q ${R(mx + nx * wv)} ${R(my + ny * wv)} ${R(ex)} ${R(ey)} Q ${R(mx - nx * wv * .25)} ${R(my - ny * wv * .25)} ${R(tx)} ${R(ty)} Z" fill="${lc}"/>`;
    }
    return o;
  }
  function tuft(x, y, s, c) {
    return `<path d="M${R(x)} ${R(y)} q ${R(-6 * s)} ${R(-10 * s)} ${R(-10 * s)} ${R(-12 * s)} M${R(x)} ${R(y)} q ${R(1 * s)} ${R(-12 * s)} 0 ${R(-16 * s)} M${R(x)} ${R(y)} q ${R(6 * s)} ${R(-9 * s)} ${R(11 * s)} ${R(-11 * s)}" stroke="${K(c)}" stroke-width="${R(2.2 * s)}" fill="none" stroke-linecap="round"/>`;
  }
  /* Eski shahar: tekis tomli uylar, shamol tutgich (bodgir), mashrabiya, ko'k eshiklar. Tunda derazalar yonadi. */
  function city(w, gy, s, xs) {
    const C = { wall: ['#DCC59B', '#D2B886', '#E4D2AE'].map(K), win: NIGHT ? GLOW : '#B79A69', mash: K('#C4A472'), door: K('#6E9DB3') };
    const B = [[-.02, 130, 74, 0, ''], [.12, 96, 112, 1, 't'], [.25, 150, 82, 2, 'm'], [.43, 104, 124, 0, 'd'], [.57, 140, 78, 1, 'm'], [.74, 96, 134, 2, 't'], [.87, 160, 90, 0, 'md']];
    let o = '';
    if (xs > 0) o += `<rect x="0" y="${R(gy - 26 * s)}" width="${R(w * xs + 20 * s)}" height="${R(28 * s)}" fill="${C.wall[1]}"/>`;
    B.forEach(([fx, bw0, bh0, wi, opt], bi) => {
      const x = (xs + fx * (1 - xs)) * w, bw = bw0 * s * (1 - xs * .55), bh = bh0 * s, top = gy - bh, wall = C.wall[wi];
      if (opt.includes('t')) { // past tom ustki xona (keng va past, minora emas)
        const tw = bw * .46, th = 20 * s, tx = x + bw * .5;
        o += `<rect x="${R(tx)}" y="${R(top - th)}" width="${R(tw)}" height="${R(th + 2)}" fill="${wall}"/>`;
        o += `<rect x="${R(tx + tw * .5 - 5 * s)}" y="${R(top - th + 6 * s)}" width="${R(10 * s)}" height="${R(8 * s)}" fill="${C.win}"/>`;
      }
      o += `<rect x="${R(x)}" y="${R(top)}" width="${R(bw)}" height="${R(bh + 2)}" fill="${wall}"/>`;
      for (let k = 0; k * 14 * s < bw - 6 * s; k++) o += `<rect x="${R(x + 2 * s + k * 14 * s)}" y="${R(top - 7 * s)}" width="${R(8 * s)}" height="${R(8 * s)}" fill="${wall}"/>`;
      const nw = Math.max(1, Math.floor(bw / (30 * s)));
      for (let k = 0; k < nw; k++) {
        const lit = !NIGHT || (bi + k) % 3 !== 1;            // tunda ba'zi derazalar qorong'i qoladi
        const wx = x + (bw / nw) * (k + .5) - 6 * s, wy = top + 18 * s, ww = 12 * s, wh = 16 * s;
        o += `<path d="M${R(wx)} ${R(wy + wh)} v ${R(-wh + ww / 2)} a ${R(ww / 2)} ${R(ww / 2)} 0 0 1 ${R(ww)} 0 v ${R(wh - ww / 2)} Z" fill="${lit ? C.win : K('#B79A69')}"/>`;
      }
      if (opt.includes('m')) {
        const mx = x + bw * .18, my = top + 40 * s, mw = 40 * s, mh = 30 * s;
        o += `<rect x="${R(mx)}" y="${R(my)}" width="${R(mw)}" height="${R(mh)}" rx="${R(2 * s)}" fill="${NIGHT ? GLOW : C.mash}"/>`;
        for (let i = 0; i < 6; i++) for (let j = 0; j < 4; j++) o += circle(mx + 4 * s + i * 6.4 * s, my + 5 * s + j * 6.6 * s, 1.9 * s, NIGHT ? C.mash : wall);
      }
      if (opt.includes('d')) {
        const dw = 26 * s, dh = 40 * s, dx = x + bw * .62, dy = gy - dh;
        o += `<path d="M${R(dx)} ${R(gy)} v ${R(-dh + dw / 2)} a ${R(dw / 2)} ${R(dw / 2)} 0 0 1 ${R(dw)} 0 v ${R(dh - dw / 2)} Z" fill="${C.door}"/>`;
        for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) o += circle(dx + 6 * s + i * 7 * s, dy + 18 * s + j * 7 * s, 1.3 * s, C.wall[2]);
      }
    });
    return o;
  }
  /* Qahva: dalla (qahvadon), finjonlar, xurmo, hil */
  const DALLAH = "M22 118 L58 118 C62 100 64 84 54 72 C50 66 46 62 46 56 L46 40 C52 38 54 34 50 30 L44 24 L41 10 L39 10 L36 24 L30 30 C26 34 28 38 34 40 L34 56 C34 62 30 66 26 72 C16 84 18 100 22 118 Z";
  const SPOUT = "M27 78 C14 72 8 52 1 30 L-2 24 L5 27 C12 46 18 62 31 71 Z";
  function dallah(x, y, s) {
    const body = K('#C58A45'), light = K('#DDA663'), dark = K('#A87436');
    return `<g transform="translate(${R(x - 40 * s)} ${R(y - 120 * s)}) scale(${s})">
      <path d="M54 76 C76 72 78 44 50 44" stroke="${dark}" stroke-width="4.5" fill="none" stroke-linecap="round"/>
      <path d="${SPOUT}" fill="${body}"/><path d="${DALLAH}" fill="${body}"/>
      <path d="M27 112 C23 96 25 84 33 75" stroke="${light}" stroke-width="4" fill="none" stroke-linecap="round"/>
      <rect x="33" y="52" width="14" height="4" fill="${light}"/><rect x="30" y="38" width="20" height="3.5" rx="1.5" fill="${light}"/>
      <rect x="18" y="114" width="44" height="6" rx="2" fill="${dark}"/><circle cx="40" cy="8" r="3.5" fill="${light}"/></g>`;
  }
  function cup(x, y, s) {
    return `<path d="M${R(x - 10 * s)} ${R(y - 14 * s)} L ${R(x + 10 * s)} ${R(y - 14 * s)} L ${R(x + 7 * s)} ${R(y)} L ${R(x - 7 * s)} ${R(y)} Z" fill="${K('#EFE4CE')}"/>
      <rect x="${R(x - 10.5 * s)}" y="${R(y - 15.5 * s)}" width="${R(21 * s)}" height="${R(3 * s)}" rx="${R(1.2 * s)}" fill="${K('#C58A45')}"/>`;
  }
  function steam(x, y, s) {
    let o = '';
    for (let i = 0; i < 3; i++) o += `<path d="M${R(x + i * 9 * s)} ${R(y)} c ${R(-6 * s)} ${R(-8 * s)} ${R(6 * s)} ${R(-14 * s)} 0 ${R(-22 * s)} s ${R(6 * s)} ${R(-14 * s)} 0 ${R(-22 * s)}" stroke="${NIGHT ? STAR : '#F1E6D0'}" stroke-width="${R(2.4 * s)}" fill="none" stroke-linecap="round" opacity=".85"/>`;
    return o;
  }
  /* Xattot: alif va nuqta o'lchovi, nuqtasiz harflar + romb nuqtalar, qamish qalam */
  function reed(x, y, s) {
    return `<g transform="translate(${R(x)} ${R(y)}) rotate(-32) scale(${s})">
      <rect x="0" y="-5" width="190" height="10" rx="5" fill="${K('#C9A877')}"/><polygon points="190,-5 222,4 190,5" fill="${K('#8B6A3E')}"/>
      <rect x="40" y="-5" width="3" height="10" fill="${K('#8B6A3E')}" opacity=".5"/><rect x="110" y="-5" width="3" height="10" fill="${K('#8B6A3E')}" opacity=".5"/></g>`;
  }
  const AR = (x, y, size, ch, c, op) => `<text dir="rtl" lang="ar" x="${R(x)}" y="${R(y)}" font-family="'Noto Naskh Arabic', serif" font-size="${R(size)}" fill="${K(c)}" opacity="${op}" text-anchor="middle">${ch}</text>`;

  const SCENES = {
    sahro(w, h, s, o) {
      const t = o.top ?? .52, f = o.focus ?? .44;
      const [d1, d2, d3] = dunes(w, h, t, ['#E6CD98', '#D2B072', '#E9D6A8']);
      return (NIGHT ? stars(w, h, t, Math.round(w / 9), 11) : '') + orb(w * (f + .36), h * (t - .2), 44 * s, '#E6A63E') + d1
        + caravan(w, h, t, w * f, .62 * s, '#B98C4E', 3, 64) + d2 + palm(w * .93, h * (t + .38), .62 * s, '#B08A55', '#8FA35E') + d3;
    },
    voha(w, h, s, o) {
      const t = o.top ?? .5, gy = h * (t + .32), [d1] = dunes(w, h, t, ['#E2D8A6', '#E2D8A6', '#E2D8A6']);
      return (NIGHT ? stars(w, h, t, Math.round(w / 10), 23) + orb(w * .42, h * (t - .22), 30 * s, '') : '')
        + d1 + `<rect x="0" y="${R(gy - 10 * s)}" width="${w}" height="${R(h - gy + 10 * s)}" fill="${K('#E6DFB6')}"/>`
        + `<ellipse cx="${R(w * .74)}" cy="${R(gy + 12 * s)}" rx="${R(150 * s)}" ry="${R(20 * s)}" fill="${K('#A8CFC2')}"/>`
        + (NIGHT ? `<ellipse cx="${R(w * .7)}" cy="${R(gy + 12 * s)}" rx="${R(40 * s)}" ry="${R(4 * s)}" fill="${MOON}" opacity=".7"/>` : '')
        + `<path d="M${R(w * .74 - 80 * s)} ${R(gy + 10 * s)} h ${R(46 * s)} M${R(w * .74 + 20 * s)} ${R(gy + 16 * s)} h ${R(60 * s)}" stroke="${K('#CDE3D6')}" stroke-width="${R(2.5 * s)}" stroke-linecap="round"/>`
        + palm(w * .52, gy, .66 * s, '#B08A55', '#93AE62') + palm(w * .64, gy, .95 * s, '#B08A55', '#7E9A52', '#C08A50')
        + palm(w * .84, gy + 4 * s, 1.05 * s, '#A9844F', '#7E9A52', '#C08A50') + palm(w * .96, gy, .7 * s, '#B08A55', '#93AE62')
        + tuft(w * .3, gy + 4 * s, s * .8, '#8FA35E') + tuft(w * .58, gy - 2 * s, s * .8, '#8FA35E') + tuft(w * .92, gy + 8 * s, s, '#8FA35E');
    },
    shahar(w, h, s, o) {
      const gy = h * (o.ground ?? .94), xs = o.focus ?? .4;
      return (NIGHT ? stars(w, h, .6, Math.round(w / 9), 37) : '') + orb(w * (xs + .1), h * .26, 30 * s, '#E6A63E')
        + `<rect x="0" y="${R(gy)}" width="${w}" height="${R(h - gy)}" fill="${K('#D9C49C')}"/>`
        + city(w, gy, s, xs) + palm(w * (xs + .3), gy, .55 * s, '#B08A55', '#8FA35E');
    },
    qahva(w, h, s, o) {
      const gy = h * (o.ground ?? .9), wx = w * .9 - 40 * s, wy = h * .1, ww = 80 * s, wh = 96 * s;
      let lat = '', d = '', hl = '';
      for (let i = 0; i < 7; i++) for (let j = 0; j < 8; j++) lat += circle(wx + 10 * s + i * 10 * s, wy + 30 * s + j * 8.4 * s, 2.6 * s, NIGHT ? '#F1E3BD' : '#DCC39C', NIGHT ? .9 : 1);
      for (let i = 0; i < 7; i++) d += `<ellipse cx="${R(w * .89 + (i % 4) * 11 * s - 16 * s)}" cy="${R(gy - 8 * s - Math.floor(i / 4) * 7 * s)}" rx="${R(6.5 * s)}" ry="${R(4.2 * s)}" fill="${K('#B07A3E')}"/>`;
      for (const [dx, dy, r] of [[-.08, 2, 20], [.04, 6, -30], [.14, 0, 50]]) {
        const cx = w * (.72 + dx), cy = gy + 12 * s + dy * s;
        hl += `<ellipse cx="${R(cx)}" cy="${R(cy)}" rx="${R(5 * s)}" ry="${R(2.6 * s)}" fill="${K('#8AA35C')}" transform="rotate(${r} ${R(cx)} ${R(cy)})"/>`;
      }
      return `<path d="M${R(wx)} ${R(wy + wh)} v ${R(-wh + ww / 2)} a ${R(ww / 2)} ${R(ww / 2)} 0 0 1 ${R(ww)} 0 v ${R(wh - ww / 2)} Z" fill="${NIGHT ? '#8E93A6' : '#C9A877'}"/>` + lat
        + `<rect x="0" y="${R(gy)}" width="${w}" height="${R(h - gy)}" fill="${K('#D8BE92')}"/>`
        + `<ellipse cx="${R(w * .72)}" cy="${R(gy)}" rx="${R(170 * s)}" ry="${R(16 * s)}" fill="${K('#CFAE78')}"/>`
        + steam(w * .62 - 6 * s, gy - 132 * s, s) + dallah(w * .62, gy, s) + cup(w * .74, gy, s) + cup(w * .79, gy - 2 * s, s * .9)
        + `<path d="M${R(w * .89 - 30 * s)} ${R(gy - 6 * s)} a ${R(30 * s)} ${R(12 * s)} 0 0 0 ${R(60 * s)} 0 Z" fill="${K('#D9B77F')}"/>` + d + hl;
    },
    xattot(w, h, s, o) {
      const ax = w * .8, base = h * (o.ground ?? .86), dc = NIGHT ? GLOW : '#D9A23A';
      let m = '';
      for (let i = 0; i < 5; i++) m += diamond(ax + 46 * s, base - 14 * s - i * 26 * s, 10 * s, dc);
      return (NIGHT ? stars(w, h, .55, Math.round(w / 14), 41) : '')
        + AR(ax, base, 170 * s, 'ا', '#B89A66', .7) + m
        + AR(w * .66, base - 10 * s, 120 * s, 'ں', '#C9AE7E', .6) + AR(w * .5, base - 40 * s, 90 * s, 'ٯ', '#C9AE7E', .45)
        + diamond(w * .66, base - 64 * s, 9 * s, dc) + diamond(w * .5 - 9 * s, base - 90 * s, 7 * s, dc) + diamond(w * .5 + 9 * s, base - 90 * s, 7 * s, dc)
        + `<path d="M${R(w * .42)} ${R(base + 4 * s)} C ${R(w * .52)} ${R(base - 20 * s)}, ${R(w * .62)} ${R(base + 24 * s)}, ${R(w * .76)} ${R(base + 2 * s)}" stroke="${K('#B89A66')}" stroke-width="${R(5 * s)}" fill="none" stroke-linecap="round" opacity=".5"/>`
        + reed(w * .9, base + 20 * s, .8 * s);
    },
    shom(w, h, s, o) {
      const t = o.top ?? .56, [d1, d2, d3] = dunes(w, h, t, ['#E8BF86', '#DDAA6C', '#EAC796']);
      return (NIGHT ? stars(w, h, t, Math.round(w / 8), 53) + orb(w * .76, h * (t - .24), 40 * s, '') : circle(w * .76, h * (t + .02), 78 * s, '#EE9A3C', .92))
        + d1 + caravan(w, h, t, w * (o.focus ?? .36), .6 * s, '#C08A50', 4, 62) + d2 + d3;
    },
  };

  /* Matn joylashuviga qarab manzara markazi (focus) */
  const FOCUS = {
    hero: { sahro: .52, shahar: .4, shom: .45 },     // matn chapda
    card: { sahro: .62, shahar: .56, shom: .56 },    // kichik karta, matn chapda
    full: { sahro: .3, shahar: .08, shom: .22 },     // matnsiz katta rasm (muqova)
    thumb: { sahro: .1, shahar: 0, shom: .1 },
  };
  function scene(name, w, h, o = {}) {
    NIGHT = !!o.night;
    const s = o.s ?? h / 260;
    const f = typeof o.focus === 'string' ? (FOCUS[o.focus] || {})[name] : o.focus;
    const svg = `<svg class="scene" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" preserveAspectRatio="xMidYMax slice" aria-hidden="true">${SCENES[name](w, h, s, Object.assign({}, o, { focus: f }))}</svg>`;
    NIGHT = false;
    return svg;
  }
  G.NUQTA_SCENES = { scene, SCENES, FOCUS, VARIANTS: ['sahro', 'voha', 'shahar', 'qahva', 'xattot', 'shom'] };
  G.scene = scene;
})(typeof window !== 'undefined' ? window : globalThis);

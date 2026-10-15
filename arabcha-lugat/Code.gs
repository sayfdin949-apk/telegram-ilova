/**
 * Arabcha Lugʻat — Telegram mini ilova uchun server (Google Apps Script)
 */
const BOT_TOKEN = 'BU_YERGA_BOT_TOKENINI_QOYING';

const SH_WORDS = 'Soʻzlar';
const SH_RES = 'Natijalar';
const SH_SET = 'Sozlamalar';
const RES_HEAD = ['Telegram ID', 'Ism', 'Username', 'Oʻrgangan soʻzlar', 'Aniqlik %', 'Javoblar', 'Mashqlar', 'Ketma-ket kun', 'Oxirgi faollik', 'Progress (oʻzgartirmang)'];

function setup() {
  const ss = SpreadsheetApp.getActive();
  let w = ss.getSheetByName(SH_WORDS);
  if (!w) w = ss.insertSheet(SH_WORDS);
  if (w.getLastRow() < 2) {
    w.clear();
    w.getRange(1, 1, 1, 4).setValues([['Arabcha', 'Oʻzbekcha', 'Dars', 'Oʻqilishi']]).setFontWeight('bold');
    const seed = SEED_WORDS;
    w.getRange(2, 1, seed.length, 4).setValues(seed);
    w.setFrozenRows(1);
    w.getRange('A:A').setFontSize(16);
    w.setColumnWidth(1, 220); w.setColumnWidth(2, 220);
  }
  let r = ss.getSheetByName(SH_RES);
  if (!r) r = ss.insertSheet(SH_RES);
  if (r.getLastRow() < 1) {
    r.getRange(1, 1, 1, RES_HEAD.length).setValues([RES_HEAD]).setFontWeight('bold');
    r.setFrozenRows(1);
  }
  let s = ss.getSheetByName(SH_SET);
  if (!s) s = ss.insertSheet(SH_SET);
  if (!s.getRange('A1').getValue()) {
    s.getRange('A1:B3').setValues([
      ['Oʻqituvchi Telegram ID', ''],
      ['Izoh', 'B1 boʻsh boʻlsa, ilovani birinchi ochgan odam oʻqituvchi boʻladi. Bir nechta ID ni vergul bilan yozish mumkin.'],
      ['', '']
    ]);
    s.getRange('A1:A2').setFontWeight('bold');
  }
  const def = ss.getSheetByName('Sheet1') || ss.getSheetByName('Лист1') || ss.getSheetByName('Varaq1');
  if (def && ss.getSheets().length > 1) ss.deleteSheet(def);
  if (BOT_TOKEN.indexOf('BU_YERGA') === 0) throw new Error('Jadval tayyor. Endi BOT_TOKEN qatoriga bot tokenini qoʻyishni unutmang.');
}

function doGet(e) { return handle((e && e.parameter) || {}); }
function doPost(e) {
  let body = {};
  try { body = JSON.parse(e.postData.contents); } catch (x) {}
  return handle(body);
}
function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
function handle(p) {
  try {
    const u = verify(p.init);
    if (!u) return out({ ok: false, error: 'auth' });
    if (p.a === 'boot') return out(boot(u));
    if (p.a === 'save') return out(save(u, p.prog, p.streak));
    if (p.a === 'teacher') return out(teacher(u));
    return out({ ok: false, error: 'action' });
  } catch (err) {
    return out({ ok: false, error: String(err && err.message || err) });
  }
}

function verify(init) {
  if (!init || BOT_TOKEN.indexOf('BU_YERGA') === 0) return null;
  const params = {};
  String(init).split('&').forEach(function (s) {
    const i = s.indexOf('=');
    if (i > 0) params[s.slice(0, i)] = decodeURIComponent(s.slice(i + 1));
  });
  const hash = params.hash;
  if (!hash) return null;
  const dcs = Object.keys(params).filter(function (k) { return k !== 'hash'; }).sort()
    .map(function (k) { return k + '=' + params[k]; }).join('\n');
  const secret = Utilities.computeHmacSha256Signature(Utilities.newBlob(BOT_TOKEN).getBytes(), Utilities.newBlob('WebAppData').getBytes());
  const sig = Utilities.computeHmacSha256Signature(Utilities.newBlob(dcs).getBytes(), secret);
  const hex = sig.map(function (b) { return ('0' + ((b + 256) % 256).toString(16)).slice(-2); }).join('');
  if (hex !== hash) return null;
  const age = Date.now() / 1000 - Number(params.auth_date || 0);
  if (age > 7 * 86400) return null;
  const user = JSON.parse(params.user || '{}');
  if (!user.id) return null;
  return user;
}

function teacherIds() {
  const s = SpreadsheetApp.getActive().getSheetByName(SH_SET);
  return String(s.getRange('B1').getValue() || '').split(/[,\s]+/).filter(String);
}
function words() {
  const w = SpreadsheetApp.getActive().getSheetByName(SH_WORDS);
  const n = w.getLastRow();
  if (n < 2) return [];
  return w.getRange(2, 1, n - 1, 4).getDisplayValues()
    .map(function (r) { return { ar: r[0].trim(), uz: r[1].trim(), topic: r[2].trim() || 'Boshqa', tr: r[3].trim() }; })
    .filter(function (x) { return x.ar && x.uz; });
}
function findRow(sh, id) {
  const f = sh.getRange('A:A').createTextFinder(String(id)).matchEntireCell(true).findNext();
  return f ? f.getRow() : 0;
}
function fullName(u) { return [u.first_name, u.last_name].filter(Boolean).join(' ') || ('ID ' + u.id); }

function boot(u) {
  let ids = teacherIds();
  if (!ids.length) {
    const lock = LockService.getScriptLock(); lock.waitLock(10000);
    try {
      ids = teacherIds();
      if (!ids.length) { SpreadsheetApp.getActive().getSheetByName(SH_SET).getRange('B1').setValue(String(u.id)); ids = [String(u.id)]; }
    } finally { lock.releaseLock(); }
  }
  const sh = SpreadsheetApp.getActive().getSheetByName(SH_RES);
  const row = findRow(sh, u.id);
  let prog = null;
  if (row) { try { prog = JSON.parse(sh.getRange(row, 10).getValue() || 'null'); } catch (x) {} }
  return { ok: true, words: words(), prog: prog, isTeacher: ids.indexOf(String(u.id)) >= 0, name: u.first_name || '' };
}

function save(u, prog, streak) {
  if (!prog || typeof prog !== 'object') return { ok: false, error: 'data' };
  const json = JSON.stringify(prog);
  if (json.length > 45000) return { ok: false, error: 'too_big' };
  const ws = words(), srs = prog.srs || {};
  let learned = 0;
  ws.forEach(function (w) { if (srs[w.ar] && srs[w.ar].b >= 3) learned++; });
  const st = prog.stats || {};
  const acc = st.answers ? Math.round(st.correct / st.answers * 100) : 0;
  const rowVals = [String(u.id), fullName(u), u.username ? '@' + u.username : '', learned, acc, st.answers || 0, st.sessions || 0, Number(streak) || 0, st.last ? new Date(st.last) : '', json];
  const lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    const sh = SpreadsheetApp.getActive().getSheetByName(SH_RES);
    const row = findRow(sh, u.id);
    if (row) sh.getRange(row, 1, 1, rowVals.length).setValues([rowVals]);
    else sh.appendRow(rowVals);
  } finally { lock.releaseLock(); }
  return { ok: true };
}

function teacher(u) {
  if (teacherIds().indexOf(String(u.id)) < 0) return { ok: false, error: 'not_teacher' };
  const sh = SpreadsheetApp.getActive().getSheetByName(SH_RES);
  const n = sh.getLastRow();
  const rows = n > 1 ? sh.getRange(2, 1, n - 1, 10).getValues() : [];
  const ws = words(), byAr = {};
  ws.forEach(function (w) { byAr[w.ar] = w; });
  const wrong = {}, students = [];
  rows.forEach(function (r) {
    if (String(r[0]) === String(u.id)) return;
    let p = {};
    try { p = JSON.parse(r[9] || '{}'); } catch (x) {}
    Object.keys(p.srs || {}).forEach(function (k) { if (byAr[k]) wrong[k] = (wrong[k] || 0) + (p.srs[k].w || 0); });
    students.push({ name: r[1], username: r[2], learned: r[3], acc: r[4], answers: r[5], sessions: r[6], streak: r[7], last: r[8] instanceof Date ? r[8].getTime() : 0 });
  });
  const hard = Object.keys(wrong).filter(function (k) { return wrong[k] > 0; })
    .sort(function (a, b) { return wrong[b] - wrong[a]; }).slice(0, 8)
    .map(function (k) { return { ar: k, uz: byAr[k].uz, n: wrong[k] }; });
  return { ok: true, students: students, hard: hard, total: ws.length };
}

const SEED_WORDS = [["هٰذَا", "bu (yaqindagi, erkak jinsi)", "1-dars", ""], ["بَيْتٌ", "uy", "1-dars", ""], ["بَابٌ", "eshik", "1-dars", ""], ["كِتَابٌ", "kitob", "1-dars", ""], ["قَلَمٌ", "qalam", "1-dars", ""], ["مِفْتَاحٌ", "kalit", "1-dars", ""], ["مَكْتَبٌ", "stol, parta", "1-dars", ""], ["سَرِيرٌ", "krovat", "1-dars", ""], ["كُرْسِيٌّ", "stul", "1-dars", ""], ["مَا", "nima", "1-dars", ""], ["مَنْ", "kim", "1-dars", ""], ["قَمِيصٌ", "koʻylak", "1-dars", ""], ["نَجْمٌ", "yulduz", "1-dars", ""], ["طَبِيبٌ", "shifokor, tabib", "1-dars", ""], ["وَلَدٌ", "bola, oʻgʻil bola", "1-dars", ""], ["طَالِبٌ", "talaba, oʻquvchi", "1-dars", ""], ["رَجُلٌ", "erkak kishi", "1-dars", ""], ["تَاجِرٌ", "savdogar, tijoratchi", "1-dars", ""], ["كَلْبٌ", "it, kuchuk", "1-dars", ""], ["قِطٌّ", "mushuk", "1-dars", ""], ["حِمَارٌ", "eshak", "1-dars", ""], ["حِصَانٌ", "ot", "1-dars", ""], ["جَمَلٌ", "tuya", "1-dars", ""], ["دِيكٌ", "xoʻroz", "1-dars", ""], ["مُدَرِّسٌ", "oʻqituvchi, mudarris", "1-dars", ""], ["مِنْدِيلٌ", "roʻmolcha", "1-dars", ""], ["ذٰلِكَ", "anavi (uzoqdagi, erkak jinsi)", "2-dars", ""], ["حَجَرٌ", "tosh", "2-dars", ""], ["لَبَنٌ", "sut", "2-dars", ""], ["سُكَّرٌ", "shakar", "2-dars", ""], ["وَ", "va", "2-dars", ""], ["مَكْسُورٌ", "siniq", "3-dars", ""], ["مَفْتُوحٌ", "ochiq", "3-dars", ""], ["مَاءٌ", "suv", "3-dars", ""], ["بَارِدٌ", "sovuq", "3-dars", ""], ["قَرِيبٌ", "yaqin", "3-dars", ""], ["بَعِيدٌ", "uzoq", "3-dars", ""], ["قَمَرٌ", "oy (osmondagi)", "3-dars", ""], ["حَارٌّ", "issiq", "3-dars", ""], ["صَغِيرٌ", "kichik", "3-dars", ""], ["كَبِيرٌ", "katta", "3-dars", ""], ["نَظِيفٌ", "toza", "3-dars", ""], ["وَسِخٌ", "kir, iflos", "3-dars", ""], ["جَدِيدٌ", "yangi", "3-dars", ""], ["ثَقِيلٌ", "ogʻir", "3-dars", ""], ["خَفِيفٌ", "yengil", "3-dars", ""], ["وَرَقٌ", "varoq, qogʻoz", "3-dars", ""], ["وَاقِفٌ", "tik turgan", "3-dars", ""], ["قَدِيمٌ", "eski", "3-dars", ""], ["جَمِيلٌ", "chiroyli", "3-dars", ""], ["دَفْتَرٌ", "daftar", "3-dars", ""], ["فَقِيرٌ", "kambagʻal, faqir", "3-dars", ""], ["غَنِيٌّ", "boy", "3-dars", ""], ["دُكَّانٌ", "doʻkon", "3-dars", ""], ["تُفَّاحٌ", "olma", "3-dars", ""], ["لَذِيذٌ", "shirin, mazali", "3-dars", ""], ["مَرِيضٌ", "kasal", "3-dars", ""], ["طَوِيلٌ", "uzun", "3-dars", ""], ["قَصِيرٌ", "kalta, qisqa", "3-dars", ""], ["غُرْفَةٌ", "xona", "4-dars", ""], ["حَمَّامٌ", "hammom", "4-dars", ""], ["مَطْبَخٌ", "oshxona", "4-dars", ""], ["مِرْحَاضٌ", "hojatxona", "4-dars", ""], ["شَارِعٌ", "koʻcha", "4-dars", ""], ["جَامِعَةٌ", "universitet", "4-dars", ""], ["هُوَ", "u (erkak)", "4-dars", ""], ["هِيَ", "u (ayol)", "4-dars", ""], ["فَصْلٌ", "sinfxona", "4-dars", ""], ["شَمْسٌ", "quyosh", "4-dars", ""], ["سَمَاءٌ", "osmon", "4-dars", ""], ["الْمَدْرَسَةُ", "maktab, madrasa", "4-dars", ""], ["الْيَابَانُ", "Yaponiya", "4-dars", ""], ["الْمُدِيرُ", "mudir, direktor", "4-dars", ""], ["الصِّينُ", "Xitoy", "4-dars", ""], ["ذَهَبَ", "ketdi, bordi", "4-dars", ""], ["الْهِنْدُ", "Hindiston", "4-dars", ""], ["خَرَجَ", "chiqdi", "4-dars", ""], ["السُّوقُ", "bozor", "4-dars", ""], ["الْفِلِبِّينُ", "Filippin", "4-dars", ""], ["الْعَمُّ", "amaki", "5-dars", ""], ["الْمُهَنْدِسُ", "muhandis", "5-dars", ""], ["الْخَالُ", "togʻa", "5-dars", ""], ["مُغْلَقٌ", "yopiq, berk", "5-dars", ""], ["الِاسْمُ", "ism", "5-dars", ""], ["الْحَقِيبَةُ", "sumka", "5-dars", ""], ["تَحْتَ", "tagida, ostida", "5-dars", ""], ["الِابْنُ", "oʻgʻil", "5-dars", ""], ["السَّيَّارَةُ", "mashina", "5-dars", ""], ["هُنَاكَ", "u yerda", "5-dars", ""], ["الْمِكْوَاةُ", "dazmol", "6-dars", ""], ["الْبَقَرَةُ", "sigir", "6-dars", ""], ["الْأُذُنُ", "quloq", "6-dars", ""], ["الْأُمُّ", "ona", "6-dars", ""], ["النَّافِذَةُ", "deraza", "6-dars", ""], ["الدَّرَّاجَةُ", "velosiped", "6-dars", ""], ["الْفَلَّاحُ", "dehqon", "6-dars", ""], ["الْيَدُ", "qoʻl", "6-dars", ""], ["الثَّلَّاجَةُ", "muzlatgich", "6-dars", ""], ["جِدًّا", "juda", "6-dars", ""], ["الْمِلْعَقَةُ", "qoshiq", "6-dars", ""], ["الْأَنْفُ", "burun", "6-dars", ""], ["الرِّجْلُ", "oyoq", "6-dars", ""], ["الْقَهْوَةُ", "qahva", "6-dars", ""], ["الْقِدْرُ", "qozon", "6-dars", ""], ["الْفَمُ", "ogʻiz", "6-dars", ""], ["الشَّايُ", "choy", "6-dars", ""], ["سَرِيعٌ", "tez", "6-dars", ""], ["أَيْضًا", "ham", "6-dars", ""], ["تِلْكَ", "anavi (uzoqdagi, ayol jinsi)", "7-dars", ""], ["مُمَرِّضَةٌ", "hamshira", "7-dars", ""], ["حَدِيقَةٌ", "bogʻ", "7-dars", ""], ["نَاقَةٌ", "tuya (urgʻochi)", "7-dars", ""], ["بَطَّةٌ", "oʻrdak", "7-dars", ""], ["بَيْضَةٌ", "tuxum", "7-dars", ""], ["مُسْتَشْفًى", "kasalxona", "8-dars", ""], ["سِكِّينٌ", "pichoq", "8-dars", ""], ["أَلْمَانِيَا", "Germaniya", "8-dars", ""], ["فَرَنْسَا", "Fransiya", "8-dars", ""], ["إِنْكِلْتَرَا", "Angliya", "8-dars", ""], ["أَمَامَ", "oldida", "8-dars", ""], ["خَلْفَ", "orqasida", "8-dars", ""], ["سُوِيسْرَا", "Shveytsariya", "8-dars", ""], ["اللُّغَةُ", "til", "9-dars", ""], ["الطَّائِرُ", "qush", "9-dars", ""], ["جَوْعَانُ", "och", "9-dars", ""], ["عَطْشَانُ", "chanqagan", "9-dars", ""], ["غَضْبَانُ", "gʻazablangan", "9-dars", ""], ["مَلْآنُ", "toʻla", "9-dars", ""], ["كَسْلَانُ", "dangasa", "9-dars", ""], ["شَهِيرٌ", "mashhur", "9-dars", ""], ["الْيَوْمُ", "kun", "9-dars", ""], ["الْيَوْمَ", "bugun", "9-dars", ""], ["الْعُصْفُورُ", "chumchuq", "9-dars", ""], ["الْمَدِينَةُ", "shahar", "9-dars", ""], ["الْآنَ", "hozir", "9-dars", ""], ["فَاكِهَةٌ", "meva", "9-dars", ""], ["سَهْلَةٌ", "oson", "9-dars", ""], ["صَعْبَةٌ", "qiyin", "9-dars", ""], ["مُجْتَهِدٌ", "tirishqoq", "9-dars", ""], ["الْقَاهِرَةُ", "Qohira", "9-dars", ""], ["الْإِنْكِلِيزِيَّةُ", "ingliz tili", "9-dars", ""], ["الْمُسْتَوْصَفُ", "poliklinika", "9-dars", ""], ["الْمِرْوَحَةُ", "ventilator", "9-dars", ""], ["الْمَدْرَسَةُ الثَّانَوِيَّةُ", "oʻrta maktab", "9-dars", ""], ["حَادٌّ", "oʻtkir", "9-dars", ""], ["الزَّوْجُ", "er (turmush oʻrtoq)", "10-dars", ""], ["الزَّمِيلُ", "sinfdosh, hamkasb", "10-dars", ""], ["وَاحِدٌ", "bir, bitta", "10-dars", ""], ["فَتًى", "yigit", "10-dars", ""], ["مَعَ", "bilan, birga", "10-dars", ""], ["الطِّفْلُ", "chaqaloq, goʻdak", "10-dars", ""], ["الْكُوَيْتُ", "Quvayt", "10-dars", ""], ["عَمَّةٌ", "amma", "12-dars", ""], ["خَالَةٌ", "xola", "12-dars", ""], ["مُسْتَشْفَى الْوِلَادَةِ", "tugʻruqxona", "12-dars", ""], ["الْحَقْلُ", "dala", "13-dars", ""], ["حُقُولٌ", "dalalar", "13-dars", ""], ["النَّاسُ", "odamlar", "13-dars", ""], ["الْقَرْيَةُ", "qishloq", "13-dars", ""], ["الضَّيْفُ", "mehmon", "13-dars", ""], ["ضُيُوفٌ", "mehmonlar", "13-dars", ""], ["الشَّيْخُ", "qariya, chol", "13-dars", ""], ["الْمَدْرَسَةُ الِابْتِدَائِيَّةُ", "boshlangʻich maktab", "13-dars", ""], ["الْحَفِيدُ", "nabira", "14-dars", ""], ["حَفَدَةٌ", "nabiralar", "14-dars", ""], ["الْأَخُ", "aka, uka", "14-dars", ""], ["إِخْوَةٌ", "aka-ukalar", "14-dars", ""], ["الْكُلِّيَّةُ", "fakultet", "14-dars", ""], ["كُلِّيَّاتٌ", "fakultetlar", "14-dars", ""], ["كُلِّيَّةُ الطِّبِّ", "tibbiyot fakulteti", "14-dars", ""], ["كُلِّيَّةُ الْهَنْدَسَةِ", "muhandislik fakulteti", "14-dars", ""], ["كُلِّيَّةُ التِّجَارَةِ", "tijorat fakulteti", "14-dars", ""], ["الْمَحْكَمَةُ", "sud, mahkama", "14-dars", ""], ["الْبَلَدُ", "shahar, mamlakat", "14-dars", ""], ["بِلَادٌ", "shaharlar, mamlakatlar", "14-dars", ""], ["أَهْلًا وَسَهْلًا", "xush kelibsiz", "14-dars", ""], ["مَرْحَبًا", "marhabo, salom", "14-dars", ""], ["الْيُونَانُ", "Yunoniston", "14-dars", ""], ["قَبْلَ", "oldin, avval", "15-dars", ""], ["بَعْدَ", "keyin", "15-dars", ""], ["الشَّهْرُ", "oy (vaqt)", "15-dars", ""], ["الْأُسْبُوعُ", "hafta", "15-dars", ""], ["مَتَى", "qachon", "15-dars", ""], ["الِاخْتِبَارُ", "imtihon", "15-dars", ""], ["رَجَعَ", "qaytdi", "15-dars", ""], ["الشَّرِكَةُ", "shirkat, kompaniya", "16-dars", ""], ["شَرِكَاتٌ", "shirkatlar", "16-dars", ""], ["قُمْصَانٌ", "koʻylaklar", "16-dars", ""], ["رَخِيصٌ", "arzon", "16-dars", ""], ["فُنْدُقٌ", "mehmonxona", "16-dars", ""], ["فَنَادِقُ", "mehmonxonalar", "16-dars", ""], ["مُدِيرُ الشَّرِكَةِ", "shirkat mudiri", "16-dars", ""], ["كَمْ", "qancha, nechta", "18-dars", ""], ["الْعِيدُ", "bayram", "18-dars", ""], ["الْمِسْطَرَةُ", "chizgʻich", "18-dars", ""], ["مَسَاطِرُ", "chizgʻichlar", "18-dars", ""], ["الرِّيَالُ", "riyol (pul birligi)", "18-dars", ""], ["رِيَالَاتٌ", "riyollar", "18-dars", ""], ["الْعَجَلَةُ", "gʻildirak", "18-dars", ""], ["عَجَلَاتٌ", "gʻildiraklar", "18-dars", ""], ["الثَّمَنُ", "narx", "19-20-dars", ""], ["الْحَافِلَةُ", "avtobus", "19-20-dars", ""], ["حَافِلَاتٌ", "avtobuslar", "19-20-dars", ""], ["السُّؤَالُ", "savol", "19-20-dars", ""], ["أَسْئِلَةٌ", "savollar", "19-20-dars", ""], ["نِصْفٌ", "yarim", "19-20-dars", ""], ["أُورُبَّا", "Yevropa", "19-20-dars", ""], ["مُخْتَلِفَةٌ", "turli xil", "19-20-dars", ""], ["أَيَّامٌ", "kunlar", "19-20-dars", ""], ["الْقِرْشُ", "qirsh (pul birligi)", "19-20-dars", ""], ["قُرُوشٌ", "qirshlar", "19-20-dars", ""], ["رَاكِبٌ", "yoʻlovchi", "19-20-dars", ""], ["رُكَّابٌ", "yoʻlovchilar", "19-20-dars", ""], ["قُدَامَى", "eskilar (koʻpligi)", "19-20-dars", ""], ["الْجَيْبُ", "choʻntak", "19-20-dars", ""], ["جُيُوبٌ", "choʻntaklar", "19-20-dars", ""], ["مَالِيزِيَا", "Malayziya", "19-20-dars", ""], ["الْمَجَلَّةُ", "jurnal", "19-20-dars", ""], ["مَجَلَّاتٌ", "jurnallar", "19-20-dars", ""], ["الْحَرْفُ", "harf", "19-20-dars", ""], ["حُرُوفٌ", "harflar", "19-20-dars", ""], ["الْكَلِمَةُ", "soʻz, kalima", "19-20-dars", ""], ["كَلِمَاتٌ", "soʻzlar", "19-20-dars", ""], ["إِنْدُونِيسِيَا", "Indoneziya", "19-20-dars", ""], ["غُرَفٌ", "xonalar", "19-20-dars", ""], ["مَكَاتِبُ", "stollar", "21-dars", ""], ["اللَّوْنُ", "rang", "21-dars", ""], ["أَلْوَانٌ", "ranglar", "21-dars", ""], ["وَلٰكِنْ", "va lekin", "21-dars", ""], ["كَرَاسِيُّ", "stullar", "21-dars", ""], ["فِنْجَانٌ", "piyola", "22-dars", ""], ["فَنَاجِينُ", "piyolalar", "22-dars", ""], ["مَدَارِسُ", "maktablar", "22-dars", ""], ["الدَّقِيقَةُ", "daqiqa", "22-dars", ""], ["دَقَائِقُ", "daqiqalar", "22-dars", ""], ["قَالَ", "aytdi (u erkak)", "22-dars", ""], ["قَالَتْ", "aytdi (u ayol)", "22-dars", ""], ["مَنَادِيلُ", "roʻmolchalar", "22-dars", ""], ["مَفَاتِيحُ", "kalitlar", "22-dars", ""], ["أَبْيَضُ", "oq", "22-dars", ""], ["أَحْمَرُ", "qizil", "22-dars", ""], ["أَخْضَرُ", "yashil", "22-dars", ""], ["أَسْوَدُ", "qora", "22-dars", ""], ["أَزْرَقُ", "koʻk", "22-dars", ""], ["أَصْفَرُ", "sariq", "22-dars", ""]];

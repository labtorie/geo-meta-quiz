/* Geo Meta Quiz collector.
   Run on an open geohints.com/meta/... page: reads the cards already on screen
   (country + image URL) and saves them as geohints-<page>.json. Makes no network requests. */
(() => {
  if (!/geohints\.com$/.test(location.hostname)) { alert('Откройте страницу geohints.com/meta/... и нажмите ещё раз.'); return; }

  const ALIAS = ['Czech Republic', 'Turkey', 'Åland', 'Hong Kong', 'Macao', 'Cocos (Keeling) Islands', 'United States', 'United Kingdom',
    'Eswatini', 'Myanmar', 'Palestine', 'Curaçao', 'United States Virgin Islands', 'Northern Mariana Islands', 'South Korea', 'North Korea',
    'Russia', 'Vietnam', 'Laos', 'Bolivia', 'Taiwan', 'Bosnia and Herzegovina', 'North Macedonia', 'Kosovo', 'Réunion', 'São Tomé and Príncipe',
    'Svalbard and Jan Mayen', 'Falkland Islands', 'Pitcairn Islands', 'British Indian Ocean Territory', 'England', 'Scotland', 'Wales',
    'Northern Ireland', 'Midway Atoll', 'Saint Pierre and Miquelon', 'Turks and Caicos Islands', 'Antigua and Barbuda', 'Trinidad and Tobago',
    'Saint Kitts and Nevis', 'Saint Vincent and the Grenadines', 'Wallis and Futuna'];
  const VARIANT = { 'Macau': 'Macao', 'Ivory Coast': "Côte d'Ivoire", 'US Virgin Islands': 'United States Virgin Islands',
    'Sao Tome and Principe': 'São Tomé and Príncipe', 'Svalbard': 'Svalbard and Jan Mayen', 'USA': 'United States', 'US': 'United States',
    'UK': 'United Kingdom', 'Great Britain': 'United Kingdom', 'Czechia': 'Czech Republic', 'Türkiye': 'Turkey', 'Aland': 'Åland',
    'Aland Islands': 'Åland', 'Åland Islands': 'Åland', 'Swaziland': 'Eswatini', 'Burma': 'Myanmar', 'Macedonia': 'North Macedonia' };
  const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/&/g, 'and').toLowerCase().replace(/[^a-z]+/g, ' ').trim();
  const names = new Map();
  try {
    const dn = new Intl.DisplayNames(['en'], { type: 'region' }), A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    for (const a of A) for (const b of A) { const n = dn.of(a + b); if (n && n !== a + b) names.set(norm(n), n); }
  } catch (e) {}
  for (const n of ALIAS) names.set(norm(n), n);
  for (const [v, n] of Object.entries(VARIANT)) names.set(norm(v), n);
  const asCountry = t => { t = (t || '').replace(/\s+/g, ' ').trim(); return t.length > 1 && t.length < 45 ? (names.has(norm(t)) ? t : null) : null; };

  // own visible text of an element, without text inside links ("Open in Google Maps") and images
  const texts = el => {
    const out = [], w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n; (n = w.nextNode());) if (!n.parentElement.closest('a[href^="http"], script, style') && n.textContent.trim()) out.push(n.textContent.trim());
    return out;
  };
  const isAsset = img => /\/storage\//.test(img.currentSrc || img.src || '') && !/\/logos\//.test(img.src);
  const imgs = [...document.querySelectorAll('img')].filter(isAsset);
  const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,div.text-3xl,div.text-2xl,div.text-xl,div.font-bold,div.font-semibold')];

  const items = [], miss = [];
  for (const img of imgs) {
    let c = null;
    // 1) the card around the image: nearest ancestor with a country name in its own text
    for (let el = img.parentElement, depth = 0; el && depth < 5 && !c; el = el.parentElement, depth++) {
      if (el.querySelectorAll('img').length > 12) break; // reached a whole section, stop
      for (const t of texts(el)) if ((c = asCountry(t))) break;
    }
    // 2) otherwise: the last country heading above the image (section layout)
    if (!c) {
      for (const h of headings) {
        if (!(h.compareDocumentPosition(img) & Node.DOCUMENT_POSITION_FOLLOWING)) break;
        const t = asCountry(h.textContent); if (t) c = t;
      }
    }
    const src = img.getAttribute('src') || img.currentSrc;
    const alt = (img.getAttribute('alt') || img.getAttribute('title') || '').trim();
    if (c) items.push({ c: names.get(norm(c)) || c, img: new URL(src, location.href).href, ...(alt && norm(alt) !== norm(c) ? { cap: alt } : {}) });
    else miss.push(src);
  }

  const page = location.pathname.replace(/^\/meta\//, '').replace(/\/$/, '') || 'page';
  const seen = new Set(), uniq = items.filter(i => { const k = i.c + '|' + i.img; return !seen.has(k) && seen.add(k); });
  const blob = new Blob([JSON.stringify({ page, url: location.href, title: document.title.trim(), items: uniq, unmatched: miss }, null, 1)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'geohints-' + page.replace(/\//g, '__') + '.json';
  document.body.append(a); a.click(); a.remove();
  alert(`Geo Meta Quiz: ${uniq.length} карточек по ${new Set(uniq.map(i => i.c)).size} странам` + (miss.length ? `, без страны: ${miss.length}` : '') + '.\nФайл сохранён в «Загрузки».');
})();

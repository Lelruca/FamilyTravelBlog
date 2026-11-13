// Every result must open an existing sight, rather than the start of a city list.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const build = process.env.TRAVEL_VERIFY_BUILD_DIR || 'public';
const registry = JSON.parse(fs.readFileSync('data/attractions.json', 'utf8'));
const html = fs.readFileSync(path.join(build, 'places/index.html'), 'utf8');
const json = html.match(/<script\b[^>]*\bid=(?:"sights-data"|'sights-data'|sights-data)(?:\s[^>]*|)>([\s\S]*?)<\/script>/);
assert.ok(json, 'Missing attraction search data');
const sights = JSON.parse(json[1]);
assert.ok(sights.length, 'Empty attraction search');
const pages = new Map(), ids = new Set();
for (const sight of sights) {
  const url = new URL(sight.u, 'https://example.invalid');
  assert.equal(url.searchParams.get('tab'), 'sights', sight.t);
  assert.ok(url.hash.startsWith('#a-'), sight.t + ': missing sight fragment');
  const id = decodeURIComponent(url.hash.slice(3));
  assert.ok(registry[id], sight.t + ': unknown attraction');
  assert.ok(!ids.has(id), id + ': duplicate search result');
  ids.add(id);
  const city = url.pathname.match(/\/places\/([^/]+)\/$/)?.[1];
  assert.equal(city, sight.p, sight.t + ': wrong city URL');
  if (!pages.has(city)) pages.set(city, fs.readFileSync(path.join(build, 'places', city, 'index.html'), 'utf8'));
  const page = pages.get(city);
  const block = page.match(new RegExp(`<div\\b[^>]*\\bid=(?:"a-${id}"|a-${id})(?:\\s[^>]*|)>([\\s\\S]*?)</div>`));
  assert.ok(block, id + ': no matching sight on destination page');
  assert.match(block[1], /<a\b[^>]*\bhref=/, id + ': destination has no chapter links');
}
for (const id of ['kolomenskoe', 'louvre', 'rijksmuseum', 'moscow--tretyakovskaya-galereya']) {
  assert.ok(ids.has(id), id + ': missing published result');
}
assert.ok(!ids.has('tretyakov-gallery'), 'Unused duplicate Tretyakov definition must not be a result');
assert.ok(!ids.has('moscow--kremlin-armoury'), 'Combined Kremlin/Armoury tag must not duplicate the two canonical sights');
console.log(`Verified ${sights.length} attraction results in ${pages.size} places: every fragment exists and has chapter links.`);

// Links to different chapters must have different visible labels and use the real TOC number.
let chapterLinks = 0;
for (const [city, page] of pages) {
  for (const block of page.matchAll(/<div\b[^>]*class=(?:"city-sight"|city-sight)[^>]*>([\s\S]*?)<\/div>/g)) {
    const labels = new Map();
    for (const link of block[1].matchAll(/<a\b([^>]*\bhref=[^>]*)>([\s\S]*?)<\/a>/g)) {
      const href = link[1].match(/\bhref=(?:"([^"]+)"|([^\s>]+))/).slice(1).find(Boolean);
      const label = link[2].replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
      assert.ok(!labels.has(label) || labels.get(label) === href, city + ': indistinguishable chapter links: ' + label);
      labels.set(label, href);
      const number = Number(label.match(/ · гл\. (\d+)$/)?.[1]);
      assert.ok(number > 0, city + ': missing chapter number in ' + label);
      const chapterPath = new URL(href, 'https://example.invalid').pathname.replace(/^.*?\/(europe|americas|asia)\//, '$1/');
      const chapter = fs.readFileSync(path.join(build, chapterPath, 'index.html'), 'utf8');
      const toc = chapter.match(/<ol\b[^>]*class=(?:"toc-list"|toc-list)[^>]*>([\s\S]*?)<\/ol>/)?.[1];
      assert.ok(toc, href + ': missing chapter table of contents');
      const current = [...toc.matchAll(/<li\b[^>]*>([\s\S]*?)<\/li>/g)].find(m => m[1].includes('aria-current=page') || m[1].includes('aria-current="page"'));
      const tocNumber = current?.[1].match(/<span\b[^>]*class=(?:"n"|n)[^>]*>(\d+)<\/span>/)?.[1];
      assert.equal(number, Number(tocNumber), href + ': link number differs from table of contents');
      assert.match(link[1], /\btitle=/, href + ': missing full chapter title');
      chapterLinks++;
    }
  }
}
const moscow = pages.get('moscow');
const kremlin = moscow.match(/<div class=city-sight id=a-moscow-kremlin>([\s\S]*?)<\/div>/)[1];
const armoury = moscow.match(/<div class=city-sight id=a-armoury-chamber>([\s\S]*?)<\/div>/)[1];
assert.ok(kremlin.includes('/russia-2021/kremlin/') && !kremlin.includes('/russia-2021/oruzheynaya-palata/'), 'Kremlin must link to its own 2021 chapter');
assert.ok(armoury.includes('/russia-2021/oruzheynaya-palata/'), 'Armoury must link to its own 2021 chapter');
for (const [name, block] of [['Kremlin', kremlin], ['Armoury', armoury]]) {
  assert.ok(block.includes('/moscow-new-year-2012/story/'), name + ': missing the shared 2012 story');
}
assert.match(armoury, /2021 · Я шагаю по Москве · гл\. 7/);
console.log(`Verified ${chapterLinks} distinct chapter labels against their tables of contents; Kremlin/Armoury separation passed.`);

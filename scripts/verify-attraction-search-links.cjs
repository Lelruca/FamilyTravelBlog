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
console.log(`Verified ${sights.length} attraction results in ${pages.size} places: every fragment exists and has chapter links.`);

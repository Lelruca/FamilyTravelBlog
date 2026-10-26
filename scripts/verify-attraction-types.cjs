// Search-data regressions: semantic matches must work without a word in the title.
// Run from the repository root. Does not modify content or UI.
const fs = require('node:fs');
const assert = require('node:assert/strict');
require('node:child_process').execFileSync(process.execPath, ['scripts/update-attraction-search-terms.cjs', '--check'], {stdio: 'inherit'});
const attractions = JSON.parse(fs.readFileSync('data/attractions.json', 'utf8'));
const types = JSON.parse(fs.readFileSync('data/attraction_types.json', 'utf8'));
const normalize = value => value.toLocaleLowerCase('ru').normalize('NFD').replace(/\p{M}/gu, '').replace(/ё/g, 'е');
const search = query => Object.entries(attractions).filter(([, a]) => {
  const text = normalize([a.title, ...a.search_terms].join(' '));
  return normalize(query).split(/\s+/).every(word => text.includes(word));
}).map(([id]) => id);
const museumsWithoutMuseum = [
  'moscow--tretyakovskaya-galereya', 'albertina', 'belvedere',
  'berlin--berlinskaya-kartinnaya-galereya', 'chicago--chikagskiy-institut-iskusstv',
  'detroit--detroytskiy-institut-iskusstv', 'dresden--drezdenskaya-kartinnaya-galereya',
  'dublin--natsionalnaya-galereya-irlandii', 'galleria-accademia', 'galleria-borghese',
  'louvre', 'mauritshuis', 'munich--lenbakhkhaus', 'munich--staraya-pinakoteka',
  'philadelphia--kollektsiya-barnsa', 'pinacoteca-brera', 'rijksmuseum',
  'rembrandt-house', 'tate-britain', 'uffizi', 'vatican--vatikanskaya-pinakoteka',
  'dearborn--grinfild-villidzh', 'highland-village', 'mcmichael-gallery'
];
for (const query of ['музей', 'музеи', 'музеев', 'museum']) {
  const found = new Set(search(query));
  for (const id of museumsWithoutMuseum) assert.ok(found.has(id), `${query} misses ${id}`);
  for (const id of ['sagrada-familia', 'barcelona--park-guel', 'toronto--si-en-tauer', 'poblenou-beach']) {
    assert.ok(!found.has(id), `${query} incorrectly returns ${id}`);
  }
}
for (const [query, id] of [
  ['музей Третьяковская', 'moscow--tretyakovskaya-galereya'],
  ['музей Ленбаххаус', 'munich--lenbakhkhaus'],
  ['галерея Уффици', 'uffizi'], ['парк Гуэль', 'barcelona--park-guel'],
  ['храм Саграда', 'sagrada-familia'], ['церковь Нотр-Дам', 'notre-dame-paris'],
  ['замок Алькасар', 'alcazar-segovia'], ['музей Гринфилд', 'dearborn--grinfild-villidzh'],
  ['технический музей', 'munich--deutsches-museum'],
  ['музей нацизма', 'munich--ns-dokumentationszentrum']
]) assert.ok(search(query).includes(id), `${query} misses ${id}`);
const munichMuseums=search('музей').filter(id=>attractions[id].parent==='munich');
assert.deepEqual(new Set(munichMuseums),new Set([
  'munich--lenbakhkhaus','munich--staraya-pinakoteka','munich-residenz',
  'munich--deutsches-museum','munich--ns-dokumentationszentrum'
]),'Munich museums must include the technical museum and the documentation centre');
const coordinates=JSON.parse(fs.readFileSync('data/place_coordinates.json','utf8'));
const dutchMuseums=search('музей').filter(id=>coordinates[attractions[id].parent]?.country_code==='NL');
assert.deepEqual(new Set(dutchMuseums),new Set([
  'amsterdam-museum','escher-museum','mauritshuis','rembrandt-house',
  'rijksmuseum','royal-delft','van-gogh-museum','van-loon','zaandam--peter-house'
]),'Dutch museum search must include names without the word museum');
for (const [id, a] of Object.entries(attractions)) {
  assert.ok(a.types.length && a.types.every(t => types[t]), `${id}: invalid classification`);
  if (a.types.includes('gallery')) assert.ok(a.types.includes('museum'), `${id}: gallery missing museum search category`);
}
for (const query of ['галерея', 'картинная галерея', 'художественная галерея']) {
  const found = new Set(search(query));
  for (const [id, a] of Object.entries(attractions)) {
    if (a.types.includes('gallery')) assert.ok(found.has(id), `${query} misses ${id}`);
  }
}
// A cathedral museum is a museum, not the cathedral building itself.
for (const id of ['milan--muzey-milanskogo-sobora', 'santiago-de-compostela--muzey-sobora-santyago']) {
  assert.ok(!attractions[id].types.includes('cathedral'), `${id}: museum mistaken for a cathedral`);
}
console.log(`Semantic search cases passed; ${Object.keys(attractions).length} classified objects, ${search('музей').length} museum results.`);

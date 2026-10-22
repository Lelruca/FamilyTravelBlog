const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const build = process.env.TRAVEL_VERIFY_BUILD_DIR || 'public';
const coordinates = JSON.parse(fs.readFileSync('data/place_coordinates.json', 'utf8'));
function walk(dir) {
  return fs.readdirSync(dir, {withFileTypes:true}).flatMap(e => e.isDirectory() ? walk(path.join(dir,e.name)) : [path.join(dir,e.name)]);
}
const expected = new Map();
for (const file of walk('content').filter(f=>path.basename(f)==='index.md')) {
  const raw = fs.readFileSync(file,'utf8');
  const front = raw.split(/^---\s*$/m)[1] || '';
  if (/^draft:\s*true\s*$/m.test(front)) continue;
  const places = front.match(/^places:\s*\r?\n((?:[ \t]+-[^\n]+\r?\n?)+)/m)?.[1];
  const inline = front.match(/^places:[ \t]*\[([^\]\r\n]*)\]/m)?.[1];
  if (!places && inline === undefined) continue;
  const url = '/' + path.dirname(file).slice('content'.length+1).replaceAll('\\','/') + '/';
  for (const line of places ? places.trim().split('\n') : inline.split(',').filter(x=>x.trim())) {
    const slug=line.trim().replace(/^-\s*/, '').replace(/^['"]|['"]$/g,'').trim();
    if (!expected.has(slug)) expected.set(slug,new Set());
    expected.get(slug).add(url);
  }
}
// Places inside a city (data/place_groups.yaml part_of) are listed with that city, not as their own row.
const groups = fs.readFileSync('data/place_groups.yaml','utf8');
const [partOfText, twinsText = ''] = groups.split(/^twins:/m);
const partOf = new Map([...partOfText.matchAll(/^[ \t]+([a-z0-9-]+):[ \t]*([a-z0-9-]+)[ \t]*\r?$/gm)].map(m=>[m[1],m[2]]));
const twins = [...twinsText.matchAll(/^[ \t]{2}([a-z0-9-]+):/gm)].map(m=>m[1]);
for (const [child,parent] of partOf) {
  assert.ok(expected.has(parent),`${child}: its city ${parent} has no chapters of its own`);
  for (const url of expected.get(child)||[]) expected.get(parent).add(url);
  expected.delete(child);
}
const index = fs.readFileSync(path.join(build,'places/index.html'),'utf8');
// each row of «Поиск» links straight to the place page; the chapters are checked on that page («Поездки» tab)
const rows = [...index.matchAll(/<a\b([^>]*data-place-item[^>]*)>([\s\S]*?)<\/a>/g)];
assert.equal(rows.length,expected.size+twins.length,'Place count differs from source chapter taxonomy');
let links=0;
for (const [,attrs,html] of rows) {
  const slug=attrs.match(/data-slug=(?:"([^"]+)"|([^\s>]+))/).slice(1).find(Boolean);
  const coord=coordinates[slug];
  assert.ok(coord,`${slug}: missing reviewed coordinates`);
  assert.ok(Number.isFinite(coord.lat) && Math.abs(coord.lat)<=85 && Number.isFinite(coord.lon) && Math.abs(coord.lon)<=180,`${slug}: invalid coordinates`);
  const reviewedSource = /^https:\/\/(?:www\.openstreetmap\.org\/(?:node|way|relation)\/\d+|wiki\.openstreetmap\.org\/wiki\/[^\s]+|www\.wikidata\.org\/wiki\/Q\d+|en\.wikipedia\.org\/wiki\/[^\s]+)$/.test(coord.source)
    || ['https://longwoodgardens.org/visit/directions','https://www.tremblant.ca/plan/getting-here'].includes(coord.source);
  assert.ok(reviewedSource,`${slug}: missing reviewed geographic source`);
  assert.ok(attrs.includes('data-lat=') && attrs.includes('data-lon='),`${slug}: coordinates not rendered`);
  const href = attrs.match(/href=(?:"([^"]+)"|([^\s>]+))/).slice(1).find(Boolean).replace(/^\/FamilyTravelBlog/,'');
  assert.equal(href, `/places/${slug}/`, `${slug}: the row does not lead to the place page`);
  const placePage=fs.readFileSync(path.join(build,'places',slug,'index.html'),'utf8');
  const trips=(placePage.match(/<section id="?city-trips"?[\s\S]*?<\/section>/)||[''])[0];
  const chapterLinks = [...trips.matchAll(/class="?city-ch"? href=(?:"([^"]+)"|([^\s>]+))/g)].map(m=>m[1]||m[2]);
  const canonical = new Set(chapterLinks.map(u=>u.replace(/^\/FamilyTravelBlog/,'')));
  // every chapter tagged with the place is on its page; the page may also show chapters that reach it only through a sight
  for (const url of expected.get(slug)) assert.ok(canonical.has(url),`${slug}: place page omits chapter ${url}`);
  for(const url of canonical) assert.ok(fs.existsSync(path.join(build,url,'index.html')),`${slug}: broken chapter ${url}`);
  // The shared site shell contains an empty lightbox image; reject actual photos.
  assert.ok(!/<img\b[^>]*\bsrc=(?:"[^"]+"|[^\s>]+)/.test(placePage),`${slug}: photographs on permanent place page`);
  links+=chapterLinks.length;
}
console.log(`Verified ${rows.length} places, ${links} direct chapter links, all coordinates and permanent place pages.`);

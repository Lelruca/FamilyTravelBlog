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
  if (!places) continue;
  const url = '/' + path.dirname(file).slice('content'.length+1).replaceAll('\\','/') + '/';
  for (const line of places.trim().split('\n')) {
    const slug=line.trim().replace(/^-\s*/, '').replace(/^['"]|['"]$/g,'').trim();
    if (!expected.has(slug)) expected.set(slug,new Set());
    expected.get(slug).add(url);
  }
}
const index = fs.readFileSync(path.join(build,'places/index.html'),'utf8');
const rows = [...index.matchAll(/<details\b([^>]*data-place-item[^>]*)>([\s\S]*?)<\/details>/g)];
assert.equal(rows.length,expected.size,'Place count differs from source chapter taxonomy');
let links=0;
for (const [,attrs,html] of rows) {
  const slug=attrs.match(/data-slug=(?:"([^"]+)"|([^\s>]+))/).slice(1).find(Boolean);
  const coord=coordinates[slug];
  assert.ok(coord,`${slug}: missing reviewed coordinates`);
  assert.ok(Number.isFinite(coord.lat) && Math.abs(coord.lat)<=85 && Number.isFinite(coord.lon) && Math.abs(coord.lon)<=180,`${slug}: invalid coordinates`);
  assert.ok(coord.source.startsWith('https://www.openstreetmap.org/'),`${slug}: missing source`);
  assert.ok(attrs.includes('data-lat=') && attrs.includes('data-lon='),`${slug}: coordinates not rendered`);
  const chapterLinks = [...html.matchAll(/href=(?:"([^"]+)"|([^\s>]+))/g)].map(m=>m[1]||m[2]).filter(u=>!u.includes('/places/'));
  const canonical = chapterLinks.map(u=>u.replace(/^\/FamilyTravelBlog/,''));
  assert.deepEqual(new Set(canonical),expected.get(slug),`${slug}: chapters differ from source`);
  for(const url of canonical) assert.ok(fs.existsSync(path.join(build,url,'index.html')),`${slug}: broken chapter ${url}`);
  const placePage=fs.readFileSync(path.join(build,'places',slug,'index.html'),'utf8');
  for (const url of chapterLinks) assert.ok(placePage.includes(url),`${slug}: permanent page omitted chapter ${url}`);
  // The shared site shell contains an empty lightbox image; reject actual photos.
  assert.ok(!/<img\b[^>]*\bsrc=(?:"[^"]+"|[^\s>]+)/.test(placePage),`${slug}: photographs on permanent place page`);
  links+=chapterLinks.length;
}
console.log(`Verified ${rows.length} places, ${links} direct chapter links, all coordinates and permanent place pages.`);

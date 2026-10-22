// Verify the frozen editorial audit and the chapter -> attraction -> geographic place links.
// Usage: node scripts/verify-place-attributions.cjs
const fs=require('node:fs'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const audit=JSON.parse(fs.readFileSync('reviews/places-audit-2026-10-22.json','utf8'));
const registry=JSON.parse(fs.readFileSync('data/attractions.json','utf8'));
const coordinates=JSON.parse(fs.readFileSync('data/place_coordinates.json','utf8'));
function walk(d){return fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(d+'/'+e.name):[d+'/'+e.name]);}
const files=walk('content').filter(f=>f.endsWith('/index.md')&&!f.startsWith('content/places/'));
assert.deepEqual(new Set(files),new Set(audit.chapters.map(c=>c.file)),'Audit coverage differs from the current chapter inventory');
const used=new Set();let links=0;
const clean=s=>s.normalize('NFC').toLowerCase().replaceAll('ё','е').replace(/\s+/g,' ');
for(const c of audit.chapters){
 const raw=fs.readFileSync(c.file,'utf8'),m=raw.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
 assert.ok(m,c.file+': missing front matter');
 const body=raw.slice(m[0].length);
 const hash=c.body_sha256_lf?crypto.createHash('sha256').update(body.replace(/\r/g,'')).digest('hex'):crypto.createHash('sha256').update(body).digest('hex');
 assert.equal(hash,c.body_sha256_lf||c.body_sha256,c.file+': author text or photo layout changed');
 const front=m[1];
 const inline=front.match(/^places:[ \t]*\[([^\]\r\n]*)\]/m),block=front.match(/^places:[ \t]*\r?\n((?:[ \t]+-[^\n]+\r?\n?)+)/m);
 const places=inline?inline[1].split(',').map(s=>s.trim().replace(/^['"]|['"]$/g,'')).filter(Boolean):block?block[1].trim().split('\n').map(s=>s.trim().replace(/^-\s*/,'').replace(/^['"]|['"]$/g,'')):[];
 assert.deepEqual(places,c.places,c.file+': geographic tags differ from review');
 assert.ok(places.length||c.no_places_reason,c.file+': unaccounted empty geography');
 for(const p of places){assert.ok(fs.existsSync('content/places/'+p+'/_index.md'),c.file+': unknown place '+p);assert.ok(coordinates[p],p+': missing coordinates');}
 const line=front.match(/^attractions:[ \t]*(\[[^\r\n]*\])/m);
 const ids=line?JSON.parse(line[1]):[];
 assert.deepEqual(ids,c.attractions,c.file+': attraction tags differ from review');
 assert.equal(new Set(ids).size,ids.length,c.file+': duplicate attractions');
 for(const id of ids){const d=registry[id];assert.ok(d,id+': unknown attraction');assert.ok(places.includes(d.parent),c.file+': attraction parent not tagged '+d.parent);used.add(id);links++;}
 const text=clean(raw.replace(/<[^>]*>/g,' '));
 for(const e of c.evidence)assert.ok(text.includes(clean(e.needle)),c.file+': evidence no longer present for '+e.id);
}
assert.deepEqual(new Set(Object.keys(registry)),used,'Unused or missing attraction definition');
for(const [id,d]of Object.entries(registry)){
 assert.ok(d.title&&d.parent,id+': incomplete definition');
 assert.equal(d.title[0],d.title[0].toLocaleUpperCase('ru'),id+': lowercase navigation label');
 assert.ok(fs.existsSync('content/places/'+d.parent+'/_index.md'),id+': unknown parent');
 if(d.place)assert.ok(fs.existsSync('content/places/'+d.place+'/_index.md'),id+': missing historical taxonomy term');
}
const rejected={
 'mexico-2025/coyoacan-ballet':/Фриды Кало/i,
 'rome-2015-2016/florence-museums':/Галилео|Академи/i,
 'girls-europe-2017/the-hague':/Эшер/i,
 'girls-europe-2017/sainte-chapelle-eiffel':/Оранжери/i,
 'poblet-2025/poblet':/кавы|дегустац/i,
 'europe-friends-2019/munich-rothenburg':/BMW|Дахау/i,
 'rockies-2018/lake-louise':/Морейн/i,
};
for(const [key,re]of Object.entries(rejected)){
 const c=audit.chapters.find(c=>c.file.split('/').slice(-3,-1).join('/')===key);
 assert.ok(c,key+': missing regression case');
 assert.ok(!c.attractions.some(id=>re.test(registry[id].title)),key+': unvisited attraction was added');
}
console.log(`Verified ${audit.summary.trips} trips, ${files.length} chapters, ${used.size} attraction definitions and ${links} links. Chapter text and photo markup unchanged; CRLF/LF differences ignored.`);
console.log(`${audit.summary.photo_only_chapters} photo-only chapters and ${audit.summary.questions} explicit identification questions remain documented; these are not claimed as a complete inventory of unnamed photographs.`);

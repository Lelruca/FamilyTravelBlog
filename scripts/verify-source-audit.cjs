// Repository validation requires only Node. Original DOCX/Drive quotations and
// photo bytes are checked separately by verify-source-audit.py.
const fs=require('node:fs'),crypto=require('node:crypto'),assert=require('node:assert/strict');
assert.equal(process.argv.length,2,'This repository check accepts no flags. Full material completeness is checked separately by verify-source-audit.py --require-complete.');
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(d+'/'+e.name):[d+'/'+e.name]);
const inventory=load('reviews/source-audit/inventory.json'),registry=load('data/attractions.json');
const types=load('data/attraction_types.json'),coordinates=load('data/place_coordinates.json');
const exported=load('data/attraction_visits.json');
const files=walk('content').filter(f=>f.endsWith('/index.md')&&!f.startsWith('content/places/'));
assert.deepEqual(new Set(files),new Set(inventory.chapters.map(c=>c.file)),'Chapter inventory changed');
assert.equal(inventory.chapters.length,files.length,'Duplicate chapter in inventory');
const accepted=new Set(['retain','add','revise_existing_definition']);
const reports=['trips','supplemental'].flatMap(dir=>fs.readdirSync('reviews/source-audit/'+dir).filter(f=>f.endsWith('.json')).map(f=>({file:'reviews/source-audit/'+dir+'/'+f,data:load('reviews/source-audit/'+dir+'/'+f)})));
const seen=new Set(),seenSources=new Set(),used=new Set(),chapterIds=new Map();
let decisions=0,links=0;
function frontMatter(file){
 const raw=fs.readFileSync(file,'utf8'),m=raw.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
 assert(m,file+': missing front matter');
 const front=m[1],inline=front.match(/^places:[ \t]*\[([^\]\r\n]*)\]/m),block=front.match(/^places:[ \t]*\r?\n((?:[ \t]+-[^\n]+\r?\n?)+)/m);
 const places=(inline?inline[1].split(','):block?block[1].trim().split('\n'):[]).map(s=>s.trim().replace(/^-\s*/,'').replace(/^['"]|['"]$/g,'')).filter(Boolean);
 const attractions=JSON.parse(front.match(/^attractions:[ \t]*(\[[^\r\n]*\])/m)?.[1]||'[]');
 assert.equal(new Set(places).size,places.length,file+': duplicate geographic tags');
 assert.equal(new Set(attractions).size,attractions.length,file+': duplicate attraction tags');
 for(const p of places){assert(fs.existsSync('content/places/'+p+'/_index.md'),file+': unknown place '+p);assert(coordinates[p],p+': missing coordinates');}
 for(const id of attractions){assert(registry[id],file+': unknown attraction '+id);used.add(id);links++;}
 chapterIds.set(file,attractions);
 return {raw,attractions,places};
}
for(const {file,data:r} of reports){
 const expected=inventory.chapters.filter(c=>c.trip_path===r.trip_path);
 assert.deepEqual(new Set(r.chapters.map(c=>c.file)),new Set(expected.map(c=>c.file)),file+': trip chapter coverage changed');
 for(const chapter of [...r.chapters,...(r.sections||[])]){
  let front,actual;
  if(chapter.file){
   assert(!seen.has(chapter.file),'Duplicate chapter report '+chapter.file);seen.add(chapter.file);
   const item=expected.find(c=>c.file===chapter.file);assert(item);
   front=frontMatter(chapter.file);
   assert.equal(crypto.createHash('sha256').update(front.raw.replaceAll('\r\n','\n')).digest('hex'),item.source_sha256_lf,chapter.file+': changed material requires review');
   assert.equal(item.text_status,chapter.text_status,chapter.file+': reading status changed');
   assert.equal(item.report,file,chapter.file+': report pointer differs');
   assert.equal(item.photos_status,chapter.photos_status||(r.photographs.status==='reviewed'?'reviewed':'unreviewed'),chapter.file+': photo status changed');
   actual=exported.chapters[chapter.file];
  }else{assert(!seenSources.has(r.source_id),'Duplicate standalone source');seenSources.add(r.source_id);actual=exported.source_reviews[r.source_id];}
  assert(actual,file+': missing evidence export');assert.equal(actual.source_review,'read');
  const visits=[],place_visits=[],acceptedIds=new Set();
  for(const o of chapter.objects){
   decisions++;assert(o.decision&&o.event&&o.evidence?.length,file+': object without decision or evidence');
   for(const e of o.evidence){
    if(e.source_file)assert(/^[0-9a-f]{64}$/.test(e.source_sha256),file+': missing evidence hash');
    if(e.source_file&&!require('node:path').isAbsolute(e.source_file)){
     assert.equal(crypto.createHash('sha256').update(fs.readFileSync(e.source_file)).digest('hex'),e.source_sha256,file+': repository evidence changed');
     if(e.quote&&e.source_file.endsWith('.md'))assert(fs.readFileSync(e.source_file,'utf8').replaceAll('\r\n','\n').includes(e.quote.replaceAll('\r\n','\n')),file+': quotation absent from chapter evidence');
    }
   }
   if(chapter.file&&chapter.photos_status==='not_required_for_text_decisions'&&o.target)assert(o.evidence.some(e=>'quote'in e),file+': photo-only target without photo review');
   if(!accepted.has(o.decision))continue;
   const visit={event:o.event,participants:o.participants||null,evidence:o.evidence,report:file,...(o.reason?{note:o.reason}:{})};
   if(o.target?.attraction){const id=o.target.attraction;assert(registry[id],file+': unknown accepted attraction '+id);acceptedIds.add(id);visits.push({id,...visit});}
   if(o.target?.places){const id=o.target.places;assert(fs.existsSync('content/places/'+id+'/_index.md'),file+': unknown accepted place '+id);place_visits.push({id,...visit});if(front)assert(front.places.includes(id),file+': missing geographic link '+id);}
  }
  assert.deepEqual(actual.visits,visits,file+': attraction export differs from source decisions');
  assert.deepEqual(actual.place_visits,place_visits,file+': geographic export differs from source decisions');
  if(front)assert.deepEqual(new Set(front.attractions),acceptedIds,chapter.file+': attraction links differ from accepted source decisions');
 }
}
assert.deepEqual(seen,new Set(files),'Missing chapter reports');
assert.deepEqual(new Set(Object.keys(exported.chapters)),seen,'Unexpected chapter exports');
assert.deepEqual(new Set(Object.keys(exported.source_reviews)),seenSources,'Unexpected standalone exports');
// The dictionary also retains historical aliases and definitions without a
// current chapter link. Presence in it is not evidence of a visit.
for(const [id,a] of Object.entries(registry)){
 assert(a.title&&a.parent&&a.types?.length&&a.search_terms?.length,id+': incomplete definition');
 assert(a.types.every(t=>types[t]),id+': unknown semantic type');
 assert(fs.existsSync('content/places/'+a.parent+'/_index.md'),id+': missing geographic parent');
 assert.equal(a.title[0],a.title[0].toLocaleUpperCase('ru'),id+': lowercase navigation title');
 if(a.place)assert(fs.existsSync('content/places/'+a.place+'/_index.md'),id+': missing historical taxonomy term');
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
 const file=files.find(f=>f.split('/').slice(-3,-1).join('/')===key);assert(file,'Missing regression chapter '+key);
 assert(!chapterIds.get(file).some(id=>re.test(registry[id].title)),key+': unvisited attraction added');
}
require('node:child_process').execFileSync(process.execPath,['scripts/source-audit-reconciliation.cjs','--check'],{stdio:'inherit'});
console.log(`${reports.length} reports; ${files.length} chapters; ${decisions} decisions; ${used.size} attractions; ${links} links verified against current source reports.`);
console.log('Repository data only. Original archive quotations/photo bytes require verify-source-audit.py. Open material limits remain; passing checks does not prove completeness.');

// Reconcile already-read source decisions with both exported data and chapter links.
// This check is not a substitute for reading source material.
const fs=require('node:fs'),assert=require('node:assert/strict');
const inventory=JSON.parse(fs.readFileSync('reviews/source-audit/inventory.json','utf8'));
const exported=JSON.parse(fs.readFileSync('data/attraction_visits.json','utf8'));
const reports=fs.readdirSync('reviews/source-audit/trips').filter(f=>f.endsWith('.json')).map(f=>({file:'reviews/source-audit/trips/'+f,...JSON.parse(fs.readFileSync('reviews/source-audit/trips/'+f,'utf8'))}));
function places(front){const block=front.match(/^places:\s*\r?\n((?:[ \t]+-[^\n]+\r?\n?)+)/m)?.[1],inline=front.match(/^places:[ \t]*\[([^\]\r\n]*)\]/m)?.[1];return new Set((block?block.trim().split('\n'):(inline||'').split(',')).map(s=>s.trim().replace(/^-\s*/,'').replace(/^['"]|['"]$/g,'')));}
const decisions=[],result=[];
for(const report of reports)for(const chapter of report.chapters){
 const front=fs.readFileSync(chapter.file,'utf8').split('---')[1],a=JSON.parse(front.match(/attractions: (\[[^\r\n]*\])/ )?.[1]||'[]'),p=places(front),exportedChapter=exported.chapters[chapter.file];
 assert(exportedChapter,'Missing chapter export '+chapter.file);
 const sourceAttractions=new Set();
 for(const o of chapter.objects){decisions.push(o);if(o.target?.attraction)sourceAttractions.add(o.target.attraction);if(!['retain','add','revise_existing_definition'].includes(o.decision))continue;
  if(o.target?.attraction){assert(a.includes(o.target.attraction),'Missing attraction link '+chapter.file+' '+o.target.attraction);assert(exportedChapter.visits.some(v=>v.id===o.target.attraction&&v.event===o.event),'Missing attraction evidence export');}
  if(o.target?.places){assert(p.has(o.target.places),'Missing geographic link '+chapter.file+' '+o.target.places);assert(exportedChapter.place_visits.some(v=>v.id===o.target.places&&v.event===o.event),'Missing geographic evidence export');}
 }
 assert(a.every(id=>sourceAttractions.has(id)),'Unexplained attraction link '+chapter.file);
 result.push({file:chapter.file,report:report.file,objects:chapter.objects.length,status:'decisions_and_links_reconciled'});
}
assert.equal(result.length,inventory.chapters.length);
const out={status:'all_current_chapter_decisions_reconciled_limits_open',chapters:result.length,trips:reports.length,object_decisions_in_chapters:decisions.length,unknown_names_and_source_limits:'reviews/source-audit/QUESTIONS.md',other_worktree_texts:'reviews/source-audit/worktree-scope.json',standalone_source_reviews:Object.keys(exported.source_reviews),method:'Полный перечень из отчётов прочитанных глав повторно сопоставлен с attraction_visits, places и attractions каждой главы. Каждая текущая объектная связь имеет решение с основанием; все принятые объектные/географические решения экспортированы и связаны с главами. Это проверка согласованности результата чтения, не доказательство абсолютного отсутствия пропусков и не заявление полного просмотра фотографий/видео.',results:result};
if(process.argv.includes('--check'))assert.deepEqual(JSON.parse(fs.readFileSync('reviews/source-audit/reconciliation.json','utf8')),out,'Saved reconciliation is stale; review changes before regenerating it');
else fs.writeFileSync('reviews/source-audit/reconciliation.json',JSON.stringify(out,null,2)+'\n');
console.log(result.length+' chapters: source decisions, exported evidence and current attraction/geographic links reconciled.');

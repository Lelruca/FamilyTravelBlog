// Export only explicit new source reviews. Absence means not audited yet.
const fs=require('node:fs');
const chapters={},source_reviews={};
const reportPaths=['reviews/source-audit/trips','reviews/source-audit/supplemental'].filter(fs.existsSync).flatMap(dir=>fs.readdirSync(dir).filter(f=>f.endsWith('.json')).map(f=>dir+'/'+f));
for(const reportPath of reportPaths){
 const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
 for(const chapter of [...report.chapters,...(report.sections||[])]){
  const visits=[],place_visits=[];
  for(const o of chapter.objects){
   if(o.target?.places&&['retain','add','revise_existing_definition'].includes(o.decision))
    place_visits.push({id:o.target.places,event:o.event,participants:o.participants||null,evidence:o.evidence,report:reportPath,...(o.reason?{note:o.reason}:{})});
   if(!o.target?.attraction||!['retain','add','revise_existing_definition'].includes(o.decision))continue;
   visits.push({id:o.target.attraction,event:o.event,participants:o.participants||null,
    evidence:o.evidence,report:reportPath,...(o.reason?{note:o.reason}:{})});
  }
  if(chapter.file)chapters[chapter.file]={source_review:'read',visits,place_visits};
  else source_reviews[report.source_id]={source_review:'read',title:report.title,site_chapter:null,visits,place_visits,report:reportPath};
 }
}
const inventory=JSON.parse(fs.readFileSync('reviews/source-audit/inventory.json','utf8'));
const allTextRead=inventory.chapters.every(c=>chapters[c.file]?.source_review==='read');
fs.writeFileSync('data/attraction_visits.json',JSON.stringify({status:allTextRead?'all_current_chapter_texts_reviewed_limits_open':'partial',default_for_unlisted_chapters:'not_audited',chapters,source_reviews},null,2)+'\n');
console.log(`Visit evidence exported for ${Object.keys(chapters).length} chapters; all others remain unaudited.`);

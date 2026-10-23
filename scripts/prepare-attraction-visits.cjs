// Export only explicit new source reviews. Absence means not audited yet.
const fs=require('node:fs');
const chapters={};
for(const file of fs.readdirSync('reviews/source-audit/trips').filter(f=>f.endsWith('.json'))){
 const reportPath='reviews/source-audit/trips/'+file;
 const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
 for(const chapter of report.chapters){
  const visits=[];
  for(const o of chapter.objects){
   if(!o.target?.attraction||!['retain','add','revise_existing_definition'].includes(o.decision))continue;
   visits.push({id:o.target.attraction,event:o.event,participants:o.participants||null,
    evidence:o.evidence,report:reportPath,...(o.reason?{note:o.reason}:{})});
  }
  chapters[chapter.file]={source_review:'read',visits};
 }
}
fs.writeFileSync('data/attraction_visits.json',JSON.stringify({status:'partial',default_for_unlisted_chapters:'not_audited',chapters},null,2)+'\n');
console.log(`Visit evidence exported for ${Object.keys(chapters).length} chapters; all others remain unaudited.`);

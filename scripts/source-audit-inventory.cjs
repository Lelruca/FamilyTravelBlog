// Inventory is derived from source files, never from the old attraction list.
// It intentionally does not mark a chapter read or identify any objects.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const walk = dir => fs.readdirSync(dir, {withFileTypes:true}).flatMap(e => e.isDirectory() ? walk(`${dir}/${e.name}`) : [`${dir}/${e.name}`]);
const hash = text => crypto.createHash('sha256').update(text.replaceAll('\r\n','\n')).digest('hex');
const file = 'reviews/source-audit/inventory.json';
const previous = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file,'utf8')) : {chapters:[]};
const previousChapters = new Map(previous.chapters.map(c => [c.file,c]));
const chapters = walk('content').filter(f => f.endsWith('/index.md') && !f.startsWith('content/places/')).sort().map(f => {
  const raw = fs.readFileSync(f,'utf8');
  const front = raw.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1] || '';
  const trip = path.posix.basename(path.posix.dirname(path.posix.dirname(f)));
  const currentHash = hash(raw);
  const old = previousChapters.get(f);
  return {file:f, trip, trip_path:path.posix.dirname(path.posix.dirname(f)), title:front.match(/^title:\s*(.+)$/m)?.[1] || '', draft:/^draft:\s*true\s*$/m.test(front), source_sha256_lf:currentHash,
    text_status:old?.source_sha256_lf === currentHash ? old.text_status : 'unread',
    photos_status:old?.source_sha256_lf === currentHash ? old.photos_status : 'unreviewed',
    reconciliation_status:old?.source_sha256_lf === currentHash ? old.reconciliation_status : 'pending',
    report:old?.report || null};
});
const result = {version:2, status:'in_progress', baseline_commit:previous.baseline_commit || cp.execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
  scope:'Every chapter in content, including drafts. Sources and photographs require separate explicit review; file discovery is not reading.',
  cross_worktree_scope:previous.cross_worktree_scope || 'pending_reconciliation_of_other_active_drafts',
  trips:[...new Set(chapters.map(c=>c.trip_path))].sort(), chapters};
if(process.argv.includes('--sync-reports')){
  const dir='reviews/source-audit/trips';
  for(const name of fs.readdirSync(dir).filter(f=>f.endsWith('.json'))){
    const report=JSON.parse(fs.readFileSync(`${dir}/${name}`,'utf8'));
    for(const c of chapters.filter(c=>c.trip_path===report.trip_path)){
      const reviewed=report.chapters.find(r=>r.file===c.file);
      if(!reviewed)continue;
      c.text_status=reviewed.text_status;
      c.photos_status=reviewed.photos_status || (report.photographs.status==='reviewed'?'reviewed':'unreviewed');
      c.reconciliation_status=report.status==='complete'?'complete':report.reconciliation?.status || (c.photos_status==='reviewed'?'identifications_open':'pending');
      c.report=`${dir}/${name}`;
    }
  }
}
fs.mkdirSync(path.dirname(file),{recursive:true});
fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');
console.log(`${result.trips.length} trips, ${chapters.length} chapters; read ${chapters.filter(c=>c.text_status==='read').length}; photos reviewed ${chapters.filter(c=>c.photos_status==='reviewed').length}. Audit remains in progress.`);

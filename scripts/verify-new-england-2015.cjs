const fs=require('fs'),assert=require('assert/strict');const w='.tmp/new-england-2015',d=JSON.parse(fs.readFileSync(w+'/photo-manifest.json')),ps=JSON.parse(fs.readFileSync(w+'/paragraphs.json','utf8').replace(/^\uFEFF/,''));const slugs=['cape-cod','pilgrims','settlement','boston','american-revolution','industrial-revolution','gilded-age','cultural-heritage'];
const normalize=s=>s.replace(/<[^>]+>/g,'').replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;|&apos;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&nbsp;/g,'\u00a0').replace(/&hellip;/g,'…').trim();let count=0,photoCount=0;
for(const [ci,ch]of d.chapters.entries()){
 const md=fs.readFileSync('content/americas/usa/new-england-2015/'+slugs[ci]+'/index.md','utf8');
 const source=ps.slice(ch.start+1,ch.end).flatMap(s=>s.replace(/<\/?lj-cut\b[^>]*>/g,'').split(/<img\b[^>]*>/)).map(normalize).filter(Boolean);
 const actual=[...md.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m=>normalize(m[1]));assert.deepEqual(actual,source,'Source text '+ch.title);count+=source.length;
 const html=fs.readFileSync(w+'/rendered/americas/usa/new-england-2015/'+slugs[ci]+'/index.html','utf8');const body=html.match(/<div class="essay-body">([\s\S]*?)<\/div>\s*<nav class="essay-navigation"/)?.[1];assert.ok(body,'Rendered body');assert.deepEqual([...body.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m=>normalize(m[1])),source,'Rendered text '+ch.title);
 const expected=d.photos.filter(p=>p.chapter===ci+1&&p.displayURL).map(p=>p.driveId).sort();
 const article=html.match(/<article class="photo-essay">([\s\S]*?)<\/article>/)[1];const shown=[...article.matchAll(/<img\b[^>]*src="([^"]+)"/g)].map(m=>m[1].match(/\/d\/([^=]+)=/)?.[1]).sort();assert.deepEqual(shown,expected,'Photos exactly once '+ch.title);photoCount+=shown.length;
 assert.ok(html.includes('Глава '+(ci+1)+' из 8'),'Chapter navigation');
}
const checks=JSON.parse(fs.readFileSync(w+'/drive-check.json'));assert.equal(checks.length,51);assert.ok(checks.every(x=>x.ok));console.log({chapters:8,verbatimParagraphs:count,photosExactlyOnce:photoCount,workingDriveLinks:checks.length,missing:d.photos.filter(p=>p.status==='unavailable').length});

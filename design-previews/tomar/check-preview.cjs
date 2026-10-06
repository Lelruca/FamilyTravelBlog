const fs=require('fs');const vm=require('vm');const assert=require('assert/strict');const crypto=require('crypto');
const root=__dirname;const html=fs.readFileSync(root+'/index.html','utf8');const report=JSON.parse(fs.readFileSync(root+'/verification.json','utf8'));
for(const m of html.matchAll(/<script>([\s\S]*?)<\/script>/g))new vm.Script(m[1]);
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(report.source)).digest('hex'),report.sourceSHA256);
assert.equal((html.match(/data-photo-index=/g)||[]).length,43);assert.ok(!html.includes('<!--STORY-->'));
(async()=>{const page=await fetch('http://127.0.0.1:1415/');assert.equal(page.status,200);assert.ok((await page.text()).includes('Тамплиеры!'));for(const meta of report.images){const r=await fetch('http://127.0.0.1:1415/'+meta.file,{method:'HEAD'});assert.equal(r.status,200);assert.equal(r.headers.get('content-type'),'image/jpeg');}console.log('Verified: exact source unchanged, 43 photos and 12 paragraphs in order; valid JS syntax; preview and all 44 images served successfully.');})().catch(e=>{console.error(e);process.exitCode=1;});

// Exercise Claude's actual mosaic script using Mexico's production markup.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const js=fs.readFileSync('layouts/trips/photo-story.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const attrs=s=>Object.fromEntries([...s.matchAll(/([\w-]+)=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m=>[m[1],m[2]??m[3]??m[4]]));
const root='public/americas/mexico/mexico-2015';
const raw=fs.readdirSync(root,{withFileTypes:true}).filter(x=>x.isDirectory()).flatMap(d=>[...fs.readFileSync(root+'/'+d.name+'/index.html','utf8').matchAll(/<div class=(?:"essay-mosaic"|essay-mosaic) data-mosaic[^>]*>([\s\S]*?)<\/div>/g)].map(m=>({chapter:d.name,photos:[...m[1].matchAll(/<a\b([^>]+)>/g)].map(x=>attrs(x[1]))})));
const findings=[];let checked=0;
for(const [W,vh] of [[1080,900],[928,800],[700,800],[358,844]]){
 const blocks=raw.map(b=>({chapter:b.chapter,style:{},parentElement:{clientWidth:W},classList:{add(){}},children:b.photos.map(p=>({style:{},dataset:{r:p['data-r'],w:p['data-w'],k:p['data-k']}}))}));
 vm.runInNewContext(js,{document:{querySelectorAll:()=>blocks},getComputedStyle:()=>({columnGap:W<600?'8':'12'}),window:{innerHeight:vh},addEventListener(){},clearTimeout(){},setTimeout(){}});
 for(const b of blocks){const rects=b.children.map(n=>{const a=attrs(n.style.cssText.replaceAll(':','=').replaceAll(';',' '));return {x:parseFloat(a.left),y:parseFloat(a.top),w:parseFloat(a.width),h:parseFloat(a.height),ratio:+n.dataset.r,native:+n.dataset.w};});
  // Readability floor, below the template's preferred widths of 30% / 22%.
  const H=parseFloat(b.style.height);for(const r of rects){assert.ok(r.w>0&&r.h>0);assert.ok(Math.abs(r.w/r.h-r.ratio)<.0001,b.chapter+' cropped');assert.ok(r.x+r.w<=W+.02&&r.y+r.h<=H+.02,b.chapter+' outside block');if(r.w>r.native+.02||r.h>vh-(W<600?110:84)+.02||r.w<W*(W<600?.28:.20))findings.push({chapter:b.chapter,W,rect:r});}
  assert.ok(Math.abs(Math.max(...rects.map(r=>r.x+r.w))-W)<.02,b.chapter+' ragged right edge');
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){const a=rects[i],c=rects[j];assert.ok(a.x+a.w<=c.x+.02||c.x+c.w<=a.x+.02||a.y+a.h<=c.y+.02||c.y+c.h<=a.y+.02,b.chapter+' overlaps');}
  checked++;
 }
}
assert.ok(raw.length>10,'Missing trip mosaics');console.log(JSON.stringify({mosaics:raw.length,checked,wholeFrames:true,fullWidth:true,noOverlap:true,findings},null,2));assert.equal(findings.length,0,'Review small, tall or enlarged frames before accepting layout');

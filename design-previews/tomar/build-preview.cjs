const fs=require('fs');const path=require('path');const crypto=require('crypto');const assert=require('assert/strict');
const root=__dirname;const sourcePath=path.resolve(root,'../../content/europe/portugal/portugal-spain-2016/tomar-batalha-nazare/index.md');
const source=fs.readFileSync(sourcePath,'utf8');const body=source.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/,'');
const title=JSON.parse(source.match(/^title: (.*)$/m)[1]);const hero=JSON.parse(source.match(/^hero_image: (.*)$/m)[1]);
const escape=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const sourceEvents=[];const blocks=[];let group=0;
for(const match of body.split(/(\{\{< photoscroller items="[^"]+" >\}\})/g)){
 if(match.startsWith('{{<')){const urls=match.match(/items="([^"]+)"/)[1].split(',');blocks.push({type:'gallery',group:++group,urls});sourceEvents.push(...urls.map(url=>({type:'photo',url})));}
 else for(const text of match.trim().split(/\r?\n\s*\r?\n/)){if(text.trim()){const p=text.replace(/\r?\n/g,'\n');blocks.push({type:'text',text:p});sourceEvents.push({type:'text',text:p});}}
}
const urls=[...new Set([hero,...sourceEvents.filter(e=>e.type==='photo').map(e=>e.url)])];fs.mkdirSync(path.join(root,'photos'),{recursive:true});
function dimensions(b){if(b.readUInt32BE(0)===0x89504e47)return {width:b.readUInt32BE(16),height:b.readUInt32BE(20)};let i=2;while(i+8<b.length){if(b[i++]!==255)continue;const marker=b[i++];if(marker===0xd8||marker===0xd9)continue;const len=b.readUInt16BE(i);if([0xc0,0xc1,0xc2].includes(marker))return {width:b.readUInt16BE(i+5),height:b.readUInt16BE(i+3)};if(len<2)break;i+=len;}throw Error('Unsupported image format');}
const images=new Map();let cursor=0;
async function worker(){while(cursor<urls.length){const url=urls[cursor++];const id=new URL(url).searchParams.get('id');const file='photos/'+id+'.jpg';const full=path.join(root,file);let b;if(fs.existsSync(full))b=fs.readFileSync(full);else{let last;for(let a=0;a<3;a++){try{const r=await fetch(url.replace(/sz=w\d+/,'sz=w1200'),{signal:AbortSignal.timeout(45000)});if(!r.ok||!r.headers.get('content-type')?.startsWith('image/'))throw Error('Image HTTP '+r.status);b=Buffer.from(await r.arrayBuffer());dimensions(b);fs.writeFileSync(full,b);break;}catch(e){last=e;}}if(!b)throw last;}images.set(url,{file,...dimensions(b)});}}
(async()=>{await Promise.all(Array.from({length:6},worker));let index=0;
const img=(url,extra='')=>{const meta=images.get(url);return `<img src="${meta.file}" width="${meta.width}" height="${meta.height}" alt="" ${extra}>`;};
const fragments=blocks.map(b=>{if(b.type==='text')return `<div class="story-text"><p>${escape(b.text)}</p></div>`;return `<section class="photo-scene" aria-label="Группа ${b.group}: ${b.urls.length} фотографий"><div class="photo-layout">${b.urls.map(url=>`<button type="button" class="photo" data-photo-index="${index++}" data-ratio="${images.get(url).width/images.get(url).height}" aria-label="Открыть фотографию ${index}">${img(url,'loading="lazy"')}</button>`).join('')}</div><div class="scene-count">${b.urls.length} ${b.urls.length===1?'фотография':b.urls.length<5?'фотографии':'фотографий'}</div></section>`;}).join('\n');
let html=fs.readFileSync(path.join(root,'template.html'),'utf8').replaceAll('<!--CHAPTER_TITLE-->',escape(title)).replace('<!--HERO_IMAGE-->',img(hero,'fetchpriority="high"')).replace('<!--STORY-->',fragments);
fs.writeFileSync(path.join(root,'index.html'),html);
const actual=[];for(const m of fragments.matchAll(/<p>([\s\S]*?)<\/p>|data-photo-index="(\d+)"/g)){if(m[1]!==undefined)actual.push({type:'text',text:m[1].replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&')});else actual.push(sourceEvents.filter(e=>e.type==='photo')[Number(m[2])]);}assert.deepEqual(actual,sourceEvents);assert.equal(fs.readFileSync(sourcePath,'utf8'),source);
fs.writeFileSync(path.join(root,'verification.json'),JSON.stringify({source:sourcePath,sourceSHA256:crypto.createHash('sha256').update(source).digest('hex'),title,paragraphs:blocks.filter(b=>b.type==='text').length,photos:index,groups:group,exactTextAndPhotoSequence:true,images:[...images.values()]},null,2));
console.log(JSON.stringify({paragraphs:blocks.filter(b=>b.type==='text').length,photos:index,groups:group,downloaded:images.size,exactTextAndPhotoSequence:true}));})();

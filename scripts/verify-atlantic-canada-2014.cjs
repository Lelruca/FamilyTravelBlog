const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

// Read the authoritative DOCX afresh; do not rely on a previous extraction.
const extract = String.raw`
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $PWD 'Отчеты/2014_ Атлантическая Канада.docx'))
$reader=[IO.StreamReader]::new($zip.GetEntry('word/document.xml').Open())
[xml]$xml=$reader.ReadToEnd(); $reader.Close()
$ns=[Xml.XmlNamespaceManager]::new($xml.NameTable)
$ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
$i=0
$paragraphs=@($xml.SelectNodes('//w:body/w:p',$ns) | ForEach-Object {
 $text=($_.SelectNodes('.//w:t | .//w:br | .//w:tab',$ns) | ForEach-Object {
  if($_.LocalName -eq 't'){$_.InnerText}elseif($_.LocalName -eq 'tab'){[char]9}else{[char]10}
 }) -join ''
 @{index=$i; text=$text}; $i++
})
$zip.Dispose()
ConvertTo-Json -InputObject $paragraphs -Depth 4 -Compress
`;
const source = JSON.parse(execFileSync('powershell.exe', ['-NoProfile', '-Command', extract], {encoding:'utf8', maxBuffer:8*1024*1024}));
const manifest = JSON.parse(fs.readFileSync('media-manifests/atlantic-canada-2014.json', 'utf8'));
const photoData = JSON.parse(fs.readFileSync('data/photos/atlantic-canada-2014.json', 'utf8'));
const photoID = url => {
 const driveID = url.match(/[?&]id=([\w-]+)/)?.[1] || url.match(/\/d\/([\w-]+)=/)?.[1];
 if (driveID) return driveID;
 const pathname = new URL(url, 'http://local.invalid').pathname;
 return manifest.r2?.photos.find(p => new URL(p.url).pathname === pathname)?.driveId;
};
const photoURL = key => photoData[key].url || `${manifest.r2.publicBase}atlantic-canada-2014/${key}`;
const decode = s => s.replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const textContent = s => decode(s.replace(/<[^>]*>/g, '')).replace(/\r\n/g, '\n');
const titleStarts = source.filter(p=>/^(Атлантика|День \d)/.test(p.text.trim())).map(p=>p.index);
assert.equal(manifest.chapters.length, titleStarts.length);
assert.equal(manifest.photos.length, 300);
const base = process.env.TRAVEL_VERIFY_BASE_URL || 'http://127.0.0.1:1313/';
async function page(route) {
 if (process.env.TRAVEL_VERIFY_BUILD_DIR) return fs.readFileSync(path.join(process.env.TRAVEL_VERIFY_BUILD_DIR, route, 'index.html'), 'utf8');
 const r = await fetch(new URL(route, base));
 assert.equal(r.status, 200, route);
 return r.text();
}

(async()=>{
 let paragraphs=0, photographs=0, photoBlocks=0;
 const uniquePhotos=new Set();
 for(const [ci,ch] of manifest.chapters.entries()) {
  assert.equal(ch.start, titleStarts[ci]);
  const end=titleStarts[ci+1]??source.length;
  const sourceTitle=source[ch.start].text.replace(/<img[\s\S]*/, '').trim();
  const md=fs.readFileSync(ch.file, 'utf8');
  assert.equal(JSON.parse(md.match(/^title: (.*)$/m)[1]), sourceTitle);
  const expected=[];
  for(const p of source.slice(ch.start,end)) {
   let text=p.text;
   if(p.index===ch.start)text=text.replace(sourceTitle,'');
   text=text.replace(/<\/?lj-cut\b[^>]*>/g,'');
   let last=0;
   const add=t=>{if(t.trim())expected.push({type:'text',text:textContent(t)});};
   for(const m of text.matchAll(/<img\b[^>]*src="([^"]+)"[^>]*>/g)) {
    add(text.slice(last,m.index));
    const photo=manifest.photos.find(photo=>photo.chapter===ci+1&&photo.sourceParagraph===p.index&&photo.sourceURL===m[1]);
    assert.ok(photo, 'Missing source mapping at paragraph '+p.index);
    assert.equal(photo.order,photo.displayOrder);
    expected.push({type:'photo',url:photo.displayURL});
    last=m.index+m[0].length;
   }
   add(text.slice(last));
  }
  const actual=[];
  for(const m of md.matchAll(/<p>([\s\S]*?)<\/p>|\{\{< (?:row|mosaic) "([^"]+)" >\}\}/g)) {
   if(m[1]!==undefined)actual.push({type:'text',text:textContent(m[1])});
   else actual.push(...m[2].split(' ').map(name=>({type:'photo',url:photoURL(path.basename(path.dirname(ch.file))+'/'+name.replace(/^[LRT]:/,''))})));
  }
  const hero=JSON.parse(md.match(/^hero_image: (.*)$/m)[1]);
  const chapter=path.basename(path.dirname(ch.file));
  const heroURL=photoURL(chapter+'/'+hero);
  const id=photoID(heroURL);
  assert.deepEqual(actual.filter(e=>e.type==='text'),expected.filter(e=>e.type==='text'),'Verbatim text and paragraph boundaries: '+sourceTitle);
  // Photo order within a group is free; its anchor in the author's text is preserved.
  const anchored = events => {
   const groups=new Map(); let anchor=0;
   for(const event of events) {
    if(event.type==='text') { anchor++; continue; }
    const photo=photoID(event.url); if(photo===id)continue;
    if(!groups.has(anchor))groups.set(anchor,[]); groups.get(anchor).push(photo);
   }
   return [...groups].map(([anchor,ids])=>[anchor,ids.sort()]);
  };
  assert.deepEqual(anchored(actual),anchored(expected),'Photo groups stay next to their original paragraphs: '+sourceTitle);
  const route=ch.file.replace(/^content\//,'').replace(/index.md$/,'');
  const html=await page(route);
  const h1=html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/);
  assert.equal(textContent(h1[1]),sourceTitle,'Rendered title: '+route);
  assert.match(md,/^layout: "photo-story"$/m);
  const prose=html.match(/<div class="?essay-body"?>([\s\S]*?)<nav class="?essay-navigation"?/)?.[1];
  assert.ok(prose,'Shared photo story body: '+route);
  const renderedParagraphs=[...prose.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m=>textContent(m[1]));
  const visibleWhitespace = s => s.replace(/\s+/g,' ').trim();
  assert.deepEqual(renderedParagraphs.map(visibleWhitespace),expected.filter(e=>e.type==='text').map(e=>visibleWhitespace(e.text)),'Rendered text: '+route);
  const renderedImages=[...html.matchAll(/<a\b[^>]*href=(?:"([^"]+)"|([^\s>]+))[^>]*data-photo-lightbox/g)].map(m=>photoID(decode(m[1]||m[2])));
  const expectedImages=[...new Set([id,...expected.filter(e=>e.type==='photo').map(e=>photoID(e.url))])];
  assert.deepEqual(renderedImages.slice().sort(),expectedImages.sort(),'All photos rendered once: '+route);
  assert.equal(new Set(renderedImages).size,renderedImages.length,'No repeated cover: '+route);
  assert.equal(id,photoID(ch.heroImage),'Selected hero preserved');
  const selected=manifest.photos.find(p=>p.driveFileId===id);
  assert.ok(selected.width>selected.height,'Horizontal hero: '+route);
  assert.ok(html.includes(manifest.r2 ? heroURL : '/d/'+id+'=w2000'),'Full-size hero');
  const placeSlugs=md.match(/^places:\n((?:  - [^\n]+\n)+)/m)?.[1].match(/(?<=  - )[^\n]+/g)??[];
  for(const slug of placeSlugs)assert.ok((await page('places/'+slug+'/')).includes('/'+route),'Place association '+slug);
  paragraphs+=renderedParagraphs.length;
  photographs+=renderedImages.length;
  renderedImages.forEach(id=>uniquePhotos.add(id));
  photoBlocks+=(md.match(/\{\{< (?:row|mosaic) /g)||[]).length;
 }
 const trip='americas/canada/atlantic-canada-2014/';
 for(const route of ['', 'americas/canada/', 'trip-year/2014/', trip])assert.ok((await page(route)).includes(trip),'Trip discovery: '+route);
 const tripHTML=await page(trip);
 const coverURL = manifest.r2?.photos.find(p => p.key === manifest.r2.verification.coverKey)?.url;
 assert.ok(tripHTML.includes(coverURL || '1QfWxGRh4rLxXLog6XrVY349vfZqp9-sl'),'Owner-selected cover preserved');
 assert.equal(manifest.coverImage,'https://drive.google.com/thumbnail?id=1QfWxGRh4rLxXLog6XrVY349vfZqp9-sl&sz=w2000');
 for(const photo of manifest.photos) {
  assert.match(photo.displayURL,/^https:\/\/drive\.google\.com\/thumbnail\?id=[^&]+&sz=w1600$/);
  assert.match(photo.archiveFile,/^\d{2} - [^/]+\/\d{2}_[^/]+$/);
 }
 assert.equal(uniquePhotos.size,300,'All 300 original photos preserved');
 const report={chapters:manifest.chapters.length,verbatimParagraphs:paragraphs,uniquePhotos:uniquePhotos.size,photoAppearances:photographs,photoBlocks,paragraphBoundaries:'original',horizontalHeroes:manifest.chapters.length,cover:'IMG_4220.JPG',pages:process.env.TRAVEL_VERIFY_BUILD_DIR?'production HTML':'HTTP 200',source:'fresh DOCX extraction'};
 console.log(JSON.stringify(report,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});

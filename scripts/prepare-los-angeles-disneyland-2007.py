"""Prepare owner-selected photos for the Los Angeles chapter; preserve pending Disneyland."""
from pathlib import Path
import json,hashlib,shutil,sys,html
from PIL import Image,ImageOps
root=Path(__file__).resolve().parents[1];slug='los-angeles-disneyland-2007';mf=root/'media-manifests'/f'{slug}.json';m=json.loads(mf.read_text(encoding='utf-8'));archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
if '--display' in sys.argv:
 assert m['storage']['drive_sync_verified'] and all(o.get('drive_id') and not o['drive_id'].startswith('local') for o in m['photos']),'Cloud originals must be verified first'
 copies=[];data={}
 for o in m['photos']:
  src=archive/o['archive_name'];assert hashlib.sha256(src.read_bytes()).hexdigest()==o['sha256'];dest=root/'static/r2'/o['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
  with Image.open(src) as raw:
   im=ImageOps.exif_transpose(raw)
   if max(im.size)<=2000 and o['exif_orientation']==1:shutil.copy2(src,dest)
   else:
    im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
   c=dict(key=o['r2_key'],original_archive_name=o['archive_name'],width=im.width,height=im.height,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest());copies.append(c);data[o['chapter']+'/'+o['site_filename']]={'w':im.width,'h':im.height}
 m['r2']={'photos':copies,'status':'awaiting-public-verification'};(root/'data/photos'/f'{slug}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
f=lambda *ns:[f'img_{n}.jpg' for n in ns]
if 'la_layout' not in m:
 m['la_layout']={'city':[f(4181,4183,4186),f(4189,4190,4194)],'aquarium':[f(4201,4198,4199),f(4209,4215,4229),f(4225,4233,4253),f(4234,4251)],'queen-mary':[f(4264,4273,4276),f(4280,4283,4286),f(4292,4287,4295)],'submarine':[f(4296,4298),f(4299,4301,4303,4304)],'hollywood':[f(4305,4307,4308)]};m['mosaic_blocks']=f(4189,4201,4225,4264,4292,4299,4305);m['featured_photos']=f(4189,4201,4264,4292,4305)
body=[]
def paragraph(p):body.append('<p>'+html.escape(p,quote=False)+'</p>')
def photos(key):
 for block in m['la_layout'][key]:
  kind='mosaic' if block[0] in m['mosaic_blocks'] else 'row';names=[('L:' if kind=='mosaic' and n in m['featured_photos'] else '')+n for n in block];body.append('{{< '+kind+' "'+' '.join(names)+'" >}}')
for p in m['rendered_paragraphs'][:-1]:paragraph(p)
last=m['rendered_paragraphs'][-1];markers=['Ну, не совсем города','Рядом стояла советская подводная лодка','Потом мы заехали в Голливуд','А потом нас ждал Диснейленд.'];cuts=[0]+[last.index(s) for s in markers]+[len(last)];parts=[last[a:b] for a,b in zip(cuts,cuts[1:])];assert ''.join(parts)==last
m['la_text_sections']=[dict(paragraph=15,start=a,end=b) for a,b in zip(cuts,cuts[1:])];m['la_text_layout_note']='Only the owner-authorized edited ending is divided at scene transitions; every edited character retained.'
# The owner is adding the aquarium recollection separately. Keep it identifiable in metadata.
paragraph(parts[0]);photos('city')
if m.get('aquarium_block_heading'):body.append('<h2>'+html.escape(m['aquarium_block_heading'])+'</h2>')
for p in m.get('aquarium_author_paragraphs',[]):paragraph(p)
photos('aquarium');paragraph(parts[1]);photos('queen-mary');paragraph(parts[2]);photos('submarine');paragraph(parts[3]);photos('hollywood');
if not m.get('disney_intro_from_la'):paragraph(parts[4])
body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}.essay-body>p:nth-of-type(n+9):nth-of-type(-n+13){margin-bottom:.35em}</style>')
chapter=root/m['contentDir']/'los-angeles/index.md';front=chapter.read_text(encoding='utf-8').split('---',2)[1];chapter.write_text('---'+front+'---\n\n'+'\n\n'.join(body)+'\n',encoding='utf-8')
if m.get('disney_layout'):
 disney=[]
 for i,p in enumerate(m['disney_rendered_paragraphs'],1):
  disney.append('<p>'+html.escape(p,quote=False)+'</p>')
  for block in m['disney_layout_by_paragraph'].get(str(i),[]):
   kind='mosaic' if block[0] in m['mosaic_blocks'] else 'row';names=[('L:' if kind=='mosaic' and n in m['featured_photos'] else '')+n for n in block];disney.append('{{< '+kind+' "'+' '.join(names)+'" >}}')
 disney.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
 chapter=root/m['contentDir']/'disneyland/index.md';front=chapter.read_text(encoding='utf-8').split('---',2)[1];chapter.write_text('---'+front+'---\n\n'+'\n\n'.join(disney)+'\n',encoding='utf-8')
if m.get('cover_image'):
 trip=root/m['contentDir']/'_index.md';text=trip.read_text(encoding='utf-8');text=text.split('cover_image:')[0] if 'cover_image:' in text else text.rsplit('---',1)[0]
 text+='cover_image: '+json.dumps('https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+slug+'/'+m['cover_image'])+'\n'
 if m.get('cover_position'):text+='cover_position: '+json.dumps(m['cover_position'])+'\n'
 trip.write_text(text+'---\n',encoding='utf-8')
for rel in ['_index.md','los-angeles/index.md','disneyland/index.md']:
 p=root/m['contentDir']/rel;txt=p.read_text(encoding='utf-8');txt=txt.replace('draft: true','draft: '+str(m['publication']['draft']).lower()).replace('draft: false','draft: '+str(m['publication']['draft']).lower());p.write_text(txt,encoding='utf-8')
out=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(out,encoding='utf-8');(archive/'photo-manifest.json').write_text(out,encoding='utf-8');print('Prepared trip:',len(m['photos']),'archived photos;',sum(len(b) for v in m['la_layout'].values() for b in v),'LA and',sum(len(b) for b in m.get('disney_layout',[])),'Disneyland photos displayed; owner text preserved.')

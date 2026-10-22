"""Reproduce the complete 2009 report and five chapters from verified Drive originals."""
from pathlib import Path
import json,hashlib,shutil,sys,html,zipfile
import xml.etree.ElementTree as ET
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
SLUG='germany-london-2009'
cfg=json.loads((ROOT/'scripts/trip-configs'/f'{SLUG}.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/cfg['archive_root']
mf=ROOT/'media-manifests'/f'{SLUG}.json'
if mf.exists():m=json.loads(mf.read_text(encoding='utf-8'))
else:
 assert '--archive' in sys.argv
 src=Path(cfg['source']);rel='Источники/'+src.name;dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(src,dest)
 assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest()
 m=dict(trip=SLUG,title=cfg['title'],contentDir=cfg['contentDir'],archive_root=cfg['archive_root'],source=dict(path=str(src),archive_name=rel,sha256=hashlib.sha256(src.read_bytes()).hexdigest()),photos=[],reference_labels=[],drive_sync_verified=False,storage=dict(originals_verified=True,drive_sync_verified=False,r2_verified=False),publication=dict(draft=True,authorized=False),cover_image=cfg['cover_image'],cover_selection=cfg['cover_selection'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=archive/m['source']['archive_name'];assert sha(source)==m['source']['sha256']
with zipfile.ZipFile(source) as z:doc=ET.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
for c in cfg['chapters']:
 for fragment in c['fragments']:
  assert ps[fragment['source_index']].strip()[fragment['start']:fragment['end']]==fragment['text']
fragments=[f for c in cfg['chapters'] for f in c['fragments']]
ordered=sorted(fragments,key=lambda f:(f['source_index'],f['start']))
indices=sorted({f['source_index'] for f in ordered})
assert indices==list(range(37,75)), 'Missing source paragraphs'
for index in indices:
 text=ps[index].strip();start,end=cfg.get('source_ranges',{}).get(str(index),[0,len(text)])
 assert ''.join(f['text'] for f in ordered if f['source_index']==index)==text[start:end], 'Missing or repeated author text'
if '--archive' in sys.argv:
 for c in cfg['chapters']:
  names=[c['hero_image']]+[n for f in c['fragments'] for block in f.get('photo_blocks',[]) for n in block['names']]
  assert len(names)==len(set(names)) or (c['slug']=='birthday' and names.count('PB080528.JPG')==2)
  for i,n in enumerate(names,1):
   existing=next((o for o in m['photos'] if o['chapter']==c['slug'] and o['site_filename']==n),None)
   if existing:assert sha(archive/existing['archive_name'])==existing['sha256'];continue
   original=Path(cfg.get('photo_sources',{}).get(n,str(Path(cfg['photo_folder'])/n)))
   rel=c['folder']+f'/{i:02}_{original.name}';dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():shutil.copy2(original,dest)
   assert sha(original)==sha(dest)
   with Image.open(dest) as im:
    e=im.getexif();w,h=ImageOps.exif_transpose(im).size;date=e.get_ifd(34665).get(36867) or e.get(306)
   m['photos'].append(dict(source_name=original.name,source_path=str(original),archive_name=rel,sha256=sha(dest),bytes=dest.stat().st_size,width=w,height=h,exif_date=date,exif_orientation=e.get(274,1),chapter=c['slug'],site_filename=n,r2_key=SLUG+'/'+c['slug']+'/'+n))
 m['drive_sync_verified']=False;m['storage']['drive_sync_verified']=False
 m['storage']['r2_verified']=False
 m['source']['all_source_paragraphs']=[p if i in indices else '' for i,p in enumerate(ps)]
 m['source'].pop('excerpts',None);m['source']['fragment_usages']=[dict(chapter=c['slug'],source_index=f['source_index'],start=f['start'],end=f['end']) for c in cfg['chapters'] for f in c['fragments']]
 m['author_paragraphs']=[ps[i].strip()[slice(*cfg.get('source_ranges',{}).get(str(i),[0,len(ps[i].strip())]))] for i in indices];m['source']['paragraph_indices']=indices;m['source']['ranges']=cfg.get('source_ranges',{})
if '--display' in sys.argv:
 assert m['drive_sync_verified'] and m['storage']['drive_sync_verified']
 previous={o['key']:o for o in m.get('r2',{}).get('photos',[])};copies=[];data={}
 for o in m['photos']:
  src=archive/o['archive_name'];assert sha(src)==o['sha256']
  dest=ROOT/'static/r2'/o['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
  with Image.open(src) as raw:
   im=ImageOps.exif_transpose(raw);rotation=cfg.get('rotations',{}).get(o['site_filename'],0)
   if rotation:im=im.rotate(rotation,expand=True)
   im.thumbnail((2000,2000));w,h=im.size
   if max(raw.size)<=2000 and o['exif_orientation']==1 and not rotation:shutil.copy2(src,dest)
   else:im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
  record=dict(rotation_degrees=rotation,key=o['r2_key'],original_archive_name=o['archive_name'],width=w,height=h,bytes=dest.stat().st_size,sha256=sha(dest))
  old=previous.get(record['key'])
  if old and old['sha256']==record['sha256'] and old.get('public_verified'):record.update(public_verified=True,public_url=old['public_url'])
  copies.append(record);data[o['chapter']+'/'+o['site_filename']]={'w':w,'h':h}
 m['r2']={'photos':copies,'status':'awaiting-public-verification'}
 (ROOT/'data/photos'/f'{SLUG}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '--archive' not in sys.argv:
 def front(d):return '---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in d.items())+'\n---\n\n'
 trip=ROOT/cfg['contentDir'];trip.mkdir(exist_ok=True,parents=True)
 fm=dict(title=cfg['title'],type='trips',draft=m['publication']['draft'],date=cfg['date'],trip_year=2009,trip_start=cfg['trip_start'],trip_end=cfg['trip_end'],continent='Европа',country=cfg['country'],geo_countries=cfg['geo_countries'],readable_photos=True,strict_photo_cap=True,cover_image='https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+SLUG+'/'+cfg['cover_image'])
 fm.update(cfg['cover_details'])
 (trip/'_index.md').write_text(front(fm).rstrip()+'\n',encoding='utf-8')
 for weight,c in enumerate(cfg['chapters'],1):
  body=[]
  for f in c['fragments']:
   body.append('<p>'+html.escape(f['text'],quote=False)+'</p>')
   for block in f.get('photo_blocks',[]):body.append('{{< '+block['kind']+' "'+' '.join(block['names'])+'" >}}')
  body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
  folder=trip/c['slug'];folder.mkdir(exist_ok=True)
  fm=dict(title=c['title'],draft=m['publication']['draft'],date=cfg['date'],weight=weight,chapter_kind='Заметка',layout='photo-story',city=c['city'],places=c['places'],hero_image=c['hero_image'],hero_card_image=c['hero_card_image'],auto_gallery=False)
  (folder/'index.md').write_text(front(fm)+'\n\n'.join(body)+'\n',encoding='utf-8')
m['cover_details']=cfg['cover_details'];m['chapters']=cfg['chapters'];m['rendered_paragraphs']=[f['text'] for f in fragments];m['text_authorization']=cfg['text_authorization']
out=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(out,encoding='utf-8');(archive/'photo-manifest.json').write_text(out,encoding='utf-8')
print(SLUG,len(cfg['chapters']),'chapters,',len(m['photos']),'originals,',len(fragments),'exact source fragments')

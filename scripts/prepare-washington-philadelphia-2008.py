"""Prepare Washington–Philadelphia 2008: original archive first, display copies second."""
from pathlib import Path
import json,hashlib,shutil,sys,html,zipfile,xml.etree.ElementTree as E
from PIL import Image,ImageOps
root=Path(__file__).resolve().parents[1];slug='washington-philadelphia-2008'
mf=root/'media-manifests'/f'{slug}.json';base=Path('G:/My Drive/Family Travel Blog Photos');archive=base/'North America/2008 - Вашингтон и Филадельфия'
source=base/'Отчеты/Штаты - разное.docx';source_photos=Path('D:/OneDrive/Photo/2008/2008 Лето/USA')
f=lambda *ns:[n.lower()+'.jpg' for n in ns]
blocks={
'22':[f('P8290476','P8290481','P8290480')],
'23':[f('P8290486','P8290488'),f('P8290496','P8300499','P8300505')],
'24':[f('P8300515','P8300519','P8300524'),f('P8300540','P8300541'),f('P8300557','P8300558'),f('P8300574','P8300577'),f('P8300582','P8300590','P8300593'),f('P8300603','P8300611','P8300612'),f('P8300630','P8300622')],
'25':[f('P8300638','P8300640','P8300645'),f('P8300649','P8300652','P8300654'),f('P8300655','P8300657'),f('P8300664','P8300666')],
'26':[f('P8300670','P8300676'),f('P8300680','P8300681','P8300684'),f('P8300686','P8310689')],
'27':[f('P8310699','P8310701'),f('P8310697','P8310704','P8310706')],
'30':[f('P9010710','P9010715'),f('P9010711','P9010717','P9010721'),f('P9010723','P9010726'),f('P9010728','P9010733'),f('P9010737','P9010741','P9010742'),f('P9010746','P9010747'),f('P9010750','P9010752')]}
chapters=[dict(slug='washington',title='Вашингтон',folder='01 - Вашингтон',indices=list(range(22,27)),places=['washington-dc']),dict(slug='philadelphia',title='Филадельфия',folder='02 - Филадельфия',indices=list(range(27,32)),places=['philadelphia','longwood-gardens'])]
# Extra rotation after EXIF orientation; full originals remain untouched.
rotations={n.lower()+'.jpg':90 for n in ['P8300519','P8300541','P8300557','P8300558']};rotations['p9010746.jpg']=270;rotations['p9010747.jpg']=270
if '--archive' in sys.argv:
 assert not mf.exists(),'Archive already initialized'
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 with zipfile.ZipFile(source) as z:doc=E.fromstring(z.read('word/document.xml'))
 ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
 assert ps[20]=='Вашингтон-Филадельфия - сентябрь 2008' and ps[32]=='Вашингтон - май 2011'
 photos=[]
 for chapter in chapters:
  names=[n for i in chapter['indices'] for b in blocks.get(str(i),[]) for n in b]
  for j,name in enumerate(names,1):
   src=source_photos/name.upper();rel=chapter['folder']+f'/{j:02}_'+src.name;dst=archive/rel;dst.parent.mkdir(parents=True,exist_ok=True)
   if not dst.exists():shutil.copy2(src,dst)
   sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dst.read_bytes()).hexdigest()==sha
   with Image.open(dst) as raw:
    ex=raw.getexif();im=ImageOps.exif_transpose(raw);rotation=rotations.get(name,0)
    if rotation:im=im.rotate(rotation,expand=True)
    photos.append(dict(source_name=src.name,source_path=str(src),chapter=chapter['slug'],site_filename=name,archive_name=rel,sha256=sha,bytes=dst.stat().st_size,width=im.width,height=im.height,exif_date=ex.get_ifd(34665).get(36867),exif_orientation=ex.get(274,1),additional_rotation_ccw=rotation,r2_key=f'{slug}/{chapter["slug"]}/{name}'))
 (archive/'Источники').mkdir(exist_ok=True);shutil.copy2(source,archive/'Источники'/source.name)
 m=dict(trip=slug,contentDir=f'content/americas/usa/{slug}',archive_root=str(archive.relative_to(base)).replace('\\','/'),title='Вашингтон — Филадельфия',source=dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),heading=ps[20],paragraph_indices=list(range(22,32)),end_before=ps[32],archive_name='Источники/'+source.name),author_paragraphs=[ps[i] for i in range(22,32)],chapters=chapters,layout=blocks,mosaic_blocks=f('P8290476','P8290496','P8300515','P8300582','P8300603','P8300638','P8300649','P8300680','P8310697','P9010711','P9010737'),featured_photos=f('P8290476','P8300515','P8300640','P8300654'),photos=photos,cover_image=None,dates=dict(start_month='2008-08',end_month='2008-09',evidence='Source: weekend before school, heading September 2008. Camera EXIF August 29–September 1; exact local times not inferred.'),publication=dict(draft=True,authorized=False),drive_sync_verified=False,storage=dict(originals_verified=True,drive_sync_verified=False,r2_verified=False),text_policy='Ten complete source paragraphs, unchanged and unsplit. Original heading retained in source; display title omits repeated date at owner request.',excluded_source_photos={p.name:'Not selected: repeated view, weak frame or reference panel; source retained unchanged.' for p in source_photos.glob('*.JPG') if p.name not in {o['source_name'] for o in photos}})
else:m=json.loads(mf.read_text(encoding='utf-8'))
if '--display' in sys.argv:
 assert m['drive_sync_verified'],'Cloud archive must be verified before display copies'
 copies=[];data={}
 for o in m['photos']:
  src=archive/o['archive_name'];assert hashlib.sha256(src.read_bytes()).hexdigest()==o['sha256'];dest=root/'static/r2'/o['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
  with Image.open(src) as raw:
   im=ImageOps.exif_transpose(raw)
   if o['additional_rotation_ccw']:im=im.rotate(o['additional_rotation_ccw'],expand=True)
   im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
   copies.append(dict(key=o['r2_key'],original_archive_name=o['archive_name'],width=im.width,height=im.height,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()));data[o['chapter']+'/'+o['site_filename']]={'w':im.width,'h':im.height}
 m['r2']={'photos':copies,'status':'awaiting-public-verification'};(root/'data/photos'/f'{slug}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '--archive' not in sys.argv:
 trip=root/m['contentDir'];trip.mkdir(parents=True,exist_ok=True);title=json.dumps(m['title'],ensure_ascii=False);draft=str(m['publication']['draft']).lower()
 cover=''
 if m.get('cover_image'):cover='cover_image: '+json.dumps('https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+slug+'/'+m['cover_image'])+'\n'
 if m.get('cover_position'):cover+='cover_position: '+json.dumps(m['cover_position'])+'\n'
 (trip/'_index.md').write_text(f'---\ntitle: {title}\ntype: "trips"\ndraft: {draft}\ndate: 2008-08-29\ntrip_year: 2008\ntrip_start: "2008-08"\ntrip_end: "2008-09"\nshort_trip: "usa"\ncontinent: "Северная Америка"\ncountry: "США"\ngeo_countries:\n  - usa\nreadable_photos: true\n{cover}---\n',encoding='utf-8')
 for weight,ch in enumerate(m['chapters'],1):
  body=[]
  for i in ch['indices']:
   body.append('<p>'+html.escape(m['author_paragraphs'][i-22],quote=False)+'</p>')
   for block in m['layout'].get(str(i),[]):
    kind='mosaic' if block[0] in m['mosaic_blocks'] else 'row';names=[('L:' if kind=='mosaic' and n in m['featured_photos'] else '')+n for n in block];body.append('{{< '+kind+' "'+' '.join(names)+'" >}}')
  body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>');folder=trip/ch['slug'];folder.mkdir(exist_ok=True)
  fm=f'---\ntitle: '+json.dumps(ch['title'],ensure_ascii=False)+f'\ndraft: {draft}\ndate: 2008-08-29\nweight: {weight}\nchapter_kind: "Заметка"\nlayout: "photo-story"\ncity: '+json.dumps(ch['title'],ensure_ascii=False)+'\nplaces:\n'+''.join('  - '+p+'\n' for p in ch['places'])+'auto_gallery: false\n---\n\n'
  (folder/'index.md').write_text(fm+'\n\n'.join(body)+'\n',encoding='utf-8')
out=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(out,encoding='utf-8');(archive/'photo-manifest.json').write_text(out,encoding='utf-8')
print('Washington–Philadelphia:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photos;',len(m['chapters']),'chapters')


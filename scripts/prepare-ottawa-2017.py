from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='ottawa-2017'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2017 - Оттава')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Онтарио (разное).docx')
old=Path('D:/OneDrive/Photo/2009/2009 Лето/Женя-Лена-Лиза')
current=Path('D:/OneDrive/Photo/2017/2017 лето')
blocks={'1':[['p7250534.jpg','p7250535.jpg']],'2':[['20170716_172950.jpg','20170716_173221.jpg']]}
site_to_source={'p7250534.jpg':old/'P7250534.JPG','p7250535.jpg':old/'P7250535.JPG','20170716_172950.jpg':current/'20170716_172950.jpg','20170716_173221.jpg':current/'20170716_173221.jpg'}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    assert ps[231]=='Оттава - исторический музей - июль 2017'
    indexes=[233,237,238,239,240]
    raw=[ps[i] for i in indexes];rendered=[p.replace('<lj-cut>','') for p in raw]
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        src=site_to_source[name];original=src.name; rel=f'01 - Исторический музей/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and date[:10] in ['2009:07:25','2017:07:16']
            rotation=90 if name=='p7250535.jpg' else 0
            if rotation:upright=upright.rotate(rotation,expand=True)
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'display_rotation_ccw':rotation,'r2_key':f'{slug}/story/{name}'})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/canada/{slug}','archive_root':'North America/2017 - Оттава','title':'Оттава: исторический музей','source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[231],'paragraph_indices':indexes,'archive_name':'Источники/'+source.name,'end_before_index':len(ps),'old_photo_reference_indices':[234,236],'old_photo_references':[ps[i] for i in [234,236]],'service_markup_removed':['<lj-cut>']},'author_paragraphs':raw,'rendered_paragraphs':rendered,'dates':{'start_month':'2017-07','end_month':'2017-07','photo_date':'2017-07-16','evidence':'July2017 source heading; current museum images July16 2017; two exact LJ archival photos July25 2009.'},'photos':photos,'layout':blocks,'mosaic_blocks':[],'featured_photos':[],'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'publication':{'draft':True,'authorized':False},'text_policy':'All5 entire author paragraphs verbatim except service lj-cut removed. Two exact original LJ museum images534/535 visually matched; two current museum hall photographs July16 2017. Other July images not used, May2017 Ottawa folder excluded.'}

else:
    m=json.loads(mf.read_text(encoding='utf-8'))
if '--display' in sys.argv:
    assert m['drive_sync_verified'], 'Cloud archive must be verified first'
    copies=[];data={}
    for o in m['photos']:
        src=archive/o['archive_name'];assert hashlib.sha256(src.read_bytes()).hexdigest()==o['sha256']
        dest=root/'static/r2'/o['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
        with Image.open(src) as raw:
            im=ImageOps.exif_transpose(raw)
            rotation=o.get('display_rotation_ccw',0)
            if rotation:im=im.rotate(rotation,expand=True)
            if max(im.size)<=2000 and o['exif_orientation']==1 and not rotation:shutil.copy2(src,dest)
            else:
                im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
            w,h=im.size
        copies.append({'key':o['r2_key'],'original_archive_name':o['archive_name'],'width':w,'height':h,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        data[m.get('chapter_slug','story')+'/'+o['site_filename']]={'w':w,'h':h,'url':'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+o['r2_key']}
    m['r2']={'photos':copies,'status':'awaiting-public-verification'};m['storage']['drive_sync_verified']=True
    (root/'data/photos'/f"{m.get('collection_slug',slug)}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '--archive' not in sys.argv:
    chapter_slug=m.get('chapter_slug','story')
    trip=root/m['contentDir'];(trip/chapter_slug).mkdir(parents=True,exist_ok=True)
    title=json.dumps(m['title'],ensure_ascii=False)
    chapter_title=json.dumps(m.get('chapter_title',m['title']),ensure_ascii=False)
    cover=('cover_image: "https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+slug+'/'+m['cover_image']+'"\n') if m.get('cover_image') else ''
    if m.get('cover_position'):
        cover += 'cover_position: '+json.dumps(m['cover_position'],ensure_ascii=False)+'\n'
    trip.joinpath('_index.md').write_text(f'''---
title: {title}
type: "trips"
draft: {str(m['publication']['draft']).lower()}
date: 2017-07-16
trip_year: 2017
trip_start: "2017-07"
trip_end: "2017-07"
short_trip: "canada"
continent: "Северная Америка"
country: "Канада"
geo_countries:
  - canada
readable_photos: true
aliases:
  - /americas/canada/ottawa-2017/
{cover}---
''',encoding='utf-8')
    body=[]
    sections=m.get('text_sections') or [dict(paragraph=i,start=0,end=len(p),blocks=m['layout'].get(str(i),[])) for i,p in enumerate(m['rendered_paragraphs'],1)]
    for section in sections:
        p=m['rendered_paragraphs'][section['paragraph']-1][section['start']:section['end']]
        body.append('<p>'+html.escape(p,quote=False)+'</p>')
        for block in section['blocks']:
            names=[('L:' if n in m['featured_photos'] else '')+n for n in block]
            kind='mosaic' if block[0] in m['mosaic_blocks'] else 'row'
            if kind=='row':names=block
            body.append('{{< '+kind+' "'+' '.join(names)+'" >}}')
    body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
    trip.joinpath(chapter_slug+'/index.md').write_text(f'''---
title: {chapter_title}
draft: {str(m['publication']['draft']).lower()}
date: 2017-07-16
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Оттава"
places:
  - ottawa
auto_gallery: false
aliases:
  - /americas/canada/ottawa-2017/story/
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Ottawa 2017:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

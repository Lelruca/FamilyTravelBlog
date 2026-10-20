from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='quebec-montreal-2003'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2003 - Квебек и Монреаль')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Канада - разное.docx')
source_photos=Path('D:/OneDrive/Photo/2003/2003 Лето_Montreal_Quebec')
f=lambda ns:[f'mq_{n:04}.jpg' for n in ns]
blocks={'6':[f([22,23]),f([24,25,26,27]),f([28,29,30]),f([2,3,4]),f([1,6,7]),f([5])], '9':[f([8,11])], '11':[f([15,16,17,18])], '14':[f([19])]}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    stop=next(i for i,p in enumerate(ps) if p.startswith('Mont Tremblant'))
    indexes=[i for i in range(1,stop) if ps[i]]
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=name[:-4]+'.JPG'; src=source_photos/original; rel=f'01 - Квебек и Монреаль/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and '2003:05:17'<=date[:10]<='2003:05:19'
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f'{slug}/story/{name}'})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/canada/{slug}','archive_root':str(archive.relative_to(Path('G:/My Drive/Family Travel Blog Photos'))).replace('\\','/'),'title':ps[0], 'source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[0],'paragraph_indices':indexes,'end_before':ps[stop],'archive_name':'Источники/'+source.name},'author_paragraphs':[ps[i] for i in indexes],'dates':{'start':'2003-05-17','end':'2003-05-19','evidence':'EXIF May 17–19, matching Saturday departure and return on holiday May 19 in source text.'},'photos':photos,'layout':blocks,'mosaic_blocks':f([24,2,1,15]),'featured_photos':f([2,1]),'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'excluded_source_photos':{'mq_0010.JPG':'Very dark interior','mq_0012.JPG':'Very dark interior','mq_0013.JPG':'Very dark interior','mq_0014.JPG':'Very dark interior','mq_0015_p.JPG':'Cropped variant of selected mq_0015.JPG; full family frame preferred','mq_0020.JPG':'EXIF May 11, outside May 17–19 trip','mq_0021.JPG':'EXIF May 12, outside May 17–19 trip','mq_0031.JPG':'Near-repeat of selected clearer full mural mq_0030.JPG; source kept untouched'},'publication':{'draft':True,'authorized':False},'text_policy':'Entire first note retained verbatim, including personal ending. No spelling or paragraph changes.'}
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
            if max(im.size)<=2000 and o['exif_orientation']==1:shutil.copy2(src,dest)
            else:
                im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
            w,h=im.size
        copies.append({'key':o['r2_key'],'original_archive_name':o['archive_name'],'width':w,'height':h,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        data['story/'+o['site_filename']]={'w':w,'h':h}
    m['r2']={'photos':copies,'status':'awaiting-public-verification'};m['storage']['drive_sync_verified']=True
    (root/'data/photos'/f'{slug}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '--archive' not in sys.argv:
    trip=root/m['contentDir'];(trip/'story').mkdir(parents=True,exist_ok=True)
    title=json.dumps(m['title'],ensure_ascii=False)
    cover=('cover_image: "https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+slug+'/'+m['cover_image']+'"\n') if m.get('cover_image') else ''
    trip.joinpath('_index.md').write_text(f'''---
title: {title}
type: "trips"
draft: {str(m['publication']['draft']).lower()}
date: 2003-05-17
trip_year: 2003
trip_start: "2003-05"
trip_end: "2003-05"
short_trip: "canada"
continent: "Северная Америка"
country: "Канада"
geo_countries:
  - canada
readable_photos: true
{cover}---
''',encoding='utf-8')
    body=[]
    for i,p in enumerate(m['author_paragraphs'],1):
        body.append('<p>'+html.escape(p,quote=False)+'</p>')
        for block in m['layout'].get(str(i),[]):
            names=[('L:' if n in m['featured_photos'] else '')+n for n in block]
            kind='mosaic' if block[0] in m['mosaic_blocks'] else 'row'
            if kind=='row':names=block
            body.append('{{< '+kind+' "'+' '.join(names)+'" >}}')
    body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
    trip.joinpath('story/index.md').write_text(f'''---
title: {title}
draft: {str(m['publication']['draft']).lower()}
date: 2003-05-17
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Квебек и Монреаль"
places:
  - quebec-city
  - montreal
auto_gallery: false
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Quebec:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

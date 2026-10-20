from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='new-york-2006'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2006 - Нью-Йорк')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Штаты - разное.docx')
source_photos=Path('D:/OneDrive/Photo/2006/2006_Декабрь_NewYork')
f=lambda ns:[f'IMG_{n}.jpg' for n in ns]
blocks={'3':[f([3611,3613,3622,3623])],
'4':[f([3632,3624,3627]),f([3634,3635]),f([3626,3637,3638])],
'5':[f([3643,3644])],
'6':[f([3648,3646,3653]),f([3656,3662]),f([3669,3671]),f([3683,3684,3686,3688])],
'7':[f([3696,3697,3690]),f([3700,3703,3706,3707])],
'8':[f([3715,3718]),f([3716,3719,3720])],
'9':[f([3721,3722]),f([3724,3725])],
'11':[f([3730,3728,3731])]}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    stop=next(i for i,p in enumerate(ps) if 'Диснейленд с Наташей' in p)
    indexes=[i for i in range(1,stop) if ps[i]]
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=name[:-4]+'.JPG'; src=source_photos/original; rel=f'01 - Нью-Йорк/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and '2006:12:23'<=date[:10]<='2006:12:25'
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f'{slug}/story/{name}'})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/usa/{slug}','archive_root':str(archive.relative_to(Path('G:/My Drive/Family Travel Blog Photos'))).replace('\\','/'),'title':ps[0], 'source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[0],'paragraph_indices':indexes,'end_before':ps[stop],'archive_name':'Источники/'+source.name},'author_paragraphs':[ps[i] for i in indexes],'dates':{'start_month':'2006-12','end_month':'2006-12','photo_start':'2006-12-23','photo_end':'2006-12-25','evidence':'EXIF December 23–25; source describes arrival the preceding evening and departure December 25.'},'photos':photos,'layout':blocks,'mosaic_blocks':f([3611,3632,3648,3683,3696,3700,3716,3730]),'featured_photos':f([3632,3648,3696,3716,3730]),'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'excluded_source_photos':{p.name:'Not selected after visual review; source retained unchanged' for p in source_photos.glob('*.JPG') if p.name not in {o['source_name'] for o in photos}},'publication':{'draft':True,'authorized':False},'text_policy':'Entire first New York note retained verbatim. No spelling or paragraph changes.'}
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
    if m.get('cover_position'):
        cover += 'cover_position: '+json.dumps(m['cover_position'],ensure_ascii=False)+'\n'
    trip.joinpath('_index.md').write_text(f'''---
title: {title}
type: "trips"
draft: {str(m['publication']['draft']).lower()}
date: 2006-12-23
trip_year: 2006
trip_start: "2006-12"
trip_end: "2006-12"
short_trip: "usa"
continent: "Северная Америка"
country: "США"
geo_countries:
  - usa
readable_photos: true
{cover}---
''',encoding='utf-8')
    body=[]
    sections=m.get('text_sections') or [dict(paragraph=i,start=0,end=len(p),blocks=m['layout'].get(str(i),[])) for i,p in enumerate(m['author_paragraphs'],1)]
    for section in sections:
        p=m['author_paragraphs'][section['paragraph']-1][section['start']:section['end']]
        body.append('<p>'+html.escape(p,quote=False)+'</p>')
        for block in section['blocks']:
            names=[('L:' if n in m['featured_photos'] else '')+n for n in block]
            kind='mosaic' if block[0] in m['mosaic_blocks'] else 'row'
            if kind=='row':names=block
            body.append('{{< '+kind+' "'+' '.join(names)+'" >}}')
    body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
    trip.joinpath('story/index.md').write_text(f'''---
title: {title}
draft: {str(m['publication']['draft']).lower()}
date: 2006-12-23
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Нью-Йорк"
places:
  - new-york
auto_gallery: false
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('New York:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

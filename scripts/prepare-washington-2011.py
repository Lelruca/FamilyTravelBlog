from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='washington-2011'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2011 - Вашингтон')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Штаты - разное.docx')
source_photos=Path('D:/OneDrive/Photo/2011/2011 Весна/Вашингтон')
f=lambda *ns:[f'p522{n}.jpg' for n in ns]
blocks={'5':[['2011-05-20-12-55-54.jpg']],'6':[['2011-05-20-14-55-28.jpg']],
'7':[['2011-05-21-10-03-44.jpg','2011-05-21-09-48-42.jpg'],f(1869,1871),f(1881,1882,1883),f(1888,1884,1885)],
'8':[f(1891,1890,1893),f(1900,1902,1907),f(1914,1919)]}
site_to_source={name:(name.upper() if name.startswith('p') else name[:10]+' '+name[11:19].replace('-','.')+'.jpg') for groups in blocks.values() for block in groups for name in block}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    end_heading='В Вашингтон вдвоем! - Aug 2015'
    assert ps[32]=='Вашингтон - май 2011' and ps[41].endswith(end_heading)
    ps[41]=ps[41][:-len(end_heading)]
    indexes=[i for i in range(33,42) if ps[i]]
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=site_to_source[name]; src=source_photos/original; rel=f'01 - Вашингтон/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and '2011:05:20'<=date[:10]<='2011:05:22'
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f'{slug}/story/{name}'})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/usa/{slug}','archive_root':str(archive.relative_to(Path('G:/My Drive/Family Travel Blog Photos'))).replace('\\','/'),'title':'Вашингтон', 'source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[32],'paragraph_indices':indexes,'end_before':end_heading,'last_paragraph_heading_suffix_removed':True,'archive_name':'Источники/'+source.name},'author_paragraphs':[ps[i] for i in indexes],'dates':{'start_month':'2011-05','end_month':'2011-05','photo_start':'2011-05-20','photo_end':'2011-05-22','evidence':'Source heading May 2011; EXIF May 20–22.'},'photos':photos,'layout':blocks,'mosaic_blocks':f(1888,1891,1900),'featured_photos':f(1888,1891,1900),'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'excluded_source_photos':{p.name:'Not selected after visual review; source retained unchanged' for p in source_photos.glob('*.JPG') if p.name not in {o['source_name'] for o in photos}},'publication':{'draft':True,'authorized':False},'text_policy':'Entire May 2011 note retained verbatim. The following 2015 title joined to its last paragraph in the DOCX is excluded. No spelling or paragraph changes.'}
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
if ('--cover-display' in sys.argv or '--display' in sys.argv) and m.get('cover_asset'):
    asset=m['cover_asset'];assert asset.get('drive_id') and not asset['drive_id'].startswith('local'), 'Cover source must be synchronized first'
    src=archive/asset['archive_name'];assert hashlib.sha256(src.read_bytes()).hexdigest()==asset['sha256']
    key=slug+'/cover/p5221891-wide.jpg';dest=root/'static/r2'/key;dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(src) as im:
        im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=90,optimize=True);w,h=im.size
    m.setdefault('r2',{})['cover']={'key':key,'original_archive_name':asset['archive_name'],'width':w,'height':h,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    dp=root/'data/photos'/f'{slug}.json';data=json.loads(dp.read_text(encoding='utf-8'));data['cover/p5221891-wide.jpg']={'w':w,'h':h};dp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    m['cover_image']='cover/p5221891-wide.jpg';m['cover_position']='center 50%'
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
date: 2011-05-20
trip_year: 2011
trip_start: "2011-05"
trip_end: "2011-05"
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
date: 2011-05-20
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Вашингтон"
places:
  - washington-dc
auto_gallery: false
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Washington 2011:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

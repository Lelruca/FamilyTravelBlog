from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='hamilton-2014'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2014 - Hamilton')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Онтарио (разное).docx')
source_photos=Path('D:/OneDrive/Photo/2014/2014 Весна/Hamilton')
f=lambda *ts:[f'20140421_{t}.jpg' for t in ts]
blocks={'5':[f(111715,111404),f(111424,111813)],'6':[f(114834,114915),f(114926)],'7':[f(124446,124528)],'8':[f(130700,131021),f(130836,131229)],'9':[f(130651,133941),f(133634)],'10':[f(131615)],'11':[f(141656),f(142022,142027)]}
site_to_source={n:n for groups in blocks.values() for block in groups for n in block}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    assert ps[0]=='Hamilton, Ontario - Apr 2014' and ps[34].startswith('Оттава 9 мая 2015')
    indexes=[1,3,4,5,8,11,14,17,20,21,24,29,30,31,32]
    raw=[ps[i] for i in indexes];rendered=raw
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=site_to_source[name]; src=source_photos/original; rel=f'01 - Hamilton/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and date[:10]=='2014:04:21'
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f'{slug}/story/{name}'})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/canada/{slug}','archive_root':'North America/2014 - Hamilton','title':'Hamilton: водопады и авиационный музей','source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[0],'paragraph_indices':indexes,'archive_name':'Источники/'+source.name,'end_before_index':34,'old_photo_reference_indices':[6,9,12,15,18,22,25,27],'old_photo_references':[ps[i] for i in [6,9,12,15,18,22,25,27]]},'author_paragraphs':raw,'rendered_paragraphs':raw,'dates':{'start_month':'2014-04','end_month':'2014-04','photo_date':'2014-04-21','evidence':'April2014 author heading; all28 OneDrive original dates April21 2014.'},'photos':photos,'layout':blocks,'mosaic_blocks':[],'featured_photos':[],'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'publication':{'draft':True,'authorized':False},'text_policy':'All15 author paragraphs retained verbatim, including spelling and punctuation and historical prices. LJ control and old embedded image tags excluded, full DOCX archived. No invented captions or headings. Photo groups follow waterfalls, museum, cockpit and simulator paragraphs.'}

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
date: 2014-04-21
trip_year: 2014
trip_start: "2014-04"
trip_end: "2014-04"
short_trip: "canada"
continent: "Северная Америка"
country: "Канада"
geo_countries:
  - canada
readable_photos: true
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
    trip.joinpath('story/index.md').write_text(f'''---
title: {title}
draft: {str(m['publication']['draft']).lower()}
date: 2014-04-21
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Hamilton"
places:
  - hamilton
auto_gallery: false
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Hamilton 2014:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

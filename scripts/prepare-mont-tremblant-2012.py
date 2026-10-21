from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='mont-tremblant-2012'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2012 - Mont Tremblant')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Канада - разное.docx')
source_photos=Path('D:/OneDrive/Photo/2012/2012-2013 Зима')
blocks={'4':[['img_20121223_141107.jpg','img_20121224_121104.jpg']], '5':[['img_20121223_141100.jpg']], '6':[['img_20121224_124144.jpg','img_20121224_124157.jpg']]}
site_to_source={n:n[:3].upper()+n[3:] for groups in blocks.values() for block in groups for n in block}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    assert ps[21]=='Mont Tremblant - рождество 2012'
    indexes=[23,24,25,26,27,29,31,32,33]
    raw=[ps[i] for i in indexes]
    rendered=[s.replace('<lj-cut text="Продолжение и фото...">','') for s in raw]
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=site_to_source[name]; src=source_photos/original; rel=f'01 - Mont Tremblant/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and '2012:12:23'<=date[:10]<='2012:12:24'
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f'{slug}/story/{name}'})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/canada/{slug}','archive_root':str(archive.relative_to(Path('G:/My Drive/Family Travel Blog Photos'))).replace('\\','/'),'title':'Mont Tremblant','source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[21],'paragraph_indices':indexes,'archive_name':'Источники/'+source.name,'photo_references':[{'raw_index':28,'filename':'IMG_20121223_141100.jpg','url':'http://ic.pics.livejournal.com/olgau/8466657/1204/1204_600.jpg'},{'raw_index':30,'filename':'IMG_20121224_124144.jpg','url':'http://ic.pics.livejournal.com/olgau/8466657/1468/1468_900.jpg'}]},'author_paragraphs':raw,'rendered_paragraphs':rendered,'formatting_only_removed':['<lj-cut text="Продолжение и фото...">'],'dates':{'start_month':'2012-12','end_month':'2012-12','photo_start':'2012-12-23','photo_end':'2012-12-24','evidence':'Christmas 2012 in author heading; selected photo EXIF December 23–24.'},'photos':photos,'layout':blocks,'mosaic_blocks':[],'featured_photos':[],'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'excluded_source_photos':{'IMG_20121223_141052.jpg':'Near duplicate of original LJ family photograph 141100; source retained','IMG_20121223_141112.jpg':'Family member cut at right edge; source retained','IMG_20121224_121054.jpg':'Near duplicate with backs facing camera; source retained','IMG_20121224_121057.jpg':'Near duplicate; selected 121104 instead'},'publication':{'draft':True,'authorized':False},'text_policy':'All nine author paragraphs retained verbatim, including spelling and punctuation. Only LJ control markup removed; two embedded old image tags replaced by their matching full OneDrive originals.'}

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
date: 2012-12-23
trip_year: 2012
trip_start: "2012-12"
trip_end: "2012-12"
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
date: 2012-12-23
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Mont Tremblant"
places:
  - mont-tremblant
auto_gallery: false
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Mont Tremblant 2012:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

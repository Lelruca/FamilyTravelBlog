from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='moscow-new-year-2012'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/Europe/2011-2012 - Москва')
source=archive/'Источники/2012-01-10 - Я не была в Москве 7 лет.txt'
source_photos=Path('D:/OneDrive/Photo/2011/2011-2012 Зима/Moscow')
img=lambda s:'img_'+s+'.jpg'
pc=lambda *ns:[f'pc272{n:03}.jpg' for n in ns]
f=lambda *ns:[f'p1072{n:03}.jpg' for n in ns]
blocks={'2':[[img('20111228_135159'),img('20111228_135356')],[img('20111228_140718'),img('20111228_143634')]],'3':[[img('20111231_234138'),img('20120101_000257')]],'5':[f(437,443),[f(449)[0],pc(415)[0]],pc(417,427)],'6':[pc(387,388),pc(399,400),pc(402,404),pc(406,408),[img('20111229_143359')]],'7':[[img('20111229_104554'),f(453)[0]],f(461,465),f(469,470),f(474,476),f(480,483,487)],'8':[[img('20120101_000244'),img('20120101_000415')]]}
blocks['12']=blocks.pop('3')+blocks.pop('8')
site_to_source={n:next(p.name for p in source_photos.iterdir() if p.name.lower()==n) for groups in blocks.values() for block in groups for n in block}
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    info=json.loads((root/'.tmp/moscow-new-year-2012/source.json').read_text(encoding='utf-8'))
    raw=info['paragraphs'];rendered=raw
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=site_to_source[name]; src=source_photos/original; rel=f'01 - Москва/{i:02}_{original}'; dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and '2011:12:25'<=date[:10]<='2012:01:09'
            photos.append({'source_name':original,'source_path':str(src),'chapter':'story','site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f'{slug}/story/{name}'})
    m={'trip':slug,'contentDir':f'content/europe/russia/{slug}','archive_root':'Europe/2011-2012 - Москва','title':info['title'],'source':info['sources'][0],'private_source':info['sources'][1],'author_paragraphs':raw,'rendered_paragraphs':raw,'dates':{'start_month':'2011-12','end_month':'2012-01','evidence':'Author post dated January10 2012, return previous morning. Original EXIF December25 2011–January7 2012; no exact departure date inferred.'},'photos':photos,'layout':blocks,'mosaic_blocks':[],'featured_photos':[],'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'publication':{'draft':True,'authorized':False},'text_policy':'Whole public text retained verbatim including spelling and punctuation; post title/timestamp and LJ Collapse control separated from body. Private letter excluded from website and Git; two excerpt suggestions local only, awaiting owner review.'}

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
if '--cover-display' in sys.argv or ('--display' in sys.argv and m.get('cover_asset')):
    o=m['cover_asset'];assert o.get('drive_id') and not o['drive_id'].startswith('local')
    src=archive/o['archive_name'];assert hashlib.sha256(src.read_bytes()).hexdigest()==o['sha256']
    key=slug+'/cover/p1072431.jpg';dest=root/'static/r2'/key;dest.parent.mkdir(exist_ok=True,parents=True)
    with Image.open(src) as raw:
        im=ImageOps.exif_transpose(raw);im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True);w,h=im.size
    m.setdefault('r2',{})['cover']={'key':key,'original_archive_name':o['archive_name'],'width':w,'height':h,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    dp=root/'data/photos'/f'{slug}.json';data=json.loads(dp.read_text(encoding='utf-8'));data['cover/p1072431.jpg']={'w':w,'h':h};dp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
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
date: 2012-01-09
trip_year: 2012
trip_start: "2011-12"
trip_end: "2012-01"
short_trip: "europe"
continent: "Европа"
country: "Россия"
geo_countries:
  - russia
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
date: 2012-01-09
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Москва"
places:
  - moscow
auto_gallery: false
---

'''+ '\n\n'.join(body)+'\n',encoding='utf-8')
if m.get('photo_captions'):
    dp=root/'data/photos'/f'{slug}.json';data=json.loads(dp.read_text(encoding='utf-8'))
    for key,caption in m['photo_captions'].items():data[key]['caption']=caption
    dp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Moscow 2011-2012:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='ottawa-2015'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2015 - Оттава')
source=Path('G:/My Drive/Family Travel Blog Photos/Отчеты/Онтарио (разное).docx')
source_photos=Path('D:/OneDrive/Photo/2015/2015 Весна/Ottawa_May')
blocks={'1': [['img_5448.jpg']], '3': [['img_5444.jpg', 'img_5445.jpg']], '4': [['img_5412.jpg', 'img_5420.jpg'], ['img_5421.jpg', 'img_5424.jpg'], ['img_5434.jpg', 'img_5487.jpg'], ['img_5539.jpg']], '5': [['img_5417.jpg', 'img_5419.jpg'], ['img_5432.jpg', 'img_5475.jpg'], ['img_5498.jpg', 'img_5515.jpg'], ['img_5532.jpg', 'img_5548.jpg'], ['img_5549.jpg']], '6': [['img_5384.jpg', 'img_5401.jpg', 'img_5406.jpg']], '7': [['img_5405.jpg', 'img_5408.jpg', 'img_5410.jpg'], ['img_5423.jpg', 'img_5426.jpg', 'img_5427.jpg'], ['img_5428.jpg', 'img_5429.jpg', 'img_5430.jpg'], ['img_5433.jpg', 'img_5449.jpg', 'img_5450.jpg'], ['img_5453.jpg', 'img_5464.jpg', 'img_5480.jpg'], ['img_5481.jpg', 'img_5499.jpg', 'img_5502.jpg'], ['img_5505.jpg', 'img_5506.jpg']], '8': [['img_5565.jpg', 'img_5577.jpg'], ['img_5581.jpg', 'img_5601-lelkapc.jpg'], ['img_5603.jpg', 'img_5606.jpg'], ['img_5613.jpg', 'img_5621.jpg'], ['img_5626.jpg', 'img_5627.jpg'], ['img_5632.jpg', 'img_5641.jpg'], ['img_5642.jpg', 'img_5645.jpg'], ['img_5646.jpg', 'img_5651.jpg'], ['img_5656.jpg', 'img_5661.jpg']]}
blocks['8']=[['img_5565.jpg', 'img_5577.jpg'], ['img_5581.jpg'], ['img_5601-lelkapc.jpg', 'img_5603.jpg'], ['img_5606.jpg', 'img_5613.jpg'], ['img_5621.jpg', 'img_5626.jpg'], ['img_5627.jpg', 'img_5632.jpg'], ['img_5641.jpg', 'img_5642.jpg'], ['img_5645.jpg', 'img_5646.jpg'], ['img_5651.jpg', 'img_5656.jpg', 'img_5661.jpg']]
chapters=[{'slug': 'tulips', 'title': 'Тюльпаны', 'archive_folder': '01 - Тюльпаны', 'paragraphs': [1, 2, 3, 4, 5, 6, 7]}, {'slug': 'ottawa', 'title': 'Оттава', 'archive_folder': '02 - Оттава', 'paragraphs': [8]}]
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(source) as z: doc=ET.fromstring(z.read('word/document.xml'))
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    assert ps[34]=='Оттава 9 мая 2015 - тюльпаны и не только' and ps[231].startswith('Оттава - исторический музей')
    indexes=[35,38,40,43,46,68,76,88];raw=[ps[i] for i in indexes];rendered=raw
    name_ch={n:c for c in chapters for j in c['paragraphs'] for bs in blocks.get(str(j),[]) for n in bs};counts={}
    photos=[]
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        c=name_ch[name];counts[c['slug']]=counts.get(c['slug'],0)+1
        incoming=next(p for p in archive.iterdir() if p.is_file() and p.name.lower()==name);original=incoming.name;src=source_photos/original
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(incoming.read_bytes()).hexdigest()==sha,'Owner file differs from full OneDrive original: '+original
        rel=c['archive_folder']+f"/{counts[c['slug']]:02}_{original}";dest=archive/rel;assert incoming.resolve().is_relative_to(archive.resolve()) and dest.resolve().is_relative_to(archive.resolve());assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);incoming.rename(dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and date[:10] in ['2015:05:09','2015:05:10']
            photos.append({'source_name':original,'source_path':str(src),'chapter':c['slug'],'site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f"{slug}/{c['slug']}/{name}"})
    (archive/'Источники').mkdir(exist_ok=True);archived_source=archive/'Источники'/source.name
    if not archived_source.exists():shutil.copy2(source,archived_source)
    assert archived_source.read_bytes()==source.read_bytes()
    m={'trip':slug,'contentDir':f'content/americas/canada/{slug}','archive_root':'North America/2015 - Оттава','title':'Оттава: тюльпаны и не только','source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'heading':ps[34],'paragraph_indices':indexes,'archive_name':'Источники/'+source.name,'pending_museum_paragraph_indices':[82,112,114,230],'pending_comparison_range':[116,229],'end_before_index':231},'author_paragraphs':raw,'rendered_paragraphs':raw,'dates':{'start_month':'2015-05','end_month':'2015-05','photo_start':'2015-05-09','photo_end':'2015-05-10','evidence':'Author states9–10May2015; original EXIF same dates.'},'chapters':chapters,'photos':photos,'layout':blocks,'mosaic_blocks':[],'featured_photos':[],'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'publication':{'draft':True,'authorized':False},'completion':{'prepared_chapters':['tulips','ottawa'],'pending_chapter':'museum','museum_and_2009_comparison_not_yet_prepared':True},'selection':'All60 photographs supplied by owner in trip root. Matched byte-for-byte to full OneDrive originals; no substitutions, no further agent selection. Moved to numbered chapter archive folders with hashes checked. Museum folder left untouched.','text_policy':'First two chapters use8 entire author paragraphs verbatim. Source museum paragraph82 and112/114/230 and2009/2015 comparison held for third chapter, full DOCX archived. No rewriting or added captions.'}

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
        data[o['chapter']+'/'+o['site_filename']]={'w':w,'h':h}
        if o['chapter']=='museum':data[o['chapter']+'/'+o['site_filename']]['caption']=str(o['year'])
    m['r2']={'photos':copies,'status':'awaiting-public-verification'};m['storage']['drive_sync_verified']=True
    (root/'data/photos'/f'{slug}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '--archive' not in sys.argv:
    trip=root/m['contentDir'];trip.mkdir(parents=True,exist_ok=True)
    title=json.dumps(m['title'],ensure_ascii=False)
    cover=('cover_image: "https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+slug+'/'+m['cover_image']+'"\n') if m.get('cover_image') else ''
    if m.get('cover_position'):
        cover += 'cover_position: '+json.dumps(m['cover_position'],ensure_ascii=False)+'\n'
    trip.joinpath('_index.md').write_text(f'''---
title: {title}
type: "trips"
draft: {str(m['publication']['draft']).lower()}
date: 2015-05-09
trip_year: 2015
trip_start: "2015-05"
trip_end: "2015-05"
short_trip: "canada"
continent: "Северная Америка"
country: "Канада"
geo_countries:
  - canada
readable_photos: true
{cover}---
''',encoding='utf-8')
    for ci,c in enumerate(m['chapters'],1):
        body=[]
        def row(block, paired=False):
            markup='{{< row "'+' '.join(block)+'" >}}'
            return '<div class="museum-pair">\n\n'+markup+'\n\n</div>' if paired else markup
        for i in c['paragraphs']:
            if c['slug']=='museum' and i==12:
                if m['layout'].get('museum-review'):body.append('<h2>Пары для проверки</h2>')
                for block in m['layout'].get('museum-review',[]):body.append(row(block,True))
                if m['layout'].get('museum-single'):body.append('<h2>Одиночные фото</h2>')
                for block in m['layout'].get('museum-single',[]):body.append(row(block))
            body.append('<p>'+html.escape(m['rendered_paragraphs'][i-1],quote=False)+'</p>')
            for block in m['layout'].get(str(i),[]):body.append(row(block,c['slug']=='museum' and i==11))
        body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
        if c['slug']=='museum':body.append('<style>.museum-pair{margin:32px 0 48px}.museum-pair .essay-group{margin:0}</style>')
        chapter=trip/c['slug'];chapter.mkdir(exist_ok=True)
        fm='---\ntitle: '+json.dumps(c['title'],ensure_ascii=False)+'\ndraft: '+str(m['publication']['draft']).lower()+'\ndate: 2015-05-09\nweight: '+str(ci)+'\nchapter_kind: "Заметка"\nlayout: "photo-story"\ncity: "Оттава"\nplaces: ["ottawa"]\nauto_gallery: false\n---\n\n'
        chapter.joinpath('index.md').write_text(fm+'\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Ottawa 2015:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

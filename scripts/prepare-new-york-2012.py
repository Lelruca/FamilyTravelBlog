from pathlib import Path
import json, hashlib, html, shutil, sys, zipfile, xml.etree.ElementTree as ET
from PIL import Image, ImageOps
root=Path(__file__).resolve().parents[1]
slug='new-york-2012'; mf=root/'media-manifests'/f'{slug}.json'
archive=Path('G:/My Drive/Family Travel Blog Photos/North America/2012 - Нью-Йорк')
source=archive/'Источники/2026-10-20 - Текст автора.txt'
source_photos=Path('D:/OneDrive/Photo/2012/2012 Весна/New York')
f=lambda *ns:[f'img_{n:04}.jpg' for n in ns]
blocks={'5':[f(2,6,8),f(10,16)],'6':[f(22,23),f(24),f(25,26)],'7':[f(29,30),f(33,36),f(38,40)],'8':[f(47,48),f(52),f(58,61)],'9':[f(63,66),f(74,81),f(91),f(95,99),f(106)],'10':[f(201,205,206),f(138,140,143),f(144,146),f(147,149,152),f(156,161,164),f(166),f(173,176),f(180),f(182,188),f(190,195,198)],'11':[f(212,213),f(215,216)]}
site_to_source={n:n.upper() for groups in blocks.values() for block in groups for n in block}
chapters=[{'slug': 'day-1', 'title': 'День 1', 'archive_folder': '01 - День 1', 'paragraphs': [1, 2, 3, 4, 5, 6, 7, 8]}, {'slug': 'day-2', 'title': 'День 2', 'archive_folder': '02 - День 2', 'paragraphs': [9]}, {'slug': 'day-3', 'title': 'День 3', 'archive_folder': '03 - День 3', 'paragraphs': [10]}, {'slug': 'day-4', 'title': 'День 4', 'archive_folder': '04 - День 4', 'paragraphs': [11, 12]}]
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already initialized; use content-only or display'
    rawfile=root/'.tmp/new-york-2012/owner-raw.txt'
    source.parent.mkdir(parents=True,exist_ok=True)
    if not source.exists():shutil.copy2(rawfile,source)
    assert source.read_bytes()==rawfile.read_bytes()
    rawtext=source.read_text(encoding='utf-8-sig')
    ps=[l[:-1] if l.endswith('\\') else l for l in rawtext.splitlines()]
    marker='**(\u00a0[Collapse](https://olgau.livejournal.com/137622.html#cutid1)\u00a0)**'
    assert marker in ps[3]
    ps[3]=ps[3].replace(marker,'')+ps[4];ps.pop(4)
    assert len(ps)==12
    photos=[];counts={}
    name_ch={n:c for c in chapters for j in c['paragraphs'] for bs in blocks.get(str(j),[]) for n in bs}
    for i,name in enumerate([n for bs in blocks.values() for b in bs for n in b],1):
        original=site_to_source[name]; src=source_photos/original; c=name_ch[name];counts[c['slug']]=counts.get(c['slug'],0)+1;rel=c['archive_folder']+f"/{counts[c['slug']]:02}_{original}";dest=archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(src,dest)
        sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
        with Image.open(dest) as im:
            ex=im.getexif();date=ex.get_ifd(34665).get(36867);upright=ImageOps.exif_transpose(im)
            assert date and '2011:05:18'<=date[:10]<='2011:05:21'
            photos.append({'source_name':original,'source_path':str(src),'chapter':c['slug'],'site_filename':name,'archive_name':rel,'sha256':sha,'bytes':dest.stat().st_size,'width':upright.width,'height':upright.height,'exif_date':date,'exif_orientation':ex.get(274,1),'r2_key':f"{slug}/{c['slug']}/{name}"})
    m={'chapters':chapters,'trip':slug,'contentDir':f'content/americas/usa/{slug}','archive_root':str(archive.relative_to(Path('G:/My Drive/Family Travel Blog Photos'))).replace('\\','/'),'title':'Нью-Йорк','source':{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'kind':'owner-pasted-LJ-text','lj_url':'https://olgau.livejournal.com/137622.html','archive_name':'Источники/'+source.name,'formatting_removed':['Markdown line-break backslashes','LJ Collapse button inside fourth paragraph; sentence joined across button']},'author_paragraphs':ps,'rendered_paragraphs':ps,'dates':{'start_month':'2012-05','end_month':'2012-05','photo_exif_start':'2011-05-18','photo_exif_end':'2011-05-21','evidence':'Owner confirms 40th birthday in 2012 and camera gift; source says previous year Washington (2011). All206 original camera dates May18–21 2011; camera year wrong, retained unchanged in originals.'},'photos':photos,'layout':blocks,'mosaic_blocks':[],'featured_photos':[],'cover_image':None,'drive_sync_verified':False,'storage':{'originals_verified':True,'drive_sync_verified':False,'r2_verified':False},'publication':{'draft':True,'authorized':False},'text_policy':'Owner pasted complete LJ text. No spelling, wording or punctuation changes. Markdown line breaks and LJ Collapse button are presentation controls; fourth paragraph rejoined across button. No invented headings or captions.'}

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
        data[o['chapter']+'/'+o['site_filename']]={'w':w,'h':h}
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
date: 2012-05-18
trip_year: 2012
trip_start: "2012-05"
trip_end: "2012-05"
short_trip: "usa"
continent: "Северная Америка"
country: "США"
geo_countries:
  - usa
readable_photos: true
{cover}---
''',encoding='utf-8')
    for ci,c in enumerate(m['chapters'],1):
        body=[]
        segments=c.get('segments') or [{'paragraph':i,'layout_key':str(i)} for i in c['paragraphs']]
        for seg in segments:
            para=m['rendered_paragraphs'][seg['paragraph']-1] if 'paragraph' in seg else m['additional_sources'][seg['additional_source']]['paragraphs'][seg['paragraph_index']]
            body.append('<p>'+html.escape(para,quote=False)+'</p>')
            for block in m['layout'].get(seg['layout_key'],[]):body.append('{{< row "'+' '.join(block)+'" >}}')
        body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
        chapter=trip/c['slug'];chapter.mkdir(exist_ok=True)
        alias='aliases: ["/americas/usa/new-york-2012/story/"]\n' if ci==1 else ''
        fm='---\ntitle: '+json.dumps(c['title'],ensure_ascii=False)+'\ndraft: '+str(m['publication']['draft']).lower()+'\ndate: 2012-05-18\nweight: '+str(ci)+'\nchapter_kind: "Заметка"\nlayout: "photo-story"\ncity: "Нью-Йорк"\nplaces: ["new-york"]\nauto_gallery: false\n'+alias+'---\n\n'
        chapter.joinpath('index.md').write_text(fm+'\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('New York 2012:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

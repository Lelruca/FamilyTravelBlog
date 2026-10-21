from pathlib import Path
import json,hashlib,html,shutil,sys,re,zipfile,xml.etree.ElementTree as ET
from PIL import Image,ImageOps
root=Path(__file__).resolve().parents[1]
CONFIG={'trip': 'atlantic-city-philadelphia-2017',
 'title': 'Atlantic City и Филадельфия',
 'archive_root': 'North America/2017 - Atlantic City и Philadelphia',
 'source': 'G:/My Drive/Family Travel Blog Photos/Отчеты/Штаты - разное.docx',
 'paragraph_indices': [183, 184, 185, 189, 190, 191, 192],
 'chapters': [{'slug': 'atlantic-city',
               'title': 'Atlantic City',
               'city': 'Atlantic City',
               'place': 'atlantic-city',
               'folder': '01 - Atlantic City',
               'source_folder': 'D:/OneDrive/Photo/2017/2017 лето/Atlantic City',
               'paragraphs': [1, 2, 3]},
              {'slug': 'philadelphia',
               'title': 'Филадельфия',
               'city': 'Philadelphia',
               'place': 'philadelphia',
               'folder': '02 - Philadelphia',
               'source_folder': 'D:/OneDrive/Photo/2017/2017 лето/Philadelphia',
               'paragraphs': [4, 5, 6, 7]}],
 'layout': {'2': [['20170804_012207.jpg', '20170804_121224.jpg'],
                  ['20170804_121245.jpg', '20170804_121417.jpg']],
            '3': [['20170804_122808.jpg', '20170804_122830.jpg'],
                  ['20170804_144504.jpg', '20170804_145207.jpg', '20170804_150054.jpg'],
                  ['20170804_183844.jpg', '20170804_184124.jpg'],
                  ['20170804_215910.jpg', '20170805_210842.jpg'],
                  ['20170804_222635.jpg', '20170804_222836.jpg'],
                  ['20170804_223649.jpg', '20170804_224238.jpg']],
            '4': [['20170805_131841.jpg', '20170805_153831.jpg'],
                  ['20170805_140133.jpg', '20170805_140332.jpg', '20170805_143941.jpg'],
                  ['20170805_134657.jpg'],
                  ['20170805_144144.jpg', '20170805_145841.jpg'],
                  ['20170805_145942.jpg', '20170805_150244.jpg'],
                  ['20170805_150105.jpg', '20170805_150513.jpg', '20170805_151647.jpg'],
                  ['20170805_154304.jpg', '20170805_154655.jpg'],
                  ['20170805_154854.jpg', '20170805_155045.jpg', '20170805_155615.jpg'],
                  ['20170805_161601.jpg', '20170805_171504.jpg', '20170805_191109.jpg']]},
 'caption_sources': {'20170805_144144.jpg': {'label': '20170805_144149.jpg',
                                             'caption': 'Хендрик Гольциус — Без Цереры и Вакха Венера '
                                                        'замёрзнет'},
                     '20170805_145841.jpg': {'label': '20170805_145848.jpg',
                                             'caption': 'Жоан Миро — Лошадь, трубка и красный цветок'},
                     '20170805_145942.jpg': {'label': '20170805_145947.jpg',
                                             'caption': 'Василий Кандинский — Импровизация № 29 (Лебедь)'},
                     '20170805_150105.jpg': {'label': '20170805_150110.jpg',
                                             'caption': 'Доротея Таннинг — День рождения'},
                     '20170805_150244.jpg': {'label': '20170805_150250.jpg',
                                             'caption': 'Василий Кандинский — Круги в круге'},
                     '20170805_151647.jpg': {'label': '20170805_151650.jpg',
                                             'caption': 'Мэри Кассат — Женщина с жемчужным ожерельем в '
                                                        'ложе'}}}
slug=CONFIG['trip'];mf=root/'media-manifests'/f'{slug}.json';archive=Path('G:/My Drive/Family Travel Blog Photos')/CONFIG['archive_root'];source=Path(CONFIG['source'])
if '--archive' in sys.argv:
 assert not mf.exists()
 with zipfile.ZipFile(source) as z:doc=ET.fromstring(z.read('word/document.xml'))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
 assert ps[180]=='Atlantic City и Philadelphia - лето 2017'
 raw=[ps[i] for i in CONFIG['paragraph_indices']];rendered=[re.sub(r'<lj-cut[^>]*>','',p) for p in raw];photos=[];refs=[]
 def original(src,rel):
  dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(src,dest)
  sha=hashlib.sha256(src.read_bytes()).hexdigest();assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
  with Image.open(dest) as im:
   ex=im.getexif();up=ImageOps.exif_transpose(im);w,h=up.size;date=ex.get_ifd(34665).get(36867)
  return dict(source_name=src.name,source_path=str(src),archive_name=rel,sha256=sha,bytes=dest.stat().st_size,width=w,height=h,exif_date=date,exif_orientation=ex.get(274,1))
 for c in CONFIG['chapters']:
  names=[n for i in c['paragraphs'] for block in CONFIG['layout'].get(str(i),[]) for n in block]
  for j,n in enumerate(names,1):
   o=original(Path(c['source_folder'])/n,c['folder']+f'/{j:02}_{n}');o.update(chapter=c['slug'],site_filename=n,r2_key=f"{slug}/{c['slug']}/{n}");photos.append(o)
 for j,(name,cap) in enumerate(CONFIG['caption_sources'].items(),1):
  o=original(Path(CONFIG['chapters'][1]['source_folder'])/cap['label'],f"Источники/Этикетки/{j:02}_"+cap['label']);o['for_photo']=name;refs.append(o)
 dest=archive/'Источники'/source.name;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(source,dest)
 assert dest.read_bytes()==source.read_bytes()
 m=dict(trip=slug,title=CONFIG['title'],contentDir=f'content/americas/usa/{slug}',archive_root=CONFIG['archive_root'],source=dict(path=str(source),archive_name='Источники/'+source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),heading=ps[180],paragraph_indices=CONFIG['paragraph_indices'],old_photo_references=[ps[i] for i in [182,186,187,188]],service_markup_removed=['<lj-cut text="Но...">']),author_paragraphs=raw,rendered_paragraphs=rendered,chapters=CONFIG['chapters'],layout=CONFIG['layout'],caption_sources=CONFIG['caption_sources'],reference_labels=refs,photos=photos,cover_image=None,drive_sync_verified=False,storage=dict(originals_verified=True,drive_sync_verified=False,r2_verified=False),publication=dict(draft=True,authorized=False),selection='38 photos selected from72 originals after visual inspection; near duplicates and label pictures excluded from public gallery. Six full labels retained in archive for verified author/title captions. No originals changed.',text_policy='Seven whole paragraphs preserved; only service lj-cut removed; no rewriting, typo correction, paragraph splits or new prose.')
else:m=json.loads(mf.read_text(encoding='utf-8'))
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
        if o['site_filename'] in m['caption_sources']:data[o['chapter']+'/'+o['site_filename']]['caption']=m['caption_sources'][o['site_filename']]['caption']
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
date: 2017-08-04
trip_year: 2017
trip_start: "2017-08"
trip_end: "2017-08"
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
        for i in c['paragraphs']:
            body.append('<p>'+html.escape(m['rendered_paragraphs'][i-1],quote=False)+'</p>')
            for block in m['layout'].get(str(i),[]):body.append('{{< row "'+' '.join(block)+'" >}}')
        body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
        chapter=trip/c['slug'];chapter.mkdir(exist_ok=True)
        fm='---\ntitle: '+json.dumps(c['title'],ensure_ascii=False)+'\ndraft: '+str(m['publication']['draft']).lower()+'\ndate: 2017-08-04\nweight: '+str(ci)+'\nchapter_kind: "Заметка"\nlayout: "photo-story"\ncity: '+json.dumps(c['city'],ensure_ascii=False)+'\nplaces: ["'+c['place']+'"]\nauto_gallery: false\n---\n\n'
        chapter.joinpath('index.md').write_text(fm+'\n\n'.join(body)+'\n',encoding='utf-8')
text=json.dumps(m,ensure_ascii=False,indent=2)+'\n';mf.write_text(text,encoding='utf-8');(archive/'photo-manifest.json').write_text(text,encoding='utf-8')
print('Atlantic City / Philadelphia2017:',len(m['author_paragraphs']),'verbatim paragraphs;',len(m['photos']),'selected photographs;', 'archive phase' if '--archive' in sys.argv else 'draft prepared')

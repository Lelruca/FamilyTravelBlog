"""Reproducible draft preparation. Configuration contains the visual selection."""
from pathlib import Path
import json, hashlib, shutil, re, html, sys, zipfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=Path('G:/My Drive/Family Travel Blog Photos')
BASE='https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'
slug=sys.argv[1]
cfg=json.loads((ROOT/'scripts/trip-configs'/f'{slug}.json').read_text(encoding='utf-8'))
mf=ROOT/'media-manifests'/f'{slug}.json'
archive=ARCHIVE/cfg['archive_root']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(p):
    p=re.sub(r'<img\b[^>]*>','',p)
    p=re.sub(r'</?lj-cut\b[^>]*>','',p)
    p=re.sub(r'<lj user="([^"]+)"\s*/?>',r'\1',p)
    p=re.sub(r'</?b>','',p)
    return p.strip()
if '--archive' in sys.argv:
    assert not mf.exists(), 'Archive already exists; do not overwrite selections'
    src=Path(cfg['source'])
    with zipfile.ZipFile(src) as z:doc=ET.fromstring(z.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    originals=[]
    for c in cfg['chapters']:
        names=[n for rows in c['layout'].values() for row in rows for n in row]
        assert len(names)==len(set(names)), 'Duplicate photo in chapter'
        for i,n in enumerate(names,1):
            source=Path(cfg.get('photo_sources',{}).get(n,str(Path(cfg['photo_folder'])/n)))
            rel=c['folder']+f'/{i:02}_{n}'
            dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copy2(source,dest)
            assert digest(source)==digest(dest)
            with Image.open(dest) as im:
                ex=im.getexif();w,h=ImageOps.exif_transpose(im).size
                date=ex.get_ifd(34665).get(36867)
            originals.append(dict(source_name=n,source_path=str(source),archive_name=rel,sha256=digest(dest),bytes=dest.stat().st_size,width=w,height=h,exif_date=date,exif_orientation=ex.get(274,1),chapter=c['slug'],site_filename=n,r2_key=f'{slug}/{c["slug"]}/{n}'))
    rel='Источники/'+src.name;dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(src,dest)
    assert digest(src)==digest(dest)
    indices=[i for c in cfg['chapters'] for i in c['paragraphs']]
    assert len(indices)==len(set(indices))
    m=dict(trip=slug,title=cfg['title'],contentDir=cfg['contentDir'],archive_root=cfg['archive_root'],source=dict(path=str(src),archive_name=rel,sha256=digest(src),paragraph_indices=indices,all_source_paragraphs=ps),author_paragraphs=[ps[i] for i in indices],rendered_paragraphs=[clean(ps[i]) for i in indices],chapters=cfg['chapters'],photos=originals,reference_labels=[],drive_sync_verified=False,storage=dict(originals_verified=True,drive_sync_verified=False,r2_verified=False),publication=dict(draft=True,authorized=False),cover_image=cfg['cover_image'],cover_selection='Provisional selection for joint owner review; preparation authorized while owner away.',text_policy='Whole author paragraphs, original spelling and punctuation; LJ image/cut service markup removed and LJ usernames retained.')
    for j,(name,ref) in enumerate(cfg.get('caption_sources',{}).items(),1):
        source=Path(cfg['photo_folder'])/ref['label'];rel=f'Источники/Этикетки/{j:02}_'+source.name
        dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(source,dest)
        assert digest(source)==digest(dest)
        m['reference_labels'].append(dict(source_name=source.name,source_path=str(source),archive_name=rel,bytes=dest.stat().st_size,sha256=digest(dest),for_photo=name,caption=ref['caption']))
else:m=json.loads(mf.read_text(encoding='utf-8'))
if '--display' in sys.argv:
    assert m['drive_sync_verified']
    copies=[];data={}
    for o in m['photos']:
        src=archive/o['archive_name'];assert digest(src)==o['sha256']
        dest=ROOT/'static/r2'/o['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
        with Image.open(src) as raw:
            im=ImageOps.exif_transpose(raw)
            if max(im.size)<=2000 and o['exif_orientation']==1:shutil.copy2(src,dest)
            else:
                im.thumbnail((2000,2000));im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
            w,h=im.size
        copies.append(dict(key=o['r2_key'],original_archive_name=o['archive_name'],width=w,height=h,bytes=dest.stat().st_size,sha256=digest(dest)))
        data[o['chapter']+'/'+o['site_filename']]={'w':w,'h':h}
        if o['site_filename'] in cfg.get('captions',{}):data[o['chapter']+'/'+o['site_filename']]['caption']=cfg['captions'][o['site_filename']]
    m['r2']={'photos':copies,'status':'awaiting-public-verification'}
    (ROOT/'data/photos'/f'{slug}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if '--archive' not in sys.argv:
    trip=ROOT/cfg['contentDir'];trip.mkdir(parents=True,exist_ok=True)
    fm=dict(title=cfg['title'],type='trips',draft=m['publication']['draft'],date=cfg['date'],trip_year=int(cfg['date'][:4]),trip_start=cfg['date'][:7],trip_end=cfg['date'][:7],short_trip=cfg['short_trip'],continent=cfg['continent'],country=cfg['country'],geo_countries=[cfg['geo_country']],readable_photos=True,cover_image=BASE+slug+'/'+cfg['cover_image'])
    if not cfg['short_trip']:fm.pop('short_trip')
    if cfg.get('strict_photo_cap'):fm['strict_photo_cap']=True
    def front(d):return '---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in d.items())+'\n---\n\n'
    (trip/'_index.md').write_text(front(fm).rstrip()+'\n',encoding='utf-8')
    ps=m['source']['all_source_paragraphs']
    for order,c in enumerate(cfg['chapters'],1):
        body=[]
        for i in c['paragraphs']:
            paragraph_class=' class="compact-list-item"' if i in c.get('compact_list_items',[]) else (' class="compact-list-intro"' if i in c.get('compact_list_intros',[]) else '')
            paragraph='<p'+paragraph_class+'>'+html.escape(clean(ps[i]),quote=False)+'</p>'
            if str(i) in c.get('beside',{}):
                body.append('{{< beside "'+c['beside'][str(i)]+'" >}}\n'+paragraph+'\n{{< /beside >}}')
                continue
            body.append(paragraph)
            blocks=c.get('photo_blocks',{}).get(str(i))
            if blocks is None:blocks=[{'kind':'row','names':row} for row in c['layout'].get(str(i),[])]
            for block in blocks:body.append('{{< '+block['kind']+' "'+' '.join(block['names'])+'" >}}')
        body.append('<style>.photo-essay{--essay-gap:16px;--cap-h:80svh}</style>')
        if c.get('compact_list_items'):body.append('<style>.photo-essay p.compact-list-intro{margin-bottom:6px}.photo-essay p.compact-list-item{margin-top:0;margin-bottom:4px}</style>')
        d=trip/c['slug'];d.mkdir(exist_ok=True)
        chapter_front=dict(title=c['title'],draft=m['publication']['draft'],date=cfg['date'],weight=order,chapter_kind='Заметка',layout='photo-story',city=c['city'],places=c['places'],auto_gallery=False)
        if c.get('hero_image'):chapter_front['hero_image']=c['hero_image']
        if c.get('hero_card_image'):chapter_front['hero_card_image']=c['hero_card_image']
        (d/'index.md').write_text(front(chapter_front)+'\n\n'.join(body)+'\n',encoding='utf-8')
out=json.dumps(m,ensure_ascii=False,indent=2)+'\n'
mf.write_text(out,encoding='utf-8');(archive/'photo-manifest.json').write_text(out,encoding='utf-8')
print(slug,len(m['author_paragraphs']),'paragraphs;',len(m['photos']),'photos')

"""Rebuild display copies and chapter layout from the verified Drive originals.

Requires Pillow. Run from the project root after archive_verified and
drive_sync_verified are true in media-manifests/rome-2015-2016.json.
Originals are never changed. Upload/HTTP verification is a separate stage.
"""
from pathlib import Path
from PIL import Image, ImageOps
import json, re, html, hashlib, sys

root=Path.cwd();trip='rome-2015-2016'
mf=root/'media-manifests'/f'{trip}.json';m=json.loads(mf.read_text(encoding='utf-8-sig'))
assert m['archive_verified'] and m['drive_sync_verified'],'Verify Drive archive first'
plan=json.loads((root/'media-manifests'/f'{trip}-layout.json').read_text(encoding='utf-8-sig'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
base='https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'
data={};copies=[];bykey={}
for p in m['album_originals']:
    source=archive/p['original_relative_path']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==p['original_sha256']
    name=re.sub(r'\.(jpe?g|png)$','.jpg',p['original_filename'],flags=re.I).replace(' ','_')
    key=f'{trip}/{p["chapter"]}/{name}'
    dest=root/'static/r2'/key;dest.parent.mkdir(parents=True,exist_ok=True)
    if '--layout-only' in sys.argv:
        with Image.open(dest) as im:w,h=im.size
    else:
        with Image.open(source) as original:
            im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((2000,2000),Image.Resampling.LANCZOS)
            im.save(dest,quality=85,optimize=True)
            w,h=im.size
    sha=hashlib.sha256(dest.read_bytes()).hexdigest()
    item={'key':key,'archiveFile':p['original_relative_path'],'original_sha256':p['original_sha256'],'w':w,'h':h,'bytes':dest.stat().st_size,'sha256':sha,'recipe':{'tool':'Pillow','exif_transpose':True,'long_side_max':2000,'no_upscale':True,'jpeg_quality':85,'optimize':True}}
    assert key not in [c['key'] for c in copies],key
    copies.append(item);p['site_filename']=name;p['r2_key']=key
    data[f'{p["chapter"]}/{name}']={'w':w,'h':h,'source':p['original_relative_path']}
    bykey[p['chapter'],p['layout_photo_number']]=(p,name)

def blocks(slug,numbers):
    # Equal-height rows respect the full frames, including people. Square
    # album edits stay square; no extra crops are applied to screen copies.
    groups=[];current=[];ratio=0
    for n in numbers:
        p,name=bykey[slug,n];info=data[f'{slug}/{name}'];current.append(name);ratio+=info['w']/info['h']
        if len(current)>=4 or (len(current)>=2 and ratio>=3):groups.append(current);current=[];ratio=0
    if current:
        if len(current)==1 and groups and len(groups[-1])==4:groups.append([groups[-1].pop()]+current)
        elif len(current)==1 and groups and len(groups[-1])<4:groups[-1]+=current
        else:groups.append(current)
    return ['{{< row "'+' '.join(g)+'" >}}' for g in groups]

places={'kleve':['kleve','nijmegen'],'florence-uffizi':['florence'],'florence-museums':['florence'],'florence-duomo':['florence'],'rome-night':['rome'],'vatican':['vatican'],'rome-colosseum':['rome'],'naples':['naples'],'pompeii':['pompeii'],'tivoli':['tivoli','rome'],'milan':['milan'],'conclusion':[]}
for c in m['chapters']:
    slug=c['slug'];f=root/f'content/europe/italy/{trip}/{slug}/index.md';src=f.read_text(encoding='utf-8');fm=src.split('---\n',2)[1];body=src.split('---\n',2)[2]
    paras=re.findall(r'<p>(.*?)</p>',body,re.S)
    assert hashlib.sha256('\n'.join(html.unescape(p) for p in paras).encode()).hexdigest()==c['text_sha256'],slug
    fm=re.sub(r'^hero_image:.*\n','',fm,flags=re.M);fm=re.sub(r'^places:\n(?:  - .*\n)*','',fm,flags=re.M)
    if slug in plan:
        hero=plan[slug]['hero'];_,name=bykey[slug,hero];assert data[f'{slug}/{name}']['w']>data[f'{slug}/{name}']['h'],(slug,'portrait cover')
        fm+='hero_image: '+json.dumps(name)+'\n'
    else:
        _,name=bykey['pompeii',21];fm+='hero_image: '+json.dumps(base+trip+'/pompeii/'+name)+'\n'
    if places[slug]:fm+='places:\n'+''.join('  - '+p+'\n' for p in places[slug])
    out=[]
    for n,p in enumerate(paras,1):
        out.append('<p>'+p+'</p>')
        if slug in plan:
            group=[i for i in plan[slug]['groups'].get(str(n),[]) if i!=plan[slug]['hero']]
            out.extend(blocks(slug,group))
    f.write_text('---\n'+fm+'---\n'+'\n\n'.join(out)+'\n',encoding='utf-8')
data_path=root/'data/photos'/f'{trip}.json';data_path.write_text(json.dumps(dict(sorted(data.items())),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
_,cover=bykey['rome-colosseum',17]
tripfile=root/f'content/europe/italy/{trip}/_index.md';s=tripfile.read_text(encoding='utf-8');s=s.replace('---\nsource_url:', '---\nsource_url:')
s=re.sub(r'^(?:cover_image|cover_position|cover_who):.*\n','',s,flags=re.M)
s=s.replace('source_url:', 'cover_image: '+json.dumps(base+trip+'/rome-colosseum/'+cover)+'\ncover_position: "center 40%"\ncover_who: "Леля, Марина, Наташа и Лиза"\nsource_url:',1)
tripfile.write_text(s,encoding='utf-8')
if '--layout-only' not in sys.argv:
    m['r2']={'status':'copies-prepared-awaiting-upload','photos':copies};m['status']='screen-copies-prepared'
mf.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(archive/'photo-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared',len(copies),'screen copies and 12 chapter layouts')

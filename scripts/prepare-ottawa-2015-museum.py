"""Reproduce museum display copies from cloud-verified full archival originals."""
from pathlib import Path
import hashlib,json,sys
from PIL import Image,ImageOps

root=Path(__file__).resolve().parents[1]
file=root/'media-manifests/ottawa-2015.json'
m=json.loads(file.read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
assert m['drive_sync_verified']
datafile=root/'data/photos/ottawa-2015.json'
data=json.loads(datafile.read_text(encoding='utf-8'))
missing_only='--missing-only' in sys.argv
copies=[p for p in m['r2']['photos'] if missing_only or not p['key'].startswith('ottawa-2015/museum/')]
for p in m['photos']:
    if p['chapter']!='museum':continue
    if missing_only and any(c['key']==p['r2_key'] and c.get('public_verified') for c in copies):continue
    assert p.get('drive_id') and not p['drive_id'].startswith('local')
    src=archive/p['archive_name']
    assert hashlib.sha256(src.read_bytes()).hexdigest()==p['sha256']
    dest=root/'static/r2'/p['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(src) as raw:
        im=ImageOps.exif_transpose(raw)
        rotation=p.get('display_rotation_ccw',0)
        if rotation:im=im.rotate(rotation,expand=True)
        im.thumbnail((2000,2000))
        im.convert('RGB').save(dest,'JPEG',quality=85,optimize=True)
        width,height=im.size
    copies.append(dict(key=p['r2_key'],original_archive_name=p['archive_name'],width=width,height=height,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),public_verified=False,display_rotation_ccw=p.get('display_rotation_ccw',0)))
    data['museum/'+p['site_filename']]={'w':width,'h':height,'caption':str(p['year'])}
m['r2']['photos']=copies
m['storage']['r2_verified']=False
m['r2']['status']='museum-copies-awaiting-public-verification'
out=json.dumps(m,ensure_ascii=False,indent=2)+'\n'
file.write_text(out,encoding='utf-8');(archive/'photo-manifest.json').write_text(out,encoding='utf-8')
datafile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared museum display copies:',sum(p['chapter']=='museum' for p in m['photos']))

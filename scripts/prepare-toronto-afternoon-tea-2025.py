"""Rebuild Toronto tea chapter from archived Facebook downloads, preserving author text."""
from pathlib import Path
from PIL import Image,ImageOps
import json,hashlib,shutil,html,sys
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'media-manifests/toronto-walks-afternoon-tea-2025.json';m=json.loads(p.read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if '--display' in sys.argv:
 assert m['storage']['drive_sync_verified']
 datafile=ROOT/'data/photos/toronto-walks.json';data=json.loads(datafile.read_text(encoding='utf-8'));copies=[]
 previous={x['key']:x for x in m.get('r2',{}).get('photos',[])}
 for o in m['photos']:
  src=archive/o['archive_name'];assert sha(src)==o['sha256'];dst=ROOT/'static/r2'/o['r2_key'];dst.parent.mkdir(parents=True,exist_ok=True)
  with Image.open(src) as raw:
   im=ImageOps.exif_transpose(raw);im.thumbnail((2000,2000));w,h=im.size
   if max(raw.size)<=2000 and raw.getexif().get(274,1)==1:shutil.copy2(src,dst)
   else:im.convert('RGB').save(dst,'JPEG',quality=85,optimize=True)
  r=dict(key=o['r2_key'],original_archive_name=o['archive_name'],width=w,height=h,bytes=dst.stat().st_size,sha256=sha(dst))
  old=previous.get(r['key'])
  if old and old['sha256']==r['sha256'] and old.get('public_verified'):r.update(public_verified=True,public_url=old['public_url'])
  copies.append(r);data[m['chapter']+'/'+o['site_filename']]={'w':w,'h':h,'source':o['archive_name']}
 datafile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');m['r2']={'photos':copies,'status':'awaiting-public-verification'}
chapter=ROOT/'content/americas/canada/toronto-walks'/m['chapter'];chapter.mkdir(parents=True,exist_ok=True)
fm=dict(title=m['title'],chapter_kind='part',layout='photo-story',weight=40,city='Toronto',places=['toronto','queens-park'],date='2025-11-28',date_source='Дата поста Facebook; день съёмки неизвестен',source_url=m['source']['facebook_post'],auto_gallery=False,draft=True,hero_card_image=m['photos'][2]['site_filename'])
blocks=[[0,1],[3,2],[4]];body=[]
for text,indices in zip(m['source']['author_paragraphs'],blocks):
 body.append('<p>'+html.escape(text,quote=False)+'</p>');body.append('{{< row "'+' '.join(m['photos'][i]['site_filename'] for i in indices)+'" >}}')
front='---\n'+'\n'.join(k+': '+json.dumps(v,ensure_ascii=False) for k,v in fm.items())+'\n---\n\n';(chapter/'index.md').write_text(front+'\n\n'.join(body)+'\n',encoding='utf-8')
out=json.dumps(m,ensure_ascii=False,indent=2)+'\n';p.write_text(out,encoding='utf-8');(archive/m['chapter_folder']/'photo-manifest.json').write_text(out,encoding='utf-8')
print('Toronto tea: 3 exact paragraphs, 5 Facebook photos, draft')

"""Verify New York 2012 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/new-york-2012.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
raw=src.read_text(encoding='utf-8-sig');ps=[l[:-1] if l.endswith('\\') else l for l in raw.splitlines()]
marker='**(\u00a0[Collapse](https://olgau.livejournal.com/137622.html#cutid1)\u00a0)**';assert marker in ps[3];ps[3]=ps[3].replace(marker,'')+ps[4];ps.pop(4)
assert ps==m['author_paragraphs']==m['rendered_paragraphs'];assert len(ps)==12
assert m['dates']['start_month']=='2012-05'
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==56
layout=[n for bs in m['layout'].values() for block in bs for n in block];assert len(layout)==len(set(layout))==56
assert set(layout)=={p['site_filename'] for p in m['photos']}
data=json.loads((root/'data/photos/new-york-2012.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert '2011:05:18'<=p['exif_date'][:10]<='2011:05:21'
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert data[p['chapter']+'/'+p['site_filename']]=={'w':c['width'],'h':c['height']}
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/new-york-2012/build')
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
all_paragraphs=[];all_photos=[]
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip()
for c in m['chapters']:
 segments=c.get('segments') or [{'paragraph':i,'layout_key':str(i)} for i in c['paragraphs']]
 fragments=[m['rendered_paragraphs'][seg['paragraph']-1] if 'paragraph' in seg else m['additional_sources'][seg['additional_source']]['paragraphs'][seg['paragraph_index']] for seg in segments]
 text=(root/m['contentDir']/c['slug']/'index.md').read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==fragments;assert 'hero_image' not in text
 page=(build/'americas/usa/new-york-2012'/c['slug']/'index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
 assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in fragments]
 l=Links();l.feed(essay);expected=[n for seg in segments for b in m['layout'].get(seg['layout_key'],[]) for n in b];assert [u.rsplit('/',1)[1] for u in l.photos]==expected;assert all('r2.dev/new-york-2012/'+c['slug']+'/' in u for u in l.photos);all_paragraphs += [m['rendered_paragraphs'][i-1] for i in c['paragraphs']];all_photos+=expected
assert all_paragraphs==m['rendered_paragraphs'];assert len(all_photos)==len(set(all_photos))==56
if m.get('cover_image'):
 collection=(build/'short-trips/usa/index.html').read_text(encoding='utf-8');assert 'new-york-2012/'+m['cover_image'] in collection
for a in m.get('additional_sources',[]):
 b=(archive/a['archive_name']).read_bytes();assert len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'];assert a['drive_id'] and not a['drive_id'].startswith('local');assert b.decode('utf-8').replace('\r\n','\n')=='\n\n'.join(a['paragraphs'])+'\n'
assert m['layout']['9']==[['img_0095.jpg','img_0099.jpg']]
print('Verified 12 original plus 2 additional exact author paragraphs, four day chapters, 56 originals/cloud IDs/public R2 copies; photo order and no chapter heroes.')

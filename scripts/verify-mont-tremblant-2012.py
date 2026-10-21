"""Verify Washington 2011 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/mont-tremblant-2012.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
with zipfile.ZipFile(src) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
assert ps[21]==m['source']['heading'];assert [ps[i] for i in m['source']['paragraph_indices']]==m['author_paragraphs'];assert len(m['author_paragraphs'])==9
assert m['rendered_paragraphs']==[p.replace('<lj-cut text="Продолжение и фото...">','') for p in m['author_paragraphs']]
assert [p['filename'].lower() for p in m['source']['photo_references']]==['img_20121223_141100.jpg','img_20121224_124144.jpg']
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==6
layout=[n for bs in m['layout'].values() for block in bs for n in block];assert len(layout)==len(set(layout))==6
assert set(layout)=={p['site_filename'] for p in m['photos']}
data=json.loads((root/'data/photos/mont-tremblant-2012.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert p.get('owner_added') or p['exif_date'][:10] in ['2012:12:23','2012:12:24']
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert data['story/'+p['site_filename']]=={'w':c['width'],'h':c['height']}
fragments=m['rendered_paragraphs']
chapter=root/m['contentDir']/'story/index.md';text=chapter.read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==fragments;assert 'hero_image' not in text and ('draft: '+str(m['publication']['draft']).lower()) in text
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/mont-tremblant-2012/build');page=(build/'americas/canada/mont-tremblant-2012/story/index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip();assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in fragments]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
l=Links();l.feed(essay);assert [u.rsplit('/',1)[1] for u in l.photos]==layout;assert all('r2.dev/mont-tremblant-2012/story/' in u for u in l.photos)
if m.get('cover_image'):
 trip=(build/'americas/canada/mont-tremblant-2012/index.html').read_text(encoding='utf-8');collection=(build/'short-trips/canada/index.html').read_text(encoding='utf-8');cover='mont-tremblant-2012/'+m['cover_image'];assert cover in collection and 'mont-tremblant-2012/story/' in trip
print('Verified 9 exact author paragraphs, LJ formatting removal only, 6 archived originals with cloud IDs and public R2 copies; photo order, short-trip cover and no chapter hero.')

"""Verify Quebec 2003 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/quebec-montreal-2003.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
with zipfile.ZipFile(src) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
assert ps[0]==m['source']['heading'];assert [ps[i] for i in m['source']['paragraph_indices']]==m['author_paragraphs'];assert len(m['author_paragraphs'])==17
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==23
layout=[n for bs in m['layout'].values() for block in bs for n in block];assert len(layout)==len(set(layout))==23
assert set(layout)=={p['site_filename'] for p in m['photos']};assert not set(layout)&{'mq_0020.jpg','mq_0021.jpg','mq_0015_p.jpg'}
data=json.loads((root/'data/photos/quebec-montreal-2003.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert p['exif_date'][:10] in ['2003:05:17','2003:05:18','2003:05:19']
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert data['story/'+p['site_filename']]=={'w':c['width'],'h':c['height']}
chapter=root/m['contentDir']/'story/index.md';text=chapter.read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==m['author_paragraphs'];assert 'hero_image' not in text and ('draft: '+str(m['publication']['draft']).lower()) in text
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/quebec-montreal-2003/build');page=(build/'americas/canada/quebec-montreal-2003/story/index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip();assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in m['author_paragraphs']]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
l=Links();l.feed(essay);assert [u.rsplit('/',1)[1] for u in l.photos]==layout;assert all('r2.dev/quebec-montreal-2003/story/' in u for u in l.photos)
if m.get('cover_image'):
 trip=(build/'americas/canada/quebec-montreal-2003/index.html').read_text(encoding='utf-8');collection=(build/'short-trips/canada/index.html').read_text(encoding='utf-8');cover='quebec-montreal-2003/'+m['cover_image'];assert cover in collection and 'quebec-montreal-2003/story/' in trip
print('Verified 17 verbatim paragraphs, 23 selected originals and public R2 copies, exact photo order, no chapter cover; trip cover '+('selected' if m.get('cover_image') else 'awaits owner choice')+'.')

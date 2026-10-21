"""Verify Washington 2011 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/washington-2011.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
with zipfile.ZipFile(src) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
assert ps[32]==m['source']['heading'];assert ps[41].endswith(m['source']['end_before']);ps[41]=ps[41][:-len(m['source']['end_before'])];assert [ps[i] for i in m['source']['paragraph_indices']]==m['author_paragraphs'];assert len(m['author_paragraphs'])==8
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==20
layout=[n for bs in m['layout'].values() for block in bs for n in block];assert len(layout)==len(set(layout))==19
assert set(layout)=={p['site_filename'] for p in m['photos']}-set(m['owner_removed_site_photos']);assert not set(layout)&{'Copy of IMG_3622.jpg'}
data=json.loads((root/'data/photos/washington-2011.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert p['exif_date'][:10] in ['2011:05:20','2011:05:21','2011:05:22']
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert data['story/'+p['site_filename']]=={'w':c['width'],'h':c['height']}
fragments=m['author_paragraphs']
chapter=root/m['contentDir']/'story/index.md';text=chapter.read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==fragments;assert 'hero_image' not in text and ('draft: '+str(m['publication']['draft']).lower()) in text
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/washington-2011/build');page=(build/'americas/usa/washington-2011/story/index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip();assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in fragments]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
l=Links();l.feed(essay);assert [u.rsplit('/',1)[1] for u in l.photos]==layout;assert all('r2.dev/washington-2011/story/' in u for u in l.photos)
if m.get('cover_asset'):
 a=m['cover_asset'];c=m['r2']['cover'];b=(archive/a['archive_name']).read_bytes();assert len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'] and a['drive_id'] and not a['drive_id'].startswith('local')
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'] and c['public_verified'];assert c['original_archive_name']==a['archive_name']
 assert data['cover/p5221891-wide.jpg']=={'w':c['width'],'h':c['height']} and c['width']>c['height'] and max(c['width'],c['height'])<=2000
 assert a['derived_from_sha256']==next(p['sha256'] for p in m['photos'] if p['site_filename']=='p5221891.jpg')
if m.get('cover_image'):
 trip=(build/'americas/usa/washington-2011/index.html').read_text(encoding='utf-8');collection=(build/'short-trips/usa/index.html').read_text(encoding='utf-8');cover='washington-2011/'+m['cover_image'];assert cover in collection and 'washington-2011/story/' in trip
print('Verified 8 verbatim paragraphs, 20 archived originals and public R2 copies, 19 displayed photographs, exact photo order, no chapter cover; trip cover '+('selected' if m.get('cover_image') else 'awaits owner choice')+'.')

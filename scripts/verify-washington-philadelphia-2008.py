"""Verify exact source paragraphs, archival originals, display copies and built pages."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image,ImageOps
root=Path(__file__).resolve().parents[1];slug='washington-philadelphia-2008';m=json.loads((root/'media-manifests'/f'{slug}.json').read_text(encoding='utf-8'));archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];source=Path(m['source']['path'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==source.read_bytes();assert m['source']['drive_id']
with zipfile.ZipFile(source) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
assert ps[20]==m['source']['heading'] and ps[32]==m['source']['end_before'];assert [ps[i] for i in m['source']['paragraph_indices']]==m['author_paragraphs'];assert len(m['author_paragraphs'])==10
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified']);assert len(m['photos'])==len(m['r2']['photos'])==63
assert json.loads((archive/'photo-manifest.json').read_text(encoding='utf-8'))==m
layout=[n for bs in m['layout'].values() for b in bs for n in b];assert len(layout)==len(set(layout))==63;assert set(layout)=={o['site_filename'] for o in m['photos']}
data=json.loads((root/'data/photos'/f'{slug}.json').read_text(encoding='utf-8'))
for o,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/o['archive_name']).read_bytes();assert len(b)==o['bytes'] and hashlib.sha256(b).hexdigest()==o['sha256'];assert o['drive_id'] and not o['drive_id'].startswith('local')
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['public_verified'] and c['key']==o['r2_key'] and c['original_archive_name']==o['archive_name']
 with Image.open(archive/o['archive_name']) as raw:
  im=ImageOps.exif_transpose(raw)
  if o['additional_rotation_ccw']:im=im.rotate(o['additional_rotation_ccw'],expand=True)
  assert im.size==(o['width'],o['height']);im.thumbnail((2000,2000));assert im.size==(c['width'],c['height'])
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert data[o['chapter']+'/'+o['site_filename']]==dict(w=c['width'],h=c['height'])
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip()
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/washington-philadelphia-2008/build')
for ch in m['chapters']:
 text=(root/m['contentDir']/ch['slug']/'index.md').read_text(encoding='utf-8');expected=[ps[i] for i in ch['indices']]
 assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==expected;assert 'hero_image' not in text and ('draft: '+str(m['publication']['draft']).lower()) in text
 page=(build/'americas/usa'/slug/ch['slug']/'index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
 assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in expected]
 l=Links();l.feed(essay);order=[n for i in ch['indices'] for b in m['layout'].get(str(i),[]) for n in b];assert [u.rsplit('/',1)[1] for u in l.photos]==order;assert all('r2.dev/'+slug+'/'+ch['slug']+'/' in u for u in l.photos)
collection=(build/'short-trips/usa/index.html').read_text(encoding='utf-8');assert slug+'/'+m['cover_image'] in collection;assert '2008 — Вашингтон — Филадельфия' in collection
trip=(root/m['contentDir']/'_index.md').read_text(encoding='utf-8');assert 'trip_start: "2008-08"' in trip and 'trip_end: "2008-09"' in trip
print('Verified: ten exact source paragraphs, two chapters, 63 archived originals and verified public R2 copies, photo order, family cover and collection card.')

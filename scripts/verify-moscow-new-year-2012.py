"""Verify Moscow New Year 2012 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/moscow-new-year-2012.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
raw=src.read_text(encoding='utf-8-sig');parts=[p for p in re.split(r'\n\s*\n',raw) if p.strip()];head=parts[0].splitlines();ps=['\n'.join(head[2:])]+[p.rstrip('\n') for p in parts[2:]]
assert m['title']==head[0];assert ps==m['author_paragraphs']==m['rendered_paragraphs'];assert len(ps)==12
private=m['private_source'];b=(archive/private['archive_name']).read_bytes();assert hashlib.sha256(b).hexdigest()==private['sha256'] and len(b)==private['bytes'];assert private['drive_id'] and not private['drive_id'].startswith('local')
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==52
layout=[n for section in m['text_sections'] for block in section['blocks'] for n in block];assert len(layout)==len(set(layout))==48
assert set(layout)=={p['site_filename'] for p in m['photos']}-set(m['owner_removed_site_photos'])
data=json.loads((root/'data/photos/moscow-new-year-2012.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert '2011:12:25'<=p['exif_date'][:10]<='2012:01:09'
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert {k:data['story/'+p['site_filename']][k] for k in ['w','h']}=={'w':c['width'],'h':c['height']}
sections=m['text_sections'];fragments=[m['rendered_paragraphs'][s['paragraph']-1][s['start']:s['end']] for s in sections]
for i,p in enumerate(m['author_paragraphs'],1):assert ''.join(m['author_paragraphs'][i-1][s['start']:s['end']] for s in sections if s['paragraph']==i)==p
chapter=root/m['contentDir']/'story/index.md';text=chapter.read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==fragments;assert 'hero_image' not in text and ('draft: '+str(m['publication']['draft']).lower()) in text
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/moscow-new-year-2012/build');page=(build/'europe/russia/moscow-new-year-2012/story/index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip();assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in fragments]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
l=Links();l.feed(essay);assert [u.rsplit('/',1)[1] for u in l.photos]==layout;assert all('r2.dev/moscow-new-year-2012/story/' in u for u in l.photos)
if m.get('cover_image'):
 trip=(build/'europe/russia/moscow-new-year-2012/index.html').read_text(encoding='utf-8');collection=(build/'short-trips/europe/index.html').read_text(encoding='utf-8');cover='moscow-new-year-2012/'+m['cover_image'];assert cover in collection and 'moscow-new-year-2012/story/' in trip
assert 'Светик, мы попали' not in page and 'Танюш, возвращаюсь' not in page
print('Verified 12 verbatim public paragraphs, 52 archived originals/cloud IDs/public R2 copies; private letter excluded, photo order and no chapter hero.')

a=m['cover_asset'];c=m['r2']['cover'];b=(archive/a['archive_name']).read_bytes();assert hashlib.sha256(b).hexdigest()==a['sha256'] and len(b)==a['bytes'] and a['drive_id'];b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'] and c['public_verified'];assert c['width']>c['height'] and max(c['width'],c['height'])<=2000;assert data['cover/p1072431.jpg']=={'w':c['width'],'h':c['height']};assert m['cover_choice']['status']=='owner-selected'

assert data['story/img_20120103_131556.jpg']['caption']=='новый дом Саши с Надей'
assert 'новый дом Саши с Надей' in page

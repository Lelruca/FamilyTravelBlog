"""Verify Atlantic City / Philadelphia2017 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/atlantic-city-philadelphia-2017.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
with zipfile.ZipFile(src) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in a.findall('.//w:t',ns)) for a in doc.findall('.//w:body/w:p',ns)]
assert ps[180]==m['source']['heading'];assert [ps[i] for i in m['source']['paragraph_indices']]==m['author_paragraphs'];assert [re.sub(r'<lj-cut[^>]*>','',p) for p in m['author_paragraphs']]==m['rendered_paragraphs'];assert len(m['author_paragraphs'])==7
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==38
layout=[n for bs in m['layout'].values() for block in bs for n in block];assert len(layout)==len(set(layout))==38
assert set(layout)=={p['site_filename'] for p in m['photos']}
data=json.loads((root/'data/photos/atlantic-city-philadelphia-2017.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert p['exif_date'][:10] in ['2017:08:04','2017:08:05']
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert data[p['chapter']+'/'+p['site_filename']]['w']==c['width'] and data[p['chapter']+'/'+p['site_filename']]['h']==c['height']
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/atlantic-philadelphia-2017/build')
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[];self.captions=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href']);self.captions.append(a.get('data-caption'))
all_paragraphs=[];all_photos=[]
norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip()
for c in m['chapters']:
 segments=c.get('segments') or [{'paragraph':i,'layout_key':str(i)} for i in c['paragraphs']]
 fragments=[m['rendered_paragraphs'][seg['paragraph']-1] if 'paragraph' in seg else m['additional_sources'][seg['additional_source']]['paragraphs'][seg['paragraph_index']] for seg in segments]
 text=(root/m['contentDir']/c['slug']/'index.md').read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==fragments;assert 'hero_image' not in text
 page=(build/'americas/usa/atlantic-city-philadelphia-2017'/c['slug']/'index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
 assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in fragments]
 l=Links();l.feed(essay);expected=[n for seg in segments for b in m['layout'].get(seg['layout_key'],[]) for n in b];
 assert [u.rsplit('/',1)[1] for u in l.photos]==expected;assert all('r2.dev/atlantic-city-philadelphia-2017/'+c['slug']+'/' in u for u in l.photos);all_paragraphs += [m['rendered_paragraphs'][i-1] for i in c['paragraphs']];all_photos+=expected
 if c['slug']=='philadelphia':assert l.captions==[data['philadelphia/'+n].get('caption') for n in expected]
assert all_paragraphs==m['rendered_paragraphs'];assert len(all_photos)==len(set(all_photos))==38
if m.get('cover_image'):
 collection=(build/'short-trips/usa/index.html').read_text(encoding='utf-8');assert 'atlantic-city-philadelphia-2017/'+m['cover_image'] in collection
assert len(m['chapters'])==2
assert [sum(1 for p in m['photos'] if p['chapter']==c['slug']) for c in m['chapters']]==[17,21]
print('Verified7 whole author paragraphs,38 full originals/public R2 copies in two chapters;6 label-backed art captions.')


assert len(m['reference_labels'])==6
for p in m['reference_labels']:
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local')
assert not {p['source_name'] for p in m['reference_labels']} & {p['source_name'] for p in m['photos']}
for name,cap in m['caption_sources'].items():assert data['philadelphia/'+name]['caption']==cap['caption']
assert (archive/'photo-manifest.json').read_bytes()==(root/'media-manifests/atlantic-city-philadelphia-2017.json').read_bytes()
assert m['publication']['draft'] is not m['publication']['authorized']

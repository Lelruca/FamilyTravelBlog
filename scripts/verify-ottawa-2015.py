"""Verify Ottawa 2015 source text, archival originals, R2 copies and rendered draft."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as E
from PIL import Image
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/ottawa-2015.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];src=Path(m['source']['path'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==m['source']['sha256'];assert (archive/m['source']['archive_name']).read_bytes()==src.read_bytes()
with zipfile.ZipFile(src) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in a.findall('.//w:t',ns)) for a in doc.findall('.//w:body/w:p',ns)]
assert ps[34]==m['source']['heading'];assert [ps[i] for i in m['source']['paragraph_indices']]==m['author_paragraphs']==m['rendered_paragraphs'];assert len(m['author_paragraphs'])==12
assert m['completion']['prepared_chapters']==['tulips','ottawa','museum'] and m['completion']['pending_chapter'] is None
assert m['drive_sync_verified'] and all(m['storage'][k] for k in ['originals_verified','drive_sync_verified','r2_verified'])
assert len(m['photos'])==len(m['r2']['photos'])==101
layout=[n for bs in m['layout'].values() for block in bs for n in block];assert len(layout)==len(set(layout))==101
assert set(layout)=={p['site_filename'] for p in m['photos']}
data=json.loads((root/'data/photos/ottawa-2015.json').read_text(encoding='utf-8'))
for p,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local');assert p['exif_date'][:10] in ['2015:05:09','2015:05:10','2009:07:25']
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['original_archive_name']==p['archive_name'] and c['key']==p['r2_key'];assert c['public_verified']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000
 assert c['width']<=p['width'] and c['height']<=p['height'];assert data[p['chapter']+'/'+p['site_filename']]['w']==c['width'] and data[p['chapter']+'/'+p['site_filename']]['h']==c['height']
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/ottawa-2015/build')
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
 page=(build/'americas/canada/ottawa-2015'/c['slug']/'index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1]
 assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in fragments]
 l=Links();l.feed(essay);expected=[n for seg in segments for b in m['layout'].get(seg['layout_key'],[]) for n in b];
 if c['slug']=='museum': expected += [n for k in ['museum-review','museum-single'] for b in m['layout'][k] for n in b]
 assert [u.rsplit('/',1)[1] for u in l.photos]==expected;assert all('r2.dev/ottawa-2015/'+c['slug']+'/' in u for u in l.photos);all_paragraphs += [m['rendered_paragraphs'][i-1] for i in c['paragraphs']];all_photos+=expected
 if c['slug']=='museum':
  assert l.captions==[data['museum/'+n]['caption'] for n in expected]
  assert len(re.findall(r'class="?museum-pair',essay))==24
assert all_paragraphs==m['rendered_paragraphs'];assert len(all_photos)==len(set(all_photos))==101
if m.get('cover_image'):
 collection=(build/'short-trips/canada/index.html').read_text(encoding='utf-8');assert 'ottawa-2015/'+m['cover_image'] in collection
assert len(m['chapters'])==3
assert [sum(1 for p in m['photos'] if p['chapter']==c['slug']) for c in m['chapters']]==[33,19,49]
print('Verified12 verbatim source paragraphs,101 archival originals/public R2 copies;24 owner-approved museum pairs and1 hall; no final single.')

assert m['layout']['4']==[['img_5581.jpg']]
tulips=[n for i in m['chapters'][0]['paragraphs'] for b in m['layout'].get(str(i),[]) for n in b];assert tulips[-len(m['family_photo_suffix']):]==m['family_photo_suffix'];assert all(n not in tulips[:-len(m['family_photo_suffix'])] for n in m['family_photo_suffix'])

assert 'img_5405.jpg' in [n for b in m['layout']['6'] for n in b]

assert len(m['museum_comparisons'])==24
assert sum(p['status']=='owner-approved' for p in m['museum_comparisons'])==24
assert all(p['years']==[2009,2015] for p in m['museum_comparisons'])
for p in m['photos']:
 if p['chapter']=='museum':assert data['museum/'+p['site_filename']]['caption']==str(p['year'])
for p in m['museum_archive_inventory']:
 b=(archive/p['archive_name']).read_bytes();assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];assert p['drive_id'] and not p['drive_id'].startswith('local')
assert len(m['museum_archive_inventory'])==147

source_names={p['site_filename']:p['source_name'].split('.')[0] for p in m['photos'] if p['chapter']=='museum'}
expected_owner_pairs={('P7250584','DSC03879'),('P7250607','DSC03880'),('P7250540','DSC03889'),('P7250549','DSC03912'),('P7250585','DSC03937'),('P7250588','DSC03950'),('P7250604','DSC03946'),('P7250618','DSC03957'),('P7250614','DSC03964'),('P7250562','DSC03970'),('P7250566','DSC03979'),('P7250545','DSC03894'),('P7250538','DSC03897'),('P7250550','DSC03924'),('P7250554','DSC03969'),('P7250569','DSC03931'),('P7250597','DSC03938'),('P7250624','DSC03956'),('P7250557','DSC03954'),('P7250563','DSC03978'),('P7250587','DSC03935'),('P7250610','DSC03949'),('P7250611','DSC03952'),('P7250578','DSC03944')}
assert {tuple(source_names[n] for n in p['photos']) for p in m['museum_comparisons']}==expected_owner_pairs
assert not m['layout']['museum-review']

assert not m['layout']['museum-single']

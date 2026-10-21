"""Verify the prepared LA chapter without requiring pending Disneyland material."""
from pathlib import Path
from html.parser import HTMLParser
from PIL import Image
import json,html,hashlib,re,sys,zipfile,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[1];slug='los-angeles-disneyland-2007';m=json.loads((root/'media-manifests'/f'{slug}.json').read_text(encoding='utf-8'));archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
assert len(m['photos'])==len(m['r2']['photos'])==73;assert m['storage']['originals_verified'] and m['storage']['drive_sync_verified'] and m['storage']['r2_verified'];assert m['publication']['authorized']==(not m['publication']['draft'])
for source in [m['source'],m['edited_source']]:
 b=(archive/source['archive_name']).read_bytes();assert hashlib.sha256(b).hexdigest()==source['sha256'] and source['drive_id'] and not source['drive_id'].startswith('local')
assert (archive/m['source']['archive_name']).read_text(encoding='utf-8').splitlines()==m['author_paragraphs'];assert m['rendered_paragraphs'][:-1]==m['author_paragraphs'][:-1]
last=m['rendered_paragraphs'][-1];parts=[];cursor=0
for s in m['la_text_sections']:
 assert s['start']==cursor;parts.append(last[s['start']:s['end']]);cursor=s['end']
assert cursor==len(last) and ''.join(parts)==last
expected=m['rendered_paragraphs'][:-1]+parts[:1]+m.get('aquarium_author_paragraphs',[])+(parts[1:-1] if m.get('disney_intro_from_la') else parts[1:])
text=(root/m['contentDir']/'los-angeles/index.md').read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',text,re.S)]==expected;assert 'hero_image' not in text
layout=[n for blocks in m['la_layout'].values() for b in blocks for n in b];assert len(layout)==len(set(layout))==34;assert set(layout)=={o['site_filename'] for o in m['photos'] if o['chapter']=='los-angeles'}-set(m['owner_removed_site_photos'])
scenes={key:[n for block in blocks for n in block] for key,blocks in m['la_layout'].items()}
assert 'img_4283.jpg' in scenes['submarine'] and 'img_4283.jpg' not in scenes['queen-mary']
assert {'img_4194.jpg','img_4280.jpg','img_4286.jpg','img_4287.jpg','img_4292.jpg','img_4295.jpg'}<=set(scenes['queen-mary'])
assert all(names==sorted(names) for names in scenes.values())
data=json.loads((root/'data/photos'/f'{slug}.json').read_text(encoding='utf-8'))
for o,c in zip(m['photos'],m['r2']['photos']):
 b=(archive/o['archive_name']).read_bytes();assert len(b)==o['bytes'] and hashlib.sha256(b).hexdigest()==o['sha256'];assert o['drive_id'] and not o['drive_id'].startswith('local');assert Path(o['source_path']).read_bytes()==b
 b=(root/'static/r2'/c['key']).read_bytes();assert len(b)==c['bytes'] and hashlib.sha256(b).hexdigest()==c['sha256'];assert c['public_verified'] and c['original_archive_name']==o['archive_name'] and c['key']==o['r2_key']
 with Image.open(root/'static/r2'/c['key']) as im:assert im.size==(c['width'],c['height']) and max(im.size)<=2000 and im.width<=o['width'] and im.height<=o['height']
 assert data[o['chapter']+'/'+o['site_filename']]=={'w':c['width'],'h':c['height']}
assert json.loads((archive/'photo-manifest.json').read_text(encoding='utf-8'))==m
build=root/(sys.argv[1] if len(sys.argv)>1 else '.tmp/los-angeles-disneyland-2007/build');page=(build/'americas/usa'/slug/'los-angeles/index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1];norm=lambda p:re.sub(r'\s+',' ',html.unescape(p)).strip();assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in expected]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.photos=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and 'data-photo-lightbox' in a:self.photos.append(a['href'])
l=Links();l.feed(essay);assert [u.rsplit('/',1)[1] for u in l.photos]==layout;assert all('r2.dev/'+slug+'/los-angeles/' in u for u in l.photos)
lj=m['disney_lj_source'];b=(archive/lj['archive_name']).read_bytes();assert hashlib.sha256(b).hexdigest()==lj['sha256'] and b==Path(lj['path']).read_bytes()
with zipfile.ZipFile(archive/lj['archive_name']) as z:doc=E.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)];assert ps[16].startswith(lj['heading']);assert [ps[16][len(lj['heading']):]]+ps[17:20]==m['disney_lj_paragraphs']
disney_text=(root/m['contentDir']/'disneyland/index.md').read_text(encoding='utf-8');assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',disney_text,re.S)]==m['disney_rendered_paragraphs'];assert 'hero_image' not in disney_text
page=(build/'americas/usa'/slug/'disneyland/index.html').read_text(encoding='utf-8');essay=re.search(r'<div class="?essay-body"?>(.*?)</div>\s*<nav',page,re.S)[1];assert [norm(p) for p in re.findall(r'<p>(.*?)</p>',essay,re.S)]==[norm(p) for p in m['disney_rendered_paragraphs']]
l=Links();l.feed(essay);disney_order=[n for blocks in m['disney_layout_by_paragraph'].values() for b in blocks for n in b];assert len(disney_order)==len(set(disney_order))==37;assert [u.rsplit('/',1)[1] for u in l.photos]==disney_order;assert all('r2.dev/'+slug+'/disneyland/' in u for u in l.photos)
assert set(disney_order)=={o['site_filename'] for o in m['photos'] if o['chapter']=='disneyland'}
assert 'img_4306.jpg' in scenes['hollywood']
for key in ['disney_owner_source','disney_edited_source']:
 b=(archive/m[key]['archive_name']).read_bytes();assert hashlib.sha256(b).hexdigest()==m[key]['sha256']
assert (archive/m['disney_owner_source']['archive_name']).read_text(encoding='utf-8').rstrip('\n')==m['disney_owner_raw']
assert (archive/m['disney_edited_source']['archive_name']).read_text(encoding='utf-8').rstrip('\n').split('\n\n')==m['disney_rendered_paragraphs']
assert not m['disney_lj_rendered'] and len(m['disney_rendered_paragraphs'])==7
if m.get('cover_image'):
 collection=(build/'short-trips/usa/index.html').read_text(encoding='utf-8');assert slug+'/'+m['cover_image'] in collection
print('Verified both chapters: 34 LA +37 Disneyland photos;73 archival originals and R2 copies,LA owner text and seven authorized Disneyland narrative paragraphs,missing Hollywood portrait restored.')

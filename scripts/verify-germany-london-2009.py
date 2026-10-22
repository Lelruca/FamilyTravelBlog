"""Verify original text fragments, complete Drive originals, R2 and rendered chapter order."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,sys,zipfile,urllib.request
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];slug='germany-london-2009'
c=json.loads((ROOT/'scripts/trip-configs'/f'{slug}.json').read_text(encoding='utf-8'));m=json.loads((ROOT/'media-manifests'/f'{slug}.json').read_text(encoding='utf-8'));archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((archive/'photo-manifest.json').read_text(encoding='utf-8'))==m
assert m['drive_sync_verified'] and m['storage']['r2_verified']
assert sha(archive/m['source']['archive_name'])==m['source']['sha256']
with zipfile.ZipFile(archive/m['source']['archive_name']) as z:doc=ET.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};ps=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
frags=[f for ch in c['chapters'] for f in ch['fragments']]
for f in frags:assert ps[f['source_index']].strip()[f['start']:f['end']]==f['text']
indices=sorted({f['source_index'] for f in frags});assert indices==list(range(37,75))
for index in indices:
 text=ps[index].strip();start,end=c.get('source_ranges',{}).get(str(index),[0,len(text)])
 assert ''.join(f['text'] for f in sorted((x for x in frags if x['source_index']==index),key=lambda f:f['start']))==text[start:end]
data=json.loads((ROOT/'data/photos'/f'{slug}.json').read_text(encoding='utf-8'));assert all('url' not in o for o in data.values())
for o in m['photos']:assert sha(archive/o['archive_name'])==o['sha256'] and o['drive_id'] and not o['drive_id'].startswith('local')
for o in m['r2']['photos']:assert o['public_verified'] and max(o['width'],o['height'])<=2000 and sha(ROOT/'static/r2'/o['key'])==o['sha256']
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ps=[];self.p=None;self.photos=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='p':self.p=[]
  if t=='a' and 'data-photo-lightbox' in a:self.photos.append(a.get('href',''))
 def handle_data(self,s):
  if self.p is not None:self.p.append(s)
 def handle_endtag(self,t):
  if t=='p' and self.p is not None:self.ps.append(''.join(self.p));self.p=None
norm=lambda s:' '.join(s.split());count=0
base=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith('http') else 'http://127.0.0.1:1371/'
for ch in c['chapters']:
 expected=[ch['hero_image']]+[n for f in ch['fragments'] for b in f.get('photo_blocks',[]) for n in b['names']]
 rel=c['contentDir'].removeprefix('content/')+'/'+ch['slug']+'/'
 with urllib.request.urlopen(base+rel) as r:raw=r.read().decode();assert r.status==200
 p=Page();p.feed(raw);assert [u.rsplit('/',1)[-1] for u in p.photos]==expected
 assert all(norm(f['text']) in [norm(x) for x in p.ps] for f in ch['fragments'])
 build=ROOT/'.tmp/germany-london-2009/build-preview'/rel/'index.html'
 if build.exists():
  q=Page();q.feed(build.read_text(encoding='utf-8'));assert [u.rsplit('/',1)[-1] for u in q.photos]==expected
  assert all(u.startswith('https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/') for u in q.photos)
  assert all(norm(f['text']) in [norm(x) for x in q.ps] for f in ch['fragments'])
 production=ROOT/'.tmp/germany-london-2009/build-production'/rel/'index.html'
 if m['publication']['draft']:assert not production.exists(), 'Unapproved chapter appeared in production'
 elif production.exists():
  q=Page();q.feed(production.read_text(encoding='utf-8'));assert [u.rsplit('/',1)[-1] for u in q.photos]==expected
  assert all(norm(f['text']) in [norm(x) for x in q.ps] for f in ch['fragments'])
 for name in expected:
  if name==ch['hero_image']:
   dimensions=data[ch['slug']+'/'+name];assert dimensions['w']>=dimensions['h'], 'Portrait chapter cover'
 count+=len(expected)
assert count==len(m['photos'])==123
print('Germany and London 2009: 5 chapters, 123 photos, 38 source paragraphs/63 exact fragments, archive/cloud/R2 verified')

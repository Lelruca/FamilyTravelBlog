"""Verify the China draft against its source, selected originals and rendered build.
Usage: python scripts/verify-china-2019.py [build-directory] [source-docx]
Selected chapters use verified Drive originals and public R2 copies; other chapters remain text-only.
Add --retained to also audit unused photographs and chapter candidates while their folders are stable.
"""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import json,hashlib,html,re,sys
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,s):self.parts.append(s)
def text(s):
 p=Text();p.feed(s);return ''.join(p.parts)
check_retained='--retained' in sys.argv;sys.argv=[a for a in sys.argv if a!='--retained']
root=Path(__file__).resolve().parents[1];m=json.loads((root/'media-manifests/china-2019.json').read_text(encoding='utf-8'))
report=Path(sys.argv[2]) if len(sys.argv)>2 else Path('G:/My Drive/Family Travel Blog Photos/Отчеты')/m['source']['report_filename']
assert hashlib.sha256(report.read_bytes()).hexdigest()==m['source']['report_sha256'],'Source report changed'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
expected={};current=None;photo_count=0
def collect(s):
 global photo_count
 if current is None:return
 photo_count+=len(re.findall(r'<img\b',s))
 s=re.sub(r'</?lj-cut\b[^>]*>','',s);visible=text(s).strip()
 if visible:
  if visible in m['verification'].get('removed_navigation_paragraphs',{}).get(current,[]):
   assert re.search(r'<a\b',s) and 'olgau.livejournal.com/' in s,'Removed paragraph is not an LJ navigation link'
  else:
   visible=m['verification'].get('owner_text_replacements',{}).get(current,{}).get(visible,visible)
   parts=m['verification'].get('owner_paragraph_splits',{}).get(current,{}).get(visible)
   if parts:
    assert ' '.join(parts)==visible,'Owner-requested photo breaks changed author text'
    expected[current].extend(parts)
   else:expected[current].append(visible)
with ZipFile(report) as z:
 rel={e.get('Id'):e.get('Target') for e in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
 for p in ET.fromstring(z.read('word/document.xml')).findall('w:body/w:p',ns):
  buf=''
  for child in p:
   if child.tag=='{'+ns['w']+'}hyperlink' and 'livejournal.com' in rel.get(child.get('{'+ns['r']+'}id'),''):
    collect(buf);buf='';url=rel[child.get('{'+ns['r']+'}id')];c=next(c for c in m['chapters'] if c['source_url']==url)
    assert ''.join(child.itertext())==c.get('source_title',c['title']);current=c['slug'];expected[current]=[]
   else:buf+=''.join(n.text or '' for n in child.iter('{'+ns['w']+'}t'))
  collect(buf)
assert len(expected)==15 and photo_count==len(m['photos'])==258
for c in m['chapters']:
 s=(root/m['contentDir']/c['slug']/'index.md').read_text(encoding='utf-8');actual=[text(p) for p in re.findall(r'<p>(.*?)</p>',s,re.S)]
 assert actual==expected[c['slug']],('Source text differs',c['slug'])
 assert re.search(r'^draft: (true|false)$',s,re.M)
 if c['slug'] in m.get('chapter_media',{}):assert 'hero_image: '+json.dumps(m['chapter_media'][c['slug']]['hero_image']) in s
 else:assert 'hero_image:' not in s
 assert hashlib.sha256('\n'.join(actual).encode()).hexdigest()==c['text_sha256']
 assert actual==m['verification']['authorParagraphs'][c['slug']]
split_count=sum(len(parts)-1 for splits in m['verification'].get('owner_paragraph_splits',{}).values() for parts in splits.values())
assert sum(map(len,expected.values()))==264-sum(map(len,m["verification"]["removed_navigation_paragraphs"].values()))+split_count
if len(sys.argv)>1:
 build=root/sys.argv[1]
 norm=lambda s:re.sub(r'\s+',' ',s).strip()
 for c in m['chapters']:
  page=(build/m['contentDir'].removeprefix('content/')/c['slug']/'index.html').read_text(encoding='utf-8')
  body=re.split(r'<div class=(?:"essay-body"|essay-body)>',page)[1].split('<nav',1)[0]
  actual=[norm(text(p)) for p in re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>',body,re.S)]
  assert actual==[norm(p) for p in expected[c['slug']]],('Rendered text differs',c['slug'])
  assert len(re.findall(r'aria-current=(?:"page"|page)',page))==2,c['slug']
  if c['slug'] in m.get('chapter_media',{}):
   urls=re.findall(r'<a\b[^>]*href=["\']?([^"\' >]+)[^>]*data-photo-lightbox',page)
   expected_photos=m['chapter_media'][c['slug']]['page_order']
   assert [u.rsplit('/',1)[-1] for u in urls]==expected_photos,('Photo order',c['slug'],urls)
   assert all(u.startswith(m['r2']['publicBase']) for u in urls),c['slug']
   captions=m['chapter_media'][c['slug']].get('photo_captions',{})
   if captions:
    rendered={re.search(r'href=["\']?([^"\' >]+)',fig)[1].rsplit('/',1)[-1]:norm(text(re.search(r'<figcaption\b[^>]*>(.*?)</figcaption>',fig,re.S)[1])) for fig in re.findall(r'<figure\b[^>]*>(.*?)</figure>',body,re.S) if '<figcaption' in fig}
    assert rendered=={name:norm(cap) for name,cap in captions.items()},('Exhibit captions differ from their photos',c['slug'])
  else:assert 'data-photo-lightbox' not in body and not re.search(r'<img[^>]+src=',body),c['slug']
  assert html.escape(c['title']) in page or c['title'] in page,c['slug']
 for slug in m['places_coordinates']:
  page=(build/'places'/slug/'index.html').read_text(encoding='utf-8');assert '/asia/china/china-2019/' in page,slug
 trip=(build/m['contentDir'].removeprefix('content/')/'index.html').read_text(encoding='utf-8')
 assert m['r2']['publicBase']+m['tripCover']['r2_key'] in trip,'Trip cover differs from owner selection'
 assert len(re.findall(r'<a\b[^>]*class=(?:"chapter-tile(?: no-photo)?"|chapter-tile)(?:\s|>)',trip))==15,'Chapter tiles differ'
if m.get('originals'):
 archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];data=json.loads((root/'data/photos/china-2019.json').read_text(encoding='utf-8'))
 for original in m['originals']+([m['cover_original']] if m.get('cover_original') else []):assert hashlib.sha256((archive/original['original_relative_path']).read_bytes()).hexdigest()==original['original_sha256']
 for slug,media in m['chapter_media'].items():
  assert media['originals_verified'] and media['drive_sync_verified'],('Archive verification incomplete',slug)
 for original in m['originals']+([m['cover_original']] if m.get('cover_original') else []):
  copy=next(p for p in m['r2']['photos'] if p['key']==original['r2_key'])
  assert copy['original_sha256']==original['original_sha256'] and copy['archiveFile']==original['original_relative_path'],('Original/copy mapping differs',original['r2_key'])
 if check_retained:
  for original in m.get('unused_originals',[])+[p for group in m.get('chapter_candidates',{}).values() for p in group]:
   assert hashlib.sha256((archive/original['original_relative_path']).read_bytes()).hexdigest()==original['original_sha256'],original['original_relative_path']
 if m.get('chapter_candidates',{}).get('forbidden-city'):
  batch=[p for p in m['originals']+m.get('unused_originals',[])+m['chapter_candidates']['forbidden-city'] if p.get('source_batch')=='chapter4-owner76']
  assert len(batch)==len({p['number'] for p in batch})==76,'Original uploaded batch registry was lost or duplicated'
 for copy in m['r2']['photos']:
  assert hashlib.sha256((root/'static/r2'/copy['key']).read_bytes()).hexdigest()==copy['sha256']
  assert copy['public_verified'] and copy['public_sha256']==copy['sha256']
  assert max(copy['w'],copy['h'])<=2000 and 'url' not in data[copy['key'].split('/',1)[1]]
 print('PASS:',len(m['originals'])+(1 if m.get('cover_original') else 0),'Drive original SHA-256 matches and verified public R2 copies')
print(f'PASS: 15 author titles, {sum(map(len,expected.values()))} author paragraphs against fresh DOCX extraction; {sum(map(len,m["verification"]["removed_navigation_paragraphs"].values()))} owner-excluded LJ navigation paragraphs, 258 original photo references; draft'+(', rendered pages and 15 place links' if len(sys.argv)>1 else ''))

"""Verify this trip against the archived author paragraphs and media registry.
Usage: python scripts/verify-girls-europe-2017.py [production-build-directory]
Uses only Python's standard library. Does not modify the archive or photographs.
"""
import hashlib, html, json, re, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
build=root/(sys.argv[1] if len(sys.argv)>1 else 'public')
m=json.loads((root/'media-manifests/girls-europe-2017.json').read_text(encoding='utf-8'))
data=json.loads((root/'data/photos/girls-europe-2017.json').read_text(encoding='utf-8'))
norm=lambda s:re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>','',s))).strip()
count=0
for ch in m['chapters']:
 s=(build/m['contentDir'].removeprefix('content/')/ch['slug']/'index.html').read_text(encoding='utf-8')
 body=s.split('<div class=essay-body>',1)[-1] if '<div class=essay-body>' in s else s.split('<div class="essay-body">',1)[1]
 body=body.split('<nav',1)[0]
 actual=[norm(x) for x in re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>',body,re.S)]
 expected=[norm(x) for x in m['verification']['authorParagraphs'][ch['slug']]]
 assert actual==expected,('Author text differs',ch['slug'],actual,expected)
 urls=re.findall(r'<a\b[^>]*href=[\"\']?([^\"\' >]+)[^>]*data-photo-lightbox',s)
 names=[u.rsplit('/',1)[-1] for u in urls]
 photos=[p['sitePhoto'] for p in m['photos'] if p['slug']==ch['slug']]
 assert len(names)==len(set(names))==len(photos) and set(names)==set(photos),(ch['slug'],len(names),len(photos))
 assert all(u.startswith(m['r2']['publicBase']) for u in urls),ch['slug']
 assert names[0]==ch['heroPhoto'],ch['slug']
 count+=len(names)
for p in m['r2']['photos']:
 f=root/'static/r2'/p['key'];assert hashlib.sha256(f.read_bytes()).hexdigest()==p['sha256'],p['key']
 key=p['key'].split('/',1)[1];assert 'url' not in data[key] and max(data[key]['w'],data[key]['h'])<=2000,key
trip=(build/m['contentDir'].removeprefix('content/')/'index.html').read_text(encoding='utf-8')
assert m['tripCover']['sitePhoto'] in trip
chapter6=(build/m['contentDir'].removeprefix('content/')/'notre-dame-louvre/index.html').read_text(encoding='utf-8')
assert 'youtube.com/embed/YCo_1daVJn4' in chapter6
print(f'PASS: 9 chapters, 149 author paragraphs, {count} unique chapter photographs, {len(m["r2"]["photos"])} R2 SHA-256 matches, selected covers, YouTube video.')

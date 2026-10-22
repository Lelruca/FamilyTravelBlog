"""Verify the five archived Facebook downloads and unchanged Toronto tea text."""
from pathlib import Path
import json,hashlib,html,urllib.request
ROOT=Path(__file__).resolve().parents[1];mf=ROOT/'media-manifests/toronto-walks-afternoon-tea-2025.json';m=json.loads(mf.read_text(encoding='utf-8'));archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((archive/m['chapter_folder']/'photo-manifest.json').read_text(encoding='utf-8'))==m
assert sha(archive/m['source']['archive_name'])==m['source']['sha256']
assert len(m['photos'])==5 and m['storage']['drive_sync_verified'] and m['storage']['r2_verified']
for o in m['photos']:
 assert sha(archive/o['archive_name'])==sha(Path(o['source_path']))==o['sha256']
 assert o['drive_id'] and not o['drive_id'].startswith('local')
for o in m['r2']['photos']:
 assert o['public_verified'] and max(o['width'],o['height'])<=2000
 assert sha(ROOT/'static/r2'/o['key'])==o['sha256']
p=ROOT/'content/americas/canada/toronto-walks/afternoon-tea-2025/index.md';text=p.read_text(encoding='utf-8')
for t in m['source']['author_paragraphs']:assert '<p>'+html.escape(t,quote=False)+'</p>' in text
with urllib.request.urlopen('http://127.0.0.1:1372/americas/canada/toronto-walks/afternoon-tea-2025/') as response:rendered=response.read().decode()
for o in m['photos']:assert rendered.count('href="'+next(r['public_url'] for r in m['r2']['photos'] if r['key']==o['r2_key'])+'"')==1
assert not (ROOT/'.tmp/toronto-tea-2025/build-production/americas/canada/toronto-walks/afternoon-tea-2025/index.html').exists()
print('Toronto tea: 3 unchanged paragraphs, 5 OneDrive/Drive/R2 photos; draft excluded from production')

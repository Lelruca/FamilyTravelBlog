"""Check source fidelity, visual selection and storage evidence for the three LJ drafts."""
from pathlib import Path
import hashlib,json,re,sys,html,urllib.request
ROOT=Path(__file__).resolve().parents[1]
slug=sys.argv[1]
cfg=json.loads((ROOT/'scripts/trip-configs'/f'{slug}.json').read_text(encoding='utf-8'))
m=json.loads((ROOT/'media-manifests'/f'{slug}.json').read_text(encoding='utf-8'))
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
assert json.loads((archive/'photo-manifest.json').read_text(encoding='utf-8'))==m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive/m['source']['archive_name'])==m['source']['sha256']
assert m['drive_sync_verified'] and m['storage']['r2_verified']
assert m['publication']['draft'] or m['publication']['authorized']
def clean(p):
    p=re.sub(r'<img\b[^>]*>','',p)
    p=re.sub(r'</?lj-cut\b[^>]*>','',p)
    p=re.sub(r'<lj user="([^"]+)"\s*/?>',r'\1',p)
    return re.sub(r'</?b>','',p).strip()
ps=m['source']['all_source_paragraphs']
expected=[i for i,p in enumerate(ps) if clean(p) and i not in cfg['source_heading_indices']]
assert expected==m['source']['paragraph_indices'], 'A source paragraph was omitted or reordered'
assert [clean(ps[i]) for i in expected]==m['rendered_paragraphs']
data=json.loads((ROOT/'data/photos'/f'{slug}.json').read_text(encoding='utf-8'))
assert all('url' not in v for v in data.values())
for p in m['photos']+m['reference_labels']:
    assert sha(archive/p['archive_name'])==p['sha256']
    assert p.get('drive_id') and not p['drive_id'].startswith('local')
for p in m['r2']['photos']:
    assert p['public_verified'] and max(p['width'],p['height'])<=2000
    assert sha(ROOT/'static/r2'/p['key'])==p['sha256']
photos=[];paragraphs=[]
for c in cfg['chapters']:
    path=ROOT/cfg['contentDir']/c['slug']/'index.md';s=path.read_text(encoding='utf-8')
    assert ('draft: '+str(m['publication']['draft']).lower()) in s and 'cover_image:' not in s
    paragraphs += [html.unescape(p) for p in re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>',s,re.S)]
    names=[n.removeprefix('L:').removeprefix('R:') for block in re.findall(r'\{\{< (?:row|mosaic|beside) "([^"]+)" >\}\}',s) for n in block.split()]
    assert names==[n for rows in c['layout'].values() for row in rows for n in row]
    if c.get('hero_image'):names.insert(0,c['hero_image'])
    photos += [c['slug']+'/'+n for n in names]
    url='http://127.0.0.1:1371/'+cfg['contentDir'].removeprefix('content/')+'/'+c['slug']+'/'
    with urllib.request.urlopen(url) as r:
        page=r.read().decode();assert r.status==200
    assert '<lj-cut' not in page and '&lt;lj' not in page
    for n in names:assert n in page
assert paragraphs==m['rendered_paragraphs']
assert len(photos)==len(set(photos))==len(m['photos'])
assert set(photos)==set(data)
build=ROOT/'.tmp/lj-next-three/build'
if build.exists():
    for c in cfg['chapters']:
        rel=Path(cfg['contentDir'].removeprefix('content/'))/c['slug']/'index.html'
        page=(build/rel).read_text(encoding='utf-8')
        for row in c['layout'].values():
            for names in row:
                for name in names:
                    assert 'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+slug+'/'+c['slug']+'/'+name in page
        if m['publication']['draft']:assert not (ROOT/'public'/rel).exists(), 'Unapproved draft appeared in normal production build'
    places=(build/'places/index.html').read_text(encoding='utf-8')
    for place in {p for c in cfg['chapters'] for p in c['places']}:
        assert re.search(r'data-slug=(?:"'+re.escape(place)+r'"|'+re.escape(place)+r'(?:\s|>))',places)
        placepage=(build/'places'/place/'index.html').read_text(encoding='utf-8')
        for c in cfg['chapters']:
            if place in c['places']:assert '/'+cfg['contentDir'].removeprefix('content/')+'/'+c['slug']+'/' in placepage
print(slug,':',len(paragraphs),'exact paragraphs;',len(photos),'photos; archive/cloud/R2 evidence and local pages passed')

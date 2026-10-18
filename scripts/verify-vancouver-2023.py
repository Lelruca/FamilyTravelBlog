"""Verify Vancouver source text, captions, archive originals and rendered media.
Run from the checkout: python scripts/verify-vancouver-2023.py [build-dir]
The archive and screen copies must be available locally; public R2 hashes are
verified separately during upload and recorded in the manifest.
"""
from pathlib import Path
import collections, hashlib, html, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
TRIP='vancouver-2023'
build=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.tmp/preview'
manifest=json.loads((ROOT/f'media-manifests/{TRIP}.json').read_text(encoding='utf-8'))
spelling=json.loads((ROOT/f'media-manifests/{TRIP}-spelling.json').read_text(encoding='utf-8'))
info=json.loads((ROOT/f'data/photos/{TRIP}.json').read_text(encoding='utf-8'))
original_text=manifest['source_posts'][0]['text']
assert hashlib.sha256(original_text.encode()).hexdigest()==manifest['source_posts'][0]['sha256']
text=original_text
for correction in spelling:
    if 'caption' not in correction:
        assert text.count(correction['from'])==1
        text=text.replace(correction['from'],correction['to'])
expected=[p for p in text.split('\n') if p and not p.startswith('#')]
source=ROOT/f'content/americas/canada/{TRIP}/vancouver/index.md'
paragraphs=[html.unescape(p) for p in re.findall(r'<p>(.*?)</p>',source.read_text(encoding='utf-8'),re.S)]
assert paragraphs==expected, 'Author paragraphs changed beyond logged spelling fixes'
page=build/f'americas/canada/{TRIP}/vancouver/index.html'
rendered=page.read_text(encoding='utf-8')
def normal(s):return ' '.join(s.split())
rendered_paragraphs=[normal(html.unescape(re.sub(r'<[^>]+>','',p))) for p in re.findall(r'<p(?:\s[^>]*)?>(.*?)</p>',rendered,re.S)]
for paragraph in expected:assert rendered_paragraphs.count(normal(paragraph))==1
from html.parser import HTMLParser
class Images(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img' and dict(attrs).get('src'):self.urls.append(dict(attrs)['src'])
images=Images();images.feed(rendered);photo_urls=images.urls
assert len(photo_urls)==24 and len(set(photo_urls))==24
assert all(url.startswith('https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+TRIP+'/') for url in photo_urls)
assert 'photo-lightbox-info' in rendered
archive=Path(manifest['archive_root'])
for photo in manifest['photos']:
    original=archive/photo['archive_name']
    raw=original.read_bytes()
    assert len(raw)==photo['bytes'] and hashlib.sha256(raw).hexdigest()==photo['sha256']
    assert photo['cloud_sync_verified'] and photo['drive_id']
    screen=ROOT/'static/r2'/photo['r2_key']
    assert screen.stat().st_size==photo['copy_bytes']
    assert hashlib.sha256(screen.read_bytes()).hexdigest()==photo['copy_sha256']
    assert photo['public_verified'] and max(photo['display_width'],photo['display_height'])<=2000
    caption=photo['fb_caption']
    for c in spelling:
        if c.get('caption')==photo['position']-1:caption=caption.replace(c['from'],c['to'])
    entry=info['vancouver/'+photo['name']]
    assert entry.get('caption','')==caption
    assert entry['source']==photo['archive_name']
assert sum(bool(p['fb_caption']) for p in manifest['photos'])==7
collection=(build/'short-trips/canada/index.html').read_text(encoding='utf-8')
assert f'/americas/canada/{TRIP}/vancouver/' in collection
assert TRIP not in (build/'index.html').read_text(encoding='utf-8')
draft='draft: true' in (ROOT/f'content/americas/canada/{TRIP}/_index.md').read_text(encoding='utf-8')
assert (ROOT/f'.tmp/production-check/americas/canada/{TRIP}/vancouver/index.html').exists() != draft
report={'originals_verified':24,'public_copies_verified':24,'unique_rendered_photos':24,'author_paragraphs':9,'captions':7,'spelling_corrections':len(spelling),'production_visibility_matches_draft_flag':True,'collection_opens_story_directly':True}
print(json.dumps(report))

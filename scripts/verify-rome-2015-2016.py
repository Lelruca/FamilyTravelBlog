"""Verify the built Rome trip against its author-text and media manifests."""
import hashlib
import json
import os
import re
import html
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'media-manifests/rome-2015-2016.json').read_text(encoding='utf-8-sig'))
build = root / os.environ.get('TRAVEL_VERIFY_BUILD_DIR', 'public')
trip = build / 'europe/italy/rome-2015-2016'

class Story(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.in_p = False
        self.paras = []
        self.images = []
        self.current = ''
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'essay-body' in attrs.get('class', '').split():
                self.depth = 1
        if self.depth and tag == 'p':
            self.in_p = True
            self.current = ''
        if tag == 'img' and '/rome-2015-2016/' in attrs.get('src', ''):
            self.images.append(attrs['src'])
    def handle_endtag(self, tag):
        if tag == 'p' and self.in_p:
            self.paras.append(self.current)
            self.in_p = False
        if tag == 'div' and self.depth:
            self.depth -= 1
    def handle_data(self, data):
        if self.in_p:
            self.current += data

assert all(manifest[k] for k in ('archive_verified', 'drive_sync_verified', 'r2_verified'))
known = {p['url'] for p in manifest['r2']['photos']}
assert len(known) == 402
seen = Counter()
total = 0
for chapter in manifest['chapters']:
    parser = Story()
    parser.feed((trip / chapter['slug'] / 'index.html').read_text(encoding='utf-8'))
    assert len(parser.paras) == chapter['paragraph_count'], chapter['slug']
    source = (root / 'content/europe/italy/rome-2015-2016' / chapter['slug'] / 'index.md').read_text(encoding='utf-8-sig')
    authored = [html.unescape(re.sub('<[^>]*>', '', p)) for p in re.findall(r'<p>(.*?)</p>', source, re.S)]
    assert hashlib.sha256('\n'.join(authored).encode()).hexdigest() == chapter['text_sha256'], chapter['slug']
    # Hugo's HTML minifier collapses whitespace; source text must still match exactly.
    assert [re.sub(r'\s+', ' ', p).strip() for p in parser.paras] == [re.sub(r'\s+', ' ', p).strip() for p in authored], chapter['slug']
    assert len(parser.images) == len(set(parser.images)), chapter['slug']
    assert set(parser.images) <= known, chapter['slug']
    seen.update(parser.images)
    total += len(parser.paras)
assert set(seen) == known
assert sum(seen.values()) == 403  # Conclusion repeats the group photograph.
data = json.loads((root / 'data/photos/rome-2015-2016.json').read_text(encoding='utf-8'))
assert all('url' not in photo for photo in data.values())
print(f'Verified 12 chapters, {total} unchanged author paragraphs, 402 unique R2 photographs.')

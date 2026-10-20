"""Check the original text, archive, display copies and rendered note."""
from pathlib import Path
from PIL import Image
import hashlib, html, json, re, sys, zipfile, xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
m = json.loads((root / 'media-manifests/detroit-windsor-2016.json').read_text(encoding='utf-8'))
archive = Path('G:/My Drive/Family Travel Blog Photos') / m['archive_root']
source = Path(m['source']['path'])
assert hashlib.sha256(source.read_bytes()).hexdigest() == m['source']['sha256']
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(source) as z:
    doc = ET.fromstring(z.read('word/document.xml'))
    source_paras = [''.join(t.text or '' for t in p.findall('.//w:t', ns))
                    for p in doc.findall('.//w:body/w:p', ns)]
author = [p for p in source_paras[1:] if p and not p.lstrip().startswith(('<img ', '<lj-cut', '</lj-cut'))]
assert author == m['author_paragraphs']
note = (root / m['contentDir'] / 'story/index.md').read_text(encoding='utf-8')
expected_text = author.copy()
for correction in m['spelling_corrections']:
    i = correction['paragraph'] - 1
    assert expected_text[i].count(correction['from']) == 1
    expected_text[i] = expected_text[i].replace(correction['from'], correction['to'])
assert expected_text == m['rendered_paragraphs']
assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>', note, re.S)] == expected_text
assert 'title: "Детройт и музей Форда"' in note
assert 'windsor-ontario' not in note.split('---', 2)[1]
trip_source = (root / m['contentDir'] / '_index.md').read_text(encoding='utf-8')
assert 'short_trip: "usa"' in trip_source and '  - canada' not in trip_source
assert m['storage']['originals_verified'] and m['storage']['drive_sync_verified'] and m['storage']['r2_verified']
expected = [m['layout']['hero']] + [n for i in range(1, 9) for n in m['layout'].get('after' + str(i), [])]
assert len(expected) == len(set(expected)) == len(m['originals']) == 23
data = json.loads((root / 'data/photos/detroit-windsor-2016.json').read_text(encoding='utf-8'))
for o, copy in zip(m['originals'], m['r2']['photos']):
    assert o['r2_key'] == copy['key']
    original = archive / o['original_relative_path']
    b = original.read_bytes()
    assert len(b) == o['original_bytes'] and hashlib.sha256(b).hexdigest() == o['original_sha256']
    assert o['drive_file_id'] and not o['drive_file_id'].startswith('local')
    b = (root / 'static/r2' / copy['key']).read_bytes()
    assert len(b) == copy['bytes'] and hashlib.sha256(b).hexdigest() == copy['sha256']
    with Image.open(root / 'static/r2' / copy['key']) as im:
        assert im.size == (copy['w'], copy['h']) and max(im.size) <= 2000
    assert copy['w'] <= o['display_oriented_width'] and copy['h'] <= o['display_oriented_height']
    assert copy['public_verified']
    assert 'url' not in data['story/' + o['site_filename']]
hero = data['story/' + m['layout']['hero']]
assert hero['w'] > hero['h']
build = root / (sys.argv[1] if len(sys.argv) > 1 else '.tmp/detroit-2016/build')
page = (build / 'americas/usa/detroit-windsor-2016/story/index.html').read_text(encoding='utf-8')
essay = re.search(r'<div class=\"?essay-body\"?>(.*?)</div>\s*<nav', page, re.S)
assert essay, 'Rendered essay body missing'
rendered = re.findall(r'<p>(.*?)</p>', essay.group(1), re.S)
normalize = lambda p: re.sub(r'\s+', ' ', html.unescape(p)).strip()
assert [normalize(p) for p in rendered] == [normalize(p) for p in expected_text]
links = re.findall(r'<a\b[^>]*href=[\"\']?([^\s\"\'>]+)[^>]*data-photo-lightbox', page)
assert [x.rsplit('/', 1)[-1] for x in links] == expected
assert all('r2.dev/detroit-windsor-2016/' in x for x in links)
trip = (build / 'americas/usa/detroit-windsor-2016/index.html').read_text(encoding='utf-8')
assert 'detroit-windsor-2016/story/' in trip
for slug in ['detroit', 'dearborn']:
    assert 'detroit-windsor-2016/story/' in (build / 'places' / slug / 'index.html').read_text(encoding='utf-8')
collection = (build / 'short-trips/usa/index.html').read_text(encoding='utf-8')
assert 'Детройт и музей Форда' in collection and 'detroit-windsor-2016/story/' in collection
assert 'r2.dev/detroit-windsor-2016/story/' + m['cover_image'] in collection
print('Verified 8 paragraphs with only 3 approved typos, 23 photos, USA outings collection and 2 geographic tags')

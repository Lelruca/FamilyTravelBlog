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
expected_text = author.copy()
for correction in m['spelling_corrections']:
    i = correction['paragraph'] - 1
    assert expected_text[i].count(correction['from']) == 1
    expected_text[i] = expected_text[i].replace(correction['from'], correction['to'])
assert expected_text == m['rendered_paragraphs']
assert len(m['chapters']) == 2 and m['chapter_covers'] is False
assert m['cover_image'] == '20160806_133129.jpg'
assert m['storage']['originals_verified'] and m['storage']['drive_sync_verified'] and m['storage']['r2_verified']
data = json.loads((root / 'data/photos/detroit-windsor-2016.json').read_text(encoding='utf-8'))
build = root / (sys.argv[1] if len(sys.argv) > 1 else '.tmp/detroit-2016/build')
normalize = lambda p: re.sub(r'\s+', ' ', html.unescape(p)).strip()
seen_photos, seen_paragraphs = [], []
for slug, chapter in m['chapters'].items():
    note = (root / m['contentDir'] / slug / 'index.md').read_text(encoding='utf-8')
    front = note.split('---', 2)[1]
    assert 'hero_image' not in front and 'windsor-ontario' not in front
    paragraphs = []
    for i in chapter['paragraph_numbers']:
        text = expected_text[i - 1]
        split = m.get('paragraph_splits', {}).get(str(i))
        if split:
            at = text.index(split['before'])
            paragraphs.extend([text[:at], text[at:]])
        else:
            paragraphs.append(text)
    assert [html.unescape(p) for p in re.findall(r'<p>(.*?)</p>', note, re.S)] == paragraphs
    seen_paragraphs.extend(chapter['paragraph_numbers'])
    photos = [n for i in chapter['paragraph_numbers'] for n in chapter['layout'].get('after' + str(i), [])]
    seen_photos.extend(photos)
    page = (build / 'americas/usa/detroit-windsor-2016' / slug / 'index.html').read_text(encoding='utf-8')
    assert 'class="essay-cover"' not in page and 'class=essay-cover ' not in page
    essay = re.search(r'<div class=\"?essay-body\"?>(.*?)</div>\s*<nav', page, re.S)
    assert essay
    rendered = re.findall(r'<p>(.*?)</p>', essay.group(1), re.S)
    assert [normalize(p) for p in rendered] == [normalize(p) for p in paragraphs]
    links = re.findall(r'<a\b[^>]*href=[\"\']?([^\s\"\'>]+)[^>]*data-photo-lightbox', page)
    assert [x.rsplit('/', 1)[-1] for x in links] == [n.rsplit('/', 1)[-1] for n in photos]
    assert all('r2.dev/detroit-windsor-2016/' in x for x in links)
    captions = re.findall(r'<figcaption[^>]*>(.*?)</figcaption>', essay.group(1), re.S)
    assert not captions
    labels = re.findall(r'<p class="museum-label">(.*?)</p>', essay.group(1), re.S)
    assert not labels
    assert 'essay-authorcap{display:none}' not in page
    overlay_captions = re.findall(r'data-caption=[\"\'](.*?)[\"\']', essay.group(1), re.S)
    assert [normalize(p) for p in overlay_captions] == [normalize(m['owner_requested_captions'][n]) for n in photos if n in m['owner_requested_captions']]
assert seen_paragraphs == list(range(1, 9))
assert len(seen_photos) == len(set(seen_photos)) == 53
assert len(m['originals']) == 52
assert {n.rsplit('/', 1)[-1] for n in seen_photos} == {o['site_filename'] for o in m['originals']} | {m['cover_image']}
assert len(m['r2']['photos']) == len(m['originals']) + 1 == 53
for o, copy in zip(m['originals'] + [m['cover_original']], m['r2']['photos']):
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
    key = o['r2_key'].split('/', 1)[1]
    assert copy['public_verified'] and 'url' not in data[key]
    assert data[key].get('caption') == m.get('owner_requested_captions', {}).get(o['site_filename'])
assert len(m['deleted_exact_duplicates']) == 4
assert all(not (archive / d['original_relative_path']).exists() for d in m['deleted_exact_duplicates'])
assert not {o['site_filename'] for o in m['removed_by_owner']} & set(seen_photos)
assert {'20160702_114009.jpg', '20160702_114107.jpg'} <= set(seen_photos)
trip_source = (root / m['contentDir'] / '_index.md').read_text(encoding='utf-8')
assert 'short_trip: "usa"' in trip_source and '  - canada' not in trip_source
for place, chapter in [('dearborn', 'story'), ('detroit', 'detroit')]:
    assert 'detroit-windsor-2016/' + chapter + '/' in (build / 'places' / place / 'index.html').read_text(encoding='utf-8')
collection = (build / 'short-trips/usa/index.html').read_text(encoding='utf-8')
assert 'Детройт и музей Форда' in collection and 'detroit-windsor-2016/story/' in collection
assert 'r2.dev/' + m['cover_r2_key'] in collection
assert m['chapters']['detroit']['layout']['after5'][0] == '20160702_170452.jpg'
assert '20160702_162720.jpg' not in seen_photos
for reference in m['reference_images']:
    assert hashlib.sha256((archive / reference['original_relative_path']).read_bytes()).hexdigest() == reference['original_sha256']
assert 'cover/20160806_133129.jpg' in m['chapters']['detroit']['layout']['after7']
assert len(m['reference_images']) == 3
print('Verified two chapters, 8 source paragraphs with 3 approved typos and authorized split, 53 photos including shared cover panorama, requested captions over photos, 3 reference labels excluded, both Edison images and wedding placement')

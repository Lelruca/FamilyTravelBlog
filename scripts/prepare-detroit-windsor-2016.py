"""Rebuild this note and its display copies from verified Drive originals.
Run with the bundled Python runtime; upload and verify public R2 bytes separately.
"""
from pathlib import Path
from PIL import Image, ImageOps
import hashlib, html, json, sys

root = Path(__file__).resolve().parents[1]
manifest = root / 'media-manifests/detroit-windsor-2016.json'
m = json.loads(manifest.read_text(encoding='utf-8'))
assert m['storage']['originals_verified'] and m['storage']['drive_sync_verified']
archive = Path('G:/My Drive/Family Travel Blog Photos') / m['archive_root']
if "--content-only" not in sys.argv:
    copies, data = [], {}
    for o in m['originals'] + ([m['cover_original']] if m.get('cover_original') else []):
        original = archive / o['original_relative_path']
        assert hashlib.sha256(original.read_bytes()).hexdigest() == o['original_sha256']
        target = root / 'static/r2' / o['r2_key']
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(original) as raw:
            im = ImageOps.exif_transpose(raw).convert('RGB')
            im.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            im.save(target, quality=85, optimize=True)
            w, h = im.size
        b = target.read_bytes()
        copies.append({'key': o['r2_key'], 'original_relative_path': o['original_relative_path'],
                       'original_sha256': o['original_sha256'], 'w': w, 'h': h,
                       'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
                       'recipe': {'exif_transpose': True, 'long_side_max': 2000,
                                  'no_upscale': True, 'jpeg_quality': 85, 'optimize': True}})
        data[o['r2_key'].split('/', 1)[1]] = {'w': w, 'h': h, 'source': o['original_relative_path']}
    (root / 'data/photos/detroit-windsor-2016.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    m['retired_r2'] = m.get('retired_r2', []) + [p for p in m['r2']['photos'] if p['key'] not in {c['key'] for c in copies}]
    m['r2'] = {'status': 'prepared-awaiting-public-verification', 'photos': copies}
datafile = root / 'data/photos/detroit-windsor-2016.json'
data = json.loads(datafile.read_text(encoding='utf-8'))
active_keys = {o['r2_key'].split('/', 1)[1] for o in m['originals'] + [m['cover_original']]}
data = {key: value for key, value in data.items() if key in active_keys}
for o in m['originals']:
    key = 'story/' + o['site_filename']
    data[key]['source'] = o['original_relative_path']
    caption = m.get('owner_requested_captions', {}).get(o['site_filename'])
    if caption:
        data[key]['caption'] = caption
    else:
        data[key].pop('caption', None)
datafile.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
base = 'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/detroit-windsor-2016/story/'
cover_url = 'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/' + m['cover_r2_key']
trip = root / m['contentDir']
title = json.dumps(m['display_title'], ensure_ascii=False)
trip.mkdir(parents=True, exist_ok=True)
trip.joinpath('_index.md').write_text(f'''---
title: {title}
type: "trips"
draft: true
date: 2016-07-02
trip_year: 2016
trip_start: "2016-07"
trip_end: "2016-07"
short_trip: "usa"
continent: "Северная Америка"
country: "США"
geo_countries:
  - usa
cover_image: "{cover_url}"
cover_title: {title}
---
''', encoding='utf-8')
for slug, chapter in m['chapters'].items():
    body = []
    for i in chapter['paragraph_numbers']:
        text = m['rendered_paragraphs'][i - 1]
        photos = chapter['layout'].get('after' + str(i), []).copy()
        split = m.get('paragraph_splits', {}).get(str(i))
        if split:
            at = text.index(split['before'])
            body.append('<p>' + html.escape(text[:at], quote=False) + '</p>')
            for photo in split['photos_between']:
                name = photo if slug == 'story' else 'story/' + photo
                body.append('{{< row "' + name + '" >}}')
                photos.remove(photo)
            body.append('<p>' + html.escape(text[at:], quote=False) + '</p>')
        else:
            body.append('<p>' + html.escape(text, quote=False) + '</p>')
        groups = []
        while photos:
            if photos[0] in chapter.get('standalone_photos', []):
                take = 1
            else:
                next_single = next((n for n, photo in enumerate(photos) if photo in chapter.get('standalone_photos', [])), len(photos))
                take = min(2 if len(photos) == 4 else 3, next_single, len(photos))
            groups.append(photos[:take]); photos = photos[take:]
        for group in groups:
            names = [n if slug == 'story' or '/' in n else 'story/' + n for n in group]
            body.append('{{< row "' + ' '.join(names) + '" >}}')
    folder = trip / slug
    folder.mkdir(exist_ok=True)
    front = {'title': chapter['title'], 'draft': True, 'date': '2016-07-02',
             'weight': chapter['weight'], 'chapter_kind': 'Заметка', 'layout': 'photo-story',
             'city': chapter['city'], 'places': chapter['places'], 'auto_gallery': False}
    lines = []
    for key, value in front.items():
        if isinstance(value, list):
            lines.append(key + ':'); lines.extend('  - ' + v for v in value)
        else:
            lines.append(key + ': ' + json.dumps(value, ensure_ascii=False))
    folder.joinpath('index.md').write_text('---\n' + '\n'.join(lines) + '\n---\n\n' + '\n\n'.join(body) + '\n', encoding='utf-8')
out = json.dumps(m, indent=2, ensure_ascii=False) + '\n'
manifest.write_text(out, encoding='utf-8')
(archive / 'photo-manifest.json').write_text(out, encoding='utf-8')
print('Prepared two chapters, no chapter covers, only three recorded typo corrections')

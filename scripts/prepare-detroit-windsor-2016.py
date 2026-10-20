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
    for o in m['originals']:
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
        data['story/' + o['site_filename']] = {'w': w, 'h': h, 'source': o['original_relative_path']}
    (root / 'data/photos/detroit-windsor-2016.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    m['r2'] = {'status': 'prepared-awaiting-public-verification', 'photos': copies}
base = 'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/detroit-windsor-2016/story/'
trip = root / m['contentDir']
(trip / 'story').mkdir(parents=True, exist_ok=True)
title = json.dumps(m.get('display_title', m['source']['title']), ensure_ascii=False)
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
cover_image: "{base}{m.get('cover_image', '20160702_120227.jpg')}"
cover_title: {title}
---
''', encoding='utf-8')
body = []
for i, p in enumerate(m.get('rendered_paragraphs', m['author_paragraphs']), 1):
    body.append('<p>' + html.escape(p, quote=False) + '</p>')
    photos = m['layout'].get('after' + str(i), [])
    groups = [photos] if len(photos) <= 4 else [photos[:3], photos[3:6], photos[6:]]
    for group in groups:
        if group:
            body.append('{{< row "' + ' '.join(group) + '" >}}')
trip.joinpath('story/index.md').write_text(f'''---
title: {title}
draft: true
date: 2016-07-02
weight: 1
chapter_kind: "Заметка"
layout: "photo-story"
city: "Детройт, Дирборн"
places:
  - detroit
  - dearborn
hero_image: "{m['layout']['hero']}"
auto_gallery: false
---

''' + '\n\n'.join(body) + '\n', encoding='utf-8')
out = json.dumps(m, indent=2, ensure_ascii=False) + '\n'
manifest.write_text(out, encoding='utf-8')
(archive / 'photo-manifest.json').write_text(out, encoding='utf-8')
print('Prepared note with', len(m['author_paragraphs']), 'paragraphs; only recorded typos corrected')

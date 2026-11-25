"""«Барселона, ноябрь 2026» (collection «Вокруг Барселоны»): the owner's photos on Drive -> archive -> R2 -> page.

The second part of the November 2026 holiday (after «Наша Польша»). Codex made the empty draft; the owner put her
photos into the trip folder on Drive and gave the text (her Facebook post, pasted in the chat on 24 Nov 2026,
kept as Drive «Источники/Барселона - ноябрь 2026.md»). One chapter, `story`.

Stages (python -I -X utf8 scripts/prepare-barcelona-november-2026.py <stage>):
  inventory  list the photos of the Drive folder (checksums, sizes, capture time) + a contact sheet (changes nothing)
  archive    move them into «01 - Барселона» as NN_<name> in page order, save the text, write both manifests
  -- then: node scripts/check-drive-sync.cjs "Europe/2026 - Барселона - ноябрь" --write
  display    screen copies (2000 px, EXIF rotation, no EXIF/GPS; HEVC video -> H.264) + data/photos
  -- then: node scripts/upload-to-r2.cjs barcelona-november-2026
  verify-r2  every public copy byte for byte
  render     the page
  verify-site <built site>
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, html, json, re, shutil, subprocess, sys, urllib.request

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path('G:/My Drive/Family Travel Blog Photos/Europe/2026 - Барселона - ноябрь')
FOLDER = '01 - Барселона'
WORK = ROOT / '.tmp/barcelona-november-2026'
MANIFEST = ROOT / 'media-manifests/barcelona-november-2026.json'
TRIP = ROOT / 'content/europe/spain/barcelona-november-2026'
SLUG, CHAPTER = 'barcelona-november-2026', 'story'
BASE = 'https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'
VIDEO_RECIPE = ['-map', '0:v:0', '-map', '0:a:0', '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', '-map_metadata', '-1']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def site_name(n): return re.sub(r'\s+', '_', n).replace('.jpeg', '.jpg')


def inventory():
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    WORK.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in ARCHIVE.iterdir() if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.mp4'))
    def one(p):
        r = dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p), kind='video' if p.suffix.lower() == '.mp4' else 'photo')
        thumb = None
        if r['kind'] == 'photo':
            with Image.open(p) as raw:
                im = ImageOps.exif_transpose(raw)
                r.update(w=im.width, h=im.height, date=(raw.getexif().get_ifd(34665).get(36867) or raw.getexif().get(306)))
                im.thumbnail((288, 218)); thumb = im.convert('RGB').copy()
        m = re.search(r'(2026)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)', p.name)
        r['sort'] = ('{}-{}-{}T{}:{}:{}'.format(*m.groups())) if m else (r.get('date') or p.name).replace(':', '-', 2).replace(' ', 'T')
        if p.name.startswith('PXL_') and m: r['sort'] = r['sort'][:11] + f"{(int(r['sort'][11:13]) + 1) % 24:02d}" + r['sort'][13:]  # Pixel names in UTC+0
        return r, thumb
    with ThreadPoolExecutor(6) as ex: pairs = sorted(ex.map(one, files), key=lambda t: t[0]['sort'])
    for i, (r, _) in enumerate(pairs, 1): r['index'] = i
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    for start in range(0, len(pairs), 20):
        sheet = Image.new('RGB', (1500, 1080), '#fafafa'); d = ImageDraw.Draw(sheet)
        for k, (r, t) in enumerate(pairs[start:start + 20]):
            x, y = (k % 5) * 300, (k // 5) * 270
            if t: sheet.paste(t, (x + (300 - t.width) // 2, y))
            d.text((x + 5, y + 222), f"{r['index']:02d} {r['name'][:34]}", fill='black', font=font)
            d.text((x + 5, y + 244), f"{r.get('w', '')}x{r.get('h', '')} {r['kind']} {r['sort'][5:16]}", fill='black', font=font)
        sheet.save(WORK / f'contact-{start // 20 + 1}.jpg', quality=88)
    (WORK / 'inventory.json').write_text(json.dumps([r for r, _ in pairs], ensure_ascii=False, indent=1), encoding='utf-8')
    for r, _ in pairs: print(f"{r['index']:2d} {r['kind'][0]} {('V' if r.get('h', 0) > r.get('w', 0) else 'H') if r['kind'] == 'photo' else '-'} {r['sort'][5:16]} {r['name']}")


# The owner's text (her Facebook post «Вторую часть отпуска мы провели в Барселоне…», pasted in the chat), verbatim.
TITLE_SOURCE = 'Барселона - ноябрь 2026'
TEXT = [
 'Вторую часть отпуска мы провели в Барселоне. Вот где ВСЕГДА прекрасная погода! Мы приехали в +20! Настроение соответствующее. Дети разбежались на работу и учёбу, а мы — гулять, гулять, на море и по городу. ',
 'На пл. Каталунии был остров революционеров — Наташа присылала фото. Продержался около недели. Потом ночью нагнали войска и за 3 часа полностью вычистили. Короче, дело только в том, чтобы принять решение. А теперь там всё уже красиво и спокойно, как обычно.',
 'Рестораны на улице, музыка. Нельзя сказать, что у испанцев какая-то «высокая кухня», но тапасы весьма приятные под сангрию :)',
 'Потом у нас были «родительские дни» — гуляли и вместе, и парами, то так, то эдак. Занимались Митиным гардеробом. Он как-то очень «ожил» в Барселоне (мы его все допрашивали, почему так — или повзрослел, или как-то ему тут проще). Он себе наставил всяких AI-агентов, которые ему всё находят: и всякие встречи, и компании. Активно бегает везде, нетворкинг на 1-м месте, ещё интервью снимает и в университете. Не очень понятно, почему вдруг так резко «заработало». Но понятно, что родителям всё мало. Нашлись поводы «промывать мозги». ',
 'Потом мы занимались бытом: папа что-то подкрасил, подремонтировал, я разобрала с Митей завалы... ',
 'Наташа больше на работе была, но и с ней мы общались, планировали будущее и просто устраивали семейные обеды. ',
 'Главное, что они живут дружно, поддерживают друг друга. Наташа, правда, больше о брате заботится, помнит, что ему надо делать, Митя зато ходит за продуктами и готовит. ',
 'Прекрасно провели время!',
]
# Photos: numbers of the inventory (capture-time order). After paragraph N: ('r', row) · ('x', row with labels) · ('v', video).
HERO = 25  # the owner's choice, 25 Nov 2026: «Вот это фото главное» — the four of them in the square (was the beach, 41)
LAYOUT = {
 1: [('r', [1, 2]), ('r', [4, 5]), ('r', [41]), ('r', [43, 42, 44])],
 2: [('r', [48, 6])],
 3: [('r', [7, 8])],
 4: [('r', [23, 24, 22]), ('x', [26, 27, 20]), ('r', [29, 30]), ('v', 28), ('r', [31, 32]), ('r', [33, 34, 35]),
     ('r', [36, 37, 38]), ('r', [39, 40, 45]), ('r', [49, 10]), ('r', [9, 13]), ('r', [11, 12])],
 5: [('r', [3, 17]), ('x', [16, 18, 19])],
 6: [('r', [46, 47])],
 7: [('r', [14, 15])],
 8: [('r', [21])],
}
TRIP_COVER = dict(photo=25, position='center 60%')  # the same main photo on the collection card (was the Gamba, 21)
# Captions: verbatim from the owner's Facebook post (personal profile, album pcb.40990267303890776, read 24 Nov 2026)
FB_POST = 'pcb.40990267303890776'
CAPTIONS = {
 20: ('40990128357238124', '«Район — для тех, кто в нём живёт, а не для тех, кто его посещает»'),
 16: ('40990128667238263', 'Митя мне кажется единственный ребенок был, который не интересовался ЛЕГО в детстве. А тут вдруг в ALDI увидел конструктор с моделью "старого комьютера" и очень захотел 🙂'),
 18: ('40990128443904832', 'Мы с ним дружно собирали'),
}
CAPTION_FIXES = [('комьютера', 'компьютера')]  # obvious typo only, display
ATTRACTIONS = ['barcelona--ploshchad-katalonii']
DRAFT = 'false'  # published with the owner's «Публикуй», 25 Nov 2026


def order():
    seq = [HERO] + [x for bl in LAYOUT.values() for k, it in bl for x in (it if isinstance(it, list) else [it])]
    inv = load(WORK / 'inventory.json')
    assert len(seq) == len(set(seq)) and set(seq) == {r['index'] for r in inv}, sorted({r['index'] for r in inv} ^ set(seq))
    o = {r['index']: r for r in inv}
    for bl in LAYOUT.values():
        for k, it in bl:
            if k in ('r', 'x'):
                ori = ['V' if o[i]['h'] > o[i]['w'] else 'H' for i in it]
                assert not (len(it) == 1 and ori[0] == 'V') and not (len(it) == 3 and ori.count('H') > 1) and len(it) <= 3, it
    return seq, o


def save_manifest(m):
    out = json.dumps(m, ensure_ascii=False, indent=2) + '\n'
    MANIFEST.write_text(out, encoding='utf-8'); (ARCHIVE / 'photo-manifest.json').write_text(out, encoding='utf-8')


def archive():
    assert not MANIFEST.exists()
    seq, o = order()
    folder = ARCHIVE / FOLDER; folder.mkdir(exist_ok=True)
    (ARCHIVE / 'Источники').mkdir(exist_ok=True)
    src = ARCHIVE / 'Источники' / f'{TITLE_SOURCE}.md'
    src.write_text(f'# {TITLE_SOURCE}\n\n' + '\n\n'.join(TEXT) + '\n', encoding='utf-8')
    photos = []
    for pos, i in enumerate(seq, 1):
        r = o[i]
        old, new = ARCHIVE / r['name'], folder / f"{pos:02d}_{r['name']}"
        assert sha(old) == r['sha256'] and not new.exists()
        old.rename(new); assert sha(new) == r['sha256']
        sn = site_name(r['name'])
        photos.append(dict(chapter=CHAPTER, inventory_index=i, archive_name=f"{FOLDER}/{new.name}", original_filename=r['name'],
                           original_bytes=r['bytes'], original_sha256=r['sha256'], kind=r['kind'], w=r.get('w'), h=r.get('h'),
                           date_original=r.get('date'), used=True, position=pos, site_filename=sn, r2_key=f'{SLUG}/{CHAPTER}/{sn}'))
    m = dict(schema_version=1, trip=SLUG, title='Барселона, ноябрь 2026', contentDir='content/europe/spain/barcelona-november-2026',
             archive_root='Europe/2026 - Барселона - ноябрь', created=datetime.now(timezone.utc).isoformat(),
             history=['Codex made the empty draft in the collection «Вокруг Барселоны» (24 Nov 2026).',
                      'The owner put her photos into the Drive folder and pasted her Facebook text; Claude archived and built the page (24 Nov 2026).'],
             sources=[dict(archive_name=f'Источники/{TITLE_SOURCE}.md', sha256=sha(src), paragraphs=TEXT, origin='owner, chat 24 Nov 2026 (= her Facebook post)')],
             photos=photos, originals_verified=True, drive_sync_verified=False, r2_verified=False)
    save_manifest(m)
    print(f'Archived {len(photos)} originals into «{FOLDER}».')


def display():
    from PIL import Image, ImageOps
    m = load(MANIFEST); assert m['drive_sync_verified'], 'check-drive-sync --write first'
    by_index = {p['inventory_index']: p for p in m['photos']}
    def make(p):
        src, dest = ARCHIVE / p['archive_name'], ROOT / 'static/r2' / p['r2_key']
        assert sha(src) == p['original_sha256']; dest.parent.mkdir(parents=True, exist_ok=True)
        if p['kind'] == 'video':
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), *VIDEO_RECIPE, str(dest)], check=True)
            w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(dest)],
                                           capture_output=True, text=True, check=True).stdout.strip().split(','))
            recipe = dict(tool='ffmpeg', args=VIDEO_RECIPE)
        else:
            with Image.open(src) as raw:
                icc = raw.info.get('icc_profile'); im = ImageOps.exif_transpose(raw).convert('RGB')
                im.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                im.save(dest, 'JPEG', quality=88, optimize=True, progressive=True, **({'icc_profile': icc} if icc else {})); w, h = im.size
            recipe = dict(tool='Pillow', exif_transpose=True, long_side_max=2000, no_upscale=True, jpeg_quality=88, exif_dropped=True)
        return p, dict(key=p['r2_key'], kind=p['kind'], archive_name=p['archive_name'], original_sha256=p['original_sha256'],
                       bytes=dest.stat().st_size, sha256=sha(dest), w=w, h=h, recipe=recipe)
    with ThreadPoolExecutor(6) as ex: res = list(ex.map(make, m['photos']))
    data = {}
    for p, c in res:
        if p['kind'] == 'photo':
            e = dict(w=c['w'], h=c['h'], source=p['archive_name'])
            if p['inventory_index'] in CAPTIONS:
                fid, text = CAPTIONS[p['inventory_index']]
                p.update(caption_source=text, caption_from=f'facebook photo {fid} ({FB_POST})')
                for a, b in CAPTION_FIXES: text = text.replace(a, b)
                e['caption'] = text
            data[f"{CHAPTER}/{p['site_filename']}"] = e
    m['caption_fixes'] = [list(f) for f in CAPTION_FIXES]
    (ROOT / f'data/photos/{SLUG}.json').write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    m['r2'] = dict(bucket='family-travel-photos', base=BASE, copies=sorted((c for _, c in res), key=lambda c: c['key']), verified=None)
    save_manifest(m)
    print(f"{len(res)} copies, {sum(c['bytes'] for _, c in res) / 1e6:.0f} MB.")


def verify_r2():
    m = load(MANIFEST)
    def get(c):
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + urllib.request.quote(c['key']), headers={'User-Agent': 'family-blog-check'}), timeout=60) as r:
                body, ct = r.read(), r.headers.get('Content-Type', '')
            return c, hashlib.sha256(body).hexdigest() == c['sha256'] and ct == ('video/mp4' if c['kind'] == 'video' else 'image/jpeg')
        except Exception: return c, False
    with ThreadPoolExecutor(12) as ex: res = list(ex.map(get, m['r2']['copies']))
    now = datetime.now(timezone.utc).isoformat()
    for c, ok in res: c['public_verified'] = now if ok else False
    m['r2_verified'] = all(ok for _, ok in res); m['r2']['verified'] = now if m['r2_verified'] else False
    save_manifest(m); print(f"{sum(ok for _, ok in res)}/{len(res)} public copies match byte for byte.")


def render():
    m = load(MANIFEST)
    by_index = {p['inventory_index']: p for p in m['photos']}
    cover = by_index[TRIP_COVER['photo']]
    (TRIP / '_index.md').write_text(f'''---
type: "trips"
title: "2026 — Барселона, ноябрь"
continent: "Европа"
country: "Испания"
geo_countries:
  - spain
short_trip: "barcelona"
trip_year: 2026
trip_start: "2026-11"
trip_end: "2026-11"
date: "2026-11-19"
cover_where: "Испания · Барселона"
cover_title: "Барселона"
cover_subtitle: "Родительский визит"
cover_when: "Ноябрь 2026"
cover_who: "Сережа, Леля, Наташа и Митя"
cover_image: "{BASE}{cover['r2_key']}"
cover_position: "{TRIP_COVER['position']}"
draft: {DRAFT}
---
''', encoding='utf-8')
    body = []
    for n, p in enumerate(TEXT, 1):
        body.append('<p>' + html.escape(p, quote=False) + '</p>')
        for k, it in LAYOUT.get(n, []):
            if k == 'v':
                body.append('{{< travel-video "' + BASE + by_index[it]['r2_key'] + '" >}}')
            else:
                body.append('{{< ' + ('exhibit-row' if k == 'x' else 'row') + ' "' + ' '.join(by_index[i]['site_filename'] for i in it) + '" >}}')
    (TRIP / CHAPTER).mkdir(exist_ok=True)
    (TRIP / CHAPTER / 'index.md').write_text(f'''---
title: "Родительский визит"
chapter_kind: "part"
layout: "photo-story"
weight: 10
city: "Барселона"
places:
  - barcelona
hero_image: "{by_index[HERO]['site_filename']}"
date: "2026-11-19"
auto_gallery: false
draft: {DRAFT}
attractions: {json.dumps(ATTRACTIONS)}
---
''' + '\n\n'.join(body) + '\n', encoding='utf-8')
    print('Rendered the trip and its chapter.')


def relayout():
    """After a change of HERO/LAYOUT: renumber the originals on Drive to the new page order (NN_), update the manifest
    and the sources in data/photos. Copies on R2 keep their names."""
    m = load(MANIFEST)
    seq, o = order()
    by_index = {p['inventory_index']: p for p in m['photos']}
    renames = []
    for pos, i in enumerate(seq, 1):
        p = by_index[i]; p['position'] = pos
        new = f"{FOLDER}/{pos:02d}_{p['original_filename']}"
        if new != p['archive_name']: renames.append((p, new))
    for p, new in renames:
        src = ARCHIVE / p['archive_name']; assert sha(src) == p['original_sha256'], src
        src.rename(src.with_name('tmp_' + src.name))
    for p, new in renames:
        tmp = (ARCHIVE / p['archive_name']); tmp = tmp.with_name('tmp_' + tmp.name)
        dest = ARCHIVE / new; assert not dest.exists(), dest
        tmp.rename(dest); assert sha(dest) == p['original_sha256'], dest
        for c in m['r2']['copies']:
            if c['archive_name'] == p['archive_name']: c['archive_name'] = new
        p['archive_name'] = new
    data_file = ROOT / f'data/photos/{SLUG}.json'; data = load(data_file)
    for p in m['photos']:
        k = f"{CHAPTER}/{p['site_filename']}"
        if k in data: data[k]['source'] = p['archive_name']
    data_file.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    m['drive_sync_verified'] = False
    save_manifest(m)
    print(f'Renamed {len(renames)} originals; run check-drive-sync --write next.')


def verify_site(site):
    m = load(MANIFEST)
    page = (Path(site) / f'europe/spain/{SLUG}/{CHAPTER}/index.html').read_text(encoding='utf-8')
    header = page[page.index('class="essay-header"'):page.index('class="essay-body"')]
    body = page[page.index('class="essay-body"'):page.index('class="essay-navigation"')]
    got = [html.unescape(re.sub(r'<[^>]+>', '', p)) for p in re.findall(r'<p>([\s\S]*?)</p>', body)]
    links = re.findall(r'href="([^"]+\.jpg)"[^>]*data-photo-lightbox', header + body)
    videos = re.findall(r'<source src="([^"]+\.mp4)"', body)
    exp = sorted(BASE + p['r2_key'] for p in m['photos'] if p['kind'] == 'photo')
    problems = []
    if got != TEXT: problems.append(f'paragraphs differ ({len(got)} vs {len(TEXT)})')
    if sorted(links) != exp: problems.append(f'photos differ: {len(links)} shown, {len(set(links))} distinct, {len(exp)} expected')
    if sorted(videos) != sorted(BASE + p['r2_key'] for p in m['photos'] if p['kind'] == 'video'): problems.append('videos differ')
    data = load(ROOT / f'data/photos/{SLUG}.json')
    for k, v in data.items():
        if v.get('caption') and v['caption'] not in html.unescape(page): problems.append(f'caption missing: {k}')
    trip = (Path(site) / f'europe/spain/{SLUG}/index.html').read_text(encoding='utf-8')
    print('\n'.join(problems) if problems else f'OK: {len(TEXT)} paragraphs verbatim, {len(links)} photos + {len(videos)} video each once from R2, captions on the page.')


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'inventory'
    if stage == 'verify-site': verify_site(sys.argv[2])
    else: globals()[stage.replace('-', '_')]()

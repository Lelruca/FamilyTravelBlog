"""Check the text draft against private DOCX snapshots and the built HTML.

Run with the bundled Python, optionally --build-dir .tmp/europe-2019-build.
The private source files are ignored by Git; their Drive URLs and SHA-256 are
recorded in the trip manifest. This check never changes a source or a chapter.
"""
from pathlib import Path
from html.parser import HTMLParser
import argparse, collections, hashlib, html, json, re, zipfile
import xml.etree.ElementTree as ET
from urllib.parse import unquote

class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.tag=None;self.parts=[];self.photos=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag=='a' and 'data-photo-lightbox' in attributes:self.photos.append(attributes.get('href'))
        if tag in ('p','h2') and self.tag is None:
            self.tag=tag;self.parts=[]
    def handle_data(self,data):
        if self.tag:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag==self.tag:
            self.rows.append(''.join(self.parts));self.tag=None

parser=argparse.ArgumentParser()
parser.add_argument('--build-dir')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'media-manifests/europe-friends-2019.json').read_text(encoding='utf-8'))
trip=root/m['contentDir']
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
sources={}
for key,s in m['sources'].items():
    p=root/s['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'],f'Source changed: {key}'
    if p.suffix=='.json':
        sources[key]=json.loads(p.read_text(encoding='utf8'))['paragraphs']
        continue
    with zipfile.ZipFile(p) as z:x=ET.fromstring(z.read('word/document.xml'))
    sources[key]=[''.join(t.text or '' for t in para.findall('.//w:t',ns)) for para in x.findall('.//w:body//w:p',ns)]
for r in m['text_records']:
    raw=sources[r['source']][r['source_paragraph']]
    clean=re.sub(r'<img\b[^>]*>','',raw)
    clean=re.sub(r'</?lj-cut\b[^>]*>','',clean)
    assert clean==r['text'],f"Changed author text: {r['chapter']} / {r['source']} / {r['source_paragraph']}"
    assert hashlib.sha256(clean.encode()).hexdigest()==r['sha256']
    if 'rendered_text' in r:
        corrected=clean
        for change in r.get('grammar_corrections',[])+r.get('formatting_corrections',[]):
            assert change['before'] in corrected
            corrected=corrected.replace(change['before'],change['after'])
        assert corrected==r['rendered_text']

distribution=m.get('preparation_distribution')
if distribution:
    preparation=[r for r in m['text_records'] if r['section']=='preparation']
    assert len(preparation)==distribution['added_fragments']
    used_preparation={(r['chapter'],r['source'],r['source_paragraph']) for r in preparation}
    private={(r['source'],r['source_paragraph']) for r in distribution['private_contacts_omitted']}
    for slug,ranges in distribution['ranges'].items():
        for key,start,end in ranges:
            for i in range(start,end):
                if sources[key][i].strip() and (key,i) not in private:
                    assert (slug,key,i) in used_preparation,f'Plan fragment missing: {slug}/{key}/{i}'

days=[];chapter_counts={}
for c in m['chapters']:
    f=trip/c['slug']/'index.md';s=f.read_text(encoding='utf-8')
    assert ('draft: false' if m.get('publication',{}).get('enabled') else 'draft: true') in s and 'layout: "photo-story"' in s
    if c.get('draft_plan_removed'):
        assert '<!-- BEGIN TEMPORARY DAY PLAN:' not in s and 'Источники:' not in s
        body=s.split('---',2)[2]
    else:
        assert '<!-- BEGIN TEMPORARY DAY PLAN:' in s
        body=s.split('<!-- END TEMPORARY DAY PLAN -->',1)[1]
    actual=[(tag,html.unescape(text)) for tag,text in re.findall(r'<(p|h2)>(.*?)</\1>',body,re.S)]
    # Body order groups main report first, then messages, then notes.
    records=[r for sec in ['report','messages','notes','preparation'] for r in m['text_records'] if r['chapter']==c['slug'] and r['section']==sec]
    expected=[('h2' if r['kind']=='heading' else 'p',r.get('rendered_text',r['text'])) for r in records]
    assert actual==expected,f'Paragraph order or text differs: {c["slug"]}'
    assert len(actual)==c['author_paragraphs']
    assert not re.search(r'<img|files\.1drv\.com|lh3\.googleusercontent|drive\.google\.com/thumbnail',s)
    assert (Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']/c['archive_folder']).is_dir()
    days.extend(c['days']);chapter_counts[c['slug']]=len(actual)
    if args.build_dir:
        built=root/args.build_dir/m['contentDir'].removeprefix('content/')/c['slug']/'index.html'
        rendered=built.read_text(encoding='utf-8')
        # Ignore whitespace collapsed by Hugo's production HTML minifier.
        def norm(t):return re.sub(r'\s+',' ',html.unescape(t)).strip()
        parsed=Paragraphs();parsed.feed(rendered)
        built_counts=collections.Counter(norm(t) for t in parsed.rows)
        for tag,text in expected:
            n=norm(text);assert built_counts[n]>0,f'Author paragraph missing in rendered page: {c["slug"]}: {text[:60]}'
            built_counts[n]-=1
        assert not re.search(r'<img[^>]+(?:files\.1drv\.com|drive\.google\.com)',rendered)
        media=m.get('chapter_media',{}).get(c['slug'])
        if media and media.get('r2_verified'):
            shared=media.get('shared_photo_sources',{})
            hero=next(p for p in m['r2']['photos'] if p['key']=='europe-friends-2019/'+shared.get(media['hero_image'],c['slug'])+'/'+media['hero_image'])
            assert hero['w']>hero['h'],'Chapter cover must be horizontal.'
            photos=[media['hero_image']]
            for group in media['groups']:
                photos.extend(group['photos'] if isinstance(group,dict) else group)
            assert len(photos)==len(set(photos)),f'Duplicate visible photo: {c["slug"]}'
            expected_urls=['https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/europe-friends-2019/'+shared.get(name,c['slug'])+'/'+name for name in photos]
            assert [unquote(url) for url in parsed.photos]==expected_urls,f'Hero/gallery R2 URL order differs: {c["slug"]}'
            for name in photos:
                copy=next(p for p in m['r2']['photos'] if p['key']=='europe-friends-2019/'+shared.get(name,c['slug'])+'/'+name)
                assert copy['public_verified'] and copy.get('selected_on_site',True)
assert sorted(days)==list(range(1,21)) and len(days)==20
assert next(c for c in m['chapters'] if c['slug']=='paris')['days']==[1,2,3]
assert m['dates']['friends_departure']=='2019-08-27'
plan=next(c['plan'] for c in m['chapters'] if c['slug']=='munich-rothenburg')
assert plan.index('Ленбаххаус')<plan.index('музей национал-социализма')<plan.index('проводы')
assert all('Pinakothek' not in r['chapter'] for r in m['text_records'])
if m['storage']['r2_verified']:
    assert all(c.get('r2_verified') and c.get('drive_sync_verified') for c in m['chapter_media'].values())
    assert m['storage']['originals_verified'] and m['storage']['drive_photo_sync_verified']
else:
    assert 'draft' in m['stage']
for p in m['originals']:
    original=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']/p['original_relative_path']
    assert hashlib.sha256(original.read_bytes()).hexdigest()==p['original_sha256']
    assert original.stat().st_size==p['original_bytes']
    assert m['chapter_media'][p['chapter']]['drive_sync_verified']
    assert not p['drive_file_id'].startswith('local')
for p in m['r2']['photos']:
    assert hashlib.sha256((root/'static/r2'/p['key']).read_bytes()).hexdigest()==p['sha256']
    assert p['w']<=2000 and p['h']<=2000
    original=next(o for o in m['originals'] if o['r2_key']==p['key'])
    assert p['w']<=original['display_w'] and p['h']<=original['display_h'],'Small source was enlarged.'
    assert m['chapter_media'][p['chapter']]['r2_verified']
    assert p['public_verified'] and p['public_mime']=='image/jpeg'
if m.get('chapter_media',{}).get('paris',{}).get('r2_verified'):
    paris=(trip/'paris/index.md').read_text(encoding='utf8')
    assert 'Источники:' not in paris and 'подтверждены итоговыми оценками' not in paris
    names=re.findall(r'\{\{< row "([^"]+)" >\}\}',paris)
    names=[n for row in names for n in row.split()]
    hero=m['chapter_media']['paris']['hero_image']
    assert hero not in names and len(names)==23 and len(set(names+[hero]))==24
    paris_intro=next(r['text'] for r in m['text_records'] if r['source']=='owner-paris-revised')
    assert paris.index(html.escape(paris_intro,quote=False))<paris.index('{{< row')
    if args.build_dir:
        page=root/args.build_dir/m['contentDir'].removeprefix('content/')/'paris/index.html'
        built=page.read_text(encoding='utf8')
        gallery=Paragraphs();gallery.feed(built);urls=gallery.photos
        assert len(urls)==24
        expected=['https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/europe-friends-2019/paris/'+n for n in [hero]+names]
        assert urls==expected,'Rendered gallery/hero must use checked R2 URLs in visible order.'
assert ('draft: false' if m.get('publication',{}).get('enabled') else 'draft: true') in (trip/'_index.md').read_text(encoding='utf-8')
if m.get('cover'):
    cover=m['cover']
    assert cover['url'] in (trip/'_index.md').read_text(encoding='utf8')
    copy=next(p for p in m['r2']['photos'] if p['key']=='europe-friends-2019/'+cover['chapter']+'/'+cover['site_filename'])
    assert copy['public_verified']
# Every nonempty Viber paragraph is retained apart from visual separators.
used={r['source_paragraph'] for r in m['text_records'] if r['source']=='viber'}
for i,p in enumerate(sources['viber']):
    if p.strip() and not re.fullmatch(r'[\s‐–—-]+',p):assert i in used,f'Viber paragraph missing: {i}'
# DOCX chapter headings represented by the exact title or retained in the body.
used_report={r['source_paragraph'] for r in m['text_records'] if r['source']=='report'}
used_report.update(r['source_paragraph'] for r in m.get('superseded_text_records',[]) if r['source']=='report')
for i,p in enumerate(sources['report']):
    p=re.sub(r'<img\b[^>]*>|</?lj-cut\b[^>]*>','',p)
    if not p.strip() or i in used_report:continue
    assert i in [0,33],f'DOCX text missing: {i}'
    if i==0:assert p in (trip/'_index.md').read_text(encoding='utf-8')
assert (root/'Отчеты/europe-friends-2019/final-plan.csv').exists()
for resource in m.get('chapter_resources',[]):
    archived=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']/resource['original_relative_path']
    local=trip/resource['chapter']/resource['filename']
    assert hashlib.sha256(archived.read_bytes()).hexdigest()==resource['original_sha256']
    assert hashlib.sha256(local.read_bytes()).hexdigest()==resource['resource_sha256']
    assert resource['drive_sync_verified'] and not resource['drive_file_id'].startswith('local')
    chapter=(trip/resource['chapter']/'index.md').read_text(encoding='utf8')
    assert 'hero_image: "route-map.png"' in chapter
    assert '{{< row "route-map.png" >}}' not in chapter
    if args.build_dir:
        built_resource=root/args.build_dir/m['contentDir'].removeprefix('content/')/resource['chapter']/resource['filename']
        assert hashlib.sha256(built_resource.read_bytes()).hexdigest()==resource['resource_sha256']
print(f'PASS: {len(m["chapters"])} chapters; all 20 days; {len(m["text_records"])} verbatim source records; {len(m["historical_photo_references"])} archived historical photo references.')
print('Photo stages checked; whole trip correctly remains an incomplete draft.')

"""Validate saved audit evidence. Passing is not a proof of editorial completeness.
Use --require-complete to reject all unread or unreconciled material explicitly.
Run with the bundled Python runtime from the repository root.
"""
from pathlib import Path
import hashlib,json,re,sys,zipfile,xml.etree.ElementTree as ET

root=Path.cwd()
load=lambda p:json.loads(Path(p).read_text('utf-8'))
inventory=load('reviews/source-audit/inventory.json')
attractions=load('data/attractions.json')
types=load('data/attraction_types.json')
actual={p.as_posix() for p in Path('content').rglob('index.md') if not p.as_posix().startswith('content/places/')}
assert actual=={c['file'] for c in inventory['chapters']},'Chapter inventory changed'
for c in inventory['chapters']:
    raw=Path(c['file']).read_text('utf-8')
    assert hashlib.sha256(raw.encode()).hexdigest()==c['source_sha256_lf'],f"Changed material: {c['file']}"
for key,a in attractions.items():
    assert a.get('types') and a.get('search_terms'),f'{key}: missing semantic classification'
    assert all(t in types for t in a['types']),f'{key}: unknown type'
    assert Path(f"content/places/{a['parent']}/_index.md").exists(),f'{key}: missing geographic parent'
reports=list(Path('reviews/source-audit/trips').glob('*.json'))
read=set();photos=set();objects=0
for report_file in reports:
    r=load(report_file)
    for original in r['photographs'].get('additional_originals',[]):
        assert hashlib.sha256(Path(original['source']).read_bytes()).hexdigest()==original['sha256'],f"Additional original changed: {original['source']}"
    source=Path(r['source']['path'])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==r['source']['sha256'],f'{report_file}: source changed'
    if r['source'].get('kind')=='photograph_manifest':
        manifest=load(source)
        photo_data=load(f"data/photos/{manifest['trip']}.json")
        archive=Path('G:/My Drive/Family Travel Blog Photos')/manifest['archive_root']
        photo_keys=set(photo_data)
        for original in manifest['photos']:
            assert hashlib.sha256((archive/original['archive_name']).read_bytes()).hexdigest()==original['sha256'],'Original photograph changed'
        paragraphs=[]
    elif r['source'].get('kind')=='facebook_profile_json':
        posts=json.loads(source.read_text('utf-8'))
        post=posts[r['source']['record_index']]
        text='\n'.join(d.get('post','') for d in post.get('data',[]))
        paragraphs=text.encode('latin1').decode('utf-8').split('\n')
    else:
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with zipfile.ZipFile(source) as z:
            doc=ET.fromstring(z.read('word/document.xml'))
        paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in doc.findall('.//w:body/w:p',ns)]
    trip_files={c['file'] for c in inventory['chapters'] if c['trip_path']==r['trip_path']}
    assert trip_files=={c['file'] for c in r['chapters']},f'{report_file}: missing trip chapters'
    for c in r['chapters']:
        if c['text_status']=='read':read.add(c['file'])
        if r['photographs'].get('status')=='reviewed':photos.add(c['file'])
        front=Path(c['file']).read_text('utf-8').split('---',2)[1]
        for o in c['objects']:
            objects+=1
            assert o.get('decision') and o.get('event') and o.get('evidence'),f'{report_file}: unexplained object'
            for e in o['evidence']:
                if 'photo' in e and r['source'].get('kind')=='photograph_manifest':
                    assert e['photo'] in photo_keys,f"Unknown source photograph: {e['photo']}"
                if 'source_paragraph' in e:
                    assert e['quote'] in paragraphs[e['source_paragraph']],f"{report_file}: unsupported quotation {o['label']}"
                if 'source_attachment_path' in e:
                    assert r['source'].get('kind')=='facebook_profile_json','Attachment quote requires a Facebook source'
                    caption=post
                    for part in e['source_attachment_path'].split('.'):
                        caption=caption[int(part)] if isinstance(caption,list) else caption[part]
                    caption=caption.encode('latin1').decode('utf-8')
                    assert e['quote'] in caption,f"{report_file}: unsupported image caption {o['label']}"
            target=o.get('target')
            if isinstance(target,dict):
                if 'attraction' in target:
                    aid=target['attraction'];assert aid in attractions,f'Unknown attraction {aid}'
                    if o['decision'] in ('retain','add','revise_existing_definition','covered_by_museum'):
                        assert f'"{aid}"' in front,f'{aid}: missing chapter relation'
                if 'places' in target:assert Path(f"content/places/{target['places']}/_index.md").exists()
for c in inventory['chapters']:
    assert (c['text_status']=='read')==(c['file'] in read),f"Inventory reading status differs: {c['file']}"
    assert (c['photos_status']=='reviewed')==(c['file'] in photos),f"Inventory photograph status differs: {c['file']}"
print(f'{len(reports)} trip reports; {len(read)}/{len(actual)} chapters read; {len(photos)}/{len(actual)} chapters with photos reviewed; {objects} object decisions with evidence.')
print('Audit IN PROGRESS. Valid evidence and valid structure do not prove absence of omissions.')
if '--require-complete' in sys.argv:
    assert all(c['text_status']=='read' and c['photos_status']=='reviewed' and c['reconciliation_status']=='complete' for c in inventory['chapters']),'Unread or unreconciled materials remain'
    assert inventory.get('cross_worktree_scope')=='reconciled','Other active draft sources have not been reconciled'
    gaps_path=Path('reviews/source-audit/source-gaps.json')
    if gaps_path.exists():
        assert all(g.get('data_status')=='reconciled' for g in load(gaps_path)['items']),'Additional original-source trips remain unreconciled'

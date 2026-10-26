"""Validate saved audit evidence. Passing is not a proof of editorial completeness.
Use --require-complete to reject all unread or unreconciled material explicitly.
Run with the bundled Python runtime from the repository root.
"""
from pathlib import Path
import hashlib,html,json,re,sys,zipfile,xml.etree.ElementTree as ET
from functools import cache

root=Path.cwd()
@cache
def load(p):
    return json.loads(Path(p).read_text('utf-8'))

@cache
def source_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
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
reports=list(Path('reviews/source-audit/trips').glob('*.json'))+list(Path('reviews/source-audit/supplemental').glob('*.json'))
read=set();photos=set();objects=0
for report_file in reports:
    r=load(report_file)
    valid_photo_keys={p['key'] for p in r['photographs'].get('additional_originals',[])}
    manifest_path=r['photographs'].get('manifest')
    if manifest_path:
        image_data_path=Path('data/photos')/Path(manifest_path).name
        if image_data_path.exists():valid_photo_keys.update(load(image_data_path))
    for original in r['photographs'].get('additional_originals',[]):
        assert source_hash(original['source'])==original['sha256'],f"Additional original changed: {original['source']}"
    source=Path(r['source']['path'])
    assert source_hash(source)==r['source']['sha256'],f'{report_file}: source changed'
    for extra in r['source'].get('additional_files',[]):
        assert source_hash(extra['path'])==extra['sha256'],f"Additional author source changed: {extra['path']}"
    if r['source'].get('kind')=='photograph_manifest':
        manifest=load(source)
        photo_data=load(f"data/photos/{manifest['trip']}.json")
        archive=Path('G:/My Drive/Family Travel Blog Photos')/manifest['archive_root']
        photo_keys=set(photo_data)
        for original in manifest['photos']:
            assert hashlib.sha256((archive/original['archive_name']).read_bytes()).hexdigest()==original['sha256'],'Original photograph changed'
        paragraphs=[]
    elif r['source'].get('kind')=='owner_text':
        paragraphs=source.read_text('utf-8').splitlines()
    elif r['source'].get('kind')=='facebook_html':
        paragraphs=[html.unescape(re.sub(r'<[^>]+>','',source.read_text('utf-8').replace('<br />','\n')))]
    elif r['source'].get('kind')=='facebook_profile_json':
        posts=load(source)
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
    for c in r['chapters']+r.get('sections',[]):
        if c.get('file'):
            if c['text_status']=='read':read.add(c['file'])
            if c.get('photos_status',r['photographs'].get('status'))=='reviewed':photos.add(c['file'])
            if c.get('photos_status',r['photographs'].get('status'))=='not_required_for_text_decisions':
                assert all(not o.get('target') or any('quote' in e for e in o['evidence']) for o in c['objects']),'Photo-only target requires a scoped photographic review'
            if c.get('photos_status')=='scoped_story_block_review':
                blocks=r['photographs'].get('scoped_blocks',[])
                assert any(b.get('chapter')==Path(c['file']).parent.name and b.get('reviewed') and b.get('scope') for b in blocks),'Scoped photo review needs an explicit story block and limits'
            front=Path(c['file']).read_text('utf-8').split('---',2)[1]
        else:
            front=None
        for o in c['objects']:
            objects+=1
            assert o.get('decision') and o.get('event') and o.get('evidence'),f'{report_file}: unexplained object'
            for e in o['evidence']:
                evidence_paragraphs=paragraphs
                if 'source_record_index' in e:
                    assert r['source'].get('kind')=='facebook_profile_json','Post selection requires a Facebook source'
                    evidence_post=posts[e['source_record_index']]
                    evidence_text='\n'.join(d.get('post','') for d in evidence_post.get('data',[]))
                    evidence_paragraphs=evidence_text.encode('latin1').decode('utf-8').split('\n')
                if 'source_file' in e:
                    extra_path=Path(e['source_file'])
                    assert source_hash(extra_path)==e['source_sha256'],'Author text source changed'
                    if extra_path.suffix.lower()=='.docx':
                        with zipfile.ZipFile(extra_path) as z:
                            extra_doc=ET.fromstring(z.read('word/document.xml'))
                        extra_ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                        extra_paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',extra_ns)) for p in extra_doc.findall('.//w:body/w:p',extra_ns)]
                        extra_text=extra_paragraphs[e['source_paragraph_extra']] if 'source_paragraph_extra' in e else '\n'.join(extra_paragraphs)
                    elif extra_path.suffix.lower()=='.json':
                        extra_data=load(extra_path)
                        if 'source_json_path' in e:
                            for part in e['source_json_path'].split('.'):
                                extra_data=extra_data[int(part)] if isinstance(extra_data,list) else extra_data[part]
                            assert isinstance(extra_data,str),'JSON evidence must address one explicit text field'
                            extra_text=extra_data
                        else:
                            assert isinstance(extra_data.get('paragraphs'),list) and all(isinstance(p,str) for p in extra_data['paragraphs']),'Additional JSON source must contain explicit author paragraphs'
                            extra_text='\n'.join(extra_data['paragraphs'])
                    else:
                        extra_text=extra_path.read_text('utf-8')
                    assert e['quote'].replace('\r\n','\n') in extra_text,f"Unsupported additional-source quote: {o['label']}"
                if 'photo' in e:
                    assert e['photo'] in valid_photo_keys,f"Unresolvable photo evidence: {report_file}: {e['photo']}"
                if 'photo' in e and r['source'].get('kind')=='photograph_manifest':
                    assert e['photo'] in photo_keys,f"Unknown source photograph: {e['photo']}"
                if 'source_paragraph' in e:
                    assert e['quote'] in evidence_paragraphs[e['source_paragraph']],f"{report_file}: unsupported quotation {o['label']}"
                if 'source_attachment_path' in e:
                    assert r['source'].get('kind')=='facebook_profile_json','Attachment quote requires a Facebook source'
                    caption=evidence_post if 'source_record_index' in e else post
                    for part in e['source_attachment_path'].split('.'):
                        caption=caption[int(part)] if isinstance(caption,list) else caption[part]
                    caption=caption.encode('latin1').decode('utf-8')
                    assert e['quote'] in caption,f"{report_file}: unsupported image caption {o['label']}"
            target=o.get('target')
            if isinstance(target,dict):
                if 'attraction' in target:
                    aid=target['attraction'];assert aid in attractions,f'Unknown attraction {aid}'
                    if front is not None and o['decision'] in ('retain','add','revise_existing_definition','covered_by_museum'):
                        assert f'"{aid}"' in front,f'{aid}: missing chapter relation'
                if 'places' in target:assert Path(f"content/places/{target['places']}/_index.md").exists()
for c in inventory['chapters']:
    assert (c['text_status']=='read')==(c['file'] in read),f"Inventory reading status differs: {c['file']}"
    assert (c['photos_status']=='reviewed')==(c['file'] in photos),f"Inventory photograph status differs: {c['file']}"
print(f'{len(reports)} source reports; {len(read)}/{len(actual)} chapters read; {len(photos)}/{len(actual)} chapters with photos reviewed; {objects} object decisions with evidence.')
print('Audit IN PROGRESS. Valid evidence and valid structure do not prove absence of omissions.')
if '--require-complete' in sys.argv:
    assert all(c['text_status']=='read' and c['photos_status'] in ('reviewed','not_required_for_text_decisions','scoped_story_block_review') and c['reconciliation_status']=='complete' for c in inventory['chapters']),'Unread or unreconciled materials remain'
    assert inventory.get('cross_worktree_scope')=='reconciled','Other active draft sources have not been reconciled'
    gaps_path=Path('reviews/source-audit/source-gaps.json')
    if gaps_path.exists():
        assert all(g.get('data_status')=='reconciled' for g in load(gaps_path)['items']),'Additional original-source trips remain unreconciled'

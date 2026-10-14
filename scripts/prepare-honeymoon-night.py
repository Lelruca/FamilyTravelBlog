"""Render reviewed chapter plans from SHA-256/cloud-verified archive originals.

Original names and files are retained. Screen copies are reproducible; R2 upload
and public-byte checks are independent stages. Supports cross-chapter sources.
"""
from pathlib import Path
from PIL import Image,ImageOps
import json,re,hashlib,sys,shutil
root=Path.cwd();trip='honeymoon-2017';mf=root/f'media-manifests/{trip}.json';m=json.loads(mf.read_text(encoding='utf-8-sig'));assert m['archive_verified'] and m['drive_sync_verified']
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];plan=json.loads((root/f'media-manifests/{trip}-layout.json').read_text(encoding='utf-8-sig'));inventory={slug:sorted([p for p in m['album_originals'] if p['chapter']==slug],key=lambda p:p['original_relative_path']) for slug in {p['chapter'] for p in m['album_originals']}}
data=json.loads((root/f'data/photos/{trip}.json').read_text(encoding='utf-8-sig'));photos={p['key']:p for p in m['r2']['photos']};originals={p['original_relative_path']:p for p in m['album_originals']};made=0
old_videos={p['key']:p for p in m['r2'].get('videos',[])};videos=[]
for asset in m.get('ancillary_assets',[]):
    if not asset.get('selected'):continue
    src=archive/asset['original_relative_path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==asset['original_sha256'];key=f"{trip}/{asset['chapter']}/{asset['original_filename']}";dest=root/'static/r2'/key;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copyfile(src,dest)
    sha=hashlib.sha256(dest.read_bytes()).hexdigest();assert sha==asset['original_sha256'];item=dict(key=key,archiveFile=asset['original_relative_path'],bytes=dest.stat().st_size,sha256=sha,content_type='video/mp4',width=1080,height=1920,recipe='Byte-identical copy of owner video; original retained')
    if old_videos.get(key,{}).get('sha256')==sha:
        for field in ['public_verified','public_checked_at']:
            if field in old_videos[key]:item[field]=old_videos[key][field]
    videos.append(item)
def resolve(slug,ref):
    ref=str(ref);source=slug
    if ':' in ref:source,ref=ref.split(':',1)
    if source=='existing':
        matches=[p for p in m['album_originals'] if p['original_filename']==ref and (p['chapter']==slug or any(u['chapter']==slug for u in p.get('site_usage',[])))]
        assert matches,(slug,ref,'archive original missing')
        return matches[0]
    if not ref.isdigit():return next(p for p in m['album_originals'] if p['chapter']==source and p['original_filename']==ref)
    indexed=inventory[source][int(ref)-1];return originals[indexed['original_relative_path']]
def photo(slug,ref):
    global made
    p=resolve(slug,ref);name=re.sub(r'\s+','_',p['original_filename']);key=f'{trip}/{slug}/{name}';src=archive/p['original_relative_path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==p['original_sha256'];out=root/'static/r2'/key;out.parent.mkdir(parents=True,exist_ok=True)
    if key not in photos:
        with Image.open(src) as original:
            im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((2000,2000),Image.Resampling.LANCZOS);im.save(out,format='JPEG',quality=85,optimize=True);w,h=im.size
        photos[key]=dict(key=key,archiveFile=p['original_relative_path'],original_sha256=p['original_sha256'],w=w,h=h,bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),recipe=dict(tool='Pillow',exif_transpose=True,long_side_max=2000,no_upscale=True,jpeg_quality=85,optimize=True));made+=1
    info=photos[key];data[f'{slug}/{name}']=dict(w=info['w'],h=info['h'],source=p['original_relative_path']);p.setdefault('site_usage',[])
    caption=plan.get(slug,{}).get('captions',{}).get(name)
    if caption:data[f'{slug}/{name}'].update(caption=caption['text'],caption_position=caption['placement'])
    usage=dict(chapter=slug,site_filename=name,r2_key=key)
    if usage not in p['site_usage']:p['site_usage'].append(usage)
    return name
# Complete the previously identified Gijon material supplied in Oviedo folder.
slug='praia-das-catedrais-gijon';f=root/f'content/europe/portugal/{trip}/{slug}/index.md';source=f.read_text(encoding='utf-8-sig');paras=re.findall(r'<p>.*?</p>',source,re.S);body=source.split('---\n',2)[2];groups={}
for n,part in enumerate(re.split(r'<p>.*?</p>',body,flags=re.S)[1:],1):
    groups[str(n)]=['r '+' '.join('existing:'+name for name in match.split()) for match in re.findall(r'{{< row "([^"]+)" >}}',part)]
if slug not in plan:
    already={name for names in re.findall(r'{{< row "([^"]+)" >}}',body) for name in names.split()}
    for number,refs in [('7',['oviedo:35','oviedo:37']),('8',['oviedo:36']),('12',['oviedo:38'])]:
        refs=[ref for ref in refs if resolve(slug,ref)['original_filename'] not in already]
        if refs:groups[number].append('r '+' '.join(refs))
    plan[slug]=dict(hero='existing:IMG_9848.JPG',groups=groups,notes=['Pelayo photograph found in Oviedo folder and matched visually; original retained with explicit cross-chapter mapping.'])
for slug,c in plan.items():
    if '--chapter' in sys.argv and slug!=sys.argv[sys.argv.index('--chapter')+1]:continue
    f=root/f'content/europe/portugal/{trip}/{slug}/index.md';src=f.read_text(encoding='utf-8-sig');fm=src.split('---\n',2)[1];paras=re.findall(r'<p>.*?</p>',src.split('---\n',2)[2],re.S);split=c.get('paragraph_split');
    if split:
        i=split['number']-1
        if paras[i+1].startswith('<p>'+split['marker']):paras[i:i+2]=[paras[i][:-4]+' '+paras[i+1][3:]]
    chapter=next(c for c in m['chapters'] if c['slug']==slug);textsha=hashlib.sha256('\n'.join(paras).encode()).hexdigest();assert chapter['text_sha256']==textsha,(slug,'author text changed')
    hero=photo(slug,c['hero'])
    if c.get('require_horizontal_hero'):assert data[f'{slug}/{hero}']['w']>data[f'{slug}/{hero}']['h'],(slug,'cover must be a horizontal original')
    fm=re.sub(r'^hero_image:.*\n','',fm,flags=re.M)+'hero_image: '+json.dumps(hero,ensure_ascii=False)+'\n'
    if c.get('plain_body_bold') and 'plain_body_bold:' not in fm:fm+='plain_body_bold: true\n'
    if c.get('card'):
        card=photo(slug,c['card']);fm=re.sub(r'^hero_card_image:.*\n','',fm,flags=re.M)+'hero_card_image: '+json.dumps(card)+'\n'
    out=[];used=[hero];blocks=[]
    for n,p in enumerate(paras,1):
        blocks_for_paragraph=c['groups'].get(str(n),[])
        if split and n==split['number']:
            prefix,suffix=p.split(split['marker'],1);out.append(prefix.rstrip()+'</p>');blocks_for_paragraph=split['before_groups']+['text <p>'+split['marker']+suffix]+blocks_for_paragraph
        else:out.append(p)
        for block in blocks_for_paragraph:
            if block.startswith('text '):out.append(block[5:]);continue
            kind,*refs=block.split();names=[]
            for ref in refs:
                marker=''
                if ref.startswith(('L:','R:','T:')):marker,ref=ref[:2],ref[2:]
                name=photo(slug,ref);assert name not in used,(slug,name,'duplicate on page');used.append(name);names.append(marker+name)
            shortcode={'m':'mosaic','e':'art-row'}.get(kind,'row');out.append('{{< '+shortcode+' "'+' '.join(names)+'" >}}');blocks.append(dict(after=n,kind=shortcode,names=names))
        if slug=='lamego' and n==11:
            for video in videos:out.append('{{< travel-video "https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+video['key']+'" >}}')
    rendered_paras=re.findall(r'<p>.*?</p>','\n\n'.join(out),re.S)
    if split:
        i=split['number']-1;rendered_paras[i:i+2]=[rendered_paras[i][:-4]+' '+rendered_paras[i+1][3:]]
    assert paras==rendered_paras
    f.write_text('---\n'+fm+'---\n\n'+'\n\n'.join(out)+'\n',encoding='utf-8');chapter.update(hero_image=hero,display_order=used,blocks=blocks,selection_notes=c.get('notes',[]))
    if c.get('captions'):chapter['photo_captions']=c['captions']
    print(slug,len(used),'photos,',len(paras),'unchanged paragraphs',flush=True)
for p in m['album_originals']:
    if p['chapter'] in plan and not p.get('site_usage'):p['selection_note']='Retained archive original, omitted from reviewed layout as similar angle, collage component, label, or photograph belonging to adjacent chapter.'
m['r2']['photos']=list(photos.values());m['r2']['videos']=videos;m['r2']['status']='night-copies-awaiting-upload';m['status']='chapters-with-owner-photos-prepared-awaiting-public-checks';m['selection_policy']='More photographs and family moments per owner request; identify concrete subjects before attaching to author text; no speculative substitutions.'
if all(p.get('public_verified') for p in [*photos.values(),*videos]):m['r2']['status']='public-photos-and-videos-verified';m['status']='reviewed-chapters-local-draft'
cover=f'{trip}/douro/IMG_0350.JPG';tripfile=root/f'content/europe/portugal/{trip}/_index.md';s=tripfile.read_text(encoding='utf-8-sig');fm,body=s.split('---\n',2)[1:];fm=re.sub(r'^(?:cover_image|cover_position|cover_when|cover_who):.*\n','',fm,flags=re.M);fm+='cover_image: "https://pub-960c15be4df04139842369d59c9b04fc.r2.dev/'+cover+'"\ncover_position: "20% 42%"\ncover_when: "Июнь — июль 2017"\ncover_who: "Ольга и Серёжа"\n';tripfile.write_text('---\n'+fm+'---\n'+body,encoding='utf-8');m['trip_cover']=dict(r2_key=cover,archiveFile=photos[cover]['archiveFile'],selection='Provisional owner portrait overlooking Douro, composed to keep person and title separate on phone and desktop')
for dest in [mf,archive/'photo-manifest.json']:dest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(root/f'data/photos/{trip}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Made',made,'new display copies',flush=True)
for slug,c in plan.items():
    p=resolve(slug,c['hero']);c['hero']=p['chapter']+':'+p['original_filename']
    for number,blocks in c['groups'].items():
        final=[]
        for block in blocks:
            kind,*refs=block.split();names=[]
            for ref in refs:
                marker=''
                if ref.startswith(('L:','R:','T:')):marker,ref=ref[:2],ref[2:]
                p=resolve(slug,ref);names.append(marker+p['chapter']+':'+p['original_filename'])
            final.append(kind+' '+' '.join(names))
        c['groups'][number]=final
(root/f'media-manifests/{trip}-layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


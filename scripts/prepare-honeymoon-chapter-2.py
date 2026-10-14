"""Rebuild Santiago from verified originals while keeping original filenames."""
from pathlib import Path
from PIL import Image,ImageOps
import json,hashlib,re
root=Path.cwd();trip='honeymoon-2017';slug='santiago-de-compostela';mf=root/f'media-manifests/{trip}.json';m=json.loads(mf.read_text(encoding='utf-8-sig'));assert m['archive_verified'] and m['drive_sync_verified'];archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
data=json.loads((root/f'data/photos/{trip}.json').read_text(encoding='utf-8-sig'));copies=[]
for p in [p for p in m['album_originals'] if p['chapter']==slug]:
    src=archive/p['original_relative_path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==p['original_sha256'];name=p['original_filename'];key=f'{trip}/{slug}/{name}';dest=root/'static/r2'/key;dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(src) as original:
        im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((2000,2000),Image.Resampling.LANCZOS);im.save(dest,format='JPEG',quality=85,optimize=True);w,h=im.size
    p['r2_key']=key;data[f'{slug}/{name}']=dict(w=w,h=h,source=p['original_relative_path']);copies.append(dict(key=key,archiveFile=p['original_relative_path'],original_sha256=p['original_sha256'],w=w,h=h,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),recipe=dict(tool='Pillow',exif_transpose=True,long_side_max=2000,no_upscale=True,jpeg_quality=85,optimize=True)))
hero='20170625_130329.jpg'
groups={1:[['IMG_9791.JPG','IMG_9792.JPG','IMG_9793.JPG']],6:[['20170625_123639.jpg'],['20170625_112112.jpg','IMG_9826.JPG','IMG_9836.JPG'],['IMG_9821.JPG']],7:[['20170625_114314.jpg','20170625_114925.jpg'],['20170625_115158.jpg','20170625_115232.jpg','20170625_115856.jpg']],8:[['20170625_125456.jpg']],9:[['20170625_124819.jpg']],10:[['20170625_124739.jpg']],12:[['20170625_123811.jpg']],13:[['20170625_133447.jpg','20170625_132430.jpg','20170625_132931.jpg','20170625_135325.jpg','20170625_135838.jpg'],['20170625_134923.jpg','20170625_134934.jpg']],14:[['20170625_183652.jpg','20170625_183514.jpg']],15:[['20170625_173846.jpg']],16:[['20170625_140538.jpg','20170625_171617.jpg'],['20170625_175258.jpg','20170625_175424.jpg'],['20170625_180052.jpg']],17:[['20170625_154309.jpg']],18:[['20170625_183624.jpg','20170625_184247.jpg'],['20170625_184426.jpg','IMG_9824.JPG']],19:[['20170625_162333.jpg','20170625_163610.jpg']],22:[['20170625_170206.jpg','20170625_204603.jpg']]}
# Shortcode filenames containing spaces cannot be used directly. Keep originals
# unchanged; only the display copy uses an underscore, recorded in the registry.
alias={}
for p in copies:
    old=p['key'].split('/')[-1]
    if old in alias:
        new=alias[old];src=root/'static/r2'/p['key'];p['key']=f'{trip}/{slug}/{new}';src.rename(root/'static/r2'/p['key']);data[f'{slug}/{new}']=data.pop(f'{slug}/{old}')
        original=next(q for q in m['album_originals'] if q['chapter']==slug and q['original_filename']==old);original['site_filename']=new;original['r2_key']=p['key']
used=[hero]+[n for rows in groups.values() for row in rows for n in row];assert len(used)==len(set(used))==42;assert set(used)=={p['original_filename'] for p in m['album_originals'] if p['chapter']==slug and p['original_filename']!='IMG_9827.JPG'}
f=root/f'content/europe/portugal/{trip}/{slug}/index.md';src=f.read_text(encoding='utf-8-sig');fm=src.split('---\n',2)[1];paras=re.findall(r'<p>.*?</p>',src.split('---\n',2)[2],re.S);out=[]
fm=re.sub(r'^hero_image:.*\n','',fm,flags=re.M)+'hero_image: '+json.dumps(hero)+'\n'
for n,p in enumerate(paras,1):
    out.append(p)
    for row in groups.get(n,[]):out.append('{{< row "'+' '.join(alias.get(name,name) for name in row)+'" >}}')
assert paras==re.findall(r'<p>.*?</p>','\n\n'.join(out),re.S);f.write_text('---\n'+fm+'---\n\n'+'\n\n'.join(out)+'\n',encoding='utf-8')
next(c for c in m['chapters'] if c['slug']==slug).update(hero_image=hero,paragraphs=len(paras),text_sha256=hashlib.sha256('\n'.join(paras).encode()).hexdigest(),display_order=[alias.get(n,n) for n in used]);m['r2']['photos']=[p for p in m['r2']['photos'] if not p['key'].startswith(f'{trip}/{slug}/')]+copies;m['r2']['status']='chapter-2-awaiting-upload';m['status']='first-two-chapters-prepared-trip-remains-draft'
for dest in [mf,archive/'photo-manifest.json']:dest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(root/f'data/photos/{trip}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Prepared',len(copies),'photos;',len(paras),'paragraphs preserved')

"""Prepare the first chapter from verified Drive originals, preserving filenames.
Run from this checkout. Upload and public-byte verification follow separately.
"""
from pathlib import Path
from PIL import Image, ImageOps
import json, re, hashlib
root=Path.cwd();trip='honeymoon-2017';slug='baiona-combarro-cambados'
mf=root/'media-manifests'/f'{trip}.json';m=json.loads(mf.read_text(encoding='utf-8-sig'))
assert m['archive_verified'] and m['drive_sync_verified']
archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root']
data={};copies=[]
for p in m['album_originals']:
    src=archive/p['original_relative_path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==p['original_sha256']
    name=p['original_filename'];key=f'{trip}/{slug}/{name}';dest=root/'static/r2'/key;dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(src) as original:
        im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((2000,2000),Image.Resampling.LANCZOS);im.save(dest,format='JPEG',quality=85,optimize=True);w,h=im.size
    p['r2_key']=key
    data[f'{slug}/{name}']=dict(w=w,h=h,source=p['original_relative_path'])
    copies.append(dict(key=key,archiveFile=p['original_relative_path'],original_sha256=p['original_sha256'],w=w,h=h,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),recipe=dict(tool='Pillow',exif_transpose=True,long_side_max=2000,no_upscale=True,jpeg_quality=85,optimize=True)))
f=root/f'content/europe/portugal/{trip}/{slug}/index.md';text=f.read_text(encoding='utf-8');fm=text.split('---\n',2)[1];body=text.split('---\n',2)[2];paras=re.findall(r'<p>.*?</p>',body,re.S)
hero='IMG_9675.JPG'
groups={7:[['20170624_100743.jpg','20170624_104323.jpg','20170624_104811.jpg']],8:[['IMG_9685.JPG','IMG_9697.JPG'],['20170624_103939.jpg','IMG_9714.JPG']],9:[['IMG_9721.JPG']],10:[['IMG_9727.JPG','IMG_9730.JPG']],11:[['20170624_121632.jpg','IMG_9731.JPG'],['20170624_121838.jpg']],12:[['IMG_9733.JPG']],15:[['IMG_9749.JPG','IMG_9742.JPG','IMG_9747.JPG'],['20170624_143403.jpg','IMG_9750.JPG','IMG_9754.JPG','IMG_9776.JPG']],18:[['IMG_9767.JPG','20170624_155019.jpg'],['IMG_9762.JPG','IMG_9765.JPG'],['20170625_095541.jpg']],19:[['20170624_185752.jpg','IMG_9755.JPG','IMG_9780.JPG','IMG_9788.JPG']],20:[['20170624_205034.jpg']],22:[['20170625_091450.jpg','20170625_091514.jpg']]}
used=[name for rows in groups.values() for row in rows for name in row]+[hero]
assert len(used)==len(set(used))==len(m['album_originals'])
assert set(used)=={p['original_filename'] for p in m['album_originals']}
fm=re.sub(r'^hero_image:.*\n','',fm,flags=re.M);fm+='hero_image: '+json.dumps(hero)+'\n'
out=[];order=[hero]
for n,p in enumerate(paras,1):
    out.append(p)
    for row in groups.get(n,[]):
        out.append('{{< row "'+' '.join(row)+'" >}}');order+=row
assert paras==re.findall(r'<p>.*?</p>','\n\n'.join(out),re.S)
f.write_text('---\n'+fm+'---\n\n'+'\n\n'.join(out)+'\n',encoding='utf-8')
m['chapters'][0].update(text_sha256=hashlib.sha256('\n'.join(paras).encode()).hexdigest(),paragraphs=len(paras),hero_image=hero,display_order=order)
m['r2']=dict(status='copies-prepared-awaiting-upload',photos=copies);m['status']='first-chapter-prepared-trip-remains-draft'
for dest in [mf,archive/'photo-manifest.json']:dest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(root/'data/photos'/f'{trip}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Prepared',len(copies),'copies;',len(paras),'paragraphs preserved')




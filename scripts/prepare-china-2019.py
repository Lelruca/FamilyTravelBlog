"""Recreate selected China display copies and layouts from verified Drive originals.
Usage: python scripts/prepare-china-2019.py [--chapter SLUG ...]
Upload and public URL verification remain separate required stages.
"""
from pathlib import Path
from PIL import Image,ImageOps
import argparse,hashlib,json,re,html
parser=argparse.ArgumentParser();parser.add_argument('--chapter',action='append');args=parser.parse_args()
root=Path(__file__).resolve().parents[1];mf=root/'media-manifests/china-2019.json';m=json.loads(mf.read_text(encoding='utf-8'));archive=Path('G:/My Drive/Family Travel Blog Photos')/m['archive_root'];datafile=root/'data/photos/china-2019.json';data=json.loads(datafile.read_text(encoding='utf-8')) if datafile.exists() else {}
selected=set(args.chapter or list(m['chapter_media'])+(['cover'] if m.get('cover_original') else []));copies=[p for p in m.get('r2',{}).get('photos',[]) if p['chapter'] not in selected];made=0
originals=[p for p in m['originals'] if p['chapter'] in selected]
if 'cover' in selected and m.get('cover_original'):originals.append(dict(m['cover_original'],chapter='cover'))
for p in originals:
 c=p if p['chapter']=='cover' else m['chapter_media'][p['chapter']];assert c['originals_verified'] and c['drive_sync_verified'],p['chapter'];src=archive/p['original_relative_path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==p['original_sha256'];dest=root/'static/r2'/p['r2_key'];dest.parent.mkdir(parents=True,exist_ok=True)
 previous=next((v for v in m['r2']['photos'] if v['key']==p['r2_key']),None)
 if previous and dest.exists() and previous['original_sha256']==p['original_sha256'] and previous.get('recipe',{}).get('rotate_clockwise',0)==p.get('display_rotate_degrees',0) and hashlib.sha256(dest.read_bytes()).hexdigest()==previous['sha256']:
  kept=dict(previous);kept['archiveFile']=p['original_relative_path'];copies.append(kept);data[p['chapter']+'/'+p['site_filename']]={'w':kept['w'],'h':kept['h'],'source':p['original_relative_path']};continue
 with Image.open(src) as raw:
  im=ImageOps.exif_transpose(raw).convert('RGB');im=im.rotate(-p.get('display_rotate_degrees',0),expand=True);im.thumbnail((2000,2000),Image.Resampling.LANCZOS);im.save(dest,quality=85,optimize=True);w,h=im.size
 b=dest.read_bytes();recipe={'tool':'Pillow','exif_transpose':True,'long_side_max':2000,'no_upscale':True,'jpeg_quality':85,'optimize':True};recipe.update({'rotate_clockwise':p['display_rotate_degrees']} if p.get('display_rotate_degrees') else {});copies.append({'key':p['r2_key'],'chapter':p['chapter'],'archiveFile':p['original_relative_path'],'original_sha256':p['original_sha256'],'w':w,'h':h,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'recipe':recipe});data[p['chapter']+'/'+p['site_filename']]={'w':w,'h':h,'source':p['original_relative_path']};made+=1
for slug,c in m['chapter_media'].items():
 if slug not in selected:continue
 f=root/m['contentDir']/slug/'index.md';s=f.read_text(encoding='utf-8');paras=re.findall(r'<p>(.*?)</p>',s,re.S);assert [html.unescape(p) for p in paras]==m['verification']['authorParagraphs'][slug]
 fm=s.split('---\n',2)[1];fm=re.sub(r'^hero_image:.*\n','',fm,flags=re.M);fm+='hero_image: '+json.dumps(c['hero_image'])+'\n';out=[]
 if c.get('hero_caption'):out.append('<div class="exhibit-cover-caption">'+html.escape(c['hero_caption'])+'</div>')
 for n,p in enumerate(paras,1):
  layout=c['layout'].get('before'+str(n))
  if layout:
   for group in layout.get('groups',[layout]):
    assert group['type'] in ['row','mosaic','exhibit-row'];out.append('{{< '+group['type']+' "'+' '.join(group['photos'])+'" >}}')
  layout=c['layout'].get('paragraph'+str(n))
  if layout:
   assert layout['type']=='beside';out.append('{{< beside "'+layout['photo']+'" >}}\n<p>'+p+'</p>\n{{< /beside >}}')
  else:out.append('<p>'+p+'</p>')
  layout=c['layout'].get('after'+str(n))
  if layout:
   for group in layout.get('groups',[layout]):
    assert group['type'] in ['row','mosaic','exhibit-row'];out.append('{{< '+group['type']+' "'+' '.join(group['photos'])+'" >}}')
 if c.get('extra_css'):out.append('<style>'+c['extra_css']+'</style>')
 f.write_text('---\n'+fm+'---\n\n'+'\n\n'.join(out)+'\n',encoding='utf-8');c['stage']='copies-prepared-awaiting-r2-verification'
for slug in selected:
 for name,caption in m.get('chapter_media',{}).get(slug,{}).get('photo_captions',{}).items():data[slug+'/'+name]['caption']=caption
datafile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');m['r2'].update(status='copies-prepared-awaiting-upload',photos=copies);mf.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(archive/'photo-manifest.json').write_text(mf.read_text(encoding='utf-8'),encoding='utf-8');print('Prepared',made,'copies and layouts for',', '.join(sorted(selected)))

"""Transfer existing visible annotations only through verified fixed geometry."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
from PIL import Image,ImageDraw
base=Path(sys.argv[1]);root=base/'B-010-animal-self-reenactment';prior=base/'B-006-motion-representation';src7=base/'B-007-scail-preflight/inputs/input_preflight';original=json.loads((prior/'annotations/annotated_landmarks.json').read_text());out=root/'reports/preflight';rows=[]
keys=['nose','left_eye','right_eye','left_front_paw','right_front_paw'];colors=['#ff0000','#00ffff','#ffff00','#ff00ff','#00ff00'];sx=1592/512;sy=896/288
for f in original['frames']:
 i=f['frame'];name=f'{i:03d}.png';a=prior/'inputs/source'/name;b=src7/'source'/name
 assert np.array_equal(np.asarray(Image.open(a).convert('RGB')),np.asarray(Image.open(b).convert('RGB')))
 with Image.open(a) as im:expected=np.asarray(im.convert('RGB').resize((1592,896),Image.Resampling.BICUBIC).crop((540,0,1052,896)))
 with Image.open(src7/'prepared_driver'/name) as im:assert np.array_equal(expected,np.asarray(im.convert('RGB')))
 with Image.open(root/'source'/name) as im:actual=np.asarray(im.convert('RGB'))
 # Input MP4 is lossless in existing path; enforce actual decoded equality.
 assert np.array_equal(expected,actual)
 points={}
 for key in keys:
  old=f['landmarks'][key];p=old['xy'];points[key]={'xy':None if p is None else [p[0]*sx-540,p[1]*sy],'uncertainty_radius_px':None if p is None else old['uncertainty_px']*max(sx,sy)+1,'visibility':old['visibility'],'kind':'visible_surface_proxy','original_xy':p,'original_uncertainty_px':old['uncertainty_px']}
 rows.append({'frame':i,'t_seconds':i/24,'points':points,'source_sha256':hashlib.sha256((root/'source'/name).read_bytes()).hexdigest()})
selected=[0,4,8,12,16];sheet=Image.new('RGB',(1024,5*920),'#222222');baseline=rows[0]['points'];comparisons=[]
for row,i in enumerate(selected):
 for col,idx in enumerate([i,0]):
  im=Image.open(root/'source'/f'{idx:03d}.png').convert('RGB');draw=ImageDraw.Draw(im)
  for key,color in zip(keys,colors):
   p=rows[idx]['points'][key]['xy'];r=rows[idx]['points'][key]['uncertainty_radius_px']
   if p is None:continue
   x,y=p;draw.ellipse((x-r,y-r,x+r,y+r),outline=color,width=2);draw.ellipse((x-2,y-2,x+2,y+2),fill=color);draw.text((x+10,y-15),key,fill=color,stroke_width=1,stroke_fill='black')
  sheet.paste(im,(col*512,row*920+24));ImageDraw.Draw(sheet).text((col*512+3,row*920+4),f'f{i}: '+('SOURCE' if col==0 else 'STATIC COPY f0'),fill='white')
 if i:
  for key in keys:
   p=rows[i]['points'][key];q=baseline[key];dist=math.dist(p['xy'],q['xy']);u=p['uncertainty_radius_px']+q['uncertainty_radius_px'];comparisons.append({'frame':i,'point':key,'displacement_px':dist,'two_observation_uncertainty_px':u,'above_uncertainty':dist>u})
sheet.save(out/'annotated-source-static.png')
(root/'annotations/source-landmarks.json').write_text(json.dumps({'provenance':'B006 manual source-only annotations; verified exact crop/time/pixels; no interpolation, no generated output viewed','geometry':{'scale_x':sx,'scale_y':sy,'crop_left':540,'crop_top':0,'additional_display_quantization_uncertainty_px':1},'genuine_joints':'UNKNOWN; not annotated','contact':'UNKNOWN; not inferred','rows':rows},indent=2)+'\n')
report={'scope':'source-only CPU preflight, generation NOT_RUN','fixed_frames':selected,'fixed_points':keys,'normalizer_px':896,'comparisons':comparisons,'coverage':{'source_visible':len(comparisons),'expected':20},'E_copy_px':sum(x['displacement_px'] for x in comparisons)/len(comparisons),'mean_uncertainty_px':sum(x['two_observation_uncertainty_px'] for x in comparisons)/len(comparisons),'judgement':'OBSERVABLE_STATIC_DIFFERENCE only if independently reviewed overlays support endpoint eye/nose locations; articulation is not established from global displacement','gain_rule':'UNDEFINED if E_copy <= mean_uncertainty; do not shrink uncertainty or choose favorable new samples after outputs','forbidden':'No time/crop/pose alignment; no inferred joints/contact; generated missing points retain coverage failure; no motion acceptance from rigid translation/zoom alone'}
(out/'observability.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'E_copy_px':report['E_copy_px'],'mean_uncertainty_px':report['mean_uncertainty_px'],'above_uncertainty':[(x['frame'],x['point'],x['displacement_px']) for x in comparisons if x['above_uncertainty']]},indent=2))

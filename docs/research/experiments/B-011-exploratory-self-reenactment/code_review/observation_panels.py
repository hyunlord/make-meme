"""Fixed source-only viewing crops, without prior landmark overlay or filtering."""
from pathlib import Path
from PIL import Image,ImageDraw
import sys,json,hashlib
src,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True);records=[]
for f in [0,4,8,12,16]:
 p=src/f'{f:03d}.png';im=Image.open(p).convert('RGB');assert im.size==(512,896)
 sheet=Image.new('RGB',(1024,900),'#eeeeee');sheet.paste(im,(0,0));d=ImageDraw.Draw(sheet)
 for y in range(0,896,50):d.line((0,y,511,y),fill='#bbbbbb',width=1);d.text((1,y+2),str(y),fill='black')
 for x in range(50,512,50):d.line((x,0,x,895),fill='#bbbbbb',width=1);d.text((x+2,1),str(x),fill='black')
 for n,box in enumerate([(220,230,440,380),(130,410,420,610)]):
  crop=im.crop(box);sheet.paste(crop.resize((440,300) if n==0 else (435,300),Image.Resampling.NEAREST),(560,35+n*390));d.text((560,10+n*390),f'f{f} source crop{box}; display only',fill='black')
 sheet.save(out/f'observe-{f:02d}.png');records.append({'frame':f,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'crop_boxes':[[220,230,440,380],[130,410,420,610]],'resize':'nearest display only; coordinates native512x896; no generated/enhanced pixels'})
(out/'panel-provenance.json').write_text(json.dumps(records,indent=2)+'\n')

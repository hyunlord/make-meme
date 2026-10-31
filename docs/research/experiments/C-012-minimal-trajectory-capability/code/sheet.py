import sys
from PIL import Image, ImageDraw
out=sys.argv[1]; dirs=sys.argv[2:]
idx=(0,4,8,12,16,20,24,28,32)
s=Image.new('RGB',(9*208,len(dirs)*(120+14)),'#202020'); d=ImageDraw.Draw(s)
for r,p in enumerate(dirs):
    label,folder=p.split('=')
    for c,i in enumerate(idx):
        s.paste(Image.open(f'{folder}/{i:03d}.png').convert('RGB').resize((208,120)),(c*208,r*134+14))
    d.text((4,r*134),label,fill='white')
s.save(out)

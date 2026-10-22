"""Recorded local background exclusions only; no image RGB edits or new pixels.
Run with B007_ROOT. Private annotations/input-mask-trim.json supplies reviewed
rectangles (x0,y0,x1,y1), outside visible paw/tail boundaries. Preserve v1.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
import numpy as np
from PIL import Image

root=Path(sys.argv[1]);inp=root/'inputs/input_preflight';out=root/'outputs/input_preflight'
records=json.loads((root/'annotations/input-mask-trim.json').read_text())
(inp/'driver_mask_local_trim').mkdir(exist_ok=True);(inp/'prepared_mask_local_trim').mkdir(exist_ok=True)
changes=[]
for record in records['frames']:
    i=record['frame'];old=np.array(Image.open(inp/'driver_mask'/f'{i:03d}.png').convert('RGB'));new=old.copy()
    for x0,y0,x1,y1 in record['background_exclusion_rectangles']:new[y0:y1,x0:x1]=0
    assert np.all((new==old)|(new==0))
    Image.fromarray(new).save(inp/'driver_mask_local_trim'/f'{i:03d}.png')
    # Identical preregistered geometry: 512x288 ->1592x896 -> center512x896.
    ids=Image.fromarray(new).resize((1592,896),Image.Resampling.NEAREST).crop((540,0,1052,896))
    ids.save(inp/'prepared_mask_local_trim'/f'{i:03d}.png')
    rgb=Image.open(inp/'prepared_driver'/f'{i:03d}.png').convert('RGB')
    before=Image.open(inp/'prepared_mask'/f'{i:03d}.png').convert('RGB')
    sheet=Image.new('RGB',(1536,896));sheet.paste(rgb,(0,0));sheet.paste(Image.blend(rgb,before,.35),(512,0));sheet.paste(Image.blend(rgb,ids,.35),(1024,0));sheet.save(out/f'local-trim-{i:02d}.jpg',quality=95)
    changes.append(dict(frame=i,removed_original_pixels=int(np.any(old!=new,axis=2).sum()),old_sha256=hashlib.sha256(old.tobytes()).hexdigest(),new_sha256=hashlib.sha256(new.tobytes()).hexdigest(),record=record))
video=out/'prepared-mask-local-trim-24fps.mp4'
command=['ffmpeg','-y','-v','error','-framerate','24','-i',str(inp/'prepared_mask_local_trim/%03d.png'),'-frames:v','17','-fps_mode','passthrough','-c:v','libx264rgb','-crf','0','-pix_fmt','rgb24',str(video)]
subprocess.run(command,check=True,timeout=90)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_read_frames,duration,width,height','-of','json',str(video)]));assert probe['streams'][0]['avg_frame_rate']=='24/1' and int(probe['streams'][0]['nb_read_frames'])==17
(root/'reports/input_preflight_local_trim.json').write_text(json.dumps(dict(changes=changes,video_probe=probe,command=command,note='Manual local floor exclusions from RGB review. No whole-floor line; visible central tail retained. Thin edges remain uncertain. Not learned segmentation accuracy or production acceptance.'),indent=2)+'\n')

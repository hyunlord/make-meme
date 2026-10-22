"""Verify existing lossless mask videos against their exact PNG sequences; CPU only."""
from pathlib import Path
import json,subprocess,sys
import numpy as np
from PIL import Image

root=Path(sys.argv[1]);results=[]
for video,folder in [('prepared-mask-24fps.mp4','prepared_mask'),('prepared-mask-local-trim-24fps.mp4','prepared_mask_local_trim')]:
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/'outputs/input_preflight'/video),'-f','rawvideo','-pix_fmt','rgb24','-'])
    actual=np.frombuffer(raw,np.uint8).reshape(17,896,512,3)
    expected=np.stack([np.asarray(Image.open(root/'inputs/input_preflight'/folder/f'{i:03d}.png').convert('RGB')) for i in range(17)])
    assert np.array_equal(actual,expected)
    colors=np.unique(actual.reshape(-1,3),axis=0).tolist();assert colors==[[0,0,0],[255,0,0]]
    results.append({'video':video,'all17_decoded_pixels_equal_png':True,'decoded_colors':colors})
(root/'reports/input_preflight_mask_decode.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS: v1 and v2 decoded pixels equal all17 PNGs; black/red only.')

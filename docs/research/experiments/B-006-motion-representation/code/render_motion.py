# /// script
# dependencies = ["Pillow"]
# ///
# Run: python3 render_motion.py B006_ROOT
"""Render manual visible points without interpolation or hidden-joint invention."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from collections import Counter
from PIL import Image, ImageDraw

root=Path(sys.argv[1]);schema=json.loads((root/'tools/annotation_schema.json').read_text())
data=json.loads((root/'annotations/annotated_landmarks.json').read_text())
frames=data['frames'];assert [f['frame'] for f in frames]==list(range(17))
output=root/'outputs';(output/'overlay').mkdir(parents=True,exist_ok=True)
summary=Counter();per_landmark={name:Counter() for name in schema['landmark_ids']};records=[]
comparison=Image.new('RGB',(5*512,4*3*312),(25,25,25))
overview=Image.new('RGB',(5*512,4*312),(25,25,25))
for frame in frames:
    index=frame['frame'];assert abs(frame['time_seconds']-index/24)<1e-8
    with Image.open(root/'inputs/source'/f'{index:03d}.png') as source:
        original=source.convert('RGB');overlay=original.copy()
    draw=ImageDraw.Draw(overlay)
    assert set(frame['landmarks'])==set(schema['landmark_ids'])
    for name,point in frame['landmarks'].items():
        assert point['visibility'] in schema['visibility']
        summary[point['visibility']]+=1;per_landmark[name][point['visibility']]+=1
        xy=point['xy']
        if xy is not None:
            assert frame['annotation_status']=='ANNOTATED' and frame['viewed_individually']
            assert point['visibility']=='visible' and point['uncertainty_px']>0
            x,y=xy;assert 0<=x<512 and 0<=y<288
            draw.ellipse((x-2,y-2,x+2,y+2),fill=(255,220,0))
            records.append({'frame':index,'point':name,'xy':xy,'normalized_xy':[x/512,y/288],
                            'uncertainty_px':point['uncertainty_px']})
        else:
            assert point['visibility']!='visible'
    draw.text((5,5),f'f{index} manual visible points; hidden joints=null',fill=(255,255,0))
    overlay.save(output/'overlay'/f'{index:03d}.png')
    col,row=index%5,index//5
    overview.paste(overlay,(col*512,row*312+24));ImageDraw.Draw(overview).text((col*512+5,row*312+5),f'f{index} @ {index/24:.4f}s',fill='white')
    with Image.open(root/'inputs/canny'/f'{index:03d}.png') as edge: canny=edge.convert('RGB')
    for k,(label,image) in enumerate([('source',original),('Canny',canny),('manual points',overlay)]):
        x,y=col*512,(row*3+k)*312
        comparison.paste(image,(x,y+24));ImageDraw.Draw(comparison).text((x+5,y+5),f'{label} f{index}',fill='white')
overview.save(output/'all17-overlay.jpg',quality=95);comparison.save(output/'all17-source-canny-overlay.jpg',quality=95)
selected=Image.new('RGB',(2560,936),(25,25,25))
for col,index in enumerate([0,4,8,12,16]):
    for row,(label,path) in enumerate([('source',root/'inputs/source'),('Canny',root/'inputs/canny'),('manual points',output/'overlay')]):
        with Image.open(path/f'{index:03d}.png') as image: selected.paste(image.convert('RGB'),(col*512,row*312+24))
        ImageDraw.Draw(selected).text((col*512+5,row*312+5),f'{label} f{index}',fill='white')
selected.save(output/'selected-source-canny-overlay.jpg',quality=95)
# Unsmoothed connected segments require adjacent manual observations only.
velocities=[]
for name in schema['landmark_ids']:
    for left,right in zip(frames[:-1],frames[1:],strict=True):
        a,b=left['landmarks'][name],right['landmarks'][name]
        if a['xy'] is not None and b['xy'] is not None:
            velocities.append({'point':name,'frames':[left['frame'],right['frame']],
                'velocity_px_per_second':[(b['xy'][i]-a['xy'][i])*24 for i in (0,1)],
                'worst_case_component_uncertainty_px_per_second':24*(a['uncertainty_px']+b['uncertainty_px']),
                'interpretation':'Finite difference of manual image observations; not subpixel motion truth.'})
trajectory=Image.new('RGB',(1024,576),'white');td=ImageDraw.Draw(trajectory)
colors=['#b32020','#2579b8','#107a42','#9955aa','#bd7400','#555555','#098c8c']
visible_names=[name for name in schema['landmark_ids'] if per_landmark[name]['visible']]
for j,name in enumerate(visible_names):
    color=colors[j%len(colors)];td.text((5,10+j*18),name,fill=color)
    for frame in frames:
        point=frame['landmarks'][name]['xy']
        if point is not None:
            x,y=point[0]*2,point[1]*2;td.ellipse((x-2,y-2,x+2,y+2),fill=color)
    for record in velocities:
        if record['point']==name:
            f,g=record['frames'];a=frames[f]['landmarks'][name]['xy'];b=frames[g]['landmarks'][name]['xy']
            td.line((a[0]*2,a[1]*2,b[0]*2,b[1]*2),fill=color,width=1)
td.text((5,550),'2x original coordinate display; no smoothing; sparse/overlapping marks are expected',fill='black')
trajectory.save(output/'trajectories.png')
commands=[]
for name,path in [('source',root/'inputs/source'),('canny',root/'inputs/canny'),('keypoint_overlay',output/'overlay')]:
    cmd=['ffmpeg','-y','-v','error','-framerate','24','-start_number','0','-i',str(path/'%03d.png'),'-frames:v','17','-fps_mode','passthrough','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(output/f'{name}.mp4')]
    subprocess.run(cmd,check=True,timeout=90);commands.append(cmd)
cmd=['ffmpeg','-y','-v','error','-i',str(output/'source.mp4'),'-i',str(output/'canny.mp4'),'-i',str(output/'keypoint_overlay.mp4'),'-filter_complex','[0:v][1:v][2:v]hstack=inputs=3[v]','-map','[v]','-frames:v','17','-fps_mode','passthrough','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(output/'source-canny-overlay.mp4')]
subprocess.run(cmd,check=True,timeout=90);commands.append(cmd)
probes=[]
for video in output.glob('*.mp4'):
    result=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=avg_frame_rate,nb_read_frames,duration,width,height','-of','json',str(video)],check=True,capture_output=True,text=True,timeout=30)
    info=json.loads(result.stdout);stream=info['streams'][0]
    assert stream['avg_frame_rate']=='24/1' and int(stream['nb_read_frames'])==17
    probes.append({'file':video.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'probe':info})
report={'visibility':dict(summary),'per_landmark':{key:dict(value) for key,value in per_landmark.items()},
    'annotated_frames':sum(f['annotation_status']=='ANNOTATED' for f in frames),'observations':records,'finite_differences':velocities,
    'root_relative':'NOT_COMPUTED: anatomical pelvis root and reliable body scale unresolved; pixel normalization is separate.',
    'temporal_quality':'UNVERIFIED','commands':commands,'videos':probes}
(root/'reports').mkdir(exist_ok=True);(root/'reports/motion_measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print('Manual motion visualization completed; no generated imagery or hidden joints inferred.')

"""Read-only technical output gate before any conditional second sampler."""
from pathlib import Path
import json
import subprocess
import sys


def check(root: Path) -> dict:
    process=json.loads((root/'reports/pipeline-process.json').read_text())
    run=json.loads((root/'outputs/official/run.json').read_text())
    assert process['reason']=='service_exit' and process['returncode']==0
    assert 'MainPID=0' in process['final_service']
    assert run['status']=='COMPLETED' and run['output_finite']
    assert run['output']['shape']==[3,17,512,896]
    assert any(row['name']=='video_verified' for row in run['phases'])
    path=root/'outputs/official/output.mp4'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))['streams'][0]
    assert (int(probe['nb_frames']),probe['avg_frame_rate'])==(17,'16/1')
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
    return {'status':'VIDEO_OUTPUT_PASS','quality':'UNVERIFIED','Lab_requires_fresh_guard':True}

if __name__=='__main__':
    print(json.dumps(check(Path(sys.argv[1])),indent=2))

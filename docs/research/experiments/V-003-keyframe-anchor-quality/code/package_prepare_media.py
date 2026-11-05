# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: /usr/bin/python3 package_prepare_media.py PRIVATE_RUNTIME.json
"""Create declared CPU comparison clips in a new directory, preserving originals."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cfg = json.loads(Path(sys.argv[1]).read_text())
    scene = json.loads(Path(cfg['scene_config']).read_text())
    segment = scene['scene']['segment']
    size = scene['anchor_generation']['resolution_master']
    out = Path(cfg['output'])
    out.mkdir(parents=True, exist_ok=False)
    source, kling = out/'source.mp4', out/'kling.mp4'
    common = [cfg['ffmpeg'], '-nostdin', '-hide_banner', '-loglevel', 'error', '-n', '-threads', '2']
    encode = ['-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'medium', '-crf', '18',
              '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
    commands = [common+['-framerate', str(segment['fps']), '-start_number', '0',
                       '-i', str(Path(cfg['source_frames'])/'%03d.png'), '-frames:v', str(segment['frames'])]
                +encode+[str(source)],
                common+['-i', cfg['kling_original'], '-vf',
                        f"trim=start_frame={segment['start']}:end_frame={segment['end_exclusive']},setpts=PTS-STARTPTS,scale={size[0]}:{size[1]}:flags=lanczos",
                        '-r', str(segment['fps']), '-frames:v', str(segment['frames'])]+encode+[str(kling)]]
    started = time.time()
    for command in commands:
        subprocess.run(command, check=True)
    records = {}
    for role, path in [('source', source), ('kling', kling)]:
        probe = subprocess.run([cfg['ffprobe'], '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                                '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate',
                                '-of', 'json', str(path)], check=True, capture_output=True, text=True)
        stream = json.loads(probe.stdout)['streams'][0]
        numerator, denominator = map(int, stream['r_frame_rate'].split('/'))
        if int(stream['nb_read_frames']) != segment['frames'] or numerator/denominator != segment['fps']:
            raise ValueError('Comparison clip timing does not match scene contract')
        if [stream['width'], stream['height']] != size:
            raise ValueError('Comparison clip dimensions do not match canonical size')
        records[role] = {'sha256': digest(path), 'bytes': path.stat().st_size, 'probe': stream,
                         'role': 'CPU_DERIVED_VIEW_CLIP_NOT_ORIGINAL_BYTES'}
    records['kling_parent_sha256'] = digest(Path(cfg['kling_original']))
    records['source_frame_hashes'] = [digest(Path(cfg['source_frames'])/f'{i:03d}.png') for i in range(segment['frames'])]
    (out/'provenance-private.json').write_text(json.dumps({'started': started, 'finished': time.time(),
        'scene_config_sha256': digest(Path(cfg['scene_config'])), 'records': records, 'commands': commands}, indent=2)+'\n')
    print(json.dumps({'status': 'COMPLETE', 'output': str(out), 'elapsed_seconds': time.time()-started}))


if __name__ == '__main__':
    main()

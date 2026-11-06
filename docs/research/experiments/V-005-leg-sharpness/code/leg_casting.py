# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "Pillow", "scipy"]
# ///
"""Reference-only fixed casting: leg_casting.py SCENE PRIVATE_RUNTIME OUTPUT.json.

Runtime: parent_code, source_summary, output_summary, frame_count, native_size.
Uses frozen parent readers and reflection policy, no SAM/model calls. Needed
for reference videos without a pre-existing generated-output metric report.
"""
from pathlib import Path
import json
import sys
from leg_io import atomic_json


def main() -> None:
    scene,runtime,output=map(Path,sys.argv[1:]);r=json.loads(runtime.read_text())
    sys.path.insert(0,r['parent_code'])
    from anchor_gates import Policy,classify
    from output_metrics import descriptors,bind
    from post_composite import Geometry,read_instances
    policy=Policy.read(scene);geometry=Geometry(policy.size,tuple(r['native_size']))
    rows=[];casting=None
    for index in range(r['frame_count']):
        source=descriptors(read_instances(Path(r['source_summary']),index,geometry),geometry)
        actual=descriptors(read_instances(Path(r['output_summary']),index,geometry),geometry)
        sm,om={x.track:x for x in source},{x.track:x for x in actual}
        tracks,reflections=classify(actual,policy)
        minimum=json.loads(scene.read_text())['sam_settings']['min_area_fraction']
        tracks=[t for t in tracks if om[t].area/(policy.size[0]*policy.size[1])>=minimum]
        if index==0:casting=bind(sm,om,tracks,policy)
        rows.append({'frame':index,'actual_tracks':tracks,'reflection_tracks':reflections,
                     'count_matches':len(tracks)==policy.count})
    atomic_json(output,{'casting':casting,'casting_status':'ESTABLISHED' if casting else 'UNESTABLISHED',
                        'frames':rows,'count_matches_fraction':sum(row['count_matches'] for row in rows)/len(rows),
                        'role':r.get('role','REFERENCE_ONLY'),'quality':'HUMAN_REVIEW_PENDING'})


if __name__=='__main__':main()

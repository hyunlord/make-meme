# /// script
# requires-python = ">=3.12"
# ///
"""Preserve baseline settings, change only reference/seed/output/deadline."""
from pathlib import Path
import json
import sys
base=json.loads(Path(sys.argv[1]).read_text())
root=Path(sys.argv[2])
deadline=sys.argv[3]
(root/'configs').mkdir(parents=True,exist_ok=True)
conditions={'R':base['reference'],'R-bg':str(root/'inputs/R-bg.png'),'P':str(root/'inputs/P.png')}
for seed in (20261022,20261023):
    for condition,reference in conditions.items():
        label=f'{condition}-{seed}'
        config={**base,'reference':reference,'seed':seed,'output':str(root/'outputs'/label),'deadline':deadline,'max_seconds':1800}
        assert config['adapter'] is None and config['optimizer_checkpoint'] is None
        (root/'configs'/f'{label}.json').write_text(json.dumps(config,indent=2))
policy={'deadline':deadline,'attempt_cap':5,'shared_gpu_lock':str(root.parent/'.b-research-gpu.lock'),'queue_url':None}
(root/'configs/policy.json').write_text(json.dumps(policy,indent=2))

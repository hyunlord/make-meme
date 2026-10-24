# CPU paired-data validator

Run with an existing Python environment providing Pydantic 2 and system ffmpeg/ffprobe:

```sh
python validate_cases.py /private/cases.json --output /private/validation.json
```

`schema.json` and `template.json` define the input. Paths may be absolute or relative to the manifest directory. Up to eight cases; each image has one frame and each video at most 240. This is a bounded local inspection utility, not a training pipeline.

Asset `timestamps` are actual encoded presentation timestamps (seconds). `frame_indices` are the original source frame indices and `source_fps` the original rate. These are separate: a segment beginning at original frame 7 can have encoded timestamps beginning at 0. A sparse sample retains its actual original indices; indices are never manufactured or repeated. `fps` records encoded rate, not source rate. Images have one timestamp; their image demuxer default rate is ignored.

Each RGB/mask asset records width, height, frames, fps, timestamps, source_id, session_id, source_fps, frame_indices, identity_id (nullable), origin (REAL/GENERATED/UNKNOWN), parent_ids. Missing assets are null and become missing_fields. UNKNOWN origin and rights never become training-ready. Source-track IDs and written evidence are declarations; the validator does not recognize biological identity or certify motion correspondence. Mask geometry/timing is checked, not animal-mask semantics.

Pair levels are SELF_RECON_SMOKE, SAME_ID_POSE_VARIATION, CROSS_ID_MOTION_PAIR. `identity_evidence` concerns R/Y; motion_correspondence and reference_pose_evidence have separate status/basis. Different D/Y IDs alone do not establish a motion pair. Rights are independently recorded for research/training/redistribution/commercial.

Full-file SHA256 and every RGB24 decoded-frame SHA256 are recorded. D=Y and R=Y-first decoded equality are separate from original-source-index lineage. JPEG/video codec differences can make decoded equality false without disproving common source-frame origin. Actual origin equality is only as trustworthy as source provenance.

Synthetic test media are strictly validator fixtures, not actual animal data or quality evidence. Reports contain private paths and must remain private. No media is uploaded. No models or GPU are used.

`structural_media_complete` means all required declared media/caption exist and decode with matching metadata and mask alignment; it is not pair acceptance. `pair_available` additionally requires origin/identity/level-specific declared evidence. `training_ready` also requires rights and no cross-split leakage. Within-case R/Y and D/Y source interval overlaps are reported separately; null means missing asset or incomparable source IDs. Pixel equality and temporal overlap are never hidden because they are valid reconstruction shortcuts.

The CLI uses typed stdlib argparse to avoid adding dependencies. Typecheck is scoped to the script directory with `typeCheckingMode=all`, including exhaustive literal-match diagnostics; no report suppression is used. Reproduce checks with existing tools only:

```sh
python -m pytest -q test_validator.py
uvx --offline ruff check .
uvx --offline basedpyright --project pyrightconfig.json --pythonpath "$(command -v python3)"
```

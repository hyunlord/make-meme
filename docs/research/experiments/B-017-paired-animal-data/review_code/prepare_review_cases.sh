#!/bin/sh
# CPU-only copy/encode for private review; does not produce training permission.
# DATA_ROOT: existing B research root; RUN_ROOT: new B017 private directory.
set -eu
: "${DATA_ROOT:?existing research root required}"
: "${RUN_ROOT:?new private B017 root required}"
mov="$DATA_ROOT/B-012-clear-motion-driving-control/cases/MOV/inputs"
lab="$DATA_ROOT/B-013-lab-driving-transfer/cases/LAB_MOV/inputs"
f0="$RUN_ROOT/inventory/retrieved"
mkdir -p "$RUN_ROOT/cases" "$RUN_ROOT/reports"
for sample in self_f7 pose_f0; do
  dest="$RUN_ROOT/cases/$sample"
  test ! -e "$dest"
  mkdir "$dest"
  cp "$mov/driver-24fps.mp4" "$dest/GT.mp4"
  cp "$mov/driver-24fps.mp4" "$dest/rendered_v2.mp4"
  cp "$mov/mask-24fps.mp4" "$dest/rendered_mask_v2.mp4"
  cp "$mov/driver/000.png" "$dest/target-first-original.png"
  cat > "$dest/prompt.txt" <<'TXT'
A small cream-colored short-haired dog-like subject stands upright on its hind legs in a bright room with a reflective pale floor. The front paws are bent before its chest; the head tilts progressively sideways near the end while the torso faces the camera.
TXT
  if [ "$sample" = self_f7 ]; then
    cp "$mov/reference.png" "$dest/ref.png"
    cp "$mov/reference-mask-white.png" "$dest/ref_mask.png"
  else
    cp "$f0/source-f0-reference.png" "$dest/ref.png"
    cp "$f0/source-f0-reference-mask-white.png" "$dest/ref_mask.png"
  fi
done
dest="$RUN_ROOT/cases/lab_missing_target"
test ! -e "$dest"
mkdir "$dest"
cp "$lab/reference.png" "$dest/ref.png"
cp "$lab/reference-mask-white.png" "$dest/ref_mask.png"
cp "$mov/driver-24fps.mp4" "$dest/rendered_v2.mp4"
cp "$mov/mask-24fps.mp4" "$dest/rendered_mask_v2.mp4"
printf '%s\n' 'NOT_A_COMPLETE_CASE: actual Lab target video and target-grounded caption missing. No GT.mp4 is created.' > "$dest/MISSING.txt"
# No frame synthesis/interpolation/warping: thumbnails only, full17 frames.
ffmpeg -nostdin -v error -threads 1 -i "$mov/driver-24fps.mp4" -vf 'scale=128:224,tile=6x3' -frames:v 1 "$RUN_ROOT/reports/target-all17.png"
ffmpeg -nostdin -v error -threads 1 -i "$f0/source-f0-reference.png" -i "$mov/reference.png" -i "$mov/driver/016.png" -filter_complex '[0:v]scale=256:448[a];[1:v]scale=256:448[b];[2:v]scale=256:448[c];[a][b][c]hstack=inputs=3[out]' -map '[out]' -frames:v 1 "$RUN_ROOT/reports/reference-f0_f7_target-f23.png"
printf '%s\n' 'Review-only source cases copied; training rights and provenance remain pending.'

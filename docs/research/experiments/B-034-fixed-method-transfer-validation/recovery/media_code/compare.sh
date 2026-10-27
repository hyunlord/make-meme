#!/bin/sh
# SOURCE PNG / BASE PNG, left/right full canvas. New CPU preview, not raw replacement.
set -eu
source_frames=$1
base_frames=$2
output=$3
test ! -e "$output"
ffmpeg -v error -framerate 24 -i "$source_frames/%03d.png" -framerate 24 -i "$base_frames/%03d.png" \
  -filter_complex '[0:v][1:v]hstack=inputs=2,scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p[v]' \
  -map '[v]' -frames:v 17 -c:v libx264 -crf 18 -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 "$output"
ffmpeg -v error -i "$output" -f null -
ffprobe -v error -show_streams -of json "$output"

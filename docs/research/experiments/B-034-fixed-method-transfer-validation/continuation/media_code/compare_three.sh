#!/bin/sh
# CPU preview only: three native-size panels; no interpolation or alignment.
set -eu
source_frames=$1
base_frames=$2
control_frames=$3
output=$4
test ! -e "$output"
ffmpeg -v error -framerate 24 -i "$source_frames/%03d.png" -framerate 24 -i "$base_frames/%03d.png" -framerate 24 -i "$control_frames/%03d.png" -filter_complex '[0:v][1:v][2:v]hstack=inputs=3,scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=yuv420p[v]' -map '[v]' -frames:v 17 -c:v libx264 -crf 18 -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 "$output"
ffmpeg -v error -i "$output" -f null -
ffprobe -v error -show_streams -of json "$output"

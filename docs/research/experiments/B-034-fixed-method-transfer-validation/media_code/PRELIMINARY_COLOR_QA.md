# Source preview color verification

Actual Chrome playback surfaces for both original GBRP driver MP4 files showed green/magenta colors inconsistent with source RGB PNGs. The original files and model inputs were not modified.

Two new preview derivatives were encoded from each existing 17-frame RGB PNG sequence with ffmpeg/libx264, 24fps, CRF18, yuv420p, no resizing/cropping/interpolation. Encoding took 0.1862s and 0.1925s; sizes are 296,103 and 500,545 bytes. Actual original hashes remained unchanged. Private receipts include commands, all17 PNG hashes, original/preview hashes and ffprobe metadata.

Actual Chrome screenshots of both new previews show natural colors corresponding to the source PNGs. Static color check PASS; temporal quality remains UNVERIFIED. The preliminary inherited global play-advance assertion failed before screenshot inspection and is preserved as failed evidence, not converted to PASS. A separate bounded visible-video color check produced the evidence above. Final viewer playback/control QA remains pending actual generated outputs.

Compact will use the compatibility preview. Full retains original driver MP4 bytes and their provenance. No model generation, encoder or input-condition change occurred.

# CPU review reproduction

Use the existing Torch/torchvision/Pillow/NumPy/ffmpeg environment. No new packages or model calls. Set B024_ROOT to the private result directory and CPU_PYTHON to the existing interpreter. The scripts refuse to overwrite prior review directories.

```sh
cd "$B024_ROOT"
"$CPU_PYTHON" scripts/prepare_input_review.py --original reports/comparison-inputs/reference.png --neutral reports/input-review-inputs/reference-rgb-neutral.png --reference-mask reports/input-review-inputs/reference-mask-black.png --driver-rgb reports/comparison-inputs/source --driver-mask "$DRIVER_MASK_DIR" --output reports/input-review
"$CPU_PYTHON" scripts/export_condition_reconstruction.py .
"$CPU_PYTHON" -c 'from pathlib import Path; from scripts.build_comparison import export_raw; r=Path.cwd(); export_raw(r/"artifacts/raw_output.pt",r/"reports/comparison-replacement-raw",r/"reports/comparison-replacement-all17.png")'
"$CPU_PYTHON" scripts/build_comparison.py --target reports/comparison-inputs/source --baseline reports/comparison-inputs/baseline --replacement reports/comparison-replacement-raw --reference reports/comparison-inputs/reference.png --neutral-reference reports/input-review-inputs/reference-rgb-neutral.png --output reports/comparison-final
"$CPU_PYTHON" scripts/verify_raw_export.py .
"$CPU_PYTHON" scripts/build_viewer.py .
```

On the existing Mac Chrome + websocket-client installation:

```sh
python3 scripts/check_viewer.py "$B024_ROOT"
python3 scripts/test_package_review.py
```

All17 PNGs are independently checked against the actual decoded raw tensor. Browser checks verify buttons/frame slider/local links and capture desktop/mobile screenshots; they do not establish continuous video perceptual quality. Reference and driver condition reconstructions use already saved decoded tensors, no extra VAE. Driving reconstruction retains native448x256, half source spatial resolution. Baseline is actual B-023 raw, not historical B-020/B-022 generated results.

Full 17-frame/30fps comparison and predeclared local0/8/16 are retained. No warp, interpolation, post-compositing or selective frames. CPU media phase total wall/peak was not separately instrumented.

The archive regression protects public files against private dedup exclusions. Final delivery additionally requires explicit expected members, CRC/all payload hashes, actual extraction plus extracted-payload hashes, and Mac/Spark byte identity; a structural ZIP check alone is insufficient.

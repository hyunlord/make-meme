# CPU review reproduction

Use the existing environment containing PyTorch/torchvision/Pillow and ffmpeg; no new packages are needed. `$B023_ROOT` is the private experiment directory and `$CPU_PYTHON` the existing CPU-capable interpreter. Do not run again over existing review outputs.

```sh
cd "$B023_ROOT"
"$CPU_PYTHON" -c 'from pathlib import Path; from scripts.build_comparison import export_raw; r=Path.cwd(); export_raw(r/"artifacts/raw_output.pt",r/"reports/comparison-replacement-raw",r/"reports/comparison-replacement-all17.png")'
"$CPU_PYTHON" scripts/build_comparison.py --target reports/comparison-inputs/source --baseline reports/comparison-inputs/baseline --replacement reports/comparison-replacement-raw --reference reports/comparison-inputs/reference.png --output reports/comparison-final
"$CPU_PYTHON" scripts/build_viewer.py .
```

On the existing Mac Chrome/websocket-client installation only:

```sh
python3 scripts/check_viewer.py "$B023_ROOT"
```

The browser check validates controls, local links and captures desktop/mobile screenshots. It does not establish perceptual temporal quality. Native 30fps/17-frame comparison, all17 frames and predeclared local0/8/16 are retained. Baseline must be the B-020 adapter-OFF raw sequence, not B-022 trained endpoints. No postprocessing modifies the generated output.

CPU media elapsed/peak memory were not instrumented as a separate phase; no GPU cost is attributed to these review scripts.

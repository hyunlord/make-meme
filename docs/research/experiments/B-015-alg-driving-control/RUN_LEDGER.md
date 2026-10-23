# B-015 execution ledger

Preregistered commit `a2847634d45d6860ea6c0d7d9c42d7dc18781b3f`. P0 reused immutable B013 LAB_STILL; PROBE1/S1/D1 completed, failures0/retries0. No new baseline, training or imagegen.

Actual sampler:40steps/88sequential forwards. Steps0–7 used u_orig→u_low→c_low; remaining32steps retained original c_orig→u_orig. Branch hash records identify already verified selected reference tensors; they are not per-forward GPU byte rehashes.

Final latent finite, exact readback, shape16×5×112×64, fileSHA `b5af6b859f1e634235f1a6354ccdc3ae22df938b54308f7b5e1fab4a8842cd20`. Raw finite3×17×896×512; MP4 verified17frames24fps (0.708333s), full ffmpeg decode PASS. Raw/MP4/final/filter hashes are in RUN_LEDGER.json. Technical validity is separate from visual quality.

Pair audit:4 driving leaves differ,12controls bit-exact; filtered reference values equal B014 MOV, while the new sidecar binds B013 STILL. Postrun149hash checks PASS. Eight model files retain prior full SHA plus fresh matching stat/mtime; no new65GB hash is claimed. Both owned units inactive/PID0, protected service unchanged and idle, swap0.

Runtime cutoff21:25UTC, task deadline22:00UTC. All GPU work finished; no continuation scheduled. Separate runtime measures and four-cell comparison are in MEASUREMENTS.json/.md.

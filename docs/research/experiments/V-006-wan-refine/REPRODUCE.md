# V-006 reproduction

Private absolute paths are kept in the execution manifests. The procedure below
does not authorize another generation, a restart, or a quality retry.

## Verified execution and last observation

- The work order, scene JSON, and PLAN were recorded before model execution.
  The selected official DiffSynth example defaults are Euler, 50 steps, shift 5,
  CFG 5, and expert boundary 0.875. Actual starting sigmas are
  0.7291666269302368 for W1-a and 0.859375 for W1-b; the equality stop was not triggered.
- `WEIGHTS.json` records the official low-noise model revision, original and
  converted shard hashes, and shared component identities. CPU conversion of
  all 1,095 tensors matched `original.to(torch.bfloat16)` bitwise. Originals are
  preserved. Bernini weights were not substituted.
- W1-a was launched under Spark-owned tmux and the guarded runner. Its measured
  first step was 44.2675 seconds; the setup-plus-50-step projection was
  2,247.2294 seconds, below the 3,600-second stop threshold.
- The last available W1-a observation was **41/50 scheduler steps**, with
  **84 attempted / 83 completed model calls**. SSH and network checks timed out
  during **2026-11-07 00:18–00:20 KST**. Subsequent remote worker state and output
  completion are **UNKNOWN**. Connection loss alone does not establish power loss,
  worker termination, or generation completion.
- W1-b has not been started. W2 is `NOT_SUPPORTED` under the requested combined
  input contract; see `W2_SUPPORT.md`. This is not a model quality failure.

The following procedure describes the frozen execution design. It must not be
read as a claim that the unobserved or downstream stages completed.

## Frozen execution procedure

1. Verify the original work order, scene JSON, input hashes, and weight hashes.
   Use only the converted bf16 transformer for inference, never the preserved
   fp32 original. Runtime configs `W1-a-runtime.json` and `W1-b-runtime.json`
   contain private paths and resolved scene values.
2. The private entry is `code/wan/wan_refine.py`. Public frozen copies are
   `code/wan_refine.py`, `code/v006runtime_config.py`, and
   `code/v006runtime_io.py`. The stage builder freezes converted weights, shared
   T5/VAE/tokenizer files, upstream code, inputs, and runtime configs.
3. Use the existing research Python, existing `run_guarded.py`, and matching
   `stages/v006-w1-a-cpu` stage. Before a heavy run, require a successful CPU
   receipt with `COMPLETE`, return code 0, and `normal_exit_recorded`.
4. The Spark-owned launcher command is
   `code/run_one_heavy.sh v006-w1-a CUTOFF_EPOCH`, with the recorded cutoff epoch
   substituted. It performs 180 seconds of external-work admission, cache drop,
   the 112 GiB startup check, and the inherited runtime guards. All model work
   is sequential; no second worker may start in parallel.
5. Project total execution time from the first actual step. A projection above
   3,600 seconds stops the run as `BLOCKED_TIME`, without a quality retry.
   The implementation requires atomic final-latent save and readback before
   decode, then retention of the 33 lossless PNGs, float tensor, and MP4.
   Their completion is not established by the last observation above.

## Downstream procedure, not yet verified as executed

After a generated-output receipt and normal exit are actually verified:

1. Run guarded SAM on the 33 RAW frames. Apply the private metric and composition
   configs using `v006_metrics.py`, `v006_composite.py`, and
   `v006_metrics_seams.py`. Prepare identity indices with
   `v006_metrics_embedding.py`, then run the inherited embedding worker under
   its own guard. Keep all inference sequential.
2. Deliver W1-a RAW plus both full-window and legs-only derivatives in an
   uncompressed intermediate viewer **before** W1-b. Only then run the declared
   W1-b stage if the original authorization, remaining budget, and guards allow it.
   Do not restart W1-a merely because its remote state cannot be observed.
3. Keep each output's `SAMPLE.json` private, link `parent_sample` to S2-s1, and
   preserve human labels as `PENDING`. Build the final package on Spark first,
   copy it to Mac, verify payload hashes, and test the actual browser viewer.
   No V-007 generation is scheduled.

## CPU checks actually run

The public-code pytest suite passed 14 tests at the pre-execution checkpoint.
The standalone W2 AST fixture separately passed its single-reference control and
expected two-reference mismatch on Spark without torch or model imports. Guard
verification covered 29 inherited tests plus four startup-threshold fixtures.
Spark's research Python does not include pytest; no package was installed.
Local ruff and basedpyright were unavailable and are not claimed as PASS.

## Evidence distinction

Source S2 RAW PNGs are decoded original-MP4 pixels, not pre-encoding RGB.
`LATENT_SHAPES.json` distinguishes observed Wan latent shapes from prior LTX
shapes derived from code. Neither browser playback nor successful ffmpeg decode
establishes continuous perceptual quality. Quality remains
`HUMAN_REVIEW_PENDING`, with temporal quality `UNVERIFIED`.

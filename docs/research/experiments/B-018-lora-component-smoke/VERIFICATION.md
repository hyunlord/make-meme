# B018 independent terminal review

Verdict: **PASS for COMPONENT_UPDATE_RELOAD_PASS within the registered one-component synthetic contract.** No blocking contradiction found. This review did not run GPU code, load checkpoint tensors, or repeat training. GPU observations below are independently reconciled saved runner evidence; my direct execution was the separate small CPU helper test suite.

## Actual evidence

- `execution-authorization.json` pins preregistration commit `2b562188cc0ad30cf822583d53a3d66babbd8e1e`, one worker, three updates, eight forwards, zero retries. `worker-attempt.json` is a write-once STARTED reservation, not a terminal status. Terminal result is in `result.json` and `pipeline-process.json`.
- All nine entries in `code-freeze.json` match current private code/config bytes. No post-execution numerical code change found.
- `result.json` reports exactly three optimizer updates and eight attempted/eight completed attention forwards. `updates.json` contains updates 1/2/3 only; every saved graph includes `FlashAttnVarlenFuncBackward`. The reviewed code calls backward before emitting each update, then checks finite gradients and completes the optimizer step. This supports actual FA2 backward, not availability alone.
- Both Q/V A gradient norms are zero at update 1; both B norms are positive. Both A gradients become positive at updates 2/3. All recorded adapter gradient and optimizer state dtypes are FP32. Every frozen-base gradient is required to be None by the executed checked code.
- Losses: 1.5443342924118042 → 1.5443276166915894 → 1.544281005859375. This small synthetic MSE reduction is not animal/video quality or Flow Matching evidence.
- CPU byte-level safetensors inspection independently confirms all four A/B payloads are FP32 and differ between initial and final files. Both initial B arrays contain all-zero bytes; initial A arrays do not. Each A shape is [4,5120], each B [5120,4], hence 81,920 trainable adapter parameters total.
- Initial and final adapter payload SHA256 match their schema sidecars. Labels are TEST_ONLY/NOT_FOR_INFERENCE; rank4/alpha4/dropout0 are recorded.
- Saved actual fixture x [1,36,5120] BF16 and target [1,36,5120] FP32 raw-byte hashes match result.json exactly. The CPU generator state after fixture creation is saved separately (5056 bytes). No animal media or condition cache participates.
- Selected checkpoint subset contains 10 tensors totaling 419,553,280 stored bytes (<1GiB). Runtime projection parameters are BF16; norm_q/norm_k parameters remain FP32. Stored FP32 and runtime-cast hashes are distinct concepts.
- Original runtime base hashes match wrapped hashes after q/v name normalization; fresh wrapped hashes equal final frozen wrapped hashes. Executed code checks frozen hashes after each update and again after reload/OFF. Source checkpoint size/mtime and selected in-memory payload hashes are unchanged. This is not a fresh whole-checkpoint 65GB posthash.
- Bzero/baseline max error, fresh reload max error and adapter-OFF max error are all 0.0, stricter than the registered atol=rtol=1e-3. No extra forward was added to obtain these measurements.

## Resources and cleanup

- Worker elapsed: 7.972472899942659 seconds. This differs from supervisor wall time and systemd service runtime; do not conflate them.
- CUDA peak allocated: 297,412,096 bytes. Observed cgroup peak: 1,729,818,624 bytes. These are different scopes and must not be added as independent CPU/GPU capacities on unified memory.
- Ten sampled guard records: minimum MemAvailable 93,343,227,904 bytes; swap zero. Recorded cgroup OOM/oom_kill events zero. Sampling does not claim every instantaneous system state was observed.
- Guard service exited normally with return code 0. `pipeline-process.json` shows inactive/MainPID0; `postrun-check.json` confirms both owned services inactive/MainPID0, queue idle, protected process identity preserved, code/source preservation checks PASS.

## Remaining limits

- My helper CPU tests: seven PASS, Ruff PASS; type check 0 errors/19 warnings, NOT_CLEAN, retained in helper reports. This is separate from actual Spark FA2 evidence and runner-wide type diagnostics.
- One final self-attention module with 36 synthetic tokens does not establish full 40-block/17-frame training feasibility, useful data pairing, identity/pose disentanglement, generalization, or output quality.
- FULL_MODEL_TRAINING, VIDEO_QUALITY and IDENTITY_POSE_DISENTANGLEMENT remain NOT_RUN. B017 rights/data gaps are unchanged.
- Upstream deprecated-autocast warnings remain in the successful execution log; no fallback backend, dependency replacement, or additional retry was used.

## Postrun runner-wide static check

Root's saved `runner-typecheck.log` reports **20 errors / 135 warnings: NOT_CLEAN** across the wider runner surface, including dynamic imports, nn.Module attributes, dictionary unions, AST boundaries and possible-unbound analysis. The helper-only 0 errors/19 warnings is not the overall runner status. These static findings remain unresolved in the frozen executed code; no suppression, code rewrite, extra GPU run or retry was performed. Actual component execution PASS and runner static NOT_CLEAN are separate findings. This review does not claim clean static typing or infer a kernel failure from these diagnostics.

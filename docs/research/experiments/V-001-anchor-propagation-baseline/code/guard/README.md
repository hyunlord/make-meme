# V-001 scoped guard copy

Four existing C-013 resume guard files are copied here. Common files are untouched.
`V001_POLICY.diff` is the complete policy diff; `PROVENANCE.json` binds old/new hashes.

## Invocation

Use the existing C-001 `run_guarded.py` adapter and C-012 `make_stage.py` with private
`C012_STAGE_SETTINGS` pointing `guard` at this directory. Both CPU and heavy routes
must resolve this same directory and freeze these actual four files. Each new stage
uses its own new memory state file, preserving historical C states. The shared research
lock, CPU route receipt, absolute path validation and normal-exit verification remain.
Service policy binding: `attempt_id=C001_V001_APPROVED_01`. The C-001 adapter uses
its established prefix check; direct supervisor policy loading requires this exact ID.
Keep existing OPTIONAL_EXPECTED_ABSENT mode and stage/boot/deadline/logical hashes.

CPU check: `python3 -m unittest discover -s code/guard -p test_v001.py` from experiment root.
No model imports, remote execution, installations or GPU work occurred in these checks.

## V-only changes

- Read mandatory PSI full avg10 and global vmstat oom_kill; missing/nonfinite counters fail closed.
- Persist contiguous pressure timers: available<12GiB for30s; PSI full avg10>25 for60s.
- Reset a duration only on recovery; never reset baseline swap/counters while running.
- Existing swap and <1GiB cumulative swap-out warn; cumulative >=1GiB stops because the
  explicit exception only authorizes values below1GiB. PSI>10 warns while observation continues.
- Startup still needs10s observation. Active severe pressure stays incomplete until recovery
  or its stop threshold. Startup can observe up to70s. Removed hidden72GiB start threshold.
- Worker cap remains min(64GiB, initial available minus12GiB); swapmax0, worker OOM,
  task cap, identity, externalGPU checks and own-worker-only cleanup remain.
- Existing idle service is accepted only when its real queue response is valid and empty.
  Busy queue, errors, unexpected refused-but-process-present state and unknownGPU still block.

12 CPU tests cover duration boundaries, restored state, recovery, strict thresholds,
startup observation, >=1GiB boundary, worker/global OOM, worker swap, queue/externalGPU,
observation gaps/errors/NaN. Actual systemd and service endpoint integration remain for
parent execution. Existing legacy typing/style is preserved rather than refactored.

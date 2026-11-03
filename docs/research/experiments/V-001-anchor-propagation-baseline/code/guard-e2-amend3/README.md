# V-001 E2 amendment 3 guard

Scope: only the user-approved E2 worker memory increase. E1 keeps `code/guard` and its64GiB cap.
The original guard files remain byte-identical; `ORIGINAL_HASHES.json` and a CPU test verify this.

Changes relative to V-001 guard:
- Startup requires MemAvailable >=112GiB (112GiB passes; one byte below blocks).
- Worker MemoryMax is min(100GiB, observed available minus12GiB). With admitted112GiB this is100GiB.
- MemoryHigh remains cap minus2GiB. MemorySwapMax=0 remains.
- 10-second startup observation, all runtime30/60-second pressure thresholds, OOM,
  services/external GPU/observation failures, deadline and exit checks are unchanged.
- Budget baseline/timers remain unchanged and cannot be reset to hide growth.

Use the existing C-001 adapter/C-012 stage builder with `guard` pointing at this directory
for BOTH E2 CPU and heavy stages. Freeze all four actual files from this directory after
final stage config changes. A CPU route receipt for the original guard is not valid for
this route, because the route hash includes guard_code. Generate/verify a fresh CPU stage.
The adapter's optional preflight-only check does not run `start_decision`; final admission
is always the supervisor's10-second observation plus112GiB gate. Do not treat preflight
alone as permission to load a model.

CPU checks (from experiment root):
```
python3 -m unittest discover -s code/guard-e2-amend3 -p 'test_*.py'
python3 -m unittest discover -s code/guard -p 'test_v001.py'
```
19 amended-copy tests and12 unchanged-original tests passed. The amended copy updates the
old32GiB admission expectation to112GiB; all other original behavioral tests are unchanged.
No SSH, GPU, model imports, installations or commits were performed by this preparation.
Supervisor now samples registered worker /proc status VmHWM each observation and writes
`peak_worker_rss_bytes_observed`, explicitly a sampled lower bound if killed before the next
sample. This survives worker OOM/guard termination and is distinct from final E2 entry
ru_maxrss. `min_available_bytes_observed` includes startup, runtime and final observations.
Disappeared/zombie processes yield null RSS; malformed live status or permission failure
remains an observation failure. No additional process or monitoring framework was introduced.

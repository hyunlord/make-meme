# V-001 E2 amendment 4 scoped execution copy

Only runtime change versus `guard-e2-amend3`: the supervisor's systemd-run command sets
`MemoryHigh={cap}` instead of `MemoryHigh={cap-2GiB}`. Cap remains100GiB, admission remains
112GiB, and all OOM/PSI/headroom/service/GPU/observation/exit checks are byte-identical.
The property is set by `supervisor.py`, not by the C-001 adapter. No common or historical
frozen runtime file was edited. User amendment4 authorizes a new E2 attempt under this
contract; it does not rewrite the previous SYSTEM_PSI_FULL_PRESSURE result.

## Application and freeze

Use the unchanged C-001 adapter and existing stage builder. Point the amendment4 private
stage settings `guard` field to the deployed `code/guard-e2-amend4` directory. Generate
new CPU and heavy stages using this same path; freeze all four actual runtime files.
The CPU route hash includes guard_code, so earlier CPU receipts cannot substitute for
this route. Confirm both generated config files use the new guard path and both freeze
maps contain these exact hashes before running either stage. The adapter's preflight-only
check does not replace the actual supervisor's10-second observation and112GiB admission.
E1 continues to use its existing64GiB guard copy.

## Evidence

CPU checks from experiment root:
```
python3 -m unittest discover -s code/guard-e2-amend4 -p 'test_*.py'
python3 -m unittest discover -s code/guard-e2-amend3 -p 'test_*.py'
```
22 amendment4 and19 unchanged amendment3 tests passed. The added test evaluates only the
MemoryHigh/MemoryMax expressions from the actual local systemd command AST, without
launching systemd, to check both properties are107374182400 bytes. Other tests prove the
one-token runtime change and unchanged historical file hashes. Compileall and diff check
passed. The zero-context audit diff needs `--unidiff-zero` if applied; it is not an execution step.

Inherited observations retain worker RSS high-water samples, cgroup memory.peak,
memory.high/max values and high events, PSI full avg10, and minimum available memory.
RSS summary remains a sampled lower bound if guard termination precedes another sample.
No SSH, GPU, model imports, installations or commits occurred during this preparation.
Actual systemd property verification remains required in parent execution evidence.

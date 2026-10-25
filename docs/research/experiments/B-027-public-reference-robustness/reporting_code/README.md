# CPU execution evidence summary

Run the existing Python with `summarize.py PRIVATE_EXPERIMENT_ROOT`. It reads the fixed animal/human/vehicle stage reports and writes only `reports/execution_summary.json` beneath that root. Re-run after stages finish; snapshot hashes of live logs naturally change. No model imports, GPU calls, dependency installation, or execution orchestration occurs.

Run `python3 test_summary.py` for CPU fixtures covering proc/cgroup units, missing and partial-stage receipts, partial JSONL, independent memory accounts and exclusion of commands/traceback paths. Initial fixture run failed on the unimplemented parser; the implemented version passes.

`RUNNING` means an attempt exists without a terminal receipt, not an independent process-liveness claim. `NOT_RUN` means no worker attempt or launch receipt. Pre-worker launch failures are counted separately from worker and sampler attempts. `INCOMPLETE_EXIT` is not success. Complete duration comes from supervisor start/finish; phase timestamps are also retained.

Memory is in bytes, with system MemAvailable minimum, swap maximum, process RSS/RssAnon/RssFile maxima, cgroup current/peak/anon/file and event counters, CUDA allocated/reserved/peak recorded separately. These overlapping accounts are never summed. RSS is the maximum observed individual process, not a sum across workers. Missing observations stay absent, not zero. Live malformed/incomplete JSONL rows are counted. Cgroup event maxima are observed cumulative counters, not an inferred cause of failure.

Only allowlisted summary fields, relative artifact names and hashes are emitted. Raw command lines, absolute paths and traceback text are not copied. The generated JSON is private evidence; do not add it or raw reports to public GitHub. This summary makes no visual or temporal acceptance claim.

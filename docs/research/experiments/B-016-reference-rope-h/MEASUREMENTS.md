# B-016 runtime measurements

All values below are measured technical execution; no visual quality conclusion.

| Cell | S guard sec | Worker sec | Sampler sec | CUDA peak GiB | Cgroup peak GiB | High | OOM | Min available GiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CFG_MOV_H0 | 1181.602 | 1179.287 | 1020.890 | 33.832 | 59.371 | 4242 | 0 | 46.304 |
| CFG_MOV_H120 | 1057.032 | 1054.303 | 965.419 | 33.846 | 62.005 | 3545 | 0 | 52.605 |

Identical guard finished-started and final worker phase elapsed definitions. Timing is observational, not a controlled performance benchmark. Both runs use40steps/80forwards; no isolated speed claim.

System available memory, CUDA allocator allocated/reserved/peak, process RSS/HWM and cgroup charged memory are distinct. High events are reclaim pressure, not OOM.

Previous full SHA plus fresh stat/mtime; no fresh full-weight hash.

Effective S cgroup caps differed: historical B013 H0=65,888,763,904 bytes; B016 H120=68,719,476,736 bytes. B016 retains the B014/B015 guard policy unchanged apart from experiment units/deadline. The verified guard resolves cap=min(64 GiB, launch MemAvailable−24 GiB), so an unchanged policy does not imply an identical effective cap. The timing table is observational and is not a retrospective same-resource-configuration performance comparison.

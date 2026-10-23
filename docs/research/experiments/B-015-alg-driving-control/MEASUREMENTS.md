# B-015 runtime measurements

All values below are measured technical execution; no visual quality conclusion.

| Cell | S guard sec | Worker sec | Sampler sec | CUDA peak GiB | Cgroup peak GiB | High | OOM | Min available GiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CFG_MOV | 1181.602 | 1179.287 | 1020.890 | 33.832 | 59.371 | 4242 | 0 | 46.304 |
| CFG_STILL | 1149.802 | 1146.788 | 1013.345 | 33.832 | 58.060 | 3670 | 0 | 46.139 |
| ALG_MOV | 1266.471 | 1262.838 | 1116.131 | 33.847 | 58.619 | 3518 | 0 | 46.507 |
| ALG_STILL | 1264.928 | 1261.937 | 1119.280 | 33.847 | 56.806 | 4674 | 0 | 46.226 |

Identical guard finished-started and final worker phase elapsed definitions. Timing is observational, not a controlled performance benchmark. 80 versus88 calls is exactly10% NFE, not10% runtime or quality improvement.

System available memory, CUDA allocator allocated/reserved/peak, process RSS/HWM and cgroup charged memory are distinct. High events are reclaim pressure, not OOM.

Previous full SHA plus fresh stat/mtime; no fresh full-weight hash.

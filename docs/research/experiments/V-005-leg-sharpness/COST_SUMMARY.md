# V005 verified cost snapshot

Observed resources are distinct: receipt peak RSS is process ru_maxrss, cgroup includes charged page cache, CUDA is allocator memory, MemAvailable is host-wide. Hardware log has no header; its 12-column schema was verified against the actual logger script. Discrete samples are not continuous extrema.

| Run | Pipeline seconds | Steps / calls | RSS GiB | Cgroup sampled peak GiB | CUDA allocated / reserved GiB | Host min available GiB | PSI full avg10 max | HW samples | GPU temperature max C |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R1-a | 81.614 | 2 / 2 | 42.282 | 71.183 | 39.583 / 39.670 | 71.274 | 0.0 | 18 | 64.0 |
| R1-b | 82.124 | 2 / 2 | 42.244 | 71.091 | 39.583 / 39.670 | 71.177 | 0.0 | 18 | 66.0 |
| R3-s1 | 136.592 | 11 / 11 | 42.249 | 71.077 | 39.583 / 39.785 | 71.136 | 0.0 | 30 | 74.0 |
| R3-s2 | 142.045 | 11 / 11 | 42.249 | 71.105 | 39.583 / 39.785 | 71.181 | 0.0 | 30 | 75.0 |

Four completed generations: 26 scheduler steps and 26 denoiser calls. Four imagegen calls, no repairs; training0. R2-s1/s2 remain NOT_SUPPORTED. Pipeline seconds exclude external admission and CPU packaging. All listed generations have COMPLETE supervisor, zero worker return code and normal exit; no NVRM events observed. No further generation is planned. Output embedding and final processing are tracked separately; no quality ranking is inferred.

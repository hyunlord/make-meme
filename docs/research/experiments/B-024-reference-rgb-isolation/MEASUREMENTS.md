# B-024 실제 비용과 실행 상태

서로 다른 메모리 회계를 더하지 않는다. peak는 allocator/cgroup 기록 또는 주기적 RSS 표본이며 동일 시점의 물리 사용량이 아니다.

| 단계 | worker 초 | CUDA peak GiB | cgroup peak GiB | sampled RSS peak GiB | 최소 MemAvailable GiB |
|---|---:|---:|---:|---:|---:|
| REF | 9.40 | 3.78 | 4.42 | 1.81 | 82.67 |
| PROBE | 3.15 | 0.02 | 0.59 | 0.82 | 88.76 |
| S | 1074.82 | 33.85 | 62.02 | 66.91 | 52.79 |
| D | 13.03 | 8.91 | 2.43 | 1.58 | 75.46 |

REF에는 기존reference/driving복원각1,원본/중립VAE+CLIP각1세트와로딩/해제가포함된다. VAE와CLIP는순차적재했고T5/DiT는없다. S의CPUloader85.07초,device이동15.47초,첫forward13.75초,샘플링(device이동포함)986.33초다. 첫forward종료의workerelapsed117.74초를단일forward시간으로쓰지않는다. D의실제VAEdecode6.75초,raw저장0.71초,MP4인코딩0.63초다.

실제 REF/PROBE/S/D 각1회,40step/80forward,재시도0·관측forward0·학습0·추가설치/다운로드0. 모든단계service_exit/returncode0이며출력·counter·finite·shape도별도로확인했다.

S cgroup.high=3031로reclaim pressure가관측됐다. cgroup.max/oom/oom_kill=0,swap0,headroom가드종료0이다. 따라서모든메모리이벤트가0이었다고보고하지않는다. 기존72GiB시작조건·24GiB실행가드는변경하지않았다. 자체pipeline/watchdog는inactive/MainPID0이며보호서비스는그대로실행중이다.

세부시간·raw카운터·파일SHA는[runtime-summary.json](runtime-summary.json)에있다.65GB기반weights는기존검증계보를재사용했으며이번전체재해시를했다고주장하지않는다.

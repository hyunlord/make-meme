# B-025 실측

[실제 stage 요약](evidence/RUNTIME_SUMMARY.json). 모든 수치는 이번 실행의 관측이며 다른 GPU 또는 긴 영상으로 외삽하지 않는다. GiB=2^30 bytes.

| 단계 | worker 초 | 실제 연산 |
|---|---:|---|
| ENC | 118.26 | common T5 positive1, IG VAE1/CLIP1, Lab encoder0 |
| LAB S | 1032.16 |40step80forward; CPU weight load43.89초, device move20.43초, sampling span964.45초 |
| IG S | 1034.79 |40step80forward; CPU weight load46.95초, device move19.52초, sampling span964.81초 |
| LAB D |13.24| VAE decode7.11초, raw저장0.74초, MP4인코딩0.79초 |
| IG D |12.68| VAE decode6.73초, raw저장0.69초, MP4인코딩0.76초 |

S별 CUDA peak allocated36,342,951,936B, observed reserved peak36,391,878,656B. cgroup peak는 LAB66,578,178,048B / IG66,577,809,408B다. sampled RSS peak는66,587,955,200B /68,569,989,120B, 시스템 최소 MemAvailable57,036,619,776B /56,130,777,088B다. allocator/RSS/cgroup/system 회계는 동일 의미가 아니며 합계로 총 사용량을 만들지 않는다. phase sampling으로 놓친 transient peak 가능성도 구분한다.

cgroup.high LAB6216/IG6009, max/OOM/oom_kill0, swap0. guard reason은 모든 stage service_exit, returncode0, 종료 MainPID0이다. 실제 결과·counter·finite·hash 확인을 함께 사용했으며 returncode만으로 성공 판정하지 않았다. 다른 서비스는 유지했고 가드를 낮추지 않았다.

새 sampler2회, 총160forward80step, decode2회, probe2회, 공통ENC1회. 자동재시도·관측추가forward·학습·다운로드·설치0. static review와 packaging은 별도 CPU 작업이다. 전체4시간 상한 안에서 종료하고 추가 실험을 예약하지 않는다.

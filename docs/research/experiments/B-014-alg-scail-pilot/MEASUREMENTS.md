# B-014 실제 실행 측정

PROBE·S·D 각1회 정상 완료, P0회 재사용. S40step·88forward, 실패0·재시도0. 영상 품질 판정은 별도다.

| 단계 | guard(s) | worker(s) | 최소 MemAvailable(GiB) | CUDA peak allocated(GiB) | cgroup high | OOM |
|---|---:|---:|---:|---:|---:|---:|
| PROBE | 5.074 | 3.566 | 83.076 | 0.017 | 0 | 0 |
| S | 1266.471 | 1262.838 | 46.507 | 33.847 | 3518 | 0 |
| D | 16.184 | 13.541 | 70.384 | 8.908 | 0 | 0 |

B013 LAB_MOV S의 동일 정의 실측은 guard 1181.602s / worker 1179.287s다. 이번 S는 guard 1266.471s / worker 1262.838s다. NFE80→88(+10%)는 walltime 증가율을 보장하지 않으며 파일 캐시·자원 상태와 trace 관측 비용을 통제한 성능 실험이 아니다.

전체 sampled swap0, cgroup OOM0. high는 회수 압력 이벤트이고 OOM으로 취급하지 않는다. 통합 메모리 가용량·CUDA allocator·RSS·cgroup을 합산하거나 동등한 값으로 해석하지 않는다. 모델은 이전 전체SHA와 새 stat/mtime 대조이며 전체 가중치를 다시 해시하지 않았다. 자세한 수치는 MEASUREMENTS.json을 따른다.

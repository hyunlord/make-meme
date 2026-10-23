# 실제 실행 계측

LAB_MOV와 LAB_STILL은 각각 P/PROBE/S/D 1회, sampler 1회씩 정상 종료했다. 실행 완료는 영상 품질 수용과 별개다.

| 조건 | 단계 | guard 전체 초 | worker 단계 초 | 최소 가용 GiB | CUDA peak allocated GiB | cgroup peak GiB | high | OOM |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LAB_MOV | P | 148.220 | 146.587 | 65.969 | 4.024 | 29.127 | 0 | 0 |
| LAB_MOV | PROBE | 7.076 | 4.691 | 83.813 | 0.017 | 0.661 | 0 | 0 |
| LAB_MOV | S | 1181.602 | 1179.287 | 46.304 | 33.832 | 59.371 | 4242 | 0 |
| LAB_MOV | D | 16.198 | 13.495 | 70.368 | 8.908 | 2.088 | 0 | 0 |
| LAB_STILL | P | 112.067 | 109.513 | 63.926 | 4.024 | 23.804 | 0 | 0 |
| LAB_STILL | PROBE | 6.075 | 3.620 | 82.665 | 0.017 | 0.599 | 0 | 0 |
| LAB_STILL | S | 1149.802 | 1146.788 | 46.139 | 33.832 | 58.060 | 3670 | 0 |
| LAB_STILL | D | 16.219 | 13.506 | 70.225 | 8.908 | 2.086 | 0 | 0 |

첫 P 시작부터 마지막 D 종료까지 2921.784초. 전체 최소 시스템 가용 46.139GiB, swap 0. 두 S 각각 40 step/80 forward, raw finite [3,17,896,512], 17프레임·24fps.

시스템 가용 메모리, cgroup 청구량, 프로세스 RSS/HWM, CUDA allocated/reserved/peak는 별도 관측값이며 더하지 않는다. JSON에 각 값을 분리했다. cgroup high는 회수/스로틀 이벤트로 OOM과 다르다. worker 시간은 마지막 phase 기록, guard 시간은 프로세스 시작/종료 포함이다. CUDA 값은 기록된 phase에서 관측한 allocator 값이며 전체 모델의 일반적 메모리 요구량으로 외삽하지 않는다.

양쪽 owned unit은 inactive/MainPID0이며 기존 Comfy만 남고 queue가 비어 있다. 대형 가중치는 prior full SHA와 이번 fresh size/mtime로 재사용 검증했다. 이번에 65GB 전체 SHA를 재계산한 것으로 표현하지 않는다. 코드·config·입력·upstream은 종료 후 864개 SHA 검사를 통과했다.

# B-023 실측

회계가 다른 시스템 가용 메모리, RSS, cgroup, CUDA allocator를 합산하지 않는다. 아래 각 peak는 서로 다른 시점일 수 있다. cgroup은 controller가 보는 메모리이며 전체 통합 메모리의 별도 합계가 아니다.

| 단계 | worker wall(s) | 최소 MemAvailable(GiB) | cgroup peak(GiB) | CUDA peak allocated(GiB) | max observed reserved(GiB) |
|---|---:|---:|---:|---:|---:|
| PROBE | 5.07 | 89.09 | 0.59 | 0.02 | 0.03 |
| S | 1092.50 | 52.68 | 62.00 | 33.83 | 33.89 |
| D | 15.17 | 75.78 | 2.16 | 8.91 | 11.56 |

S 적재94.61초, sampler loop976.40초. D VAE 적재0.80초, decode6.72초, raw 저장0.70초, MP4 인코딩0.79초. worker wall 합계1112.75초(약18.55분)는 실제 준비·검토 전체 wall과 다르다. P 재인코딩0이며 CPU 파생/사전검토는 착수16:54UTC부터 S 시작 전까지의 작업에 포함된다.

S 최대 관측 RSS65.32GiB, RssAnon31.45GiB, RssFile43.23GiB는 각 peak이므로 서로 합산하지 않는다. cgroup memory.high3197회, max/oom/oom_kill0. high는 기록상 reclaim/throttle 이벤트이며 OOM이나 누수 확정값이 아니다. 모든 stage swap0, 기존72GiB시작/24GiBheadroom 유지. 종료 MemAvailable89.29GiB, 소유 worker 없음.

final latent SHA256 `9b325fef3e4dfebe4622414569bce28e6b6c517d817414d25e08b0f05c79ee8b`
raw SHA256 `51045949c0ab0c02ebe3bd18e646185e353c173c2a89e40e8db7a2b8a9736c2f`
MP4 SHA256 `82ff53052db0146d35aec1a9b1f76f74b5f38c79b2e8192257cdd6b4125c529e`

private 원시 runtime-summary/terminal/mode/guard/phase JSON을 보존했다. 7개 runtime artifact의 Mac/Spark SHA 동일성 및 독립 CPU raw/latent finite/shape 검증을 수행했다. 전체 영상 품질 PASS와 구분한다.

CPU 검토자료 생성·브라우저 확인의 개별 elapsed/peak는 별도 계측하지 않아 NOT_MEASURED다. 착수16:54UTC부터 raw/비교의 정적 검토·문서 작성17:28UTC까지 약34분 경과는 전체 작업의 중간 wall 관측이며 GPU 시간이나 최종 packaging 시간을 뜻하지 않는다.

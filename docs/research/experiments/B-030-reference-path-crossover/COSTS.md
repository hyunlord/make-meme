# B-030 실제 비용과 사용량

새 full sampler 4/4와 decode 4/4가 완료됐다. 각 sampler40step·80forward, 합계160step·320forward다. PROBE4회, encoder/학습/update/새설치/다운로드/재시도0회. 기존 대각4출력은 재생성하지 않았다.

| 과제·셀 | PROBE(s) | S load+sample(s) | D load+decode+encode(s) | CUDA peak allocated(GiB) | 최저 MemAvailable(GiB) |
|---|---:|---:|---:|---:|---:|
| human Y12 | 8.09 | 1017.67 | 16.22 | 33.847 | 53.316 |
| human Y21 | 5.07 | 998.66 | 15.24 | 33.847 | 52.911 |
| vehicle Y12 | 5.08 | 1001.06 | 15.23 | 33.847 | 52.971 |
| vehicle Y21 | 5.07 | 997.82 | 15.23 | 33.847 | 53.382 |

순차 PROBE→S→D 전체 실행 wall time: **68.37분**. 시작 `2026-10-26T08:29:42.182615+00:00`, 종료 `2026-10-26T09:38:04.228458+00:00`. 각 stage 시간 합계 68.34분이며 실제 영상 샘플링만의 시간이 아니라 모델 로딩·조건 복원·저장·decode·MP4 인코딩을 포함한다.

전체 관측 CUDA peak allocated 33.847GiB, CUDA max reserved 33.893GiB, cgroup peak 62.585GiB, 관측 RSS max 88.312GiB. 서로 다른 회계이므로 합산하지 않는다. 실행 watchdog의 최저 MemAvailable 52.911GiB, swap 최대0, cgroup OOM event0.24GiB headroom과 시작72GiB 조건을 낮추지 않았다.

`memory.high` 이벤트는 일부 stage에서 관측됐고 최대 누적값은6580이다. OOM0을 모든 메모리 압력 이벤트0으로 해석하지 않는다. 가드 임계값을 낮추거나 해당 기록을 삭제하지 않았으며 실제 guard 종료는 없었다.

준비는 기존cache2leaf교체와6CPU fixture검사이며 GPU준비인코딩0회다. 실행 전 준비는 약10분 이내였다. 시각검토·문서화·ZIP/전송 시간은 위68분 실행시간에 포함되지 않으며 최종 전달시각까지의 작업시간과 구분한다.

네 case의 PROBE/S/D 모든 process receipt가 `service_exit`,returncode0,MainPID0이며 개별 result COMPLETED를 함께 확인했다. 마지막 stage 후 두 자체systemd unit은 inactive/MainPID0, 시스템 가용메모리는 약89GiB·swap0으로 회복했다. 기존 다른 서비스는 종료하지 않았다.

Watchdog의 ExecStopPost는 이미 종료·회수된 own pipeline unit에 stop을 요청해 `Unit ... not loaded` 메시지를 남겼다. 각 pipeline의 실제 성공receipt·최종latent·MP4·counter를 확인했으며 이 메시지를 추가실패나 재시도근거로 쓰지 않는다. 공식upstream deprecation FutureWarning도 보존했다.

원시 측정과 출력 SHA256/크기는 [MEASUREMENTS.json](MEASUREMENTS.json)에 공개 경로 없이 기록했다. 전체 raw log/resource trace는 비공개 산출물에 둔다. 기술적 출력 성공과 영상의 외형·동작 성공은 별도 판정이다.

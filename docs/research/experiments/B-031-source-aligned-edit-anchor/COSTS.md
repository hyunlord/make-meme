# B-031 비용과 자원

전체 비용은 이미지 모델 확보·로딩·실패한 앵커·수동 support·영상 전이를 모두 포함한다. 영상 한 건의 sampler 시간만으로 효율 개선을 주장하지 않는다. 아래 Qwen 값은 [실측 JSON](ENV_RUNTIME_SUMMARY.json), SCAIL은 실제 단계 receipt에서 집계했다. 최종 패키징·전송 종료 시각은 DELIVERY 기록에 남긴다.

## 이미지 모델 확보와 실행

| 항목 | 실제 값 / 한계 |
|---|---|
| 공식 가중치·필수 파일 | 35개,57,720,463,453bytes(53.756GiB), pinned revision 전체 해시 PASS |
| 다운로드 문제 | Xet 쓰기 정체 후 자체 다운로드 unit만 종료, 같은 revision HTTP transport fallback1회. 원인 확정하지 않음 |
| 보존 incomplete | 13,211,501,446bytes. 전체 모델 폴더70,931,975,386bytes(약66.06GiB) |
| 실제 누적 네트워크 전송량 | UNKNOWN. 파일 payload를 wire retransmission 계측으로 부르지 않음 |
| 전체 파일 해시 검증 | CPU streaming68.883초, 모델 적재 아님 |
| 새 패키지 설치 / 학습 / 외부 생성 | 모두0 |
| Qwen worker wall-clock | 2,598.925초(43.315분), 로딩·6개 호출·기록 포함 |
| 6개 pipeline 호출 합계 | 2,304.272초(38.405분), 각379.340~389.980초 |
| 실제 생성 연산 | 6시도/6기술완료, 각40step·80forward, 합480forward, 재시도0 |
| CPU meta/mmap 로딩 | 1.079초. 이후 실제 GPU 이동 비용과 별개 |
| GPU 이동 | text encoder78.269초,VAE1.283초,transformer206.223초 |
| 수동 차량 support | 228.29초, 원래 draft와 수정 계보 보존 |

이미지 출력의 기술 완료6개는 적합한 앵커6개를 뜻하지 않는다. animal/human R1은 참조 자세를 따라 영상용으로 부적합했고, vehicle R1만 영상 단계로 선정했다. R2 세 개도 전부 평가·보존했다.

## 메모리 회계

- Qwen 실제 parameter bytes 합57,698,920,550(약53.74GiB). 모델 파일 크기나 전체 peak와 같지 않다.
- CUDA peak allocated60,057,443,328bytes(55.933GiB), peak reserved63,206,064,128bytes(58.865GiB).
- 시스템 MemAvailable 표본 최소27,847,270,400bytes(25.935GiB), swap 사용0. 24GiB headroom을 낮추지 않았다. 표본 최소는 연속적인 물리 peak 계측이 아니다.
- process RSS 표본 최대10,952,196,096bytes, cgroup peak10,915,954,688bytes; cgroup high/max/OOM event0. CUDA·RSS·cgroup·시스템 값을 합산하지 않는다. cgroup64GiB 제한만으로 GPU 통합 메모리가 전부 계측됐다고 보지 않는다.
- `pipeline_released`라는 runtime phase 이름과 달리 `del`/`empty_cache` 뒤에도 CUDA allocated40,917,650,944bytes가 남았다. 정확한 잔존 참조 원인은 UNKNOWN. 추가 수명 감사로 범위를 확대하지 않았다.
- **실제 프로세스 종료** 후 자체 Qwen pipeline/watchdog PID0·inactive와 MemAvailable96,412,590,080bytes 회복을 따로 확인한 뒤 SCAIL로 넘겼다. 두 모델의 동시 상주는 없었다.

Transformers의 rope_parameters/mrope_section 경고와 이미 종료된 자체 unit을 stop하려던 경고는 raw log에 보존했다. 실제6회 실행 완료가 다른 버전과의 수치·의미 동등성을 입증하지 않는다. 기존 SCAIL/ComfyUI 환경과 타 프로세스는 변경하지 않았다.

## 영상과 전체 wall-clock

Vehicle R1 ENC9.103초 / PROBE5.079초 / S1003.427초 / D15.197초로 모두 완료했다. 신규 sampler1회·40step80forward·decode1회, 재시도0이다. S CUDA peak allocated33.847GiB, cgroup peak62.019GiB, 최소 시스템 가용50.684GiB, swap0이다. 모든 자체 GPU worker 종료 뒤 가용94,288,988KiB 회복을 확인했다. Qwen과 SCAIL 회계를 합산해 peak라고 부르지 않는다.

이미지 worker와 영상 네 단계의 wall-clock 합은3631.731초(60.529분)다. 다운로드·입력/코드 준비·검토·수동 작업·패키징 비용은 이 합 밖이며, 전체 elapsed는 최종 DELIVERY에서 시작 시각과 종료 시각으로 계산한다. 시작2026-10-26 14:46:41UTC, hard deadline20:46:41UTC, heavy cutoff20:16:41UTC를 유지한다.

최종 양 호스트 ZIP 검증까지 전체110.74분(6644.35초)이 걸렸다. 이는 다운로드·준비·검토·패키징·전송을 포함하며 [DELIVERY](DELIVERY.md)의 실제 UTC 경계에서 계산했다. 이후 전달 영수증 Git 동기화는 별도 마감 작업이다.

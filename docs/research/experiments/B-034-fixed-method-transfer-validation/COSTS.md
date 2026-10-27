# B-034 실제 비용과 미실행 비용

| 실행 | 실제 wall | 결과 |
|---|---:|---|
| Qwen guarded worker 전체 |1065.507초,17.76분 | 두 앵커 완료; 로딩·두 생성·종료 포함 |
| 위 worker 중 초기 CPU/device 이동 |270.134초 | 전체에 이미 포함, 중복 합산 금지 |
| 차량 image 호출 |390.525초 |40step/80forward |
| 인물 image 호출 |398.567초 |40step/80forward, 앵커 부적합 비용도 포함 |
| 차량 ENC |68.671초 | 공식 조건과 full-resolution source encode1 |
| 차량 BASE_S |1004.594초,16.74분 |40step/80forward final latent 저장; 종료 가드 BLOCKED |
| 차량 A0 수동 support |42.820초 | coarse agent polygon, 독립 인간 GT 아님 |
| BASE target support / E / M |0, NOT_RUN | 디코딩된 BASE가 없어 작성하지 않음 |
| source 브라우저 preview 파생 인코딩2 |0.379초 합계 | 실제 색상 오류를 피한 PNG 기반 새 preview; 원본 MP4 불변 |

Qwen+ENC+BASE의 guarded worker wall 합은 **2138.772초(35.65분)**이다. 이는 입력 선정·코딩·주석·검토·문서·패키징·전송을 포함한 총 프로젝트 wall이 아니다. 전체 착수의 정밀 timestamp가 없어 계획의01:15UTC는 보수적 예산 기준이며 실측 시작으로 가장하지 않는다. 이 작업에서 직접 관측한 최초 clock은01:24:33UTC다. 최종 archive 검증 시각/전송시간은 비공개 delivery receipt로 별도 보존한다. 준비·검토 중 agent 대기 시간을 GPU kernel 시간으로 쓰지 않는다.

## 메모리 회계

| 단계 | 최소 OS MemAvailable GiB | peak CUDA allocated GiB | 관측 CUDA reserved peak GiB | peak cgroup GiB | RSS HWM/관측 peak GiB |
|---|---:|---:|---:|---:|---:|
| Qwen |26.064|55.912|별도 요약 미기록|16.429|2.039, phase 관측값 |
| ENC |63.913|7.295|8.578|33.868|33.252, HWM |
| BASE_S |52.585|33.846|33.893|62.009|62.115, HWM |

서로 다른 회계·표본/peak이므로 열을 합산하지 않는다. swap은 모든 해당 관측에서0이다. BASE cgroup `high=6454`는 보존하고 `max=0, oom=0, oom_kill=0`과 구분한다. 이번 중단 reason은 headroom이나 OOM이 아니라 `other_service_work`이며 정확한 발동 원인은 UNKNOWN이다.

## 사용량과 세 비용 관점

신규 이미지2/2, 신규 full sampler1/4, 영상 VAE decode0/8, full-resolution source encode1/2, STEP converter 호출0. 새 모델/패키지/데이터 다운로드·학습·LoRA·외부 생성·imagegen·자동 재시도0이다. 인물 영상 전체와 차량 downstream은 NOT_RUN이다.

캠페인 비용에는 부적합 인물 앵커와 완료 후 중단된 BASE가 포함된다. 기존 BASE/support가 있을 때 STEP을 적용하는 증분 비용은 **이번에 미측정**이다. 향후 one-pass 비용도 미입증이다. 실제 비교를 완료하지 못했으므로 비용 대비 품질 개선율이나 B033 대비 속도 향상을 계산하지 않는다. 근거는 [QWEN_COSTS](QWEN_COSTS.json), [EXECUTION_COUNTS](EXECUTION_COUNTS.json), [GUARD_EVENT](GUARD_EVENT.md)다.

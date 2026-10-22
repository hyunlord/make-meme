# B-007A 결과

**사전검증 완료: GB10 실제 FlashAttention BF16 커널 PASS. SCAIL 전체 모델 실행 가능성은 아직 미검증이다.** 모델 가중치 다운로드·전체 diffusion·학습은 모두 0이며 B-007B는 NOT_RUN/미승인이다.

## 실제 연산 결과

고정 SCAIL Wan commit `78fe19576bb06be96c2375e088574a262a300edb`의 attention wrapper를 변경 없이 직접 실행했다. GB10 CC12.1, Torch2.14.0+cu130, CUDA13.0, FlashAttention2.8.4에서 FA2=true/FA3=false였다. BF16 QKV, B=1, H=40, D=128, Lq=64; Lk=32/64/80 및 padding을 검사했다. FP32 SDPA MATH와 비교한 사전 기준은 atol=0.01, rtol=0.02이며 모든 출력 finite다.

| 실제 케이스 | 최대 절대 오차 | RMSE | 판정 |
|---|---:|---:|---|
| self-full | 0.00364769 | 0.00041746 | PASS |
| self-key-padding | 0.00438702 | 0.00046932 | PASS |
| image-cross | 0.00465846 | 0.00055537 | PASS |
| text-cross-padding | 0.00415826 | 0.00043620 | PASS |

작은 FA+FP32 SDPA 비교 전체 peak allocated는 **46,262,784 bytes**, supervisor 시간은4.001초다. 개별 case 시간도 두 연산과 동기화를 포함한다. FA 단독 성능이나 14B 모델 메모리 측정치가 아니다. [원시 수치 요약](KERNEL_SUMMARY.json).

## 실패와 제한 수정 이력

1. 릴리스2.8.3.post2는 C++17 설정과 기존 Torch의 C++20 요구 충돌로12.003초 뒤 실패했다.
2. 두 번째이자 마지막 source 방법은 공식 FlashAttention commit `2bdeddd15af6f1c44cd41e6f5b08b9e544398397`와 CUTLASS `7127592069c2fe01b041e174ba4345ef9b279671`이다. 공식 C++20/SM121 경로를 사용했고 source/backend를 수정하지 않았다.
3. 기존 Ninja 실행 파일의 PATH 누락 때문에 serial build가 시작되어 자체 프로세스만 종료하고 같은 source를4 workers로 재개했다. 이 sub-invocation은156.053초였다.
4. 내부35분 guard가06:45:34 UTC에 종료했다. 이는 메모리 오류가 아니라 deadline이며79/97 objects를 보존했다. 사용자2시간 상한 안에서 한 번의 동일 source/cache continuation을 사전 등록했고 실제 남은18 targets를626.161초에 완료했다. 새 설치 방법·다운로드·무한 재시도가 아니다. 원래 실패/timeout 로그는 보존했다.
5. 설치 뒤 별도5분 guard 아래 실제 kernel4개를 수행했다. 모든 자체 process group은 종료됐다.

의존성 source archive 합계 **56,998,912 bytes**(소량 문서/metadata 별도),2GB 이하. compiler 최대4. 빌드 중 최소 MemAvailable **68,959,162,368 bytes**, 관측 swap0. 기존 환경의 method1 실패 후 baseline 대비138개 metadata/Torch fingerprint는 변경0이며 **method1 이전 byte snapshot은 없다**. 공식 setup/CUDA121파일과 wrapper의 pinned 원본 일치를 확인했다. A의 기존 알려진111개 파일 hash도 모두 같지만 전체 파일시스템 불변 검증으로 확대하지 않는다.

## 입력·마스크·시간축

- 실제 Lab 사진과 원본17장 해시를 검증했다. reference/driving은 동일 red ID, 배경black이다. VACE의 white mask 의미와 혼용하지 않았다.
- 원본 RGB/mask에 동일 crop/resize를 적용했다. 세로 reference 때문에 공식 H/W 교환 규칙을 반영한 H896×W512이며119개 가시점이 crop 안에 남았다. 가려진 관절은 새로 만들지 않았다. 가로 원본의 좌우 배경은 잘리므로 원본 전체 framing 보존은 아니다.
- 초기 비학습 GrabCut의 바닥 반사 오염 v1과 기록된 수동 국소 제외 v2를 모두 보존했다. 얇은 바닥/발/꼬리 경계 잔여는 **PARTIAL/UNRESOLVED**다. 자동 segmentation 성능이나 production mask 통과로 보고하지 않는다.
- pinned mask helper를 Mac CPU에서 실제 실행: reference **[28,1,112,64]**, driving **[28,5,56,32]**, red slots1/8/15/22. 실제 driver bilinear half→helper1 순서이며 area fractional occupancy가 생긴다. [입력 검사](INPUT_PREFLIGHT.md), [tensor 기록](MASK_TENSOR_CHECK.json).
- CPU 입력17프레임24fps 영상은0.708333초, 마지막 표본은16/24초다. 같은 프레임을16fps로 쓰면1.0625초가 된다. mask MP417장 decode는 PNG와 모두 픽셀 일치했다.
- 향후 writer의 명시적24fps 전달 최소 patch와 mock 검사는 준비됐지만 upstream에 적용하지 않았다. 실제 diffusion writer 통합은 NOT_RUN이며24fps 인코딩 자체가 학습된 동작 시간 prior 검증은 아니다. 연속 재생 품질은 **UNVERIFIED**다.

## 자원 위험과 남은 판정

공식 checkpoint metadata의 비선택 파일 합계 **80,002,038,274 bytes**, SAT checkpoint65,582,563,395 bytes다. 실제 가중치는 받지 않았다. 기존 가용 disk는1,227,718,524,928 bytes로 metadata 크기를 수용하지만, 변환 output O가 추가로 필요하다. O가 원본 checkpoint와 같다는 가정이면 합계145.585GB이며 이는 상한이 아니다.

변환은 map_location/mmap/dtype cast 없이 torch.load하고 원본 객체를 유지한다. 저장 dtype/device와 실제 peak는 **NOT_MEASURED**다. 통합 메모리128,524,300,288 bytes를 CPU/GPU 각각의 독립128GB로 더하지 않는다. 작은 attention PASS는 checkpoint 변환·load·긴 token·VAE·전체 forward의 peak 보증이 아니다. [자원/코드 감사](MODEL_RESOURCE_AUDIT.md).

## 결론과 다음 한 단계

**B-007A 연구 범위는 완료, 작은 커널 gate만 PASS, 입력 마스크는 PARTIAL, 전체 모델 readiness/영상 품질은 미검증이다.** 다음 후보 하나는 별도 승인된 **B-007B 공식 SCAIL-2 Wan RGB driving baseline**이다. 승인 전 다운로드0을 유지한다. 시작 전 현재 메모리/디스크를 다시 측정하고 변환 peak guard, 마스크 경계 검토, 실제24fps writer 연결을 고정해야 한다. 변환 OOM, 긴 sequence 메모리, animal anatomy/identity 전이 실패 가능성을 남긴다. 이번에는 그 실행을 시작하지 않는다.

[실행 이력](RUNNING.md) · [재현 코드/명령](REPRODUCE.md) · [한국어 수식 학습](../../lessons/B-007-attention-memory-feasibility.md) · [질문](QUESTIONS_KO.md) · [해설](ANSWERS_KO.md).

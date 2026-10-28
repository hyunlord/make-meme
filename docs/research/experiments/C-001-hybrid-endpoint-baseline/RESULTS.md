# C-001 — 실제 두 영상 기준선 결과

**PIPELINE_COMPLETE / ANCHOR_PAIR_PARTIAL / IDENTITY_PARTIAL / SAM_ANALYSIS_COMPLETED / SAM_CONDITIONING_NOT_RUN / TEMPORAL_UNVERIFIED**

두 공개 사례에서 실제 native imagegen 앵커4장, SAM 분석70개 입력, VACE 생성 영상2개를 얻었다. 영상마다33프레임·50 scheduler step·100 model_fn call이며, 원출력·최종 latent·모든 프레임·MP4를 보존했다. 양끝 출력에 앵커를 덮어쓰지 않았다. 영상 생성은 각각291.70초와292.91초였다. 기술 실행 완료와 원본 동작 보존은 다른 결과다.

## 두 사례에서 실제로 보이는 결과

| 축 | 차량: car-roundabout→car-shadow | 개: dog→dog-gooses |
|---|---|---|
| 앵커 적합성 | ANCHOR_PARTIAL: 은색 높은 차체와 방향 전환은 맞지만 배경 미세 요소 변화 | ANCHOR_PARTIAL: 검정/흰 외형은 맞지만 종료 자세·발 위치가 원본과 다름 |
| 앵커 쌍 일관성 | 은색 차체·루프레일·세로형 뒤등이 양끝에서 대체로 연결 | 검정 털·흰 주둥이/가슴/발이 양끝에서 대체로 연결 |
| 출력 양끝 충실도 | PARTIAL: 입력과 유사하나 정확한 복사 아님 | PARTIAL: 특히 마지막 위치·자세·꼬리가 입력 앵커와 다름 |
| 중간 외형 | IDENTITY_PARTIAL:33장에 대체 차체 특징 유지, source Mini 회귀는 보이지 않음 | IDENTITY_PARTIAL:33장에 검정/흰 특징 유지, source 크림색 개 회귀는 보이지 않음 |
| 원본 동작 | MOTION_PARTIAL: 우측 주행→뒤쪽3/4 회전 순서는 유사. 궤적·시점별 회전량의 일치 미입증 | MOTION_FAIL: source8/16은 이미 정면 접근·전방 발디딤인데 생성8/16은 측면·낮은 머리 상태에 머무름. 큰 접근 방향만 유사 |
| 보호 장면 | SCENE_PARTIAL: 건물/난간 배치 대체로 유사하지만 source16의 파란 원형 방향 표지가 생성에서 사라지거나 바뀌고 배경 차량도 다름 | SCENE_PARTIAL: 울타리·수풀·잔디 배치는 유사하지만 잔디 세부와 카메라 blur/texture가 달라짐 |
| 경계·접촉·그림자 | 정적 시트에서 큰 분리는 뚜렷하지 않음. 바퀴 회전·세부 접촉·그림자 정확성 UNVERIFIED | 발 디딤 상태와 source 관절 phase 불일치. 털 경계·접지의 연속 정확성 UNVERIFIED |
| 시간 품질 | TEMPORAL_UNVERIFIED | TEMPORAL_UNVERIFIED |

두 에이전트가 앵커·전체33프레임 시트·동일 좌표 중간 비교를 정적으로 검토했다. 작은 target reference 때문에 정확한 개체 정체성까지 입증하지 못한다. 표의 외형 평가는 구별되는 특징 유지에 대한 제한된 판단이다. 브라우저 재생·ffmpeg decode 성공을 사람이 연속 재생을 보고 판단한 시간 품질 PASS로 바꾸지 않는다.

차량은 외형 교체와 거친 회전 순서가 보이는 유용한 첫 기준선이지만 보호 장면 실패가 있다. 개는 외형 교체가 보여도 원본의 시점별 동작 보존은 실패했다. 따라서 두 사례의 원본 동작·장면 보존을 포함한 결합 목표를 완수한 기본 시스템으로 채택하지 않는다. **검토용 hybrid 기준선으로 보존**하고 다음 모듈을 논의한다. 완전 로컬 생성 성과나 일반화된 품질 개선으로 부르지 않는다.

## 실제 조건과 보조 수치

공식 `firstlastframe` helper로 RGB endpoint0/32와31 missing frame을 구성했다. reference 목록으로 대신하지 않았으며 `vace_reference_image=None`이다. 영상 모델 입력은 두 전체 프레임 앵커와 caption이다. 원본 중간 RGB, SAM track/mask는 생성에 사용하지 않았다.

기존 검증된 DiffSynth VACE1.3B 경로의 BF16/SDPA/tiled VAE, Euler50/CFG5/sigma_shift5, seed20261028을 고정했다. 공식 runner UniPC/shift16과의 차이와33→9 temporal mask 제한은 `BACKEND_CONTRACT.md`에 명시했다. 실제 latent는 두 사례 모두 `[1,16,9,60,104]`, BF16, atomic save/readback exact였다.

| 전체 프레임 RGB L1(0..255) | 시작 | 종료 |
|---|---:|---:|
| 차량 앵커 대비 실제 출력 | 7.649 | 14.990 |
| 개 앵커 대비 실제 출력 | 5.551 | 17.542 |

이 수치는 입력과 출력의 차이를 보여 주는 보조 진단이며 identity 점수나 편집 정답 영상과의 오차가 아니다. 네 endpoint 모두 pixel-exact=false다. 전체 수치와 관측 범위는 `NUMERICS.json`에 있다.

## SAM: 실제 수행과 범위

기존 SAM3.1 Comfy integration을 서버 없이 호출해 source66프레임과 네 앵커를 분석했다. Source query는 car/dog, 첫 프레임 GT 겹침으로 대상 후보를 선택했다. 선택 보조 IoU는0.983681/0.952602이며 full tracking 정확도 점수가 아니다. Raw packed mask, visible mask, bbox/center/area, overlay, role 연결을 보존했다. 앵커는 별도 detection이며 automatic cross-domain identity 연결 성과로 부르지 않는다.

실제 분석38.479초, fallback0. 기존 integration revision은 고정했고 upstream weight revision은 UNKNOWN이다. 제한된 정적 spot check에서 대체로 적절한 대상 영역을 확인했다. 세부·전체 시간 tracking 품질은 UNVERIFIED다. `SAM_ANALYSIS.md` 참조.

## 운영 결과와 역사 보존

사전 계획·입력은 `4ea7753`, 앵커 provenance와 실행 코드는 `c117861`에서 GPU 실행 전에 게시했다. 최초 CPU systemd worker는 exit0였지만 cgroup이 사라진 뒤 정상 종료 proof를 만들려던 순서 때문에 최종 `NOT_CLEAN/OBSERVATION_FAILED`였다. 해당 영수증을 보존했다. 기존 identity proof를 먼저 적용하도록 C 전용 supervisor 사본에서 두 줄 수정했으며 B-034 코드는 바꾸지 않았다. 실제 fresh CPU 재실행과 두 나머지 CPU route는 COMPLETE였다. CPU 실패1, 정상 CPU route3이며 heavy 복구 사용0이다.

기존 메모리·외부 GPU·service·identity 보호를 유지했다. 시작72GiB/실행24GiB 등은 이 연구의 운영 예산이지 공식 안전 보증이 아니다. SAM과 두 영상의 실제 heavy guard 모두 COMPLETE/CLEAR, 정상 종료 proof=true, cleanup error0, 최종 GPU 작업 없음이었다. 전역 swap1,040,384B는 처음부터 끝까지 안정적으로 관측돼 GLOBAL_SWAP_WARNING으로 남았고 0으로 보고하지 않았다. 자체 swap.current/max0, OOM/OOM-kill/high event0, 관측된 swap growth/swap-out은0이었다. 최근10초 PSI full 비율의 관측 최대는 차량1e-7, 개3e-7(0.00003%)로 중단 기준보다 낮았다. 최소 MemAvailable은 차량88.288GiB, 개88.308GiB였다. Cgroup current는 전체 CUDA 메모리 회계라는 주장이 아니다.

B-034는 운영 보류 상태 그대로이며 복구하지 않았다. 다른 서비스·프로세스 종료, 시스템 설정 변경, 새 패키지·가중치 다운로드, 학습, 업스케일, 후합성은0이다.

## 검토와 전달

검토본은 SOURCE / TARGET REFERENCE / START ANCHOR / END ANCHOR / GENERATED VIDEO, 원본/생성 native속도 나란한 재생,33프레임 슬라이더, source SAM overlay 영상, 앵커 mask/role, 전체 시트, 동일 좌표 중간 target 확대, 앵커/출력 endpoint 비교를 포함한다. 실제 Chromium1280/768/375에서 이미지 decode·슬라이더·영상6개 재생 진행·JS오류0·모바일 overflow0을 확인했다. 영상6개는 ffmpeg decode와33frame/16fps도 확인했다.

생성 MP4는 원본 바이트를 그대로 전달한다. Source preview·SAM overlay preview·contact sheet는 명시한 새 검토 파생본이다. 원본 raw와 latent는 full 저장소에 있고 compact에 포함하지 않는다. 전달 검증은 `DELIVERY.json`에 별도 기록한다. 공개 Git에는 개인 경로·PID·사진/영상·가중치·조건 tensor를 게시하지 않았다.

## 다음에 바꿀 한 가지 — 아직 실행하지 않음

같은 네 앵커와 seed를 유지하고 **원본에서 얻은 시점별 객체 운동 경로를 실제 생성 조건으로 연결하는 대조 하나**를 제안한다. 양끝만으로는 중간 회전량·접근 phase가 고정되지 않는다는 관측에서 나온 가설이다. 단순2D 중심 경로만으로 개의 관절·접촉까지 해결된다는 주장은 하지 않는다. 표현·연결 방법은 이번 결과를 사용자와 검토한 뒤 설계한다. 추가 사례·seed·모델·학습·장영상은 시작하지 않았다.

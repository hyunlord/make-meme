# B-020 — 실제 Lab 영상의 FM tail 학습 결과

상태: **COMPLETED / 실제 FM 학습·저장/reload PASS / 목표 자세 재현 FAIL / 품질 개선 NOT_ESTABLISHED / temporal UNVERIFIED**.

사용자가 제공하고 비공개 로컬 연구를 허용한 실제 Lab 영상과 기존 앉은 참조 사진을 사용했다. 이전 DATA_PENDING과 제3자 자료 권한 미확인 이력은 삭제하지 않는다. 사전 실행 고정 `e8d32f7baed33fe8057ac79e1faa724e93a3577f`, 중간 관측 `c6f9c14`.

## 실제 완료와 범위

- 원본 f126~142, source PTS4.200000~4.733333초,17frame/30fps. encoded duration17/30초.896×512 letterbox로 전신을 보존했다. 원본은1920×1080/30fps이며 temporal resampling은 없다.
- target Y와 driving D는 동일한 실제 RGB. R은 별도 시점의 앉은 Lab 사진이다. **D=Y SELF_RECON_FM_SMOKE**이며 cross-ID 안무/일반화 실험이 아니다.
- P1에서 실제 Y를 정상 VAE로 인코딩해 `[16,5,64,112]` FP32 target latent와 조건을 저장했다. prefix4tuple 각각1회의 실제 positive full forward에서 h38와 기준 velocity를 저장했다.
- 마지막 block39 self-attn Q/V rank4·alpha4·dropout0 LoRA81,920파라미터만20 AdamW update했다. 공식 frozen head/unpatchify를 통과한 실제 velocity MSE이며 인공 hidden MSE가 아니다.
- 네 split parity·fresh reload·adapter OFF 최대오차0. 기반가중치는 worker의 실제 값 hash 비교에서 불변이었다. 독립 검토는 해당 receipt·실행 소스·작은 tensor/adapter를 확인했으며 전체 base를 별도로 다시 읽은 것은 아니다.
- 각 backward에서 실제 FA2 backward3경로와 head 입력 gradient를 확인했다. 첫 A gradient0/B양수, 이후 A/B양수를 구분했다. train20update와추가tail10eval을 완료하고 더 학습하지 않았다.

## 고정 tuple별 실제 MSE

| tuple | sigma | 전 | 후 |
|---|---:|---:|---:|
| train_0 | 0.2 | 0.1455920786 | 0.1454725415 |
| train_1 | 0.5 | 0.0507136025 | 0.0506716855 |
| train_2 | 0.8 | 0.0315620080 | 0.0314944796 |
| holdout | 0.65 | 0.0384031795 | 0.0383795351 |

감소는 작다. holdout은 같은clip의 별도sigma/noise일 뿐 독립영상·새개체 검증이 아니다. loss 감소·학습배선·저장/reload·영상 변화·실제 개체/동작 품질을 하나의 PASS로 합치지 않는다. [학습 receipt](TRAINING_SUMMARY.json).

## 영상의 관측

학습 전 전체17장 정적 검토에서는 앉은 reference 자세·침대 배경·중앙portrait 배치가 유지됐다. 후반 머리가 이미지 왼쪽으로 변하지만 주둥이/머리가 참조영역 경계에서 잘리고 얼굴이 흐려진다. 실제Y의 서 있는 전신/목표장면 재현은 FAIL이다. 학습 후 전체17장과 원본크기 local0/8/16 비교를 직접 확인했다. trained도 앉은 자세·침대·중앙portrait 배치를 유지하고 후반 머리/주둥이가 경계에서 잘렸다. target의 사족으로 서 있는 전신 재현은 양쪽 모두 FAIL이며, 뚜렷한 품질 개선은 NOT_ESTABLISHED다. 실제 개체와 단순 검은 Lab 외형의 구분, 정확한 머리각도/접촉/타이밍은 UNCERTAIN으로 남긴다. 실제 연속 재생 품질은 UNVERIFIED다.

원본/생성의 전체 프레임과 같은30fps 비교를 비공개로 보존한다. 보간·upscale·warp·선별·속도변경은 하지 않는다. reference letterbox 여백이 출력에 남는 현상도 숨기지 않는다.

## 자원과 실행 한계

P worker170.530초, baseline sampler1060.444초. TRAIN worker38.8368초/guard40.4857초, CUDA peakallocated4,854,839,808bytes, sampled cgrouppeak3,242,049,536bytes, 최소시스템가용87,317,381,120bytes. 이들은 서로다른 회계이며 합쳐서 메모리 용량을 계산하지 않는다. 전체 phase측정은 [MEASUREMENTS.json](MEASUREMENTS.json)에 있다. PREFIX/BASE_S/TRAIN_S의 cgroup high 이벤트는 각각2531/2871/1498로0이 아니며 보존했다. 모든phase의 max/OOM/oom_kill과swap은0이다. high는 해당 메모리 회계의 압박/회수 이벤트이며 CUDA전체 사용량이나 OOM과 동일한 지표가 아니다.

기존 model fullSHA는 B-007D 검증값을 재사용했고 이번에65GB전체를 새로 rehash했다고 주장하지 않는다. 실행 code/upstream hash와 입력/hash/실제텐서계약은 확인했다. 새다운로드/학습설정탐색/재시도/imagegen/외부생성API는0.

## 남은 기술·해석 제한

- 수동mask의 얇은 꼬리·발 경계와 f0안쪽 뒷다리 support과대 영역은 PARTIAL이다. 자동segmentation성능이 아니다.
- helper10CPU검사PASS이나 runtime typing은80errors462warnings NOT_CLEAN이다. 주로 미해결upstreamimport·recursive tensor tree·dynamicexec진단이며 무관한 리팩터링/억제를 하지 않았다.
- adapter serializer의 상위label `TEST_ONLY/NOT_FOR_INFERENCE`가 B018형식에서 상속됐다. B020 provenance는 `PRIVATE_ONE_CLIP_FM_OVERFIT_NOT_PRODUCTION`이며 이번 사용자허용 학습후비교에만 적용했다. 과거B018adapter를 재사용한 것이 아니고 production기본경로에도 적용하지 않았다. 이 metadata불일치를 숨기거나 실행중파일을 덮어쓰지 않았다.
- 전체40block backward·cross-ID·개체/자세분리·일반화·상용품질은 NOT_RUN/NOT_ESTABLISHED다.

## 재현·후속

[입력 고정](INPUT_AMENDMENT.md), [재현](REPRODUCE.md), [실행 기록](RUNNING.md), [한국어 수학/코드 해설](../../lessons/B-020-real-fm-tail-overfit.md). 비공개ZIP는 실제 실행호스트에 생성한 뒤 Mac으로 전송·CRC·payload/ZIP SHA를 확인한다. 미디어/latent/adapter/특징/weights를 공개하지 않는다. 추가실험은실행하지 않는다.


## 품질을 나눈 판정

| 항목 | 학습 전 | 학습 후 | 결론 |
|---|---|---|---|
| target의 서 있는 전신 | 착석 유지 | 착석 유지 | 양쪽 FAIL |
| 후반 머리의 화면 왼쪽 변화 | 있음, 경계 잘림 | 있음, 경계 잘림 | 명확한 개선 NOT_ESTABLISHED |
| 실제 Lab 얼굴·귀·주둥이 | 검은 Lab/참조 유사, 후반 blur | 비슷한 잔여 손상 | 실제 개체 충실도 UNCERTAIN |
| 넓은 가슴·사지 | 착석사진 중심 | 착석사진 중심 | 서 있는 목표 체형 검증 실패 |
| 장면/배경·padding | reference 침대/세로배치 유지 | 동일한 실패 유지 | target 장면 재현 FAIL |
| 연속 재생 품질 | UNVERIFIED | UNVERIFIED | 정적 전체프레임 확인만 수행 |

## 최종 실행 수와 종료

P1, prefix positive4forward, TRAIN1(20update/20backward/10추가tail평가), baseline/trained sampler각1(각40step/80forward), decode각1. 새모델/다운로드/외부생성/튜닝/재시도0. 모든7단계exit0, 자체pipeline/watchdog inactive/MainPID0, 기존서비스동일identity/idle 확인. 총작업은4시간한도내다.

## 다음 가설 하나 — 아직 실행하지 않음

**20update의 작은 적합량이 품질 변화 부족의 한 원인인지** 확인하는 동일계약의 사전고정100update 실험만 제안한다. 새 모델·학습층·rank·lr·데이터·noise·prompt를 동시에 바꾸지 않고, 고정tuple MSE와 같은noise의 실제출력을 비교한다. 같은clip overfit이며 일반화검증이 아니고, 이번에 추가80update나영상은 실행하지 않았다. 자원이 낮다는 이유로 자동 확장하지 않으며 별도 계획/실행지시가 필요하다. 이번 결과만으로 마지막block 용량 부족이나 전체모델학습 불가능을 확정하지 않는다.

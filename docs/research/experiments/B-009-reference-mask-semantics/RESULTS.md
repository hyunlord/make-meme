# B-009 결과 — WHITE 조건만으로 직립 동작 전달은 개선되지 않음

**EXECUTION_PASS / CONDITION_CONTROL_PASS / UPRIGHT_MOTION_FAIL / IDENTITY_UNCERTAIN / TEMPORAL_UNVERIFIED.** P·PROBE·S·D를 각1회 수행해 실제17프레임24fps MP4와 최종 latent를 확보했다. 전체17장 시각 검토에서 B-008과 B-009 모두 착석·앞발을 바닥에 둔 자세가 남았다. 원본의 직립과 들어 올린 앞발은 전달되지 않았다. 이는 단일 입력·seed에서 WHITE 조건만으로 충분하지 않다는 결과이며, 모델 전체 능력이나 실패의 유일 원인을 입증하지 않는다.

## 실행 범위와 실제 개입

사전 고정 commit은 `1936356099823ebf720a26a5e82671fdbe6cec67`이다. [PLAN](PLAN.md), [재현 명령](REPRODUCE.md), [코드 차이](RUNTIME_DIFF.diff)를 따른다. 기존 B-008 Mref-black 출력은 재생성하지 않고 대조군으로 보존했다.

새 mask는 정확한 BLACK344,824픽셀만 WHITE로 바꾸고 RED113,928픽셀의 값·위치·면적을 그대로 유지했다. RGB reference/driving, driving mask, prompt, animation `replace_flag=False`, weights/mixed dtype/FA, seed20261022, UniPC40/shift3/CFG5,512×896·17프레임·24fps를 고정했다. RGB 사진의 배경을 지우거나 새 segmentation을 적용한 것이 아니다. [독립 입력 감사](INPUT_AUDIT.md).

새 마스크 SHA256은 `ea54f417f109793210c405d2452152b839fd57f81329811fb650958e830bab9f`다. 기존 A/B-008/H 자산과 실행 기록을 보존하며 신규 P/PROBE/S/D는 각각 최대1회, 실패 포함·재시도0이다. 다운로드·학습·imagegen·외부 생성·공식 인간 예제 재생성은 범위 밖이다.

## 확인된 실제 단계

| 단계 | 현재 상태 | guarded 시간 | 근거 |
|---|---|---:|---|
| P | PASS |114.974초|새 Lab 조건 캐시 저장·검증|
| CPU 조건 대조 | PASS |별도 시간 미기재|양 CFG mask prefix만 변화, 나머지14leaf exact|
| PROBE | PASS |6.079초|16leaf/RNG 복원·정상 종료|
| S | PASS |1093.089초|실제40step/80forward, finite final latent 저장·readback|
| D | PASS |15.233초|finite raw [3,17,896,512], MP4 전체decode PASS|

P 새 cache SHA256은 `e151044c4939c751b551c839f878acedfa233485db72275594d75e619e518ae3`다. 실제16개 leaf 중 t4/t10, 즉 양 CFG branch `ref_masks`만 pinned helper가 예측한 WHITE reference prefix 변화(max absolute delta1)를 보였다. RED 및 다른 색상, generated plane은 정확히 보존됐다.

나머지14개 leaf는 모두 bit-identical/max delta0이었다. reference RGB latent·driving RGB latent·CLIP·text·driving mask·initial noise·RNG·scheduler가 보존됐으며 사전 float tolerance에 기대어 통과한 사례가 아니다. 사전 정책은 비마스크 floating encoder 조건 rtol1e-5/atol1e-6, mask/noise/RNG/schedule exact였다. 큰 예상 밖 변화가 있으면 S를 차단하도록 검사했다.

## 실제 정적 시각 검토

주 에이전트가 원본/실제 참조/B-008/B-009의 전체17프레임 시트와 f0/4/8/12/16 확대 비교를 직접 확인했다. 프레임별 좋은 결과만 골라 판정하지 않았다. native24fps 비교 MP4는17프레임·0.708333초이며 보간·warp·프레임 복제·속도 변경이 없다.

| 항목 | B-008 | B-009 | 해석 |
|---|---|---|---|
| 원본 뒷발 직립 | FAIL | FAIL | 전구간 착석 형태 유지 |
| 앞발 위치·들림 | FAIL | FAIL | 두 앞발이 침대에 내려가 있음; source의 들어 올린 앞발 단계 미재현 |
| 머리·몸 변화와 타이밍 | 미입증 | 미입증 | 작은 머리/크기 변화가 있으나 source 동작 단계 전달로 판단할 근거 없음 |
| 검은 Lab 견종 외형 | 관찰됨 | 관찰됨 | 검은 털·늘어진 귀·넓은 머리와 가슴 유사 |
| 실제 특정 Lab 개체 | UNCERTAIN | UNCERTAIN | 견종 유사성을 특정 개체 수용으로 올리지 않음 |
| 묵직한 체형 | 부분 관찰 | 부분 관찰 | 넓은 가슴/몸통이 남지만 착석이라 요청한 직립 체형·사지 재현은 검증 불가 |
| 정적 형상 | 큰 붕괴 미관찰 | 큰 붕괴 미관찰 | 시트에서 명백한 큰 머리/사지 파괴는 보이지 않음; 미세 털·접촉은 수용 아님 |
| source 외형 누수 | 뚜렷한 옅은 털 누수 미관찰 | 같음 | 광범위한 누수 부재를 증명하지 않음 |
| 경계·가림·발 접촉·반사 | PARTIAL/UNCERTAIN | PARTIAL/UNCERTAIN | 기존 마스크 얇은 경계 결함 보존; 실제 물리 접촉은 미검증 |
| 실제 속도 시간 품질 | UNVERIFIED | UNVERIFIED | 연속 재생을 사람이 직접 관찰한 것으로 보고하지 않음 |

두 결과는 정적 검토상 매우 비슷한 착석 구도다. 바이트 동일하다는 뜻은 아니다.

이번 animation에서 WHITE는 참조 배경 가시성을 요청한다. 침실이 남는 것 자체를 FAIL로 판정하지 않으며, 참조의 착석 자세에 고정되는 현상과 구분한다. 배경만 달라진 것을 동작 성공으로 계산하지 않는다. 원본 스튜디오에서 개체만 교체하는 replacement는 다른 계약이고 이번에는 mode를 바꾸지 않는다.

이번 결과는 여전히 착석이므로 WHITE 하나만으로 충분하지 않다는 범위에서 해석한다. B-008 실패의 유일 원인이나 전체 동물 일반화를 증명하지 않는다.

## 검증 한계와 역사적 정정

[CPU 검증](CPU_VALIDATION.json)은10개/1.11초/GPU0으로 PASS다. driving mask1e-7 변화도 exact 검사에서 거부했다. syntax·critical Ruff는 PASS지만 [전체 type 검사](STATIC_VALIDATION.json)는17파일832errors로 **NOT_CLEAN**이다. 동적 upstream/tree 관련 정적 부채와 실제 실행 성공을 구분한다.

고정 README는 mixed resolutions/fps 학습을 명시한다. writer 기본16fps를 고정된16fps 학습 분포로 해석했던 설명은 [새 학습 문서](../../lessons/B-009-semantic-mask-conditioning.md)에서 정정하고 과거 B-008 결과는 보존했다. BLACK은 모든 상황에서 잘못된 mask가 아니며 RGB alpha 제거와도 다르다.

## 실행·메모리·보존 증거

[RUN_LEDGER](RUN_LEDGER.json), [MEASUREMENTS](MEASUREMENTS.json), [실제 조건별 hash](CONDITION_COMPARISON.json)에 단계별 근거를 남겼다. 각 단계 exit0/guard reason=service_exit이며 마지막 owned unit은inactive/MainPID0이다. sampler1/1·재시도0·학습0·신규 모델0. 종료 후535개 코드/upstream/입력 보존 검사PASS.

S 최소 MemAvailable51.975GiB, cgroup 기록 peak62.006GiB, CUDA 기록 peak allocated33.831GiB, swap0. cgroup high 이벤트2101은 실제 발생했고 숨기지 않는다. max/oom/oom_kill은0이었다. 서로 겹치는 system/RSS/cgroup/CUDA 회계는 합산하지 않는다. CUDA는 관측 시점 값이며 관측하지 않은 전체 시간의 절대 peak를 단정하지 않는다.

최종 latent FP32[16,5,112,64]는 finite이며 실제 P initial noise와 구별된다. 파일SHA `22055e7161a59364630598df41619d344c7ad7bbc2503e07464d7d7c46a903e5`, 값SHA `103d3dfc2b9ac6bb7c3b101000f25ea3985779266beb1bf6671aa04bb9968dd7`. MP4 SHA `c3dea3bd5a21f7768a92b0a434dbf7c195a4bc7365fa4b9b12161ed94dc40152`;512×896/17f/24fps/0.708333초. raw·latent·입력·마스크·전체 trace는 비공개 묶음에 보존한다.

결과 후 소형 보고서 전송에서 SSH peer reset1회가 발생했지만 전송만 재시도해 완료했다. 생성/디코딩 재시도와 구분한다. 정적 검사832errors는 남아 있고 이번 실행 성공이 typecheck clean을 뜻하지 않는다.

## 다음 연구 하나와 종료

다음 후보 하나는 source 첫 프레임을 reference로 쓰는 제한된 동물 자기 재현 진단이다. **새 생성 없는 first-frame-repeat 정적 대조군**과 동작 방향·위상·시간 변화를 비교해야 이미 직립인 reference 복사로 성공하는 평가 오류를 피할 수 있다. 작은 동작 때문에 구분 불가능하면 INCONCLUSIVE로 남긴다. 이는 Lab identity 성공 실험이 아니며 reference/text 변경을 단일 mask 인과효과로 주장하지 않는다. 이번 B-009에서는 실행하지 않았다.

공개는 문서·비민감 코드·설정·hash·요약만 포함한다. 비공개 ZIP의 최종 CRC/파일hash·양호스트 전달 상태는 DELIVERY에 별도 기록한다. 추가 mask/seed/prompt·자기 재현·학습으로 자동 확대하지 않고 종료한다.

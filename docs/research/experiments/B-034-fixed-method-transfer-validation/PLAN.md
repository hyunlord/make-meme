# B-034 — 고정 clean-prediction 방법의 새 공개 입력 검증

상태 PREPARING / 생성 전 등록. 작성 2026-10-27. 시작 원격 `d401b0180168bd3db4b554ba127f1395c80c9c78`. 사용자 실행 지시와 [전체 의뢰서](../../work_orders/20261027-B034-fixed-method-transfer-validation.md)가 범위를 정의한다. 원문의 PROPOSED는 문서 작성 당시 상태다. Spark 실제 조회에서 중복 B034 실행/산출물이 없고 기존 서비스만 있음을 확인했다.

## 질문과 고정 방법

B033의 국소 PARTIAL을 보존하고 새 강체/비강체 입력에서 같은 규칙이 target 외형·source 동작을 훼손하지 않으면서 두 대조군보다 편집 내부/경계를 개선하는지 확인한다. B032는 저비용 기준선, B031 결합 FAIL은 그대로다. 새 강도·스케줄·마스크 탐색은 하지 않는다.

두 입력은 [CASES](CASES.md)에 이미지 생성 전에 고정한다. Qwen/SCAIL은 B031의 모델·환경·정밀도·설정을 재사용한다. Qwen Image1=source f0 전체, Image2=target GT bbox+10% margin 및 support 밖128. 이미지40step/true CFG4/guidance1/negative 단일공백/seed20261026. 각1회만 수행하며 부적합 앵커는 영상 NOT_RUN이고 사례를 교체하지 않는다.

적합한 A0의 실제 support를 확인해 밖128, RED/BLACK R_star를 만든다. 새 공개 source이므로 필요한 text/driving/reference 조건은 공식 기존 encoder에서 만들며 BASE/STEP은 같은 저장 cache·noise/RNG/scheduler를 공유한다. SCAIL replacement=True, UniPC40/shift3/CFG5/seed20261022, history/additional_ref=None, LoRA/ALG/B029 gate/manualRoPE OFF. 896×512·17프레임, source_fps=null/preview24fps/timebase_assumed=true.

## 순서와 비교

1. 두 source/target, caption, 외형·동작·보호 장면과 코드/설정을 고정하고 push한다.
2. 이미지 최대2회 후 실제 A0 적합성을 판정한다. Qwen 종료·자원 회복 뒤에만 SCAIL을 실행한다.
3. 적합 과제의 BASE sampler/decode 각1회. Full-resolution source VAE encode 각1회.
4. BASE의 실제 target T를 제한된 수동/CPU polygon으로 표시한다. 공개 source GT S와 합치며 H=empty. 주석 총30분 이내. source clip bbox 긴변 L로 r=max(2,ceil(.02L)), Euclidean core와 바깥4px feather의 기존 compositor를 그대로 쓴다. E와 평가 crop을 STEP 전에 고정한다.
5. B033과 같은 시간 max 묶음 [0],[1..4],[5..8],[9..12],[13..16], 공간8×8 max 및3×3 guard로 M을 만든다. source/target support coverage를 확인한다.
6. A=BASE+RGB_POST, B=M*z_BASE+(1-M)*z_source를 한 번 decode+같은 RGB_POST, C=B033 converter의 clean prediction에 같은 혼합을 적용하는 STEP+같은 RGB_POST. 모든 raw도 보존한다.

`clean_constraint.py`는 B033과 byte 동일하게 재사용한다. 공식 converter를 한 번 호출한 뒤 corrector/history/predictor에 전달하며 noisy state에 clean source를 직접 붙이지 않는다. CPU 기존 계약을 재사용하고 새 shape·coverage·cache·noise·40conversion만 확인한다. final latent를 decode 전에 원자 저장하며 실패해도 재샘플링하지 않는다.

## 평가와 중단

전체17장 및 local0/8/16, BASE 전에 입력 사건, STEP 전에 경계/접촉 관측창을 고정한다. target 외형, source 동작, 형태, 보호 장면, 경계/접촉을 분리한다. source-copy·target 정지복사는 실패다. STEP이 E를 벗어나면 MASK_INCOMPATIBLE/FAIL이며 E를 바꾸지 않는다. temporal=UNVERIFIED; 실제 연속 인간 시청이 없으면 정적 관측으로 대체하지 않는다.

과제별 ADDITIONAL_BENEFIT / NON_REGRESSION_ONLY / TRADE_OFF / NO_BENEFIT 또는 WORSE / INCONCLUSIVE 또는 NOT_RUN을 사용한다. 오염 없는 사례도 유지한다. 두 사례는 전 범주 일반화나 성공률의 근거가 아니며 사전학습 중복 UNKNOWN이다.

## 상한·보존

이미지2, BASE2+STEP2 sampler4, source encode2, decode8(source reconstruction 포함), 재시도0. 새 모델/패키지/학습/외부생성0. 기존 DAVIS archive를 재사용하며 신규 데이터 다운로드 현재0. 기존72GiB 시작/24GiB headroom/swap0/타 서비스 보호를 유지한다. GPU 작업은 순차 fresh worker다.

실제 최초 도구 시각의 정밀 계측이 없어 보수적 예산 시작을 2026-10-27 01:15UTC로 둔다. 최초 이 문서에 연결된 clock 관측은01:24:33UTC다. hard deadline07:15UTC, heavy cutoff06:45UTC이며 마지막30분은 보존/전달에 남긴다. 이를 실측 시작 시간으로 가장하지 않는다.

결과·CASE_OUTCOMES·COSTS·재현·한국어 해설과 HISTORY/ROADMAP을 갱신하고 연구 branch만 push한다. compact/full을 분리해 실제 CRC/추출/payload hash/양 호스트 전송을 검증한다. 공개에는 비민감 코드·문서·hash만 올린다. 이번 비교 후 추가 실험을 실행하거나 예약하지 않는다.

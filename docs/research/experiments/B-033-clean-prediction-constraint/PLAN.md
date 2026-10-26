# B-033 — clean prediction 원본 제약과 마지막 latent 혼합

상태 COMPLETED / 실행 PASS / 시각 PARTIAL. 아래는 사전 고정한 계획이며 실행 결과는 [RESULTS](RESULTS.md)에 분리한다. Parent B031/B032. 시작 원격 aaf40a92cdc2c85259ad239ab455b2f3124e9b98. 전체 [원문 의뢰서](../../work_orders/20261027-B033-integrated-work-order-ko.md)를 변경 없이 보존하며 이 계획의 상세 계약으로 사용한다. 원문의 PROPOSED는 작성 당시 상태이고 실행 승인은 사용자 요청이다.

## 질문과 통제

같은 vehicle_R1 입력·R_star·조건16leaf·초기noise·RNG·UniPC40 shift3 CFG5에서 원본 배경을 매 clean prediction에 제약하면 마지막 latent 혼합보다 편집 내부/접촉/경계가 개선되는가? 원거리 RGB 복원은 방법 성과가 아니다. B031 raw/동물·사람FAIL과 B032 PARTIAL은 보존한다.

- RAW_BASE: B031 기존 raw, sampler0.
- RGB_POST: B032 MASK_ASSISTED, sampler0.
- FINAL_LATENT_ONLY: 기존 final latent와 full-resolution z_src의 고정M 혼합, decode1.
- STEP_CONSTRAINED: super.convert_model_output 호출 직후 corrector/history 전에 동일M/source로 clean prediction 혼합, sampler최대1/decode1.
- 두 새 결과에 동일 B032 float E의 RGB_POST를 적용한다. 기존compositor 재사용, mask 수정0.

## 고정 지도와 입력

E는 원래 S/T/Hempty,r11,outer4px의 float 재현이다. uint8 preview를 float원본으로 사용하지 않는다. M은 f0/f1..4/f5..8/f9..12/f13..16 max,8x8 spatialmax,3x3 maxguard1회로 [1,1,5,64,112]. source/targetcore coverage와 E PNG양자화를 생성 전 고정한다. 새 출력에 맞춘 support 수정0. Source full RGBencode [16,5,64,112] 최대1, source재구성decode최대1. Half-resolution driving 확대나reference 대체 금지.

896×512,17frames,source_fps=null,preview24fps,timebase_assumed=true. ReplacementTrue,history/additional_refNone,adapter/ALG/gate/manualRoPE OFF. 기존mixedloader/FA2/tinyCUDA/anchor와순차freshworker 유지. 공개manifest는별칭/hash만, 실제경로는비공개다.

## 실행 순서와 검증

1. 중복실행·원격HEAD·기존입력/코드 확인,의뢰서와계획등록.
2. 좁은scheduler subclass와 max4CPU검사: OFF/M1 trajectory, M0 finite/sourceclean, 실제shape/coverage, finalmixendpoint/불변.
3. 코드·config·inputhash·crop 고정 후 push/remote확인.
4. sourceencode/source재구성/finalcontrol을순차진행,phase별사용량저장.
5. sampler1회40step80forward·convert40회·finitefinal원자저장 후decode1. 실패재시도0.
6. 같은E후합성·전체17장/crop비교,수학/비용/한계기록,compact/full검증전달.

predict_x0True/flow_prediction/thresholdingFalse/solver_pNone,실제sigmas/finalsigma0/lower_order_final을확인한다. CFG/forward/history순서변경0,clean source를noisy state에직접붙이지않는다. 기존solver수렴차수/정당성보장주장0.

## 예산과 중단

보수적시작2026-10-26T23:23:00Z,새GPU작업cutoff2026-10-27T01:08:00Z,전체deadline01:23:00Z. sourceencode1/source decode1/control decode1/step decode1/fullsampler1. Qwen/T5/CLIP/학습/설치/다운로드0. 기존시작72GiB/실행24GiBheadroom/swap0/타서비스보호유지. 중복B033없음,기존ComfyUI관측·보존. 입력/수치/guard오류시후속중단,실패도예산소비.

## 사전 평가

B032 고정crop과local0/8/16,전체17장. target높은차체/창/루프/후미등,sourceMini회귀,우향/후면노출순서,뒤바퀴아래조각/strip,halo/이중잔상/절단/그림자와frozenmask불일치를따로본다. 작은wedge는실제차체내부라고확정하지않는다. 동일RGB후합성이후이득이없거나target회귀면미채택. temporalUNVERIFIED,개발1case/seed/output-mask-assisted한계유지. 한비교후종료,추가sweep없음.

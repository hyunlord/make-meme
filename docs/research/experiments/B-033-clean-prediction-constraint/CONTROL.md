# 고정 대조군과 계보

- RAW_BASE: 기존 B-031 vehicle R1. 재생성0. 실제 final latent SHA256 `a37224b66fa154e5b90da552359184de374b3b451b97fba9a3edaf2ba908f821`.
- RGB_POST: 기존 B-032 MASK_ASSISTED. radius11/feather4/Hempty 및 출력 보조 target support를 보존한다.
- FINAL_LATENT_ONLY: 위 final latent와 새 full-resolution source latent를 같은 M에서 마지막 한 번 혼합. 신규 DiT0, decode1.
- STEP_CONSTRAINED: 같은 조건·noise·M·source latent로 40step의 converted clean prediction만 제약. 신규 sampler 최대1.

두 신규 결과의 raw와 같은 E의 RGB_POST를 모두 보존한다. 기존 MP4는 재인코딩하지 않는다. 신규 decode와 신규 합성 MP4는 새 파생물 인코딩이다. RGB_POST의 E0 source exact와 E1 generated exact는 수식의 성질이다.

실제 source/source_support/target_support 각17개 해시가 B-032 INPUT_FREEZE와 일치했다. Efloat를 기존 PNG규약으로 양자화한 17개 지도도 같았다. source/target core 모두 M1에 포함됐다. 이 coverage는 실제 VAE receptive field 검증이 아니다. 경계의 최대 약15px 주석 불확실성, 5.75분 기존 주석 비용을 유지한다.

기존 조건16leaf와 최초 noise는 B-031 producer receipt 및 B-027 원래 계보를 확인해 그대로 재사용했다. 새 source encode는 기존 half-resolution driving latent의 확대가 아니다. source latent는[16,5,64,112], 기존 driving은[16,5,32,56]이다.

source reconstruction과 final-only decode는 실제17프레임896×512, preview24fps로 완료됐다. 시간축은 source_fps=null/timebase_assumed=true이며 실제 원본초단위 시간 보존 주장이 아니다. 영상의 temporal 품질은 별도 연속 관측이 없으면 UNVERIFIED다.

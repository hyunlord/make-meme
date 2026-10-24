# B-020 실행 기록

2026-10-24 · 사용자 제공 실제 Lab 자료 · 시작 HEAD `64a66452561544fbb2d8c2bf6113a01db7710fe6`.

## 입력과 사전 검사

- 사용자 동일 개체 확인과 비공개 로컬 학습·평가 허용을 기록했다. 미디어 공개 권한은 없다.
- source-only 선택 f126~142,30fps,896×512,17장. D=Y SELF_RECON_FM_SMOKE. [상세 입력 확정](INPUT_AMENDMENT.md).
- RGB/마스크 실제 decode34/34 일치, D=Y 파일 일치. pinned CPU 전처리4개 tensor shape/hash 확인. 수동 mask와 얇은 경계 PARTIAL을 남겼다.
- FM/helper CPU10검사 PASS. 고정4tuple·부호·시간·shape·dtype·finite·cache binding·head derivative와 사전 parity 허용오차를 검사했다. 이 값은 실제 14B GPU split parity 증거가 아니다.
- 새 helper 정적검사 오류0·upstream Tensor.backward stub 경고1. 전체 동적 runtime 정적검사는 NOT_CLEAN이며 미해결 upstream import/recursive tensor-tree 타입/dynamic exec 진단을 보존한다. 전체 타입 리팩터링이나 경고 억제는 하지 않는다.
- P는 정상 VAE로 실제 Y를 인코딩한다. prefix4개는 실제 noised input의 최종 velocity를 같은 forward에서 저장한다. tail의 공식 head는 고정하되 gradient를 끊지 않는다. baseline/trained는 같은 P noise·RNG·scheduler·조건을 사용한다.

## 실행 경계

현재 사전 고정 중이며 GPU NOT_RUN. P1 → PREFIX4tuple → baseline S1/D1 → TRAIN1(max20update) → trained S1/D1 순서, 실패 이후 종속 단계를 실행하지 않는다. 실제 phase마다 종료·자원 회복·시도 장부를 확인한다. 4시간 한도와 기존24GiB headroom·swap0·타서비스 보호를 유지한다.

학습 성공, 한 clip FM loss 감소, 같은 clip noise/time holdout, 저장/reload, 영상 변화, 실제 개체/동작 품질은 각각 판정한다. D=Y shortcut과 temporal UNVERIFIED 경계를 유지한다.

## 실제 P 완료

P1의 실제 target VAE/조건 인코딩 완료. worker170.530초, guard172.593초, exit0/inactive/MainPID0. 입력 전처리4개 hash가 고정값과 일치했다. condition receipt SHA `c56c2c6481499e203f2acf58bf126afae57935cfec8079f10e2beb376e898e60`. 자원 회복 후 PREFIX1에서 고정4tuple을 추출한다. 아직 optimizer update와 영상 sampler는0이다.

## 실제 PREFIX 완료

4tuple의 실제 positive 전체 forward를 각각1회 완료했다. h38은 `[1,12992,5120]` FP32, post-projection context `[1,769,5120]` FP32, e0 `[1,6,5120]`/head e `[1,5120]` FP32로 관측됐다. generated/ref/driver token은8960/1792/2240이다. [해시 receipt](PREFIX_SUMMARY.json). clean exit 후 BASE_S를1회 시작했다. 아직 tail parity와 optimizer update는 NOT_RUN이다.

## 학습 전 sampler 완료

BASE_S1 실제40step/80forward 완료, worker1060.444초. finite final latent의 저장/readback 이후 clean exit를 확인했다. BASE_D가 같은 latent·config·condition hash를 검증한 뒤 디코딩한다. 아직 영상 품질/학습 효과는 판정하지 않았다.

## 실제 FM tail 학습 완료

TRAIN1에서20update와10추가tail평가를 완료했다. 4tuple의 분리경로 parity max_abs0, 기반가중치 불변, freshreload/OFF max_abs0. 실제 FA2 backward3경로 및 frozen-head 입력 gradient를 확인했다. holdout MSE0.0384031795→0.0383795351로 소폭 감소했다. [실제 학습 receipt](TRAINING_SUMMARY.json). loss 감소는 영상/개체/동작 개선의 증거가 아니다. 동일 P/noise/config의 TRAIN_S1에 진입하며 추가update는 없다.

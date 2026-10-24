# B-021 재현 계약

현재 실행은 B-020 producer의 실제 initial adapter와 Y/조건/네 prefix를 읽는 B-021 consumer다. 공개 소스만으로 개인 입력과 모델을 복구할 수는 없으며, 실제 경로·시도 ID·해시는 비공개 manifest에 있다.

## 시작점과 변경 범위

B-020 initial payload SHA256:
`1a603a234d0806dcfc2738a1aaf380f0ad98baf934d543a73d7dbea307d1a56b`.

Q/V A는 FP32 `[4,5120]`, B는 FP32 `[5120,4]`이며 B는 정확히0이다. 초기값은 실물을 로딩하며 같은 seed로 대체하지 않는다. B-020 final20 adapter와 optimizer를 혼합하지 않는다. 과거 serializer의 TEST_ONLY label은 원본 그대로 보존하고, 새 B-021 산출물 scope는 PRIVATE_ONE_CLIP_FM_OVERFIT_NOT_PRODUCTION으로 기록한다.

P·prefix 전체 forward는0이다. 캐시 producer의 코드/config/조건/target/noise/geometry/model binding을 검사하고, 새 consumer 코드와 예산은 별도 manifest에 둔다. `fm_contract.py`의 수치 정의와 기존 공식 block/head/FA2 경로를 유지한다.

## 실행 순서

1. CPU 계약과 초기/캐시 계보 검증, 실행 코드·config·재생 기준 사전 고정.
2. TRAIN fresh worker1: initial 로딩 + fresh AdamW,0/20/50/100 고정4tuple 평가.20 replay 실패 시21이전 중단. checkpoint에는 adapter·optimizer moments/step·CPU/CUDA RNG·tuple cursor를 저장한다.
3. TRAIN 정상 종료·자원 회복 후 PROBE1 → S1 → D1. S는100endpoint만 설치하고 기존 조건과 실제 initial noise로40step/80forward. D전 final latent를 원자 저장한다.
4. 기존 baseline/20회 결과는 재생성하지 않고, source/0/20/100의17프레임·30fps를 비교한다.

실제 명령과 시도별 완료 단계는 비공개 `stages/*/reports`에 보존한다. 종료 후 guard/시도 파일을 지우고 재실행하는 절차가 아니며, 추가 실행은 이번 예산에 포함되지 않는다.

## 유지할 해석 경계

고정3tuple regression이며 sameclip holdout1개는 독립영상test가 아니다. D=Y shortcut과 positive-only 감독은 그대로다. 100update는40samplingstep과 다른 단위이며, 학습 loss 감소·checkpoint복원·실제 영상 품질은 각각 보고한다. 기존 typing 진단을 성공으로 바꾸기 위한 ignore나 전역 정리는 하지 않는다.

## 실제 종료 상태

TRAIN1은20회 adapter replay assertion으로 종료했다. 0/20 checkpoint와 평가를 보존했으며 PROBE/S/D는 실행하지 않았다. 본 문서의 실행 순서는 사전 계약이지100회 완료 기록이 아니다. 비공개 ZIP의 재현 자료는 원인 검토용이며 이번 실행을 자동 재개하는 승인이 아니다.

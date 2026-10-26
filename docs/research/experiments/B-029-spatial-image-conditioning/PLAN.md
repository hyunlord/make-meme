# B-029 — 기존 이미지 cross-attention의 위치별 재가중

사전 고정: 2026-10-26 03:34 UTC. B-028 완료 후 분기 A, 기준선 B-027. [DECISION](DECISION.md), [전체 수행 계약](../../work_orders/20261026-B028-to-method-research.md).

## 계산 계약

기존 `O=Wo(T+I)+b`에서 `O=Wo(T+g*I)+b`로 이미지 항만 변경한다. 텍스트·output bias·FlashAttention·reference VAE self-attention·RoPE·precision·가중치는 그대로다. generated query에서 `g=1+0.5*(E-mean_HW(E))`, 다른 reference/driving query는1. 모든 해당 block,40step,양 CFG에 동일하게 적용한다. OFF/lambda0은 기존 함수로 돌아간다. 실제 ref_length/additional_ref_length/seq_length/grid metadata로 범위를 확인하고 모든 입력에 통하는 상수를 만들지 않는다.

E는 기존 source instance support다. clip 전체 bbox의 긴 변10%를 올림한 반경의 정사각 dilation을 각 프레임에 적용하고, 영상 밖은0으로 clip, 고정7×7 평균 필터, 0..1 제한, 실제 generated token H/W로 area resize한다. 시간은 f0, f1..4, f5..8, f9..12, f13..16의 합집합을 사용한다. 시간 합집합→dilation→7×7 smoothing→area 순서를 고정한다. 이는 VAE receptive field의 명시적 근사이며 target RGB alpha가 아니다. CONTROL은 token H/W 각각 절반 cyclic shift, 평균/histogram/lambda/시간 순서 동일. 겹침을 사전 보고한다.

## 입력과 예산

기존 공개 animal/human/vehicle × R1/R2의 B-027 입력·cache16leaf·noise·RNG·scheduler를 읽기 전용으로 재사용한다. 새 encoder0, baseline 생성0. source_fps=null/preview24/17frame/896×512,40step80forward,UniPC/shift3/CFG5/seed20261022, replacement=True,history/additional_ref=None,adapter/ALG/manualRoPE OFF다.

METHOD6: animalR1,R2,humanR1,R2,vehicleR1,R2. CONTROL2: animalR1,vehicleR1. 각 sampler1/decode1, 실패 포함8회, 자동재시도0. 실행 순서는 각 과제 METHOD R1,R2 후 해당 CONTROL R1로 고정한다. 실제 final latent를 먼저 원자 저장한다. 입력·비유한값·안전 문제만 후속 중단 사유다.

전체 의뢰 deadline 2026-10-26 09:37 UTC. 방법 설계/구현/CPU검사는03:34부터 최대2시간. 기존72GiB 시작/24GiB headroom/swap0/타 서비스 보호/순차 fresh worker를 유지한다. 설치·학습·외부생성0. 이 CPU 지도/코드 추가로 효율 향상을 가정하지 않는다.

## 사전 검사와 관측

작은 CPU 검사6개 범위: OFF/lambda0, generated 범위, text/bias 불변, 지도 시간/공간/broadcast/finite, cache/noise/weights 불변, CONTROL 통계/공간 차이. 작은 fixture를14B 수치 동일성으로 주장하지 않는다. 첫 실제 forward에서 module 경로·SHA·runtime 범위·gate 통계를 기록하고 추가 forward0, dense attention dump0. 완료40step80forward 및 모든 block 적용 횟수를 확인한다.

## 평가

B-027의 사전 target 특징/동작 사건/보호 장면을 그대로 사용한다. human 보호 배경은 실제 관객·건초더미·포장면이며 과거 돌담 오기는 기존 시각 검토에서 정정됐다. 전체17장/local0/8/16, SOURCE/REFERENCE/BASE/METHOD 및 지정CONTROL을 제공한다. 외형, 방향·순서, 형태, 보호 영역 추가/소실, R1/R2민감도, 비용을 분리한다. source-copy/참조 정지 복사는 실패다. raw 보정·좋은 프레임 선별0. 연속 시청 없으면 temporal=UNVERIFIED. 이3과제는 방법 선택에 쓴 개발 패널이다.

실행 코드·지도·실제 입력 해시를 추가 고정하여 commit/push/remoteSHA 확인한 뒤 GPU를 시작한다. 종료 후 METHOD/RESULTS/ABLATIONS/COSTS/REPRODUCE/한국어 lessons, full 및 review-lite를 검증한다. 후속 자동 실행0.

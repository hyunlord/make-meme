# B-025 실행 전 고정

2026-10-25 11:10 UTC 착수, 15:10 UTC 작업 종료 상한. 시작 원격 HEAD `cf10a682ca136235a1ef737d953d4e059612e711`. 중복 B025 실행/완료 기록이 없음을 확인했다. 현재 입력·CPU 검사 완료, GPU NOT_RUN이다.

## 입력과 비교 계약

B024의 source f126..142, 17프레임/30fps/896×512 및 driving RGB/mask, 실제 noise/RNG/scheduler를 재사용한다. 두 참조를 첫 sampler 전에 고정한다. Lab은 B024 회색 RGB와 RED/BLACK mask를 그대로 사용한다. IG는 기존 사용자 원본 사진과 기존 개체 support를 사용한다. 원본의 파생사진과 원본 파일 hash는 서로 다르므로 동일 파일로 쓰지 않는다.

IG의 원본은 4000×3000이고 기록된 aspect-fit 683×512, 좌우 padding106/107을 적용한다. 기존 1600×1200 개체 support의 RGB 좌표 계보를 확인했다. support 밖/padding RGB128, 안의 resize RGB exact 보존, semantic RED/BLACK이다. 기존 얇은 발·꼬리 경계는 PARTIAL_UNRESOLVED이며 새 segmentation/수동 보정은 없다.

생성 전 root 및 별도 검토 에이전트가 원본/처리 참조/마스크 overlay를 정적으로 확인했다. 이는 독립 인간 ground truth가 아니다. Lab은 검은 짧은 털·넓은 주둥이/늘어진 귀·넓은 가슴과 굵은 앞다리, IG는 회갈색 짧은 털/흰 목가슴·길고 좁은 주둥이/접힌 귀·가늘고 긴 사지의 관측 방향을 평가한다. 참조 사진의 착석/누운 자세와 크기 차이는 보존한다.

공통 caption은 PLAN §4의 문장 그대로이며 negative는 empty다. 사용자 편집 의도는 '원본 장면과 자연동작을 보존하며 지정 참조 개체로 교체'이고 모델 caption과 별도다. B024의 외형 지정 caption 출력은 이번 중립 caption의 Lab 대조군이 아니다.

## 계산과 예산

공통 positive T5는 한 번만 계산한다. Lab VAE/CLIP는 B024에서 재사용하고 IG VAE/CLIP는 각각 한 번 계산한다. 두 cache는 별도 저장하며 pair 허용 변경은 양 CFG ref/CLIP/refmask 최대6leaf, 나머지10leaf와 device/tree 계약을 보존한다. 실제 mask가 같더라도 허용 변경 전부를 강제하지 않는다.

정식 replacement=True, history/additional_ref=None, adapter/ALG/manualRoPE OFF. seed20261022, UniPC40, shift3, CFG5 유지. REF_LAB과 REF_IG 각각 full sampler 최대1회/80forward, final decode 최대1회, probe 최대1회이며 자동 재시도는 없다. 두 입력 확정과 공개 코드 고정 뒤 순차 GPU worker만 실행한다. 첫 출력의 품질 실패는 두 번째 조건 생략 사유가 아니다.

기존72GiB 시작·24GiB 실행 headroom·swap0·서비스 보호를 유지한다. 첫 실제 forward의 참조 객체 연결만 기록하며 추가 관측 forward는 없다. final latent를 decode 전에 보존한다. 새 설치/모델/학습/외부 생성/imagegen/후처리 보정은0이다.

## 평가 경계

전체17장과 local0/8/16, 같은30fps에서 source/두 참조/두 raw 출력을 비교한다. 외형 반영·실제 개체 일치·동작·장면·형태를 따로 판단한다. reference RGB와 mask·자세가 함께 바뀌므로 순수 identity 효과나 encoder별 원인을 주장하지 않는다. 직접 연속시청 없으면 temporal=UNVERIFIED. 이 한 pair 후 종료한다.

## 종료 기록

상단은 실행 전 고정 당시 기록이다. 이후 ENC와 두 PROBE/S/D가 모두 완료됐고 신규 sampler2/2, retry0이다. 최종 상태와 기술/시각 판정은 RESULTS.md 및 MEASUREMENTS.md를 따른다. IG 외형 반응은 있으나 참조 누운 자세로 인해 결합 편집 목표는 FAIL이다. 추가 GPU 작업은 종료했으며 후속 실험을 예약하지 않는다.

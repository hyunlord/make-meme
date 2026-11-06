# V-005 사전 계획

작성: 2026-11-06 04:10 UTC. 실행 시작 인수: 04:05 UTC. 부모 b5b354cc422c2cbf9299f332c70f51812b9795f5, branch docs/v-research-20261103. 과거 판정과 산출물은 보존한다.

## 고정 계약과 실행 순서

첨부 의뢰서와 V005_SCENE_CONFIG.json을 기준으로 V004 S2의 같은 장면·크기·확대 canny·수용 앵커 11장을 재사용한다. 모델 코드 e98f6d927d83c92ef2be6aec76c8440b19306e39, 1152×640·73프레임·24fps, seed는 설정값 그대로다. Lab 1.115987460815047/IG 1.14의 기존 조건 파일을 hash로 재사용하고 재산정하지 않는다.

1. 사전 commit 및 R2 공식 지원 확인.
2. R1-a/R1-b: 두 단계 모두 공식 grid에서 요청 sigma에 가장 가까운 시작점을 선택. 1단계는 S2-s1 RAW의 VAE 인코딩을 초기 clean latent로, 2단계는 공식대로 1단계 결과를 spatial-upsample한 clean latent로 사용한다. 기존 GaussianNoiser의 flow-matching 혼합 및 조건 마스크를 보존한다. 단계별 실제 sigma/step/latent 계보 기록.
3. 출력 SAM과 R1 국소 합성, 신규 앵커 18/22/26/30 제작·게이트. 기존 11장은 그대로 유지.
4. R3-s1, 지원될 경우 R2-s1, 중간 비압축 폴더 전달. R2 미지원이면 이유를 표시하고 완료된 R1/R3-s1 전달.
5. R3-s2 및 지원될 경우 R2-s2, 전체 측정/뷰어/학습용 SAMPLE 기록/최종 전달.

## 결과 전 확인된 기술 제약

- 공식 distilled 두 단계 grid에서 요청 0.35와 0.55는 모두 0.421875로 매핑되며, 각 단계 남은 Euler step은 1개다. R1 두 셀은 요청 계약대로 기록하지만 실제 강도는 같으므로 서로 다른 강도의 인과 비교로 주장하지 않는다. 임의 sigma를 삽입하지 않는다.
- frozen IC-LoRA pipeline은 distilled-only이다. R2의 네 지원 조건 중 공식 비축소+IC-LoRA+키프레임 결합 경로가 충족되지 않으면 NOT_SUPPORTED로 남긴다. 별도 비축소 어댑터 경로 개발이나 다른 commit 전환은 하지 않는다. 상세 근거 R2_SUPPORT.md.
- 다리 최상단 점/회색 비율/경계 분산은 대리 지표이다. 사용자 보고 V004 개선은 사용자 관측으로 기록하며 이번 출력 자동 우열/성공 판정은 하지 않는다.

## 평가 정의

V004 기본·확대·방향·개체수·배경 지표를 그대로 적용한다. 추가 다리 측정의 좌표계·luma·Laplacian·경계·결측 및 국소 합성 규칙은 같은 scene config의 measurement_policy에 결과 전에 명시한다. 첨부 원본 hash도 함께 보존한다. 반사와 원본에서 관측되지 않은 crop 바깥은 제외한다. 결측은 null과 coverage로 표시하며 0점으로 채우지 않는다.

R1 전체 RAW/원본 배경 POST/국소 다리 합성은 별도 파생물로 보존한다. 지표는 frame14–34 평균/최대, 나머지 평균/비율과 전프레임 값을 남긴다. Kling 조명·크기 차이 때문에 직접 점수 비교로 해석하지 않는다. 품질 HUMAN_REVIEW_PENDING, 연속 지각 검수 temporal=UNVERIFIED.

## 환경·보호·예산

인수 때 동일 Spark 부팅, uptime12시간57분, 기존 hw.csv 5초 간격 갱신, GPU compute 없음, 디스크 여유429GiB를 관측했다. 펌웨어·입력 hash·guard 실측은 별도 기록한다. 연구 전용 기존 worktree가 부모 HEAD이며 깨끗한 상태였다.

신규 imagegen≤8, 생성/다듬기≤6, 학습0·품질재시도0. R2미지원 셀의 예산을 다른 변형에 전용하지 않는다. 6시간 실행 예산(외부 GPU 대기/다운로드 제외), 마지막30분 기록·전달. 보수적 신규 heavy cutoff09:35 UTC, 종료10:05 UTC(대기제외 연장 필요시 실제 장부만 적용). 모든GPU는 단일 흐름, CPU 문서/코드는 병렬 가능. 기존 drop-caches/allocator/100GiB cgroup/NVRM/OOM/PSI/메모리/외부GPU180초 관측을 유지한다. R2단일생성45분 초과시 중단하고 나머지seed생략. 전원차단 시 증거 보존 후 남은생성중단.

## 데이터 기록과 전달

개인 경로·사진·영상·마스크는 Git 제외. 출력별 비공개 SAMPLE.json과 V003/V004 소급12개를 경로/hash로 기록한다. 인간 판정은 PENDING, 기존 서술을 임의 학습 레이블로 바꾸지 않는다. 공개 dataset/SCHEMA.md만 게시한다.

필수 중간 전달1회 및 최종 Downloads/V005-review-실제날짜/index.html 비압축 폴더. RAW/POST, 14–34반복,0.25/0.5배속,RAW하체2배보기,선명도그래프,2프레임간격앵커시트,빈HUMAN_REVIEW 제공. Spark에서 먼저 완성한 후 Mac 전송과 hash 검증. 후속 생성/학습은 예약하지 않는다.

# B-003 사전 계획 — 구조 조건의 영향

상태: PLANNED. 작성 2026-10-22 01:32 UTC. parent B-002. 기준 문서 commit `dffcbb7f4c18c02feb2355a9aab857c99def3d5f`.

## 질문과 가설

R-bg를 고정하면 실제 Canny와 무정보 Canny의 차이가 출력 자세와 동작에 얼마나 영향을 주는가? 두 조건이 모두 착석하면 이 설정에서 구조 영향이 약하거나 reference 자세와 경쟁한다는 근거다. 실제 Canny가 원본 직립/발 위치에 더 가까우면 구조 경로가 유효하다는 근거다. 둘 다 실패하면 baseline/설정/표현 한계를 우선 검토한다. 두 seed로 전 모델의 능력을 일반화하지 않는다.

## 고정 및 개입

- 기존 Wan2.1-VACE-1.3B, revision `574e6a744642ce3bee319afc31496b88bde8aac4`, DiffSynth `f39d731a3e318d25b725eb3389cfddb184619842`.
- adapter=null, 학습 0, 새 모델/다운로드/native imagegen/외부 생성 API 없음. A 자산·코드·선택·장부 보존.
- B-002 R-bg SHA256 `d4d5ff988fa13f6b3c18165f1043c49e510baa12bffabb8a66c8a26865b8f2b2`. 같은 RGB decoder와 gray128 pad 사용.
- 기존 prompt/negative,512×288,17프레임,24fps,20steps,CFG5,vace_scale1,sigma_shift5,full-white video mask,BF16,SDPA,tiled VAE를 고정한다. 나머지 resolved defaults도 기록한다.
- C-real: 기존 source f0~16의 Canny70/150. C-null: 같은 RGB uint8 크기의 17개 all-zero 프레임. 원본 source와 reference는 바꾸지 않는다.
- RGB0은 image normalization 후 -1이며 latent0이나 VACE branch 제거가 아니다. reference와 mask 경로는 양쪽에 남는다.

## 실행 순서와 상한

1. C-real /20261022
2. C-null /20261022
3. C-real /20261023
4. C-null /20261023

네 셀 모두 신규 실행한다. 실패 포함 최대4회, 자동 재시도 없음. 동일 seed의 실제 noise/text/reference tensor와 조건 해시를 비교한다. 기존 B-002 출력은 참고 이력이며 이 네 셀의 대체물이 아니다.

전체 deadline 2026-10-22 03:26:56 UTC (시작01:26:56부터2시간), child도 이를 따른다. GPU heavy job 하나, 기존 다른 작업 중단 금지. 시작 MemAvailable40GiB 이상, 실행 중20GiB 미만 지속·swap증가·GPU오류·deadline 도달 시 자기 프로세스만 중단한다. source/reference/condition 입력 오류 또는 실패 시 원인을 기록하고 예산을 넘는 재실행을 하지 않는다.

## 사전 점검과 평가

실제 pipeline의 vace_video 전달, dtype/range/shape, VAE context 및 reference slice, adapter 부재를 확인한다. 같은 조건의 paired 비교에서 source→output 정답 영상이 없으므로 PSNR을 개체 교체 품질로 쓰지 않는다.

원본과 모든 출력의 f0/4/8/12/16 contact sheet, 대표 실제 프레임을 정적으로 관찰한다. 자세(착석/직립·지지발), 원본 동작 단계 대응, 검은 Lab 외형, 배경 복사, 귀/코/목/사지/몸통 형상을 구분한다. 연속 재생을 직접 관찰하지 못하면 시간 품질은 UNVERIFIED. 파일 재생 가능 여부와 관측을 구분한다. process/pipeline시간,CUDA peak allocated/reserved,시스템 메모리,실패를 기록한다.

## 제출과 종료

PLAN을 실행 전에 commit/push하고 주요 단계 기록 후 RESULTS·한국어 이론/질문/해설·HISTORY·ROADMAP을 갱신한다. 공개는 비민감 코드/설정/해시/요약만. 사진/원본/출력/개인 절대경로/전체로그/모델은 private ZIP에만 둔다. 작은 ZIP을 실제 Spark /tmp에 만들고 무결성 검사 후 Mac 전송 여부를 명시한다. 비교 한 번 뒤 종료하고 다음 실험 하나만 제안한다. 전체제작·IG·윙크·킥·Kling 수용은 NOT_RUN.

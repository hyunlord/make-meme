# make-meme 연구 기록

이 디렉터리는 작업의 **방향성, 목표, 로드맵, 실험 의도, 결과, 결정 이유**를 지속적으로 남기는 기준 기록이다. ZIP과 대화는 보조 전달 수단이며, 연구 이력의 유일한 저장소로 쓰지 않는다.

## 먼저 읽을 문서

1. [연구 방향과 트랙 경계](CHARTER.md)
2. [로드맵](ROADMAP.md)
3. [누적 히스토리](HISTORY.md)
4. [모든 작업에 적용할 기록 규칙](RECORDING_PROTOCOL.md)
5. [최근 실험: B-013 Lab driving 전이 비교](experiments/B-013-lab-driving-transfer/RESULTS.md)
6. [새 실험 문서 양식](templates/EXPERIMENT.md)

## 현재 상태 — 2026-10-24

B-013은 동일 구간의 Lab MOV/STILL을 각각 한 번 생성하고 종료했다. 실행·조건 통제 PASS, 전신 직립 FAIL, 국소 반응 PARTIAL, temporal UNVERIFIED다. [결과](experiments/B-013-lab-driving-transfer/RESULTS.md) · [한국어 이론](lessons/B-013-cross-identity-driving.md). 다음 연구 제안은 한 가지만 남겼으며 추가 추론·학습은 실행하지 않았다. A는 계속 보존·동결한다.

## 초기 상태 — 2026-10-22 기록 보존

- A: native imagegen 전용 MCP 실험. 기존 자산과 이력은 보존하고 추가 생성·보정 확장은 동결한다.
- B: DGX Spark에서 로컬 모델을 이해하고 학습·추론·개선하는 연구·학습 트랙.
- B-001: 첫 야간 실험 완료 보고가 있다. toy Flow Matching과 VACE LoRA의 학습 경로, 학습 도시 장면의 복원 개선을 확인했다고 보고됐다. Lab 춤 전이는 별도의 미학습 baseline에서 실패했다. 일반화·시간 품질·서비스·논문 성과는 미확인이다.
- B-002: **통제 비교 COMPLETED**. 신규5회 완료+기존1개 재사용. 두 seed에서 배경 복사는 줄었으나 착석은 유지했다. 개체·춤 전이는 미수용, 시간 품질은 UNVERIFIED. [결과](experiments/B-002-reference-background/RESULTS.md) · [이론](lessons/B-002-conditioning.md).

## 이 문서 브랜치의 범위

이 초기 문서 세트는 원격 `main`의 scaffold를 기준으로 추가한 **문서 전용 변경**이다. 로컬 Spark/Mac의 B 실험 코드나 미추적 파일이 이 브랜치에 모두 들어 있다는 뜻이 아니다. 이 브랜치를 실행용 코드의 최신본으로 오해하지 않는다.

실행 담당 에이전트는 기존 로컬 실험 환경을 보존하고 문서만 안전하게 가져온다. 결과를 기록할 때 실제 실행 스크립트·설정의 revision 또는 content hash를 함께 남기고, 필요한 비민감 연구 스크립트도 명시적으로 버전 관리한다.

## 작업의 기본 순서

`기존 기록 읽기 → 목표·가설·상한 사전 기록 → 실행 → 관측 기록 → 해석과 한계 → 다음 결정 → Git commit/push 확인`

실패한 결과도 남긴다. 결과를 보며 바뀐 계획은 변경 사유와 함께 기록한다. 실험 실패와 문서 동기화 실패는 별도 상태다.

공개 저장소이므로 개인 사진·원본 동영상·토큰·개인 경로·대형 모델/캐시/로그를 자동으로 올리지 않는다. 실행 자료는 로컬에 보관하고 공개 문서에는 비민감 요약·재현 명령·자산 별칭·해시를 남긴다.

B-002 실행 이후에는 선별한 비민감 실행 코드·설정·검증 요약을 추가했다. 여전히 실제 자산과 전체 실행 환경을 포함한 checkout은 아니다.

B-003: **COMPLETED**,4/4추론·0학습. 두 seed 모두 real착석/null사족으로 구조 영향은 확인됐으나 원본 직립 춤은0/4. 시간UNVERIFIED. [결과](experiments/B-003-structure-condition/RESULTS.md) · [이론](lessons/B-003-structure-conditioning.md).

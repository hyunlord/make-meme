# C-013 Codex 실행 의뢰 보존

2026-11-02 현재 세션의 사용자 실행 지시를 적용한다. 이것은 새 실험 번호나 별도 승인 요청이 아니다. 전체 실행 세부는 사전 [PLAN](../experiments/C-013-frozen-unseen-path-generalization/PLAN.md)과 동봉 원본 [PATHS](../experiments/C-013-frozen-unseen-path-generalization/PATHS.json)에 고정한다. 아래는 실행 계약 전사 요약이며 원문 전체 사본이라고 표시하지 않는다.

- C-012 checkpoint2048 동결, 새 학습0. I25/I50/I75/S 미학습 경로 일반화와 seed20261029 BASE 배경 대조를 실제 실행한다.
- 승인: 기존 자료/SSH 읽기, 작은 CPU 경로·평가기·설정, 신규5영상, 한국어 결과/검토자료, 이번 파일만 연구 branch commit/push, 기존 Spark/Mac 전달.
- 금지: optimizer/backward, seed/CFG/scale/checkpoint 탐색, 모델/데이터/패키지 설치·다운로드, imagegen/SAM/CoTracker/DragAnything/14B, target/endpoint 신규 encode·FM probe, 구조·dtype·sampler 변경, 후합성/warp/복원/업스케일/보간/endpoint 덮어쓰기, 가드 완화, 타 작업 종료·환경변경·파일삭제.
- 경로 공식/9점 offsets/정규화/sidecar whitelist/추론 설정/50step50call은 PLAN/PATHS와 부모 코드를 따른다. 입력 및 평가 경로 동일. 양끝은 부모 tensor exact 복사, 기존 앵커 파일 사용.
- 순서 BASE_S2/I25_S1/I50_S1/I75_S1/S_S1. 정상 sampler5, 예비 기계복구1, hard cap6; 품질 재시도0. 총2시간, 마지막20분 전달. 모델 적재 후 실패도 예산 장부에 남긴다.
- 안전·권한·자료 문제는 정확히 기록하고 해당 부분 중단. 입력/평가기 실패를 능력 실패로 해석하지 않는다. 기존 결과·변경·raw 보존. 이전 세션 복원 불필요.
- Q1 보간 가운데 y96/120/144 여부, Q2 요청 vs 학습A/B attraction, Q3 S 순서, Q4 단일 공/무늬/형태/배경, Q5 seed2 BASE 손상, Q6 ON 추가 변화, Q7 일반화 범위와 다음 요소 하나를 최종 보고한다.
- 위치/외형/배경/시간 품질 분리. temporal=UNVERIFIED without continuous perceptual review. 추가 학습·seed·경로·외부모델 자동 실행/예약 금지.

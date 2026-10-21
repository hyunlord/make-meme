# 모든 연구 작업의 GitHub Markdown 기록 규칙

이 규칙은 특정 코딩 도구나 세션에 의존하지 않는다. Codex/Claude Code/사람 모두 같은 연구 기록을 사용한다.

## 1. 저장소에 남기는 것

- `CHARTER.md`: 연구 방향, 장기 목표, A/B 경계, 성공 정의. 방향이 바뀔 때 변경 이유를 기록한다.
- `ROADMAP.md`: 전체 단계, 현재 위치, 다음 조건부 단계. 완료/계획/보류를 구분한다.
- `HISTORY.md`: 날짜별 목표, 실제 작업, 관측, 결정, 실패, 근거 링크. append-only.
- `experiments/<ID>/PLAN.md`: 실행 전에 정한 질문·가설·변수·예산·평가·중단 조건.
- `experiments/<ID>/RESULTS.md`: 실제 실행한 조건·결과·미실행·해석·한계·다음 한 가지 결정.
- `lessons/<ID>-<topic>.md`: 수학과 실제 코드·실험의 연결, 이해 질문과 별도 해설.
- `decisions/<ID>.md`: 여러 선택지 중 왜 특정 방향을 택했는지 중요한 결정에 한해 기록. 사소한 변경마다 파일을 만들지 않는다.

같은 내용을 여러 문서에 길게 복제하지 않는다. CHARTER/ROADMAP은 요약, PLAN/RESULTS는 실험 세부, HISTORY는 사건과 이유를 남긴다.

## 2. 작업 전

1. 현재 저장소 URL, branch, HEAD, git status, 기존 agent 지시와 연구 문서를 읽는다.
2. 로컬 실행 checkout과 문서 branch가 같은 코드라고 가정하지 않는다. 원격 `main`에는 로컬 미추적 실험 코드가 없을 수 있다.
3. `PLAN.md`에 experiment_id, 작성 시각, parent experiment, 목표, 사전 가설, 변경 변수, 고정 변수, 자원 상한, 평가/중단 조건을 적는다.
4. 연구 방향이나 순서가 바뀌면 ROADMAP/HISTORY에 이유를 적는다.
5. 실행 전 계획을 커밋한다. 가능한 경우 실험 전 문서 branch에 push한다. 네트워크 문제로 push가 안 되어도 로컬 기록을 보존하며, 공개된 척하지 않는다.

기존 AGENTS.md/CLAUDE.md가 있으면 읽고 보존한다. 실제 실행 checkout의 적절한 범위에 이 문서를 먼저 읽도록 짧은 링크 규칙만 추가할 수 있다. 사용자의 기존 규칙을 덮어쓰거나 전역 설정을 변경하지 않는다.

## 3. 실행 중

- 주요 단계 종료·실패·설정 변경 때 HISTORY와 RUNNING 메모를 갱신한다. 모든 셸 명령마다 긴 문서를 만들 필요는 없다.
- 결과를 본 뒤 계획을 바꾸면 원래 계획을 지우지 않는다. amendment에 시각·이유·영향받는 run을 남긴다.
- run ID, config hash, 실행 코드 hash/commit, weight revision/hash, 입력/조건/noise hash, 자원·실패·출력 위치를 기록한다.
- 모델의 현재 상태, 이전 실험 가중치가 남았는지, hook이 동작을 바꿨는지를 확인한다.
- private 절대 경로와 토큰이 섞이는 raw log는 로컬에만 보관하고 공개 요약을 분리한다.

## 4. 작업 종료

- RESULTS에 실제 완료/실패/미실행, 관측 사실, 가설, 한계, 다음 한 가지 실험을 분리한다.
- ROADMAP 현재 상태와 HISTORY를 갱신한다. 실패도 결론이므로 삭제하지 않는다.
- 실행 코드·설정·작은 검증 테스트는 필요한 파일만 명시적으로 stage한다. `git add .`로 개인 자산을 함께 넣지 않는다.
- 수정 범위와 secret/private asset diff를 검사한 뒤 commit한다.
- 이미 확인된 `hyunlord/make-meme` 연구 branch로 push하고 원격 HEAD가 로컬 commit과 같은지 확인한다.
- main에 바로 push하거나 강제 push, reset/clean, 기존 branch 히스토리 재작성, 자동 PR merge는 하지 않는다.
- 인증 실패·충돌·원격 branch 이동이 있으면 우회하지 않는다. 로컬 commit/patch를 남기고 `SYNC_PENDING`과 이유를 보고한다. 기존 작업을 지우지 않는다.

최종 보고에는 branch, 실제 commit SHA, 원격 반영 여부, GitHub 문서 위치를 포함한다. 로컬 MD 작성만 해 놓고 GitHub 기록을 완료했다고 하지 않는다. 자기 자신의 commit SHA를 같은 commit의 파일에 미리 적으려 하지 말고, final response 또는 후속 기록에서 commit을 참조한다.

## 5. 공개·비공개 분리

이 저장소는 공개다. 연구 계획을 GitHub에 남기라는 지시를 원본 데이터 공개 허가로 확대하지 않는다.

기본 공개 가능 범위: Markdown, 비민감 설정, 재현 스크립트, 소형 익명화 지표, 모델/입력/출력의 해시, 자산 별칭, 공식 출처 링크.

기본 제외: 원본 반려동물 사진과 개인 영상, 미공개 출력, 얼굴/집 내부, 음원·권리 불명 자료, 모델 weights, adapter/optimizer 실물, latent cache, venv, 다운로드 dataset, private IP·SSH 계정·토큰·개인 디렉터리, 전체 raw log.

공개 설정은 `${DATA_ROOT}`/`${MODEL_ROOT}`/`${RUN_ROOT}` 등으로 경로를 표현하고 실제 경로 매핑은 로컬에 둔다. 원본 사진을 임의로 익명화해서 올리는 일도 하지 않는다.

## 6. 재현성과 근거 수준

최소 재현 단위는 다음이다.

`experiment ID + PLAN revision + 실행 코드 commit/hash + model revision + 입력/condition/noise hash + resolved config + 실제 출력 + 실행 명령`

seed가 같다고 GPU의 byte-identical 결과를 보장하지 않는다. 독립 실행으로 확인하지 않은 결과는 '보고됨/기록 검토'와 '직접 재실행'을 구분한다.

연구 코드가 로컬에만 있다면 소스 없는 hash만으로 완전 재현이 가능하다고 주장하지 않는다. 이번 실험에 필요한 비민감 실행 스크립트를 명시적으로 추적하고, 공개할 수 없는 입력의 제공 조건을 적는다.

## 7. 가벼운 완료 검사

체크할 것은 PLAN/RESULTS/HISTORY/ROADMAP의 링크·상태·변수·한계가 일관되는지, run_manifest와 설명이 같은지, 실제 remote 반영이 됐는지다. 복잡한 승인 상태 머신이나 새 CI 시스템을 먼저 만들지 않는다.

실험 상태(PLANNED/RUNNING/COMPLETED/BLOCKED)와 동기화 상태(PUSHED/SYNC_PENDING)는 별도로 기록한다. 특정 성능 수용 항목이 NOT_RUN/UNVERIFIED인 것과 통제 실험을 완료한 것도 구분한다.

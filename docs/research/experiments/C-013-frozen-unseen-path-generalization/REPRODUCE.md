# C-013 실행 계보

현재: 승인된 resume1의5영상 생성·평가 완료. 아래 최초 시도 부분은 역사 기록이며 현재 미완료 상태가 아니다.

부모: C-012 @ 6fba3a00d587bc0f130420e0f5b8c264b5e7a548. 사전 계획 commit c515cc8. 실제 절대경로와 SSH 정보는 공개하지 않는다. 기존 연구 Python, 모델, tokenizer, VAE, C-012 task/cache/checkpoint/trace를 비공개로 그대로 사용한다.

## 최초 시도: 실제 수행
1. 동봉 PATHS.json byte 동일 복사 및 공식 검증.
2. `RESEARCH_PYTHON code/prepare.py PARENT_ROOT C013_ROOT` (CPU): checkpoint hash, sidecar whitelist,33×9×2 positions, 양끝·공유 field exact, 원자 저장/readback. PREPARE.json.
3. 부모 `make_stage.py`로 C-013 전용 stage config 생성. 부모 `code/gen/generate_video.py`를 그대로 연결했다. C-001 run_guarded.py + C-003 guard 변경 없음. stage 이름에 c013과 run을 넣었다. 기존 make_stage의 C012 binding 문구/4시간 내부 deadline은 상속되었지만 실제 세션2시간 제한이 우선하며, 첫 admission 중단 직후 종료했다.
4. 첫 cpu route에서 START_SWAP_BUDGET, exit2. heavy route 실행 안 함. stage 폴더 존재를 실행 완료로 해석하지 않는다.
5. Mac에서 criteria.py 기하 contract와 모든 새 Python AST syntax 확인. 이미지 fixture는 미실행.

## 최초 시도의 코드 상태
- prepare.py: Spark CPU 실제 실행/readback 확인.
- criteria.py: Mac 순수 기하 검사 통과.
- parity.py: 실제 생성 trace 비교용. 실행할 새 출력이 없어 NOT_RUN.
- evaluate_paths.py: 부모 Reader/renderer 재사용 scaffold. fixture/evaluate 모두 NOT_RUN. 검증 완료된 평가기로 간주하지 않는다.
- 부모 생성기·검출기·가드 소스는 수정하지 않았다.

## 최초 시도 종료 당시 재현 안내
기존 안전 조건을 충족하고 재개가 허용된 경우, 기존 C-013 RUNS/실제 outputs를 확인하여 완료 셀을 중복 실행하지 않아야 한다. 현재 완료 셀은0이다. 기존 stage/실패 증거를 덮어쓰지 않는다.

CPU fixture의 명령 형태: `RESEARCH_PYTHON code/evaluate_paths.py PARENT_ROOT C013_ROOT fixtures`. 검출 fixture가 통과하기 전 실제 출력 평가 금지. 생성은 기존 guarded cpu→heavy 경로와 원래 순서/예산을 유지한다. 각 출력 뒤 `python code/parity.py PARENT_ROOT C013_ROOT RUN_ID`. 마지막 `... evaluate_paths.py ... evaluate`는 다섯 출력이 실제로 존재할 때만 사용한다.

parity는 full96 context, initial latent, text hash,50개 sigma/timestep/CFG, 전체 condition/mask PNG bytes, point shared hash,50step/50call,latent readback을 비교한다. 새로운 forward는 없다. 원본 MP4/raw/PNG/latent는 비공개 원위치에 보존한다.

## 최초 시도 전달
DELIVERY.json의 패키지는 중단 기록용이다. 신규/과거 MP4, 가중치, latent, private stage 설정/raw log는 포함하지 않는다. 정상 영상 viewer 요구는 미충족/NOT_RUN으로 남긴다.


## 2026-11-02 승인된 resume1 (위 최초 중단 기록 보존)

정책 승인과 사전 기록은 40cf524. 공통 guard는 수정하지 않고 C-013/resume1/guard에 원본 네 파일을 복사했다. memory.py만 code/resume-memory.patch의 두 줄을 제거했다. safety/policy/supervisor는 원본과 byte 동일 검사. CPU와 heavy의 guard_code는 같은 C-013 사본이며 freeze는 그 실제 파일들을 가리킨다. 각 단계에서 freeze readback을 확인한다.

기존 make_stage.build(ROOT, NAME, KIND, PARENT_GENERATOR, CONFIG_ARGS, INPUTS, OUTPUTS, DEADLINE)를 사용했다. NAME은 c013-resume1-RUN_ID, KIND는 cpu/heavy. C012_STAGE_SETTINGS는 부모 설정에서 guard 절대경로만 C-013 사본으로 바꾼 private JSON. 새로운 supervisor/launcher는 없다. 기존 guarded 실행 명령을 순서대로 호출하는 shell만 사용했다. deadline은 재개 실행 시작+90분으로 실제 바인딩했다. 과거 c013-BASE_S2-cpu 상태를 재사용하거나 baseline을 덮어쓰지 않는다.

사전 live 관측은 observe+MemoryBudget.inspect(start=True)로6회/2초 간격. 실제 cpu/heavy admission은 기존 supervisor가 각각 충분한10초 관측을 다시 확보한다. 각 stage의 baseline은 그 stage의 실제 첫 sample이며 worker 생애 중 재설정하지 않는다. 모든 stage 시작값과 이후 증가량은 RUNS에 공개 요약하고 원자료는 private로 보존한다.

Spark 기존 연구 Python에서 check_resume_policy.py와 evaluate_paths.py ... fixtures 수행. 후자는 실제 전체화면 Reader와 renderer를 사용하며4개 새 oracle 최대 오차가1px 미만인지, 빈 배경/두 공/이동 배경/학습A·B 반례를 확인한다. 이후 생성5셀, 각 parity.py, evaluate_paths.py ... evaluate, build_review.py 순서. 새 이미지 학습·target/endpoint encode·외부모델·설치 없이 실행한다.

검토 페이지는 원 MP4와 전33PNG를 복사한다. 시트는3×3 주시점 파생물, SVG는 요청 선과 측정 점, oracle은 평가 정답이라고 명시한다. 브라우저 재생/slider 검증은 연속 지각 검수가 아니다.

현재 재현 근거: RUNS.json의5개 parity·10개 guard 종료, FIXTURES.json, METRICS.json, BROWSER_QA.json. 완료 셀을 중복 생성하지 않는다. 최종 패키지는 DELIVERY.json 참조. 최초 중단 자료는 historical-attempt01에 보존한다.

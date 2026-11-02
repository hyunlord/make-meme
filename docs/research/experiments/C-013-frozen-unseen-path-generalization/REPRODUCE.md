# C-013 실행 계보 및 미완료 지점

부모: C-012 @ 6fba3a00d587bc0f130420e0f5b8c264b5e7a548. 사전 계획 commit c515cc8. 실제 절대경로와 SSH 정보는 공개하지 않는다. 기존 연구 Python, 모델, tokenizer, VAE, C-012 task/cache/checkpoint/trace를 비공개로 그대로 사용한다.

## 실제 수행
1. 동봉 PATHS.json byte 동일 복사 및 공식 검증.
2. `RESEARCH_PYTHON code/prepare.py PARENT_ROOT C013_ROOT` (CPU): checkpoint hash, sidecar whitelist,33×9×2 positions, 양끝·공유 field exact, 원자 저장/readback. PREPARE.json.
3. 부모 `make_stage.py`로 C-013 전용 stage config 생성. 부모 `code/gen/generate_video.py`를 그대로 연결했다. C-001 run_guarded.py + C-003 guard 변경 없음. stage 이름에 c013과 run을 넣었다. 기존 make_stage의 C012 binding 문구/4시간 내부 deadline은 상속되었지만 실제 세션2시간 제한이 우선하며, 첫 admission 중단 직후 종료했다.
4. 첫 cpu route에서 START_SWAP_BUDGET, exit2. heavy route 실행 안 함. stage 폴더 존재를 실행 완료로 해석하지 않는다.
5. Mac에서 criteria.py 기하 contract와 모든 새 Python AST syntax 확인. 이미지 fixture는 미실행.

## 현재 코드 상태
- prepare.py: Spark CPU 실제 실행/readback 확인.
- criteria.py: Mac 순수 기하 검사 통과.
- parity.py: 실제 생성 trace 비교용. 실행할 새 출력이 없어 NOT_RUN.
- evaluate_paths.py: 부모 Reader/renderer 재사용 scaffold. fixture/evaluate 모두 NOT_RUN. 검증 완료된 평가기로 간주하지 않는다.
- 부모 생성기·검출기·가드 소스는 수정하지 않았다.

## 조건부 재현 순서 (이번 세션 자동 실행 없음)
기존 안전 조건을 충족하고 재개가 허용된 경우, 기존 C-013 RUNS/실제 outputs를 확인하여 완료 셀을 중복 실행하지 않아야 한다. 현재 완료 셀은0이다. 기존 stage/실패 증거를 덮어쓰지 않는다.

CPU fixture의 명령 형태: `RESEARCH_PYTHON code/evaluate_paths.py PARENT_ROOT C013_ROOT fixtures`. 검출 fixture가 통과하기 전 실제 출력 평가 금지. 생성은 기존 guarded cpu→heavy 경로와 원래 순서/예산을 유지한다. 각 출력 뒤 `python code/parity.py PARENT_ROOT C013_ROOT RUN_ID`. 마지막 `... evaluate_paths.py ... evaluate`는 다섯 출력이 실제로 존재할 때만 사용한다.

parity는 full96 context, initial latent, text hash,50개 sigma/timestep/CFG, 전체 condition/mask PNG bytes, point shared hash,50step/50call,latent readback을 비교한다. 새로운 forward는 없다. 원본 MP4/raw/PNG/latent는 비공개 원위치에 보존한다.

## 전달
DELIVERY.json의 패키지는 중단 기록용이다. 신규/과거 MP4, 가중치, latent, private stage 설정/raw log는 포함하지 않는다. 정상 영상 viewer 요구는 미충족/NOT_RUN으로 남긴다.

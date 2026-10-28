# 고정 구현의 한정 재개 계보

이번 EXPECTED_ABSENT_02는7개 runtime Python 파일을 직전 고정본에서 byte-identical로 복사했다. 기존 입력·noise·E/M·clean_constraint 및 historical allowed snapshot은 유지했다. config의 새로운 root/unit/resume ID/deadline과 이번 사용자 승인만 갱신했다. 구현이 literal로 검사하는 기존 policy attempt_id는 고정 구현 식별자로 남기고 실제 실행 식별자는 resume_attempt_id로 별도 기록했다.

기존 worker의 --preflight-only를 각 stage에 실행하여48개 파일·loader report 경로·현재 안전 조건을 확인했다. 새 테스트는 실행하지 않았다. 사전 commit 이후 S supervisor만1회 호출했다.

```sh
"$EXISTING_PYTHON" "$FROZEN_CODE/worker.py" "$STEP_S_ROOT" --preflight-only
"$EXISTING_PYTHON" "$FROZEN_CODE/worker.py" "$STEP_D_ROOT" --preflight-only
"$EXISTING_PYTHON" "$FROZEN_CODE/supervisor.py" "$STEP_S_ROOT"
```

마지막 명령은 이미 모델/sampler 시도를 소비했다. 같은 root나 다른 root로 자동 재시도하는 명령이 아니다. STEP_D는 호출하지 않았다.

실제 시작3표본은 CLEAR/swap0였고, CPU staged loading 및 cache 복원 뒤 DiT device 이동 도중 시스템 swap256KiB를 관측해 기존 guard가 자체 worker를 종료했다. 최종 unit inactive와 GPU 목록 비어 있음은 정리 증거이며 정상 모델 완료 증거가 아니다. 마지막 counter receipt가 없으므로 완료40/80/40을 만들지 않는다. STEP 방법 효과는 미검증이며 과거 BASE/CONTROL 판정도 유지한다.

종료 후48개 frozen 파일을 다시 hash 확인했다. full weights를 재해시하거나 커널·환경·서비스·swap 설정을 변경하지 않았다. 새로운 media가 없어 실패 근거와 작은 실행 기록만 전달한다.

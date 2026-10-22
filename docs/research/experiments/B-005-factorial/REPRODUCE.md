# B-005 재현 및 계보

시작 원격 HEAD `582e67ca0b153b5d602b04587b9f57cd36ad3426`, 실행 고정 `ac0ecbec709ac72a36668ed22f2d09a42577f257`을 push/원격대조한 뒤 실행했다. PLAN은 변경하지 않았다.

## 실행본과 공개본

기존 Spark B-001 격리환경과 Wan2.1-VACE-1.3B revision `574e6a744642ce3bee319afc31496b88bde8aac4`, DiffSynth commit `f39d731a3e318d25b725eb3389cfddb184619842`를 사용한다. 모델9파일과upstream핵심5파일 재해시는 reuse_audit.json에 있다. 전체upstream tree 인증은 아니다.

공개 config의 `${BASELINE_ROOT}`, `${B002_ROOT}`, `${B003_ROOT}`, `${B004_ROOT}`, `${RUN_ROOT}`, `${B_ROOT}`는 접근 권한이 있는 로컬 경로로 치환한다. runner가 자동 환경변수 확장을 하는 것은 아니다. private ZIP은 실제 config와 경로를 보존한다. 공개 code는 개인경로만 별칭화하여 실행본SHA와 다를 수 있다. 모델·개인 원본은 공개하지 않으므로 공개파일만으로 동일 입력을 복원할 수 없다.

## 순서

1. audit_reuse.py: 기존6개 actual_input_hashes·source/condition/reference/mask 실제 decode, 고정config/runtime, CPU 초기noise, 모델·script 무결성.
2. 신규 config2개와 실행code hash 고정·commit/push 후 PREREGISTRATION 기록.
3. 다음 launcher를 seed별 한 번씩 순차 실행. 종료코드가 실패여도 소비하며 재시도하지 않는다.
4. validate_runs.py로 신규2+기존6의 전체factorial context 및 파일·시간축 검증.
5. tools/review_outputs.py로 동일17프레임24fps 비교. tools/package_review.py로 private ZIP 및 CRC/payload SHA 검증.

```sh
CUDA_MODULE_LOADING=LAZY OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 "$BASELINE_ROOT/.venv/bin/python" "$RUN_ROOT/scripts/launch_video.py" "$RUN_ROOT/configs/R-gray-C-null-20261022.json" R-gray-C-null-20261022
# 첫 실행 종료 후 seed20261023도 같은 환경으로 한 번.
```

이는 이번 수행 경로 기록이며 추가 실행 승인이 아니다. launcher의소비장부·deadline을 지우거나 새 실험으로 횟수를 초기화하지 않는다. config의 과거 max_updates필드는 inference에서 사용하지 않으며 실제학습0이다. resolved_defaults는 pinned source/call 근거이며 모든 scalar를 runtime hook으로 채취했다는 뜻이 아니다.

## 재사용·출력

|B005 표시|실제 원본|
|---|---|
|bg-real|B003 outputs/C-real-{seed}|
|bg-null|B003 outputs/C-null-{seed}|
|gray-real|B004 outputs/R-gray-{seed}|
|gray-null|B005 outputs/R-gray-C-null-{seed}|

기존6개 복사본의480개파일은 byte hash대조한다. initial_noise.pt는원격원본에남기고ZIP에서는제외하며actualtensorhashJSON은보존한다. 2×2 배치의 행은bg/gray,열은real/null이다. 파일검증과 실제연속재생 품질검토는별개다. 보간·프레임복제·시간축변경없음. 원본은다른개체의동작영상이며실제Lab정답영상이아니다.

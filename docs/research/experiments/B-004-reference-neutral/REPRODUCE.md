# B-004 재현 경로

PLAN 기준 원격 b08f4a5a163bd0e8256a2c7491585dd9074cc2e9, 실행 고정 eafa250e9d03818bf6b94e69f3d2ae657076ec98. 모델/upstream revision과 hash는 RESULTS/reuse_audit 참조. 공개 설정의 `${BASELINE_ROOT}`, `${B002_ROOT}`, `${B003_ROOT}`, `${RUN_ROOT}`, `${B_ROOT}`는 사용 권한이 있는 private 경로로 치환해야 한다. 자동 환경변수 확장 코드는 없다. 원본 자산은 공개하지 않으므로 공개파일만으로 동일 입력을 복원할 수 없다.

실제 실행 순서: audit_reuse.py로 모델/입력/CPU noise 대조 → 코드 commit/push 확인 → PREREGISTRATION.json 및 코드 해시 저장 → 아래두run순차 → validate_runs.py → review_outputs.py → package_review.py. 기존 소비 장부를 지우거나 새 project로 재시도하지 않는다. 아래는 수행 기록이며 추가 실행 승인이 아니다.

```sh
CUDA_MODULE_LOADING=LAZY OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 "$BASELINE_ROOT/.venv/bin/python" "$RUN_ROOT/scripts/launch_video.py" "$RUN_ROOT/configs/R-gray-20261022.json" R-gray-20261022
# 첫 프로세스 종료 후 같은 환경으로 seed20261023 한 번
python reports/validate_runs.py "$RUN_ROOT" "$B003_ROOT"
python tools/review_outputs.py "$RUN_ROOT" "$BASELINE_ROOT"
python tools/package_review.py "$RUN_ROOT" /tmp/make-meme-B-004-20261022.zip
```

launch cap2/globaldeadline는 실험의 과거 운영 제한이다. 새 실행은 별도 승인·시간창 필요. PRIVATE ZIP에는 실제 경로 매핑/config/두attempt 장부와 재사용 계보가 있다. SHA는 공개용 별칭 치환 전 실행본을 기준으로 하므로 공개code와 byte동일하다는 주장이 아니다. 패키지는 모델/venv/cache/noise.pt를 제외하며 initial_noise.json의 actualtensorhash를 보존한다. 관측도구는 RNG before/after 동일을 검증했다.

리뷰 비교 영상 좌→우: source | R-bg | R-gray. 17frames/24fps=.708333초. 보간·프레임 복제·속도변경 없음. 두seed모두포함, static검토와 temporal UNVERIFIED 구분.

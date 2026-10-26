# B-030 재현 계약

기존 pinned SCAIL 환경만 사용한다. `${B027_ROOT}`, `${B030_ROOT}`, `${PINNED_PYTHON}`는 비공개 로컬 경로다. 완료된 case의 attempt를 삭제하거나 같은 예산으로 재실행하지 않는다.

```sh
# CPU only; original B027 cache is read-only
CUDA_VISIBLE_DEVICES='' "$PINNED_PYTHON" -m pytest -q code/test_crossover.py code/test_contract.py
for task in human vehicle; do
  CUDA_VISIBLE_DEVICES='' "$PINNED_PYTHON" code/prepare_layout.py "$B030_ROOT/tasks/$task" "$B027_ROOT/tasks/$task" "$B030_ROOT/code"
  "$PINNED_PYTHON" code/freeze_run.py "$B030_ROOT/tasks/$task"
done
# Only after the plan/code/config/visual preregistration is committed
bash code/run_all.sh "$B030_ROOT" "$PINNED_PYTHON"
```

`cases/R1`은 Y12(VAE+mask R1, CLIP R2), `cases/R2`는 Y21(VAE+mask R2, CLIP R1)다. 실행 순서는 human Y12 → human Y21 → vehicle Y12 → vehicle Y21. 각 case는 PROBE → S → D의 fresh worker이며 직전 process 종료·실제 결과를 확인한다. sampler와 decode 각각 4회 상한, 자동 재시도 0회다.

CPU cache 파생은 두 `clip_fea` leaf(t2,t8)만 바꾸며 나머지14leaf·16leaf tree/device/container·noise 파일·RNG·scheduler는 행의 B027 기록을 유지한다. `contracts.py`는 두 원래 producer receipt를 먼저 확인한 뒤 파생 receipt와 expected-diff를 확인한다. 새 cache는 B030에서만 기록하며 B027 provenance를 덮어쓰지 않는다.

실제 forward의 positive/negative 첫 호출에서 ref/clip/mask object와 hash 계보를 기록한다. 공식 upstream SHA 검증과 baseline 추출 sampler/loader를 그대로 유지하며 B029 gate 소스는 포함하지 않는다. P/encoder 0회, attention 관측을 위한 추가 forward 0회다.

사전 CPU fixture는 6 tests PASS이며 작은 tensor 경계 검사다. 실제14B 수치 동등성·시각 품질 검사가 아니다. compileall과 shell syntax PASS. ruff/basedpyright 실행파일이 현재환경에서 발견되지 않아 static typing은 NOT_CLEAN/UNVERIFIED로 유지하며 설치나 전체 타입 리팩터링은 하지 않았다.

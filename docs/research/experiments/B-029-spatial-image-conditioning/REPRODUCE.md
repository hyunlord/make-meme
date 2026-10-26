# B-029 재현 계약

기존 pinned 환경만 사용한다. 아래 root 변수는 비공개 로컬 경로로 설정하며 공개 문서에 개인 절대경로를 쓰지 않는다. 기존 완료 run을 덮어쓰거나 같은 예산으로 재실행하지 않는다.

```sh
# 각 task의 source mask에서 CPU 지도 한 세트만 생성
python code/build_support_maps.py "$B027_ROOT/tasks/$task" "$B029_ROOT/tasks/$task/shared_support"
# METHOD: 각3task; CONTROL: animal/vehicle만
python code/prepare_layout.py "$B029_ROOT/tasks/$task/$variant" "$B027_ROOT/tasks/$task" "$B029_ROOT/code" "$variant"
python code/freeze_run.py "$B029_ROOT/tasks/$task/$variant"
# 사전 commit/push 및 remote SHA 확인 이후에만 순차 실행
python code/runtime_launch.py "$worker" 1800 "$PINNED_PYTHON" "$B029_ROOT/code/run_phase.py" "$worker" "$stage"
```

고정 순서: animal METHOD R1→R2→CONTROL R1, human METHOD R1→R2, vehicle METHOD R1→R2→CONTROL R1. 각 case PROBE→S→D. 앞 단계의 실제 성공 receipt와 프로세스 종료를 확인한다. CPU 지도 준비와 layout 순서는 서로 독립이지만 freeze에는 둘 다 완료되어야 한다.

B-027 producer cache는 재인코딩하지 않는다. 초기noise 파일·16leaf·RNG·scheduler를 그대로 유지한다. 최종latent는 S 종료 전에 저장하며 D 실패로 S를 다시 실행하지 않는다. raw 영상은 source_fps=null, preview24fps,17frame이며 실제 원본 초 단위 시간 정합을 주장하지 않는다.

## 사전 CPU 검증

```sh
CUDA_VISIBLE_DEVICES='' SCAIL_MODEL_SOURCE="$PINNED_UPSTREAM/wan/modules/model_scail2.py" \
 "$PINNED_PYTHON" -m pytest -q code/test_contract.py code/test_spatial_image_gate.py
```

실제 결과: `10 passed in 0.75s` (기존 계약4 + 방법 계약6). 실제14B 모델/FlashAttention GPU 수치 동등성 검사가 아니다. `compileall`과 diff whitespace 검사도 통과했다. LSP는 transport closed로 STATIC_LSP_UNAVAILABLE/NOT_CLEAN이며 설치·재시작으로 범위를 넓히지 않았다.

실패 기록: 첫 CPU 지도 생성에서 config의 클래스 라벨을 Python 클래스명으로 사용해 `StopIteration`이 발생했다. SHA가 고정된 실제 `model_scail2.py`의 `SCAIL2Model` 생성자에서 patch_size를 읽도록 한 줄 수정한 뒤 세 지도 실제 생성이 통과했다. 인접 `model.py`의 `WanModel`은 실행 경로가 아니므로 사용하지 않았다. 첫 combined pytest 명령에서 `SCAIL_MODEL_SOURCE` 환경변수를 누락해 두 fixture가 KeyError로 실패했고, 문서의 명시적 환경변수 명령으로 수정했다. 모두 GPU 실행 전 CPU 준비 오류이며 sampler 사용량0을 유지했다.

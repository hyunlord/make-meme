# CONTINUATION_01 재현 및 중단 경계

실제 실행 코드는 사전 고정 commit `8b65e8a1fc778ea9bf3d04316e24f7851c40b5f6`의 `continuation/code`다. 기존 recovery/global run_phase와 B033 clean_constraint는 수정하지 않았다. 과거 작업을 반복하지 말고 [CODE_FREEZE.json](CODE_FREEZE.json)의 SHA를 먼저 확인한다.

```sh
# CPU 정책 검증, GPU 없음
python3 -m unittest discover -s continuation/code -p 'test_*.py'
# 실제 실행했었던 명령 형태. 기존 attempt가 존재하므로 그대로 재실행 금지.
"$B007E_PYTHON" "$CONT_ROOT/code/supervisor.py" "$CONT_ROOT/stages/CONTROL_D"
"$B007E_PYTHON" "$CONT_ROOT/code/supervisor.py" "$CONT_ROOT/stages/STEP_S"
```

`CONT_ROOT`는 비공개 B034 continuation/CONTINUATION_01 root다. private config에는 기존 Python/upstream/model 위치·정확한 allowed service identity·부모 artifact·deadline이 있다. 개인 절대 경로는 공개하지 않는다.

CONTROL의 `artifacts/final_latent.safetensors`는 기존 BASE/source/M을 B033 `mix_clean`으로 결합한 값이며 새 sampling 결과가 아니다. VAE는 이 값만 1회 decode했다. source 재복원과 BASE 재디코딩은 없었다. 새 MP4는 PNG에서 24fps/BT709/yuv420p로 인코딩한 파생물이다.

STEP은 `B007E_LOADER_REPORT` 누락으로 CPU loader 종료 직전 실패했다. [FAILURE_VERIFICATION.md](FAILURE_VERIFICATION.md)를 따른다. 미실행 STEP_D 명령을 완료 재현 절차처럼 제시하지 않는다. 새로운 예산 없이 attempt 파일을 삭제하거나 수정 후 재실행하지 않는다.

CPU fixture 14개는 신원·재사용·외부 PID·큐·관측 오류·불확실성 30초·normal-exit receipt 및 수거된 unit 메타데이터 경계를 검사한다. CPU `/bin/sleep 2` unit lifecycle 관측과 실제 CONTROL 종료가 retention 경로의 근거이며, 전체 STEP 성공이나 영상 방법 이득의 근거는 아니다.

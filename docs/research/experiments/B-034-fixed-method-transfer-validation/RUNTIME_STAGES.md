# 실제 단계 상태

| 단계 | 상태 | 실제 사용 |
|---|---|---|
| rigid Qwen | COMPLETED, anchor eligible | 40 image steps / 80 forwards |
| nonrigid Qwen | COMPLETED, ANCHOR_UNSUITABLE | 40 image steps / 80 forwards |
| rigid ENC | COMPLETED | 조건 준비1, full source encode1 |
| rigid BASE_S | final latent saved; teardown guard BLOCKED | 40 steps / 80 forwards |
| rigid BASE_D | NOT_RUN | decode0 |
| rigid support/E/M | NOT_CREATED | BASE raw 없음 |
| rigid CONTROL_D / STEP_S / STEP_D | NOT_RUN | 추가 sampler0 / decode0 |
| nonrigid video 전체 | NOT_RUN_ANCHOR_UNSUITABLE | encoder0 / sampler0 / decode0 |

자체 Qwen/video pipeline과 watchdog은 모두 MainPID0/inactive로 확인했다. 기존 ComfyUI 프로세스는 보존됐다. 자동 재시도나 다음 실험 예약은 없다.

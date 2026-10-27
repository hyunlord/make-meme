# 실행 재현 경로

기존 Qwen 환경의 `qwen_launch.py ROOT 7200 PYTHON qwen_runner.py ROOT`가 고정된 두 case를 순차 처리한다. `PREFLIGHT_QWEN.json`의 코드·입력·환경 freeze를 먼저 검증한다. 모델은 기존 로컬 파일만 읽는다. 재현 명령은 이번 허용 횟수를 추가로 부여하지 않는다.

적합 판정된 A0에만 `manual_anchor_mask.py A0.png TASK/inputs/anchor`를 사용한다. polygon은 실제 A0의 관측 가능한 대상만 표시하며 원본 GT를 새 대상 정답으로 복사하지 않는다. `prepare_config.py TASK`, `prepare_layout.py TASK CODE UPSTREAM MODELS`는 CPU 입력 정합과 실행 freeze를 만든다. 영상 실행 전에 해당 freeze를 연구 브랜치에 기록한다.

각 stage는 기존 SCAIL Python에서 `runtime_launch.py STAGE_ROOT SECONDS PYTHON run_phase.py STAGE_ROOT STAGE`로 실행한다. ENC, BASE_S, BASE_D가 종료한 후 BASE 영상의 실제 대상 support를 준비한다. `prepare_support.py TASK`가 고정 E/M을 기록한다. 이 기록과 평가 crop을 동결한 뒤 CONTROL_D, STEP_S, STEP_D로 진행한다. 모든 worker는 이전 worker의 정상 종료와 자원 회복을 확인한다.

마지막 CPU `postcompose_export.py TASK`는 BASE/FINAL_ONLY/STEP에 같은 E를 적용한다. 원본 영상이나 기존 raw는 덮어쓰지 않는다. 새 영상은 새 파생물로 인코딩된다. 원본 raw와 최종 latent는 full에 보존하고 compact에 포함되지 않는 항목까지 검증했다고 하지 않는다.

개인 절대경로는 공개하지 않으며 실제 로컬 경로·명령·PID·단계별 receipt는 비공개 자료에 남긴다. 미실행 단계는 명령이 있다는 이유로 완료로 보고하지 않는다.

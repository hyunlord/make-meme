# STEP_S 실패 검증

- 실제 예외: `KeyError: 'B007E_LOADER_REPORT'`.
- 기존 `video_code/run_phase.py:8`은 `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `B007E_LOADER_REPORT=<stage reports>/loader.json`을 설정한다.
- 새 `continuation/code/worker.py:15`는 앞의 offline 두 환경만 설정했다. 이 wrapper 이식 누락은 실행 담당 agent의 오류다.
- unchanged `video_code/staged_loader.py:141`은 CPU 가중치 적재 이후 `os.environ["B007E_LOADER_REPORT"]`를 읽어 보고서를 exclusive create 한다. 여기서 실패했고 `dit_loader_complete_cpu`, DiT CUDA 이동, 첫 forward, sampler에는 도달하지 않았다.
- `phase_sample.py:28`에서 loader 호출이 반환되지 않았다. 새 sampler 시도 1회 예산은 소진했고 실제 forward/step은 0이다. STEP_D와 재시도는 NOT_RUN이다.

새 guard의 `guard_reason=COMPLETE`는 GPU/queue 위험이 없어진 관측 결과다. worker exit=1, unit failed/exit-code, normal_exit_recorded=false, final_safety_decision=UNIT_EXIT_NOT_VERIFIED, 최종 status=NOT_CLEAN이므로 작업 성공이 아니다. 이 문자열을 소급 수정하지 않는다.

CONTROL은 exact live identity 등록 → active/exited 정상 종료 receipt → 자체 완료 unit stop → fresh safety CLEAR/inactive/MainPID0 순서를 실제 통과했다. 과거 RECOVERY_01의 UNKNOWN_GPU_PID나 B034 other_service_work 원인을 새 결과로 소급 확정하지 않는다.

다음에 필요하다면, 먼저 기존 runner의 필수 환경을 새 wrapper에 정확히 연결하고 CPU에서 요구 환경 계약을 검사해야 한다. 이번에는 실행 코드를 사후 수정하거나 재시도하지 않았다. 새 STEP 시도는 별도 사용자 승인이 필요하다.

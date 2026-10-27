# 과거 기록과 RECOVERY_01 가드

과거 B034 BASE_S의 `other_service_work`와 `BLOCKED_AT_BASE_TEARDOWN`은 변경하지 않았다. 당시 발동 queue/GPU PID 응답이 없어 `UNKNOWN / INSUFFICIENT_EVENT_TELEMETRY`다.

이번 시작은 queue running/pending0, 허용된 기존 서비스만 GPU에 존재하고 starttime·command hash가 일치했다. 시스템72GiB 시작/swap0와 자체 이전 worker 부재를 확인했다. 복구 unit은 기존 unit과 별도이며 전역 predecessor 검사/guard 정책은 변경하지 않았다.

새 decoder는 raw/PNG/MP4 검증을 끝내고 worker_complete를 남겼다. 그러나 종료 관측에서 cgroup.procs는 비었고 nvidia-smi에는 기존 서비스 외 PID 하나가 남았다. 같은 관측의 systemd MainPID는 그 PID를 가리켰으며 `/proc`에서 command hash는 빈 byte의 hash로 관측됐다. queue는 비었고 memory/swap 문제는 없었다. 즉 관측 채널 사이 시점 차이를 시사하지만 PID를 임의 허용하지 않았다. guard_reason은 정확히 `UNKNOWN_GPU_PID`이며 종료 감시는 NOT_CLEAN이다.

최종 관측에서는 미분류 PID0·queue0·기존 허용 서비스 identity 유지·own MainPID0/inactive를 확인했다. worker returncode0와 final observation COMPLETE는 guard_reason을 덮어쓰지 않는다. ExecStopPost의 own unit not loaded 메시지는 종료된 ephemeral unit 정리 시 출력됐으며 원문을 보존한다.

이 새 기록은 과거 B034 원인의 확정 근거가 아니다. 모든 queue/PID identity·시각·monotonic·자체 cgroup·systemd·memory 원시 관측은 비공개 로그에 있다. 공개에서는 민감 식별자와 전체 command를 제외한다. 다른 프로세스 종료·queue 삭제·가드 완화0, 재시도0이다.

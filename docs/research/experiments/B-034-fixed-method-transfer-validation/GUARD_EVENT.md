# BASE sampler 종료 시 관측

BASE는 40 scheduler step / 80 forward를 마치고 finite final latent를 원자적으로 저장했다. worker `BASE_S_complete` 기록은 epoch 1793067221.0436022이다. 그러나 watchdog 최종 reason은 `other_service_work`이며 `service_exit`가 아니다. returncode=0, MainPID=0, Result=success만으로 이 차이를 지우지 않는다.

마지막 watchdog sample(epoch 1793067222.235109)은 cgroup.procs가 비어 있다. 직전 sample에는 해당 worker가 있었다. 이때 memory.events는 high=6454, max=0, oom=0, oom_kill=0이었다. 시스템 headroom이나 swap 가드 위반 기록은 없다.

사후 읽기 전용 확인에서 기존 서비스 queue는 비어 있었고 GPU에는 기존 허용 서비스만 남았다. 허용 PID의 starttime 및 command hash는 기존 값과 일치했다. 하지만 실제 중단 조건을 만족시킨 queue 응답과 GPU PID 집합은 기록되지 않았다.

가능성은 (1) 실제 다른 서비스의 짧은 작업, (2) 자기 worker 종료 시 cgroup와 GPU PID 회계의 시차, (3) 모니터링 표본의 비동기 관측이다. 현재 기록은 2를 시사하지만 확정하지 못한다. 원인 UNKNOWN이며 guard를 무시하거나 과거 reason을 수정하지 않는다. sampler 재시도는 하지 않는다. 후속 GPU 단계는 중단한 상태로 보존한다.

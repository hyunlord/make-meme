# 관측 재현 범위

기존 승인 SSH alias에서 배포 start script와 CLI/installer의 실행 연결만 읽었다. 서비스 start script는 실행하면 외부 프로세스를 종료할 수 있으므로 실행하지 않는다.

현재 표본은 ss listener 조회, nvidia-smi compute-apps 조회, system/user manager list-jobs, 기존 endpoint의 제한된 queue GET으로 구성했다. 2초 간격 3표본이다. queue 실패는 null count로 보존한다.

서비스 정상 중지 상태를 확인할 관리자 증거가 없고 외부 GPU 작업이 존재해 실행 준비를 종료했다. 부재한 manager를 임의 unit으로 대신하거나 외부 작업을 종료하여 재현하지 않는다. 런타임 코드 변경·정책 활성화·새 모델 worker는 없다.

# 서비스 상태 읽기 전용 감사

상태: **BLOCKED_MANAGER_STATE_UNVERIFIED**. 추가로 새 3개 표본 모두 외부 GPU 작업이 관측되어 독립적인 실행 차단 조건이다.

## 확인한 연결

- 기존 실행 스크립트는 setsid/nohup으로 CLI를 시작하고 CLI는 ComfyUI를 foreground subprocess로 호출한다. 스크립트는 읽기만 했으며 실행하지 않았다.
- 해당 CLI의 comfy 하위 명령에는 start/proxy가 있지만 상태 조회·durable PID 등록 인터페이스는 확인되지 않았다.
- 제한된 관련 system/user unit·컨테이너 정의 확인에서 이 배포에 대응하는 상태 관리자를 식별하지 못했다. 이것은 모든 가능한 관리자 부재의 증명이 아니다.
- 선택된 연구 실행 경로에서 queue 호출은 안전 관측기에만 있다. 따라서 선택적 보호 대상이라는 설계는 확인됐지만 정상 중지 상태는 확인되지 않았다.

## 세 표본과 판정

12:48:46/48/50 UTC 표본은 listener 부재, queue 연결 거절, system/user pending job 0을 보였다. 외부 GPU 작업 1개는 세 표본 모두 존재했다. 해당 작업을 조회 이상의 방식으로 조작하지 않았다.

관리자의 inactive/stopped 상태 및 전환 상태를 증명할 권위 있는 인터페이스가 없으므로 STOPPED_CONFIRMED를 만들지 않았다. queue는 UNAVAILABLE/counts=null로 새 증거에 기록했다. 기존 관측 코드와 과거 0/0 기록은 수정하지 않았다.

새 정책 코드·manifest 활성화, GPU worker, sampler, decode, 추가 CPU 회귀검사 모두 미실행이다. 입력·가중치·E/M·cache·noise·bootstrap·guard는 그대로다.

## 읽은 배포 파일 해시

| 별칭 | SHA256 |
|---|---|
| start_comfy.sh | 89e3451512e8873cb0161ec57ea0d1515d4fdd721c393d73e7f8ab510a387fbf |
| cli.py | c703541ac656cbf8edd3779c3d04a45aad0dc0353a3a3198d49d366d30cd1fd8 |
| installer.py | b7ffe55bf20e66c24dbf6136168b99bd3f9db0565f7daa2b77919c4a9534ae63 |

개인 실행 경로·PID·boot identity·원시 명령은 비공개 증거에만 있다. 이전 SSH 장애나 종료 가드 원인은 이 감사로 확정하지 않는다.

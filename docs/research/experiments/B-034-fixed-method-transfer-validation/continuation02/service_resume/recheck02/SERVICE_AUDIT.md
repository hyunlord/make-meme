# SERVICE_RESUME_02 현재 상태 재확인

**BLOCKED_MANAGER_STATE_UNVERIFIED**. 이번 14:34 UTC 표본에서는 외부 GPU 작업이 없으며, 앞선 외부 GPU 차단은 역사 기록으로만 보존한다.

## 논리적 배포와 현재 runtime의 구분

기존 수동 setsid/nohup 실행 스크립트 → CLI → foreground subprocess 연결과 세 파일 해시를 다시 확인했다. 해당 queue가 연구 계산 의존성이 아닌 안전 관측기라는 이전 선택 코드 확인은 재사용한다.

관련 system/user unit 목록과 service 정의·컨테이너·프로세스의 제한된 재확인에서도 이 배포의 정상 inactive/stopped를 조회하는 관리자 인터페이스는 확인되지 않았다. 이것은 호스트 어디에도 관리자가 없다는 전수 증명이 아니다. 수동 launch mechanism을 알고 있다는 것과 durable lifecycle 상태를 알고 있다는 것은 다르다.

stopped_allowed 정책은 **NOT_ACTIVATED**다. 현재 프로세스·listener 부재를 정상 중지로 승격하거나 allowlist를 비우지 않았다.

## 실제 세 표본

- UTC 14:34:45.307686 / 14:34:47.353088 / 14:34:49.405161, 약 2초 간격.
- GPU process 목록 0, 기존 endpoint listener 없음, queue CONNECTION_REFUSED → UNAVAILABLE/counts=null.
- system/user manager pending job 0. 현재 MemAvailable 약100.06GiB, swap 사용량0. 이는 manager 상태 미확인 gate를 대체하지 않는다.
- 관련 CONT02 worker·unit 및 worker-attempt/result/final-latent 증거 없음. 새로운 GPU 시도 예산은 소비하지 않았다.

## 실행 장부

새 GPU worker·model load·sampler·decode·service operation·fixture 실행 0. 코드 변경 0. 이전 성공 CPU24와 preflight4는 재실행하지 않았고 새로운 PASS로 세지 않는다. 기존 입력·mask·cache·가중치·서비스·과거 증거는 변경하지 않았다.

## 확인한 코드 해시

| 파일 별칭 | SHA256 |
|---|---|
| start_comfy.sh | 89e3451512e8873cb0161ec57ea0d1515d4fdd721c393d73e7f8ab510a387fbf |
| cli.py | c703541ac656cbf8edd3779c3d04a45aad0dc0353a3a3198d49d366d30cd1fd8 |
| installer.py | b7ffe55bf20e66c24dbf6136168b99bd3f9db0565f7daa2b77919c4a9534ae63 |

비공개 원시 receipt SHA256: `5b080c3e6f5682070ad878e07bcb627262af9adc92ec87bb000226b24cf187b6`. 개인 경로·PID·boot identity는 공개 파일에 포함하지 않았다.

다음에 필요한 사실은 기존 배포의 정상 중지/전환 상태를 권위 있게 확인할 운영 인터페이스다. 이 작업에서 새 관리자를 만들거나 서비스를 재시작하지 않았다.

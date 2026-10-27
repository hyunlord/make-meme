# 논리 서비스와 runtime instance, 중지와 관측 실패

서비스의 논리 신원 L은 배포 경로·launcher·실행 사용자·endpoint·정책 계보다. runtime 신원 I는 특정 boot에서 PID/starttime/cgroup/invocation으로 식별하는 실제 실행체다. 재부팅으로 I가 사라져도 L이 없어지는 것은 아니다. 반대로 L을 안다고 현재 상태를 안다고 할 수는 없다.

이번 선택된 SCAIL 경로는 8190 queue를 조건 인코더·DiT·VAE에 사용하지 않고, safety가 다른 작업과의 충돌을 확인하는 데 사용한다. 필수 생성 의존성과 선택적 보호 대상을 구분할 수 있지만, optional이라는 말이 관측 실패를 허용한다는 뜻은 아니다.

허용 조건을 다음과 같이 쓴다. 이는 생성 모델 수식이 아니라 운영 논리다.

`safe = service_state_valid ∧ no_external_gpu ∧ memory_ok ∧ swap_zero ∧ own_lifecycle_valid`

`service_state_valid`는 확인된 ACTIVE_IDLE 또는 정책이 허용한 STOPPED_CONFIRMED다. 후자는 관리자 중지 상태·관련 프로세스/listener/GPU 부재·전환 부재의 일치하는 관측이 필요하다. 모르는 항을 True로 두지 않는다.

queue의 `counts=null`은 0이 아니다. UNAVAILABLE은 값을 모르는 상태이고, NOT_APPLICABLE_CONFIRMED_STOPPED는 정상 중지 근거로 질의 대상이 없는 상태다. 기존 코드는 오류 목록으로 차단했으므로 실패 뒤 빈 배열이 남았다는 사실을 과거 안전 우회라고 부르지 않는다.

확인된 launcher는 수동 setsid/nohup → CLI → ComfyUI 경로였다. 보호 역할은 확인했지만, 권위 있는 inactive/stopped 및 전환 상태를 제공하는 기존 관리자 근거는 확인하지 못했다. 이번 세 표본에서는 별도 GPU 작업도 관찰됐다. 이는 정책을 완화하거나 STEP을 실행할 근거가 아니다.

## 이해 확인 질문

1. 알려진 launcher가 있는데도 STOPPED_CONFIRMED를 바로 부여하면 안 되는 이유는?
2. queue count null과 0은 어떤 다른 주장을 뜻하는가?
3. 서비스 상태가 확인돼도 외부 GPU 작업이 있으면 왜 실행할 수 없는가?

## 별도 해설

1. launcher는 시작 방법을 설명하지만 현재 관리 상태·전환 예약·정상 종료를 반드시 증명하지 않는다.
2. 0은 정상 응답에서 관측한 작업 부재다. null은 미관측 또는 해당 없음을 나타내며 별도 status로 둘을 구분해야 한다.
3. 안전 조건은 논리곱이다. 한 조건의 통과가 다른 조건의 실패를 상쇄하지 않는다. 타 작업을 종료해서 통과시키지 않는다.

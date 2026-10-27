# CONTINUATION_02 비용과 미실행

상태 **BLOCKED_SSH**, heavy/model 적재 시도 0회, sampler 0회, forward/step/constraint 0회, VAE decode 0회다. BASE/CONTROL·source/reference 인코딩·설치·다운로드·학습도 0회다.

승인된 기존 Spark SSH alias로 읽기 전용 상태 확인 연결을 2회 시도했다. 첫 연결은 timeout, 두 번째는 `ConnectTimeout=10`으로 제한했고 역시 port22 timeout이었다. 새 주소·계정 추측이나 무제한 재연결은 하지 않았다. 원격 작업이 실행 중인지, 현재 메모리가 안전한지는 **미확인**이며 장비 오류나 GPU 원인으로 단정하지 않는다.

Mac의 CPU fixture 24개(bootstrap10+기존 guard14)를 통과했다. 첫 3개 fixture 기대 경로가 macOS `/var`와 canonical `/private/var`를 구분하지 못해 실패했으며 fixture root를 resolve했다. 실제 경로 제한은 완화하지 않았다. 새 worker의 `--preflight-only`는 torch/Wan import·loader.json·worker attempt 없이 종료했다.

같은 Spark Python·실제 STEP_S 경로에서의 preflight, fresh live safety, runtime freeze, 원격 전송은 NOT_RUN이다. 로컬 검사 성공을 실제 실행 준비 PASS 또는 영상 방법 결과로 보고하지 않는다. CPU 준비와 SSH 실패 외의 장비 시간·GPU 메모리는 측정하지 않았다.

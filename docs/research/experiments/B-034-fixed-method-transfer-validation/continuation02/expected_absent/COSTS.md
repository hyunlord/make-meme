# 비용과 사용 장부

- 이번 운영 변경 시작: 2026-10-27 16:13:44 UTC.
- 실제 시작 가드: 16:22:26 UTC. 첫 표본에서 외부 GPU 작업을 발견하여 예정된 3표본을 끝까지 실행하지 않고 즉시 거절했다.
- 약 8분 42초는 정책 구현·검사·사전 고정·시작 확인까지의 벽시계 시간이다. 최종 문서화·패키징은 별도 전달 기록에 포함한다.
- 소규모 CPU 계약 13개 PASS, 실제 Spark preflight STEP_S/STEP_D PASS. 과거 CPU24는 재실행하지 않았다.
- supervisor 호출 1회, worker/model load/full sampler/decode 각각 0회. 실제 step/forward/constraint 각각 0이다.
- 시작 MemAvailable 약88.50GiB, swap 사용량0. CPU RSS·cgroup·CUDA peak는 모델 worker가 없어 측정되지 않았다. 이를 생성 peak0으로 보고하지 않는다.
- 새 패키지·모델·학습·encoder·BASE/CONTROL 재생성·자동 재시도·외부 서비스 조작 모두0.

서비스 부재 기대 정책 자체는 관측됐지만 외부 GPU 보호는 유지되어 시작을 차단했다. preflight CLEAR는 이후의 장비 독점을 보증하지 않는다. 추가 시도는 하지 않았다.

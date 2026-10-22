# B-007D 실행 기록

시작 2026-10-22 11:34 UTC, hard deadline14:34 UTC. 시작 원격 HEAD `ee7ef695cd6f438779166dce71fdbea1507cc129`와 공통 연구 문서·B-007C 결과·PLAN 확인.

순서: 원본/환경 고정 → OS 격리 실제 probe → metadata-only 최대1회 → static parity → 자원/저장 전략 → 조건부 변환 최대1회 → 실제 tensor parity → 문서/ZIP/원격 검증. 신규 대형 다운로드·모델 load·diffusion·학습은0.

OS 격리에서는 sanitized environment, credential/socket 비노출, host private file 접근 차단, network 차단, source/code/environment read-only와 전용 output만 writable을 확인한다. 실패 시 실제 restricted load를 시작하지 않는다. synthetic probe는 실제 checkpoint attempt가 아니며 별도로 기록한다.

기존 B-007B 전체 CLI를 그대로 조합하면 metadata/materialized load가 중복될 수 있어 이번에는 두 번의 실제 load 상한을 지키는 별도 entry를 준비한다. 두 번째 load에서 얻은 같은 mmap state로 값 검증까지 수행한다. 원본 gate와 기존 코드는 수정하지 않는다. 전용 임시 출력은 검증 후에만 최종 파일로 발행한다.

코드는 실제 restricted load 전에 commit/push로 고정한다. unknown global 추가 허용·unsafe pickle·실제파일 재작성은 금지한다. OS 격리 미구현 또는 metadata 실패 시 BLOCKED다.

## 12:55 UTC — 실제 metadata gate PASS

실행 코드 `5e134fa3c8668bd9abe8b00067c01d84cd2580b3`를 원격에 고정한 뒤 실제 첫 로드를 수행했다. 격리·정확한 ambient 집합·외부 supervisor cleanup probe PASS. 실제987개 source tensor metadata/ZIP storage와1307개 mapping을 확인했고 scope가 복원됐다. 전체 hash 포함45.209초, restricted FakeTensor load0.167초. 전체 hash와 load I/O는 분리했다. cgroup peak8GiB는 file cache를 포함하며 값 검증은 아직 NOT_VERIFIED다. 독립 검토가 static storage987개를 다시 대조했다. 신선한 메모리·디스크 여유 확인 후32GiB cap의 두 번째이자 마지막 변환 시도에 진행한다. 실패 시 재시도 없음.

## 13:04 UTC — 변환 완료 / 종료

실제 두 번째 로드 및1307개 tensor 전체 값 검증 PASS. 원본 SHA 유지, 출력 SHA8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118. guard456.759초. 두 container exit0/PID0, supervisor inactive. 추가 실행 없음. [최종 결과](RESULTS.md).

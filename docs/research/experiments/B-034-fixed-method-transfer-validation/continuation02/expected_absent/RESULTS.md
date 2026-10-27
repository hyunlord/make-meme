# EXPECTED_ABSENT_01 결과 — BLOCKED_EXTERNAL_GPU_AT_START

2026-10-28 KST. 사전 고정 커밋: `efd801ad3e0dae72a1c4f60b0fd742f91a06a78a`.

## 실제 결과와 연구 판단

새 STEP 영상은 없다. 따라서 STEP이 BASE/FINAL_LATENT_ONLY보다 추가 이득을 만들었는지는 **NOT_RUN / INCONCLUSIVE**다. 기존 BASE의 클래식 target 외형 FAIL, CONTROL의 동일 후합성 뒤 추가 개선 미관찰, 비강체 ANCHOR_UNSUITABLE/영상 NOT_RUN, B-033 단일 사례 PARTIAL을 유지한다. 실행 전 안전 차단을 생성 방법의 품질 FAIL로 해석하지 않는다. 기본 방법 채택 근거는 여전히 없다.

## 한정 정책과 실제 차단 원인

사용자가 이번 attempt에만 승인한 OPTIONAL_EXPECTED_ABSENT를 preflight와 실제 supervisor가 같은 설정으로 읽도록 구현했다. 과거 STOPPED_CONFIRMED를 소급 활성화하지 않았고 이전 allowlist/snapshot도 보존했다. 과거 관리자 상태 미확인으로 다시 차단한 것이 아니다.

16:22:26.826 UTC의 실제 시작 첫 표본에서 서비스 프로세스·자식·8190 listener 부재와 정확한 연결 거부를 관측했다. 서비스 상태는 EXPECTED_ABSENT_OBSERVED, queue UNAVAILABLE/counts=null이다. 하지만 별도의 GPU 작업1개가 관측되어 UNKNOWN_GPU_PID로 차단했다. MemAvailable88.50GiB, swap사용0, 관측 오류0이었다. 필수3표본 중1표본에서 이미 위반하여 즉시 종료했다. 이를3표본 PASS로 보고하지 않는다.

실제 외부 GPU identity와 명령 정보는 비공개 receipt에만 보존했다. 외부 작업을 종료하거나 자동 허용하지 않았다. supervisor 반환2, 자체 unit inactive/not-found/MainPID0, worker-attempt 없음이다. 자동 재시도·대기 후 자동 재개·후속 예약은 하지 않았다.

## 검증과 사용량

- 한정 정책 CPU13개 PASS, 동일 Spark Python worker의 S/D preflight PASS. 기존 CPU24는 재실행하지 않았다.
- 독립 코드 검토와 공개 코드 hash freeze PASS. bootstrap·모델 계산·B033 제약·입력 E/M은 유지했다.
- supervisor 호출1회, heavy worker/모델 적재/full sampler/decode 각각0회.
- 실제 forward/step/clean constraint 각각0, 신규 final latent/raw/MP4 없음.
- BASE/CONTROL 재생성·재decode, encoder·학습·설치·다운로드·서비스 조작0회.
- CONTINUATION_01의 실패 포함 heavy 시도1회/forward0 기록은 별도로 보존한다. 이번 미사용 CONT02 예산을 실행 성공으로 바꾸지 않는다.

CPU 검사 성공은 GPU 독점을 보장하지 않는다. 사전 preflight 이후 외부 작업이 나타난 사실을 실제 시작 가드가 차단했다. 실행 중 서비스 재등장 시 중단 경로는 CPU fixture로 검증했으며 실제 모델 실행 중 상황을 관측한 것은 아니다.

## 전달과 종료

새 raw/latent가 없으므로 full/compact와 기존 영상 묶음을 반복 생성하지 않는다. 새 정책·코드·실측·거절 receipt·보고서만 작은 비공개 evidence ZIP으로 전달한다. 실제 검증 범위와 양 호스트 위치는 DELIVERY.md에 기록한다. 기존 시각 결과는 이번 차단으로 변경되지 않으며 temporal=UNVERIFIED다.

이번 작업은 여기서 종료한다. 다음 연구 방법이나 튜닝을 제안·시작하지 않는다. 현재 남은 것은 동일 고정 STEP 비교이며, 실제 외부 작업 충돌이 해소된 별도 실행 기회 전에는 재개하지 않는다.

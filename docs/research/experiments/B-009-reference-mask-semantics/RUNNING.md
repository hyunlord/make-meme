# B-009 실행 기록

현재 상태: RUNNING / 신규 P·PROBE·S·D NOT_RUN.
시작 원격 HEAD `2b734cbeef6cdca1b334a672b240a7b0f5c2f45f`. 기존 격리 문서 checkout을 fast-forward로 갱신하고 A/B-008/H 실행 자산을 보존한다. 전체 종료시각2026-10-23 06:55UTC를 보수적으로 적용한다.

1. COMPLETED: 정확한 BLACK→WHITE 신규 mask, RED 및 RGB/driver 보존·pinned helper·실행 계약/비교 tolerance 사전 검증.
2. COMPLETED: 최소 실행 코드/config/입력 hash 사전 commit/push 및 독립 검토.
3. IN_PROGRESS: P1→조건 비교→PROBE1→S1→D1, fresh worker 종료와 자원 회복 확인. 실패 시 재시도 없이 후속 중지.
4. PENDING: 원본/B-008/B-009 전체17장·24fps 비교와 평가·한국어 이론.
5. PENDING: 공개 결과 commit/push·비공개 ZIP 양호스트 CRC/해시·자체 프로세스 종료 검증.

이번 변경은 Lab 사진 배경 수정이 아니라 reference semantic mask의 가시성 조건만 바꾸는 것이다. replace_flag=False/animation 유지. 침실 잔류 자체는 실패가 아니며 직립·앞발·동작 단계가 주 평가다. 기존 mask 결함PARTIAL, temporal은 실제 연속 관찰 전UNVERIFIED. 자기 재현은 보류하며 자동 실행하지 않는다.

## 시작 환경

Spark aarch64, MemAvailable95,114,608,640bytes,swap0,연구 디스크 여유1,127,348,158,464bytes. 기존 ComfyUI GPU 프로세스만 확인했으며 종료하거나 변경하지 않는다. 기존72GiB 시작/24GiB 실행 headroom과swap0정책을 유지한다.

## 사전 입력·코드 검사

새 mask는RED113,928픽셀을 정확히 보존하고BLACK344,824픽셀만WHITE로 변경했다. 독립 pinned helper 검사와 전처리ref_mask_img FP32[3,896,512] SHA `67c43d812cd0f8f889defa496357929aae73d96b0a6ac9421c1eb9e1ffbd3ff3`를 확인했다. 사진/driver는 변경하지 않았다. CPU10fixture·criticalRuff·syntax PASS, 전체typecheck832errors/17files는NOT_CLEAN으로 기록한다. 같은마스크·noise·RNG·scheduler는exact, 비마스크 인코더 float만사전 rtol1e-5/atol1e-6; 의미있는차이는S차단이다. 독립 코드 검토PASS, GPU는아직NOT_RUN.

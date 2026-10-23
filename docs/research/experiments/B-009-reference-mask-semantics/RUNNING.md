# B-009 실행 기록

현재 상태: COMPLETED / P·PROBE·S·D PASS / 동작 전달 FAIL / temporal UNVERIFIED.
시작 원격 HEAD `2b734cbeef6cdca1b334a672b240a7b0f5c2f45f`. 기존 격리 문서 checkout을 fast-forward로 갱신하고 A/B-008/H 실행 자산을 보존한다. 전체 종료시각2026-10-23 06:55UTC를 보수적으로 적용한다.

1. COMPLETED: 정확한 BLACK→WHITE 신규 mask, RED 및 RGB/driver 보존·pinned helper·실행 계약/비교 tolerance 사전 검증.
2. COMPLETED: 최소 실행 코드/config/입력 hash 사전 commit/push 및 독립 검토.
3. COMPLETED: P1→조건 비교→PROBE1→S1→D1, fresh worker 종료와 자원 회복 확인. 실패 시 재시도 없이 후속 중지.
4. COMPLETED: 원본/B-008/B-009 전체17장·24fps 비교와 평가·한국어 이론.
5. COMPLETED: 공개 결과 commit/push·비공개 ZIP 양호스트 CRC/해시·자체 프로세스 종료 검증.

이번 변경은 Lab 사진 배경 수정이 아니라 reference semantic mask의 가시성 조건만 바꾸는 것이다. replace_flag=False/animation 유지. 침실 잔류 자체는 실패가 아니며 직립·앞발·동작 단계가 주 평가다. 기존 mask 결함PARTIAL, temporal은 실제 연속 관찰 전UNVERIFIED. 자기 재현은 보류하며 자동 실행하지 않는다.

## 시작 환경

Spark aarch64, MemAvailable95,114,608,640bytes,swap0,연구 디스크 여유1,127,348,158,464bytes. 기존 ComfyUI GPU 프로세스만 확인했으며 종료하거나 변경하지 않는다. 기존72GiB 시작/24GiB 실행 headroom과swap0정책을 유지한다.

## 사전 입력·코드 검사

새 mask는RED113,928픽셀을 정확히 보존하고BLACK344,824픽셀만WHITE로 변경했다. 독립 pinned helper 검사와 전처리ref_mask_img FP32[3,896,512] SHA `67c43d812cd0f8f889defa496357929aae73d96b0a6ac9421c1eb9e1ffbd3ff3`를 확인했다. 사진/driver는 변경하지 않았다. CPU10fixture·criticalRuff·syntax PASS, 전체typecheck832errors/17files는NOT_CLEAN으로 기록한다. 같은마스크·noise·RNG·scheduler는exact, 비마스크 인코더 float만사전 rtol1e-5/atol1e-6; 의미있는차이는S차단이다. 독립 코드 검토PASS, GPU는아직NOT_RUN.

## P·조건 통제·PROBE 통과 / S 시작

실행 전 고정 `1936356099823ebf720a26a5e82671fdbe6cec67`와 원격 SHA 일치를 확인했다. P1 guarded114.974초, 새 cache SHA `e151044c4939c751b551c839f878acedfa233485db72275594d75e619e518ae3`. 실제 양 CFG reference mask(t4/t10)만 pinned helper대로 WHITE prefix가 달라졌고 다른14leaf는bit-identical/maxabs0이다. RGB ref/driving·CLIP·text·driving mask·noise·RNG·scheduler가 실제로 보존돼 수치 허용오차를 사용할 필요가 없었다. 주 에이전트와 독립 검토가 receipt/cache/policy/code 결합을 확인했다.

PROBE1 guarded6.079초,16leaf/RNG 복원·정상 종료 후 S1을 시작했다. 최종latent/MP4·동작 결과는 아직 미확인이다.

최종 실제 실행·관찰은 [RESULTS](RESULTS.md), ZIP CRC/268payload 해시·양호스트 동일성은 [DELIVERY](DELIVERY.md)에 기록했다. 승인된 한 번의 비교를 종료했으며 추가 실행은 없다.

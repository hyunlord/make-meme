# CONTINUATION_02 재개 결과 — BLOCKED_LIVE_SAFETY

연결은 회복됐지만 **새 STEP 출력은 없다**. 기존 safety의 실제 관측은 `OBSERVATION_FAILED`이며 `queue:CalledProcessError`와 `allowed_identity_mismatch`를 반환했다. 기존 큐 endpoint는 연결 거부, 사전 고정한 보호 서비스 PID는 부재였다. 현재 boot identity도 과거와 달랐다.

GPU PID 목록이 비어 있고 MemAvailable 약100.158GiB/swap0인 사실만으로 큐·서비스 신원 검사를 무시하지 않았다. 기존 allowlist를 비우거나 새 PID로 바꾸지 않았고 서비스를 시작·종료하거나 가드를 수정하지 않았다. 예전 SSH timeout 원인을 재부팅으로 소급 확정하지 않는다.

## 실행 계보와 예산

- 기존 BLOCKED_SSH/CPU-only 기록과 ZIP 보존.
- 현재 원격 HEAD16552da 확인, 재개 계획12:03:47Z 고정.
- 새 STEP heavy/loading/sampler0, actualforward/step/constraint0, decode0.
- BASE/CONTROL 재생성·재decode0, encoder·학습·이미지·설치0.
- 기존 보호 서비스 부재 및 큐 관측 실패로 supervisor/GPU worker 시작하지 않음.
- STEP final latent/raw/MP4 없음. 새로운 방법 결과가 아니라 운영 사전조건 차단이다.

## 연구 판정

STEP이 두 대조군보다 이득을 만들었는지는 여전히 **INCONCLUSIVE**다. 기존 BASE target 외형 FAIL과 FINAL_ONLY 동일POST 후 추가이득미관찰은 유지한다. 비강체 ANCHOR_UNSUITABLE/영상NOT_RUN, B033 기존 단일 사례PARTIAL도 바꾸지 않는다. 기본채택 근거는 추가되지 않았다.

이번에 새 시각 관측은 없으며 temporal=UNVERIFIED다. 연결 복구 자체를 실행 성공으로, CPU preflight를 GPU 안전 성공으로 보고하지 않는다.

다음 전제는 기존 보호 서비스/큐의 정상 운영과 승인된 서비스 신원 계약을 다시 확립하는 것이다. 그 상태를 가드가 실제로 확인하기 전에는 남은 STEP을 실행하지 않는다. 이번에는 서비스 운영을 변경하거나 재시도·배경실행을 예약하지 않는다.

## 실제 Spark CPU 계약 검사

동일한 기존 Spark Python과 실제 worker entrypoint로 STEP_S/STEP_D 각각 부모 loader변수 없음/과거값의 총4개 preflight를 수행해 통과했다. 매회47개 freeze파일을 확인했고 torch/model import=false, loader.json·worker-attempt 생성없음을 확인했다. Spark CPU fixture24개도 통과했다. 이는 앞선 Mac-only 상태에서 실제 호스트의 CPU 계약 검증까지 진전된 것이며 GPU 안전 PASS는 아니다.

preflight 이후 다시 관측한 guard도 같은 두 오류를 반환했다. 새 stage/config/freeze는 CPU로 준비했지만 supervisor/모델 worker를 시작하지 않았다. 실제 실행 budget은 여전히 heavy0/decode0이다. 원격 증거와 비용은 RESUME_CPU_REPORT·RESUME_MEASUREMENTS·RESUME_COSTS에 별도 연결한다.

# B-034 CONTINUATION_02 서비스 상태 재개 결과

**BLOCKED / UNKNOWN_OR_CONFLICT. 신규 GPU 작업 0회.** 서비스의 선택적 보호 역할은 확인했지만, 정상 중지 상태를 확인할 관리자 근거가 없고 새 관측에서 외부 GPU 작업도 있었다. STEP과 최종 영상 비교는 미실행이다.

## 확인과 미확인

| 항목 | 실제 결과 |
|---|---|
| 선택한 생성 경로의 큐 의존성 | safety 관측만 사용; 필수 모델 의존성 아님 |
| 기존 실행 계보 | 수동 setsid/nohup → CLI → foreground ComfyUI 호출 |
| 정상 중지·전환 부재의 관리자 상태 | UNVERIFIED; 알려진 launcher와 현재 상태 증거는 별개 |
| 8190 listener / queue | listener 없음 / UNAVAILABLE, counts=null |
| 외부 GPU 작업 | 2초 간격 세 표본 모두 1개 존재 |
| STOPPED_CONFIRMED 정책 활성화 | NOT_IMPLEMENTED; 적용 전제 미충족 |
| 기존 allowlist·bootstrap·종료 신원 guard | 변경 없음 |

현재 표본은 2026-10-27 12:48:46/48/50 UTC다. 이 시점의 관측이며 이후 호스트 상태를 보증하지 않는다. 외부 GPU 작업은 관리자 상태 미확인과 독립적인 차단 사유다. 해당 작업이나 서비스를 시작·중지·재시작하지 않았다. queue 연결 실패를 빈 큐로 바꾸지 않았다.

서비스의 논리적 역할·launcher 계보와 현재 boot/runtime 관측은 분리해 보존했다. 정상 중지를 확인하지 못했으므로 runtime instance가 없다고 확정하거나 실행 허용 manifest를 만들지 않았다. 개인 경로·PID·boot identity·원시 명령은 비공개 증거에만 있다.

## 사용 장부와 기존 판정

이번 heavy/model load, sampler, forward, scheduler step, constraint, decode, encoder, 학습, 설치는 모두 0회다. 코드가 바뀌지 않아 기존 CPU 24개 검사를 반복하지 않았다. CONTINUATION_02의 STEP1/decode1 예산은 여전히 미사용이며 자동 예약하지 않았다. CONTINUATION_01의 실패한 heavy1회는 그대로다.

- BASE target 외형 FAIL, CONTROL의 동일 후합성 뒤 추가 이득 미관찰을 유지한다.
- STEP 출력은 없으며 두 대조군 대비 추가 이득은 NOT_RUN / INCONCLUSIVE다.
- 비강체 ANCHOR_UNSUITABLE 및 영상 NOT_RUN, B-033의 단일 사례 PARTIAL을 유지한다.
- 새로운 품질 근거가 없어 방법 기본 채택 근거는 늘지 않았다. temporal=UNVERIFIED다.
- 과거 other_service_work, UNKNOWN_GPU_PID, BLOCKED_SSH, loader 오류는 소급 수정하지 않았다.

## 종료와 다음 전제

운영 확인 단계에서 종료한다. 미확인 사실은 **이 배포의 현재 정상 중지 및 전환 상태를 증명하는 권위 있는 관리 상태**다. 별도로 실제 외부 GPU 작업도 관측됐으므로, 관리 상태만 해결돼도 바로 실행할 수는 없다. 다음 재개 전에는 두 조건을 함께 확인해야 하며 서비스 재시작·외부 작업 종료·가드 완화를 대안으로 사용하지 않는다.

독립 읽기 전용 검토도 같은 차단 판정에 동의했다. 새 미디어나 대형 ZIP을 만들지 않고 이번 의뢰·관측·보고서만 작은 증거 묶음으로 전달한다. [관측](SERVICE_AUDIT.md), [표본](STATE_SAMPLES.json), [비용](COSTS.md), [재현 범위](REPRODUCE.md), [해설](LESSON_KO.md).

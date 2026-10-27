# CONTINUATION_01 가드 검토

## 범위와 판정

검토 대상은 continuation 전용 artifact consumer, worker/supervisor, lifecycle 정책과 CPU fixture다. 기존 recovery 및 전역 sampler의 정책을 변경하지 않는다. GPU 실행 전 코드 검토에서 발견한 아래 항목은 수정 후 재확인했으며, 현재 확인된 실행 차단 결함은 없다. 이는 실제 GPU 실행·영상 품질 PASS 판정이 아니다.

과거 `BLOCKED_AT_BASE_TEARDOWN / other_service_work`와 RECOVERY_01의 `UNKNOWN_GPU_PID / NOT_CLEAN`은 보존한다. 마지막 관측에서 동일 PID/starttime의 command/cgroup 정보가 사라지고 곧 프로세스가 종료된 기록은 lifecycle 경합 가설과 부합하지만, 당시 boot/invocation 등 충분한 자료가 없으므로 원인은 UNKNOWN이다. 과거 reason을 정상 종료로 재분류하지 않는다.

## 확인한 종료 계약

- worker가 GPU 작업을 시작하기 전에 live PID, starttime, boot ID, 정확한 unified cgroup line, unit InvocationID와 최초 command hash를 기록한다. identity receipt는 임시 파일을 atomic replace하여 전달한다.
- MainPID 일치나 빈 command만으로 종료를 인정하지 않는다. PID 재사용, boot/cgroup/invocation 불일치는 차단한다.
- 확인된 동일 worker의 정상 종료 증거와 zombie/dead 상태가 있는 경우만 `OWN_WORKER_DRAINING`으로 분류한다. `/proc` 부재는 `IDENTITY_UNCERTAIN`이며 허용 PID 등록이 아니다.
- 최초 불확실성 관측부터 최대 30초로 제한한다. queue busy, 외부 GPU PID, 관측 실패, 메모리·swap 위반은 draining/completion보다 우선한다.
- `RemainAfterExit=yes`로 정상 종료 메타데이터를 보존한다. active/exited, MainPID 0, 정상 exit code/status, Result success, 같은 InvocationID/ExecMainPID와 안전한 queue/GPU/메모리를 확인해 durable 정상 종료 receipt를 남긴 뒤 완료된 자체 unit만 stop한다. 이후 자체 PID 예외 없이 새 queue/GPU/메모리 관측, 72GiB 시작 여유와 swap 0, unit inactive/MainPID 0을 확인한다. GC로 최종 metadata가 없어지는 경우는 앞서 저장한 정확한 종료 receipt와 구분하며, 최종 InvocationID가 남아 있으면 등록 값과 일치해야 한다.
- 관측 예외와 cleanup 실패는 NOT_CLEAN receipt에 보존한다. 다른 서비스 종료나 가드 임계값 완화는 없다.

OS·GPU·systemd 관측은 하나의 원자적 snapshot이 아니다. 따라서 경합을 완전히 없앴다고 주장하지 않으며, 불충분한 증거는 계속 차단한다. 각 다음 단계는 부모 orchestration의 순차 실행 및 새 live safety 확인을 필요로 한다.

## 수정 후 재확인한 사항

1. worker identity JSON의 부분 쓰기/read 경합: atomic replace로 수정.
2. 최종 systemd 관측 예외로 receipt가 사라질 가능성: OBSERVATION_FAILED / NOT_CLEAN 보존.
3. cgroup substring 비교: 정확한 `0::<ControlGroup>` line 비교로 축소.
4. GPU가 비었어도 unit 종료가 확인되지 않는 경우: 별도 `normal_exit` gate 추가.
5. transient unit 종료 메타데이터 GC: 자체 unit에만 RemainAfterExit를 적용해 정상 종료 증거를 먼저 저장하고 명시적으로 정리한다. GPU PID 부재/불명확성을 정상으로 허용하는 변경은 아니다.

## CPU 검증 근거

실제 실행 명령:

```sh
python3 docs/research/experiments/B-034-fixed-method-transfer-validation/continuation/code/test_safety.py
```

리뷰어 재실행 결과: **14 tests, OK**. 정상 종료, PID 재사용, 외부 PID, queue, 관측 실패, `/proc` 부재, 30초 상한, 빈 command, invocation 불일치, 메모리 우선순위, 완료 조건, 72GiB 시작 조건, final active/비정상 종료 거부, receipt 부재 및 다른 invocation 거부를 확인했다. 이는 정책 fixture이며 실제 GPU teardown을 재현한 시험이 아니다.

`CPU_ARTIFACT_VALIDATION.json`은 BASE final latent의 파일·tensor·sidecar hash, `[16,5,64,112]` FP32 finite, generated-only 및 40step/80forward 계보를 기록한다. 부모 reason은 원래 값 그대로다. CONTROL의 E=0/source exact와 E=1/BASE exact도 CPU에서 확인됐다. 공식 import 뒤 CUDA initialized가 true였다는 기존 검사 실패를 숨기지 않으며, 명시적 CUDA tensor 연산 0회와 별도로 기록한다.

## 계산·횟수 보존

CONTROL은 저장된 BASE final latent 혼합과 해당 결과 decode 1회이며 SOURCE_RECON decode를 추가하지 않는다. STEP은 기존 `phase_sample`과 동일한 clean constraint 모듈을 사용한다. B-033/B-034 clean constraint의 동일 SHA256:

```text
7c24c3c14d39e07ea77f01fd45ffe13c051e1c7ef14be77f8329348ed120aebb
```

새 consumer의 `predecessor=None`은 명시적 artifact-consumer 경로에 한정된다. 기존 전역 predecessor 검사를 삭제한 것이 아니다. 원본 BASE·recovery·sampler 이력은 유지한다. 실제 CONTROL/STEP 시도 수, 종료 gate와 출력 검증은 이후 runtime evidence로 별도 판정한다.

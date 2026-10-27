# B-034 RECOVERY_01 결과

**저장된 BASE를 새 sampling 없이 1회 VAE decode했다. Decode PASS, 종료 감시 NOT_CLEAN이다.** [사전 코드 커밋](https://github.com/hyunlord/make-meme/commit/ac5aceef0ed18bb327f8f2c715430b7a29693b4a) 이후 새 live safety CLEAR로 시작해 `[3,17,512,896]` finite raw·PNG17장·24fps MP4를 확보했다. CONTROL/STEP은 실행하지 않았다.

## 상태를 분리한 결과

| 판정 축 | 실제 상태 |
|---|---|
| 이전 실행 | BLOCKED_AT_BASE_TEARDOWN 보존 |
| 과거 가드 이유 | other_service_work 보존 |
| 과거 원인 | UNKNOWN / INSUFFICIENT_EVENT_TELEMETRY |
| 부모 artifact | VALIDATED: 파일·sidecar·FP32 tensor hash·finite·BASE40/80 계보 |
| 이번 시작 live safety | CLEAR: queue0/0, 허용 서비스 identity 일치, 가용 메모리72GiB 이상, swap0 |
| 복구 decode | PASS: raw/17PNG/MP4, 실제 VAE decode1회 |
| 복구 종료 감시 | NOT_CLEAN: UNKNOWN_GPU_PID |
| 최종 자원 관측 | 허용 서비스만 남음, queue0/0, 자체 unit inactive/MainPID0 |
| 비강체 앵커 | ANCHOR_UNSUITABLE 보존 |
| B034 방법 비교 | NOT_RUN |
| temporal | UNVERIFIED |

종료 중 한 표본은 queue0/0, 빈 cgroup PID 집합과 GPU에 남은 미분류 PID를 함께 기록했다. 같은 표본의 systemd MainPID는 그 PID와 일치했고 `/proc` starttime은 남아 있지만 command bytes는 비어 있었다. 이는 이번 종료의 서로 다른 관측 시점/회계를 보여주며, 안전 정책은 이를 임의 허용하지 않았다. worker returncode0/출력 PASS와 guard reason을 함께 보존한다. 다음 최종 관측은 미분류 PID0·자체 unit inactive였다. 이 자료로 과거 B034 가드의 원인을 소급 확정하지 않는다.

## 차량 영상 검토

Agent가 실제 SOURCE/TARGET/A0/BASE와 전체17프레임 시트, local0/8/16의 원본 크기 이미지를 정적으로 확인했다. 독립 인간 평가나 실제 속도의 연속 시청은 아니다.

| 축 | 관측과 판정 |
|---|---|
| Target 외형 | **FAIL.** A0/target의 어두운 클래식 전면·독립된 노출 바퀴·열린 상부 대신 닫힌 객실과 높은 루프의 현대적인 SUV/왜건형 차체가 전17장에 나타난다. 단순 배경 보존으로 교체 성공을 주장하지 않는다. |
| Source형 회귀 | source와 같은 차량군의 실루엣으로 돌아가는 근거가 있다. 단, source의 은색 SUV와 그릴/전면/색이 달라 정확한 원본 복사나 byte-copy라고 단정하지 않는다. |
| 거친 동작 | **PARTIAL 정적 근거.** 오른쪽 먼 위치에서 화면 왼쪽/앞으로 접근하며 크기가 커지고 측면이 더 보이는 흐름은 source와 대략 대응한다. 바퀴 회전·정확한 타이밍은 UNCERTAIN이다. |
| 보호 장면 | 산·숲·초지·도로 곡선·울타리의 큰 배치는 대체로 유지된다. 하지만 세부 수목·노면·산 질감은 흐려지거나 달라지고 상하 검은 가장자리가 있다. 원본 exact 보존 PASS는 아니다. |
| 새 그래픽·이중 객체 | 검토한17장에 B031형의 큰 별도 도로 차량 그래픽이나 뚜렷한 두 번째 차량은 관찰하지 못했다. 무결한 장면 보존 또는 일반적인 부재 보증은 아니다. |
| 형태·접촉 | 차량 몸통과 주행 실루엣은 대체로 연속적인 정적 배열이지만 작은 바퀴·접지·그림자·전면 세부는 UNCERTAIN이다. target 유지 실패와 별도 판정한다. |
| 시간 품질 | **UNVERIFIED.** MP4 전체 decode/브라우저 재생 가능성은 실제 연속 시청 품질 검수가 아니다. |

따라서 결합 편집 목표는 target 외형 때문에 FAIL이다. 이는 저장된 BASE의 관측이며 실행하지 않은 STEP의 효과를 성공/실패로 판정하는 근거가 아니다. 이번은 source-copy와 reference 활용을 구분해야 하는 이유를 다시 보여주며, CONTROL/STEP과 출력 support 작성은 자동 시작하지 않는다.

## 범위

신규 이미지·encoder·BASE/STEP sampler·학습·설치·재시도는0회다. 기존 latent·원본 MP4·전역 predecessor/guard·기존 실패 문서는 변경하지 않았다. raw 보존 후 브라우저용 MP4를 새로 인코딩했으므로 전체 작업을 재인코딩0으로 표현하지 않는다.

[계획](RECOVERY_PLAN.md), [전체 의뢰서](WORK_ORDER_KO.md), [계보](ARTIFACT_LINEAGE.json), [재현](REPRODUCE.md), [비용](COSTS.md), [짧은 해설](LESSON_KO.md).

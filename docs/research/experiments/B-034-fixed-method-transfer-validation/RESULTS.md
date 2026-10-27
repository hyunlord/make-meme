# B-034 결과 — BASE latent 보존, 방법 비교 BLOCKED

**BLOCKED_AT_BASE_TEARDOWN.** 새 차량/인물 입력을 사전에 고정하고 두 이미지 앵커를 생성했다. 차량은 영상 단계에 진입했으나 BASE 종료 시 watchdog의 `other_service_work` 기록 때문에 decode 이후를 중단했다. 따라서 같은 후합성 뒤 B033 방법의 추가 이득·회귀·무효는 이번에 판정할 수 없다. B033의 기존 국소 PARTIAL은 그대로이며 기본 채택하지 않는다.

## 실제로 본 결과

- 차량 A0는 높은 은색 SUV를 어두운 클래식 전면·노출 바퀴로 바꾸고 원본의 전면 접근 배치를 대체로 유지했다. 작은 크기 때문에 세부 target 일치·접촉은 UNCERTAIN이다.
- 인물 A0는 밝은 머리·무늬 상의·검은 하의를 반영했지만, 원본의 오른쪽 측면 보행 대신 큰 뒷모습을 중앙에 만들었다. **ANCHOR_UNSUITABLE**이며 다른 사진/사례로 채우지 않았다. 인물 영상은 전부 NOT_RUN이다.
- 차량 BASE는 실제40 scheduler step·80 model forward와 finite final latent 저장까지 완료했다. 그러나 디코딩하지 않았으므로 차량 영상의 target 유지·source 동작·경계 품질을 관측했다고 쓰지 않는다.

[앵커 판정](ANCHORS.md), [과제별 결과](CASE_OUTCOMES.md), [실제 실행·중단 근거](GUARD_EVENT.md), [비용](COSTS.md).

## 중단을 완료로 바꾸지 않는다

BASE worker의 결과 파일과 final latent는 완료를 기록하고 systemd returncode는0/MainPID는0이었다. 반면 supervisor reason은 `other_service_work`다. 마지막 기록의 cgroup.procs는 비어 있었고 직전에는 자체 worker PID가 있었다. 종료 시 GPU 관측 지연/경합 가능성이 있지만, 조건을 발동한 실제 GPU PID 집합과 queue 응답은 보존되지 않아 **원인 UNKNOWN**이다. 잠깐 발생한 실제 다른 작업도 배제할 수 없다.

이후 읽기 전용 확인에서는 queue가 비었고 허용된 기존 서비스만 남았으며 메모리/swap도 회복됐다. 이는 현재 상태의 증거이고 과거 가드 이유를 소급 무효화하지 않는다. `service_exit`만 허용하는 사전 downstream 계약을 삭제·완화하지 않고 BASE_D, CONTROL_D, STEP_S, STEP_D를 모두 미실행으로 남겼다. sampler 재시도·가드 수정·다른 프로세스 종료는0회다.

## 비교의 수용 범위

| 항목 | 실제 상태 |
|---|---|
| 고정 두 공개 입력과 원본/참조 계보 | 사전 고정, 입력 CPU 검사 PASS |
| Qwen 이미지 | 2/2 실행, 기술 완료; 차량 ELIGIBLE, 인물 결합 목표 FAIL |
| 차량 조건·원본 full-resolution VAE encode | 각 필요한 경로1회, 완료 |
| 차량 BASE sampler | 1회,40step/80forward, final latent 보존; 종료 가드 NOT_CLEAN |
| BASE/FINAL_ONLY/STEP 영상 decode | 0회, NOT_RUN |
| STEP sampler / clean converter 효과 | 0회, NOT_RUN |
| BASE 기반 target support·동일 후합성 | NOT_RUN, raw 영상 없이 주석을 추정하지 않음 |
| 새 모델/패키지/데이터 다운로드·학습·외부 생성 | 모두0 |
| 시간 품질·일반화·자동화 | UNVERIFIED / 미입증 |

source-copy의 대가로 배경만 좋아졌는지도 평가할 출력이 없다. 기술적인 latent 완료를 편집 품질 PASS로 바꾸지 않는다. 두 입력 중 좋은 subset만으로 시스템 성공률을 만들지 않는다.

## 보존과 다음 한 작업

원본 입력, 두 실제 A0와 실패, 차량 BASE final latent·source latent·조건 계보·원시 가드 기록을 보존했다. 검토 페이지에는 생성되지 않은 BASE/FINAL/STEP 영상을 NOT_RUN으로 표시한다. 브라우저의 기존 RGB MP4 색상 오류 때문에 source PNG에서 별도 yuv420p preview를 만들었으며 모델 입력 MP4는 해시 불변이다. 재생 가능성 확인은 인간의 연속 시간 품질 검수가 아니다.

다음은 **저장된 차량 BASE final latent의 제한된 VAE-only decode 가능 여부를 별도 승인 범위에서 확인하는 작업 하나**다. 먼저 가드 종료 기록과 현재 타 서비스 상태를 정확히 연결해야 하며, 이를 위해 같은 sampler를 다시 돌리지 않는다. 이번에는 새 guard·방법 튜닝·후속 실행을 시작하거나 예약하지 않는다. 비강체의 upstream 외형/자세 결합 실패는 미해결로 남는다.

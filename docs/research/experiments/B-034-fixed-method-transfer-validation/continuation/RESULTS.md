# B-034 CONTINUATION_01 결과

**FINAL_LATENT_ONLY는 완료했지만, 같은 RGB_POST 뒤의 뚜렷한 추가 이득은 관찰하지 못했다. 클래식 target 외형 FAIL은 그대로다. STEP은 새 래퍼의 loader 환경변수 전달 누락으로 첫 forward 전에 실패하여 방법 비교를 마치지 못했다.**

사전 계획9652805와 코드/영역 고정8b65e8a 이후 실행했다. 실패 포함 sampler 시도1회 예산을 소진했으므로 수정 재시도하지 않았다. 새 STEP 영상·final latent는 없으며 STEP_D는 NOT_RUN이다. 기존 BASE raw/영상/latent 및 과거 실패는 변경하지 않았다.

## 실제 시각 결과

SOURCE/TARGET/A0/BASE/FINAL_LATENT_ONLY, 동일 RGB_POST의 전체17프레임과 고정 local0/8/16을 agent가 정적으로 검토했다. 실제 속도의 연속 시청이나 독립 인간 평가는 아니며 **temporal=UNVERIFIED**다.

| 축 | BASE + RGB_POST | FINAL_LATENT_ONLY + 같은 RGB_POST | STEP |
|---|---|---|---|
| 클래식 target 외형 | FAIL: 노출 바퀴·긴 클래식 차체·열린 상부 대신 닫힌 SUV/왜건 | FAIL 유지: 지붕·앞유리·덮인 바퀴의 SUV형 그대로 | 평가 불가 |
| Source형 회귀 | 현대 차량군 실루엣. 정확한 원본 복사는 아님 | 같은 차량군이 유지됨 | 평가 불가 |
| 접근 동작 | 거친 접근·크기 증가·측면 변화 PARTIAL | 같은 거친 흐름. 추가 동작 이득 미관찰 | 평가 불가 |
| 보호 장면 | E=0은 source exact. 편집 안쪽 도로는 generated와 source가 다름 | 원거리 raw 배경은 원본에 가까워지지만 같은 POST 뒤 핵심 이득은 미관찰 | 평가 불가 |
| 경계·접촉 | 차량 옆 도로 strip, 바퀴 아래 검은 조각·색차가 남음 | 같은 하부/우측 조각과 톤 경계가 대체로 남음 | 평가 불가 |
| 물리적 그림자·가림 | UNCERTAIN / H=empty / MASK_PARTIAL | 동일 한계 | 평가 불가 |
| 큰 별도 도로 그래픽 | BASE부터 미관찰 | 부재를 개선으로 세지 않음 | 평가 불가 |

FINAL_ONLY raw에서는 source latent를 넣은 바깥 배경의 질감이 달라졌다. 그러나 이번 주 질문은 원거리 복원이 아니라 **동일 후합성 이후의 편집 내부·경계·접촉 추가 이득**이다. 해당 정적 비교에서는 **NO_BENEFIT(뚜렷한 추가 이득 미관찰)**로 남긴다. 미세한 차이를 전부 같다고 단정하지 않으며 수치 품질 점수나 유의성을 만들지 않는다.

STEP의 방법 판정은 **INCONCLUSIVE / 실제 방법 출력 NOT_RUN**이다. 실행 연결 오류를 clean-prediction 방법의 효과 없음이나 target 회복 실패로 해석하지 않는다. BASE부터 없던 target을 유지했다는 non-regression PASS도 사용하지 않는다. 결합 편집 목표는 확보된 BASE/CONTROL 모두 target 외형 때문에 FAIL이다.

## 완료·실패·미실행

| 단계 | 결과 |
|---|---|
| 종료 신원 최소 보완 | CPU14 fixture와 실제 CPU-only systemd lifecycle 검증 PASS |
| S/T/E/M 및 crop | STEP 전에 고정, H=empty/r4/feather4/기존 latent pooling, MASK_PARTIAL |
| CONTROL_FINAL_ONLY | 실제 decode1, finite FP32 `[3,17,512,896]`, PNG17장·24fps MP4 PASS |
| CONTROL 종료 감시 | 정상 종료 신원 receipt·자체 unit 정리·fresh safety PASS |
| STEP_S | **FAILED_BEFORE_FIRST_FORWARD**: `KeyError: 'B007E_LOADER_REPORT'` |
| STEP 실제 계산 | CPU staged weight 적재 후 실패, 모델 forward0/완료step0/clean constraint0 |
| STEP final latent / STEP_D | 없음 / NOT_RUN |
| BASE 재생성·재decode / source/reference encode | 모두0 |
| 새 이미지·학습·설치·다운로드·자동재시도 | 모두0 |

새 래퍼 [worker.py](code/worker.py)는 offline 변수 두 개만 설정하고 기존 [run_phase.py](../video_code/run_phase.py)의 `B007E_LOADER_REPORT` 설정을 빠뜨렸다. 그대로 재사용한 [staged_loader.py](../video_code/staged_loader.py)는 CPU 가중치 적재 뒤 보고서 경로를 `os.environ`에서 읽으며 KeyError를 냈다. 이 원인은 traceback과 실제 호출 코드로 확인된 **이번 실행 연결 오류**다. 새로운 커널·모델 한계·메모리 부족이 원인이라고 보고하지 않는다.

STEP supervisor의 guard_reason은 `COMPLETE`지만 worker exit=1, normal_exit_recorded=false, final decision=`UNIT_EXIT_NOT_VERIFIED`, 전체 status=`NOT_CLEAN`이다. 위험 PID가 사라진 관측을 실행 성공으로 해석하지 않았다. CONTROL에서 검증한 정상 종료 경로와 STEP의 비정상 종료는 구분한다. 자체 프로세스 종료·fresh safety와 비용은 [MEASUREMENTS](MEASUREMENTS.json), [COSTS](COSTS.md), [재현](REPRODUCE.md)에 기록한다.

## 보존한 한계와 결정

기존 BLOCKED_AT_BASE_TEARDOWN/other_service_work, RECOVERY_01 UNKNOWN_GPU_PID/NOT_CLEAN, 비강체 ANCHOR_UNSUITABLE/영상 NOT_RUN은 그대로다. 새 fixture나 CONTROL 종료 성공을 과거 실패에 소급 적용하지 않는다.

T는 BASE의 잘못된 SUV silhouette에 대한 output-assisted coarse annotation이다. 원하는 target의 GT가 아니며 이 영역은 다른 클래식 차체를 제약할 수 있다. 고정 detail crop은 원본 union의 오른쪽 전체 경계를 포함하지 않아 해당 seam은 full-frame17장으로 함께 확인했다. mask/crop을 결과에 맞춰 축소·확장하지 않았다. E=0 source exact는 합성 수식의 성질이다.

**B033 방법을 기본 채택할 추가 근거는 아직 없다.** 이번 STEP 효과는 미평가이고 앞단 target 외형 전파 실패도 해결되지 않았다. 다음 한 작업은 기존 loader의 실행 환경 계약을 사전 CPU 검사로 고정한 후, 별도 승인된 예산에서 **동일 저장 입력·동일 E/M의 남은 STEP/해당 decode만** 완료하는 것이다. 새 사례·강도·mask·모델·학습을 추가하지 않으며 이번 턴에서는 재시도하거나 예약하지 않는다.

[사용자 지시](WORK_ORDER_KO.md), [계획](PLAN_AMENDMENT.md), [가드 검토](GUARD_REVIEW.md), [support](SUPPORTS.md), [검증 한계](VALIDATION.md), [한국어 해설](LESSON_KO.md), [전달](DELIVERY.md).

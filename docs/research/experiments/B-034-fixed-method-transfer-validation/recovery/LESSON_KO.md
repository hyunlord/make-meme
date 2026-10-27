# 저장된 latent 복구: 네 가지 상태를 분리하기

## 직관과 수식

샘플링 완료, 저장물의 무결성, 프로세스 종료, 현재 자원 안전은 서로 다른 명제다. 마지막 scheduler 출력이 유한한 값으로 저장됐더라도 supervisor가 타 작업을 관측하면 다음 단계는 멈출 수 있다. 반대로 과거 가드의 발동 원인을 확정하지 못한다고 해서 새로운 시점의 별도 안전 판정까지 불가능한 것은 아니다.

이번 소비 계약은 `A = valid_hash ∧ valid_tensor ∧ valid_lineage`, `L_now = queues_empty ∧ process_identity_allowed ∧ headroom_ok ∧ swap_zero ∧ observations_ok`다. 명시적으로 승인된 복구 entrypoint는 `A ∧ L_now`를 요구한다. 과거 실행의 성공을 `L_now`로 소급 증명하지 않는다. 기존 downstream predecessor 검사도 그대로 남는다.

## 실제 텐서와 연산

저장물은 reference prefix나 noise가 아닌 생성 구간의 마지막 model-space `x0`다. tree는 `{'x0':[tensor]}`, FP32 shape는 `[16,5,64,112]`다. 이번 계산은 기존 WanVAE wrapper의 `D(x0)` 하나이며 기대 결과는 `[3,17,512,896]`이다. wrapper가 수행하는 normalization/scaling을 별도로 두 번 적용하지 않는다. source encode, DiT velocity prediction, scheduler step은 없다.

공식 decoder로 raw를 보존한 후 PNG/MP4를 만드는 것은 영상 모델의 새로운 sampling과 다르다. 다만 VAE decode 역시 실제 GPU 계산이므로 worker·메모리·실행 횟수에 포함한다. 24fps는 검토 시간축이며, source_fps=null인 공개 프레임의 실제 촬영 시간을 증명하지 않는다.

## 코드와 관측 근거

부모 계산은 [phase_decode.py](../video_code/phase_decode.py)의 `decode` 함수이며 기존 predecessor 정책은 [run_phase.py](../video_code/run_phase.py)에 남긴다. 새 복구의 구체적인 entrypoint·receipt·가드 관측은 [재현 기록](REPRODUCE.md), 실제 완료 여부와 차이는 [복구 결과](RECOVERY_RESULTS.md)에 연결한다. 과거 미보존 queue/PID는 새 telemetry로 복원할 수 없으며 UNKNOWN으로 남긴다.

## 질문

1. 현재 queue가 비어 있으면 과거 `other_service_work`가 오탐이었다고 말할 수 있는가?
2. final latent hash가 맞으면 GPU 안전 검사를 생략할 수 있는가?
3. BASE MP4가 만들어지면 B033 clean-prediction 방법의 전이 성공인가?

## 별도 해설

1. 아니다. 서로 다른 시점의 관측이며 발동 순간 기록이 없다.
2. 아니다. 무결성은 파일/계산 계보의 성질이고 실행 안전은 현재 시스템의 성질이다.
3. 아니다. 이번에는 BASE만 복원하며 CONTROL/STEP 비교는 NOT_RUN이다. BASE의 시각 품질 역시 외형·동작·장면·형태를 따로 검토해야 한다.

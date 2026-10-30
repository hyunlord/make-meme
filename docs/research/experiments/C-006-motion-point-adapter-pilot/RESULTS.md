# C-006 — 실제 학습·9영상 완료, 동작 이득 미입증

**주 평가: NO_ESTABLISHED_GAIN. 기본 채택하지 않는다.** horsejump-low와 lucia 각각의 BASE / TRACK_ON / TRACK_NULL 6개, 기존 개 편집 앵커의 별도 HEAD_ONLY 진단 3개를 새로 생성했다. 모든 영상은 416×240, 33프레임, 50 scheduler step / 100 model_fn call이다. 원래 출력 양끝을 앵커로 덮어쓰거나 색보정하지 않았다. 전체 33장과 고정 인덱스를 같은 시점으로 비교했으며 실제 연속 지각 검수는 하지 않아 **temporal=UNVERIFIED**다.

## ON이 BASE/NULL보다 동작을 잘 따랐는가?

| 구분 | 같은 인덱스에서 실제 관측한 결과 | 판정 |
|---|---|---|
| horsejump-low, 동일 개체 | 세 조건 모두 접근→도약→우측 진행의 거친 순서는 남는다. ON이 BASE/NULL보다 보이는 다리 사건이나 재등장을 정확히 따르는 근거는 없다. ON/NULL 모두 t1부터 붉은 파편이 생기고 4~28에서 화면을 넓게 덮으며, 말·기수의 중복 윤곽과 잔상이 29~32에도 남는다. BASE도 장애물·배경 색 파편이 있지만 대상이 더 식별 가능하다. | NO_ESTABLISHED_GAIN, 외형·보호 장면의 명확한 회귀 |
| lucia, 동일 개체 | 우향 보행과 대략적인 보폭 교대는 세 조건에 있다. 8의 벌어진 보폭, 16의 겹침, 24의 분리에서 ON의 추가 정확도는 입증되지 않는다. ON/NULL은 대략 3~29의 주황·붉은 배경, 분홍 보도, 흐린 머리·등 윤곽이 매우 비슷하다. BASE도 흰 신발을 검정 신발처럼 바꾸고 벤치를 손상하지만 녹색 장면은 더 잘 남는다. | NO_ESTABLISHED_GAIN, 외형·보호 장면 회귀 |
| 기존 개 편집 앵커, HEAD_ONLY | 검정/흰 외형과 거친 접근은 일부 남지만 ON/NULL의 대략 2~32에서 얼굴의 녹회색 잔상·블록형 분절과 붉은 잔디가 관측된다. NULL의 16~28 일부에서 파편이 더 크지만 ON이 BASE보다 코·눈 진행을 정확히 따른다는 근거는 없다. | NO_ESTABLISHED_GAIN, 얼굴 식별성과 장면 회귀 |

ON과 NULL의 실제 motion context와 출력은 다르다. 그 차이를 유용한 제어로 올리지 않는다. 두 신규 조건이 모두 회귀했으므로 실제 궤적이 불필요하다고 결론낼 수도 없다. 가려진 발·관절이나 중복된 출력 윤곽을 임의로 대응시키지 않았다. 표면점 대응은 **MOTION_MEASUREMENT_LIMITED**, 모호하거나 사라진 부위는 AMBIGUOUS/MISSING이며 정밀 trajectory RMSE는 null이다. 발 접촉은 UNCERTAIN이다.

## 같은 개체와 편집 앵커 진단의 차이

주 평가는 원본 영상의 실제 양끝을 사용한 self reconstruction이며 원본의 중간 RGB/clean latent를 sampler에 넣지 않았다. train/validation/test는 원본 시퀀스별 8/2/2로 분리했다. DAVIS 객체 mask를 사용한 MASK_GIVEN/DATASET_MASK_ASSISTED 실험으로, SAM의 일반 객체 발견 성능을 검증한 것이 아니다.

별도 개 진단은 학습에서 제외한 기존 C-001 원본·기존 두 편집 앵커와 SAM 윤곽을 재사용했다. C-004 교정 끝 앵커와 C-003 구조선은 쓰지 않았다. 코·화면 좌우 눈 세 점만 수동으로 대응시켜 endpoint bbox 비율로 retarget했다. tracker 원본 끝점과 수동 source 끝점의 거리는 416 좌표에서 1.17/1.47/0.81px였지만 수동 오차 약 ±2px와 motion blur가 있으므로 GT 정확도 검증은 아니다. 끝 앵커의 낮은 자세 충돌, 수동 bbox, 얼굴만 있는 입력의 한계를 유지한다. 다리 제어 또는 일반적인 개체 교체 성공을 주장하지 않는다.

## 실제로 학습됐는가?

실행 판정은 **GRADIENT_CONNECTED / TRAIN_COMPLETE / CHECKPOINT_RELOAD**다. FP32 trainable parameter 1,275,072개만 256회 업데이트했고 8개 학습 영상은 각각 32번 선택됐다. backbone은 BF16 동결이며 optimizer에는 adapter만 들어갔다.

첫 정상 update에서 native↔bypass와 native↔zero-adapter 최대 차이는 모두 0이었다. 실제 마지막 네 block 및 head 입력에 gradient가 연결됐고 첫 update의 zero-init projection 뒤 두 번째 update에서 MLP gradient도 관측됐다. 동결 parameter version·표본 불변, FP32 optimizer 상태와 RNG/cursor의 저장·readback, 최종 checkpoint 재로딩 예측 차이 0을 확인했다. trained checkpoint 중간부터의 장시간 연속 재개는 실행하지 않았다.

고정 validation 6개 probe의 one-step Flow Matching loss는 모두 감소했다. 그러나 같은 모델을 CFG5로 50 step 연쇄 실행한 영상에서는 색과 형태의 회귀가 발생했다. **loss·gradient·저장 경로의 성공은 영상 품질의 성공이 아니다.** 자료 수, 학습량, CFG 조건, residual 크기, 점 표현 중 하나를 원인으로 확정할 수 없다.

## 입력 관측과 비용

각 사례의 세 실행은 실제 초기 noise, VACE context, mask64, condition RGB 요약 hash가 같았다. ON/NULL은 같은 최종 checkpoint와 endpoint patch를 사용하며 point context가 달랐다. NULL은 실제 중간 tracker 위치·visibility/validity를 읽지 않았다. 생성 mask와 33→9 압축 한계는 유지했고 관측용 추가 DiT forward는 0이다.

학습 active 256.00초, 실제 학습 forward/backward 256회, 고정 validation 18회, 진단 5회다. 영상 sampler 9회/상한10회, 총 450step/900call, raw 297프레임을 보존했다. 영상 시간은 COSTS에 셀별로 기록한다. CoTracker source 12 pass 7.382초와 별도 개 1 pass 1.361초, 성공한 주 cache 41.702초와 별도 cache 7.703초를 분리한다. 수동 주석·검토 시간은 별도 timer가 없어 null이다. imagegen·backbone 학습·패키지 설치·품질 재시도·VAE-only 복구는 0회다.

기계적 실패 두 건도 보존한다. 최초 cache는 CPU latent와 CUDA sampling grid의 device 불일치로 4 VAE encode 후 실패했다. 최초 학습은 y=None에서 사용되지 않는 native flag에 대한 과도한 assert 때문에 validation/학습 core forward 전에 실패했다. 둘 모두 raw NOT_CLEAN / OBSERVATION_FAILED / cgroup REMOVED:exit_not_verified를 보존한다. 해당 시점의 원인은 worker exception이었고 resource threshold/OOM/external 충돌은 관측되지 않았다. device만 맞추고 잘못된 assert를 제거한 뒤, 저장된 step 0 상태에서 승인된 기계적 복구를 수행했다. 실패를 PASS로 바꾸거나 사용량을 되돌리지 않았다.

## 종료와 다음 논의

현재 adapter를 기본 채택하지 않는다. 다음에 논의할 한 가지는 **one-step FM 오차 감소가 실제 CFG sampling에서 기존 예측 보존과 안정성으로 이어지지 않은 간극**이다. 이를 확인하기 위한 추가 학습·scale/seed/prompt 탐색은 이번에 시작하지 않았다. 점 대응 연구 전체의 실패나 궤적 정보의 무용성을 주장하지 않는다.

C-001 PARTIAL, C-002 차량 TRADE_OFF/개 COARSE_CONTROL_ONLY, C-003/C-004 NO_ESTABLISHED_GAIN, C-005 자원 중단과 A/B의 실패·UNKNOWN은 그대로 보존한다. [수치](NUMERICS.json), [비용](COSTS.json), [이론·코드 해설](LESSON_KO.md), [전달 검증](DELIVERY.json)을 함께 본다.

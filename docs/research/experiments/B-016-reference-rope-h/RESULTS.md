# B-016 결과: reference H120만으로 착석·후기 얼굴 손상을 해결하지 못했다

**COMPLETED / 실행·단일 개입 검증 PASS / 전신 전이 FAIL / 목표 품질 개선 NOT_ESTABLISHED / temporal UNVERIFIED.**

기존 CFG_MOV_H0와 신규 CFG_MOV_H120의 전체17장을 비교했다. H120도 침대 위 착석과 지지 앞발을 유지했다. 후반 머리 변화는 생기지만 위·옆으로 꺾이는 양상과 눈·주둥이·귀 손상이 남아 원본의 명료한 roll을 더 잘 재현했다고 수용할 수 없다. 일부 프레임의 선명도 차이를 전체 동작·실제 개체 보존 성공으로 올리지 않는다. ALG는 계속 OFF이며 기본 경로로 채택하지 않는다.

## 실제 실행과 단일 변경

시작 원격 `6ef151b090d6c839e99d84a3547e7671f128e5ac`, 착수·평가 고정 `bae4123be29ad14679193f71a51b82bb66f17e83`, 실행 전 코드·설정 원격 고정 `68c5af7ee7eaad07e09769c3547b8ebe0ef7b964`. [PLAN](PLAN.md)과 [사전 평가](PREREG_EVALUATION.md)를 출력 후 변경하지 않았다.

- 신규 **P0 / PROBE1 / S1 / D1 / sampler1 / retry0**. 신규 모델·다운로드·학습·LoRA·imagegen·외부 생성0. 기존 결과·A·upstream·모델을 보존했다.
- 원본 source f7..23, 실제 Lab RGB, RED/WHITE reference mask, RGB driving/mask, prompt, negative empty, seed20261022·실제 noise/RNG, UniPC40·shift3·CFG5, history=None, additional_ref=None, replace_flag=False, 512×896·17f·24fps와 기존 mixed loader/FlashAttention을 유지했다. 입력은 기존512×288 자료에서 확대·crop된 것으로 새 고해상도 정보가 아니다.
- B-013 LAB_MOV cache SHA `b7e5c62d8cb3a67e3cca0e104a536cf54c86937fa136f8554dbe55062ba9bf5d`와 전체16leaf를 그대로 사용했다. 초기 noise value SHA `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`도 같다. P 재인코딩·4개 driving leaf 교체 실험이 아니다. [입력·부모 계보](PREREGISTERED_INPUTS.json).
- 유일한 생성 개입은 reference H 위치 인덱스120이다. reference T/W=0, generated T/H/W=1/0/0, driving T/H/W=1/0/120을 유지했다. 120픽셀 이동, reference latent 내용 변경, 공식 replacement 전체 재현이 아니다.

## 실제 patch 연결과 검증의 범위

원본 SCAIL commit `78fe19576bb06be96c2375e088574a262a300edb`는 수정하지 않았다. [격리 모델 diff](MODEL_PATCH.diff)는 optional scalar 인자·ref H 지정·scalar 위치 관측만 추가한다. 기존 CFG sampler 추출 경로를 재사용했고 ALG3항식·필터·88forward 경로는 사용하지 않았다.

실제 GPU worker에서 canonical module `wan.modules.model_scail2`의 class file와 forward globals가 격리 모듈 SHA `33f51bc678bf3b888686f1c707e5275735085069d030da0ba22af98c3051f54b`와 일치했다. strict1307개 tensor key/shape 적재, 16,395,544,384parameters,8192 complex128 frequency,40blocks를 확인했다.

**실제40step·80forward**, 각40block에80회 위치 검사를 수행했다. 상세 trace는 첫/마지막 step의 두 CFG branch160행만 저장했다. Q/K가 같은 원래 RoPE 함수를 사용하며 dense attention 교체·전체 attention map·관측용 추가 forward는 없다. 실제 token 수는 reference1792, generated8960, driving2240이다. [호출·출력 장부](RUN_LEDGER.json).

[CPU 감사](CPU_AUDIT.json)는10검사 PASS다. OFF/0 helper 일치, ref 외 출력 bit-exact, Q/K norm 최대차9.5367e-7, ref-ref logit 최대차7.1526e-7은 사전 atol/rtol2e-5 안이다. cross logit 최대차는 video2.406847/drive1.898464다. 이는 **고정 synthetic Q/K의 pre-softmax 검사**이며 실제 softmax/후속 layer 불변 증거가 아니다.

보존한 한계: CUDA-hidden full-package import는 upstream T5의 current_device 기본값에서 실패했다. 별도 inert namespace meta fixture는 그 프로세스만의 구조 검사이며 실제 GPU 연결을 대신하지 않는다. 이후 실제 full runtime 연결은 위처럼 검증했다. 새 typed helper2개는 오류·경고0이지만 상속 dynamic adapter3개의 typecheck90오류145경고는 **NOT_CLEAN**이다. 검사 억제·무관한 전면 리팩터링은 하지 않았다.

## 전체17프레임 정적 비교

두 agent가 같은 labelled 자료의 전체17장을 실제로 열어 판독했다. 독립 인간 ground truth나 blind 통계평가가 아니다. 정밀 각도·관절 좌표·gain·유의성을 만들지 않았고, 이미지·latent를 사후 warp/보간/정렬하지 않았다.

| 항목 | 기존 CFG_MOV_H0 | 신규 CFG_MOV_H120 |
|---|---|---|
| 전신·앞발 | 착석·침대 지지 앞발, **FAIL** | 같은 착석·지지 앞발, **FAIL** |
| 초기 상태 | reference에 가까운 정면 착석 | 처음부터 머리 기울임·화면 배치가 다름; source 시간 변화 재현 자체가 아님 |
| 후반 국소 변화 | local12~16 변화가 커지나 심한 얼굴 번짐 | local12는 비교적 읽히지만 이후 위/옆으로 꺾임·왜곡. source roll 방향·증가 순서의 유용한 개선 **미입증** |
| 눈·귀·주둥이·목 | 후기 형상 손상 | 후기 손상 지속. 일부 더 읽히는 프레임으로 전체 개선 판정 불가 |
| 외형·체형 | 검은 짧은 털·처진 귀·넓은 몸통 | 같은 견종 특징과 묵직한 착석 몸통은 남음; 실제 개체 특히 후기 **UNCERTAIN** |
| source 외형 누수 | 뚜렷한 옅은 털·가는 전신 대체는 관측 안 됨 | 뚜렷한 옅은 털·가는 전신 대체는 관측 안 됨 |
| 배경·프레이밍 | reference 방·침대 유지 | 방은 유지되나 침구 밝기·색/노출·배치 차이; 의도치 않은 변화로 기록 |
| 시간 품질 | **UNVERIFIED** | **UNVERIFIED** |

사전 local0/sourcef7에서는 이미 H120의 머리 각도와 배치가 다르다. local12/sourcef19에서는 두 출력 모두 앉아 있고 H120 얼굴이 H0보다 부분적으로 선명해 보이지만, local14/sourcef21와 local16/sourcef23에서 H120의 머리는 위/옆으로 돌아 눈·주둥이·목 대응이 불명확해진다. 원본은 직립 상태에서 머리-몸통 상대 roll이 증가한다. 두 출력의 단순 반응이나 큰 변화만으로 원본 안무 성공이라고 하지 않는다.

정밀한 발끝·꼬리·가림·접촉은 UNCERTAIN이다. 기존 mask의 얇은 경계·반사 문제는 PARTIAL_UNRESOLVED이며 이번에 보정하지 않았다. reference 침실 유지 자체는 animation의 실패가 아니다. H120이 영상에 영향을 줬다는 사실과 reference pose/identity가 성공적으로 분리됐다는 주장은 다르다. 한 seed·한 사례와 비결정성 한계상 일반화·상용급 품질·새 방법을 주장하지 않는다.

## 실제 산출물·자원·재현

최종 FP32 latent `[16,5,112,64]`를 decode 전에 원자 저장·finite·readback 검증했다. 값 SHA `156aaae4753a2d00508b1cf6f6a69702822c95e0889a9f4267a8cd7c715d9bc5`는 초기 noise와 다르다. S 정상 종료와 자원 회복 후 VAE-only D를 한 번 실행했다. raw는 finite `[3,17,896,512]`, MP4는17f·24fps·0.708333초다. 첫/마지막 표본 간격16/24초와 파일 길이17/24초를 구분한다.

| 산출물 | SHA256 |
|---|---|
| final_latent.safetensors | `f56454aabc78db6156ed143c6f4aebf3d46e51c90e15639d8873ba9becbdf29f` |
| raw_output.pt | `f41fbd2d06a098d64c05e3e20a260a7c8f5d5cf60fe00fd5ffb5296c89bafb56` |
| output.mp4 | `8812534d363e314c62bbf4008c22e98d794afccad0e548de5ba0c716efae6253` |

S guard1057.032초·worker1054.303초·sampler965.419초, D guard16.223초. CUDA peak allocated33.846GiB, cgroup peak62.005GiB, 최소 시스템 가용52.605GiB, swap/OOM0. cgroup high3545는 숨기지 않는다. 기존24GiB headroom을 낮추지 않았다. RSS/cgroup/CUDA/시스템 메모리를 별도 물리 메모리처럼 합산하지 않는다. 기존 H0와 실측 시간은 다르지만 비동시 실행·메모리 회계/실효 cap 차이 때문에 성능 개선 benchmark라고 주장하지 않는다. [실측](MEASUREMENTS.md), [원자료 요약](MEASUREMENTS.json).

종료 후95개 code/input/cache hash와8개 모델 stat를 확인했다. 모델은 이전 전체SHA+현재 size/mtime이며 이번에 전체 가중치를 재해시했다고 하지 않는다. 자체 watchdog/pipeline은 inactive/MainPID0, 보호 서비스 queue는 idle이었다. 신규 GPU 작업은 모두 끝났다.

비공개 viewer는 source/reference/H0/H120 네 열, 전체17장·사전 사건·native24fps 비교 MP4를 제공한다. 기존 H0 PNG17장을 byte 그대로 복사하고 새 raw만 동일 양자화했다. 파일 재생/버튼 QA는 실제 연속 영상의 지각적 품질 확인과 다르며 temporal은 UNVERIFIED다. 최초 CPU renderer 명령의 미배치 스크립트 경로 오류는 보존했고 고정 도구 복사 후 렌더를 완료했다. 모델 재시도가 아니다.

[한국어 수식·코드 해설](../../lessons/B-016-rope-and-spatial-conditioning.md), [재현](REPRODUCE.md), [실제 호출 기록](RUN_LEDGER.md)을 함께 제공한다. 공개에는 문서·비민감 코드·설정·해시만 포함하며 미디어·cache·latent·weights는 공개하지 않는다. private ZIP은 검증 후 별도 전달 기록으로 연결한다.

## 다음 가설 하나 — 실행하지 않음

**실제 동물의 identity와 reference 자세를 구분하도록 학습할 paired 데이터가 부족한 것이 착석 고정의 주요 제약일 수 있다.** 다음 한 작업은 같은 개체의 서로 다른 자세 reference와 목표 동작 영상으로 구성할 수 있는 허가된 소규모 paired 학습 데이터의 타당성 감사다. input/reference/target·가림·개체별 분할과 정답 누출을 먼저 확인하고, 실제 Lab 정답 영상이 없으면 다른 강아지를 Lab target으로 쓰지 않는다.

이는 현재 결과로 원인이 증명됐다는 뜻이 아니며 adapter 학습 성공을 보장하지 않는다. offset 숫자 탐색 대신 학습으로 pose/identity 분리를 검증할 데이터가 있는지 한 가설을 준비하려는 것이다. **이번에는 데이터 수집·추가 모델·학습·추론을 실행하지 않았다.** offset sweep·추가seed·ALG결합도0으로 종료한다.

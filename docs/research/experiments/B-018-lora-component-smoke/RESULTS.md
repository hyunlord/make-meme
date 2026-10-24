# B-018 — 실제 attention LoRA backward·update·reload 통과

**COMPONENT_BACKWARD_PASS / COMPONENT_UPDATE_RELOAD_PASS.** 기존 SCAIL 마지막 self-attention 한 모듈에서 공식 FlashAttention2 backward와 AdamW3회 업데이트를 실행했다. 이는 **SYNTHETIC_TENSOR_CONTRACT_TEST**이며 동물 데이터 학습이나 영상 품질 실험이 아니다. B-017의 RIGHTS_PENDING/DATA_GAP는 그대로다.

## 실제 실행

사전 고정·원격 확인 commit `2b562188cc0ad30cf822583d53a3d66babbd8e1e` 후 GPU worker1/1을 실행했다. 재시도0, attention forward8회, backward3회, optimizer update3/3회다. 전체 모델·인코더·VAE·영상 sampler·개인 미디어·조건 cache 사용0, 새 다운로드0이다.

선택한 `blocks.39.self_attn.`은 실제10tensor,104,888,320개 기반 parameter, 원본F32 payload419,553,280bytes다. 공식 dim5120/head40/head_dim128과 RoPE를 유지하고 x/pseudo target `[1,36,5120]`을 사용했다. projection BF16·norm원본FP32·adapter FP32·loss FP32, Q/V rank4·alpha4·dropout0, adapter81,920개만 AdamW lr1e-4/wd0 대상으로 삼았다.

| update | synthetic MSE | Q A/B grad norm | V A/B grad norm | 관측 구간 시간 |
|---|---:|---:|---:|---:|
| 1 | 1.5443342924 | 0 / 0.019751525 | 0 / 0.011200055 | 0.8341s |
| 2 | 1.5443276167 | 0.001475579 / 0.019745743 | 0.001597707 / 0.011199303 | 0.4727s |
| 3 | 1.5442810059 | 0.002951117 / 0.022136787 | 0.003195208 / 0.012884749 | 0.4691s |

시간에는 forward/backward/update와 해당 검사·hash 비용이 포함되며 순수 kernel latency가 아니다. loss 감소는 참고일 뿐 추가 학습이나 품질 성공의 근거가 아니다. 첫 A gradient0은 Bzero 초기화와 일치하고, 이후 A/B 모두 finite 비영 gradient와 실제 parameter delta를 보였다. 각 graph에 `FlashAttnVarlenFuncBackward`가 존재하고 backward가 완료됐다. SDPA fallback은 사용하지 않았다.

## 불변·복원 검증

- 기반 parameter는 optimizer 객체 집합에서 제외되고 grad=None, runtime cast 후 hash가 모든 update 전후 동일했다.
- Bzero vs baseline, fresh component+saved adapter vs trained, adapter OFF vs baseline: **max absolute error 모두0**. 사전 tolerance atol/rtol1e-3를 변경하지 않았다.
- fresh component는 같은 선택 가중치를 새로 적재했고 기반 hash도 동일했다. adapter payload는 별도 safetensors+해시 schema이며 TEST_ONLY/NOT_FOR_INFERENCE다.
- 원본 선택10개 host tensor를 끝에 재hash했다. checkpoint size/mtime와 공식 source SHA도 유지됐다. 전체65GB 파일을 이번에 새로 rehash한 것은 아니다.
- 실제 input/target/RNG fixture와 initial/final adapter는 비공개 보존했다. 현재 inference 경로에 연결하지 않았다.

[실제 결과·해시](result.json), [update 상세](updates.json), [실행 코드 고정](code-freeze.json), [공식 attention 계약](ATTENTION_CONTRACT.md).

## 자원·검증 한계

Worker 내부 관측7.9725초, CUDA peak allocated297,412,096bytes(283.63MiB). 이는 전체 통합 메모리 사용량이나 full-model training peak가 아니다. watchdog의 전체 소요 및 시스템/RSS/cgroup은 [실측](MEASUREMENTS.json)에서 별도로 기록한다. 자체 worker/watchdog 모두 inactive·MainPID0, 기존 서비스 식별과 idle queue 보존을 확인했다.

CPU11검사(LoRA7+guard/precision4) 및 공식 RoPE AST helper36token CPU gradient 검사가 통과했다. AST helper 검사는 full package/GPU 검증과 구분한다. GPU 전에 norm BF16반올림 문제를 찾아 FP32 직접 보존으로 수정하고 회귀 검사를 추가했다. Helper Ruff 통과, typecheck0errors/19warnings **NOT_CLEAN**이다. 광범위 typing 정리나 환경 변경은 하지 않았다.

**FULL_MODEL_TRAINING=NOT_RUN, VIDEO_QUALITY=NOT_RUN, IDENTITY_POSE_DISENTANGLEMENT=NOT_RUN.** 실제 FlashAttention backward 성공은 전체40block·17프레임 학습의 메모리 적합성, FM 목적함수, 동물 일반화 또는 공식 SAT LoRA recipe 완성을 뜻하지 않는다.

## 다음 한 연구

**동일한 synthetic 계약에서 마지막 transformer block 전체로 범위를 한 단계 넓힌 제한적 backward·메모리 검증 계획**을 제안한다. attention 단독에서 빠진 residual·cross-attention·MLP 경로의 gradient 연결과 activation 비용을 확인하는 질문이다. 실제 데이터 권한 확보는 별도 과제로 남으며, 이번에 다음 block 실험·전체 모델 학습·추가 생성은 시작하지 않았다.

[한국어 수식·코드·관측 해설과 질문/답안](../../lessons/B-018-lora-component.md), [재현](REPRODUCE.md), [전달 검증](DELIVERY.md).

## 종료 후 정적 검사 추가 관측

Runner/guard/AST-helper 범위의 basedpyright 검사에는 **20errors/135warnings**가 남았다. 동적 공식 모듈 import와 `nn.Module` 속성, 혼합 dict 추론, AST 함수 경계, 반복문 후 변수 수명에서 발생했다. 실제 worker 성공과 별개로 코드의 정적 타입 품질은 **NOT_CLEAN**이다. 실행한 frozen code를 사후 바꿔 검사 결과를 감추거나 GPU를 다시 돌리지 않았다. 상세 진단은 비공개 로그에 보존한다. 이 구현을 일반 학습 프레임워크나 배포 준비 코드라고 부르지 않는다.

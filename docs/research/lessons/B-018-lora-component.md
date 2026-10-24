# B018 — 작은 LoRA가 실제 역전파 경로에 연결됐는가

현재 상태: 공식 소스 계약 및 CPU 11개 검사 PASS(LoRA helper7+guard4, 1.22초), 단일 GPU worker에서 COMPONENT_UPDATE_RELOAD_PASS. 실제 optimizer3회·attention forward8회를 마쳤다. helper typing은0 errors/19 warnings로 NOT_CLEAN이다. 이 실험은 `SYNTHETIC_TENSOR_CONTRACT_TEST`이며 실제 반려견 자료·FM target·영상 생성은 사용하지 않는다. B017의 학습 권리 미확인과 Lab Y 부재는 그대로다.

## 1. 직관과 수식

고정 가중치 W0에 작은 보정만 학습한다. column-vector 표기에서

\[
h=W_0x+b+sBAx,\quad s=\alpha/r,
\]

A는 `[r,d_in]`, B는 `[d_out,r]`다. q와 v 각각 dim5120, rank4이면 adapter는 projection당40960개, 합81920개다. 실행은 이 q/v adapter 객체만 명시적으로 optimizer에 넣고 기반 parameter 불변을 검사했다. 원논문 [LoRA](https://arxiv.org/abs/2106.09685v2)는 이 저랭크 parameterization의 근거이지 이번 동물 동작 성능의 보장이 아니다.

출력에 대한 gradient를 g라 하면 한 표본에서

\[
\nabla_B L=s g(Ax)^T,\qquad \nabla_A L=s B^Tg x^T.
\]

B=0이면 첫 A gradient는0이고 B gradient는 일반적으로0이 아닐 수 있다. 이후 B가 바뀌면 A gradient도 생길 수 있다. ‘일반적으로’는 보장이 아니므로 actual finite gradient와 parameter delta를 측정한다. loss 값이 존재하거나 tensor 이름에 lora가 포함됐다는 사실만으로 optimizer 연결을 인정하지 않는다.

## 2. freeze와 graph 차단은 다르다

W0의 `requires_grad=False`는 해당 parameter gradient를 저장하지 않는다는 뜻이다. 고정층 뒤에서 앞쪽 adapter로 derivative를 전달해야 할 수 있다. 학습 branch 전체를 `no_grad`/`inference_mode`로 실행하면 필요한 graph까지 없어진다. `eval()`은 dropout 등 모듈 동작 모드이며 gradient 계산을 끄는 명령이 아니다. [PyTorch autograd](https://docs.pytorch.org/docs/2.14/notes/autograd.html#locally-disabling-gradient-computation).

정확한 검사는 adapter parameter 객체만 optimizer에 포함되는지, base grad=None인지, base 값이 유지되는지, adapter 저장/새 instance reload가 같은 입력 출력을 복원하는지다. BF16 연산과 FP32 adapter master parameter를 구분하며, dtype cast가 autograd를 자동으로 끊는다고 가정하지 않는다.

## 3. 실제 module·shape·RoPE

[공식 WanSelfAttention](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L251-L305)의 입력은 `[1,36,5120]`, Q/K/V는 `[1,36,40,128]`로 실제 실행했다. Q/K RMSNorm은 head reshape 이전 전체5120축이다. ref16/video16/pose4를 joint attention하며 Q/K RoPE를 적용한다. T/H/W 주파수는 complex22/21/21로 나뉘고 pose multiplier에는 공간 average pooling이 포함된다. [정확한 계약](../experiments/B-018-lora-component-smoke/ATTENTION_CONTRACT.md)을 따른다.

FA는 attention score 전체를 메모리에 보관하는 단순 구현과 다른 실행 전략을 사용하지만, forward 가능성이 backward kernel 지원이나 전체 학습 메모리 fit을 보장하지 않는다. 이번에는 기존 FA 경로를 실제 backward까지 통과하는지 확인하며 다른 backend로 자동 대체하지 않는다.

## 4. 이 loss는 Flow Matching이 아니다

이번 목적함수는 `mean((F(x)-y_synthetic)^2)`다. x와 y는 고정 수치 배열이며 영상 latent 경로·sigma·noise-minus-data target이 없다. 따라서 loss가 내려가도 FM 학습이나 동물 motion 학습이라고 부를 수 없다. 실제 SAT RFLoss는 Y latent와 noise에서 `(1-sigma)Y+sigma*noise`, target=`noise-Y`를 만들고 history/OCR 제외 mask를 적용한다. [공식 RFLoss](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/loss.py#L653-L766).

이번의 성공은 코드 배선·선택 커널·update/reload에 한정된다. 전체 모델 적재, text/VAE 조건,40block activation,17프레임 backward, 일반화와 영상 품질은 NOT_RUN이다. 3 update 안에 loss가 단조 감소하지 않는다고 추가 학습하거나 seed를 바꾸지 않는다.

## 5. 실제 관측

선택 가중치 header를 실제 확인했다. 마지막 `blocks.39.self_attn.`의 q/k/v/o weight·bias와 norm_q/norm_k weight 총10개이며 모두 원본 F32다. payload 합은419,553,280 bytes, parameter 수는104,888,320개다. 이 수치는 선택 파일 내용의 크기이지 GPU peak memory가 아니다. 로컬 공식 두 소스 파일 SHA도 Spark header receipt와 일치했다. CPU helper는 FP32에서 Bzero 출력 일치·gradient·freeze·save/reload를 검사했다. 최종 CPU suite는11 PASS이며, 이 결과를 CUDA FA backward로 대체하지 않는다. GPU receipt `reports/result.json`과 `reports/updates.json`을 실제 읽어 아래 결과를 확인했다. header와 소스 판독을 runtime PASS로 쓰지 않는다. TEST_ONLY adapter를 기존 inference에 활성화하지 않는다.

단일 worker의 기록 시간은7.9724729초, 실제 update는3회, 완료된 attention forward는8회다. 각 backward graph에 `FlashAttnVarlenFuncBackward`가 관측됐으며 공식 FA2 wrapper 경로였다. 첫 backward의 q.A/v.A gradient norm은 둘 다0, q.B/v.B는 각각0.0197515/0.0112001이었다. 두 번째 A norm은0.00147558/0.00159771, 세 번째는0.00295112/0.00319521로 실제 비영이 됐다. B gradient는 세 번 모두 비영·finite였다. 실제 adapter delta도 기록됐으며 첫 A delta0과 이후 비영 delta를 구분했다.

| update | synthetic MSE | 판정 범위 |
|---|---:|---|
| 1 | 1.5443342924 | Bzero에서 B gradient·update 연결 |
| 2 | 1.5443276167 | A/B gradient·update 연결 |
| 3 | 1.5442810059 | 제한된 세 번째 update 완료 |

Bzero 대비 baseline, 저장 adapter의 fresh reload, adapter OFF 대비 baseline의 max absolute error는 모두0이었다. 사전 tolerance는 atol=rtol=1e-3였으며 결과를 보고 완화하지 않았다. 선택 payload의 저장 hash와 실행 dtype의 기반 tensor hash가 보존됐고, fresh instance에서도 같은 기반 값이 확인됐다. 전체65GB 파일을 다시 읽어 hash한 검증이라고 확대하지 않는다.

CUDA allocator peak allocated는297,412,096 bytes다. 이는 PyTorch allocator peak이며 시스템 통합 메모리·RSS·cgroup peak와 같지 않다. 한 모듈36token 성공을 전체40block의 학습 메모리 가능성으로 추정하지 않는다. loss의 작은 감소도 실제 영상 품질 개선이 아니다. FULL_MODEL_TRAINING / VIDEO_QUALITY / IDENTITY_POSE_DISENTANGLEMENT는 모두 NOT_RUN이다.

### 재현 입력과 코드 경계

사전등록 commit은 `2b562188cc0ad30cf822583d53a3d66babbd8e1e`다. `configs/smoke.json`은 seed20261024, 입력 `[1,36,5120]`, q/v rank4·alpha4·dropout0, AdamW lr1e-4·weight_decay0, 최대3 update를 고정한다. CPU generator로 x와 target을 순서대로 만들고 x만 BF16로 변환하며 target은 FP32다. 실제 입력 byte SHA256은 `4b7054fd697673b5093e2d6489d492beb058e69257426ef4970789d0c518b253`, target은 `b91b192314809e1a2a5dcaf885801e39f7124c3420bf09ec202837317aebe06c`다. 입력 shape와 BF16 dtype, target FP32 dtype를 hash와 함께 읽어야 한다. 코드 동결과 실제 실행 hash는 `reports/code-freeze.json` 및 `reports/runtime-contract.json`에 각각 보존돼 있다.

`code/component_runner.py`는 공식 WanSelfAttention을 구성하고 선택 tensor를 읽는다. 저장 F32 중 projection weight/bias만 BF16로 cast하고 norm_q/norm_k parameter는 F32로 보존한다. `code/lora_component.py`는 새 명시적 adapter wrapper이며 공식 모델 코드 자체의 기능이라고 부르지 않는다. runtime dtype 경계와 값 보존을 검사하는 runner, CPU helper, resource guard는 각각 `reports/code-freeze.json`의 SHA에 연결된다. 같은 FP32 저장 값과 BF16 cast 값을 비교해 기반 모델이 변했다고 오판하지 않으며, norm을 무심코 BF16으로 내리는 것도 동일 연산으로 간주하지 않는다.

## 6. 실제 Lab 자료는 별도의 과제

최초 제안은 편안한 앉기·고개 돌리기·걷기·자연스럽게 일어나기 등, 두 촬영 session에서5–10초 영상6–10개와 다른 시점 사진6–10장이다. 충분한 데이터라는 보장은 없다. 전신·발을 가능한 한 담고 큰 카메라 회전과 민감 배경을 줄이며, 강제로 직립하거나 춤추게 하지 않는다. 원 fps/해상도/PTS, 촬영자·개체·session·private training 허용 범위를 보존한다. session 단위 hold-out은 같은 Lab의 새 장면 평가이지 unseen identity 평가가 아니다. 이번에는 촬영 요청 전송·수집·학습을 실행하지 않는다. 기존 제3자 source의 권리는 계속 UNKNOWN이다.

## 이해 확인 질문

1. 첫 backward에서 A gradient가0이면 LoRA가 실패한 것인가?
2. frozen o projection을 no_grad로 감싸도 그 앞의 q/v adapter를 학습할 수 있는가?
3. synthetic MSE가3 update 동안 감소하면 실제 영상 FM 학습이 검증됐는가?

## 별도 해설

1. Bzero 초기화에서는 수식상 정상일 수 있다. B gradient와 update 후 A gradient, 실제 parameter delta를 함께 본다.
2. 필요한 graph를 차단할 수 있으므로 안전한 대체가 아니다. weight freeze와 연산 graph 보존을 구별한다.
3. 아니다. 수치 배선 검사일 뿐 sigma 경로·실제 target·조건·전체 모델과 데이터 목적은 검증하지 않았다.

정적 코드 품질도 실제 연산 성공과 분리한다. 종료 후 runner 범위 basedpyright에는20errors/135warnings가 남아 NOT_CLEAN이다. helper의19warnings와 별도이며, frozen 실행 코드·원래 진단을 보존했다. 실제 backward가 동작했다는 사실만으로 일반적인 타입 안전성이나 배포 준비 상태를 주장하지 않는다.

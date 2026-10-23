# B-008 — 외형 참조와 RGB 동작 조건이 만나는 곳

최종 상태: **Lab P/PROBE/S/D 기술 실행 PASS / 동작 전달 FAIL / 실제 개체 UNCERTAIN / 시간 품질 UNVERIFIED**. [계획](../experiments/B-008-lab-rgb-baseline/PLAN.md)은 실제 앉은 Lab 사진과 원본 f0~16을 사용한 한 번의 기준선이다. H의 공식 인간 영상 성공은 이번 개체·체형·안무 성공을 보장하지 않는다. 이번에는 가중치 theta를 학습하지 않고 조건 c를 바꾼다.

## 1. 직관과 변수

참조 사진 R은 “누구인가”, 원본 RGB 영상 D는 “어떻게 움직이는가”에 관한 정보를 제공하도록 기대한다. 그러나 RGB에는 자세뿐 아니라 얼굴·털·체형·배경도 들어 있고, 사진에는 외형뿐 아니라 앉은 자세·시점도 있다. 역할을 프롬프트로 지정했다고 이 정보들이 완전히 분리된 것은 아니다.

설명용 표현은 `c=E(R,D,M,p)`, `v_theta(z_sigma,sigma,c)`, `Y=Decode(z_final)`이다. M은 reference/driving instance mask, p는 고정 prompt, z는 생성할 영상 latent다. c는 하나의 단순 벡터가 아니라 여러 branch의 tensor·list·None과 설정을 묶은 표기다. 원본의 물리적 영상 시점 i/24초와 denoising sigma는 서로 다른 축이다.

## 2. 실제 코드의 조건 경로

고정 소스는 SCAIL `78fe19576bb06be96c2375e088574a262a300edb`다. [reference/CLIP/text 준비](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L200-L350)와 [driving encode·조건 구성](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L431-L511)을 연결해서 읽는다.

1. RGB reference는 VAE latent와 CLIP feature로 처리된다. instance mask도 별도 latent-grid 표현을 만든다.
2. driving RGB는 공식 코드에서 bilinear half-size 처리 후 VAE encode된다. 코드의 `pose_latents`라는 변수명은 이 경로가 관절 좌표만 담는다는 뜻이 아니다. 실제 입력은 RGB다.
3. driving mask도 half-size 처리 후28채널 표현으로 압축된다. RED는 이번 Lab의 instance 대응이며 일반적인 검은색/흰색 alpha 개념으로 대체하지 않는다. mask의 얇은 발·꼬리·반사 경계 불확실성은 남긴다.
4. [DiT forward](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803)는 reference와 noisy generated latent를 시간축으로 연결하여 patch embedding한다. reference mask embedding을 더하고, 별도 driving latent/mask embedding을 token축으로 연결한다. text와 CLIP는 context embedding 경로로 들어간다.

이는 참조와 driving에 서로 영향을 줄 수 있는 계산 경로가 있음을 보여준다. 어느 branch가 어떤 픽셀을 만들었는지는 이 소스만으로 증명되지 않는다. “누수”의 구체적 원인 판정에는 입력을 통제한 후속 비교가 필요하다.

## 3. shape를 코드에서 예측하고 실측과 구분하기

다음 표에서 noise/reference/driving/mask는 실제 Lab P의 **관측값**이다. final latent와 raw output도 실제 S/D에서 확인됐다. 공간 VAE stride8, 시간 압축 후 T5, patch(1,2,2)를 적용한다.

| 항목 | shape | 증거 범위 |
|---|---|---|
| generated noise | `[16,5,112,64]` FP32 | P 관측, batch 제외 C,T,H,W; S final도 같은 shape로 확인 |
| reference latent | `[16,1,112,64]` FP32 | P 관측, 생성 프레임이 아닌 참조 prefix |
| reference mask | `[28,6,112,64]` FP32 | P 관측, 참조1+generated5 grid |
| driving latent | `[16,5,56,32]` FP32 | P 관측, half-size RGB 조건 |
| driving mask | `[28,5,56,32]` FP32 | P 관측, driving과 같은 grid |
| raw output | `[3,17,896,512]` | D 관측, finite RGB output |

reference token은112×64/4=1792, generated는5×1792=8960, driving은5×56×32/4=2240으로 합계12992다. 이 예측은 H의 가로 shape를 reshape한 것이 아니라 세로 입력의 각 축에서 유도한 값이다. 면적이 같아 token 수가 같더라도 회전된 공간 좌표·내용·RoPE 의미가 동일하지는 않다. 실제 P text는 positive `[44,4096]` BF16, negative `[1,4096]` BF16이고 CLIP는 `[1,257,1280]` FP16이다.12992 token 계산은 이 shape에 대한 코드상 계산이며 아직 실제 DiT hook 관측은 아니다.

## 4. velocity와 최종 영상

시간 규약을 `z_sigma=(1-sigma)x+sigma*epsilon`으로 설명하면 velocity는 `epsilon-x`이며 sampling은 sigma가 줄어드는 방향이다. 실제 [UniPC flow prediction 변환](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L300-L327)은 이를 clean sample 추정과 solver에 연결한다. 교육용 Euler와 실제 UniPC predictor/corrector를 같은 구현으로 부르지 않는다.

[공식 CFG loop](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L375-L426)는 `v_cfg=v_null+5*(v_cond-v_null)`을 계산한다. arg_null에도 동일 reference/driving/mask/CLIP가 있고 text context가 다르다. null을 “모든 조건이 없는 모델”로 해석하지 않는다.40 step이면 두 branch의80 forward가 필요하며 이번 실제 완료 counter는80 forward·40 step으로 확인됐다.

최종 generated latent만 [VAE decode](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L544-L568)에 전달한다. wrapper가 scaling을 복원하므로 외부에서 중복 적용하지 않는다. reference prefix나 초기 noise가 final latent를 대신하지 않는다.

## 5. 체형과 동작 단계를 분리해서 읽기

morphology는 가슴·몸통 폭, 사지 길이·굵기, 얼굴·귀 비율이다. motion phase는 머리가 어느 방향으로 얼마나 진행해 회전하는지, 앞발이 오르고 내리는 단계와 시점이다. 묵직한 Lab에 원본의 가는 실루엣이나 모든 픽셀 위치를 그대로 요구하면 올바른 체형 변화도 실패로 오해할 수 있다. 반대로 직립 실루엣 하나만 맞으면 안무가 전달됐다고 판단하는 것도 부족하다.

앉은 참조 자세 고정, 원본의 가는 체형/귀/얼굴 복사, 참조/원본 배경 혼입은 **관측할 실패 유형**이다. 가능한 설명은 RGB와 참조의 결합 정보, 학습 분포, condition 간 충돌이지만 이번 출력 전에는 실제 실패나 원인으로 단정하지 않는다. 한 사례로 조건 분리 학습의 인과효과나 일반화 확률을 추정할 수 없다. 참조에 안 보이는 부위와 발 접촉은 불확실로 남긴다.

## 6. 24fps와 cache 유효성

source 시점은 `t_i=i/24`초다.17프레임/24fps 파일 길이는0.708333초, 첫/끝 sample 간격은0.666667초다.16fps로 저장하면 같은17장을1.0625초에 재생하므로 물리적 동작 속도가 바뀐다.24fps 저장은 source의 시간을 유지하는 일이며 모델의 native16fps prior를 다시 학습하는 것은 아니다. H 인간16fps와 Lab24fps의 차이를 동물 도메인 하나의 통제된 효과로 해석하지 않는다.

H의 사람 조건 캐시는 Lab에 사용할 수 없다. R/D/M/p, crop·resize, encoder weights, dtype·autocast가 달라지면 E의 출력 계약을 다시 확인해야 한다. device는 저장된 leaf별로 복원한다. CPU sigma와 generator state를 일괄 CUDA로 옮기지 않는다. 같은 seed라도 shape와 RNG 소비가 달라질 수 있어 H noise hash와 같아야 한다고 강제하지 않고, **Lab P→S의 실제 noise 값·state**를 확인한다. `eval()`과 `no_grad()`는 모드와 graph 기록을 각각 다루며 서로 대체하지 않는다. [PyTorch autograd modes](https://docs.pytorch.org/docs/2.14/notes/autograd.html#locally-disabling-gradient-computation).

## 7. 이번 관측과 반례의 자리

Lab P는118.06초에 완료했고4개 독립 전처리 tensor hash가 일치했다. 새 Lab cache는17,685,156 bytes, SHA256 `96164a2c54d38e86f006504824a85499f669eaca12f05ee3e6afe5a3858a0287`이다. 이후 S는80 forward·40 step을 완료했고 D raw/MP4를 확보했다. flatten된 noise 값 hash는 H와 같은 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`으로 관측됐다. 같은 seed와 element 수에서 나온 일치이며 H와 같도록 강제한 검사가 아니다. shape는 Lab `[16,5,112,64]`와 H `[16,5,64,112]`로 다르므로 hash 하나만으로 공간 tensor가 같다고 말하지 않는다. H cache/사람 자산은 재사용하지 않았다. H는 기술 경로의 근거이며 Lab 결과가 아니다. 품질 검토에서는 source/preprocess/reference/output의 f0,4,8,12,16과 전체17장을 같은 framing으로 검토하고, 개체·체형·동작 phase·경계·배경을 각각 기록한다. 정적 시트만 보았다면 시간 품질은 UNVERIFIED다. 생성 성공과 개체/안무 수용은 분리하며 통계적 성공률이나 임의 종합점수를 만들지 않는다.

### 실제 생성 완료와 품질의 구분

[실행 장부](../experiments/B-008-lab-rgb-baseline/RUN_LEDGER.json)의 guarded 시간은 P118.060초, PROBE6.063초, S1066.317초, D15.219초다. 각1회, 재시도0, 종료 PID0/inactive다. final latent는 finite FP32 `[16,5,112,64]`, readback exact이며 P→S noise exact다. final 값 hash `24f40d5fd79571fdecd969f5e5ba1227c55a096c9a8770e2022469c270fe1813`은 initial noise와 다르다. raw `[3,17,896,512]`와17프레임·24fps·0.708333초 MP4를 확인했다.

이는 새 Lab 입력으로 기술 경로가 완료됐다는 증거다. 실행 담당자는 실제 f0/4/8/12/16과 전체17프레임을 정적으로 검토했다. 결과는 아래와 같으며 개체·안무 수용과 기술 완료를 구분한다. 시간 품질은 UNVERIFIED다. 출력이 있다는 이유로 source RGB가 의도한 motion만 전달했다고 결론 내리지 않는다.

### 실제 정적 품질 관측

출력은 실제 참조의 검은 Lab 얼굴·귀와 넓은 앉은 가슴을 닮았고, 참조의 침대·커튼 배경이 강하게 남았다. 검은 Lab 견종 외형이 알아볼 만하다는 사실은 특정 반려견 identity 성공을 뜻하지 않아 **실제 개체는 UNCERTAIN**이다. 보이는 가슴·얼굴의 형태는 대체로 알아볼 수 있으나 가려진 뒷부분과 접촉은 UNCERTAIN이다.

전체17프레임에서 앉은 자세가 유지되고 앞발은 침대에 남았다. 원본의 뒷발 직립 자세·앞발 동작이 전달되지 않아 **motion transfer는 FAIL**이다. 머리·몸 위치의 작은 변화가 보여 동일 프레임 복제라고 주장하지 않는다. 참조 pose/background의 잔류는 실제 관측됐고, 원본 흰 강아지의 외형 복사는 뚜렷하지 않았다. 연속 재생을 직접 확인하지 않았으므로 temporal=UNVERIFIED다.

이 결과는 “참조의 외형을 남겼으니 조건 분리가 성공했다”는 해석의 반례다. 얼굴·가슴뿐 아니라 원치 않은 앉은 자세와 배경도 함께 남았다. 다만 이를 특정 attention branch나 학습 데이터의 유일 원인으로 단정할 수 없다. 이번 단일 입력으로 일반적 동물 motion 능력 부재와 cross-body identity transfer의 난점을 분리해 입증하지 못했다.

다음 제안은 **같은 원본 동물의 첫 프레임을 reference로 쓰는 RGB-driving 자기 재구성 진단 한 가지**다. 기본 동물 동작 재현과 다른 체형·개체로의 전달 난점을 구분할 단서를 얻는 목적이며, 아직 실행하지 않았다. 이 비교도 reference 정보가 달라지므로 모든 인과를 분리하는 증명이라고 부르지 않는다. 이번 실행 뒤 추가 생성·학습은 하지 않았다.

## 이해 확인 질문

1. `pose_latents`를 사용했는데도 원본 강아지의 얼굴이나 체형이 출력에 남을 수 있다는 가설은 어떤 실제 입력 경로에 근거하는가?
2. 두 출력에서 머리 중심의 픽셀 좌표가 다르면 항상 동작 전달 실패인가? 체형과 phase를 어떻게 분리할 것인가?
3. H와 같은 seed인데 Lab noise hash가 다르면 오류인가? 무엇을 비교해야 하는가?

## 해설 — 먼저 질문에 답한 뒤 읽기

1. 이 경로는 RGB를 줄여 VAE encode하므로 자세 이외 정보도 포함할 수 있다. 이는 가능성의 근거이지 실제 누수 원인의 증명은 아니다.
2. 가슴·머리 크기와 framing 변화로 좌표가 달라질 수 있다. 회전 방향·단계·앞발의 상대 이동을 확인하면서 체형도 별도 평가한다. 보이지 않는 관절을 지어내어 정답으로 쓰지 않는다.
3. shape·조건 및 RNG 소비가 다르면 동일 seed만으로 같은 tensor를 보장하지 않는다. Lab의 실제 P noise와 S 입력 값/hash/state, dtype/device 및 scheduler 계약을 대조해야 한다.

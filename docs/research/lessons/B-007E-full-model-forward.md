# B-007E — 파일 변환에서 실제 모델 forward로

[입력 감사](../experiments/B-007E-scail-forward/INPUT_AUDIT.md) · [계획](../experiments/B-007E-scail-forward/PLAN.md). 아래 shape와 호출 수는 고정 소스 기반 예상이며, 실제 forward trace가 도착하기 전에는 실측으로 쓰지 않는다.

## 1. 가중치 파일과 실행 모델

B-007D의 65.58GB FP32 파일은 tensor 값의 저장물이다. Module은 architecture와 parameter/buffer를 가진 실행 객체다. 보통 architecture 초기화 후 checkpoint load와 state_dict copy를 수행하면 초기 parameter와 checkpoint tensor가 동시에 존재할 수 있다. meta-init은 초기 실제 storage를 생략하고 assign은 storage 소유를 넘길 수 있지만, key/shape·buffer·dtype·device가 완성돼야 forward할 수 있다.

FP32→BF16은 원소당 bytes를 4→2로 줄이지만 유효 자릿수도 달라진다. 원본 변환본의 byte-identical parity는 BF16 실행 모델의 수치 동일성으로 이어지지 않는다. parameter 메모리, temporary cast, activation, T5/CLIP/VAE, file page cache는 분리해 측정한다. unified memory를 CPU/GPU 두 용량으로 합산하지 않는다.

## 2. 세 종류의 video token

H896W512 또는 H512W896은 같은 면적이다. 생성 대상17f의 VAE latent 예상은 C16,T5,H/8,W/8이다. 한 장 reference는 T1이며 공간 해상도는 동일하다. RGB driver는 pipeline에서 공간을 절반으로 줄여 encode하므로 예상 공간은 H/16,W/16이다. patch(1,2,2)라면 생성 token은 `5×(H/16)×(W/16)=8960`, reference는 `1×(H/16)×(W/16)=1792`, driver는 `5×(H/32)×(W/32)=2240`이다. 총12992 token 예상이다.

[고정 pipeline](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L438)의 latent 준비와 [model](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py)의 token 결합을 실제 trace와 대조한다. mask는 개체 대응·배경 가시성 조건이다. mask color ID가 하나라고 video RGB의 pose나 identity가 자동 보장되는 것은 아니다.

40 heads, head dimension128이면 self-attention Q/K/V 예상 shape는 `[1,12992,40,128]`이다. naive attention score는 head당 N² 요소를 가진다. FlashAttention은 IO와 중간 score materialization을 줄이지만 모델 parameter와 다른 activation을 없애지 않는다. 작은 kernel smoke 성공과 실제12992-token forward 성공은 다르다. wrapper에서 본 Q/K dtype와 kernel 직전 cast dtype도 구분한다.

## 3. Noise time과 물리적 video time

Flow path를 `zσ=(1−σ)x+σε`로 쓰면 `dzσ/dσ=ε−x`다. sampling은 높은σ에서0으로 간다. 고정 UniPC는 단순 Euler가 아니며 이전 model output을 재사용한다. shift3은 schedule 재분배이며 물리적 fps 변경이 아니다.

CFG5에서는 `v=v_uncond+5(v_cond−v_uncond)`를 계산한다. [고정 두 forward 분기](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L391)에 따라 single17f segment40steps는 보통80 DiT 호출 예상이다. 실제 완료된 forward 수와 실패 위치는 hook trace로 확인한다.

Lab의 sample time은 `t_i=i/24`, 공식은 `i/16`이다. 출력17장의 파일 길이는 각각17/24와17/16초이고 첫~마지막 sample 간격은16/24와16/16초다. writer fps24는 입력 시간축을 보존하지만 model의16fps 설정·학습 motion prior가24fps에서도 올바른 동작을 재현한다는 증거가 아니다. loop 끝→처음 점프와 내부 불연속도 구분한다.

## 4. 무엇을 성공으로 부를 것인가

- LOAD_PASS: 실제 weights와 architecture 적재, key/buffer/dtype 계약 및 자원 확인.
- FIRST_FORWARD_PASS: 실제 조건과 token으로 한 DiT forward 완료.
- VIDEO_OUTPUT_PASS: sampler·VAE decode·17장 인코딩 완료.
- 개체·동작 수용: 실제 reference/source와 비교한 별도 시각 판단.

앞 단계만으로 뒤 단계를 인정하지 않는다. 연속 재생을 직접 확인하지 못하면 temporal=UNVERIFIED다. 현재 새 생성/forward 실측은 대기 중이며 LoRA 업데이트는0이다.

[질문](../experiments/B-007E-scail-forward/QUESTIONS_KO.md) · [해설](../experiments/B-007E-scail-forward/ANSWERS_KO.md)

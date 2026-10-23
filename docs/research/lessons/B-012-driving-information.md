# B-012 — driving의 시간 정보는 무엇을 더하는가

현재 선택 구간과 실행 결과는 확정 근거를 기다리는 상태다. 아래 shape는 기존 동일 규격 경로에서 예상하는 값이며 B-012 실측으로 대신하지 않는다. [계획](../experiments/B-012-clear-motion-driving-control/PLAN.md)은 같은 모델·reference·text·noise에서 MOV와 STILL을 한 번씩 비교한다. B-011의 자기 재현 1회와 B-010의 생성 0회 기록은 보존한다.

## 1. 정적 출력과 정적인 입력

STATIC COPY는 source 첫 프레임을 반복한 비생성 출력이다. STILL은 첫 RGB와 첫 mask를 17번 반복해 **생성 모델에 입력**한 결과다. MOV는 선택한 실제 17장 RGB와 그에 대응하는 mask를 입력한다. 따라서 STILL이 움직인다고 실험 실패는 아니다. 같은 reference·text와 학습된 prior만으로도 영상 변화가 생길 수 있다.

B-011은 STATIC COPY 대비 source 화면 변화의 대응 근거를 얻었지만, 정적 driving을 모델에 넣지는 않았다. B-012는 이 빈 대조를 채운다. MOV가 더 많이 움직이는가보다, source에서 사전 기록한 부위 배치·방향·이벤트 순서에 더 가까운가를 묻는다.

## 2. 수식에서 개입을 정확히 정의하기

\(c=(c_{ref},c_{drive},c_{mask},c_{text})\)라 하자. 고정 가중치의 조건부 속도장은 \(v_\theta(z_\tau,\tau,c)\)이며 sampler가 초기 noise \(z_1=\epsilon\)에서 최종 latent와 영상을 만든다. 조건을 바꾸는 추론 실험이지 학습 loss나 가중치를 바꾸는 실험이 아니다.

\[
c^{MOV}=(R,E(D_{0:16}),M_{0:16},T),\qquad
c^{STILL}=(R,E(D_0,D_0,\ldots,D_0),M_0^{repeat},T).
\]

여기서 \(E\)는 실제 driving RGB 전처리와 VAE이고 \(M\)은 semantic mask의 실제 압축 표현이다. 식은 두 표현을 한 묶음으로 개입한다는 요약이며 원시 RGB mask가 그대로 DiT에 들어간다는 뜻은 아니다. RGB만의 독립 효과나 driving branch 제거가 아니다.

같은 \(\epsilon\), generator state, scheduler, reference/text를 사용하면 noise 선택이라는 혼동을 줄인다. 그러나 한 seed의 paired 결과는 표본 집단의 평균 효과나 일반화를 추정하지 못한다. MOV/STILL이 다르다는 것과 MOV가 **유용한** 목표 동작 정보를 더했다는 것은 다른 결론이다. 후자는 source 이벤트와의 대응이 필요하다.

## 3. 실제 코드에서 RGB가 시간 조건으로 바뀌는 위치

고정 버전은 SCAIL-2 `78fe19576bb06be96c2375e088574a262a300edb`다. [scail.py L435–453](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L435-L453)은 driving RGB를 bilinear로 공간 절반 크기로 줄여 VAE encode하고, driving mask도 절반 크기로 줄여 별도 helper로 압축한다. `pose_latents`라는 이름은 여기서 읽는 데이터가 skeleton 좌표라는 뜻이 아니다. 이번 경로는 RGB driving이다.

[vae.py L515–542](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L515-L542)의 encode는 첫 1장, 이후 4장씩 처리하며 convolution feature cache를 유지한다. 17장에는 \(1+(17-1)/4=5\)개의 latent 시점이 생긴다. 마지막 분포 출력에서 `mu`를 택해 고정 scaling을 적용한다. 이것은 현재 inference 구현을 읽은 사실이며 학습 데이터의 시간 분포나 동물 동작 학습 능력을 검증한 것은 아니다.

그래서 \(E(D_0^{repeat})\)를 \(E(D)\)의 첫 latent slice 반복으로 대체할 수 없다. 시간 문맥·첫 프레임 경계 처리·비선형 encoder의 결과가 다를 수 있다. STILL도 17프레임 RGB 비디오를 독립적으로 encode해야 한다. 이미지가 반복돼도 latent 시간 slice가 모두 같은 값이어야 한다는 검사도 만들지 않는다.

mask helper는 7개 semantic 색을 추출하고 공간 압축 및 4시점 channel packing으로 28채널을 만든다. 따라서 mask도 실제 반복 RGB mask에서 계산한다. mask의 시간 변화만 남기면 STILL에도 운동 단서가 들어간다. [scail_utils.py의 실제 helper](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106-L141)

## 4. 예상 tensor와 4개 변경/12개 보존

고정 17장·H896/W512 입력의 예상 shape다. 아직 B-012의 실측은 아니다.

| 항목 | 예상 shape/dtype | MOV↔STILL 계약 |
|---|---|---|
| noise | `[16,5,112,64]` FP32 | actual bytes·shape 동일 |
| reference latent | `[16,1,112,64]` FP32 | 동일 |
| reference mask | `[28,6,112,64]` FP32 | 동일 |
| driving latent | `[16,5,56,32]` FP32 | 변경 기대 |
| driving mask | `[28,5,56,32]` FP32 | 변경 기대 |
| CLIP | `[1,257,1280]` FP16 | 동일 |
| positive text | `[L,4096]` BF16 | 같은 문장·L·값; L은 실행 확인 |
| negative text | `[1,4096]` BF16 | empty negative 동일 |

[조건 dictionary L480–508](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L480-L508)에서 두 CFG branch 모두 같은 visual 조건을 사용한다. 현재 cache의 16leaf 중 두 branch의 `pose_latents`와 `driving_masks`, 합계 4leaf만 변경 기대다. 이들은 **두 의미 조건이 branch마다 연결된 것**이지 독립적인 4개 실험 요인이 아니다. 나머지 12leaf(reference·CLIP·text·noise/RNG/schedule)를 실제로 비교한다. 같은 seed라는 문구만으로 noise 동일성을 대신하지 않는다.

동일 encoder 입력의 허용 오차와 exact 계약은 결과 전에 고정한다. 변경 기대 4개가 실제로 같으면 개입이 latent에서 성립했는지부터 살핀다. 모델이 움직임을 무시했다는 결론을 먼저 내리지 않는다. 값이 달라진 것만으로 semantic 동작 정보가 충분히 보존됐다는 결론도 내리지 않는다.

## 5. CFG와 두 종류의 시간

[실제 CFG](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L389-L410)는 \(v_{CFG}=v_u+5(v_c-v_u)\)다. \(u\)는 empty text 쪽이며 visual 조건은 유지된다. unconditional을 무조건·정적·driving-off와 동의어로 쓰면 안 된다.

noise time \(\tau\)는 latent의 denoising 수준이고, physical video time은 frame \(k\)의 \(t_k=k/24\)초다. 40step은 영상 40프레임이 아니며 CFG에서는 조건당 80forward를 계획한다. 17프레임 파일 길이 17/24초와 첫·끝 시점 차이 16/24초도 다르다. 24fps를 임의로 바꾸거나 frame skip·보간으로 동작을 키우지 않는다.

[model_scail2.py L741–803](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803)에서는 reference+generated patch와 driving patch를 결합하고 text/CLIP 문맥을 사용한다. attention이 정보를 섞을 수 있다는 코드 구조와, 이번 개체의 정확한 부위 운동을 실제로 재현했다는 관측은 별개다. attention map 자체도 이 실험의 인과 증명을 대신하지 않는다.

## 6. 아직 확인하지 않은 것

선택 구간·사전 이벤트·실제 condition 비교·MOV/STILL 생성·품질은 **NOT_RUN/근거 대기**다. 예측 shape와 이전 B-011 결과를 새 실측으로 보고하지 않는다. 실제 출력에서는 같은 17장 전체를 같은 canvas와 24fps로 비교하고 출력별 warp/scale/lag 탐색을 하지 않는다. 불명확한 발끝·가림은 UNKNOWN/UNCERTAIN과 coverage로 남긴다.

MOV가 source 이벤트에 더 가까우면 이 입력에서 **동적 RGB+mask pair의 유용한 추가 정보**라는 탐색적 근거다. 두 결과가 비슷하더라도 모든 조건에서 driving을 무시한다는 결론은 아니다. 두 결과가 다르기만 하면 목표 동작 제어 성공도 아니다. 17장과 여러 표면점을 독립된 반복 실험으로 세지 않는다. Lab cross-identity·접촉 물리·일반화는 이번 평가가 아니다. 연속 재생을 직접 관찰하지 못하면 temporal=UNVERIFIED다.

## 이해 확인 질문

1. STILL RGB는 f0 반복인데 mask는 MOV 그대로라면 무엇이 달라지는가?
2. 왜 STILL latent를 MOV latent 첫 slice 반복으로 만들지 않는가?
3. MOV가 STILL보다 더 크게 움직이면 무엇을 확인했고 무엇이 더 필요한가?

## 별도 해설

1. mask로 시간 정보가 남는다. 정적 driving pair라는 계약이 깨져 RGB+mask 공동 시간 정보의 효과를 분리하기 어렵다.
2. 실제 VAE는 첫 프레임 경계와 이후 시간 cache를 사용하는 비선형 encoder다. 반복 영상의 encode와 latent의 반복은 동등하다고 보장되지 않는다.
3. 출력 변화량의 차이를 본 것이다. 사전 source 이벤트의 방향·순서·시점에 더 가까운지, 구조가 보존되는지 확인해야 유용한 제어라고 해석할 수 있다. 한 pair로 일반화나 통계적 유의성을 주장하지 않는다.

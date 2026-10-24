# B-024 — semantic mask와 실제 RGB 배경 분리

상태: 고정 공식 코드, 실제 REF/cache/sampler/D 기록과 실행 담당자의 전체17프레임·local0/8/16 정적 시각 검토를 연결한 설명이다. 40step·80forward와 decode가 완료됐다. B-023보다 장면·전신 자세의 정적 개선이 관측됐지만 reference 사용과 cross-ID 전이는 식별되지 않았다. 과거 B-023의 기술 PASS와 원본 보존 과제 FAIL은 그대로 보존한다.

## 1. 직관: “배경을 쓰지 말라”와 “배경 픽셀을 전달하지 않는다”

BLACK semantic mask는 모델이 해석하는 조건이다. 원래 침실 RGB를 지우는 연산이 아니므로 사진의 VAE·CLIP 특징에는 침실과 letterbox 정보가 남을 수 있다. B-024는 같은 Lab의 픽셀·위치·크기·착석 자세·semantic mask를 보존하고 비객체 RGB만 회색128로 바꾼다. 배경과 padding이 함께 바뀌므로 침실만의 단독 효과로 해석하지 않는다.

세 연산은 다르다.

| 종류 | 개입 위치 | 실제 의미 | B-024 |
|---|---|---|---|
| semantic mask | learned mask embedding | 색으로 개체 대응과 배경 가시성 지시 | B-023 그대로 |
| RGB gating | encoder 앞 입력 픽셀 | support 밖 실제 RGB를 상수로 대체 | 이번 개입 |
| attention mask | attention logit/연결 | 특정 query-key 접근을 제한 | 사용하지 않음 |

고정 semantic mask가 있는 것과 attention의 특정 항에 $-\infty$를 더하는 것은 동일하지 않다. 설명용 attention은 $A=\mathrm{softmax}(QK^\top/\sqrt d+B)$이고, hard attention mask라면 금지 연결의 $B_{ij}=-\infty$다. SCAIL 색상 mask는 이 hard mask가 아니라 `patch_embedding_mask`의 결과를 영상 feature에 더하는 경로다. 이 설명을 위해 실제 dense attention map을 만들거나 FlashAttention을 바꾸지 않는다.

## 2. 수식과 가정

$R\in\{0,\ldots,255\}^{3\times512\times896}$는 실제 전처리 reference, $M\in\{0,1\}^{512\times896}$는 같은 좌표의 기존 RED support다. channel broadcasting을 생략하면

$$
R_{fg}=M\odot R+(1-M)\odot128.
$$

따라서 $M[p]=1$인 위치에서 $R_{fg}[p]=R[p]$가 정확해야 한다. support 면적·bbox·위치·크기·자세는 바뀌지 않는다. 이것은 grayscale 변환이나 새로운 segmentation이 아니다. mask 밖의 미포함 털은 기존 support의 한계이며 새로 그려 복원하지 않는다.

조건을

$$
C_{ref}(R,M)=\big(E_{VAE}(N(R)),E_{CLIP}(N(R)),E_{mask}(M)\big)
$$

로 쓰자. $N(r)=2r/255-1$은 공식 입력의 정규화이며 회색128은 $1/255\approx0.00392157$이다. 회색128을 정확한 normalized zero나 no-reference로 부르면 안 된다. CLIP wrapper는 이 입력을 다시 [0,1]로 옮기고 CLIP 전용 normalization을 적용한다.

B-024에서는 $E_{VAE}$와 $E_{CLIP}$를 모두 새 $R_{fg}$에서 계산한다. 원래 latent에 작은 mask를 곱하는 것은 $E_{VAE}(R_{fg})$와 일반적으로 다르다. 원래 CLIP만 그대로 쓰면 배경 정보의 다른 경로를 남기며 이번 계획의 공동 개입과도 달라진다.

## 3. 픽셀 보존은 feature 보존을 뜻하지 않는다

encoder 위치 $i$의 출력을 $E(R)_i$라 하면 입력 밖의 변화에 대한 국소 근사는

$$
\Delta E_i\approx\sum_{j:M[j]=0}\frac{\partial E_i}{\partial R_j}\Delta R_j.
$$

$M[i]=1$이어도 위 합은0일 필요가 없다. VAE의 convolution receptive field와 attention/context, CLIP의 영상 token 문맥 때문에 피사체 안쪽 특징도 배경 변경의 영향을 받을 수 있다. 따라서 이번 검사는 foreground RGB exact equality를 요구하지만 foreground latent equality를 요구하지 않는다. 이 식은 실제 Jacobian을 측정했다는 뜻이 아니라 왜 두 검사가 다른지 설명하는 근사다.

배경 제거는 자세 제거가 아니다. Lab의 몸통·발 배치가 같은 픽셀로 남아 있으므로 착석 정보는 계속 존재한다. shape·귀·털 등 identity와 pose를 별도 representation으로 분해한 것도 아니다. 회색이 출력에 복사되거나 임의 배경이 생성되는 위험도 있다.

## 4. 실제 pinned 코드와 tensor 연결

SCAIL-2 revision `78fe19576bb06be96c2375e088574a262a300edb`를 읽었다.

- [`wan/scail.py::generate` L220–230](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L220): reference RGB와 semantic mask를 각각 [-1,1]로 입력한다. RGB에 mask를 곱하지 않는다.
- [동일 함수 L286](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L286): 전체 reference RGB를 `[3,1,H,W]`로 VAE encode한다. B-020에서 이어진 실제 shape는 `[16,1,64,112]`다.
- [동일 함수 L335–338](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L335): 같은 `img`를 `clip.visual([img[:,None,:,:]])`에 전달한다.
- [`CLIPModel.visual` L511–525](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/clip.py#L511): 전체 canvas를 model image_size 정사각형으로 bicubic/align_corners=False resize하고 CLIP normalization, `use_31_block=True` visual forward를 실행한다. 기존 실제 output은 `[1,257,1280]`이다. 별도의 자동 foreground crop이라고 가정하지 않는다.
- [`model_scail2.py::forward` L751–763](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L751): RGB reference와 generated latent의 embedding에 semantic embedding을 더하고 driving embedding을 붙인다.
- [같은 파일 L873–900](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L873): head 뒤 unpatchify는 `additional_ref_length+ref_length` offset부터 generated 길이만 반환한다. 이것은 공식 소스의 사실이며 실제 이번 runtime의 전체 계보 검증과 동일하지 않다.

| 내용 | 기존 실제 shape | 기대 변경 |
|---|---|---|
| reference RGB | [3,512,896] | support 밖만 |
| ref_latents 양 CFG | 각각[16,1,64,112] | 변경 |
| clip_fea 양 CFG | 각각[1,257,1280] | 변경 |
| ref_masks 양 CFG | 각각[28,6,64,112] | 보존 |
| pose_latents 양 CFG | 각각[16,5,32,56] | 보존 |
| driving_masks 양 CFG | 각각[28,5,32,56] | 보존 |
| noise | [16,5,64,112] | 보존 |
| text/RNG/timesteps/sigmas | B-023 그대로 | 보존 |

기대 계약은 tensor 4leaf 변경/12leaf 보존이다. leaf 개수만으로 통과시키지 않고 의미별 경로·hash·dtype·shape·parent를 확인해야 한다. replacement=true, semantic BLACK/RED와 WHITE/RED, 전체 T/H/W RoPE, CFG5·UniPC40·shift3·seed·실제 noise는 유지한다. 양 CFG branch가 같은 시각 조건을 공유하므로 negative text가 비어 있어도 reference와 driving은 제거되지 않는다.

기존 ref/driver latent의 VAE decode는 각각 참조 사진과 절반 공간 해상도의 driving 표현을 확인하는 손실 복원이다. 원본 RGB와 byte equality를 요구하지 않으며, 이것을 신규 diffusion 생성으로 세지 않는다. 반대로 shape가 맞는다는 것만으로 사진/영상 의미까지 확인됐다고 하지 않는다.

## 5. 무엇을 식별할 수 있는가

새 조건부 속도장을 $v_\theta(z_\sigma,\sigma;C_{ref}(R_{fg},M),C_{drv},c)$로 쓰면, 같은 initial noise에서 조건 변경 때문에 생성 경로가 달라질 수 있다. 이번 변화는 reference VAE와 CLIP에 동시에 들어가므로 어느 encoder가 변화의 원인인지 분리할 수 없다. background와 letterbox도 함께 바뀐다. 개체 픽셀의 원래 착석과 위치·크기는 남는다.

판정은 참조 침실 감소만이 아니라 원본 타일방·구도 보존, 사족기립·고개 순서, 얼굴/귀/목/사지, 실제 개체·체형을 나누어 본다. 침실이 회색이나 다른 방으로 바뀌는 것은 source preservation 성공이 아니다. source와 reference가 같은 실제 Lab이므로 잘된 결과도 source copy로 설명될 수 있으며 cross-ID나 reference necessity는 미검증이다. B-002 VACE 실험은 다른 모델의 역사적 결과이고 이번 대조군은 B-023 raw다.

## 6. 실제 결과와 해석

- 기존 RED support 37,209픽셀의 RGB·support·bbox를 보존하고 밖만128로 만든 입력 검사는 PASS다. 사진의 자세나 canvas 크기는 바꾸지 않았다.
- 원래 reference의 VAE `[16,1,64,112]` FP32 및 CLIP `[1,257,1280]` FP16 재인코딩은 기존 cache와 max_abs=0, RMS=0이었다. 이번 관측값이며 모든 GPU 재실행의 byte determinism을 보장하는 조건으로 일반화하지 않는다.
- 독립 cache payload 확인에서 t2/t3/t8/t9만 변경되고 나머지12leaf 및 device/scalar 구조는 동일했다. 원래 reference 복원은 착석 Lab+침실, driving 복원은 사족 Lab+타일방+후기 왼쪽 고개돌림이었다. driving 복원은448×256이며 fullresolution 원본이 아니다. 제한 검사에서 구체적인 ref/driver 바꿔치기·중복정규화·generated offset 결함은 찾지 못했다. 모든 잠재 결함의 배제 증명은 아니다.
- 실제 sampler40step/80forward와 final latent 저장 및 D decode가 완료됐다. 새 encoder 조건이 반영된 생성과 출력 파일 확보는 기술적 성과이며 시각 수용과 구분한다.

실행 담당자는 새 전체17프레임과 local0/8/16 비교를 직접 정적으로 보았다. B-023의 참조 침실과 중앙 세로 구획은 사라졌고, 사족으로 선 Lab와 source의 타일·러그·로프·의자·창 구도가 강하게 대응했다. 후반 머리는 화면 왼쪽으로 돌며 B-023에서 보였던 중앙 경계의 잘린 번짐 얼굴은 관찰되지 않았다. 이는 장면과 전신 자세, 대략적인 고개 방향의 정적 개선 근거다. 정밀 관절 타이밍이나 사람의 native속도 연속 시청을 검증한 것은 아니므로 temporal=UNVERIFIED를 유지한다.

출력이 source와 매우 비슷하므로 파일 대체 여부와 모델의 source-copy 경향을 구분해야 한다. `comparison-raw-provenance.json`은 실제 `raw_output.pt`의 SHA `e33ac003e663f3e2a32c7740f116d4d0dfd6259eff379cc30906e9b6d2562f3b`, shape `[3,17,512,896]`에서 양자화한 값과17장 export가 모두 정확히 일치함을 확인했다. source 원본 픽셀과는 모든 프레임이 다르며 frame별 RGB 절대오차 평균은 약10.94–15.16/255였다. 이는 source 파일을 그대로 넣었다는 오류를 배제하는 자료이고 지각 품질 점수나 reference 사용 증거가 아니다. 모델이 driving을 중심으로 source와 유사한 영상을 재구성하는 설명은 여전히 가능하다.

따라서 이번 결론은 **비객체 RGB 중립화 뒤 동일 개체 사례에서 장면·자세가 개선됐다**는 것이다. VAE와 CLIP를 동시에 바꿨으므로 encoder별 원인, 배경과 padding 각각의 원인, pose/identity 분리는 식별되지 않는다. source와 reference가 같은 실제 Lab이므로 잘 맞는 개체가 참조에서 왔는지 driving에서 왔는지도 이 비교만으로 알 수 없다. 새 모델 방법·일반화·cross-ID 성공으로 보고하지 않는다.

다음 연구 가설 하나는 **동일한 source와 실행 조건에서 명확히 다른 허용된 개체의 reference를 사용해도 원본 장면·동작을 유지하면서 그 reference 외형을 반영하는가**이다. 제한된 controlled cross-ID replacement 한 건으로 실제 reference 사용과 source-copy 설명을 구분할 수 있도록 계획한다. 이는 제안이며 이번 실행에 추가 생성·자료 수집·색/seed 탐색을 넣지 않았다.

## 이해 확인 질문

1. RED support 안 RGB가 완전히 같다면 reference latent의 그 영역도 같아야 하는가?
2. BLACK semantic mask와 회색 RGB, attention mask는 왜 서로 대체할 수 없는가?
3. 침실이 사라졌지만 Lab이 여전히 앉아 있고 새 방이 생겼다면 무엇을 확인했고 무엇을 확인하지 못했는가?

## 별도 해설

1. 아니다. encoder가 주변/전체 문맥을 이용하므로 support 밖 RGB가 안쪽 특징을 바꿀 수 있다. 픽셀 불변과 feature 불변은 다른 계약이다.
2. semantic mask는 학습된 embedding, RGB 중립화는 실제 encoder 입력 수정, attention mask는 query-key 연결 제한이다. 회색도 encoder에 실제 입력되며 branch-off가 아니다.
3. 참조 배경 의존의 감소 가능성만 부분적으로 관측한 것이다. source 장면 보존·자세 전이·정체성 분리는 성공하지 않았고 VAE/CLIP 중 어느 경로의 효과인지도 분해하지 못한다.

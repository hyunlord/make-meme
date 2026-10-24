# B-023 — FM 오차와 편집 목표, semantic mask와 픽셀 보존

이 문서는 공식 source, B-020 cache metadata 및 B-023 실제 실행 기록에 근거한다. cache 파생, 40step·80forward, 유한 raw decode와 MP4 저장은 PASS다. 전체17프레임 시트와 local0/8/16의 정적 시각 검토에서는 목표 품질 개선이 입증되지 않았다. 실행 성공과 품질 판정을 분리한다. [공식 코드·조건 감사](../experiments/B-023-task-aligned-replacement/OFFICIAL_CONTRACT_AUDIT.md)와 [입력 계약](../experiments/B-023-task-aligned-replacement/INPUT_CONTRACT.md)을 함께 읽는다.

## 1. 과제를 바꾸면 같은 사진도 다른 조건이 된다

직관: 참조 사진에서 어떤 개체를 가져올지와 어느 영상 장면을 유지할지는 다른 질문이다. reference RGB를 그대로 두고 semantic 배경 mask와 mode를 바꾸면 모델에게 주는 과제 설명이 달라진다. 사진의 방을 검은 RGB로 지우는 작업과도 다르다.

수식의 변수: $V\in\mathbb R^{3\times17\times512\times896}$는 원본 RGB, $R\in\mathbb R^{3\times512\times896}$은 seated Lab 사진, $M_V,M_R$는 색상 semantic mask, $c$는 text, $m$은 mode다. 생성 분포를

$$
p_\theta(Y\mid V,R,M_V,M_R,c,m)
$$

로 나타낸다. 이는 각 조건이 독립적으로 제어된다는 보장이 아니다. B-023은 $M_R$의 배경과 $m$을 함께 바꾼다. 따라서 모드+마스크의 과제 비교이며 mask 하나의 순수 인과효과로 분해할 수 없다.

실제 코드: `wan/scail.py::generate`에서 RGB VAE 경로와 semantic helper 경로는 분리된다. `model_scail2.py::forward`는 reference+generated의 patch embedding에 mask embedding을 더하고 driving token을 연결한다. BLACK은 7색 채널 모두0, WHITE는 white채널이 켜짐, RED는 개체 대응이다. mask는 학습된 조건이므로 BLACK에 해당하는 RGB 정보가 모델에서 완전히 사라진다는 뜻은 아니다. reference RGB latent와 CLIP에는 배경·착석 정보가 그대로 남는다.

실제 shape: B-020 metadata의 ref `[16,1,64,112]`, driving `[16,5,32,56]`, noise `[16,5,64,112]`, ref mask `[28,6,64,112]`, driver mask `[28,5,32,56]`를 사용한다. H/W의 순서는 W896/H512와 반대 표기인 tensor `[H,W]`다. 세로형 이전 밈 실험의 `[112,64]`와 혼동하면 안 된다.

한계: 기존 WHITE/WHITE+animation이 공식 전처리 사례와 다르다는 사실만으로 이전 품질 실패의 원인을 확정하지 못한다. 이번 한 번의 task-aligned output이 실제 판정 대상이다.

## 2. FM target을 잘 맞추는 것과 편집 목표를 만족하는 것은 다르다

직관: B-022는 정해진 noise/sigma/조건에서 속도 예측을 더 잘 맞추는 학습이었다. 실제 출력은 여러 sampler 상태를 지나고, 장면 보존·자세·정체성을 함께 만족해야 한다. 고정 tuple 오차 감소가 그 모두를 자동 해결하지 않는다.

실제 B-020 실행 코드 [`mix_velocity`와 `velocity_mse`](https://github.com/hyunlord/make-meme/blob/docs/b-research-20261022/docs/research/experiments/B-020-real-fm-tail-overfit/code/fm_contract.py#L61)는 아래 혼합·target과 원소 평균 MSE를 구현한다(L61–81). 이 링크는 연구 구현이며 upstream 전체 학습 loss와 동일하다는 주장으로 확대하지 않는다. 공식 모델 조건 경로와의 연결은 [고정 SCAIL `forward`](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L651)를 함께 확인한다.

설명에 쓰는 data→noise 규약은

$$
z_\sigma=(1-\sigma)z_Y+\sigma\epsilon,\qquad
v^*=\epsilon-z_Y,\qquad
\mathcal L_\mathrm{FM}=\mathbb E\|v_\theta(z_\sigma,\sigma,C)-v^*\|^2.
$$

$z_Y$는 VAE target latent, $\epsilon$는 Gaussian noise, $\sigma$는 noise 시간이며 실제 영상 프레임 시간과 다르다. $\sigma:1\to0$ 방향으로 sampler가 복원한다. 실제 scheduler의 UniPC weighting·다중 step 계산을 단일 Euler식과 동일하다고 주장하지 않는다. 교육용 Euler 근사는 $z_{k+1}=z_k+(\sigma_{k+1}-\sigma_k)v_\theta(z_k,\sigma_k,C)$다.

B-020/022의 고정 3tuple 경험위험 $\widehat L=\frac13\sum_jL_j$은 전체 noise/시간/조건 분포의 기대손실과 다르다. 마지막 block 특징은 그 tuple의 실제 noised input·sigma·조건에서 나온 값이므로 다른 noise에 재사용할 수 없다. 이번 B-023은 그 adapter를 쓰지 않으며 업데이트0이다.

편집 목적은 별도의 제약이다. 예를 들어 motion timing, 개체/체형, 보호 영역 보존, 시간 안정성을 각각 $Q_m,Q_i,Q_b,Q_t$로 두면 원하는 것은 이 조건들이 함께 수용되는 출력이다. 이 기호들은 이번에 계측한 scalar metric이 아니라 평가 항목이다. 임의 합산 score나 통계적 유의성을 만들지 않는다. source 복사 $Y=V$는 배경·동작 보존을 쉽게 만족하므로 실제 cross-ID reference 사용의 증거가 되지 않는다.

실제 관측: B-022 고정 tuple loss 감소와 품질 개선 미입증은 이전 RESULTS로 보존한다. B-023은 실제 추론·디코딩을 완료했다. 정적 시각 비교에서는 전신 자세와 원본 장면 보존에 실패했고 목표 품질 개선은 미입증이다. 새 결과가 좋아도 같은 Lab의 reference와 source를 사용하므로 실제 개체 교체 일반화는 미입증이다.

## 3. CFG의 negative branch에도 시각 조건이 남는다

두 branch는 positive/negative text가 다르고 같은 reference, driving, mask를 공유한다.

$$
v_{\rm CFG}=v_\theta(z,\sigma,C_{\rm visual},c_-)
+w\{v_\theta(z,\sigma,C_{\rm visual},c_+)-v_\theta(z,\sigma,C_{\rm visual},c_-)\},\quad w=5.
$$

empty negative는 text가 비어 있다는 뜻이며 reference/driver 제거가 아니다. B-023은 양쪽 branch ref mask와 replace flag를 같이 바꾼다. `reports/cache-derivation.json`의 실제 PASS는 16leaf 중 두 branch의 ref_masks(t4/t10)만 변경, 나머지14leaf 동일을 기록한다. 두 replace_flag scalar만 false→true이며 RNG·noise·scheduler도 보존됐다. RED 37,209픽셀은 그대로이고 WHITE 421,543픽셀만 BLACK으로 바뀌었다. old helper prefix exact, parent cache unchanged도 true다. P 재인코딩은0회이며 새 prefix shape는 `[28,1,64,112]`다. 이는 입력 계약 PASS이고 영상 품질 판정이 아니다.

코드 연결: `wan/scail.py`의 `arg_c/arg_null`(L479–505), `model_scail2.py` mask embedding(L751–763). mask는 VAE가 아니라 helper에서7색×4시간→28채널로 패킹된다. reference1frame은4회 반복, driving17frame은5latent time으로 압축된다. area interpolation으로 경계 coverage가 실수값이 될 수 있으므로 latent mask를 binary라고 부르지 않는다.

## 4. replacement mode는 H120 하나가 아니다

직관: reference와 driving과 생성 token을 어디에 놓는지는 모델의 관계 해석에 영향을 준다. 내용 tensor가 같아도 위치 조건은 달라진다.

RoPE의 한 축을 단순화하면 $q_p=R(p)q$, $k_r=R(r)k$이고 내적은 $q^\top R(r-p)k$다. 실제 모델은 head차원을 T/H/W 회전으로 분할한다. reference의 위치를 바꾸면 다른 stream과의 상대 위치가 바뀐다. 픽셀을 실제로120px 이동하는 연산은 아니다.

추가 reference가 없을 때 공식 animation→replacement offsets:

| stream | animation T/H/W | replacement T/H/W |
|---|---|---|
| reference | 0/0/0 | 0/120/0 |
| generated | 1/0/0 | 0/0/0 |
| driving | 1/0/120 | 0/0/120 |

`model_scail2.py::forward` L836–856에서 확인했다. B-016처럼 H만 바꾸면 generated/driver T offset이 남아 공식 replacement가 아니다. B-023은 공식 bool 경로를 사용하고 별도 offset override를 추가하지 않는다. 실제 첫 두 forward의 block kwargs도 reference=(0,120,0), generated=(0,0,0), driving=(0,0,120)을 기록했다. active LoRA=0, ALG=false, manual RoPE override=false다. 첫 두 forward의 관측을 모든 layer·step의 전체 attention 검사로 확대하지 않는다. mode 경로 확인과 실제 시각적 성공은 별도다.

## 5. 향후 edit support E, alpha, 계산 비용

이 절은 연구 v2의 후속 가설이며 이번 B-023 실행이 아니다. raw 생성 RGB를 $G_t$, source를 $V_t$, 편집할 픽셀의 가중치를 $E_t\in[0,1]$라 하면

$$
Y_t=(1-E_t)\odot V_t+E_t\odot G_t.
$$

$E=0$인 uncompressed pixel은 source를 보존할 수 있다. MP4 encoding 후의 바이트/색차까지 exact라고 할 수 없다. E는 foreground alpha와 다르다. target의 넓어진 실루엣, 원래 객체가 있던 자리를 지운 배경, 그림자·반사·경계도 편집 영역에 들어갈 수 있다. source 객체 mask만 쓰면 새 체형이 잘리거나 잔상이 남는다. RGB SCAIL 출력이 RGBA/clean plate를 자동 제공한다고 가정하지 않는다.

또한 후처리 E 또는 masked loss는 dense DiT token수를 줄이지 않는다. token수 $N=N_{ref}+N_{gen}+N_{drv}$와 attention/MLP 실행은 그대로다. 실제 절감은 ROI해상도·token처리·solver 등 실행을 바꿨을 때 비용을 별도 실측해야 한다. 이번에는 crop·해상도·solver를 바꾸지 않는다.

## 실제 실행과 남은 품질 판정

- 공식 source/mode/mask 계약 감사: COMPLETED.
- B-023 새 cache leaf/scalar 실측: PASS (`cache-derivation.json`: 2 changed / 14 identical, replace_flag 두 scalar 변경, RED 보존, parent 불변, P=0).
- 실제 40step/80forward 완료, final latent 저장 후 S 종료, VAE-only D 완료: PASS.
- raw `[3,17,512,896]` finite=true, MP4 896×512·17frame·30fps·0.566667초: VIDEO_OUTPUT_PASS.
- 사용량: P=0, PROBE=1, sampler=1, decode=1, optimizer update=0, prefix forward=0, retry=0.
- 전신 자세: FAIL. B-020 OFF처럼 착석이 남아 자연스럽게 사족으로 선 source 자세를 재현하지 못했다.
- 원본 장면 보존: FAIL. 중앙 세로 reference 침실 영역이 남고, 옆의 흰 padding은 목재 바닥·창·의자처럼 보이는 새 내용으로 바뀌었다. source의 타일 방·러그·장난감·카메라 구도는 유지되지 않았다.
- 후반 local9–16 머리는 대체로 화면 왼쪽을 향해 source 방향과 부분적으로 대응하지만, 번짐·귀/주둥이 변형과 중앙 세로 경계에서의 잘림이 남는다. 움직임 증가를 품질 개선으로 세지 않는다.
- 검은 Labrador 견종 유사성은 보이나 실제 반려견 일치와 체형 폭은 UNCERTAIN이다. 전체 목표 품질 개선은 NOT_ESTABLISHED.
- temporal: 직접 연속 시청 전 UNVERIFIED.
- 실제 identity-changing replacement와 일반화: NOT_ESTABLISHED.

품질 검토는 raw와 B-020 adapter-OFF, 실제 source를 동일17frame/30fps로 비교한다. B-022 결과를 B-020 baseline으로 바꿔 부르지 않는다. 이번 관측의 다음 가설은 reference의 공간 canvas/layout 정보가 개체와 장면의 분리를 방해할 수 있다는 것이다. 다음 연구는 추가 생성 전에 기존 reference 전처리·padding·latent 공간 배치와 출력의 중앙 경계 대응을 제한적으로 추적하는 한 가지 진단을 제안한다. 이번에 실행하지 않았다. 정확한 버그 원인이나 모든 replacement 입력의 실패로 일반화하지 않는다.


실측 시간은 PROBE 5.074초, S worker 1092.504초, D worker 15.170초다. S 내부 model load 94.609초와 sampler loop 976.400초는 S worker 시간에 포함된다. D 내부 VAE decode는 6.719초다. 내부 시간을 worker 시간에 다시 더해 총비용을 부풀리지 않는다. 근거는 비공개 `runtime-summary.json`, `runtime-terminal.json`, `runtime-mode-evidence.json`, D의 `video.json`이며 공개 실측 요약은 해당 실험 기록에 남긴다.

| 지표 | S | D |
|---|---:|---:|
| 최소 시스템 MemAvailable | 52.679 GiB | 75.781 GiB |
| cgroup peak | 62.004 GiB | 2.157 GiB |
| 최대 관측 RSS | 65.315 GiB | 1.810 GiB |
| CUDA peak allocated | 33.832 GiB | 8.908 GiB |
| 최대 관측 CUDA reserved | 33.893 GiB | 11.562 GiB |

각 열의 메모리는 서로 다른 회계·시점의 값이므로 합산하지 않는다. GB10 통합 메모리에서 cgroup/RSS/CUDA를 독립 용량처럼 더하면 중복 계산이 된다. S의 cgroup high events=3197은 기록에 남긴다. max/oom/oom_kill events는0, swap은0이며 headroom guard 종료는 없었다. high events가 있었다는 사실만으로 OOM이나 driver 버그라고 판정하지 않는다. 실행 종료 시 소유 worker가 남지 않았다는 terminal 기록과 출력 파일을 함께 확인했으며, returncode=0만으로 성공을 정하지 않았다.

## 먼저 생각할 질문

1. reference mask를 BLACK으로 바꿨는데 reference 방이나 착석 자세가 남을 수 있는 이유는 무엇인가?
2. B-023이 B-020보다 원본처럼 보이면 mask의 단독 효과와 reference identity 활용이 모두 입증되는가?
3. raw generation 뒤 source mask로 합성하면 배경 보존과 dense inference 비용은 각각 어떻게 바뀌는가?

## 별도 해설

1. mask는 학습된 semantic embedding이다. RGB VAE/CLIP 정보는 지워지지 않고 모델이 조건을 완벽히 따르는 hard 연산도 없다. BLACK 채널0은 RGB alpha0과 다르다.
2. 아니다. mode와 mask가 함께 바뀌고 같은 Lab source/reference여서 sourcecopy 설명이 가능하다. 비교는 task alignment의 탐색 증거이며 단일 요인 분해와 cross-ID reference 사용은 별도 문제다.
3. E=0인 raw pixel은 보존할 수 있지만 source mask와 새로운 체형·그림자·지운 배경 영역이 다르면 경계/잔상이 남는다. 이미 끝난 dense forward의 token수·연산량은 후처리로 줄지 않는다.

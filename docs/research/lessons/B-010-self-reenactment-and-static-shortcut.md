# B-010 — 자기 재현과 첫 프레임 복사의 구분

최종 **DIAGNOSTIC_INSUFFICIENT / GPU P·PROBE·S·D 모두0회 NOT_RUN**이다. [PLAN](../experiments/B-010-animal-self-reenactment/PLAN.md)은 원본 동물의 첫 프레임을 reference로 사용해, 이후 변화가 첫 프레임 정지 복사보다 잘 재현되는지 묻는다. 새 모델·학습·low-pass 처리는 하지 않는다.

## 1. 직립을 제공하고 직립을 성공으로 세면 안 된다

B-008/B-009는 앉은 Lab reference로 다른 원본 동물의 직립 동작을 전달하려 했다. 이번에는 원본 개체·장면·초기 자세를 이미 맞춰 주는 self-reenactment다. reference 자체가 직립이므로 출력이 직립이라는 사실만으로 동작 전달을 입증할 수 없다. 첫 프레임을17장 반복하는 CPU 정적 대조군도 그 조건을 만족한다.

같은 개체 재현이 성공해도 실제 Lab로의 cross-identity·체형 변환 성공은 아니다. reference RGB·mask·positive text가 함께 바뀌므로 B-009와 단일요인 비교도 아니다. 목적은 해당 입력에서 관측 가능한 시간별 변화가 재현되는지 확인하는 제한된 진단이다.

## 2. 계산 계약과 두 시간축

`c=E(R,D,M,p)`로 조건 묶음을 표기하고 `v_theta(z_sigma,sigma,c)`를 frozen 모델의 조건부 벡터장이라 하자. theta는 이번에 학습하지 않는다. z의 T축은 물리적 영상 시간이고 sigma는 denoising time이다.17 source frame의 시점은 `t_i=i/24초`;40 solver step은40개 영상 프레임이 아니다.

[고정 SCAIL 조건 구성](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L431-L511)은 reference VAE/CLIP, half-size driving RGB VAE, semantic mask와 text를 전달한다. [DiT](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803)는 reference/generated embedding과 driving embedding을 token축으로 결합한다. RGB driving은 순수 관절 좌표가 아니며 reference에는 자세·배경도 들어 있다.

세로512×896·17frame에서 예상 generated latent는 `[16,5,112,64]`, reference `[16,1,112,64]`, driving `[16,5,56,32]`다. reference mask `[28,6,112,64]`, driving mask `[28,5,56,32]`, decoded RGB `[3,17,896,512]`를 실제 P/S/D와 대조한다. 이 값은 이전 같은 해상도 실행과 코드에서 유도한 예상값이며 B-010 실측은 아직 아니다. positive text 길이는 새 prompt의 실제 encoder 결과로 확인한다.

[공식 loop](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L375-L426)의 CFG는 `v_cfg=v_neg+5*(v_pos-v_neg)`다. 두 branch는 reference/driving/mask/CLIP를 공유하고 text context가 다르다. CFG를 높이는 것은 motion 조건만 분리해서 강화하는 조작이 아니다. 이번 CFG5·UniPC40·shift3과 기존 precision/device·RNG 계약을 유지한다. sigma가 감소하는 실제 solver 규약과 noise→data 방향의 교육용 t 식을 혼동하지 않는다.

## 3. 정적 shortcut에 관한 선행연구와 적용 한계

확인한 원문은 Choi et al.의 [Improving Motion in Image-to-Video Models via Adaptive Low-Pass Guidance, arXiv:2506.08456v2](https://arxiv.org/html/2506.08456v2)다. 현재 v2는2026-02-24판이며 계획의 제목 표현과 다르다. 저자들은 I2V가 reference의 고주파 세부에 일찍 묶여 정적 외형을 따라가는 현상을 분석하고, 초기 denoising에는 low-pass 조건을 쓰다가 원래 reference로 전환하는 ALG를 제안한다. 실험 대상에는 Wan 계열과 LTX-Video가 포함된다.

이 논문은 참고할 메커니즘 가설이다. SCAIL은 별도 reference VAE/CLIP와 RGB-driving·semantic mask 경로를 함께 사용한다. B-008/B-009의 착석 결과가 논문의 원인과 같다는 검증은 없다. 논문의 동작량 개선이 우리 source의 동작 방향·타이밍 추종을 보장하지도 않는다. **이번에는 ALG·필터·새 loss를 구현하거나 적용하지 않는다.** 논문 성능 수치와 기여를 이번 실험 성과로 가져오지 않는다.

## 4. 변화 오차는 무엇을 측정하는가

관측 표면점 j의 고정 canvas 좌표를 `p_Y(t,j)`라 하고 `q_Y(t,j)=p_Y(t,j)-p_Y(0,j)`로 초기 위치 대비 변화를 정의한다. source의 고정 기준 크기 s로 정규화하면

`E_motion(Y)=Σ_valid ||q_Y(t,j)-q_src(t,j)||₂ / (n_valid*s)`.

t>0의 동일 표면점이 양쪽0과t에서 실제 관측돼야 한다. copy 대조군은 `p_copy(t,j)=p_src(0,j)`라서 q_copy=0이다. 따라서 E_copy는 source가 실제로 움직였는지를 반영하는 기준이다. s는 결과를 본 뒤 유리하게 조정하거나 프레임마다 바꾸지 않는다.

q는 시작 위치의 상수 오차를 제거하므로 초기 절대 자세 오류를 숨길 수 있다. 초기 자세·형태는 별도 검토한다. 전체 평행 이동이나 zoom만으로도 표면점이 움직이므로 앞발·머리의 상대 움직임과 방향·단계를 함께 본다. frame별 정렬·최적 lag·time warp로 오차를 지우지 않는다.

`gain=1-E_motion/E_copy`는 E_copy가 관측 불확실성보다 충분히 클 때만 보조 지표다. 분모가 작으면 UNDEFINED/INCONCLUSIVE이며 임의 epsilon을 더해 큰 개선율을 만들지 않는다. 관측점 오차는 t와0의 차분 양쪽에 들어가므로 작은 source 변화를 과신하지 않는다.

가려진 점을 추정 관절로 채우지 않는다. 생성 형상이 무너져 대응점을 못 찾으면 missing/invalid와 coverage를 함께 보고한다. source/static/generated의 비교 가능한 공통 표본과 제외 이유를 드러내어 불리한 점 누락이 낮은 오차로 보상되지 않게 한다. 정적 시트의 frame-indexed 변화 검토와 실제24fps 재생 관찰은 별도이며 후자가 없으면 temporal=UNVERIFIED다.

## 5. 조건 변경과 결과 해석

새 reference latent/CLIP/reference mask/positive text는 바뀔 수 있다. driving latent/mask, negative text, noise 값+shape+dtype, generator state, timesteps/sigmas는 사전 정책에 맞춰 보존해야 한다. B-009의 “mask 두 leaf만 변화” 검사를 그대로 쓰면 이번 과제를 잘못 검사하게 된다. 새 입력의 실제 P 연결을 hash·leaf별 변경 집합으로 확인한다.

이번에는 생성 전 관측 가능성 gate에서 중지했다. 따라서 EXECUTION_PASS나 생성물의 MOTION_FOLLOWING_OBSERVED / STATIC_COPY_LIKE / STRUCTURE_FAIL을 판정할 결과가 없다. 자기 재현이 좋아도 RGB driving의 인과 기여를 독립 증명하지 않는다. 같은 reference/text에서 driving 시간을 바꾸는 등의 추가 대조는 별도 연구이며 이번에 실행하지 않는다.

## 6. 실제 생성 전 판정

20개 평가 표면점 항목의 static-copy 기준 오차 E_copy는15.5107px, 평균 전파 관측 불확실성은19.4222px였다. E_copy가 불확실성보다 작아 현재 주석으로 정적 대조군과 생성의 articulated motion을 신뢰성 있게 판별할 근거가 부족했다. 끝점의 코·눈 변화는 보이지만 전역 이동·scale 변화의 영향을 분리하기 어렵고, 앞발 변화는 모두26.8889px의 해당 불확실성 경계보다 작았다. 실행 담당자와 독립 검토자가 실제 시트·crop을 확인했다.

이는 원본에 움직임이 없다는 결론도, SCAIL 생성 실패도 아니다. 원래 B-006 관측을 옮기며 생긴 불확실성과 현재 판별 기준에서의 **DIAGNOSTIC_INSUFFICIENT**다. 원본 클립 자체가 본질적으로 사용할 수 없다고 단정하지 않는다.

[장부](../experiments/B-010-animal-self-reenactment/RUN_LEDGER.json)에 P/PROBE/S/D·sampler·model load·학습·신규 생성 모두0회, 재시도0이 기록됐다. 준비 코드와 CPU8개 fixture 통과는 실제 모델 동등성이나 생성 성공이 아니다. targeted typecheck81errors는 NOT_CLEAN이며 숨기지 않는다. 초기 조건 tensor와 생성 raw의 예상 shape는 실측으로 승격하지 않는다.

다음 제안은 **같은17프레임의 native-resolution 수동 표면점 주석 감사 한 가지**다. B-006에서 이전된 주석의 불확실성을 줄일 수 있는지 CPU 자료에서 확인하는 목적이며 아직 실행하지 않았다. 새 구간·seed·모델·생성으로 자동 전환하지 않는다.

## 이해 확인 질문

1. 직립 출력과 낮은 flicker가 first-frame reference 실험에서 motion 성공을 입증하지 못하는 이유는 무엇인가?
2. displacement error가 작아도 초기 자세나 articulated motion이 틀릴 수 있는 이유는 무엇인가?
3. ALG 논문과 유사한 정적 결과를 보았다는 이유만으로 SCAIL에도 같은 처방이 검증됐다고 할 수 있는가?

## 별도 해설

1. 정적 첫 프레임 반복만으로 직립과 안정성을 얻을 수 있다. source의0 이후 변화가 그 대조군보다 잘 재현되는지 봐야 한다.
2. q는 초기 상수 오차를 지우고, 전체 이동/zoom도 포함한다. 초기 절대 자세·형태와 관절 부위의 상대 방향·위상을 별도 확인한다. coverage와 불확실성도 함께 필요하다.
3. 아니다. 논문의 입력 conditioning·평가와 SCAIL의 reference/driving/mask 경로가 다르다. 관련 가설로 읽되 이번에는 적용하지 않았고 원인도 입증하지 않았다.

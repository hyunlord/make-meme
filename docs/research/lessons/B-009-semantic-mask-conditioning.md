# B-009 — RGB를 지우는 마스크와 의미 조건의 차이

현재 **실물 결과 NOT_RUN / 대기**다. [PLAN](../experiments/B-009-reference-mask-semantics/PLAN.md)은 B-008 결과를 보존하고 reference mask의 정확한 BLACK 픽셀만 WHITE로 바꾸는 한 번의 비교다. reference RGB, RED 개체 영역, driving RGB/mask, prompt와 sampling 설정은 고정한다. 착석 실패의 원인이 마스크였다고 미리 결론 내리지 않는다.

## 1. 먼저 바로잡는 역사적 해석

B-008은 실제17프레임 출력에 착석 자세와 침실이 남았고 동작 전달 FAIL이었다. 그 관측은 보존한다. 그러나 다음 두 해석은 구분해야 한다.

- [고정 README의 mask 의미](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#L84-L100)는 BLACK을 배경 비가시, WHITE를 배경 가시, 색상을 개체 대응으로 정의한다. BLACK이 모든 사용 상황에서 오류인 것은 아니다. 이번 WHITE animation에서는 침실이 남는 것 자체를 실패로 판정하지 않는다.
- [고정 README의 checkpoint 표](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#L132-L138)는 mixed resolutions/fps 학습을 명시한다. 이전 문서의 “native16fps prior” 추론은 writer 기본16fps로 학습 분포를 단정한 것으로 정정한다.24fps 저장은 source 시간축을 유지하며 이번 비교에서 FPS를 바꾸지 않는다. H 인간16fps와 Lab24fps의 비교가 통제된 domain 실험이 아니라는 한계는 여전히 유효하다.

이 문서에서 정정을 남기고 과거 결과·파일·실행 장부는 덮어쓰지 않는다.

## 2. alpha masking이 아니다

alpha 합성이라면 `R_masked=alpha*R+(1-alpha)*background`처럼 RGB 자체가 바뀐다. pinned [scail.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L284-L307)는 reference RGB를 VAE encode하고 mask를 별도로 helper에 넣는다. mask로 reference RGB를 곱해 제거하지 않는다.

따라서 BLACK 배경 mask도 원본 RGB의 침대·커튼을 물리적으로 삭제하지 않는다. 모델에 전달되는 배경 가시성 조건이 달라질 뿐이다. BLACK의 seven-channel zero는 reference branch OFF나 unconditional generation을 뜻하지 않는다. RGB latent·CLIP·text·driving은 여전히 존재한다.

## 3. 실제7색→28채널 계산

[extract_and_compress_mask_to_latent](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106-L141)는 normalized RGB `m∈[-1,1]`을 받는다. 각 밝음 indicator는

`r=1[m_R>tau], g=1[m_G>tau], b=1[m_B>tau]`, `tau=(225-127.5)/127.5`다.

코드는 **strict >**다. 주석의 “≥225”와 달라 경계값 검사는 실제 float 연산과 비교식을 따라야 한다. canonical0/255는 경계 모호성과 떨어져 있다. 순서는 다음과 같다.

| color index | 색 | indicator |
|---:|---|---|
|0|WHITE|rgb|
|1|RED|r(1-g)(1-b)|
|2|GREEN|(1-r)g(1-b)|
|3|BLUE|(1-r)(1-g)b|
|4|YELLOW|rg(1-b)|
|5|MAGENTA|r(1-g)b|
|6|CYAN|(1-r)gb|

BLACK은7개가 모두0이다. 공간축은3번의 ceil-half로 줄이고 area interpolation을 사용한다. 결과는 셀 내 coverage 비율로 분수가 될 수 있다. helper docstring의 binary 출력 설명만 보고 최종값이 항상0/1이라고 주장하면 안 된다.

시간은 첫 frame을4번 반복한 뒤 나머지 frame을 붙이고, 연속4개 frame의7색을28채널로 pack한다. 채널 인덱스는 `7*j+k`(temporal slot j=0..3, color k=0..6)다. T17이면 `(17-1)/4+1=5`; reference T1이면 같은 reference가4개 slot에 들어간다. 그러므로 reference WHITE는0/7/14/21, RED는1/8/15/22채널이다. 이것은7색을 각각4회 연속 나열하는 순서가 아니다.

이번 reference helper output은 `[28,1,112,64]`이고, [공식 조건 구성](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L441-L453)이 generated 부분의 zero plane5개를 붙여 `[28,6,112,64]`를 만든다. WHITE 변화는 reference prefix에 한정돼야 하며 RED와 generated plane을 바꾸는 개입이 아니다. driving은 별도 half-size RGB/mask 경로이고 이번에 변경하지 않는다.

## 4. 벡터장에 mask가 들어가는 위치

설명용 `c=(c_ref,c_drive,c_mask,c_text)`에서 비교는 같은 noise `z_sigma`와 theta에 대해 `v_theta(z_sigma,sigma,c_mask_black,...)`와 `v_theta(z_sigma,sigma,c_mask_white,...)`가 이끄는 출력을 보는 것이다. 실제 [model_scail2.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L766)는 mask embedding을 reference/generated 및 driving embedding에 더한다. CFG 양 branch에도 reference mask가 전달되므로 두 branch의 prefix 변화를 모두 확인해야 한다.

정밀도·device·입력과 scheduler를 고정하고, 새 P의 비마스크 조건은 기존 B-008과 대조한다. GPU 재인코딩에 대한 허용오차는 결과를 보기 전에 정한다. byte equality와 수치 tolerance를 섞지 않고 어느 tensor에 어느 기준을 적용했는지 남긴다. 예상 밖의 큰 reference latent 변화가 있으면 “mask-only” 유효성을 먼저 의심한다. seed만 같다는 이유로 통제를 선언하지 않는다.

성공해도 이 입력에서 의미 마스크 조건이 출력에 영향을 준 근거다. 전체 동물 일반화나 B-008 실패의 유일한 원인 증명은 아니다. 여전히 착석이면 WHITE 하나가 충분하지 않았다는 범위까지 결론 낸다.

## 5. animation과 replacement, 평가의 함정

이번 `replace_flag=False`는 animation이며 그대로 유지한다. [모델의 RoPE 분기](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L830-L850)는 mode에 따라 시간·공간 shift를 바꾼다. mode를 동시에 바꾸면 mask만의 비교가 아니다. 원본 스튜디오 안 개체만 바꾸는 최종 응용은 별도 replacement 계약이다.

주 평가는 뒷발 직립, 들어 올린 앞발, 머리/몸의 source phase 대응이다. 배경만 바뀌거나 몸이 조금 흔들리는 것은 안무 성공이 아니다. WHITE가 요청하는 참조 침실의 유지와 원치 않는 착석 pose 고정은 분리한다. 특정 개체는 UNCERTAIN일 수 있고 실제 재생 미관찰 시 temporal=UNVERIFIED다.

보류된 source-first-frame 자기 재현은 첫 reference 자체가 직립인 함정이 있다. 이후 별도 실행한다면 새 생성 없는 first-frame-repeat 정적 대조군과 motion direction/phase/time을 비교해야 한다. 이번에는 그 실험을 실행하지 않는다.

## 6. 관측 상태

B-008 원본 mask는 RED113,928/BLACK344,824/WHITE0 pixels였다. B-009 실제 CPU변환·helper 출력·P/S/D와 품질 판정은 아직 대기다. 이 숫자는 계획의 parent 근거이며 신규 실행 성과가 아니다. 공개에는 hash/비민감 요약만 남긴다.

## 이해 확인 질문

1. BLACK mask인데도 침실 RGB 정보가 모델에 전달될 수 있는 이유는 무엇인가?
2. WHITE 채널이0/7/14/21인 이유와 area downsample 뒤 분수가 생기는 이유는 무엇인가?
3. WHITE 결과에서도 침실이 남고 Lab가 앉아 있다면 배경과 동작을 각각 어떻게 판단해야 하는가?

## 별도 해설

1. RGB는 따로 VAE/CLIP 처리되며 mask가 RGB를 곱해 지우는 alpha가 아니다. BLACK은 의미 조건의 zero이지 reference branch 제거가 아니다.
2.4개 시간 slot 각각에7색이 들어가는 pack 순서다. area 평균은 각 latent 셀의 색 영역 coverage를 전달한다.
3. WHITE animation은 배경 가시성을 요청하므로 침실 유지 자체는 실패가 아니다. 원본 직립·앞발 동작이 전달되지 않으면 motion은 실패이며, WHITE만으로 충분하지 않다는 결론만 가능하다.

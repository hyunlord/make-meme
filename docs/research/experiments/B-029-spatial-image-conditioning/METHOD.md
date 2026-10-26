# B-029 방법 — 생성 위치별 이미지 조건 출력 재가중

상태: **실제 실행 중 / 완료 case의 코드 연결 확인 / 전체 효과 판정 대기**. [B-028 결과](../B-028-object-reference-normalization/RESULTS.md)를 검토한 뒤 [DECISION](DECISION.md)에서 분기 A를 선택했다. 공통 기준선은 전 6case의 **B-027**이다. B-028의 외형 반응 개선과 차량 방향·자세 회귀, human R2 형태 결함을 보존하며 case별 좋은 결과를 섞지 않는다.

## 질문과 단일 개입

대상 외형 반영 부족과 대상 밖 그래픽 추가가 함께 남은 상황에서, 기존 CLIP 이미지 attention 출력의 전달 위치를 조절하면 외형·원본 동작·장면의 결합 목표가 개선되는가를 묻는다. 실패 원인이 이 경로라고 확정한 실험은 아니다.

고정 SCAIL의 text/image attention 출력과 출력 projection을 각각 \(T,I,W_o,b_o\)라 하면 기존 계산과 이번 변경은 다음과 같다.

\[
O=W_o(T+I)+b_o,\qquad O'=W_o(T+g\odot I)+b_o.
\]

이미지 attention의 **head를 합친 출력**에만 계수를 곱한다. text, bias, Q/K/V, FlashAttention backend, 가중치, 정밀도, RoPE 및 token 순서는 바꾸지 않는다. 기존 reference VAE의 joint self-attention 경로도 그대로 남는다. 새 학습 parameter와 optimizer는 없다.

## 고정 지도와 범위

1. B-027 source의 기존 instance support 17장을 사용한다.
2. 시간 그룹은 `f0`, `f1..4`, `f5..8`, `f9..12`, `f13..16`이며 각 그룹에서 support 합집합을 만든다.
3. clip 전체 support bbox 긴 변의 10%를 올림한 **반경**으로 정사각 dilation한다. 영상 밖은 0으로 취급한다.
4. 고정 7×7 평균 필터, `[0,1]` 제한, 실제 generated token H/W로 area resize를 순서대로 적용하여 \(E\)를 만든다.
5. 시간 slice별 공간 평균 \(\mu_t=\operatorname{mean}_{h,w}E_{t,h,w}\)로 \(g=1+0.5(E-\mu_t)\)를 계산한다.

생성 query 이외에는 `g=1`이다. generated 범위는 실제 runtime의 `additional_ref_length + ref_length`부터 `seq_length`개이며 `[t,h,w]` flatten 순서와 일치시킨다. 모든 해당 cross-attention block, 40 sampler step, 양 CFG branch에 같은 지도 규칙을 사용한다. OFF 또는 lambda 0은 원래 함수를 사용한다.

이 지도는 target RGB alpha·정답 실루엣·hard attention mask가 아니다. source보다 넓거나 다른 target 체형을 정확히 예측하지 않는다. 시간 합집합은 VAE 시간 압축에 맞춘 명시적 근사이며 정확한 receptive field가 아니다. `mean(g)=1`은 계수 평균일 뿐 `mean(gI)`, 특징 norm 또는 예측 속도장 크기의 보존을 뜻하지 않는다.

## 코드의 접점과 runtime 계약

공식 revision은 `78fe19576bb06be96c2375e088574a262a300edb`다.

| 위치 | 확인된 공식 코드의 역할 |
|---|---|
| [`WanI2VCrossAttention.forward` L348–375](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L348-L375) | context를 image/text로 나누어 별도 attention, `img_x` flatten 후 `x + img_x`, 마지막 `self.o` |
| [`WanAttentionBlock.forward` L424–460](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L424-L460) | block은 길이 metadata를 받지만 기존 cross-attention 호출에는 전달하지 않음 |
| [token 구성 L741–823](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L823) | `additional_ref → ref → generated → driving` 순서 및 grid/길이 구성, 별도 CLIP context 구성 |
| [`unpatchify` L870–899](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L870-L899) | 같은 generated offset에서 영상 출력 추출 |

`img_x:[B,L,C]`에 gate `[1,L,1]`를 broadcast한다. 게이트는 실제 연산의 dtype/device를 유지해야 한다. 예시 latent `[16,5,64,112]`, patch `(1,2,2)`라면 generated grid `[5,32,56]`, reference 1,792 / generated 8,960 / driving 2,240 token을 예상하지만 **실제 metadata 검사로 확인할 값**이며 모든 입력의 상수가 아니다.

실험 API와 코드/지도 해시는 [PREREGISTRATION](PREREGISTRATION.json)에 사전 고정했다. 공식 소스 분석과 실제 GPU 관측을 구분한다.

- [`build_support_maps.py`](code/build_support_maps.py)의 `support_map`과 CLI는 source support에서 위 순서로 지도 E를 만든다.
- [`spatial_image_gate.py`](code/spatial_image_gate.py)의 `install(model, support_path, GateConfig(...))`은 `GateInstallation`을 반환한다. `GateMode.METHOD/CONTROL`과 `strength=0.5`, 보고서 경로를 명시한다. block prehook으로 실제 길이/grid를 전달하고 `compile_forward`가 공식 소스의 합산 직전에 image-only 변환을 삽입한다. 공식 소스 SHA를 검사한다.
- `GateInstallation.report()/assert_complete()/remove()`는 관측 요약, 완료 횟수 검증, 원래 bound forward 복원을 담당한다. OFF/lambda0은 원래 forward를 유지한다. 작은 CPU 계약6개와 기존 계약4개가 통과했다. 전체14B OFF 수치 동등성은 검증하지 않았다.
- 실제 forward는 generated 시작1,792·길이8,960·driving suffix2,240, grid[5,32,56]을 기록했다. 이미지 출력 dtype은 FP32이며 변경하지 않았다. module/SHA와 case별 계수 통계는 runtime 보고서에 남긴다.
- 완료된 case마다40step·80forward와40block×80 gate 적용을 확인했다. 미완료 case를 완료로 계산하지 않는다.

## 비교와 변하지 않는 입력

B-027의 공개 animal/human/vehicle × R1/R2 입력·16leaf cache·실제 noise·RNG·scheduler를 읽기 전용으로 재사용한다. 새 encoder와 baseline 생성은 0회다. source FPS는 미확인이고 `source_fps=null / preview_fps=24 / timebase_assumed=true`를 유지한다. 실제 원본 초 단위 타이밍 보존이라고 하지 않는다.

METHOD는 6case, CONTROL은 사전 선택한 animal R1과 vehicle R1이다. CONTROL은 token 지도 H/W를 각각 절반 cyclic shift하며 계수 histogram·평균·lambda·시간 순서를 유지한다. 겹침을 사전에 기록하되 더 유리한 shift를 탐색하지 않는다. 모든 출력은 각각 최대 1sampler·1decode, 40step·80forward, 재시도 0이다. 상세 안전 조건과 실행 순서는 [PLAN](PLAN.md)을 따른다.

OFF 기능, generated 범위, text/bias 불변, 지도와 broadcast, cache/noise/weight 보존, CONTROL 통계/공간 차이만 필요한 범위에서 검사한다. 소형 fixture 통과는 전체 14B 수치 동일성이나 영상 품질 증명이 아니다. 관측용 추가 forward와 dense attention dump는 하지 않는다.

## 선행기법과 판정 한계

[IP-Adapter §3.2.2](https://arxiv.org/html/2308.06721v1#S3.SS2.SSS2)는 분리된 text/image attention과 이미지 항 scale을 사용한다. [Diffusers 공식 공간 masking](https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter#masking)과 [고정 구현](https://github.com/huggingface/diffusers/blob/v0.35.1/src/diffusers/models/attention_processor.py#L4361-L4395)은 image attention 출력에 공간 mask를 곱하고 projection 전에 더하는 선례다. 따라서 이번은 기존 SCAIL 경로의 한정된 개입 실험이며 공간 가중 자체의 신규성을 주장하지 않는다.

참조 VAE 경로와 후속 attention의 정보 확산이 남는다. 대상 부근 강화가 외형보다 참조 자세 복사를 키울 수도 있다. 외형만 좋아지고 원본 동작·장면·형태가 나빠지면 trade-off다. METHOD와 CONTROL이 비슷하면 “대상 위치에 맞춘 배정”이라는 설명은 미입증이다. 지도 겹침은 대조력을 낮춘다.

전체 17장과 local0/8/16, 사전 외형 특징·동작 사건·보호 장면으로 판정한다. 이 3과제는 방법 선정에 사용한 개발 패널이며 6출력·102프레임은 독립 반복이 아니다. 연속 재생 관찰이 없으면 temporal=UNVERIFIED다. 실제 효과와 다음 검증 승격 여부는 결과 작성 단계까지 **PENDING**이다.

# B 트랙 통합 연구 의뢰서 — 전처리 비교에서 생성 메커니즘 개입으로

작성: 2026-10-26
저장소: hyunlord/make-meme
브랜치: docs/b-research-20261022
상태: 후속 수행 의뢰서 / 새 방법 미선정 / 실제 GPU 실행 없음

이 문서를 실행 담당 Codex 또는 Claude Code에 전달한다. B-028 결과를 보지 않고 다음 원인이나 방법의 유효성을 확정하지 않는다. 아래에서는 결과 확인, 방법 선택, 실제 구현, 제한된 대조 실험까지의 범위를 함께 지정한다.

## 1. 목표와 이번 완료 조건

최종 목표는 원본 영상 V, 참조 이미지 R, 자연어 편집 지시 P를 받아, 대상 객체의 외형을 참조에 맞게 바꾸면서 지정된 원본 동작·시간 순서·장면·다른 객체를 보존하는 로컬 영상 편집 방법이다. 단일 DGX Spark에서 품질과 전체 비용을 함께 검증한다.

특정 반려견에 맞춘 개인화 실험으로 돌아가지 않는다. 개인 사진의 추가 촬영이나 목표와 같은 자세의 사진 확보를 연구 전체의 필수조건으로 삼지 않는다. 기존 개인 사례는 선택적 회귀 사례이며, 이번 주 실험은 이미 확보한 공개 개발 패널이다. A의 native imagegen 경로와 B의 로컬 생성 연구는 분리한다.

이번 완료 조건은 문서·설치·테스트만의 PASS가 아니다.
- B-028의 실제 결과와 남은 병목을 정리한다.
- 필요한 경우 기존 생성기의 실제 계산 경로에 변경 하나를 구현한다.
- 같은 입력의 기준선·방법 적용·핵심 제거/음성 대조 결과를 얻는다.
- 외형·동작·장면 보존·비용 중 무엇이 달라졌는지 설명하고 채택·기각·불확실을 결정한다.

개선되지 않은 결과도 유효한 종료다. 성공 문장을 만들기 위해 사진·prompt·seed·설정을 계속 바꾸지 않는다.

## 2. 현재 작업 보존과 B-028 처리

최신 원격 HEAD와 로컬 상태, 실제 실행 중인 자기 작업을 먼저 확인한다. 확인 기준으로 공유된 HEAD는 ebd728c4c48823f6d7f627174370455ec1736138이며, 이 커밋으로 강제 reset하지 않는다. 이후 작업과 미추적 자산을 보존한다.

우선 읽을 문서:
- docs/research/CHARTER.md
- docs/research/RESEARCH_V2_SOURCE_PRESERVING_EDITING.md
- docs/research/HISTORY.md
- docs/research/ROADMAP.md
- docs/research/experiments/B-027-public-reference-robustness/RESULTS.md
- docs/research/experiments/B-027-public-reference-robustness/CASES.md
- docs/research/experiments/B-028-object-reference-normalization/PLAN.md
- B-028의 실제 RESULTS·비교 자료·실행 장부가 있으면 함께 확인

B-028이 완료됐다면 그 결과를 재사용한다. 다른 worker에서 진행 중이면 중단시키거나 동시에 새 GPU 작업을 시작하지 않는다. 이 의뢰서는 그 작업 종료 후 이어서 적용하며, 별도 백그라운드 감시 작업은 만들지 않는다.

B-028이 미착수이고 이 의뢰서를 수행하는 단독 worker라면 기존 PLAN의 6회 상한 안에서 먼저 수행한다. 부분 실행이라면 미실행 case만 확인하며, 이미 실패·완료한 case를 새 예산처럼 다시 생성하지 않는다. 기존 B-028 실행 범위를 늘리지 않는다.

현재 원격 문서가 PLANNED라는 이유만으로 로컬에서도 미실행이라고 가정하지 않는다. 입력 파일명·manifest·run ID를 확인한다.

## 3. B-028 결과를 보고 다음 분기를 결정

B-027/028의 같은 공개 3과제×2참조를 나란히 검토한다. 전체17장, 사전 사건 프레임, 실제 입력 참조를 확인한다. 사람의 연속 재생 검수를 하지 못했다면 temporal=UNVERIFIED를 유지한다.

질문은 다음 네 가지다.
1. 목표 외형은 반영되는가, 원본 객체가 남는가?
2. 원본 움직임 대신 참조 자세를 복사하는가?
3. 얼굴·사지·치마·차체 형태가 무너지는가?
4. 보호 배경에 문자·그래픽·다른 물체가 생기거나 기존 물체가 사라지는가?

다음 실험의 기준선은 B-027 입력 방식 또는 B-028 입력 방식 중 하나를 패널 전체에 공통으로 고른다. 모든 case에서 유리한 결과만 골라 섞은 best-of 기준선을 만들지 않는다. 선택 근거와 case별 개선·회귀를 DECISION.md에 남기고 이후 생성 전에 고정한다.

기준선 선택 원칙: B-028이 공동 목표를 개선하고 명백한 큰 회귀가 없으면 B-028을 사용한다. 효과가 없거나 중요한 회귀가 있으면 B-027로 돌아간다. 혼합 결과라면 단일 기본값을 명시하고 다른 쪽은 별도 역사 비교로 보존한다. 품질을 임의의 숫자 하나로 합쳐 선택하지 않는다.

분기 A: 외형 반영 부족, 참조 자세 영향, 보호 장면 손상 중 반복되는 문제가 남으면 4~9절의 작은 생성 경로 개입을 검토·실행한다.
분기 B: B-028이 3과제의 두 참조 모두에서 관측 가능한 외형·동작·장면 목표를 충족했다면 불필요한 새 방법을 만들지 않는다. 미사용 공개 source/target 조합 2개에서 기준선 최대2회만 검증하고 종료한다. 시간 품질과 일반화가 완전히 입증됐다고 하지는 않는다.
분기 C: 구체적인 잘못된 입력·캐시·실행 경로 오류가 발견되면 최소 수정과 결과 영향을 먼저 기록한다. 오류 수정과 새 알고리즘을 섞어 방법 개선이라고 보고하지 않는다. 추측만으로 전체 변환·커널·가중치 감사를 재개하지 않는다.

분기 A와 B를 모두 자동 실행하지 않는다. 어떤 분기를 선택했는지 생성 전에 기록한다.

## 4. 방법 선택 — 한 가지 작은 개입만

방법 구현 실험은 번호가 비어 있으면 B-029로 기록한다. 이미 사용 중이면 다음 번호를 사용하고 이번 의뢰서와 연결한다. B-028 결과와 무관하게 미래 실험 번호·원인을 확정하지 않는다.

우선 가설:
“이미지 참조 특징의 영향이 교체 대상과 보호 문맥에 공간적으로 구분되지 않는 것이 품질 상충에 기여하는가? 기존에 학습된 이미지 특징의 전달 위치를 조절하면 외형과 동작·장면 보존의 결합 결과가 개선되는가?”

우선 구현 후보는 기존 CLIP 이미지 cross-attention 출력의 query 위치별 재가중이다. 새 모델·무작위 adapter를 붙이는 것이 아니라 이미 학습된 경로에 가역적인 연산 하나를 넣는다. 객체 인코더를 새로 학습하거나 정체성·자세 분리가 이미 달성됐다고 부르지 않는다.

고정 SCAIL 소스 78fe19576bb06be96c2375e088574a262a300edb의 wan/modules/model_scail2.py에서 다음을 확인한다.
- WanI2VCrossAttention은 텍스트 attention 결과와 img_x를 별도로 계산한 뒤 합한다.
- CLIP 경로와 reference VAE latent의 joint self-attention 경로는 다르다.
- 이미지 경로만 바꿔도 VAE 경로에는 참조의 자세·배경 정보가 남을 수 있다.

최대90분 안에 위 경로와 IP-Adapter의 decoupled attention/공간 마스크, 관련 영상 편집 방법을 좁게 대조한다. 문헌만 수십 편 정리하지 말고 이번 개입과 겹치는 부분·달라지는 부분·예상 반례를 짧게 남긴다.

결과가 이 후보를 시험할 근거를 주지 않는다면 억지로 선택하지 않는다. 대체는 기존 가중치·기존 입력만으로 가능한 조건 경로 개입 하나에 한하며, 실제 함수·연산·대조군·예산을 구현 전에 구체적으로 고정한다. 새 backbone 설치, 유료/원격 생성, 학습할 정답이 없는 무작위 adapter 학습, 사진 재선정으로 대체하지 않는다. 대체 방법까지 구체화할 수 없으면 METHOD_NOT_READY와 빠진 근거를 명시하고 종료하며, 문서 완성을 방법 구현 PASS로 세지 않는다.

이후 5~8절은 우선 후보를 선택했을 때의 기본 계약이다. 다른 방법을 선택하면 같은 수준의 단일 변경·OFF·음성/제거 대조 계약을 사전 문서화하고 동일한 새 생성 상한을 지킨다.

## 5. 우선 후보의 정확한 수식과 적용 위치

현재 계산을 단순화하면 다음과 같다.
T = Attention(Q, K_text, V_text)
I = Attention(Q, K_image, V_image)
O = W_o(T + I) + b_o

변경:
O_new = W_o(T + g * I) + b_o

g는 query token별 broadcast 계수다. W_o 뒤의 합쳐진 출력을 통째로 곱하지 않는다. 그러면 텍스트 경로와 bias까지 바뀌기 때문이다.

생성 영상 token에 대응하는 편집 지지 지도 E를 0~1로 구성하고, 각 latent 시간 slice의 공간평균을 mu라고 한다.
- BASE: g = 1
- METHOD: g = 1 + lambda * (E - mu)
- 첫 pilot의 lambda = 0.5, 전 case·전 layer·전 denoising step에 동일

이 규칙은 공간평균 계수를1로 유지하며 대상 부근은 더, 바깥은 덜 반영하는 시험이다. 실제 feature norm·attention 확률·모델의 총 참조 영향·품질이 보존된다는 뜻은 아니다. g의 평균만 같고 I와의 상관·후속 비선형 연산은 달라질 수 있다.

첫 실험에서는 학습·시간 schedule·layer 선택을 동시에 추가하지 않는다. 기준선이 사용하는 모든 해당 이미지 cross-attention block에 같은 규칙을 적용한다. positive/negative 양 CFG에도 같은 지도를 적용해 CFG 분기를 새로 정의하지 않는다.

reference token과 driving token의 g는1로 유지한다. generated token 범위는 actual ref_length/seq_length/additional_ref_length 등 runtime 메타데이터로 확인한다. 길이를 모델의 모든 입력에 통하는 상수로 하드코딩하지 않는다.

reference VAE의 self-attention, RoPE, 텍스트, sampler, 가중치, precision은 유지한다. 이 개입은 CLIP 특징의 직접 전달 한 경로를 시험할 뿐, 배경의 픽셀 보존이나 pose-free identity를 보장하지 않는다. 이후 self-attention을 통한 간접 전파도 남는다.

## 6. 편집 지지 지도와 음성 대조

E는 참조 사진의 누운/선 실루엣이 아니라 원본 영상에서 교체할 객체의 source mask로 만든다. source pose를 유지하고 싶은 출력 위치를 기준으로 한다.

기본 규칙:
- 기존 source instance label만 사용한다. 새 segmentation을 하지 않는다.
- clip 전체 source bbox의 긴 변10%를 고정 공간 여유로 사용해 각 프레임 mask를 팽창한다. source frame 밖은 clip한다.
- 이진 mask는 고정7×7 평균 필터로 경계를 부드럽게 하고 0~1로 제한한다.
- 모델의 실제 generated token H/W로 area resampling한다.
- 17프레임→5latent 시간의 기본 지도는 첫 프레임 단독, 이후1~4/5~8/9~12/13~16의 지지 영역 합집합으로 만든다. 이는 시간 대응을 위한 명시적 근사이며 VAE의 정확한 receptive field라고 부르지 않는다.
- source frame과 token slice의 지도·offset·shape를 시각화한다. 실제 모델의 temporal/patch 규약이 이 전제와 다르면 생성 전에 근사 규칙을 수정·기록한다.

지도는 feature 전달 위치를 조절하는 soft prior이지 최종 RGB alpha나 hard crop이 아니다. 체형 변화로 source 실루엣 밖이 필요할 수 있고 가려진 target geometry는 알 수 없다. source 픽셀 좌표에 신체를 강제로 맞추지 않는다. 팽창률·필터·lambda를 결과 뒤에 조정하지 않는다.

핵심 음성 대조 CONTROL:
- METHOD와 같은 E를 token 공간에서 높이·너비 각각 절반만큼 cyclic shift한다.
- g_control = 1 + lambda * (shift(E) - mu)
- 시간 순서·계수의 histogram·평균·lambda·계산량은 같고 공간 배정만 달라진다.
- wraparound는 대조군을 위한 연산일 뿐 제품 입력 전처리가 아니다.

두 대조 case는 새 출력 전에 고정한다. 우선 반복된 실패가 있는 서로 다른 두 과제의 R1을 사용한다. shifted map과 원래 map이 너무 겹쳐 대조의 구분력이 낮으면 그 한계를 사전에 표시한다. 여러 shift를 생성해서 유리한 것을 고르지 않는다.

CONTROL보다 METHOD가 낫더라도 모든 차이를 정체성·자세 분리로 해석하지 않는다. 이것은 주입 위치의 유용성을 좁게 보는 대조다. 이 계열의 마스킹·재가중 자체가 새 아이디어라고 주장하지 않는다.

## 7. 구현 검사와 생성 예산

기존 실험 코드를 복제해 새 거대 framework를 만들지 말고, 별도 실험 모듈과 on/off 설정으로 좁게 구현한다. 실제 사용한 patch·upstream revision·입력을 기록한다.

필수 검사는 4~6개로 제한한다.
- OFF 또는 lambda0에서 기준 함수와 기능상 일치한다.
- generated token 범위만 직접 변조되고 ref/driving query는 그대로다.
- text output·W_o bias를 별도로 스케일하지 않는다.
- E와 token 좌표·시간·broadcast가 맞으며 유한하다.
- 원래 가중치·입력 cache·noise가 불변이다.
- METHOD와 CONTROL의 계수 통계와 공간 차이가 의도대로다.

작은 고정 tensor fixture와 기존 테스트를 사용한다. 검증만을 위해 전체 모델을 새로 학습하거나 full clip을 별도 반복 생성하지 않는다. 첫 실제 forward의 가벼운 hook으로 적용 위치·gate min/max·평균·모듈 경로를 확인한다. 대형 attention map이나 모든 feature dump를 만들지 않는다.

FlashAttention의 기존 연산은 그대로 사용하고 img_x의 결과에 broadcast 연산을 추가한다. L×L dense attention 행렬을 만들거나 backend를 바꾸지 않는다. 새 학습 파라미터는0이다. 단순 연산 추가여도 비용은 실측하고0이라고 가정하지 않는다.

방법 분기 A의 신규 sampler 상한은8회다.
- METHOD: 기존3과제×2참조=6회
- CONTROL: 사전 선택2case×1회=2회
- BASE: 선택한 B-027 또는 B-028 출력 재사용, 새 생성0회

각case는 기존40step·80forward와 decode1회다. 각 baseline에 대응하는 실제 initial noise와 입력을 사용한다. total method denoising은 최대320step·640forward다. 기존 결과의 재사용 가능 계보가 없으면 다른 출력으로 대체하지 말고 해당 비교 한계를 기록한다. baseline 재생성을 이 예산에 몰래 추가하지 않는다.

첫 결과가 시각적으로 나쁘다는 이유만으로 사전 지정한 나머지 과제를 생략하지 않는다. 입력 오류·비유한값·안전 문제는 중단 사유다. 실패도 시도에 포함하고 seed나 설정을 바꾼 자동 재시도를 하지 않는다.

## 8. 평가 — 이번에는 실제 방법 효과를 판정

모든 case에서 SOURCE / REFERENCE / BASE / METHOD를 보여 주고, 해당 두 case에는 CONTROL을 추가한다. 표시 이름을 A/B로 가린 평가 페이지와 실제 라벨을 밝힌 페이지를 함께 제공하면 좋다. 단순 익명 표시는 독립 블라인드 사람 평가를 했다는 뜻은 아니다.

생성 전에 target 외형 특징2~3개, source 동작 사건2개, 보호할 객체·배경을 기존 패널 정의에서 가져와 고정한다. 결과를 보고 성공하기 쉬운 사건으로 바꾸지 않는다.

핵심 축:
- target 외형 반영: 원본 객체가 남는지, 참조에 있는 외형 변화인지
- source 동작: 방향·순서·자세·이동이 유지되는지
- 형태: 얼굴·팔·사지·치마·차체 연결이 유지되는지
- 보호 장면: 문자·서명 모양·그래픽·다른 물체의 추가/소실
- R1/R2 변화에 대한 강건성
- end-to-end 비용과 실패 포함 사용량

정밀 개체식별·가려진 몸·정확 관절각의 근거가 없으면 UNCERTAIN으로 둔다. 사람의 실제 이름·신원을 식별하지 않는다. 외형 개선만으로 전체 성공을 선언하지 않는다.

낮은 해상도 참조의 세부를 확대해서 복원했다고 하지 않는다. source mask를 편집 후 객체의 픽셀 정답으로 쓰지 않는다. 새 실루엣의 합당한 가림과 보호 장면 소실을 구분한다. 정량 지표가 가능하면 보조값으로 쓰되 임의 joint score나 정확한 identity accuracy를 만들지 않는다.

raw 프레임은 보정하지 않는다. 합성·얼굴 복원·SR·보간·문자 제거·시간/위치 정렬을 섞지 않는다. source-copy는 identity-change 실패, reference 정지 복사는 motion 실패다.

17장 정적 검토와 preview24fps 재생을 구분한다. 원본 FPS가 미확인인 기존 공개 패널은 그 상태를 유지한다. 사람이나 검토 주체가 실제 연속 시청을 하지 않았다면 temporal=UNVERIFIED다. 이것만으로 탐색 비교를 중단하지 않되 논문/제품 품질 PASS로 올리지 않는다.

6출력이나102프레임을 독립 반복으로 세지 않는다. 동일3과제는 개발 자료이며 이미 방법 선택에 사용됐다. 이번 결과를 미사용 일반화 평가로 부르지 않는다.

## 9. 채택·기각과 다음 경계

결과표는 개선/동일/악화와 근거 프레임을 축별로 기록한다. 적어도 두 과제에서 결합 목표에 유리하고 나머지에 명백한 큰 퇴행이 없을 때만 다음 검증 후보로 승격한다. 이는 작은 개발 패널의 운영 기준이며 통계적 유의성 기준은 아니다.

- METHOD가 BASE와 CONTROL보다 유리하면, 위치를 고려한 참조 경로 제어의 후속 후보로 남긴다. 아직 신규성·일반화가 입증된 것은 아니다.
- 외형만 좋아지고 동작/형태/장면이 악화되면 trade-off로 기록한다.
- METHOD와 CONTROL이 비슷하면 위치 선택 때문이라는 설명은 미입증이다.
- 전반적 효과가 없으면 이 고정 가설을 기각/보류하고 종료한다. lambda·mask·layer·sigma sweep으로 이어가지 않는다.

이후 미사용 데이터 검증, 선택적 학습, 다른 backend, 효율화, 수초·두 객체·15초 확장은 로드맵에 적되 이번에 자동 실행하지 않는다. 방법이 잘됐다는 이유로 범위를 임의로 늘리지 않는다.

향후 학습 모듈을 제안할 때는 trainable parameter, 데이터 R/D/Y, loss, source-copy shortcut, 분리된 평가 자료, 메모리·update 예산이 필요하다. 데이터/목표 없이 랜덤 adapter를 붙여 'identity module'이라고 부르지 않는다. 기존 학습 가능 경로와20→100회 결과는 재사용하되 같은 실습을 반복하지 않는다.

VideoPainter 같은 다른 backend는 임의 reference를 받는 전체 경로와 로컬 첫 프레임 편집 단계를 확인한 별도 실험으로 설계한다. generic text-to-image 결과나 정답 edited frame을 넣고 원래 V/R/P 과제를 해결했다고 주장하지 않는다.

## 10. 자원·작업 상한

이번 의뢰 전체의 벽시계 작업 상한은8시간이다. 새 방법의 설계·구현·작은 검사에 최대2시간을 배정하고, 관측 가능한 출력 비교를 위한 시간을 남긴다. 이 상한은 실행 담당자의 자원 제한이지 완료 시간 보장이 아니다.

B-028이 이미 완료됐다면 추가 신규 sampler는 분기 A 최대8회 또는 분기 B 최대2회다. 미착수 B-028까지 수행한다면 기존6회와 합쳐 전체 최대14회다. 이미 다른 세션에서 사용된 시도는 중복 사용하지 않는다. 총시간 상한에 닿으면 미실행 항목을 그대로 기록한다.

GPU 작업은 단일 DGX Spark에서 하나씩 순차 실행한다. 기존 phase 분리·tiny CUDA·72GiB 시작/24GiB 실행 headroom·swap0·타 서비스 보호를 유지한다. 다른 프로세스 종료·driver 변경·swap 변경·가드 완화를 하지 않는다.

새 대형 모델/가중치/패키지 설치, 외부 생성·imagegen, optimizer update는0이다. 기존 학습된 모듈을 그대로 사용하는 추론 메커니즘 실험이다. 분기 B에서만 기존 캐시에 없는 공개 소규모 데이터 다운로드를 최대1GiB 허용하고 출처·이용 조건을 기록한다.

각 endpoint의 final latent를 decode 전에 저장한다. decode 실패로 sampler를 다시 실행하지 않는다. CUDA allocated/reserved, OS MemAvailable/RSS, cgroup charge/events는 각각 보고하고 더해서 총메모리라고 하지 않는다. cold/warm·model load·encoder·sampler·decode·전처리·사람 수정 시간을 구분한다.

새 방법이 더 빠를 것이라고 가정하지 않는다. NFE가 같다는 것과 실행 시간이 같은 것도 구분한다. 이번 성과는 우선 동일 모델·유사 생성 예산에서의 품질 변화이며, 실제 비용을 줄이지 않았으면 효율성 향상을 주장하지 않는다.

## 11. 공부·선행 연구·GitHub 기록

한국어 해설은 다음을 실제 구현·수식·출력과 연결한다.
1. 이미지와 텍스트의 분리 cross-attention, VAE reference self-attention과의 차이
2. feature/residual 재가중과 attention-logit mask, semantic mask, 최종 RGB 합성의 차이
3. token 좌표·시간 압축·편집 support 근사의 의미
4. OFF와 공간 음성 대조가 각각 어떤 설명을 검사하는지
5. 개발 패널 개선과 일반화·상용급·논문 기여의 차이

직관 → 수식/가정 → tensor와 실제 함수 → 실험 결과 → 반례 순으로 적는다. 핵심 질문3개와 해설도 남긴다. 형식상 긴 교과서를 복제하지 않는다.

우선 확인할 1차 자료:
- 고정 SCAIL 코드: https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py
- IP-Adapter 논문: https://arxiv.org/abs/2308.06721
- 공간 마스크 문서: https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter
- VideoPainter 공식 구현: https://github.com/TencentARC/VideoPainter

공간 마스킹과 이미지/텍스트 조건 분리는 이미 존재하는 아이디어다. 이번 구현은 기제 진단·기준선 확장이며 '최초의 새로운 방법'으로 이름 붙이지 않는다. 실제 독창성은 추가 방법·강한 대조·여러 미사용 입력의 검증 뒤에 판단한다.

작업 전 이 의뢰서를 docs/research/work_orders에 기록한다. B-028 결과를 확인한 뒤에만 다음 실험의 PLAN과 DECISION을 확정한다. B-029 번호가 이미 있으면 덮어쓰지 않는다.

CHARTER/RESEARCH_V2의 오래된 최신 상태, HISTORY/ROADMAP을 정리하되 과거 실패·보류·예산·사전 계획은 보존한다. 실행 전 코드·입력·상한·평가 기준을 commit/push해 원격 SHA를 확인한다. 동시 편집이 보이면 fetch/reconcile하고 force push하지 않는다.

종료 시 RESULTS, METHOD, ABLATIONS, COSTS, REPRODUCE, 한국어 lessons와 다음 결정 한 개를 남긴다. 실제로 한 것과 제안만 한 것을 구분한다. 정적 타입 진단과 runtime·품질 판정을 분리하고, 이번 경로의 실제 오류는 고치되 무관한 전체 타입 리팩터링을 하지 않는다.

## 12. 산출물과 종료 보고

개인 미디어·비밀정보·가중치·condition cache·latent를 공개 GitHub에 올리지 않는다. 공개 데이터도 원래 재배포 조건을 확인한다. 공개에는 비민감 코드·설정·출처 명세·결과 요약을 남긴다.

Spark와 Mac의 /tmp에 다음을 분리 보존한다.
- full ZIP: 재현 설정·runner·실제 결과·raw·최종 latent·실패 장부·검증 근거. 기존 대형 가중치와 중복 corpus/cache는 제외.
- review-lite ZIP: 입력 참조, 비교 MP4, 모든 프레임을 열 수 있는 뷰어, 비교 시트·보고서·실측. raw tensor·latent·중복 PNG는 제외. 검토용은 기존 MP4를 재사용하며 무단 재인코딩으로 화질을 바꾸지 않는다. 크기 목표는250MiB 이하이나 필요한 증거를 버려 맞추지 않는다.

실제 전송·CRC·payload hash·추출을 검증하고 수행한 범위만 보고한다. 원본 full을 삭제하지 않는다. 자체 worker와 watchdog을 종료하고 기존 서비스를 보존한다.

최종 답변 맨 앞에는 다음을 적는다.
- 무엇을 바꿨고, 실제 영상에서 무엇이 좋아지거나 나빠졌는가?
- 기존 방식과 음성/제거 대조보다 나았는가?
- 참조 외형·동작·장면을 함께 보존했는가?
- 추가 비용은 얼마이며, 근거가 부족한 부분은 무엇인가?
- 다음 단계로 넘길 방법인가, 기각/보류할 가설인가?

그다음 실제 생성 횟수·테스트·해시·ZIP·GitHub 링크를 적는다. 테스트 수나 파일 무결성만으로 연구 성공을 대신하지 않는다.

이번 의뢰 범위 종료 후 멈춘다. 추가 seed·학습·새 모델 설치·다음 연구를 자동 실행하거나 예약하지 않는다.

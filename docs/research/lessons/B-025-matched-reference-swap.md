# B-025 — 같은 원본에서 참조 묶음이 실제 출력을 바꾸는가

두 조건 실행·정적 검토 후 설명이다. PLAN, 결정문서, 연구 공통 기록과 현재 `code/phase_encode.py`, `code/pair_contract.py`를 읽었다. ENC 조건 준비와 두 sampler의40step/80forward·decode가 완료됐다. 참조 외형 반응은 관측됐지만 IG의 전신 동작 전이는 실패했다. 실행 성공과 품질 수용을 분리한다.

## 직관: 같은 개체는 복사와 교체를 구분하기 어렵다

B-024에서는 source와 reference가 같은 Lab였다. 결과가 그 개처럼 보이고 source의 자연동작·방을 잘 따르더라도 모델이 reference를 이용했는지, driving 개체를 재구성했는지 구별하기 어렵다. raw가 원본 파일과 다르다는 검사는 파일 바꿔치기를 배제하지만 모델 수준의 source-copy 설명은 배제하지 않는다.

이번에는 같은 source와 같은 외형 중립 caption을 두고 Lab/IG 참조 묶음만 바꾼다. 단순히 결과 둘이 달라지는 것을 성공으로 보지 않는다. 차이가 생성 전에 관측한 각 참조의 털색·무늬·귀·주둥이·사지 비율과 대응하고, 원본 장면과 동작도 보존돼야 한다.

## 수식: 무엇을 고정하고 무엇을 함께 바꾸는가

$V$는 Lab driving RGB, $M_D$는 해당 semantic mask, $P^*$는 공통 caption, $\epsilon$은 실제 초기 noise다. $R_k$는 중립 배경을 적용한 참조 RGB, $M_k$는 RED/BLACK 참조 mask이며 $k\in\{L,I\}$는 Lab/IG다.

$$
C(R_k,M_k)=\big(E_{VAE}(R_k),E_{CLIP}(R_k),E_{mask}(M_k)\big),
$$
$$
Y_k=G_\theta\big(V,M_D,C(R_k,M_k),P^*,\epsilon\big).
$$

모델 가중치·scheduler·정밀도·mode·시간축을 고정한 한 쌍이다. seed 동일만으로 충분하지 않으며 실제 noise·RNG·timesteps·sigmas를 확인한다. 이후의 noisy latent는 조건이 달라지면 서로 달라지는 것이 정상이다. 같은 초기 noise는 두 결과의 차이를 줄여 읽는 통제이지 같은 궤적이나 통계적 유의성의 보장이 아니다.

예를 들어 관측 특성 $F$에 대해 $F(Y_I)-F(Y_L)$를 비교할 수 있다. 그러나 이 차이는 RGB·mask·사진 속 pose·support·사진 품질을 포함한 **참조 묶음 교체 효과**다. identity만의 순수한 인과효과, VAE/CLIP 각각의 효과로 나눌 수 없다. 무정보 reference 대조군도 없으므로 reference의 필요성을 증명하지 않는다.

기존 B-024 caption에는 검은 Lab·넓은 가슴·굵은 사지 지시가 있었다. 이를 그대로 IG에 쓰면 text/ref 충돌이 생기고, IG에서만 text를 바꾸면 text 기여가 섞인다. B-025는 외형 중립 $P^*$ 하나를 양쪽에 사용하므로 새 Lab 결과도 필요하다. B-024 결과는 역사맥락이며 새 pair의 정확한 대조군이 아니다.

## Tensor와 실제 코드 연결

원본은 기존 자연동작 f126..142, W896×H512,17frame/30fps다. B-024 Lab reference latent/CLIP와 driving·noise를 재사용하고, 공통 positive T5를 한 번 계산하여 두 case에 동일하게 복사한다. IG는 그 실제 masked RGB를 VAE/CLIP에 각각 한 번 보내고 semantic helper로 ref mask를 만든다.

| 조건 | shape | pair에서의 계약 |
|---|---|---|
| ref_latents 양 CFG | 각각[16,1,64,112] | reference 따라 변경 |
| clip_fea 양 CFG | 각각[1,257,1280] | reference 따라 변경 |
| ref_masks 양 CFG | 각각[28,6,64,112] | reference support 따라 변경 허용 |
| pose_latents 양 CFG | 각각[16,5,32,56] | 보존 |
| driving_masks 양 CFG | 각각[28,5,32,56] | 보존 |
| noise | [16,5,64,112] | 보존 |
| positive/negative text | [62,4096]/[1,4096] BF16 | pair 내부 보존 |
| RNG/timesteps/sigmas | [16] uint8/[40] int64/[41] FP32 | pair 내부 보존 |

`code/phase_encode.py::run`은 B-024 parent receipt를 검사하고 cache를 복사한다. 공통 positive context를 양쪽 `arg_c.context`에 넣고 negative는 재사용한다. IG의 새 VAE·CLIP는 양 CFG의 `ref_latents`와 `clip_fea`에 넣는다. 새 ref mask prefix `[28,1,64,112]` 뒤에는 원래 generated zero suffix를 보존한다.

`code/pair_contract.py::pair_changes`는 허용 변경 키를 t2/t3/t4/t8/t9/t10으로 제한하고 RGB VAE/CLIP 네 키의 변화를 요구한다. mask 두 키는 허용하되 우연히 같은 support가 나오면 반드시 변경됐어야 한다고 요구하지 않는다. pair 외 나머지10leaf는 동일해야 한다. 별도로 새 Lab과 B-024는 positive t1만 바뀌는지 검사한다. 실제 `reports/pair-conditions.json`은 PASS이며 t2/t3/t4/t8/t9/t10의6leaf 변경, 나머지10leaf 동일, structure/device 불변, Lab 대 B-024는 t1만 변경을 기록했다. 두 실제 conditions.json에서 위 shape와 dtype도 확인했다. 공통 positive T51회, IG VAE1회·CLIP1회, negative T5/Lab VAE/Lab CLIP/전체 P는0회였다. 두 cache SHA는 LAB `9d825797775caea37324ea0dd3dc67b3e63fffca0ace49cf182d62709c44b0bf`, IG `32a4c1ca7d0b5453cd34ad464f1046658d7150aab15d39d22000d6d0aba285c5`다. 이 준비 결과를 실제 sampler 인자 수용이나 품질 PASS로 확대하지 않는다.

공식 [SCAIL `generate`](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L286)는 reference VAE와 [CLIP](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L335)를 별도 경로로 받는다. [mask embedding](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L751)은 학습된 조건이며 hard alpha가 아니다. 회색 RGB128도 no-reference가 아니고, BLACK semantic mask도 attention 차단이 아니다. 두 참조에 같은 규칙을 적용해도 다른 pose·support의 영향을 제거하지 않는다.

## 실제 관측과 수용 범위

실제 조건 검사는6leaf 변경/10leaf 보존이며 두 경우 모두40step/80forward와 decode가 완료됐다. 실행 담당자와 별도 검토자는 전체17장 및 local0/8/16 정적 비교를 보았다. 이는 독립 사람 ground truth나 native속도 연속 시청이 아니다. 근거는 `pair-conditions.json`, `CONDITION_REVIEW.json`, `RUNTIME_SUMMARY.json`, `VISUAL_REVIEW.md`다.

| 평가 축 | REF_LAB | REF_IG |
|---|---|---|
| 참조 방향 외형 | 검고 두꺼운 몸통의 Lab 외형 | 회갈색 털·흰 가슴/목·가느다란 주둥이·접힌 귀·가는 사지로 변화 |
| source 전신 자세 | 사족으로 서는 자세 유지 | 말아 누운 몸통·접힌 다리로 참조 자세를 강하게 따름: FAIL |
| 고개 변화 | 후반 화면 왼쪽 방향·대략적 순서 대응 | 후기 왼쪽/아래/자기 몸 뒤쪽으로 움직이나 source의 서있는 고개 궤적 보존은 미입증 |
| 장면 | 타일방·로프·가구·창의 대략적 배치 유지 | source와 유사한 방은 남지만 전경 로프가 사라짐: PARTIAL |
| 형상과 개체 | source보다 매끈한 얼굴/비율 변화 | 검은 Lab 이중 잔상은 없고 큰 얼굴 붕괴는 두드러지지 않지만 세부 동일성은 미확인 |

두 결과가 단순 색상만 다른 것은 아니다. IG의 관측 무늬·귀·주둥이·사지 비율이 함께 나타나므로 **참조 묶음의 외형·자세 반응**에 근거가 있다. 그러나 IG의 누운 참조 자세가 유지되어 원본 사족 기립과 앞발/지지발 배치를 전달하지 못했다. 따라서 appearance 반응과 joint motion-transfer FAIL을 함께 기록한다. 머리가 나중에 왼쪽으로 움직였다는 것만으로 source의 궤적·크기·정밀 타이밍까지 맞췄다고 하지 않는다.

REF_LAB의 성공처럼 보이는 부분은 same-ID source-copy로도 설명된다. REF_IG의 변화는 단순 driving 개체 유지 설명을 약화시키지만 실제 반려견 identity 일치까지 자동 입증하지 않는다. 귀·무늬·체형이라는 외형 반응과 해당 개체의 세밀한 동일성은 다르다. 정확한 pet identity는 UNCERTAIN, temporal은 UNVERIFIED다. 미세 발끝·접촉·가림·flicker도 정적 시트만으로 모두 검증하지 못한다.

원본 장면이 대략 남는 것과 모든 보호 영역이 보존되는 것도 다르다. IG의 전경 로프 손실은 누락으로 남기며 잘된 방 구도만 보고 전체 scene PASS로 올리지 않는다. 참조 support·RGB·pose·사진 품질을 함께 바꿨으므로 결과를 RGB-only 또는 identity-only 인과효과로 부르지 않는다. 어떤 encoder나 mask 경로가 누운 자세를 지배했는지도 이번 pair로 분리하지 못한다.

## 다음 검증 가설 하나

**동일 IG 개체의 reference 자세가 driving의 전신 자세 전달을 좌우하는가?** 기존 누운 reference와 적법하게 사용 가능한 동일 IG의 자연스러운 기립 reference를 같은 source·중립 caption·noise·모드·sampling 조건에서 비교하는 한정 실험을 제안한다. 실제 그런 reference가 확보돼 있다고 가정하거나 이번에 요청·수집·생성을 시작하지 않는다. 동일 개체를 유지하면 identity 차이를 줄일 수 있지만 사진 시점·support·조명·보이는 부위도 바뀔 수 있으므로 완벽한 pose-only 인과 분리는 아니다. 다음 실험은 이 변경을 기록하고 서있는 모습만이 아니라 원본 고개/사지의 방향·순서와 장면 보존을 함께 평가해야 한다. 추가 seed·학습·모델 변경을 자동 실행하지 않는다.

## 이해 확인 질문

1. 출력이 source 파일과 다른 pixel이라면 reference를 사용했다는 증거가 되는가?
2. 왜 B-024 결과를 새 IG 결과의 정확한 대조군으로 사용하지 않는가?
3. IG 사진 조건에서 털색이 바뀌지만 Lab의 넓은 몸통과 얼굴이 남으면 어떻게 기록해야 하는가?

## 별도 해설

1. 아니다. 재인코딩·생성 과정에서도 source 개체를 거의 그대로 재구성할 수 있다. 파일 계보는 입력 대체 오류 검증이고 reference 기여는 별도 통제 비교의 질문이다.
2. B-024는 외형을 지정한 caption이고 이번 pair는 공통 중립 caption이다. 둘 사이를 ref-only 차이라고 하면 text 변화가 섞인다. 같은 $P^*$로 Lab/IG 두 출력을 새로 비교한다.
3. appearance PARTIAL로 기록하고 실제 pet identity·체형 교체는 미입증 또는 실패로 구분한다. motion과 scene이 유지되는지는 다시 별도 축으로 기록한다. 출력 변화 자체를 identity 성공으로 승격하지 않는다.

# B-015 — ALG × driving 대조군 완성과 경로 결정

작성: 2026-10-24 · parent: B-013/B-014 · 상태: **PLANNED / NOT_RUN**

계획의 원격 등록은 GPU 실행이나 예산 사용이 아니다. 사용자가 실행 담당자에게 본 계획 수행을 지시할 때 아래 한정 범위를 적용한다. 기존 B-014의 sampler1회·B-013의2회 및 실패·미수용 기록을 보존한다.

## 0. 연구 방향과 현재 결론

B 트랙의 장기 목표는 DGX Spark급 로컬 자원으로 이미지·영상 생성의 모델/아키텍처/메커니즘을 이해하고 개선하여 높은 생성 품질과 검증 가능한 연구 기여를 얻는 것이다. A(native imagegen-only MCP)는 동결하며 B에는 외부 생성 API를 넣지 않는다.

기준 결과 commit은 `14afab19df2d9b464b3d6685e24747a675ac9660`이다. B-014 RESULTS/ADAPTATION_AUDIT 및 `code/alg.py`, `code/alg_runtime.py`를 원격에서 읽었다. 정확한 ALG3항식·공간 필터·초기8step와 실제40step/88forward 실행은 보고됐으나, 전신 직립 FAIL·후반 얼굴/귀 손상 지속·실제 개체 UNCERTAIN으로 목표 품질 개선은 NOT_ESTABLISHED다. 이식 검증과 성능 수용은 별개다.

이번 계획 작성 세션은 업로드 ZIP을 container와 Python으로 읽으려 했으나 ClientError로 실패했다. 크기182,189,796bytes, SHA `d0ec1d69de03d695e5adf421cc43f7fc47b55e663fff3404c17a9fd116e8c589`, CRC/402개 payload·Mac/Spark 일치는 실행 담당자의 보고값이며 독립 검증하지 않았다. MP4/정적 시트/실제 tensor bytes를 직접 확인하거나 Spark 재실행한 것으로 주장하지 않는다.

**이번은 ALG 설정 탐색이 아니라, 남은 대조군1개로 현재 ALG pilot을 마무리하는 연구다.** 저역통과 강도·활성구간·seed를 추가 검색하지 않는다. B-014의 목표 품질 실패를 ALG_STILL의 성공적인 정지 외형으로 뒤집지 않는다.

## 1. 질문과 비교 구성

질문: 같은 Lab reference/text/noise에서 ALG를 적용했을 때의 외형/움직임 변화가 정적인 driving에서도 생기는가, 동적 driving을 함께 줬을 때 주로 나타나는가?

| guidance | MOV | STILL |
|---|---|---|
| 기존 CFG | B-013 LAB_MOV 재사용 | B-013 LAB_STILL 재사용 |
| 고정 ALG | B-014 LAB_MOV_ALG 재사용 | **이번 LAB_STILL_ALG 1회** |

이 네 셀은 한 입력·한 seed의 기술적/서술적 비교다. 17프레임을 독립17표본으로 보지 않으며, 유의성·일반화·새로운 방법의 성능을 주장하지 않는다. MOV/STILL 개입은 RGB+mask의 시간 정보를 함께 바꾸는 것이지 RGB 단독 또는 branch-off가 아니다.

## 2. 재사용·변경 계약

- B-013 LAB_STILL의 실제 `conditions.safetensors`와 sidecar/입력 manifest를 읽기 전용으로 재사용한다. P 재인코딩0. 실제 캐시를 찾고 검증하며 경로·SHA를 추측하지 않는다.
- B-013 LAB_STILL과 B-014 LAB_MOV cache의 실제16leaf 비교에서 양 CFG driving latent/mask4개만 다르고 나머지12개가 일치하는지 확인한다. 원본 cache provenance/stat/hash가 비교 불가능하면 GPU 전에 INPUT_BLOCKED로 기록하며 신규 baseline을 생성해 채우지 않는다.
- B-014 `alg_runtime.py`는 filtered-reference sidecar의 `parent_cache_sha256`을 강제한다. MOV용 sidecar를 STILL에 그냥 붙이거나 검사를 삭제하지 않는다. **STILL cache를 parent로 하는 새 sidecar**를 만들어 알고리즘/filter-code hash·실제 source reference hash·생성 시각과 원본 sidecar 연결을 남긴다. 필터 텐서는 동일 reference+동일 CPU 코드로 생성한 동일 값이어야 하며 이전 MOV sidecar/캐시를 덮어쓰지 않는다.
- B-014 원본 reference 값 hash `0ad957276e89e5692743ee9d8438044fe37daa48500c311746ccd949e93703c0`, filtered 값 hash `40e6a0c2132cfc19f0a211a8cc654b21425e681b58cd45472656f3191454abda`와 비교한다. 실제 환경/값이 맞는지 확인하고 맞지 않는 경우 기존 성공값을 기록에 강제로 넣지 않는다.
- RGB Lab 사진·RED/WHITE ref mask·positive text·negative empty·CLIP·noise/RNG·scheduler·weights·precision·attention·P/S/D 경계를 바꾸지 않는다. source f7~23,512×896,17프레임24fps,seed20261022,UniPC40,shift3,CFG5,history=None,replace_flag=False,LoRA/enhancer OFF 유지.

## 3. 고정 ALG와 호출 계약

공식 ALG commit `3657bfd0d408631db2443b491498c44e1cb2e5c6`의 Eq.(2)와 Wan 코드에 맞춘 B-014 이식을 그대로 재사용한다. spatial down-up ratio0.4,bilinear/antialias=True/align_corners=False,reference[16,1,112,64]의 공간45×26→112×64. 시간·채널 혼합, clamp, 재정규화 없음.

초기 i0..7:
`prediction = u_orig + 5*(c_low-u_low)`
후반 i8..39:
`prediction = u_orig + 5*(c_orig-u_orig)`

초기는 original-negative,filtered-negative,filtered-positive를 순차 호출한다. 후반은 B-014와 동일한 기존 positive→negative 순서다. 전체40scheduler update·88sample-equivalent DiT forward이며 batch3·추가 counterfactual forward는 금지한다. first-frame overwrite/clamp 없음. 기존 noise time과 video frame time을 구분한다.

CPU에서 parent binding·cache 불변·다른 조건 불변·88call/40step 예상값·필터 해시·비활성시 기존 경로를 검사한다. 기존 B-0149fixture를 재사용하고 sidecar parent 차이를 위한 최소 테스트만 추가한다. 새로운 승인 상태기계·MCP·대형 리팩터링·전수 타입 부채 해결은 이번 범위가 아니다. NOT_CLEAN 이력은 유지하고 핵심 변경 영향 검사는 수행한다.

## 4. 실행 범위·안전·원본 보존

- 신규 encoder P0, PROBE최대1회, S(full sampler 실패 포함)최대1회, 해당 final latent D최대1회. 재시도0,새 seed0,기존3셀 재생성0.
- 전체 작업 상한3시간. 기존 정상 tinyCUDA/anchor·mixed loader·FA·fresh worker·S 종료 후 D 로딩·최종latent 원자저장을 유지한다. 원본 checkpoint 재다운로드/변환/학습/LoRA/imagegen/외부API0.
- 이전72GiB 시작/24GiB runtime headroom·swap0·cgroup/다른 서비스 보호 정책 유지. 현재 자원과 guard를 검증하고 deadline/unit명만 현재 작업에 맞게 갱신한다. 타 프로세스 종료,가드 완화,drop_caches,sudo/driver/swap/clock 변경 금지.
- 디코딩이 실패해도 저장된 final latent를 보존하며 sampler를 다시 실행하지 않는다. 시도·실패·정상종료를 각각 기록한다. 생성 실행 중 실제88branch와40step·finite/readback을 검사한다. 결과가 나쁘다는 이유로 제외하지 않는다.

## 5. 평가와 해석

SOURCE/실제Lab reference/기존CFG_MOV/CFG_STILL/ALG_MOV/새ALG_STILL을 동일24fps·공통canvas로 비교하고 전체17프레임 및 사전 local0/12/14/16을 포함한다. posterior 좋은프레임 선별·warp·얼굴복원·업스케일·보간·속도변경 금지.

각셀에서 별도로 판정:
1. 전신: 착석/직립·앞발배치(단순 머리움직임으로 직립성공 금지).
2. 동작: 원본 후반 head roll의 방향·순서·시점(움직임 크기/flicker와 구분).
3. 형상: 눈·귀·주둥이·목/몸통 손상, 손상 시작 시점과 invalid/가림.
4. 개체/체형: 검은Lab 견종 인상과 실제 반려견 일치를 분리.
5. 비용: 40step80대88forward,같은 정의의sampler시간·전체시간·메모리·추가비용.

해석 예:
- 두ALG셀에서 비슷한 외형 변화/손상이 나타남 → 해당 변화가 동적 driving을 필요로 하지 않는다는 단일사례 근거. 보편 원인/특정 신경망 경로 증명 아님.
- STATIC계열은 상대적으로 안정적이고 두MOV에서 손상 → 이 입력의 동적 전이에서 어려움이 나타난다는 근거. reference가 유일한 원인이라는 결론은 아님.
- ALG_STILL에서도 비슷한 머리움직임이 생김 → ALG_MOV의 움직임 증가를 source 추종으로 간주하지 않음.
- 결과가 미세/상충/관측 불확실하면 INCONCLUSIVE. 관절각도·접촉·고정밀 gain을 지어내지 않는다.

q가 의미 있게 측정된 경우에만 설명용 interaction
`I=[q(ALG,MOV)-q(ALG,STILL)]-[q(CFG,MOV)-q(CFG,STILL)]`
을 사용할 수 있다. 이번에는 독립 q가 없으면 정성적2×2 표만 사용한다. 시간/지점/픽셀을 독립시행으로 세지 않고 유의성 계산 금지. 연속 재생을 실제 관찰하지 못하면 temporal=UNVERIFIED 유지. 실행자가 review.html의 기능검사를 사람 지각검수로 주장하지 않는다.

## 6. 이론·메커니즘 학습

`lessons/B-015-guidance-driving-interaction.md`에 직관→수식→실제코드→관측→한계→질문/해설을 기록한다.

같은 noisy latent z, noise time tau, driving D에서 u_R=v(z,tau,R,c_neg,D),c_R=v(z,tau,R,c_pos,D),L=LP(R)로 두면
`v_CFG=u_R+w(c_R-u_R)`
`v_ALG=u_R+w(c_L-u_L)`
`v_ALG-v_CFG=w[(c_L-u_L)-(c_R-u_R)]`.

이것은 **같은 z에서의 대수식**이다. ALG와CFG의 실제 생성 궤적은 첫개입 이후 달라져 서로 다른 z에서 예측하므로 두 실행의 branch norm을 빼서 이 차이를 실측했다고 주장하지 않는다. 원래u_R·CLIP·mask 경로가 남고 저주파 큰 착석 실루엣이 유지될 수 있어 '참조 전체 제거'나 '자세 전용 제거'가 아니라는 한계를 설명한다. positive/negative에서 비슷한 변화는 차분에서 줄어들 수 있지만 실제로 그렇게 됐다는 증거는 이번 로그만으로 부족하다.

B-014 alg_runtime은 branch별 prediction_norm을 저장하지만 활성구간 c_orig counterfactual이나 전체벡터내적을 저장하지 않는다. norm값만으로 cosine/상쇄/정체성 loss 기여를 산출하지 않는다. 추가 forward나 재생성 없이 존재하는 정보만 요약한다.

원논문은 I2V의 dynamic degree 문제, 우리과제는 서로 다른 사진의 개체·초기자세를 유지/변환하면서 RGB driving의 정확한 동작을 따르는 문제라는 차이를 명시한다. 이 이식/음성 결과 자체를 독창적1티어논문이라고 부르지 않는다.

## 7. 사전 종료·전환 규칙

이2×2를 완료하면 **현재 ratio0.4/초기20% ALG pilot 비교는 닫는다**. ALG_STILL의 결과만으로 B-014의 목표품질 실패를 성공으로 바꾸지 않으며, MOV에서 이미 목표개선이 없으므로 현방법을 제품 기본값으로 승격하지 않는다. 추가seed/강도/구간/LoRA/SR/새모델을 자동실행하지 않는다.

후속은 결과기반으로 한 연구만 제안한다. 기본 방향은 reference의 큰 공간배치·자세 정보와 개체 세부/CLIP 정보를 어떻게 구분할지에 대한 명시적 경로 개입 또는 학습 가능한 조건모듈의 가설이다. 기존 입력을 회색/흰색으로 바꾸는 탐색이나 '더흐리게/더오래' 탐색을 무기한 반복하지 않는다. 새 학습은 데이터/목표/실측가능성과 선행연구를 별도 설계한 뒤 실행한다.

## 8. GitHub·자료·완료

시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL, B-013/B-014 RESULTS·코드·ALGconfig를 읽고 PLAN과 실제parent cache/config/hash를 고정한다. 공통HISTORY·ROADMAP에 B-014완료와 B-015의진단목적·종료규칙을 링크한다. 실험 전 코드/config commit/push, 종료 후RESULTS/REPRODUCE/PAIR_AUDIT/한국어lesson/HISTORY/ROADMAP을 갱신하고 remoteSHA확인. 원격HEAD이동·충돌 시 덮어쓰기/force push/reset/clean 금지.

공개는 비민감코드·문서·설정·해시·요약만. 개인영상·사진·mask·좌표·cache·filtered sidecar·latent·weights·비밀값/절대경로는 비공개로 유지한다. 검토ZIP은 새결과·기존3셀의작은비교·raw/latent·sidecar규약·실패/실측·재현을 포함하고 대형weights제외. /tmp/의실제Mac/Spark경로·CRC·manifest·SHA·전송동일성을 구분해 보고한다. 자체프로세스 종료 확인. 계획만 등록하고 실제생성한척하지 않는다.

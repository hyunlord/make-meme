# B 연구 v2 — 원본 장면을 보존하는 참조 이미지·프롬프트 기반 영상 객체 편집

## 2026-10-26 최신 실행 방향 — 공개 다중 사례의 객체 편집

최종 목표는 특정 반려견 전용 모델이 아니라 다양한 대상의 참조 기반 원본 보존 영상 편집이다. 개인 자료는 회귀 사례로 보존하며 전체 연구의 실행 선행조건으로 삼지 않는다. B-026은 OPTIONAL_REFERENCE_DIAGNOSTIC / REFERENCE_PENDING으로 유지하고 새 개인 촬영을 요구하지 않는다.

[B-027](experiments/B-027-public-reference-robustness/PLAN.md)은 공개 DAVIS 자료에서 최대3개 source/target 과제와 같은 target의 두 참조를 고정하는 탐색적 개발 패널이다. SCAIL replacement와 비객체 RGB128을 유지하고 최대6회 실제 출력의 외형·동작·장면·형상·비용을 분리한다. mask-given 평가이며 자동 추적·일반화·논문 benchmark를 입증하지 않는다. 과거 B-023~025의 개선과 실패는 보존하고 다음 방법은 이번 결과를 보고 하나만 선택한다.


작성: 2026-10-24. 실행 범위 개정: 2026-10-25. 과거 두 생성·밈 입력·ROI 후보는 Git 이력에 보존한다. 현재 실행 계약은 [B-023 개정 계획](experiments/B-023-task-aligned-replacement/PLAN.md)이며, 상위 구성 전체를 구현하는 작업이 아니다.

## 1. 목적과 범위

입력은 원본 영상 V, 객체별 참조 이미지 집합 R, 편집 지시 P다. 출력 Y는 지시한 객체를 참조의 개체·체형으로 바꾸되 원본의 시간축·카메라·보호 영역과 지정한 동작/이벤트를 유지해야 한다. 목표 하드웨어는 사용자의 단일 DGX Spark다. 대형 서버·유료 영상 생성 서비스가 아닌 로컬 모델로 품질과 자원 효율을 검증한다.

장기 범위는 객체 단위 삽입·치환·합성이다. 첫 B-023은 **같은 실제 Lab의 다른 자세 참조를 사용한 정식 replacement 과제 적합성 진단**이다. source-copy와 reference 사용을 구분할 수 없어 identity-changing replacement 검증은 후속 과제로 남긴다. 사람/동물용 모델의 성과를 자동차·제품 등 모든 객체로 일반화하지 않는다. 처음부터 새 동작 발명, 전체 장면 재생성, 2개체15초, 음성 합성까지 동시에 요구하지 않는다. 원본의 동작을 보존하는 편집과 새로운 행동을 추가하는 편집은 별도 과제다.

A(native imagegen-only MCP)는 동결·독립 보존한다. B에는 native imagegen, 외부 생성API, 원격 prompt enhancer, A의 생성물을 넣지 않는다. 개발 에이전트가 코드를 작성하는 것과 최종 로컬 편집 시스템이 실행 중 외부 생성 서비스를 의존하는 것을 구분한다. 기존 입력의 비공개 추론 허용과 학습/공개 배포 권한도 구분한다.

## 2. 현재까지의 증거와 우선순위 변경

검토 기준 연구 HEAD는 `9940848b59d52537194aa7118792efb15ad9a8e8`. B-012 same-reference MOV/STILL은 한 구간에서 동적 RGB+mask의 추가 기여를 관측했다. B-013 실제 Lab은 착석 유지와 MOV 후반 얼굴 손상을 보였다. 고정 ALG와 H120은 품질 개선을 입증하지 못했다. B-018/019는 로컬 backward·LoRA 배선, B-020은 실제 자연동작 영상의 작은 FM tail 학습을 확인했다. 이것들은 실행/학습 기반과 실패 증거이지 상용급 editing 또는 새 알고리즘의 증거는 아니다.

대부분의 기존 품질 실험은 `replace_flag=False`인 animation이었다. 정식 replacement의 전체 입력·마스크·모드 계약과 동일하지 않다. H120만 변경한 B-016도 replacement baseline이 아니다. 따라서 animation 실패만으로 source-preserving editing 전체의 한계를 결론내리지 않는다.

B-022는 완료됐다. optimizer/RNG/cursor 재개와 추가80update, matched20/100 영상 확보는 PASS이나 착석·후반 얼굴 손상·잘림이 남아 품질 개선은 NOT_ESTABLISHED다. B-021 FAIL을 보존하며 같은 마지막block Q/V·고정tuple 학습량 확대는 종료한다. 다음은 실제 Lab 자연동작 f126..142의 같은 입력에서 공식 replacement 모드와 의미 마스크를 함께 맞추는 1회 비교다. 원인이 조건 불일치라는 가설은 아직 미검증이다.

## 3. 편집 계약 — 자연어와 모델 caption을 분리

사용자 지시를 EditSpec으로 구조화한다. 초기에는 사람이 확인한 작은 JSON/YAML로 충분하고, 별도 agent framework나 새 LLM 설치를 먼저 하지 않는다. 향후 자동 parser는 로컬에서 실행하며 uncertain 역할 연결은 사용자 수정 가능하게 한다.

필수 정보: source track ID, target reference ID 목록, 객체별 작업, 유지할 동작·이벤트 시각, 허용 체형 변화, 보호할 다른 객체/장면, 시간축, 편집 가능한 영역과 자원 예산.

예시:

```yaml
operation: replace_subject
objects:
  - source_track: lead_dancer
    target_reference: lab_01
    preserve: [motion_timing, trajectory]
    allow: [body_width_change, limb_thickness_change]
  - source_track: secondary_dancer
    target_reference: ig_01
preserve: [camera, shot_cuts, audio, unedited_objects]
events:
  - event: source_wink
    assigned_target: lab_01
    time: source_timestamp
constraints:
  invent_missing_events: false
```

이벤트는 원본에 실제로 있는 것을 기준으로 하며 번호나 timestamp를 지어내지 않는다. 모델에 전달하는 caption은 결과 영상 자체를 서술한다. SCAIL 공식 README도 편집 명령문과 generated-video description을 구분한다. parser 정확도와 generator의 시각적 편집 성공은 별도 평가한다.

## 4. 제안 시스템 — source-preserving editing을 원칙으로, 구현 방식은 비교

경량 입력/역할 확인 → shot/track/mask와 보호 영역 → 참조 기반 시간 일관 생성 → 필요한 영역만 장면에 반영 → 검토·출력.

### 4.1 최소 분석

첫 baseline의 필수는 source frame/PTS, 대상 track, semantic correspondence mask, 참조 identity, 역할 명세다. 모든 사례에 pose·depth·flow·3D를 동시에 요구하지 않는다. 가림 실패에는 occlusion ordering, 카메라/경계 문제에는 flow 등을 필요한 경우에만 추가한다. 분석 모델도 비용이 있으며 ARM/CUDA 호환·실제 메모리를 따로 측정한다. 자동화 이전에 제한된 수동 mask/track으로 생성기의 능력을 시험할 수 있다.

### 4.2 첫 생성 backend

이미 구동한 SCAIL-2의 **공식 replacement 모드 전체**를 먼저 사용한다. 기존 P→PROBE→S→D, mixed precision loader, tiny CUDA 선행, 조건 캐시와 final latent 보존을 재사용한다. ALG OFF, 임의 RoPE override OFF, B018~022 adapter OFF다.

reference 배경은 원본 장면과 무관하고 target source의 배경은 보존해야 한다는 의미를 official mask 계약으로 표현한다. 색상 semantic mask와 alpha matte는 다르다. animation cache의 bool 하나만 바꾸거나 H120만 적용하고 replacement라고 부르지 않는다.

공식 backbone 출력은 RGB다. RGBA/정확한 alpha/depth를 자연스럽게 출력한다고 가정하지 않는다. 해당 출력이 필요하면 별도 matting/추정 또는 학습된 헤드가 필요한 후속 연구다.

### 4.3 국소 재합성의 정확한 의미

source V_t, generator의 edited RGB G_t, 편집 가중치 E_t라면:

`Y_t = (1-E_t)*V_t + E_t*G_t`.

E는 객체 alpha가 아니라 **어디를 편집 결과로 교체할지 나타내는 edit support**다. E=0인 raw pixel 영역은 source를 정확히 보존할 수 있다. 그러나 이것만으로 객체 교체 성공이나 계산량 감소를 입증하지 않는다.

edit support는 source 객체 영역뿐 아니라 target의 새 실루엣, 지워진 객체가 있던 배경, 경계 전이, 필요한 그림자/반사를 포함할 수 있어야 한다. source가 target보다 작거나 클 때 source mask만 사용하면 잘림·잔상·빈 영역이 생긴다. 앞을 가리는 보호 객체는 원래 순서를 유지한다. target 체형을 원본 silhouette에 비선형 warp로 강제하지 않는다.

객체만 alpha로 덮으면 source 객체가 남아 있거나 가려졌던 배경이 비어 있을 수 있다. clean plate/inpainting 또는 edited-region RGB가 필요한 이유다. 이번 B-023에서는 **정식 replacement의 raw RGB만** 판정한다. 제한된 source 복원·ROI 합성·pure foreground-layer 생성은 관측된 실패에 따라 선택할 후속 후보이며 이번에는 실행하지 않는다.

### 4.4 계산량에 대한 정정

mask 밖 loss를0으로 하거나 결과에 alpha를 붙여도 dense DiT의 전체 token 수는 자동으로 줄지 않는다. 실제 효율 개선은 ROI/공간해상도 축소, 검증된 sparse computation, context reuse, fewer-step/distillation, staged memory 등의 실행 변화와 실측으로 입증한다. 고정512p 모델에서 작은 ROI를 다시512p로 키우기만 하면 토큰 절감이 없을 수 있다.

ROI에는 객체뿐 아니라 가림·바닥·조명 문맥을 충분히 포함한다. frame마다 흔들리는 crop을 쓰지 말고 shot-level 좌표와 가역 mapping을 고정한다. 필요한 context를 잃어 품질이 내려가면 효율성 성공이 아니다.

## 5. 수학적 연구 목표

`Y = F_theta(V,R,P)`에서 동작/정체성/장면보존/시간 품질의 제약을 만족하며 전체 비용 C를 줄이는 문제로 본다.

`min C_total`, subject to `Q_identity, Q_motion, Q_preservation, Q_temporal >= preregistered acceptance`.

C에는 분석·mask 수정·인코딩·모델 로딩·생성·복원·합성·인코딩·실패 재시도·사람 수정 시간을 포함한다. masked generation 면적만으로 비용을 주장하지 않는다. 허용 변화 밖의 pixel 보존은 강한 제품 제약이지만 source-copy는 이를 trivially 만족하므로 identity-change 성공을 동시에 요구한다.

학습을 다시 할 때 target은 작업 모드와 일치해야 한다. source-scene-preserving editing target과 reference-scene animation target을 섞어 loss를 줄이지 않는다. paired target이 없을 때 원본 다른 동물 영상을 target identity 정답으로 선언하지 않는다. 연구 사용 가능한 역방향 driving/렌더링 pair/사전학습을 검토하되 기존 방법과 구분한다. B020의 D=Y smoke는 실제 FM 배선 증거로만 보존한다.

## 6. 결과를 기준으로 진행하는 로드맵

| 단계 | 핵심 질문 | 요구 산출물 |
|---|---|---|
| R0/B-023 | 정식replacement가 실제 task를 얼마나 수행하는가? | 실제Lab 자연동작의같은개체replacement1회, B020adapter-OFF와raw비교, 합성0 |
| R1 | 한개체에서 제어·개체·장면을 함께 보존하는가? | 같은개체의 다른ref자세·다른짧은동작, source-copy와작업맞춤baseline 비교 |
| R2 | 무엇을 작게 바꾸면 joint quality가 올라가는가? | 한가지조건/데이터/학습개입과 제거비교; 준비검사만확장금지 |
| R3 | 같은품질에 비용을 줄이는가? | native generation 대 실제low-res/ROI+refinement, end-to-end 시간·메모리 |
| R4 | 길이·가림·두배역으로 확장되는가? | 먼저수초 단일개체, 이후두개체·역할교차·15초; chunk경계실패 포함 |
| R5 | 재현·일반화·서비스·논문에 충분한가? | 고정test identities/scenes/motions, 강한baseline, 자원맞춤평가·공개가능코드 |

날짜만 채우는4주/8주 일정 대신 위 증거를 통과해야 범위를 넓힌다. 다만 완벽한 pose ground truth나 byte-identical 독립 학습 재현을 첫 탐색 출력의 필수조건으로 걸지 않는다. 입력계약·저장/복원·실제 finite·안전은 엄격하고, 관측상 불확실성은 관측결과와 함께 기록한다.

## 7. DGX Spark 자원 계획

단일 GB10/현재128GB 통합메모리 환경을 기본으로 하되 실제 장비의 fresh MemAvailable·disk·CUDA환경을 사용한다. NVIDIA 공식273GB/s 메모리 대역폭이나 FP4 peak를 BF16영상처리량으로 환산하지 않는다. CPU offload는 다른 물리GPU로 보내는 것이 아니며 CPU/GPU 메모리 회계를 중복 합산하지 않는다.

첫 B023은 기존 모델만, 한 worker씩 순차, 신규 full sampler 최대1회·40step80forward, 학습0·추가다운로드0. 기존72GiB 시작/24GiB headroom·swap0·서비스보호 규칙을 유지한다. 향후 실제 baseline 시간을 기준으로 하루/주간 trial budget을 정하고, 생성0회인 감사에만 연구시간이 누적되지 않게 한다.

측정은 CUDA allocated/reserved, OS가용/RSS, cgroup charge/events, 경과시간, sampler NFE, 데이터/캐시 storage를 각각 남긴다. one-block5.816GiB나 현재짧은clip 비용을 전체40block학습·15초로 단순 선형외삽하지 않는다. cold/warm 실행을 구분한다.

## 8. 평가 계약

기술실행 PASS와 시각적 task PASS를 나눈다. 필수 축은 target 개체/체형, source 동작·event timing, 보호배경/다른객체, 경계·가림·접촉/그림자, 시간적일관성, role mapping, 전체비용이다.

원본 복사와 참조 첫프레임 반복을 무료 trivial baseline으로 둔다. 높은 배경점수·낮은flicker만으로 source-copy를 성공으로 세지 않는다. CLIP/DINO similarity는 있는모델을 쓸 때도 보조값이며 실제 반려견 식별과 동일하지 않다. cross-body motion은 source joint pixel 좌표 완전일치가 아니라 사전동작방향/순서/접촉·허용체형으로 평가한다.

edit footprint E를 포함한 모든확장영역을 공개가능요약으로남기고, 결과를본뒤경계를좁혀오류를제외하지않는다. outside-E raw 보존·자동mask품질·고정원본객체밖 drift·E면적을구분한다. raw RGB의 bit equality와 손실압축MP4 재decode의pixel차이를구분한다. alpha 합성으로만얻은outside-E점수를모델능력으로주장하지않는다.

원본/reference/raw/final, 전체frame sheet, native속도단회재생을 제공한다. 실제사람연속검토 주체/항목이없으면 temporal=UNVERIFIED로둔다. 재생버튼검사와지각검사는다르다. 첫 pilot은 정성판정가능; 정량이불확실하다는이유로출력자체를무한보류하지않는다. 논문평가는블라인드paired 사람평가, 복수seed/identity/scene/motion, 데이터출처그룹분할·오차범위로확장한다.

## 9. 논문 위치 — 현재는 가설이고 구현기능 자체가 기여는 아님

기존 VideoSwap은 shape-changing subject swapping, VideoAnydoor는 reference identity·trajectory기반 insertion, AnyV2V는 첫프레임편집+temporal feature주입, VideoPainter는 context제어 video inpainting을 이미 다룬다. SCAIL도 replacement를제공한다. 따라서 '객체만생성해서합성', 'MCP로연결', 'LoRA사용'만으로새로움주장금지.

주력 후보는 **체형변화·가림·재노출에 따라 edit support와 생성자원을 조절하면서 외형·동작·장면 보존을 함께 유지하는 방법**이다. 고정dilation+feather/풀프레임baseline보다 같은비용에서낫거나 같은품질에서싸다는증거가필요하다. 이것은 미검증가설이며 baseline실패원인이identity라면 먼저그기제를연구한다.

보조 후보는 reference-pose robustness, foreground/context계산분리, 장구간identity메모리다. 한 번에세방법을합쳐효과를주장하지않는다. 논문주장은 특정편집task·정의된quality/cost budget에 한정한다. 상용모델보다낫다는말은동일입력·다양한반례·충분한비교없이쓰지않는다. 기존사용자가허용한상용결과는정성참고가능하지만새유료호출은하지않고학습target으로사용하지않는다.

## 10. 공부·구현·기록 운영

각실험은 한글로 핵심질문,직관,수식/가정,실제tensor/코드,측정,반례와다음결정을남긴다. 모든실험마다같은교과서·거대감사체계를복제하지않고직접연결된1~2개주제를깊게다룬다.

v0는 CLI+작은JSON명세+기존viewer면된다. 자동프롬프트parser/MCP는로컬코어의편집성공후얇은wrapper로붙인다. 외부호스트가자연어명세를만들더라도생성엔진과런타임은로컬이어야하고,완전로컬제품이라면parser도로컬이어야한다.

CHARTER/ROADMAP/HISTORY와실험별PLAN/RESULTS/lessons/decisions를연결하고실행전변수·상한을고정한다. 현재단일방향문서와B023을권위있는새우선순위로참조하되과거상태는삭제하지않는다. 개인사진·영상·실제경로·latent·adapter·weights는비공개이며일반계획/비민감코드/해시만GitHub에기록한다.

## 공식 근거와 검토 범위

검토일2026-10-24. 아래자료의기능설명은설계참고이며Spark재현성·품질을직접시험한것은아니다.

- SCAIL 고정코드/모드/학습: https://github.com/zai-org/SCAIL-2/tree/78fe19576bb06be96c2375e088574a262a300edb
- VideoSwap: https://arxiv.org/abs/2312.02087
- VideoAnydoor: https://arxiv.org/abs/2501.01427
- AnyV2V: https://arxiv.org/abs/2403.14468
- VideoPainter: https://yxbian23.github.io/project/video-painter/
- Spark hardware: https://docs.nvidia.com/dgx/dgx-spark/hardware.html

이번작성은원격계획/코드와공식문헌검토다. 기존ZIP미디어를재생해새품질판정을한것이아니고실제GPU·데이터수집·학습·다운로드를실행하지않았다.

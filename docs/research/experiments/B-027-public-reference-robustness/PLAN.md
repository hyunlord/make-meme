# B-027 — 공개 다중 사례에서 참조 자세·시점에 대한 편집 강건성 비교

실행 후 안내: 이 문서는 사전 등록 당시 상태를 보존한다. 최신 종료 결과는 [RESULTS](RESULTS.md), 다음 제안은 [NEXT_DECISION](NEXT_DECISION.md)이다. 아래 GPU NOT_RUN은 등록 시점의 기록이다.

작성: 2026-10-25. 상태: **PLANNED / DATA_SELECTION_NOT_RUN / GPU NOT_RUN**.
기준 연구 HEAD: `84e00dc28691c64cc84ed667b29b2de31f6d688f`.
이 문서 등록은 자료 다운로드·모델 실행을 의미하지 않는다. 사용자가 실행 담당자에게 수행 지시를 보낼 때 아래 범위를 적용한다.

## 1. 상위 목표와 이번 결정

목표는 특정 반려견 전용 모델이 아니라, 원본 영상 V + 참조 이미지 R + 프롬프트 P로 대상 객체를 교체하면서 지정된 동작·장면·시간축을 보존하는 방법을 단일 DGX Spark에서 연구하는 것이다. 사용자 사진은 회귀 사례로 보존하지만 주 개발 데이터나 실행 선행조건으로 삼지 않는다. A(native imagegen-only)와 B(local-model-only)는 독립이다.

B-026의 기립 IG 사진 비교는 OPTIONAL_REFERENCE_DIAGNOSTIC / REFERENCE_PENDING으로 보존한다. 개인 사진이 없다는 이유로 전체 연구를 DATA_PENDING으로 두지 않는다. 사용자에게 새 촬영·개인사진 제출을 요구하지 않는다. B-024의 배경 RGB 분리 개선과 B-025의 외형 반영/자세 복사를 지우거나 일반화된 결론으로 올리지 않는다.

이번에는 새 학습이나 임의의 조건 스케일을 추가하지 않는다. 이미 작동하는 **SCAIL 정식 replacement + 비객체 RGB128**을 고정하고, 공개 자료에서 서로 다른 source/target 인스턴스와 참조 자세·시점으로 작동 범위를 본다. 단순 자료 감사가 아니라 **조건이 준비된 사례의 실제 생성과 비교 결과**가 필수 산출물이다.

## 2. 핵심 질문과 실험 단위

서로 다른 3개 편집 과제 i에 대해 source V_i와 target 인스턴스 B_i를 선택한다. B_i의 두 참조 R_i1,R_i2는 같은 공개 영상의 같은 연속 track에서 뽑되 자세 또는 시점이 눈에 띄게 달라야 한다. source의 인스턴스 A_i와 target B_i는 구분 가능해야 한다.

`Y_i1 = F(V_i, R_i1, P_i; epsilon_i)`
`Y_i2 = F(V_i, R_i2, P_i; epsilon_i)`

같은 과제 안에서는 source·caption·noise·설정이 같고 reference bundle만 달라진다. 원하는 성질은 두 결과가 target의 외형을 유지하면서 모두 source의 동작을 따르는 것이다. 두 결과의 모든 RGB가 같아야 한다는 요구는 아니다. 사진의 조명·가림·시점·mask도 함께 변하므로 순수 pose 하나의 인과효과라고 부르지 않는다.

실험 단위는 **3개의 paired task**다. 6개 출력·102개 프레임을 독립 6회·102회 실험으로 취급하지 않는다. 한 seed씩의 탐색적 개발 패널이며 논문용 독립 test/일반적 성공률/새 benchmark 기여가 아니다.

## 3. 공개 자료를 실행자가 직접 확보

우선 DAVIS 공식 TrainVal 프레임·instance masks를 사용한다. 원본·target reference를 다른 sequence/track에서 선택할 수 있고 target 참조 둘은 같은 target track에서 얻는다. 교체 정답영상 Y가 없더라도 추론 평가를 할 수 있다. 원본 영상을 교체 후 pixel GT로 둬서는 안 된다.

공식 출처:
- https://davischallenge.org/davis2017/code.html
- https://davischallenge.org/
- 데이터 라이선스 표기: 공식 사이트 저장소 `davisvideochallenge/davisvideochallenge.github.io`의 index.html에 CC BY-NC 4.0 명시. 연구용 평가와 제품·상업 사용을 구분한다.

DAVIS가 접근 불가능하거나 필요한 과제가 없으면 VPBench의 적절한 소규모 공개 subset 또는 사용 범위가 명시된 다른 공개 자료를 검토한다. 소프트웨어 LICENSE가 media 권한까지 뜻한다고 가정하지 않는다. 공개 접근 가능성과 학습·재배포·상업 이용 권한도 구분한다. VPBench는 segmentation/inpainting/editing 자료이며 제공 사실만으로 cross-ID 정답 pair나 모든 영상의 동일 이용 조건을 가정하지 않는다.
- https://huggingface.co/datasets/TencentARC/VPBench
- https://github.com/TencentARC/VideoPainter

이번 새 허용 범위는 **공개 데이터 다운로드 최대5GiB(누적 전송량)**다. 기존의 실험별 다운로드0 제한을 그대로 적용해 데이터 준비를 막지 않는다. 신규 대형 모델·패키지 설치는0이다. 자료 전체를 미러링하지 말고 필요한 공식 archive/subset부터 확보한다. 기존 환경과 별도 data root를 쓴다.

가입·이메일·신청·토큰 제공·접근제어 우회가 필요한 자료는 이번 의존성으로 채택하지 않는다. 한 제공처가 막히면 다른 공개 후보를 사용한다. 적합 자료가 일부만 있으면 가능한 pair를 실행하고 미충족 범위를 기록한다. 원천 자료 모두에 실제 접근/사용범위 문제가 있을 때만 구체적인 외부 장애로 보고하며 개인 반려견 사진을 요청하는 분기로 되돌아가지 않는다.

Manifest에는 dataset/revision/sequence/track/frame 번호, source와 target 구분 근거, 출처·이용 조건, 공개 가능 범위, 해시, 처리 해상도·시간축을 남긴다. 데이터셋 제공권과 개인의 신원을 임의로 확정하지 않는다. 공개 track ID는 실제 개인·반려동물의 생체 신원 인증이 아니다.

## 4. 사례 선정 — 출력 보기 전에 고정

목표 구성:
1. 비강체 동물→다른 동물 인스턴스. 가능하면 같은 종류에서 외형이 구별되는 교체.
2. 사람/인간형 캐릭터→다른 인스턴스. 정상적인 비민감 행동만 사용한다.
3. 차량 등 강체 객체→다른 인스턴스. 이는 character 모델의 도메인 확장 탐색이며 실패를 지원영역과 구분한다.

최대12개 input 후보만 검토하고, 각 층에서 먼저 적합한 task를 고정한다. 특정 종류의 자료가 없으면 다른 독립 인스턴스로 대체하되 대체 이유·범위 축소를 명시한다. 성공 출력이 나올 때까지 쉬운 자료로 바꾸지 않는다. 최소2개 공용 task가 준비되면 한 범주의 부족 때문에 전체를 멈추지 않는다.

각 source는 컷 전환 없는 연속17프레임, 한 대상이 식별되고 관측 가능한 동작이 있어야 한다. 극단적인 가림·대형 카메라 회전은 첫 패널에서 제외하되, 목표 reference 둘을 모두 source와 같은 자세로만 고르지 않는다. 서로 다른 자세/시점이 실제로 있는 target track를 선택한다. '서 있는 특정 IG' 같은 특수 입력은 필요하지 않다.

참조 두 장은 target track의 연속 인접 프레임 복제 대신 가시적 자세/시점 변화가 있는 프레임을 선택한다. target과 source가 같은 파일·같은 개체인 self-copy 조건을 cross-ID라 부르지 않는다. 두 target 참조의 실제 관측 특징과 한계도 기록한다.

프레임 시퀀스만 제공되고 원래 FPS/PTS를 확인할 수 없으면 `source_fps=null / preview_fps=24 / timebase_assumed=true`로 명시한다. 이 경우 평가는 프레임 순서와 정규화된 clip time 기준이며 native 초 단위 동작 타이밍을 보존했다고 하지 않는다. 실제 FPS가 있으면 그것을 사용한다. 소리·프레임 보간·숨은 frame skip은 사용하지 않는다.

모델 입력은 기존 검증된512p 수준, 총 공간 면적을 키우지 않는 landscape896×512 또는 portrait512×896 중 source에 맞춰 선택한다. 같은 task의 두 run은 동일 shape·aspect-fit 규칙이다. 동일한 정적 source canvas를 유지하고 crop/개체 warp로 목표를 쉽게 만들지 않는다. 입력을 확대해도 새 고해상도 관측이 생겼다고 하지 않는다.

## 5. 모델·조건 고정

기존 검증된 SCAIL checkpoint/upstream/메모리 실행 경로를 재사용한다. 새 backend를 동시에 설치하지 않는다. SCAIL은 이번 기준선이지 최종 보편 모델로 확정한 선택은 아니다.

정식 replacement=True, history/additional_ref=None, adapter/ALG/manualRoPE OFF, UniPC40step·shift3·CFG5, negative empty, seed20261022를 사용한다. 한 task 내 실제 initial noise·generator state·scheduler는 같게 맞춘다.

각 reference는 resize 후 target support 안 RGB를 보존하고 바깥/padding을128로 채운다. semantic reference mask는 RED/BLACK, source driving mask는 RED/WHITE다. 학습된 segmentation 출력 대신 공개 GT instance mask를 쓸 수 있지만 이는 'mask-given' 기준선이며 자동 선택·추적 성능은 NOT_RUN이다. mask가 일부 부족하면 제한된 CPU 수정을 입력 단계에서 기록한다. geometry·pose를 생성하거나 source silhouette로 비선형 변형하지 않는다.

Caption은 task마다 실제 완료된 영상의 행동·장면과 'reference 대상에 맞는 외형'을 서술한다. 같은 task의 두 참조에는 byte-identical한 caption을 쓴다. 특정 reference 자세·색·세부 외형을 텍스트로 대신 지시하지 않는다. 자연어 편집 지시와 backend caption을 구분한 작은 EditSpec을 저장한다. 새 LLM parser는 만들지 않는다.

참조 두 bundle의 VAE/CLIP/semantic mask만 달라질 수 있다. 그 외 조건은 고정한다. 같은 개체의 사진도 silhouette/가림이 달라질 수 있어 mask 완전일치를 요구하지 않는다. 기존 캐시를 덮어쓰지 않고 필요한 encoder 계산만 수행한다. 전체 파이프라인 감사를 반복하거나 exact GPU 재계산을 새 보편 gate로 만들지 않는다.

## 6. 실행 범위 — 생성 결과까지 수행

- 신규 full sampler 최대 **6회**: 최대3 task ×2reference, 각40step80forward. 실패도1회로계상, retry0.
- 해당 final latent decode 최대6회. source-copy/첫프레임 반복 CPU 기준선은 모델 호출0.
- 새 학습0, 새 가중치/대형 모델/패키지 설치0, 외부 생성/imagegen0.
- 공개 데이터 다운로드 최대5GiB. 입력 준비·선정 목표 상한2시간, 전체 작업 상한8시간. 이는 작업 범위 제한이며 실제 완료시간 예측이 아니다.
- 기존72GiB시작/24GiB headroom·swap0·타서비스 보호·phase별guard를 유지한다. GPU-heavy 단계는 순차 실행한다.
- 같은pair의 첫 결과가 나쁘다는 이유로 둘째를 생략하지 않는다. 진짜 입력 불일치·NaN·안전 문제는 중단한다. 특정case만 손상됐고 공용 코드가 정상이라면 남은 사전선정case는 예산안에서 진행한다.
- 최종 latent를 먼저 저장하고 decode 실패로 sampler를 다시 실행하지 않는다.
- 자료 선정 후 실제 실행 코드/manifest를 고정한다. 실패/비유한값/안전 검사 외에 완벽한 관절 주석·새 identity metric·타입 경고 전체제거를 첫 출력의 필수조건으로 두지 않는다.

## 7. 평가 — 정답 edited video가 없어도 할 수 있는 것

질문은 외형/원본 동작/보호 장면/시간 안정성을 함께 만족하는가이다. 결과를 임의로후처리하지 않는다. ROI합성·SR·보간·얼굴복원·warp0.

각 task에서 출력 전에 다음을 고정한다.
- target을 source와 구분할 관측 가능한 특징2~3개. 범주/색상반영과 실제identity를분리.
- source의 동작 방향·순서 또는 부위 사건2개. target 체형이 다른데 source joint pixel 완전일치를 요구하지 않음.
- 보호할 배경/비편집객체의 대표영역. target silhouette 변화로 생길 합당한 가림·접촉영역과 먼 보호영역을 구분.

전체17frame와실제속도(또는명시한preview속도) single-play·frame step viewer를 제공한다. A/B참조라벨을숨긴보기와전체입력보기를모두제공하고, agent판독을독립사람블라인드평가로부르지않는다. 사람이연속재생을검수하지않으면temporal=UNVERIFIED로남기되미관찰을성공으로채우지않는다.

개체外형, 동작/자세, 장면, 형상/가림, 시간품질을PASS/PARTIAL/FAIL/UNCERTAIN으로각각보고한다. source-copy는동작·배경이좋아도identity-change FAIL, ref정지복사는외형이좋아도motion FAIL이다.

source와edited의전체PSNR을주요편집점수로쓰지않는다. subject는바뀌어야하므로원본이pixelGT가아니다. 보호영역raw오차는보조값이고편집영역면적/위치·인코딩차이를같이남긴다. optional이미지유사도는기존모델이있을때만보조로쓰고동물신원정답이나새metric기여로부르지않는다.

원본public영상은입력자료이지교체후정답영상이아니다. pairGT없다는이유로추론평가를막지않되, 추후supervised학습에는별도의target설계가필요하다. source/target track별분할과고정개발패널을남기고이자료를나중에튜닝한뒤독립test로재명명하지않는다. 기반모델의pretraining중복은UNKNOWN이다.

## 8. 비용·연구성과·다음 결정

시간은 data/mask준비·encoder·load·S·D·viewer/평가를구분하고실패포함전체비용을보고한다. CUDAallocated/reserved, OSavailable/RSS, cgroup/events는별도로기록한다. cachewarm/cold와한task두조건재사용을명시한다. attention 한block peak나ROI면적을전체모델비용으로외삽하지않는다.

이번의성공은 '모든영상이잘됨'으로만정하지않는다. **개인자료에의존하지않는3task입력·최대6개실제출력·동일평가표·비용표·실패영역**을얻는것이일차산출물이다. 다만코드PASS를품질PASS로바꾸지는않는다.

실험후선택할다음가설은하나뿐이다.
- 참조가달라도외형유지·동작추종: 독립개체/길이·가림검증으로확장.
- 외형반영되지만참조자세/시점이출력을끌고감: reference의공간배치와외형전달을분리할구체적인조건/학습개입을제안. 더잘맞는개인사진을요청하지않음.
- 동작은맞지만target외형무시: identity주입/표현·sourcecopy억제관점으로질문수정.
- 특정범주에서만실패: SCAIL지원범위와입력/마스크문제를구분하고일반객체편집에맞는두번째backend를검토. 모든객체로무리하게일반화하지않음.
- 주된실패가장면/경계: 보호영역·원본문맥조건·inpainting/합성연구검토. 개체/동작실패를합성으로가리지않음.

B-028의알고리즘·추가예산은이결과전에확정/실행하지않는다. 다음제안은어떤현상을어떤변경으로개선하고무슨대조군과비교할지구체화한다. 결과에관계없이새smoke·개인사진대기·update숫자확대에복귀하지않는다.

## 9. 문헌·공부·기록·제출

선행비교는최대3방법을핵심기제중심으로검토한다: VideoSwap의semantic correspondence, VideoAnydoor의identity/trajectory/pixel warper, VideoPainter의context branch·inpainting. 공식논문·실제코드/weights공개를분리한다. VideoAnydoor는검토당시README에code release준비로적혀있어바로실행가능하다고가정하지않는다. 이문헌들을이번에모두설치하거나재학습하지않는다.

한국어lessons에는조건불변성의직관→수식→실제cache→관측을연결한다. 같은V/P/noise와같은target의R1/R2에서동작은source에묶이고외형은target에묶여야한다는요구, referencebundle교란,새data의inference평가와pairedtraining의차이,품질-비용관계를다룬다.

시작전CHARTER/RESEARCH_V2/ROADMAP/HISTORY에서 '특정개인자료=전체연구선행조건' 문구를고치되과거사실은보존한다. B026은선택적보류, B027은공용개발평가로연결한다. 코드와기록을기존research branch에commit/push하고원격SHA확인한다. 기존실행중작업은종료시키거나덮어쓰지않는다.

산출물: CASES.md, 비민감public manifest와download recipe, configs와run matrix, 실제모든출력/실패, RESULTS.md, COSTS.md, 한국어lesson, NEXT_DECISION.md, viewer, 재현명령. 공개조건을확인한코드/metadata/링크만GitHub에올리고개인미디어·weights·비밀값은올리지않는다. 공개원천데이터의재배포허가와download recipe공개는구분한다.

실제실행후단일비공개ZIP를Spark/Mac /tmp에보존하고CRC·manifest/hash·전송동일성을확인한다. 모델weights와중복조건cache는제외한다. GPU자체프로세스종료를확인한다. 최종보고는비교영상/실패양상→3task범위→비용→검증한계→다음방법가설순서다.

## 참고한 1차 자료

- DAVIS: https://davischallenge.org/davis2017/code.html
- DAVIS dataset license metadata: https://github.com/davisvideochallenge/davisvideochallenge.github.io/blob/master/index.html
- VPBench: https://huggingface.co/datasets/TencentARC/VPBench
- VideoPainter code: https://github.com/TencentARC/VideoPainter
- VideoSwap: https://videoswap.github.io/ , https://arxiv.org/abs/2312.02087
- VideoAnydoor: https://arxiv.org/abs/2501.01427 , https://github.com/yuanpengtu/VideoAnydoor

검토는원격코드·공식문서읽기다. 실제공용자료선정·다운로드·Spark실행·새로운품질판정은아직하지않았다.

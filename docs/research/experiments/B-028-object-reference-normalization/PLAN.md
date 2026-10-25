# B-028 — 공개 고정 패널의 객체 중심 참조 정규화

작성 2026-10-26. 상태 **PROPOSED / PLANNED / NOT_RUN**. 사용자에게 수행 지시가 전달될 때만 아래 예산을 적용한다. 신규 GPU·모델 다운로드·학습은 문서 작성 중 0회다.

## 1. 상위 목표와 이번 결정

원본 영상 V, 대상 참조 R, 편집 지시 P로 원하는 객체를 치환하면서 원본 동작·장면을 보존하고 단일 DGX Spark에서 품질/비용을 개선한다. 개인 Lab/IG 사진의 추가 확보에 연구를 종속시키지 않는다. A imagegen 트랙은 분리·동결한다.

B-027의 공개 3과제×2참조와 실패를 보존한다. reference scale/position을 그대로 둔 B-027 기준선과, 같은 사진/마스크에서 객체 중심으로 정규화한 전처리를 비교한다. target frame·pose·source·prompt를 더 유리한 것으로 교체하지 않는다. 이것은 새 알고리즘 또는 reference-pose disentanglement를 주장하는 작업이 아니라, 재사용 가능한 입력 기준선의 한정 검증이다.

동물 reference의 support는 896×512에서 R1=4197px(0.9149%), R2=10601px(2.3108%)이며 첫 bbox는152×46px다. 작은 참조가 유일한 실패 원인이라고 확정하지 않지만, 원본 canvas의 대부분을 회색으로 유지한 입력이 encoder에 전달되는 것은 실제 시트/manifest에서 확인했다. 사람 R2에는 GT가 제외한 전경 가림이 있다. 확대는 누락 세부·가려진 몸을 복원하지 않는다.

모델을 바꾸면 backbone·학습·입력 계약·프롬프트 요구가 한꺼번에 달라진다. 따라서 이 전처리 비교를 한 번만 완료하고, 결과 없이 crop/scale sweep을 계속하지 않는다.

## 2. VideoPainter 제안의 범위 정정

공식 TencentARC/VideoPainter commit `bbab6cd5cd5cb89f0e2444305c32fd74a010ae0a`, `infer/edit.py`를 읽었다. 해당 편집 경로는 source frame/mask에서 FLUX Fill로 편집 첫 프레임을 만들고 이를 video[0]/masked_video[0]에 넣어 전파한다. OpenAI client/원격 prompt rewriting 호출도 코드에 있다. 관측한 generate_video 인터페이스는 별도 임의 target-reference를 SCAIL처럼 직접 받는 경로가 아니다. ID resampling이라는 이름만으로 별도 reference identity encoder가 제공된다고 가정하지 않는다.

따라서 VideoPainter는 원본 문맥 보존과 첫프레임 편집 전파의 후보이며, 바로 동일한 V/R/P 과제의 drop-in 교체로 선언하지 않는다. 추후 비교에는 `I_edit=G(V0,R,P)`를 만드는 로컬 reference-guided 첫프레임 단계 또는 명시된 oracle anchor가 필요하다. oracle은 일반 사용자 입력이 아니며 downstream-only 결과로 분리한다. generic 텍스트 이미지로 target을 대체하면 기존 정확한 참조 객체 과제와 다른 평가다. 이번에는 설치·다운로드·외부 API·첫프레임 생성·VideoPainter 추론을 하지 않는다.

## 3. 고정 패널과 변수

B-027 선택 그대로 사용:
- animal: source dog f0..16; target dog-gooses track1 f0/f85
- human: source dance-twirl f0..16; target dance-jump track1 f0/f16
- vehicle: source car-roundabout f30..46; target car-shadow track1 f0/f39

기존 입력과 GT mask를 재사용한다. 새 자료/촬영/웹이미지/standing reference를 요구하지 않는다. source 프레임순서17장,896×512,source_fps=null,preview24fps,timebase_assumed=true를 유지한다. 이미 쓴 데이터는 개발 패널이며 모델학습자료와의중복UNKNOWN/외부heldout아님을 유지한다. 실제 사람 신원을 식별하거나 같은track을 생체신원인증으로 부르지 않는다.

원본 source RGB/driving mask/공통 caption/negative empty/실제 initial noise/RNG/UniPC40/shift3/CFG5/seed20261022는 case별 B027 값과 동일하다. 공식replacement True, history/additional_ref None, adapter/ALG/manualRoPE OFF. 현재 정상 모델/정밀도/커널/loader를 바꾸지 않는다.

## 4. 전처리 규칙 — 모든 참조에 하나의 식

B027에서 실제사용한896×512 masked reference와같은좌표의 binary support M에서 시작한다. RGB밖은128이고 semantic mask는RED/BLACK이다. 원본/전처리파일계보를확인하되 전체감사반복은금지.

M의 최소 bbox를 [x0,y0,x1,y1)로 정하고 w=x1-x0,h=y1-y0,cx=(x0+x1)/2,cy=(y0+y1)/2로 둔다. 고정 q=0.80, canvas W=896,H=512에 대해:

`s = min(q*W/w, q*H/h)`

`x' = s*(x-cx)+W/2`, `y' = s*(y-cy)+H/2`

같은 isotropic affine를 RGB와 M에 적용한다. RGB는bicubic,M은nearest,canvas밖은128,M'밖RGB는128로재설정한다. M'에서 RED/BLACK semantic mask를 다시 만든다. RGB·mask의pixel-center 규약/반올림을code와미소fixture로고정해정합오류를피한다.

회전·flip·비등방성변형·사지/얼굴보정·생성형SR·새segmentation·구멍채우기는0. 기존 R2의 가려진 부분은 새정보로 채우지 않는다. source 크기에 맞추거나 source silhouette로 reference를 warp하지 않는다. 같은 상수/알고리즘을6장에 적용한다. q나방법을결과를보고선택하지않는다.

이는 참조의 위치·scale·보간·mask 배치를 함께 바꾸는 **전처리 묶음**이다. 자세관계를 바꾸지 않지만 학습된 encoder의특징은변할수있다. 개체RGB가pixel-exact로유지된다고하지않고 재표본화를 명시한다. native정보량이증가했다고하지않는다. 원래 bbox/area/입력해상도,scale와출력bbox/area,두입력시트를저장한다.

## 5. 조건과 구현

새 masked RGB를 VAE·CLIP 양쪽에 인코딩한다. ref mask도동일좌표로계산한다. latent crop/resize만으로RGB encoder를대체하지않는다. target 프레임번호/실제고유RGB를바꾸지않는다.

새 case 대 대응 B027 case에서 허용차이는 양CFG ref_latents/clip_fea/ref_masks 최대6leaf다. 기존context/negative/driving/noise/RNG/timesteps/sigmas/device·container계약은 유지한다. 원래cache를덮어쓰지않고producer/consumer를분리한다. 공통T5/source인코딩과기존6개샘플러를재실행하지않는다. 양CFG실제첫forward의참조연결을관측하되추가DiTforward는0.

geometry exact, 유한입력, 의도한condition연결,기반model보존은엄격히확인한다. 독립GPU연산의 byte-identical 재현이나 완벽한관절GT를새로운gate로만들지않는다. 기존미디어/인코더/샘플러검사를전부반복하지않고이번변경의2~4개CPU계약검사로한정한다.

## 6. 실행 상한

- 새full sampler 최대6회: 기존3과제×2reference 각각1회. 실패도시도에포함.
- 각40step·80forward,최종latent저장후decode각1회. 기존6raw는재사용.
- 인코더는필요한새reference VAE/CLIP만;공통조건재사용. P재계산은필요한reference부분만과제별최대1worker. PROBE는기존정상경로의필요횟수만.
- 신규학습/모델·패키지다운로드/외부API/imagegen/새데이터0. 다른seed/CFG/q/negative prompt sweep0. 새타입체계·MCP서버·메모리가드신설0.
- 총작업상한4시간,전처리·사전계약목표상한45분. GPU-heavy순차1개,자동재시도0. 같은B028이이미실행중/완료면중복금지.
- 기존MemAvailable시작72GiB/실행24GiB,swap0,타서비스보호및단계분리유지. 기존worker외프로세스종료/driver변경/가드완화금지.
- 첫결과가시각적으로나쁘다는이유로다른고정조건을생략하지않는다. 입력오류·비유한값·자원안전문제는중단하고실제상태저장.

## 7. 평가와 다음 결정

같은6개입력에 B027/B028을나란히비교한다. SOURCE,원래/정규화reference,두raw,전체17frame·local0/8/16을제공한다. 후처리합성·워터마크지우기·얼굴복원·보간·SR·출력별시간/위치정합은하지않는다.

평가축: (1) target 외형과source-copy여부 (2) source동작방향·순서 (3) 얼굴·사지·치마/차체형태 (4) 보호문맥의문자/서명/추가객체 (5) 같은target의R1/R2민감도 (6) encoder/생성/전체비용. 더크게움직임·단순recolor·배경보존만으로joint성공을선언하지않는다. 사람은의상/머리/형태등관측가능특징만다루고실제신원인증을하지않는다.

동물만개선되면전처리의특정입력효과,전체외형만개선되고동작이손상되면trade-off,배경장식만사라지면보호문맥부분개선으로기록한다. 작은reference비율/가림은교란이며단일원인으로확정하지않는다. q가커질수록항상좋거나모든crop이정답이라고하지않는다.

정량화가능한비편집영역차이도원본보다target실루엣이넓어지는합당한가림과구분한다. source객체영역을edited GT로쓰지않는다. 새crop을많이확대했다고정보량·인지품질향상으로대체하지않는다.

Agent 정적검토/프레임파일검사와사람의연속지각검토를구분한다. 실제nativeFPS미확인,preview24fps와루프경계를표시한다. 실제시청없으면temporalUNVERIFIED.3과제·6개matched출력은독립6개개체/102반복이아니다. 여러도메인전체성능·논문신규성·상용우월성미입증.

이번한번이후반복crop/scale탐색을종료한다. 개선되면공통입력baseline후보로보존하고미사용사례는후속에정한다. 개선없거나trade-off면해당가설을접고조건분리구조/target anchor stage를갖춘다른backend의한정비교를검토한다. 단순텍스트편집을정확참조교체로바꾸어보고하지않는다. VideoPainter 설치·학습·추가실험은이번범위가아니다.

## 8. 공부·기록·산출물

한국어해설은 (a) 전처리좌표/scale와encoder에보이는신호,확대와정보복원의차이 (b) masked-video context와reference identity/edited-first-frame의서로다른계약을실제코드와연결한다. VideoPainter의ID resampling을보편reference-image encoder로혼동하지않는다.

시작전PLAN/조건/변환/예산을고정하고CHARTER·ROADMAP·HISTORY에개인자료와독립적인공개패널연구의위치를기록한다. 종료후RESULTS/조건/자원/재현/이론/다음결정을비민감코드와함께commit/push·remote확인한다. main/force-push/이력삭제금지.

공개재배포권한을임의확대하지않는다.새private raw/latent/조건은full archive로보존하고,공유용review-lite는영상·참조/전체시트·manifest·보고서·재현코드를유지해raw/latent/중복PNG를제외한다.기존video/image를재인코딩하지말고full/lite의SHA를구분한다.각archive의실제포함범위·CRC·해시·Mac/Spark전송상태를검증한다.이미없는파일을포함했다고하지않는다.

최종보고는시각joint결과→한계→실행횟수/비용→바로볼자료→다음가설순서다.작업프로세스를종료하고다음결과전새작업을예약하지않는다.

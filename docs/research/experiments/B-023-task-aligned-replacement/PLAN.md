# B-023 — B-022 결과 이후: 동일 자연동작 입력의 공식 replacement pilot

개정 2026-10-25 · **REVISED / PLANNED / NOT_RUN**. 사용자에게 새 수행 지시를 받은 실행자가 아래 한정 범위를 실행한다. 문서 수정은 GPU 실행이 아니다.

이 문서는 B-022 결과를 검토한 뒤 기존 2026-10-24 후보안을 교체한 것이다. 과거 후보(기존 밈 f7..23의 SELF_REPLACE/LAB_REPLACE 2회 및 ROI 합성)는 Git 이력 `6a359ae85f134ca879a2d521d7fd771b401b5d55`에 보존하며 **이번 실행 범위가 아니다**. 지금은 원본·참조·시간축을 바꾸지 않고 신규 sampler 최대1회로 제한한다.

상위 목표: [원본 보존 영상 객체 편집](../../RESEARCH_V2_SOURCE_PRESERVING_EDITING.md). 관련 결과: [B-022](../B-022-resumed-update-comparison/RESULTS.md). 선택 이유는 [20261025 결정](../../decisions/20261025-B-022-review-and-B-023-revision.md)에 기록한다.

## 1. 지금 내리는 결정

B-022는 유효한20회 상태에서80회 추가해 총100회 학습·재로딩과 정확히 대응하는 두 영상을 확보했다. 고정tuple loss는 줄었지만 착석·후반 얼굴/귀 손상·머리 잘림은 남았다. 이는 현재 한clip/세fixed tuple/마지막block QV rank4 학습 범위에서20→100의 품질 개선이 입증되지 않았다는 뜻이다. 모든 학습의 실패나 데이터/모델 한계를 확정하지 않는다.

동일 구성의200/500/1000update 확대와 독립학습 replay/FA 원인 감사는 다음 작업으로 두지 않는다. 기존 adapter와 optimizer는 연구 자산으로 보존하지만 이번 기본 추론에는 적용하지 않는다.

## 2. 새로 확인한 입력 계약 차이

B-020 INPUT_AMENDMENT에는 reference와driving 모두 RED 개체/WHITE 배경, replace_flag=False가 기록되어 있다. B-022는 해당 조건을 보존했다. 이번 검토는 그 기록을 확인한 것이고 기존 비공개 마스크 픽셀을 직접 재확인한 것은 아니다. 실행자는 이미 있는 실제 mask 파일/조건 cache로 이 의미를 짧게 확인한다.

고정 SCAIL-2 `78fe19576bb06be96c2375e088574a262a300edb`가 가리키는 SCAIL-Pose submodule은 `519c7f54cb972e7f92684213b7ef6c3e05a8f3b2`다.
- `NLFPoseExtract/process_animation_aio.py`: reference mask background WHITE, driving writer의기본background BLACK.
- `NLFPoseExtract/v2_helper.py`: `write_colored_mask_video(..., bg_color=(0,0,0))`가기본.
- `NLFPoseExtract/process_replacement.py`: reference mask background BLACK, driving mask background WHITE, driving RGB 자체는복사한다. `test_mode`가아닌일반reference 경로는RGB사진의배경을자동으로blackout하지않는다.
- pinned main README: mask black/white는배경비가시/가시, 색상은개체대응; replacement에는replace_flag와해당mask, prompt는결과영상의설명이다.

따라서 B020/022의조합은공식기본animation/replacement전처리어느쪽과도완전히같지않다. **그차이가실패원인이라고확정하지않는다.** 두배경WHITE가항상불법입력이라는뜻도아니다. 올바른과제계약으로생성한결과가필요하다. B009의ref배경변경과B016의H120단독개입은공식replacement전체가아니다.

## 3. 질문·비교·한계

질문: 같은실제Lab사진과같은자연동작원본을사용하고 학습adapter없이공식replacement계약으로바꾸면, 참조착석/침실대신source의사족서기·고개방향·장면을재현하는가?

- 새 case: **NATURAL_LAB_REPLACEMENT** 1개.
- primary historical comparator: **B-020의미학습adapterOFF raw baseline**. B022의20/100은학습된별도맥락이며주요동일모델기준선으로대체하지않는다.
- CPU source-copy baseline: 모델생성없이원본그대로. 같은개체이므로source만복사해도겉보기성공할수있다는함정을명시한다.
- 최종 결과는same-identity/different-pose scene-conditioning pilot이다. cross-ID 객체치환,reference가필수로사용됐다는증거,두개체춤,15초,일반화는NOT_RUN이다.
- 모드와reference배경mask가동시에달라지는**과제계약의묶음비교**다. replace_flag하나의독립인과효과라고부르지않는다. 공식animation새생성/2x2 ablation은이번0회다.

## 4. 입력과 원본 시간축 고정

B020에서사용허가된실제Lab source f126..142 inclusive, PTS4.2..4.733333초,17frame30fps,가로896×세로512 aspect-fit을그대로사용한다. duration17/30과표본간격16/30을구분한다. 새crop/upscale/다른영상/과거meme24fps로바꾸지않는다.

기존앉은Labreference RGB·RED subject support·driving RGB/support·prompt·negativeempty·seed20261022·UniPC40·shift3·CFG5·history/additional_refNone을유지한다. 기존prompt는이미source바닥에서사족으로서서고개를돌리는결과를서술하므로그대로재사용한다. 새로운촬영·권한감사·정밀관절주석을요구하지않는다.

reference semantic mask만 BLACK background + 기존RED support로파생파일을만든다. RGB사진의침실을blackout/삭제/포즈편집하지않는다. 그림속실제배경과letterbox padding도마스크상비가시로표시하되RGB/padding값은그대로둔다. driving은원본RED support+WHITE background를유지한다. 기존binary support/계보를사용하고색공간RGB/BGR·경계보간·유효색을확인한다. JPEG회색경계값을아무임계값으로잘라새실루엣을만들지않는다. 불확실경계는그대로기록한다.

공식mask helper와실제half-downsample/28채널packing순서로새마스크조건을계산한다. 과거safetensors채널을근거없이수동반전하거나기존캐시를덮어쓰지않는다. encoder출력은입력·버전·shape·dtype·해시계보가같으면재사용할수있다. 필요하면새P1회까지만허용한다; targetY/prefix훈련특징은재계산0회.

## 5. 공식 replacement 실행 경로

양CFG조건에replace_flag=True를설정하고,공식model이정한T/H/W모드설정을사용한다. B016 Hoverride/ALG callback/학습adapter를활성화하지않는다. 모델이실제로받은flag·mode별offset과active LoRA수가0임을작은스칼라trace로확인한다. 원래체크포인트의vanilla block을사용한다.

SCAIL생성입력은mask와RGB가별도다. semanticmask를alpha로사용하거나sourceRGB에곱해정보를지우지않는다. 추가SAM/pose/depth가중치·remote Gemini enhancer를실행하지않는다. 기존support를재사용해전처리와동일한입력계약을만드는것이지공식SAM성능을검증하는것은아니다.

고정RGB/T5/CLIP/driving latent/noise/RNG/scheduler는기존B020과비교한다. 예상변경은양CFG의reference mask와replace_flag/그에따른모델위치설정이다. 무조건모든16leaf가일치해야한다거나driving4개가변경돼야한다는옛검사를재사용하지않는다. 최초noise는seed만이아닌실제tensor로일치확인한다. 잘못된입력·NaN·shape/device오류·안전문제는차단하되독립GPU연산의미세한roundoff를파라미터replay실험으로확대하지않는다.

## 6. 범위와 종료

전체작업상한3시간,새fullsampler실패포함최대1회(40step80forward),decode최대1회,자동retry0. 새로운GPU worker는기존P/PROBE/S/D순차경로를사용한다. P가불필요하면encoder적재를생략한다. final latent를decode전에원자저장하고D실패로재샘플링하지않는다.

학습update0,기존prefix추출0,모델/패키지/데이터다운로드0,외부생성/imagegen0. 기존안전조건(시작72GiB/실행24GiBheadroom,swap0,타서비스보호)과환경을유지한다. 상위scope/cgroup/CUDA회계는별도로측정하고다른작업을종료하지않는다. 이미종료한B022를재개하지않는다.

이번에는**ROI재합성·matting·얼굴보정·SR·frame interpolation·warp를추가하지않는다**. source를붙여좋아진화면으로모델의raw실패를가리지않기위해서다. 원본보존합성은원모델결과를본뒤필요성이확인되면다음선택지가된다.

## 7. 시각 평가 — loss 대신 실제 편집 목표

SOURCE / REFERENCE / B020_BASE_OFF / B023_REPLACEMENT를분리표기하고 전체17frame·기존local0/8/16·원본속도30fpsviewer를제공한다. B022STEP20/100은선택적인역사맥락으로만표시한다. 재생가능/정적시트와직접연속시청을구분한다.

평가축:
1. 사족으로서기와사지배치(두발춤이아님).
2. 원본의고개방향·순서·타이밍. 단순큰움직임/깜빡임은성공이아님.
3. 주둥이·눈·귀·목손상과후반잘림,추가reference letterbox복사.
4. source의타일바닥/창가장면·카메라·비편집물체보존. semanticvisible는pixelhardconstraint가아니므로raw차이를측정한다.
5. 실제Lab개체·체형과견종유사성을구분. D도같은개체라reference사용/새개체교체증거는미입증.
6. 실제단계별시간/NFE·CUDA/OS/cgroup메모리와실패포함비용.

source-object영역밖raw오차/분포·고정배경패치의변화를보조로쓰되몸크기/그림자가바뀔수있는경계띠를분리표시한다. rawRGB오차와MP4손실압축차이를혼동하지않는다. source-copy가배경/동작점수를잘받아도editing능력의증거가아니다. 임의similarity임계값·정량gain을만들지않는다.

직접연속시청을할수없으면temporal=UNVERIFIED를유지하고사용자가짧게비교하기쉽게한다. staticPASS를temporalPASS로바꾸지않는다. 이한번이잘나와도Kling대체·논문기여라고하지않는다.

## 8. 연구 해설·다음 판단·이력

한국어해설은이번과직접연결된두가지: (a) loss의조건분포와실제편집task계약의차이, (b) semanticmask/모드와alpha합성의차이를수식·pinned코드·관측으로설명한다. 새로운전체attention감사나toy학습은반복하지않는다.

생성/원본장면의의미있는개선이보이면현재sameidentitycopy의한계를적고실제cross-ID후속가설하나를제안한다. 배경만바뀌고자세·얼굴이실패하면부분효과이며motion/identity문제는남는다. 차이가없으면모드불일치단독해결을지지하지않으며1000update/다른offset/새프롬프트탐색으로자동확대하지않는다. 다음구체실험은결과를본뒤정하고이번에는실행하지않는다.

착수전CHARTER/ROADMAP/HISTORY와실제B022종료를확인한다. 기존oldB023설정대신본개정안을읽었음을runconfig에남기고입력·코드·조건차이를commit/push한뒤실행한다. HISTORY/ROADMAP에B022학습량pilot종료와B023수정이유·실제상태를기록한다. 종료후RESULTS/INPUT_CONTRACT/조건비교/자원/재현/해설을갱신한다. 기능/실행과typingNOT_CLEAN은구분한다.

GitHub에는비민감코드·계획·관측요약만넣는다. 개인사진/영상/마스크/좌표/실제경로/latent/adapter/weights는비공개. 단일검토ZIP을실제Spark/Mac /tmp에저장·전송·CRC/manifest/hash확인하며대형가중치·중복훈련prefix는제외한다.

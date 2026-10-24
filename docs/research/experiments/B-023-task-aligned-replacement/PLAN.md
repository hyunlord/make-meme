# B-023 — 과제에 맞는 공식 replacement 기준선과 원본 보존 합성

2026-10-24 · parent B-012/B-013/B-020~022 · **PLANNED / NOT_RUN**.
상위 방향: [B 연구 v2](../../RESEARCH_V2_SOURCE_PRESERVING_EDITING.md).
사용자가 실행자에게 이 계획의 수행을 지시할 때 아래 범위를 적용한다. 문서 게시만으로 GPU 생성이 실행/승인된 것은 아니다.

## 0. 핵심 질문·변경 이유

목표는 source video의 장면·시간축·동작을 유지하며 reference의 개체를 넣는 것이다. 지금까지 animation=False가 아니라 **replace_flag=False인 animation**을 주로 시험했다. B-016 H120 단독 변경도 공식 replacement 전체와 다르다. 따라서 새가중치 학습/추가ALG보다 **공식 replacement 입력·mask·모드 계약을 갖춘 task-aligned baseline**을 먼저 확보한다. 성공을 보장하지 않으며 과거실험도삭제하지않는다.

이번 비교는 animation과replacement의순수한단일변수인과실험이아니다. 작업에맞게모드·마스크·caption·fullscene전처리가함께바뀐다. 과거animation출력은역사맥락이며동일조건대조군이라부르지않는다.

목표산출물은새로운계획문서만이아니라 raw replacement MP4, source보존composite, 전체프레임비교, 실패유형과전체자원실측이다.

## 1. 범위와 실행 상한

- A와과거B의모델·checkout·미추적파일·실패·예산기록보존. 학습adapter OFF, ALG OFF, 임의Hoverride OFF. 기존정상 SCAIL checkpoint/upstream `78fe19576bb06be96c2375e088574a262a300edb`와분리메모리경로재사용.
- B-022가실행중이면종료시키지않고동시GPU금지. 미착수라면DEFERRED_BY_TASK_REDEFINITION로계획우선순위를남기고B023부터. B022의기존PLAN/결과를삭제하지않는다.
- 총작업상한4시간. source/mask/config준비는합계최대60분을목표로하고필요이상감사를늘리지않는다.
- **신규full sampler최대2회(실패포함)**: SELF_REPLACE1, LAB_REPLACE1. 각40step80forward,decode각1,자동retry/seed탐색0. P인코딩과probe도각조건최대1회. 동일source조건의검증된재사용은허용하지만전체다른reference cache복사는금지.
- 모델·패키지·데이터다운로드0, 학습0, imagegen/외부생성/remote prompt enhancer0. 새segmentation가중치를설치하지않고이미있는도구/CPU수동support를사용한다.
- 기존72GiB시작/24GiB시스템headroom·swap0·타서비스보호규칙유지. 실제OS/CUDA/cgroup계측은구분. shutdown/driver/swap변경·타프로세스종료금지.

## 2. 입력을 원본 장면 기준으로 확정

이미사용이허용된기존meme source의 f7..23 17장을우선사용한다. B012manifest에서원본파일·SHA·24fps·PTS를확인하고, 실제원본파일에서 직접읽는다. 원본의실촬영/합성여부UNKNOWN은그대로이고이영상으로학습하지않는다.

v0기본canvas는 **가로896×세로512**다. native 원본전체를aspect-fit/letterbox하여camera와배경을잘라내지않는다. 기존512×288→확대→세로crop 이미지는원본정보를복원하는자료로대체하지않는다. 원본이실제로없으면없다고보고하고다른파일을조용히대체하지않는다. 전체source를보존한다는주장과ROI자료만보존한다는주장을구분한다.

동일17frame24fps,원본PTS와선형좌표변환·padding을manifest로고정한다. audio는학습조건에넣지않고최종긴영상단계에서적법하게원본timebase로재결합한다.

모든frame에서한개체track를식별한다. 기존mask를재사용하려면원본좌표로의정확한mapping과coverage를확인한다. 없으면제한된CPU mask준비를한다. 발/꼬리/귀경계의모호함은PARTIAL로표시하고가려진관절정답을만들지않는다. 완벽한keypoint평가를생성의선행조건으로요구하지않는다.

## 3. 공식 replacement 계약을 확인하고 실제로 사용

pinned README, generate.py, process_replacement의사용가능한고정소스, wan/scail.py, model_scail2.py를읽어최소차이를확인한다. 설치없는읽기전용소스검토로충분한부분은그렇게한다.

- `replace_flag=True`를사용한다. bool을변경한것과공식전체계약을맞춘것을구분한다.
- 동일target/control region에같은색ID를사용한다. reference의무관한배경은비가시, source에서보존할배경은가시라는의미를공식semantic mask로표현한다. 일반예상은reference=RED subject+BLACK background,driving=RED subject+WHITE visible source background이며 **실제고정preprocessor/예제와검증한뒤확정**한다. 검증과다르면공식근거에맞춰입력amendment를생성전기록한다.
- semantic mask는alpha매트가아니다. sourceRGB에black mask를곱해서동작정보를지워서는안된다.
- default replacement의T/H/W는공식모델이설정하게한다. B016의animation T1+H120 hybrid를재사용하지않는다. 실제ref/video/drive 위치계약을작은scalar trace로확인한다.
- history/additional_ref=None,LoRA/enhancerOFF,기존mixed precision·FlashAttention·UniPC40/shift3/CFG5·negative empty·seed20261022를유지한다. 같은출력shape일때실제initial noise값도공유·검증한다.
- positive prompt는'교체해라'라는지시가아니라 **교체가완료된source 장면의객체·외형·동작**을서술한다. 사용자의역할지시/EditSpec과backend caption을따로저장한다. 보이지않는wink/kick/품종을지어내지않는다.

기존condition builder의hardcode된False,ref배경색,H/W/fps,모드검사등만좁게수정한다. cache producer/consumer·shape/normalization 검사를삭제하지않고새기대계약으로검증한다. 공식모드가RGB를출력하며RGBA/정답alpha가없다는것도기록한다.

## 4. 두 case와 실행 순서

### SELF_REPLACE

reference=선정 source f7의동일개체. source와같은개체를다시넣는진단이다. caption도실제source에맞춘다. 이결과가좋아도reference를무시하고source를복사했을수있으므로identity編集성공은아니다. 입력mode·mask·장면보존의기술적baseline으로본다.

### LAB_REPLACE

reference=기존실제검은Lab사진. source는그대로다. 별도reference semantic mask와caption을사용한다. Lab의넓은가슴·굵은사지등을유지하며원본자세·시간흐름을옮기는목표다. SELF대LAB는reference/text가바뀌는task비교이지순수identity인과분리는아니다.

CPU원본복사영상을무료baseline으로만든다. SELF의품질이나쁘다는이유만으로LAB를생략하지않는다. 입력계약불일치/NaN/안전문제일때만중단한다. SELF_PASS를무한gate로만들지않고2회한도내실제task결과를확보한다.

P→PROBE→S→D의기존경로를사용한다. 새로운mode에맞춘cache를생성하고final latent를D전에보존한다. decoder/인코딩실패로sampler재실행금지. weight/hash는검증된기반을보존하며매번65GB전체를읽어야한다고하지않는다.

## 5. 같은 LAB raw로 source보존 합성 비교 — 추가 sampler0

LAB raw를본뒤좋은영역만뽑아붙이는것이아니라 **source만보고사전고정한edit envelope**를사용한다. v0는17장 source subject box의shot-level union에가로/세로각15%문맥margin을더하고canvas안으로clip한고정ROI를기본으로한다. 이는품질최적값이아니라명시적baseline이다. datasetsemanticmask를alpha로바로사용하지않는다.

ROI내부weight1,외곽안쪽8px feather,외부0인edit weight E를만든다. 보호할앞쪽occluder가확인된경우 source관측에근거한보호mask를분리한다. 정확한규칙과수정은생성전고정한다. 복잡한occlusion을임의로정답처리하지않는다.

`final=(1-E)*source+E*raw_generated`를raw RGB에서수행한다. 별도foreground 추출/shape warp/face복원/추가SR/색보정은첫비교에넣지않는다. E는객체alpha가아닌편집영역이다. ROI안에는기존객체제거·배경복원·새객체·경계가함께필요할수있다.

target이사전ROI밖으로나오거나source잔상이남으면CROP_SUPPORT_FAILURE로남긴다. 결과를본뒤ROI를늘려더좋아보이게하고동일baseline이라고하지않는다. raw와clipped composite를둘다보존하고후속support개선의증거로삼는다. 합성이객체얼굴/동작실패를해결했다고주장하지않는다.

## 6. 평가·산출물

SOURCE / reference / SELF raw / LAB raw / LAB composite와17장전체를같은시간축으로제공한다. 예전animation은비교판별도에'다른모드/전처리의역사자료'로표시하며마치동일seed단일개입비교처럼하지않는다.

질문: 원래개체대신실제Lab특징이들어갔나? 원본직립/머리방향·순서를따르나? 원본배경/카메라/다른객체가보존되나? 얼굴/귀/사지·경계/가림/접촉이무너지나? 비용은얼마인가?

source-copy는배경/동작을보존해도identity변경이없으므로taskFAIL. generic검은개와실제Lab의일치를구분한다. reference침실복사,원본개체잔상,거대한체형축소,노출/색변화도기록한다.

source-labeled객체영역밖raw drift,사전E바깥의raw/composite pixel오차,E의전체면적비율,경계띠의차이를따로산출한다. composite의outside-E exact보존은구현특성이지모델기여가아니다. MP4손실압축차이를raw합성오류로혼동하지않는다. 단일source/seed로통계적우월성을주장하지않는다.

사전 local0/12/14/16과모든frame관측, native24fps 단회재생·프레임이동을제공한다. 사람이실제속도로검토한경우만temporal수용을별도기록한다. 도구가영상을재생할수있다는것만으로PASS하지않는다. 논문용독립눈가림평가는후속이며이번에는탐색결과를정직하게남긴다.

측정: 전체P/로드/S/D/합성/인코딩시간,model NFE,OS가용/RSS/CUDA allocated/reserved/cgroup,mask준비시간,실패포함사용량. 동일fullframe생성뒤합성만했으면생성FLOP절감은0/NOT_ESTABLISHED다.

## 7. 기록·학습·다음 결정

실행전EditSpec·입력·공식모드확인·mask·caption·edit envelope·예산을고정한다. CHARTER/ROADMAP/HISTORY에새문제정의와B022상태를요약연결한다. 코드·캐시·출력보존은기존규칙대로하고새MCP나거대승인시스템은만들지않는다.

lessons/B-023-task-aligned-editing.md는 animation/replacement차이,semantic mask와alpha/edit support차이,disocclusion/가림,全frame모델과ROI계산량,source-copy trivial해를수식·실제코드·이번출력에연결한다. 핵심이론1~2개를깊게쓰고같은감사문서를다시대량복제하지않는다.

원격에는비민감문서·코드·해시만commit/push후HEAD확인. 개인미디어·caption의private정보·mask·latent·weights·절대경로는비공개로보존. 작업후단일ZIP를실제Spark/Mac /tmp에만들고전송/CRC/manifest/SHA를확인한다. 대형weights·중복archive는제외한다.

두case완료후멈춘다. 정식replacement가품질을개선하면한개체의다른ref/동작으로검증,합성경계만문제면support/가림가설,identity/pose가계속문제면task에맞는데이터/조건학습가설하나를선택한다. 새모델다운로드·추가학습·다른offset·ALG·업스케일·두개체15초는자동시작하지않는다.

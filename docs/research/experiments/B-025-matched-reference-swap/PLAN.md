# B-025 — 같은 원본·중립 caption에서 Lab/IG 참조 묶음 교체

작성 2026-10-25 · parent B-024 · **PLANNED / NOT_RUN**. 문서 등록은 실행·예산 승인이 아니다. 사용자가 실행 담당자에게 이 계획의 수행을 지시할 때 아래 범위를 적용한다.

## 1. 연구 목표와 이번 질문

상위 목표는 원본 영상 V, 객체별 참조 R, 편집 지시 P를 받아 원본 장면·동작·시간축을 보존하면서 원하는 개체로 교체하고, 단일 DGX Spark에서 품질과 전체 비용을 개선하는 것이다. [연구 v2](../../RESEARCH_V2_SOURCE_PRESERVING_EDITING.md)를 유지한다. A의 native imagegen 경로와 B의 local 모델 경로는 독립이다.

B-024에서 reference 비객체 RGB를128로 바꾸고 VAE/CLIP를 다시 계산한 뒤, 기존 침실·착석 구획과 후기 손상이 줄었다는 정적 관측을 얻었다. 그러나 source/reference가 같은 Lab이고 caption도 black Labrador를 명시했으므로, driving 개체를 복사하거나 텍스트를 따른 결과와 참조 기반 교체를 구분하지 못한다.

이번 질문: **같은 source·caption·initial noise에서 reference 묶음만 Lab에서 IG로 바꾸면, 동작·장면을 보존하면서 출력 외형이 해당 참조 방향으로 바뀌는가?**

C(R)=(reference RGB의 VAE latent, CLIP, reference semantic mask)라 놓으면 비교는 Y_L=G(V,C(R_L),P*,epsilon), Y_I=G(V,C(R_I),P*,epsilon)이다. P*에는 breed/coat/체형 지시를 넣지 않는다. 이는 reference 묶음의 기여 검사이며 RGB만의 효과, identity만의 순수 효과, 필요성 증명은 아니다. 서로 다른 참조의 posture·support·사진 품질도 함께 다르다.

## 2. 검토 근거와 한계

기준 HEAD `f8dff4ac08d2393eeb4d90d7b29b7d7afe00fad5`의 B-024 RESULTS/CONDITIONS와 B-020 INPUT_AMENDMENT를 원격에서 읽었다. B024는 두 CFG의 ref/CLIP4leaf만 변경하고12leaf를 유지했다. source와출력이픽셀동일하지않고raw에서출력PNG가파생됐다는보고는파일대체를배제하는근거지만모델수준source-copy는배제하지않는다.

검토자는 첨부 `/mnt/data` ZIP에 container/Python을 실제 시도했으나 ClientError로 열지 못했다. 213,673,511bytes 및 SHA `e7547ed8fbe8de13222ede089fb1fd66c639b76e1f3319f0c6fa1b58f57c3ecd`, CRC/334payload/양호스트일치는 실행자의 보고값이며 이번 독립 검증이 아니다. 정지프레임이나 연속영상을 직접 보았다고 하지 않는다.

B024의 caption은 검은Lab·넓은가슴·굵은사지라는 외형정보를 포함한다. 그 문장에 IG사진만 넣으면조건충돌이된다. IG용caption까지 바꾸는한출력은실용시험으로는가능하지만사진기여와text기여를분리하지못한다. 그래서 **중립caption 하나를 사전고정한 새2출력**으로 비교한다. B024는 역사자료이며 새로운 Lab 대조군으로 자동 대체하지 않는다.

## 3. 사례·입력

source는B024의실제Lab자연동작f126..142,17frame30fps,W896/H512다. 실제processed RGB·drivingsemanticmask·공간변환·PTS·모델weights/precision·seed20261022·실제initial noise·RNG·UniPC40shift3CFG5·negative empty를재사용한다. 다른meme구간/24fps/다른crop으로변경하지않는다.

| case | reference | driving | caption |
|---|---|---|---|
| REF_LAB | B024와같은중립배경Lab RGB/support | 같은실제Lab영상 | 동일P* |
| REF_IG | 사용자가기존편집용으로제공한원본IG RGB/support,중립배경 | 동일영상 | 동일P* |

IG참조는A에서생성한이미지가아닌사용자제공원본사진이어야한다. 알려진manifest·허용asset root에서확인하고개인홈전체를검색하지않는다. 실제파일·사용범위는기존계보를이용한다. 새촬영·같은허가의반복요청이나새모델다운로드를기본선행조건으로만들지않는다. 실제원본이없으면REF_UNAVAILABLE을보고하고다른개체/이미지로몰래대체하지않는다. 두참조입력확정을끝내기전에첫sampler를쓰지않는다.

Lab참조는B024의회색RGB와semantic mask를그대로사용한다. IG는같은aspect-fit/padding규칙을적용하고,기존사용가능support가없으면최대30분의기존CPU/수동도구로개체support만만든다. 어느조건도target crop을source실루엣에맞춰비선형warp하거나세부를생성하지않는다. 새모델로segmentation하지않는다. 서로다른원본사진이므로mask/bbox가동일해야한다는검사를하지않는다.

두참조모두개체support안의관측RGB는기록된resize후보존하고밖은RGB(128,128,128)로한다. semantic mask는RED개체/BLACK배경이다. drivingmask는기존RED대상/WHITEsource배경그대로다. neutral RGB와BLACKsemantic표현을혼동하지않는다. 지원밖흰padding도회색이며maskedRGB에서VAE와CLIP를모두계산한다.

사진선택·mask·transform·출력관측특징은생성전에고정한다. ref별로실제로보이는털색/흰무늬·주둥이·귀·가슴·사지비율중3개정도의구별특징을기록한다. 숨은부위나품종정답만으로실제개체일치를주장하지않는다.

## 4. 공통 caption

사전제안 P*:

> A dog matching the reference image stands naturally on all four legs on a light tiled floor in a sunlit room. It gently turns its head toward the left side of the image while its body stays mostly in place. The stable camera shows the dog's full body and the surrounding room.

두case에완전히같은positive문장과empty negative를쓴다. Lab/IG,black/gray/white, broad/slender/thick/thin 등의target외형표현을넣지않는다. 과거caption의target외형을남겨놓지않는다. 실제source관측과충돌하는내용만첫GPU생성전에한번정리하고동일문장으로고정한다. 별도enhancer/외부API/새LLM설치는없다. 사용자역할명세와이caption은별도필드다.

## 5. 코드·조건 재사용

기존정상replacement=True,history/additional_ref=None,LoRA/ALG/manualRoPEOFF와P/PROBE/S/D분리경로를사용한다. B024연결감사·source/ref VAE복원을다시전체반복하지않는다. 반복을정당화할구체적새오류가없으면이미확인한기반은재사용한다.

필요연산은공통P* T5 positive1회, IG maskedRGB의VAE+CLIP각1회와새semanticmask변환이다. Lab VAE/CLIP·driving·noise/scheduler는검증된B024cache로재사용가능하다. encoder수명·device메타데이터를보존한다. 최소변경이불가능할경우case별정상P최대1회로제한하고실제재계산을보고한다. 학습target/앞39층prefix는필요없다.

새pair내 허용차이는양CFG의 ref_latents/clip_fea/ref_masks(최대6leaf)뿐이다. 나머지text/negative/driving/noise/RNG/schedule 등은값·shape·dtype·device계약을보존한다. 실제같은shape의reference support가우연히같으면6개가반드시모두달라야한다고요구하지않는다. 변경집합·보존집합과배경규칙을semantic field로확인한다. 동일seed만으로noise동일성을추측하지않는다.

B024대REF_LAB 비교에는P*로바뀐positive조건이있다. 이를ref만바뀐비교라고부르지않는다. B024를새pair의정확대조군으로재사용하지않는이유다. 기반cache는읽기전용으로두고producer/consumer·실제referenceID를명시한다. 최초실제forward에서각참조묶음이전달됐는지만작게관측하고추가forward/attention대형dump를하지않는다.

## 6. 실행 범위

**새로운full sampler 최대2회(실패포함): REF_LAB1, REF_IG1.** 동일seed의한쌍이며복수seed일반화가아니다.각40step/80forward·finaldecode1회. encoder준비는위범위,probe는각최대1회. GPU-heavyworker는순차실행. 자동retry·추가prompt/gray/crop/scale/CFG/step검색0. 첫결과시각실패만으로다음case를생략하지않는다. 데이터/연결/비유한/안전오류는중단한다.

전체작업상한4시간,입력/mask준비는최대45분을목표로한다. 기존72GiB시작/24GiBheadroom·swap0·타서비스보호유지. 새학습/모델/설치/외부생성/imagegen0. 가드변경·다른프로세스종료금지. 최종latent를D전에저장하고D실패로S재실행하지않는다.

B024의약33.85GiB peak/17.9분은이전실측이고예상보증이아니다.각case실제P·모델로드·S·D·메모리·수동준비시간을남기되CUDA/cgroup/RSS를합산하지않는다. 이번에는ROI합성·보간·SR·얼굴복원·위치warp를하지않는다. 바뀐객체가원본보다가늘다는이유로source실루엣에억지로맞추지않는다.

## 7. 평가: 원본복사와 진짜참조반응 구분

SOURCE / LAB_REF / IG_REF / REF_LAB raw / REF_IG raw,전체17장과local0/8/16·native30fps를보존한다. 이전B023/B024는역사자료로분리한다. 새두출력은같은canvas/timeaxis로표시하고좋은프레임만선별하지않는다.

주요축은다음이다.
1. reference package sensitivity: 같은P*와source에서두출력의외형이각참조방향으로구별되는가?
2. replacement evidence: REF_IG가source의검은Lab를유지하는가,아니면IG의관측색/무늬·얼굴·사지비율이반영되는가? 색상변경만이라면partial이다.
3. preservation: 원본사족자세·고개방향/순서·바닥/가구·camera가유지되는가? 체형차이때문에모든관절pixel이같아야한다고요구하지않는다.
4. integrity: 얼굴/귀/목/발·잔상·배경누수·경계/가림/접촉. 강아지가사라지거나원본개체가이중으로남지않는가?
5. temporal: 실제연속시청없으면UNVERIFIED. 재생조작성공·프레임시트·동일에이전트다중검토를독립사람평가로취급하지않는다.

breed/appearance반영,실제petidentity,source-motion·scene유지,제품수용을각각기록한다. 참조묶음에는RGB외에mask와pose/사진조건도다르므로순수identity단일변수라부르지않는다. 두출력이달라지기만하면성공이아니고,차이가각참조특징과맞아야한다. 무정보/nullreference대조군이없으므로참조필요성이나원인경로를완전히식별했다고하지않는다.

판정예시: 둘다Lab유지→source-copy/task실패가능성이남음. ref에따라외형만맞지만motion붕괴→identity반응증거+jointtaskFAIL. 둘다각ref외형과source동작/scene유지→한쌍의유망한reference-guided editing사례,일반화/상용품질아님. 색만변함→appearancePARTIAL. REF_LAB부터실패하면P*변화와불안정성한계를같이기록하고IG만불리하게원인단정하지않는다.

## 8. 공부·기록·제출

해설은same-ID에서source-copy가왜성공처럼보이는지, fixedtext/drive/noise와reference묶음교체의의미,mask/RGB모두변경되는한계,견종유사성과petidentity평가차이를이번실제코드·두출력에연결한다. 미세수치재현을위한추가커널검사를하지않는다.

착수전CHARTER/v2/HISTORY/ROADMAP/B024결과를읽고B024의개선을보존한다. 이번은연구방향변경이아닌,개선된입력표현을고정해실제교체기여를보는다음단계다. 실행전case입력·공통prompt·조건·평가·예산을기록하고commit/push한다. 종료후RESULTS/한국어해설/REPRODUCE/자원/HISTORY/ROADMAP갱신과remoteSHA확인. 데이터권한의기존허용범위와A/B경계를유지한다.

개인미디어·mask·casecaption의민감내용·latent·weights·절대경로·secret은공개하지않는다. 단일privateZIP를Spark/Mac /tmp에생성·전송하고CRC·manifest·hash·실제추출을검증한다. 새두raw/MP4/finallatent·두reference·source·전체비교·재현·실패근거를넣고대형weights/중복prefix제외. 같은실험의진행중작업을발견하면중복실행하지않는다.

이번한쌍후종료하고결과를먼저검토한다. 길이확장·다중개체·밈전체·학습·별도null/마스크/encoder경로제거실험은자동실행하지않는다. 다음연구하나는실제관측된병목에근거해제안만한다.

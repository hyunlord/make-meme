# V-002 사전 계획

작성: 2026-11-04T05:46:38Z 착수, 이 PLAN은 신규 입력 제작·모델 실행 전에 고정한다.
부모: V-001, branch docs/v-research-20261103, parent0cfd0ef1b66be66b20765b644f063894d4044b82. 기존worktree와변경보존.

## 목적과 부모 관측

사용자 직접 판정: V-001 E1은 “개가 움직이지만 원본과 전혀 다른 동작을 한다.” 이를 HUMAN_REVIEW의 새 근거로 보존한다. 낮은 공간·시간 조건 해상도와 depth대비는 원인 후보이며 분리된 인과시험으로 입증된 것은 아니다. E2는 보류, 재실행0. 현재Spark새boot와이전boot NVRM NV_ERR_NO_MEMORY 기록을 확인했으며 이전원격실행의정상종료를소급주장하지않는다.

## 고정 입력과 변형

원본[240,313),73프레임24fps. 실제track0=오른쪽앞Lab,track1=왼쪽뒤IG,반사track2/3. 기존앵커1장과SAM/depthraw/E1출력2개해시확인. imagegen/원본SAM/depth추론재실행0.
832×480: canonical1280×720→853×480→좌10/우11crop. Masknearest변환뒤square dilation Lab24px,IG12px,반사12px,합집합RGB(255,255,255). PNG readback세채널/면적검증. 원본팽창전마스크가평가정답이다.
M1: 마스크안127,밖원본. M2: 안기존depth,밖원본. M3: frame0전체앵커/전체mask0,이후M1. 기존앵커SAM실제두개체를공식VACE규약의흰배경crop2개로만든다. Prompt/seed20261103은동봉JSON그대로.
검증된DiffSynth VACE경로를재사용하며 공식수치기본50step/CFG5/shift16을명시한다. 기존runner의Euler scheduler는유지하고공식VACE UniPC와다름을기록한다. VACE마스크밖은조건이며출력pixelexact를가정하지않는다. BF16/tiledVAE와가중치선택은실제코드/헤더로검증한다.
LTX는부모1152×640/73/seed20261103/11steps/앵커/Union1.0그대로,canny만교체한다. 설치된LTX공식compute_reference의Canny계산을사용하되사용자고정92/200을사용한다(확인한공식현재기본100/200과다름). 1152×640에서계산하며Comfywrapper의별도512축소를도입하지않는다.

## 평가와 14B 선택

V-001 E1두개를먼저SAM측정. 출력각각SAM1회,canonical역환산·반사규칙부모유지. IoU는팽창전원본과배역별로계산한다. missing출력mask는empty이므로IoU0을포함한전체프레임평균과관측만평균/coverage를함께기록한다. SAM기술실패는점수0으로위장하지않고미측정/후보제외.
66/73이상실제2마리인M변형중Lab/IG전체프레임평균IoU최대. M1이eligible이고최고점과0.02이내일때M1우선; ineligible M1은선택불가, M2/M3정확동점이면M2우선. 후보없으면NO_14B_CANDIDATE. 결과전에해석고정.
14B1step측정1회,73예상150분초과이면49prefix,49예상225분초과이면ENGINE_TOO_SLOW. 49예측은동일probe의latent시간비로외삽하며추가probe없음. 측정값/한계기록.
출력SAM상태·IoU·궤적·뒤바뀜위치proxy·Lab/IG높이비·반사색참고·마스크밖MAE·비용을분리. 사용자품질HUMAN_REVIEW_PENDING,연속지각UNVERIFIED. 9시점시트,동기뷰어,빈양식.

## 메모리와 운영

V002전용기존guard사본. MemoryHigh=MemoryMax100GiB,보수적시작112GiB여유기준유지. 모든heavy할당기expandable_segments:True. 가중치dtype+T5+VAE+활성값peak추정<=100GiB증거필수,초과차단. pagecache중복가능성별도명시.
적재직전사용자설치명령sudo -n /usr/local/sbin/drop-caches만호출가능. 현재명령없음,ABSENT_CONTINUE로기록;다른sudo/설치/서비스수정없음. 커널journal현재읽기가능,worker시작이후새NV_ERR_NO_MEMORY첫건이면자체worker정상종료시도후ENGINE_STOPPED_NVRM/재시도0. 권한없으면기록후나머지가드유지.
OOM,가용<12GiB30초,PSIfull>25%60초,외부GPU/서비스충돌/관측오류중단을유지. 05:49UTC외부GPU작업관측,해당작업보존하며heavy시작하지않고CPU준비만진행. CPU/모델실행은단일root흐름,에이전트는CPU/static전용.

## 순서·예산·종료

인수/사전commit → CPU입력검증 → V001 E1 SAM2 → M1/M2/M3 → SAM/선택 → 14Bprobe/조건부1생성 → LTXcanny1 → 최종SAM/측정/뷰어 → 기록/전달.
신규영상최대5,14Bprobe최대1,품질재시도0,학습0,imagegen0,외부API0,Bernini0. 정상생성완료셀재실행없음.
전체7시간: 2026-11-04T12:46:38Z(21:46:38KST)종료,12:16:38Z(21:16:38KST)부터기록전달. 시간상완료예측안되는생성은시작하지않는다. 입력/모델/환경기계오류는같은범위에서수정하되가드중단재시도없음.
공개문서/코드/hash만stage/push. 개인미디어/경로/원시로그/weights는private. 기존ZIP/과거판정보존,새compactZIPMac전달CRC/실제추출/hash확인. 자체process종료와외부작업보존확인. V003자동예약0.

## 14B 사전 메모리 판정

신규 출력 확인 전 정적 적재 코드와 실제 저장 dtype 크기로 보수적 peak를 계산했다. 14B는약128GiB 추정으로100GiB상한초과, ENGINE_BLOCKED_MEMORY_ESTIMATE. 후보 선택은 M1–M3 측정 후 규칙대로 기록하되 후보가 있어도 이번14Bprobe/생성은 시작하지 않는다. 원본FP32전체CPU복사는없지만pagecache와temporaryCUDA중복을제외할근거가없다. 별도변환·새offload구현을추가하지않는다. SAM/1.3B/LTX는각40/85/95GiB계획추정으로개별guard대상이며실측상한을보장하는수치가아니다.

## 시작 관측 및 CPU 검증 추가 기록

2026-11-04T06:11Z: 최초 SAM 기준선 CPU guarded admission은 외부 GPU 작업으로 거절됐다. Worker 생성·모델 적재·SAM 호출은 모두 0회이며 해당 stage와 원본 관측을 보존한다. 외부 배치의 일시적인 GPU 공백은 종료로 간주하지 않는다. 실행 중인 엔진의 안전 중단을 재시도하지 않으며, 현재는 모델 실행 전 외부 자원 충돌 상태다.

M1–M3와 LTX canny의 직접 CPU 입력 검사 통과(torch import 없음). LTX의 누락된 --config 인자는 아직 실행하지 않은 stage에 수정 후 freeze를 갱신했다. 원래 CLI 오류는 비공개 기록에 보존한다. 정적 검토에서 blocking defect 없음; 실제 추론 검증을 대신하지 않는다.

## 이번 실행 종료

2026-11-04T06:11:38Z 관측에서 외부 배치가 여전히 살아 있었다. 30회 관측(06:01:22–06:11:03Z) 동안 parent가 모두 존재했고 GPU 작업이 반복됐다. 신규 모델 실행을 시작하지 않고 BLOCKED_EXTERNAL_GPU로 종료한다. 예산은 0회 사용이며 자동 재시작은 예약하지 않는다. 14B는 별도 사전 메모리 상한으로 차단된다. 준비된 입력과 미실행 검토물을 전달하며 모델 품질 결론은 내리지 않는다.

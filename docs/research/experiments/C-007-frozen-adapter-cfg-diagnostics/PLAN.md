# C-007 사전 고정 — 동결 adapter의 분기·CFG·생성 경로 진단

부모 c4aef32de21de4073bd4eb1861df4d35f2eda793와 C-006 결과는 불변이다. 작업 시작 2026-10-30T10:07:03Z, 전체 상한14:07:03Z, GPU 작업 종료 목표13:37:03Z이다. 기존 1.3B·현재 C003 guard·절대경로 run_guarded를 재사용하며 가드/환경/서비스 정책을 수정하지 않는다.

질문은 단일 분기 회귀, CFG 분기 차이의 결합, 반복 경로 이탈을 구분하는 것이다. 어떤 원인도 먼저 확정하지 않는다. 학습·optimizer·backward·update·imagegen·tracker·SAM·다운로드는 모두0회다.

## 고정 입력과 순서

진단은 validation elephant/goat, 영상은 사전순 첫 validation elephant다. 기존 mask-given 동적 layout, 실제 source 양끝, prompt, negative, points/exclusions, 독립 endpoint VAE patch를 유지한다. step0/128/256 checkpoint 실재/hash와 정확한 grid는 INFERENCE_INPUT_MANIFEST.json에 둔다.

one-step: 1000-grid shift5에서 sigma0.95/0.75/0.50/0.20/0.05의 최근접index208/625/833/952/990. 영상별 CPU noise seed20261101/20261102 하나를 다섯 sigma 및 모든 조건에 공유한다. native/bypass/0ON/0NULL/128ON/128NULL/256ON/256NULL × positive/negative ×10state=160forward. native/bypass/zero 허용오차atol=rtol=1e-3이며 실질 불일치면 IMPLEMENTATION_MISMATCH로 중단한다.

영상 순서는 BASE_1→ON_1→BASE_5→ON_5다. ON은256만 사용한다. Euler50/shift5/seed20261028/416×240/33frames/BF16/SDPA/tiledVAE/VACE1.0 고정. CFG1은positive50call, CFG5는positive50+negative50call, 합계300call/200step/4decode다. 2×2 완료 셀을 다시 생성하지 않는다.

각 영상 pre-step0/25/40/47/49의latent/실제branch/combined prediction을 읽기전용 저장한다. BASE_5/ON_5의10state에서 native/ONpositive/negative40forward로 같은-state delta와 실제저장예측 replay를 비교한다. 추가fixture/replay예비16forward, sampler기계적예비1, VAE복구1 상한이며 품질retry0이다. 안전중단은재시도하지않는다.

## 정답 분리와 계측

진단만clean_latent/loss_mask를읽는다. 생성과rollout replay는정확9key whitelist(sequence,split,prompt,patches,anchor_valid,positions,visible,valid,box_wh) sidecar를쓴다. clean/context/lossmask를sidecar에복사하지않고VACE/text는실제pipeline에서다시인코딩한다. 별도사후CPU비교로cache/실제context차이를기록한다.

CFG는Literal1/5와실제호출config.guidance에연결한다. native연산은불변이고trace는actualpositiveflag+contexthash로분기를확인한다. sigma와BF16 modeltimestep, 영상frame t와samplerstep j를구분한다. residual은원래projection한번의출력과원래덧셈결과만관측하며FP32통계가sampler연산을바꾸지않는다. 실제gate/kernel의기하support도읽기전용계산한다. 큰tensor는state별해제하고trace목표256MiB이하로보존한다.

## 사전 관측과 판정

Root가 source전체33장과고정9장을출력전정적검토했다. 코끼리뒤/왼측면이주로보이며머리/코는화면오른쪽에가려져있다. 화면왼쪽뒤쪽으로보이는발은0–12낮고16–23들려굽혀지며27–32더수직으로내려온다. 몸통의우향/멀어짐은작고카메라는대체로고정이다. 분무/먼지가하체를가려정확접촉·해부학적좌우는UNCERTAIN이다. 돌담/건물/나무/전경바위/분무원점을별도보호항목으로본다. 숨은관절GT를만들지않는다.

같은CFG의ON−BASE를먼저비교하고두CFG간증분회귀를해석한다. 전체33장/고정9장의외형·거친진행·색번짐·중복윤곽·배경·양끝을같은index로평가한다. temporal은실제연속지각검수없으면UNVERIFIED다. 가능한중복판정은BRANCH_REGRESSION/CFG_INTERACTION_SUPPORTED/LOW_SIGMA_REGRESSION/ROLLOUT_SENSITIVITY_OBSERVED/COMMON_ADAPTER_EFFECT/IMPLEMENTATION_MISMATCH/INCONCLUSIVE이며대안설명을남긴다. latentMSE를motion점수로쓰지않고CFG를항상5배오류로설명하지않는다. 새CFG기본채택/후속학습은자동시작하지않는다.

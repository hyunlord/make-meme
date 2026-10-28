# C-002 사전 고정 계획

시작2026-10-28T15:43Z, heavy cutoff18:23Z, 전체종료18:43Z. CPU 준비 목표40분. C-001 완료commit `5ba0cdbe4a11bb35ae77ce638acbbcc501e90da2`의 기존 C branch/worktree를 이어 사용한다. A/B와 C-001 실패·PARTIAL·UNVERIFIED를 보존한다.

질문은 하나다. 같은 양끝 앵커와 모델에서 원본 SAM 윤곽의 시간 변화를 중간 RGB조건으로 전달하면 ENDPOINT 또는 정적 윤곽보다 원본 진행을 더 잘 따르는가? 윤곽에는 원본 체형도 포함되며 순수 motion만의 분리가 아니다.

고정 순서: 차량MOV → 차량STILL → 개MOV → 개STILL. 신규heavy4 + 기계복구예비1(총≤5), 각50scheduler step, 기대100model_fn call. 품질재시도0, ENDPOINT 재생성0, imagegen0, SAM 재분석0, 설치/다운로드/학습/새모델0. 최종latent뒤 오류는 sampler 재실행 없이 보존물 재사용하며 VAE-only복구는 전체≤1이다. 실제위험시 자동재시도/가드완화없음.

C-001 source(car-roundabout30..62,dog0..32), target(car-shadow0,dog-gooses85), 네 anchor, source mapping/resize와 두 ENDPOINT MP4를 그대로 쓴다.832×480·33frames·양끝0/32·preview16fps, source_fps=null/timebase_assumed=true. 파일33/16초와 표본간32/16초를 구분한다.

SAM selected source track0의 기존66개 binary832×480마스크만 쓴다. 원본과mask좌표·sequence·nonempty를 검사했고, 독립 정적검토에서두clip 주대상이 유지됐다. 차량 초기 일부마스크에1–3px원격speckle이 있어bbox가커질수있다. 삭제/GT교체/재분할하지 않고 외곽선renderer의실제입력으로보존한다. 개mask의 털/꼬리/발 경계는 근사이며 관절정답이 아니다.

L_t는 흰uint8RGB바탕/검정external simplecontour/두께3px이며 공식VACE layout semantics를 따른다. MOV중간은L_1..L_31, STILL중간은L_0반복, 양끝은동일anchorRGB다. G는양끝전체0/중간전체255이고S나L로대체하지않는다. reference=None, PNG/in-memory전달이며sourceRGBoverlay는검토용이다.

C-001의WanVACE1.3B/revisions/실파일hash·BF16·SDPA·tiledVAE·Euler50·CFG5·shift5·seed20261028·rand_devicecpu·각caption/negative를고정한다. 실제vace_scale도기존default유지기록.33→9nearest-exactmask와inactive/reactive경로를수정하지않는다. 최초원래model_fn직전실제latents와vace_context shape/dtype/hash/finite를기록한다. 추가forward/RNG변경없음. 새MOV/STILLnoisehash를비교하며 C-001은기록부재로같은seed/경로까지만주장한다.

사전평가: 차량은target은색높은차체/루프레일/뒤등유지와Mini회귀, 우측이동/후면노출, source8/16/24위치·크기·회전, 파란원형표지/난간/배경차량, 바퀴접촉을본다. 개는검정/흰특징/원본체형회귀, 접근/방향, source8/16정면진행·고개·발디딤, 꼬리/얼굴/다리, 울타리/수풀/잔디를본다. C-001개종료anchor의낮은자세/발위치가source와충돌함을전제한다.

전체33장과동일index0/4/8/12/16/20/24/28/32를비교한다. 위치·크기/거친방향/시간진행/내부자세/외형/endpoint/장면/접촉/temporal/비용을분리한다. 새출력segmentation/pose추론과시간재정렬없음. 실제연속지각검수없으면temporal=UNVERIFIED다. MOV↔STILL은종료anchor충돌정도도다를수있어순수시간인과효과라고하지않는다.

기존C-001guard와absoluteCPUroute를그대로재사용한다. C001접두어가있는unit/attempt 식별은그adapter계약때문이며각이름에C002와cell을포함한다. threshold·서비스정책의의미·한도계산은변경하지않는다. 공통연구lock과cell별baseline, 한영상sampler→decode의동일baseline을유지한다. 실행전코드/조건commit+push+remoteSHA, 이후실제4영상과비교/수학/비용/한계를기록한다. compact는원MP4와명시한검토파생본, full은raw/latent/무손실전체프레임이다. 양호스트/tmp CRC·추출·payload·전송hash를확인하고종료한다.

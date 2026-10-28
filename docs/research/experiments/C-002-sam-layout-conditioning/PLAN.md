# C-002 사전 고정 계획

시작 2026-10-28T15:43Z, heavy cutoff 18:23Z, 전체 종료 18:43Z. CPU 준비 목표 40분. C-001 완료 commit `5ba0cdbe4a11bb35ae77ce638acbbcc501e90da2`의 기존 C branch/worktree를 이어 사용한다. A/B와 C-001 실패·PARTIAL·UNVERIFIED를 보존한다.

질문은 하나다. 같은 양끝 앵커와 모델에서 원본 SAM 윤곽의 시간 변화를 중간 RGB 조건으로 전달하면 ENDPOINT 또는 정적 윤곽보다 원본 진행을 더 잘 따르는가? 윤곽에는 원본 체형도 포함되며 순수 motion만의 분리가 아니다.

고정 순서: 차량 MOV → 차량 STILL → 개 MOV → 개 STILL. 신규 heavy 4 + 기계 복구 예비 1(총≤5), 각 50 scheduler step, 기대 100 model_fn call. 품질 재시도 0, ENDPOINT 재생성 0, imagegen 0, SAM 재분석 0, 설치/다운로드/학습/새 모델 0. 최종 latent 뒤 오류는 sampler 재실행 없이 보존물 재사용하며 VAE-only 복구는 전체≤1이다. 실제 위험 시 자동 재시도/가드 완화 없음.

C-001 source(car-roundabout 30..62, dog 0..32), target(car-shadow 0, dog-gooses 85), 네 anchor, source mapping/resize와 두 ENDPOINT MP4를 그대로 쓴다. 832×480·33frames·양끝 0/32·preview 16fps, source_fps=null/timebase_assumed=true. 파일 33/16초와 표본 간 32/16초를 구분한다.

SAM selected source track 0의 기존 66개 binary 832×480 마스크만 쓴다. 원본과 mask 좌표·sequence·nonempty를 검사했고, 독립 정적 검토에서 두 clip 주대상이 유지됐다. 차량 초기 일부 마스크에 1–3px 원격 speckle이 있어 bbox가 커질 수 있다. 삭제/GT 교체/재분할하지 않고 외곽선 renderer의 실제 입력으로 보존한다. 개 mask의 털/꼬리/발 경계는 근사이며 관절 정답이 아니다.

L_t는 흰 uint8 RGB 바탕/검정 external simple contour/두께 3px이며 공식 VACE layout semantics를 따른다. MOV 중간은 L_1..L_31, STILL 중간은 L_0 반복, 양끝은 동일 anchor RGB다. G는 양끝 전체 0/중간 전체 255이고 S나 L로 대체하지 않는다. reference=None, PNG/in-memory 전달이며 source RGB overlay는 검토용이다.

C-001의 WanVACE1.3B/revisions/실파일 hash·BF16·SDPA·tiled VAE·Euler50·CFG5·shift5·seed20261028·rand_device cpu·각 caption/negative를 고정한다. 실제 vace_scale도 기존 default 유지 기록. 33→9 nearest-exact mask와 inactive/reactive 경로를 수정하지 않는다. 최초 원래 model_fn 직전 실제 latents와 vace_context shape/dtype/hash/finite를 기록한다. 추가 forward/RNG 변경 없음. 새 MOV/STILL noise hash를 비교하며 C-001은 기록 부재로 같은 seed/경로까지만 주장한다.

사전 평가: 차량은 target 은색 높은 차체/루프레일/뒤등 유지와 Mini 회귀, 우측 이동/후면 노출, source 8/16/24 위치·크기·회전, 파란 원형 표지/난간/배경 차량, 바퀴 접촉을 본다. 개는 검정/흰 특징/원본 체형 회귀, 접근/방향, source 8/16 정면 진행·고개·발디딤, 꼬리/얼굴/다리, 울타리/수풀/잔디를 본다. C-001 개 종료 anchor의 낮은 자세/발 위치가 source와 충돌함을 전제한다.

전체 33장과 동일 index 0/4/8/12/16/20/24/28/32를 비교한다. 위치·크기/거친 방향/시간 진행/내부 자세/외형/endpoint/장면/접촉/temporal/비용을 분리한다. 새 출력 segmentation/pose 추론과 시간 재정렬 없음. 실제 연속 지각 검수 없으면 temporal=UNVERIFIED다. MOV↔STILL은 종료 anchor 충돌 정도도 다를 수 있어 순수 시간 인과효과라고 하지 않는다.

기존 C-001 guard와 absolute CPU route를 그대로 재사용한다. C001 접두어가 있는 unit/attempt 식별은 그 adapter 계약 때문이며 각 이름에 C002와 cell을 포함한다. threshold·서비스 정책의 의미·한도 계산은 변경하지 않는다. 공통 연구 lock과 cell별 baseline, 한 영상 sampler→decode의 동일 baseline을 유지한다. 실행 전 코드/조건 commit+push+remote SHA, 이후 실제 4 영상과 비교/수학/비용/한계를 기록한다. compact는 원 MP4와 명시한 검토 파생본, full은 raw/latent/무손실 전체 프레임이다. 양 호스트 /tmp CRC·추출·payload·전송 hash를 확인하고 종료한다.

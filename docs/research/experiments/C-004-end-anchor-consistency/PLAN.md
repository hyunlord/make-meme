# C-004 사전 고정 — 종료 앵커 충돌 진단

작성2026-10-30 KST00:28:53. 이력부모22f93081b335ae0c27ec62da57116e119ffc2573; 비교부모C002853ee952795246648b3a6e46d37d5dead03abef3. 기존 C track에서 작업하며 과거 결과를 보존한다.

질문은 기존 동적 윤곽/시작 앵커/모델을 그대로 두고 source local32에 더 맞춘 종료 앵커 한 장이 종료부 또는 중간 진행을 개선하는가다. 새 알고리즘·C003구조선은 없다. 전체90분, 마지막15분전 heavy시작 종료; native1call/1candidate, 적합하면 정상영상1×50step100call, 기계적heavy예비1, VAE복구1, 품질재시도0. 새다운로드/패키지/학습/SAM/추출0. C003 현재guard를 그대로 사용하며 safety실패시 우회/재시도하지 않는다.

## 실제 사전 관측과 수용 기준

Source32는 이미 머리가 낮다. 몸통은 화면 위쪽 뒤로 이어지고 코는 몸통 왼쪽 아래, 화면 왼쪽 앞발은 코 아래 전방, 화면 오른쪽 앞발은 뒤쪽 위에 보인다(OBSERVED). 후방 다리·관절·정확한 접촉은 가림/blur로 AMBIGUOUS/OCCLUDED다. 기존 종료도 큰 배치와 앞발 배열은 비슷하지만 목/주둥이와 앞몸통의 낮은 웅크림 인상이 더 크다. 차이를 일반적인 기립 자세로 바꾸지 않는다. target 털·체형 차이로 실루엣 pixel일치는 요구하지 않는다.

새 앵커는 큰 낮아짐 충돌 감소, 검정/흰 얼굴·가슴·발 및 시작 디자인 유지, 단일개체/중복신체없음, 큰 카메라·배경·배치 변화없음을 확인한다. 명확하면 SUITABLE_FOR_COMPARISON, 일부오차지만방향개선이면 PARTIAL_BUT_USABLE로영상진행. 충돌유지/큰손상이면 ANCHOR_UNSUITABLE/VIDEO_NOT_RUN으로종료한다. 영상결과전 판정을 고정하며 두 번째 imagegen은 없다.

## 고정 입력과 평가

C001 dog33장/source_fps=null/timebase_assumed=true,832×480/preview16fps,시작앵커/target reference/caption/negative/C002layout31/G는 그대로다. Native입력3장의 역할·hash·정확한prompt는 IMAGEGEN_REQUEST.json에 고정했다. 기존 end는 비교전용으로 native입력에서 제외한다. 원출력보존후 C001 aspect-fit LANCZOS+blackpadding만 적용한다.

영상은 C002 video_generate.py 변경없이 config end_anchor/output만 변경한다. C003 bootstrap/guard도 그대로다. Euler50/CFG5/shift5/seed20261028/cpu RNG/BF16/SDPA/tiledVAE/scale1.0/referenceNone. 실제condition0..31pixel동일/32만변경,G/reactive동일/inactive32만변경,noise/mask64를C002와비교한다.33→9mask한계보존; latent마지막만변경assertion없음.

SOURCE/target/start/oldend/newend/C002/C004를 전체33장 같은인덱스,고정0/4/8/12/16/20/24/28/32로 본다.1–28중간/29–31종료접근/32마지막을분리한다. 머리·몸통높이·보이는앞발배열,접근·크기,검정흰외형,배경,형태손상,앵커충실도를평가한다. 관절/접촉GT없음; 연속지각검수없으면temporalUNVERIFIED. 새앵커에이미있던배경변화와영상에서생긴변화를구분한다. 종료앵커전체변경효과이며자세하나의순수인과효과아니다.

판정은 ENDPOINT_GAIN_ONLY/MIDCLIP_GAIN/TRADE_OFF/NO_ESTABLISHED_GAIN/WORSE/INCONCLUSIVE 중 증거에따른다. 한사례한seed이며추가실험자동시작없음. 실제결과·한국어수식/코드해설·비용·검증된Spark/Mac compact와remoteSHA까지기록한다.

# B034 CONTINUATION_02 — 보호 서비스 상태 계약 amendment

사용자가 [의뢰서 전체](WORK_ORDER_KO.md)의 수행을 승인했다. 기준원격/로컬HEAD `a72e65e457a6164b648ada7323e6dd3008088a25`를 확인했다. 기존 BLOCKED/UNKNOWN/CONT01실패 및 사용장부는 변경하지 않는다.

시작2026-10-27T12:44:39Z, 새 heavy cutoff14:29:39Z, 전체harddeadline14:44:39Z. 서비스읽기확인목표20분, 작은정책수정목표30분. 마지막15분기록전달. 남은CONT02 STEP1(40/80/40)/decode1만 허용하며BASE/CONTROL/encoder/이미지/학습/설치0이다.

## 운영 계약

서비스의 실제관리주체·배포계보·논리적신원을 먼저 확인한다. 선택된 연구경로가 queue를 생성 의존성으로 사용하지 않고 충돌방지관측에만 사용하는 경우에만 optionalprotected로 선언한다. 관리자나필수가동요구를 확인하지 못하면그항목을BLOCKED로보고한다.

ACTIVE_IDLE은 확인된논리/현재runtime신원+올바른queue실제0/0과기타안전기준을필요로한다. STOPPED_CONFIRMED는 user승인stopped_allowed와managerinactive/stopped+process/child/cgroup/listener/GPUabsence+noactivating/restarting/jobs를2초간격3표본으로확인해야한다. connectionrefused/unitnotfound/권한부족만으로허용하지않는다.

논리manifest(unit/container·owner·exec/deployment·endpoint·policyhash)와현재boot/runtime(PID/starttime/invocation/cgroup 또는instance없음) snapshot을분리한다. 실행중새PID자동등록0. 중지서비스활성화/active재시작/외부GPU/queuebusy는자체worker만중단한다. 다른서비스시작/종료/재시작/disable0.

queue상태는 AVAILABLE+실제counts, UNAVAILABLE+null, NOT_APPLICABLE_CONFIRMED_STOPPED+null로구분한다. null을0으로바꾸지않는다. 기존빈queue표현과과거실패를소급수정하지않는다.

72GiBstart/24GiBheadroom/swap0, 외부GPU보호, 기존자체worker종료identity와bootstrap그대로. 새전체watchdog/controller없음. 새 CPUfixture6상태와기존24회귀를확인하고 실제preflight와supervisor/worker가같은manifest/정책을검증한다. 모델을검사용으로올리지않는다.

## 실행 순서와 고정 입력

관리자/서비스역할감사 → 조건이충족된작은정책·CPU검사 → 실제manifest/config/inputhash고정commit → freshsafety → STEP1 → final latent원자저장/readback → 자체종료/자원회복 → freshsafety → D1 → 동일E RGB_POST/전체17비교 → 기록ZIP전송.

SCAIL·precision·loader·FA·B033cleanconstraint·noise/RNG/scheduler·양CFG·reference/driving·E/M·crop은그대로다. UniPC40/shift3/CFG5/replacement,896×512/17f/preview24fps/sourcefpsnull/timebaseassumed. LoRA/ALG/B029/manualRoPE OFF. 새support/강도/스케줄탐색0.

## 품질 판정·제출

기존BASE+POST/FINAL_ONLY+동일POST/STEP+동일POST의내부·경계추가이득을본다. 클래식target외형/SUV잔존/접근동작/도로산울타리/경계접촉그림자를구분한다. 잘못된BASE SUV support의제약을기록한다. target없으면nonregressionPASS금지; 배경개선과결합FAIL은함께기록가능. temporalUNVERIFIED(실제연속시청없음).

실행되면새STEPrawlatent만full,비교미디어는작은compact로분리한다. 운영단계차단이면새증거만작게보존한다. 공개에는개인PID/bootID/전체command/개인path/cache/weights없음. 양호스트CRC/실제추출/payloadhash/byte동일성을실제범위로검증한다. 같은범위뒤종료,추가실험예약0.

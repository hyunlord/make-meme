# B-034 CONTINUATION_02 — 보호 서비스 상태 계약 갱신과 미사용 STEP 완료

상태: 제안 의뢰서. 이 문서 작성 중 Spark 접속·서비스 변경·GPU 실행·GitHub 쓰기는 하지 않았다.
기준 기록: `a72e65e457a6164b648ada7323e6dd3008088a25`
저장소: `hyunlord/make-meme` / 브랜치: `docs/b-research-20261022`

## 0. 이번 지시의 승인 범위

사용자가 실행 담당자에게 이 문서의 수행을 지시할 때, 아래의 **명시적인 보호 서비스 상태 정책 변경**과 아직 사용하지 않은 STEP 작업을 승인한 것으로 적용한다. 이전 의뢰서의 ‘과거 PID가 반드시 존재해야 한다’는 전제를 조용히 우회하는 것이 아니다.

- 기존 큐 서비스가 연구 런타임의 필수 의존성이 아니라 다른 작업과의 충돌을 피하기 위한 보호 대상인 경우에만, **확인된 중지 상태도 허용하는 선택적 보호 서비스**로 이번 실행 정책을 변경할 수 있다.
- 서비스의 관리 주체·논리적 신원·현재 상태가 확인되지 않거나, 별도 운영 요구에서 반드시 가동되어야 하는 서비스라면 선택적으로 바꾸지 않는다. 그 구체적인 미확인 항목만 보고한다.
- 다른 서비스를 시작·종료·재시작·비활성화하거나, 큐를 삭제·가짜 응답으로 대체하지 않는다. 해당 서비스의 사용자 작업을 방해하지 않는다.
- 메모리·swap·미분류 GPU 작업·자체 worker 종료 신원 확인은 유지한다.
- 새 연구 번호, 새 모델, 새 비교 과제는 추가하지 않는다. B-034의 남은 비교를 마무리하는 운영 변경이다.

## 1. 기존 결과와 확인 범위

CONTINUATION_01의 loader 변수 누락과 실패 시도는 보존한다. CONTINUATION_02의 실제 Spark preflight 4회·CPU 검사 24개 PASS도 보존한다. 이번 마지막 재개에서는 heavy/model load/sampler/decode가 모두 0회였으므로, 그 단계에서 GPU 예산을 새로 소비하지 않았다.

기존 BASE target 외형 FAIL, FINAL_LATENT_ONLY의 동일 후합성 뒤 추가 이득 미관찰, 비강체 ANCHOR_UNSUITABLE, B-033의 한 사례 국소 PARTIAL은 변경하지 않는다. STEP 효과는 아직 NOT_RUN/INCONCLUSIVE다.

업로드 기록에는 기존과 다른 boot identity, 부재한 과거 보호 PID, 큐 요청 실패, 빈 GPU PID 관측이 있다. 이것을 재부팅의 이유나 이전 SSH 장애·종료 가드 원인의 확정 근거로 쓰지 않는다. 현재 안전 여부는 실행 시 다시 관측해야 한다.

## 2. 최소한의 읽기 전용 상태 확인

기존 승인 SSH alias, 같은 host 및 namespace에서 확인한다. 본 확인은 목표 20분으로 제한하며 일반적인 호스트 복구/서비스 운영 프로젝트로 확대하지 않는다.

1. 현재 boot ID·uptime·실제 실행 사용자와 기존 설정을 확인한다.
2. 기존 서비스 정의·실행 manifest·기존 포트 8190의 관리 주체를 먼저 찾는다. 이름을 추측해 아무 서비스나 대상으로 삼지 않는다.
3. 관리자가 systemd이면 실제 unit의 LoadState/ActiveState/SubState/MainPID/InvocationID/ControlGroup/ExecStart 및 활성화 대기 상태를 읽는다. 컨테이너 등 다른 관리자라면 해당 관리자의 동등한 상태를 읽는다. 새 관리 도구를 설치하지 않는다.
4. 같은 호스트/namespace의 listener, 해당 서비스 프로세스와 자식/cgroup, GPU 프로세스, queue 응답을 각각 확인한다.
5. 실제 필수 연구 실행 경로가 이 큐 서비스에 호출을 보내는지, 단지 안전 관측에만 사용하는지 선택된 코드 경로에서 확인한다. 보호 목적뿐이라면 중지 상태 허용이 가능한 설계다.

`connection refused` 하나, 빈 GPU 목록 하나, 또는 과거 PID 부재 하나만으로 중지 상태를 확정하지 않는다. `unit not found`나 권한 부족도 정상 중지와 같지 않다. 확인 가능한 관리 주체가 없으면 추측하지 않는다.

## 3. 서비스 선언과 실행 중 PID를 분리한다

기존 allowlist를 비워서 검사를 통과시키지 않는다. 과거 파일은 그대로 보존한다. 새 실행에 대해 다음 두 층의 작은 manifest를 만든다.

A. 논리적 서비스 선언
- 알려진 서비스의 실제 관리 주체/unit 또는 컨테이너 식별
- 실행 사용자·실행 파일/배포 경로·기존 설정의 계보
- 기존 endpoint
- 이번 사용자의 지시에서 파생된 `stopped_allowed`와 정책 문서 해시

B. 이번 실행의 runtime snapshot
- 현재 boot identity
- 확인된 서비스 상태
- active인 경우 현재 PID/starttime/unit invocation/cgroup 등
- stopped인 경우 runtime instance는 없음과 그 확인 근거

재시작 뒤 PID가 다르다는 이유만으로 전부 금지하지 않되, GPU에 보이는 아무 프로세스나 새 보호 대상으로 등록하지도 않는다. 논리적 배포 신원을 먼저 확인한 뒤 현재 runtime snapshot을 한 번 고정한다. 실행 중 자동 PID 재등록은 하지 않는다.

## 4. 세 가지 상태를 명시적으로 처리한다

### ACTIVE_IDLE

알려진 서비스의 논리적 신원·현재 프로세스 신원이 확인되고, 올바른 endpoint가 정상 응답하며 실제 running/pending이 모두 0일 때만 후보 상태로 인정한다. 메모리·GPU·다른 서비스 검사까지 통과해야 시작한다.

ACTIVE 상태인데 큐 연결이 안 되거나, 응답의 소유자가 불명확하거나, 작업이 있으면 차단한다. endpoint가 달라졌다는 추측으로 임의 포트를 선택하지 않는다.

### STOPPED_CONFIRMED

이 서비스가 선택적 보호 대상임이 확인되고 위 정책 변경이 적용됐을 때만 허용한다. 다음을 함께 관측한다.
- 서비스 관리자의 inactive/stopped 상태와 실제 프로세스 부재.
- 서비스 관련 listener·자식 프로세스·GPU 작업이 없음.
- activating/restarting/대기 중인 manager job 등 관측 가능한 전환이 없음.
- 같은 범위의 독립된 관측이 일치함. 예: 2초 간격 3개 표본.

이때 queue는 `running=0`이 아니라 `NOT_APPLICABLE_CONFIRMED_STOPPED`, count는 null로 기록한다. 중지된 서비스가 다시 켜지면 실행 조건이 달라지는 것이므로 자동으로 무시하지 않는다.

### UNKNOWN_OR_CONFLICT

권한 부족, 관리자 미확인, failed/activating/restarting 상태, listener/프로세스와 관리자 상태 불일치, active 서비스의 queue 불가, 미분류 GPU PID, busy queue는 모두 차단한다. 실패를 정상 중지로 재분류하지 않는다.

현재 snapshot에서 시작 가능해도 실행 중 상태는 계속 관측한다. 중지된 서비스가 시작되거나, 기존 active 서비스가 재시작되거나, 새 외부 GPU 작업/queue 작업이 나타나면 기존 정책에 따라 **이번 자체 연구 worker만** 안전하게 중단한다. 외부 서비스를 끄거나 disable하지 않는다. 이것은 충돌을 완전히 원자적으로 방지하는 예약 시스템이 아니며, 기존 플랫폼에 공유 작업 lock/예약 방식이 있다면 재사용한다.

## 5. 관측 실패를 빈 큐로 표현하지 않는다

현재 safety.py는 요청 전 빈 목록을 초기화하므로, 요청 실패 뒤에도 queue_counts가 0/0으로 남는다. errors 때문에 현재 코드는 차단했으며, 이를 이미 우회한 것으로 보고하지 않는다.

새 관측은 다음을 구분한다.
- 정상 응답: status=AVAILABLE, 실제 counts.
- 요청 실패: status=UNAVAILABLE, counts=null, 원시 오류.
- 위 조건으로 확인된 정상 중지: status=NOT_APPLICABLE_CONFIRMED_STOPPED, counts=null, 관리자 근거.

null/관측 실패를 숫자 0으로 바꾸는 fallback을 넣지 않는다. 기존 보고서 값은 소급 수정하지 말고 새 관측 형식의 변경 이유를 기록한다.

## 6. 작은 코드 변경과 CPU 확인

검증된 bootstrap, loader 초기화, 자체 worker 종료 신원 처리는 재사용한다. 새 전체 watchdog framework, controller, 커널 검사는 만들지 않는다.

추가 CPU 계약은 다음 상태에 한정한다.
1. 신원이 일치하는 active/idle은 다른 안전 조건 통과 시 허용.
2. active인데 queue 요청이 실패하면 차단.
3. 정책과 관리자/프로세스 근거가 모두 있는 stopped만 허용.
4. 포트 실패만 있고 관리자 근거가 없으면 차단.
5. PID 재사용·boot 변화·논리 신원 불일치·새 외부 작업은 차단 또는 새 실행 전 재확인.
6. stopped로 시작한 서비스가 실행 중 활성화되면 다음 GPU 단계 금지 및 기존 자체 작업 중단 정책 적용.

기존 24개 fixture는 회귀검사로 재사용하고, 전체 파이프라인 감사를 다시 하지 않는다. 실제 worker의 preflight와 실행이 같은 정책 함수와 manifest를 사용하는지 확인한다. 모델을 적재해 안전 검사를 테스트하지 않는다.

코드·manifest·허용 정책과 예상 변경을 실행 전에 GitHub 연구 브랜치에 고정한다. 개인 PID·boot ID·전체 command·개인 경로는 공개하지 않는다. 논리 정책과 비민감 코드·해시만 공개한다.

## 7. 안전 확인 뒤 미사용 STEP과 decode까지 진행

새 운영 계약과 fresh safety가 통과하면 보고서만 쓰고 멈추지 않고 같은 작업에서 잔여 비교를 수행한다. 통과하지 못하면 바뀌지 않은 CPU 검사를 반복하지 말고 실제 미확인 사실 하나와 근거를 남긴다.

시작 시점의 현재 사용 장부를 확인한다. 아직 사용하지 않은 CONTINUATION_02 예산만 사용한다.
- STEP heavy/model-loading attempt 최대 1회.
- full sampler 최대 1회: 40step·80forward·40clean conversion.
- 성공한 final latent의 VAE decode 최대 1회.
- BASE/CONTROL 재생성·재decode, source/reference encoder, 새 이미지·학습·설치·다운로드·재시도: 0회.

과거 CONTINUATION_01의 실패한 heavy 1회는 유지한다. 이번 추가 CPU 작업을 무제한 GPU 승인으로 해석하지 않는다.

입력·cache·실제 noise·RNG·scheduler·E/M·mask/crop·B-033 제약 코드를 바꾸지 않는다. UniPC40/shift3/CFG5, replacement=True, LoRA/ALG/B029 gate/manualRoPE OFF를 유지한다. 896×512·17프레임, source_fps=null/preview24fps/timebase_assumed=true를 유지한다.

기존 72GiB 시작 가용 메모리/24GiB 실행 headroom·swap0·외부 서비스 보호 기준은 그대로다. 모델 준비 전 live safety, STEP 종료/메모리 회복 후 decode 전 fresh safety를 각각 수행한다. final latent를 decode 전에 원자 저장한다. decode 실패 때문에 STEP을 다시 생성하지 않는다.

## 8. 최종 비교·판정

기존 BASE+RGB_POST, 기존 FINAL_LATENT_ONLY+동일POST, 신규 STEP+동일POST를 비교한다. 모든 raw와 전체17장 및 기존 crop도 남긴다. 추가 합성 규칙 변경·mask 축소·SR·warp·보간은 하지 않는다.

목표 클래식 차량의 외형, SUV/source형 잔존, 원본 접근 동작, 산·도로·울타리 보존, 경계·바퀴·접촉·그림자를 별도 판정한다.

배경만 좋아지고 target 외형이 없으면 보호 장면의 이득과 전체 편집 FAIL을 함께 기록한다. BASE부터 target이 없으므로 같은 SUV가 유지됐다는 것으로 target non-regression PASS를 주지 않는다. 실제 연속 시청 없이는 temporal=UNVERIFIED다.

마스크는 잘못된 BASE의 SUV support를 포함하는 output-assisted 조건이라는 한계를 유지한다. 방법 개선의 일반화·자동화·정확한 개체 일치로 확대하지 않는다.

## 9. 시간·기록·제출

전체 상한 2시간. 서비스 상태 확인·작은 정책 수정 목표 30분, 마지막15분은 기록·전달·종료에 남긴다. 이를 끝없는 서비스 복구로 확대하지 않는다. 실제 상태를 확인할 수 없으면 서비스 재시작이나 가드 완화 대신 구체적인 이유로 종료한다.

HISTORY·ROADMAP에는 이번이 연구 방법 변경이 아니라 부팅/서비스 상태 변화에 대한 운영 계약 amendment임을 기록한다. 기존 BLOCKED·UNKNOWN·실행 오류를 지우지 않는다. 새 코드·정책과 실제 실행 장부를 commit/push하고 remote SHA를 확인한다.

실행했다면 STEP 결과·기존 두 대조군·뷰어·보고서를 작은 compact로, 새 raw/latent를 full로 분리한다. 기존 큰 raw는 compact에 중복하지 않는다. 검증된 Spark/Mac /tmp 경로와 CRC·payload hash·전송 동일성을 실제 범위로 기록한다.

운영 확인 단계에서 멈추고 새 미디어가 없다면 대형 ZIP을 다시 만들 필요는 없다. 새로운 증거와 변경 파일만 작은 묶음으로 보존한다.

이 범위 뒤 종료한다. 새 모델·새 사례·강도 탐색·학습·후속 자동 실행은 하지 않는다.

---
### 작성 시 확인한 근거
- 원격 RESUME_RESULTS: a72e65e457a6164b648ada7323e6dd3008088a25 / continuation02/RESUME_RESULTS.md
- 같은 revision의 continuation02/code/safety.py
- 첨부 resume-evidence ZIP: 61,555 bytes, payload 44개 검증, SHA256 f9cf5959d4ff7371cdfaa4a90e928be823d0cef5eb2be791ae75d16c6605872c
- Linux kernel의 boot_id 문서: https://kernel.org/doc/html/v6.6/admin-guide/sysctl/kernel.html
- systemd 상태 정의: https://freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html

이 근거는 저장된 관측과 코드의 검토다. 작성자가 현재 Spark의 service manager나 GPU 상태를 직접 확인했다는 의미가 아니다.

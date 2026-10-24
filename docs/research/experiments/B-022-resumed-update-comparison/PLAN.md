# B-022 — 수치 반복성의 제한 확인과 동일 checkpoint의 20→100 update 비교

작성: 2026-10-24 · parent B-021 · **PLANNED / NOT_RUN**. 계획 게시만으로 GPU 실행·예산 승인이 되는 것은 아니다. 사용자가 실행 담당자에게 수행 지시를 전달할 때 아래 한정 범위를 적용한다.

## 0. 근거와 연구 질문

B-021 기준 commit `e4b860bdac827027c7e5092cd398350971b39303`의 RESULTS, phase_train.py, budget_contract.py를 읽었다. 실제20update·8평가, initial/입력/옵션 일치, 네 loss replay PASS. A/B 각 원소의 atol1e-7/rtol1e-5를 초과해100회 비교는 중단됐다. 기존 FAIL과 미실행 상태를 수정하지 않는다. loss차 최대2.831221e-7, adapter 최대절대차 약9.79e-7~5.24e-6라는 보고 수치만으로 영상 동등성·학습오류·FA2원인을 확정하지 않는다. B020/B021 prediction 직접 비교는 아직 없고, base 최종 hash/fresh reload/OFF도 B021에서 NOT_REACHED다.

첨부 B021 ZIP은 검토자의 container/Python에서 ClientError로 읽지 못했다. 33,089,507bytes/SHA `811285094906d7b718f43493d7f8857a65dbcbd1e62a796a004557dd76865b77`와257개 payload 무결성은 실행 담당자의 보고이며 이번 독립 검증이 아니다.

새 질문은 'B020과 파라미터를 매우 엄격하게 재현했는가'가 아니라 **'유효하게 저장된 B021의 같은20update checkpoint를 출발점으로, 80회를 더 학습하면 loss/실제 영상이 변하는가'**다. 원인 진단은 한정하고 이전 run과 개별 A/B 일치가 새 학습 진행의 필수조건인 것으로 두지 않는다. 이는 사후 B021 PASS 변경이 아닌 새 실험과 해석 범위의 명시적 변경이다.

## 1. 고정 범위·예산

- 기존 허용된 실제 Lab 자료·B020 조건/target/4prefix cache·모델·환경을 그대로 사용. P0, prefix full forward0, 새자료/모델/패키지 다운로드0, A/imagegen/외부생성0. ALG OFF/H0, 마지막block self_attn Q/V rank4·alpha4·dropout0만 학습한다.
- 신규 optimizer update **최대80회**: B021의20에서21~100으로 이어간다. 0부터100 재학습하거나 B020final20을 대체 출발점으로 사용하지 않는다.
- 업데이트 없는 tail진단/평가 forward 총 **최대40회**. 그중 동일상태 반복 backward 최대3회·optimizer0. 학습80backward와 구분한다. 반복성 확인은 최대30분으로 한정하며 새deterministic backend나 커널 수리 프로젝트로 확대하지 않는다.
- 학습 worker 최대1회(진단 포함), 기존 checkpoint의 실제 영상 비교를 위한 full sampler **최대2회**: 정확한 B021 step20 1회, 그 상태를 재개한 step100 1회. 각각40step80forward·D최대1회·retry0. B020의20회 영상은 보조 역사자료이지 새 matched step20 결과로 대체하지 않는다.
- 전체 작업 최대3시간. 기존72GiB 시작·24GiB 시스템headroom·swap0·타서비스 보호와 phase별 guard 유지. 기존 tail cap16GiB 규약은 CUDA 전체메모리의 hard cap 증명으로 해석하지 않는다. 기존 sampler cap은 해당 단계 규약 유지. 다른 작업 종료·sudo/driver/swap/clock/전역캐시 삭제 금지.
- 새rank/lr/학습층/tuple/seed/프롬프트 탐색0. 실패시 자기 작업만 종료. 정적타입 진단은 실행 correctness와 분리해 보존하고 억제/전면리팩터링하지 않는다.

## 2. 보존·정확한 재개가 먼저

1. B021 restart-020의 tensor/primitive schema, sidecar·해시·producer 계보, adapter-020과 A/B값·dtype 일치를 확인한다. 기본모델은 원래 고정된 가중치에서 로딩한다. 종료된 B021 프로세스의 base가 불변이었다고 이번 검사로 소급 증명하지 않는다.
2. parameter 객체와 이름 순서를 명시한다: q.A,q.B,v.A,v.B. optimizer state의 번호만 믿지 말고 이름/shape/dtype/param-group 순서와 연결한다. AdamW exp_avg/exp_avg_sq/step20, options, RNG, next tuple cursor2를 복원한다. update21은 train_2다.
3. optimizer는 정확한 새parameter 객체들로 구성한 뒤 저장상태를 load하고 state의 값·dtype·device 정책을 검사한다. capturable=False의 step tensor를 포함한 모든state를 무조건GPU로 보내지 않는다. 데이터복사와 CPU readback은 비실행 증거이고 실제 재개 검증은 별도다.
4. 진단·모듈구성 완료 뒤 checkpoint를 다시 로딩해 RNG/adapter/optimizer/cursor를 재설정한다. 진단이 학습 경로의 입력이나optimizer를 바꾸지 않게 한다. `.grad=None`은 매반복 확인한다. initial Bzero로 다시 시작하지 않는다.
5. 같은 checkpoint의 fresh component reload 및 adapterOFF의 prediction parity는 기존 기준 atol=rtol1e-3에서 확인한다. exact 여부·raw 차이도 기록한다. 비유한값·잘못된shape/입력/optimizer 대상·state불일치·base변경·같은상태load 기능불일치는 중지 사유다.

## 3. 제한된 수치·기능 진단

- B020 step20과 B021 step20을 각각 같은4개cached tuple에 넣어 최종 velocity tensor 자체를 비교한다. scalar loss만 같으면 함수가 같다고 가정하지 않는다. baselineOFF 대비학습변화와 두run간변화를 분리해 maxabs/RMS/relative L2를 보고한다. 작은 분모는 UNDEFINED. B021기록의 OFF대비RMS를 두run사이차이로 오해하지 않는다.
- A/B 오차와 실제 lowrank 변화 DeltaW=(alpha/r)BA의 차이를 구분한다. 필요시 저랭크 Gram 계산/소규모 고정입력 작용으로 비교하고 큰 full delta행렬이나 attention map를 무조건 저장하지 않는다. BA분해의 비유일성은 수학적주의사항이지 이번 차이의 증명된 원인이 아니다.
- B021 step20 상태, 한 고정 tuple, 동일loss에서 **업데이트 없이 동일 tail+head forward/backward 3회**를 실행할 수 있다. 매회grad clear·상태/RNG복원·동기화, 예측/gradient의pairwise차이·norm·유한값을 기록. 기존FA2 deterministic=False 경로를 유지하고 실제버전을 기록한다. 이 결과는 '해당tail경로 반복성'이며 FA2만의 원인 확정이 아니다. 일치해도 이전20step차이의원인이 사라진 것은 아니다.
- FA2공식 API의 deterministic backward 옵션은 한국어해설에서 검토하되, 이번에 켜거나 PyTorch전체결정론을 설정해 학습backend를 바꾸지 않는다. 새kernel 설치·SDPA교체 금지.
- 기존 B020와 B021의 A/B 재현오차는 관측으로 보존한다. 숫자 오차만으로 학습을 안전하게 진행할 수 있다는 보장도 하지 않는다. **재개 가능한 동일state·입력·gradient·출력parity와 안전계약이 충족되면, 원인 UNKNOWN을 유지해도 원인단정을하지않고20→100 비교로 진행한다.** 보정되지 않은 새'tolerance PASS'로 기존replay를 덮지 않는다.

## 4. 동일 학습 궤적의20→100

기존 AdamW lr1e-4/wd0/betas/eps/resolved options, tuple순서와FMloss를 유지한다. positive조건의h38/head_e/blockkwargs·표준정밀도와frozen head gradient를 보존한다. prefix캐시는 각sigma/noise조건에만 사용한다.

저장step20에서80회만 추가한다. loss/finite gradient/adapter delta를 기록하고, 평가snapshot20/50/100에서 같은4tuple을 비교한다. 같은clip sigma/noise holdout은 독립영상평가가 아니다. train row를 먼저 durable저장하고 gate검사한다. B021의누락된20번째scalar행은 새로 만들어 채우지 않는다.

저장/reload/OFF·frozenbasehash·processcleanup을 정상경로뿐 아니라 가능한 finally 경로에서도 수행하며 실패로도달못한검사는 NOT_REACHED로남긴다. adapter/optimizer/RNG/step/cursor를20원본보존/50/100으로 저장한다. 100이 아닌 best중간checkpoint를 사후선택하지 않는다.

## 5. 영상: 같은 출발점의20과100을 비교

입력은B020의실제Lab f126~142,896×512·17f30fps·원래sampler noise/seed·UniPC40·shift3·CFG5다. B021 checkpoint20과 새100을 각각정확히 식별해 같은전체모델 추론경로에 적용한다. 두 생성의실행순서와hash를 명시한다. 양쪽 모두 신규 fullsampler1회씩이며 추가seed/retry0.

SOURCE/새STEP20/새STEP100을같은시간축과전체17장으로비교한다. B020baseline/step20은별도역사맥락으로표시한다. 전신사족서기,후반머리방향·순서,얼굴/귀/목번짐,reference영역잘림·padding·장면을분리한다. loss감소·자세재현·개체보존을하나의PASS로묶지않는다. animation배경과GT재구성목표도분리해해석한다. 직접연속시청을하지못하면temporal=UNVERIFIED다.

20/100양쪽기술실행이가능하면품질이나쁘다는이유로둘째를생략하지않는다. 자원/정합/유한값등실제기술문제면정지한다. 최종latent를decode이전에보존하고decode실패로sampling을반복하지않는다. 이한clip/고정tuple실험을일반화/상용품질/학습분포전체의수렴으로부르지않는다.

## 6. 학습·기록·공개 범위

lessons/B-022-reproducibility-and-resume.md: seed와연산결정론, IEEE연산순서의roundoff, FA2default와deterministic옵션, LoRA DeltaW=BA와factor비유일성, MSE한숫자가예측동등성을증명하지못하는이유, checkpointserialization exactness/같은statefunction parity/독립training replay/영상재현의서로다른수준을수식·실제코드·관측으로설명한다. 최초gradient norm차이만으로커널원인확정금지.

공식참고: https://docs.pytorch.org/docs/stable/notes/randomness.html , https://github.com/Dao-AILab/flash-attention/blob/v2.8.3/flash_attn/flash_attn_interface.py , https://arxiv.org/abs/2106.09685 . 문서버전과실제설치버전은구분하며이번실행에서pinned localbinary/소스확인한다.

작업전RECORDING_PROTOCOL/CHARTER/ROADMAP/HISTORY, B020/021 결과와실제코드를읽는다. 새run ID·사전평가·복원계약·예산을commit/push하고실행한다. HISTORY/ROADMAP에B021fail보존과새질문전환을기록한다. 종료후RESULTS/실측/이론/재현/상태를갱신하고remoteSHA확인한다. main/forcepush/기존이력변경금지. 현재는문서등록만이며코드/GPU실행0이다.

개인미디어·latent·prefix·optimizer·adapter·비밀경로는공개하지않는다. private ZIP에는두endpoint와최종latent·비교·재개근거·실패기록을포함하고대형weights/중복prefix는제외한다. 실제Mac/Spark의/tmp위치·전송·CRC/manifest/hash를검증한다. 이번이후자동200/500update·결정론최적화·새학습층·새자료를추가하지말고결과에근거한다음가설하나만제안한다.

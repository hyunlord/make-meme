# B-022 결과 — 정확한 상태 재개 PASS, 목표 영상 품질 개선 미입증

B-021의 STOPPED_AT_REPLAY_20과 엄격한 adapter replay FAIL은 보존한다. B-022는 그 유효한20회 checkpoint의 optimizer/RNG/cursor를 포함한 재개 실험이다.

## 완료한 기술 검증

- restart20 payload 및18개 tensor가 B-021과 byte-identical. q.A/q.B/v.A/v.B와 AdamW moment·step20·RNG·cursor2를 복원했다. update21은 train_2다.
- 실제 추가80update, 누적100에서 종료. durable row는21..100이며 기존 B-021의 누락된20번째 row는 만들지 않았다.
- 비학습 tail forward33/40, 진단 backward3/3. P와 prefix 재계산0, 재시도0.
- fresh module의20회 네 tuple reload/OFF와100회 종료 검사: 원시 max_abs0, 기존 atol=rtol1e-3 유지.
- 이번 worker의 frozen base/source storage 불변 PASS. B-021 과거 종료 검사는 여전히 NOT_REACHED.

독립 검증: [TRAIN_REVIEW.json](TRAIN_REVIEW.json). 실행 코드는 preregistered commit `76bf4d0a159ca6bd06c1e7dbb810b2b4bfc8b96e`에서 고정했다.

## 고정 FM 평가

| tuple |20|50|100|
|---|---:|---:|---:|
|train_0|0.1454722583|0.1452070177|0.1448749900|
|train_1|0.0506718382|0.0505884141|0.0504798330|
|train_2|0.0314944424|0.0311658792|0.0308459513|
|holdout|0.0383793972|0.0382911973|0.0382253155|

![tuple별 평가](evaluation-by-tuple.png)

세 training tuple과 같은 clip holdout의 경험손실은 감소했다. 서로 다른 sigma의 loss를 하나의 하강곡선으로 해석하지 않는다. holdout은 독립 영상/개체 test가 아니다. D=Y의 복사 shortcut은 남는다.

## 수치 진단

B-02020과 B-02120의 최종 velocity RMS 차이는0.000538–0.000768, max_abs는0.03125였다. 유사한 scalar MSE는 함수 동등성의 증거가 아니다. 같은 상태의 무update 반복3회는 prediction 차이0, gradient 최대 차이2.2828e-10이었다. 이는 tail 전체 경로의 관측이며 FA2 단독 원인은 UNKNOWN이다. 고정4개 probe의 BA 작용 검사는 전 입력에 대한 동등성 증명이 아니다.

## 영상

두 endpoint 각각 실제40step/80forward와1회 decode를 완료했다. raw는 finite `[3,17,512,896]`, MP4는896×512·17프레임·30fps·0.566667초다. final latent `[16,5,64,112]` FP32는 decode 전에 저장·재로딩했다. 같은noise·RNG·scheduler와 조건16개leaf의값/device·config동일성을검증했다. 기존 B-02020회 영상은 역사 맥락이며 새 matched20 결과로 덮어쓰지 않는다.

에이전트가 원본/참조, 각endpoint전체17장,3열전체프레임비교와native f9/12/16을 직접 정적으로 확인했다. 실제 연속 재생은 관찰하지 못했으므로 **temporal=UNVERIFIED**다.

| 항목 | matched20 | resumed100 | 해석 |
|---|---|---|---|
| target 사족 서기 |FAIL: 착석 유지|FAIL: 착석 유지|추가80회로 전신 목표 개선 미입증|
| 고개 방향·순서 |후반 화면 왼쪽 전환|유사한 후반 왼쪽 전환|정확한 타이밍/각도 UNCERTAIN, 개선 미입증|
| 얼굴·귀·주둥이·목 |중후반 얼굴 번짐/변형|유사한 손상 잔존|형상 개선 미입증|
| 실제 개체·체형 |검은 Lab/참조 유사성, 정확한 개체일치 UNCERTAIN|동일 제한|견종 유사성을 개체 품질 PASS로 삼지 않음|
| 장면·framing |침실 복사, 흰 좌우 padding, 후반 머리 왼쪽 잘림|동일 실패 양상|원본 사족 장면을 유지하지 못함|
| 시간 품질 |UNVERIFIED|UNVERIFIED|파일 재생 가능과 시청 검증은 별도|

17/17 PNG가 byte-identical한 것은 아니다. 실제 출력의 차이는 있으나 이를 품질 개선으로 해석하지 않는다. 같은17장·30fps의 비교MP4와 전체시트는 비공개ZIP에 포함하며 좋은프레임선별·warp·보간을 하지 않았다.

최종 판정: **RESUME_TRAIN_SAVE_RELOAD=PASS, MATCHED_VIDEO_DELIVERY=PASS, TARGET_POSTURE=FAIL, QUALITY_IMPROVEMENT=NOT_ESTABLISHED.**

## 남은 검증 한계

전체 정적 typing은 NOT_CLEAN(755 errors)이며 세부 CPU 검사와 inherited dynamic import 진단을 [CPU_VALIDATION.md](CPU_VALIDATION.md)에 기록했다. 억제나 전체 타입 리팩터링은 하지 않았다. 이번 검사는 한 clip·세 fixed tuple과 마지막block Q/V rank4에 한정된다.

## 사용량과 종료

TRAIN1, 추가80update(누적100), 진단backward3, 비학습tailforward33, PROBE1, sampler2, decode2. P/prefix 재계산·재시도·새다운로드·새모델·추가튜닝0이다. 두sampler는1137.25/1124.26초, 두decode는14.21/16.22초였다. [실측](MEASUREMENTS.md). 소유한pipeline/watchdog는inactive/MainPID0이며 기존다른서비스는유지했다. 종료MemAvailable96,190,951,424bytes·swap0.

## 다음 가설 하나

고정tuple loss를 더 줄이는 것보다 **현재 animation 조건이 참조 착석/장면을 보존하도록 작용하는 과제 불일치가 주요 제한인지** 먼저 검사한다. 원격에 별도로 등록된 [B-023 공식 replacement baseline](../B-023-task-aligned-replacement/PLAN.md)은 이 가설을 검증할 다음 경로다. 이는 이번 결과만으로 확정한 원인이 아니며 단순mode 하나의 인과효과도 아니다. 이번에는 실행하지 않았고200/500update·커널 연구로 확대하지 않는다.

## 실행 연결 근거의 범위

독립CPU검토는각endpoint의adapterSHA가다르고,실제sample코드가`blocks.39.self_attn.q/v`에enabled LowRankLinear를설치한뒤검증된A/B를복사하며공식40block루프가그projection을호출함을확인했다. 별도runtimeadapteractivation hook/per-parameter hash를추가관측한것은아니다. successful80forward와실제코드/입력계보를근거로하고,독립activationtrace라고과장하지않는다.

[endpoint 검토](review-endpoints.json) · [자원 원시요약](resource-summary.json). 공개파일에는개인절대경로나미디어를넣지않았다.

한국어 수식·코드·질문/해설: [같은 checkpoint의 재개와 수치 반복성](../../lessons/B-022-resumed-update-comparison.md). 계획의가칭B-022-reproducibility-and-resume대신실제실험slug로파일명을정리했으며내용·실행계약변경은없다.

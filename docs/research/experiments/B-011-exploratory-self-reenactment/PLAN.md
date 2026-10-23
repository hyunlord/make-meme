# B-011 — 관측 계약 보정과 제한된 탐색적 동물 자기 재현

작성: 2026-10-23 · parent: B-010 · 상태: **PLANNED / NOT_RUN**

계획 공개는 실행 승인이 아니다. 사용자가 실행 담당자에게 이 계획을 전달해 수행을 지시할 때만 아래 새 범위를 적용한다. B-010의 미사용 예산을 자동 승계하지 않는다.

## 0. 방향·검토 근거·수정 이유

장기 목적은 DGX Spark급 로컬 자원에서 이미지·영상 생성의 수학·아키텍처·조건화 메커니즘을 이해하고 실제 품질을 개선하는 것이다. A의 native imagegen 전용 MCP는 동결한다. B에는 외부 생성 서비스와 A 생성물을 끼워 넣지 않는다. 실행 통과, 학습 이해, 품질 개선, 논문 독창성을 구분한다.

B-010 고정 결과 commit은 `6b69bcd65968f2b783791ed45ced7ac6c065f2ce`다. 이번 계획 작성자는 원격 RESULTS/evaluate_preflight.py와 업로드 ZIP 내부 코드·주석·프레임을 읽고 source f0/4/8/12/16, 머리 확대, 주석 overlay를 시각 검토했다. ZIP 37,571,236 bytes와 SHA256 `56adc95ede3e1e82b3bdebd2035ad68c8ea2970956ab7a9c3dc251b11108fee8`, CRC 및 manifest 238개 파일의 크기·해시를 직접 검증했다. Mac/Spark 두 실물에 접속하거나 GPU를 재실행한 것은 아니다. 연속 재생 품질은 미수용이다.

B-010은 원래 PLAN의 사전 기준에 따라 적절히 중단했다. 모델 실패가 아니다. 그러나 첫 탐색적 자기 재현에 정확한 관절 운동의 정량 식별까지 실행 전 필수로 묶으면, 평가 준비만 반복할 위험이 있다. 따라서 **기존 B-010 결과는 보존하고, 새 B-011에서 평가 범위를 사전에 나누어 제한된 생성 관찰까지 진행**한다. 유리한 결과를 만든 뒤 기준을 낮추는 것이 아니다.

15.5107px는 정적 복사 대비 20개 위치 변화의 평균이다. 19.4222px는 실측 tracker RMSE가 아니다. B-006 에이전트 시각 주석의 머리2px/앞발4px 보수적 반경에 max(1592/512,896/288)을 곱하고 1px를 더한 뒤 두 시점의 반경을 더한 평균이다. 통계적 표준편차·95% CI가 아니다. 같은 f0를 공유하는 변위들을 독립 표본처럼 처리하지 않는다.

분리 집계상 머리12항목 평균 변화16.3814px/평균 반경합14.4444px, 반경합을 넘는 관측7개이며 앞발8항목은14.2045px/26.8889px다. 이는 source의 일부 절대 위치 변화가 관측됨을 뜻할 뿐 articulation 성공이나 통계적 유의성은 아니다. 사후 부분집합을 선택해 B-010을 PASS로 바꾸지 않는다.

512×896 모델 입력은 기존512×288 프레임을1592×896으로 bicubic 확대 후 crop한 것이다. 이를 새로운 고해상도 원본이라고 부르지 않는다. 재주석은 읽기/좌표 양자화 오류를 줄일 수 있으나 정보 복원을 보장하지 않는다.

## 1. 새 질문과 평가 수준

질문: 동일 개체·장면·초기 자세 reference를 주었을 때, frozen SCAIL-2가 source의 관측 가능한 시간 변화를 STATIC COPY보다 재현하는가?

- 수준 A, 탐색적 시간 변화: 참조 복사·단순 흔들림·source와 대응하는 전체 이동/크기/머리 변화를 분리해 관찰한다. source에 실제 존재하는 전체 이동은 그 자체로 유효한 화면상 변화지만 관절 안무 성공은 아니다.
- 수준 B, 부위 상대 운동: 머리와 앞발의 상대 변화·동작 방향·타이밍을 가능한 범위에서 평가한다. 불확실하면 이 항목은 INCONCLUSIVE다.
- 수준 C, cross-identity/체형·물리 접촉/일반화: 이번에 입증하지 않는다. Lab 정체성·전체 춤·Kling 수준 수용은 NOT_RUN.

평균 변위<평균 보수적 반경 하나로 모든 탐색 생성을 차단하지 않는다. 반대로 수치가 없는데 모션 PASS라고 하지 않는다. **실행 안전·입력 계약 gate는 유지하고, 정량 평가의 불확실성은 결과 항목의 불확실성으로 남긴다.**

## 2. CPU 관측 보정 — 최대30분

B-010의 동일17프레임·static copy·reference·마스크를 유지한다. source를 고정시킨 뒤 결과와 무관하게 f0/4/8/12/16의 코·양눈·양앞발 visible proxy를 검토한다. 더 좋은 프레임이나 새 구간으로 바꾸지 않는다.

- 기존 overlay를 먼저 보지 않는 재관측과 재관측 간 차이를 기록할 수 있다. 같은 에이전트의 반복 판독은 인간 독립 ground truth나 보정된 오차 분포가 아니다.
- 실제 클릭 도구/이미지 열람/수동 입력 방식과 좌표계·줌 배율을 기록한다. 하지 않은 클릭·사람 검수를 주장하지 않는다. 겹치는 눈·발은 UNCERTAIN/null로 남긴다.
- 단순히2px/4px를 더 작은 수치로 바꿔 통과시키지 않는다. 기존 보수적 반경, 새로운 판독 반복성, systematic bias 가능성을 별도 열로 유지한다.
- 원본 촬영/압축 프레임의 더 높은 해상도 사본이 이미 존재하면 존재·시간 대응만 기록한다. 이번 입력은 바꾸지 않는다. 생성형 업스케일/샤프닝으로 평가 정답을 만들지 않는다.
- 전체 이동·크기 변화와 부위 상대 변화를 별도 보고한다. 부위 상대 거리/각도를 추가할 경우 원본만 보고 정의를 고정하고 전체 결과에 적용한다. 출력별 warp/zoom/시간정렬로 점수를 유리하게 바꾸지 않는다.

CPU 검토가 끝나면 관측법과 판단 가능/불가능 항목을 문서로 고정한다. source와 static 사이 일부 화면상 변화는 있지만 정확한 관절 정량성만 부족한 경우 **탐색적1회 생성으로 진행**한다. 입력 누락·영상 프레임 자체 불일치·가드 위반 또는 실제로 원본이 완전 정적임이 확인되면 중단한다. 평가 불확실성을 숨기지 말고 모호한 항목의 성공 판정을 유보한다.

## 3. 입력·모델 계약과 변경 집합

B-010에서 이미 준비한 실제 processed source f0를 RGB reference로 쓰고, f0 RED support+WHITE 배경 reference mask를 그대로 사용한다. driving17장과 driving mask는 B-009/B-010 고정 자산을 재사용한다. 모델 입력512×896,17frames,24fps를 유지한다.

positive prompt는 B-010 사전 문장을 그대로 사용한다:
`A small light-colored short-haired dog stands upright indoors, making subtle head and front-paw movements.`

seed20261022, UniPC40steps, shift3, CFG5, negative empty, replace_flag=False, history=None, LoRA/enhancer OFF. 기존 SCAIL2 weights/upstream/FlashAttention/mixed-BF16·FP32 staged loader/tiny CUDA 선행 연산과 anchor/P→PROBE→S→D 분리 경로 유지. 새 메모리·체크포인트 감사를 추가하지 않는다.

B-010의 실제 P는 NOT_RUN이므로 새 P가 필요하다. B-009 Lab cache를 그대로 쓰지 않는다. B-009와 비교해 expected-changed는 positive text1, 양branch reference latent2·CLIP2·ref mask2의 총7leaf다. driving latent/mask·negative text·noise·RNG·schedule9leaf는 실제로 비교하고 기존 선언 tolerance/exact 규칙을 지킨다. 조건 계약이 맞지 않으면 S 전에 중단한다.

새 과제 reference/text가 함께 달라지므로 B-009 대비 순수 단일요인 인과 비교가 아니다. frozen model이 자기 재현에 성공해도 Lab 실패 원인을 reference pose 하나로 확정하지 않는다.

## 4. 실행 예산과 안전

사용자 전달 시 새 P·PROBE·S·D 각각 최대1회, full sampler 실패 포함 최대1회, 재시도0. B-010 사용0은 보존하고 새 run ID를 연결한다. 전체 작업 최대3시간, 앞의 CPU관측은30분 이내.

실행 경로를 바꾸지 말고 기존24GiB headroom·swap0·다른 작업 보호·cgroup 정책을 유지한다. deadline/unit명만 실제 새 작업에 맞춘다. sudo/driver/OS/swap변경·drop_caches·타 프로세스종료 금지.

새 대형 모델/weights 다운로드0, 새 학습/LoRA0, imagegen/외부 생성API0. 원본15초/새구간/다른seed/low-pass guidance/SR/보간/quantization을 동시에 시험하지 않는다.

최종 latent를 저장·재로딩 검증한 다음 S를 종료하고 자원 회복 후 D를 실행한다. D 실패 시 S 재생성 금지. 모델이 영상 대신 source를 그대로 반환하는 우회를 쓰지 않는다.

## 5. 평가: 사전 정의된 범위를 유지

source / STATIC COPY / 생성 전체17프레임을 같은 시간축으로 비교한다. B-009는 맥락용으로만 병기한다. raw·latent·native24fps MP4·정적 시트 보존. 출력이 없으면 관련 품질은 NOT_RUN.

- 파일/finite PASS와 모델의 개체·동작 품질을 구분한다.
- reference가 이미 직립하므로 직립 유지 단독 성공 금지.
- 노이즈·flicker·전체 zoom으로 source와 다른 변화가 커진 것은 motion 성공이 아니다.
- source의 변화 방향·순서를 보이는 표면점/국소 이미지의 변화와 함께 읽는다. 관측이 애매하면 정량 항목 INCONCLUSIVE를 허용한다.
- 정적 복사 대비 개선율의 분모가 오차에 묻히면 gain은 UNDEFINED로 둔다. 대신 raw displacement/오차범위/coverage 및 정적·시간적 관측을 나란히 제시한다. p-value·95% CI·전체 성공률을 임의로 만들지 않는다.
- 출력 대응점이 무너지거나 가려지면 invalid/coverage를 명시하고 빼서 좋은 점수만 남기지 않는다. 생성 후 유리한 표면점·프레임을 고르지 않는다.
- 실제 속도의 연속 재생을 관찰하지 못하면 temporal=UNVERIFIED. 파일 decode나 브라우저 play 이벤트가 사람 시청을 뜻하지 않는다.

최종 결론은 (i) 관측 가능한 시간 변화 재현 근거, (ii) 부위 상대 운동 근거, (iii) 외형·형상, (iv) 평가 불확실성을 분리한다. 이번 생성은 탐색 사례1건이지 논문 성능·동물 일반화 증명이 아니다.

## 6. 공부·연구 기록

한국어 lessons/B-011-measurement-and-generative-diagnostics.md에 다음을 연결한다.

- 위치 오차 반경u와 표준불확실성/신뢰구간/실측RMSE의 차이.
- q=A p+b라면 보수적 반경의 선형전파 ||A||u, 두 시점 변위의 반경합 u0+ut. 분포/상관 정보가 없는 상태에서 sqrt합으로 바꿔 불확실성을 줄이지 않는다.
- 실제 sampling 좌표, 확대 표시 픽셀, 원본 정보량의 차이.
- 전체 화면 이동 재현과 articulation을 분리한 측정량 정의.
- 조건부 속도장 v_theta(z,t,reference,driving,text)에서 정적 reference 복사와 시간적 driving 활용을 어떤 실험으로 구별할 수 있는지. noise time과 physical frame time 구분.
- source-only 탐색 평가설계와 생성 후 점수 선택의 차이, 단일 seed의 한계.

수식→실제 코드→원본 관측→생성 결과(실행된 경우)→한계→질문/별도답안. 간단한 CPU uncertainty fixture면 충분하며 대형 평가 프레임워크를 만들지 않는다.

## 7. GitHub/제출/종료

기존 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL 및 B-010 PLAN/RESULTS를 읽고 원격HEAD·dirty state 확인. B-010의 중단은 그대로 둔다. 새 B-011 시작 전 관측법·코드/config를 커밋하고 HISTORY/ROADMAP에 **평가 수준을 분리하는 사전 변경**을 기록한다.

완료 후 RESULTS·한국어 해설·실측·재현·HISTORY·ROADMAP을 갱신, 연구branch commit/push와 remote SHA 확인. main 직접수정·force/reset/clean·자동merge 금지. 개인source/좌표/마스크/latent/cache/weights/비밀경로는 공개하지 않는다. 검토 ZIP에는 실제 결과와 실패·불확실성 자료를 넣고 weights는 제외, Mac/Spark 위치·CRC·파일hash·바이트대조 범위 보고.

한 번의 탐색 이후 종료한다. 결과가 해석 불가하면 같은17프레임의 측정 감사를 계속하지 말고 **기존 원본 중 더 명확한 동작을 가진 짧은 구간을 source-only로 선택하는 후속 실험** 한 가지만 제안할 수 있다. 이번에는 구간 변경·추가생성·학습을 자동 실행하지 않는다.

## 참고

- B-010 RESULTS와 evaluate_preflight.py: 이 저장소 parent commit의 실제 실행 근거.
- NIST TN1297 Type B uncertainty: https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-4-type-b-evaluation-standard-uncertainty
- OpenCV resizing/interpolation: https://opencv.org/blog/resizing-and-rescaling-images-with-opencv/

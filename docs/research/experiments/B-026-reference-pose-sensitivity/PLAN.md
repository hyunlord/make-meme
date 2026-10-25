# B-026 — 같은 IG의 참조 자세 적합성과 실제 동작 전달

작성: 2026-10-25 · parent: B-024/B-025 · 상태: **PLANNED / REFERENCE_AVAILABILITY_UNCONFIRMED / GPU NOT_RUN**.
문서 등록은 실행 승인이 아니다. 사용자가 수행 지시를 전달하고 실제 참조 자료를 확정했을 때만 아래 한정 범위를 적용한다.

## 1. 목적과 근거

최종 목표는 영상+참조 이미지+프롬프트로 원본 장면·동작·시간축을 유지하며 원하는 개체를 교체하는 로컬 시스템이다. A는 동결·독립이며 B는 외부 생성 API/imagegen/A 생성물을 사용하지 않는다.

기준 commit `eb0f86ad3654315f3c0bd2de206461104b6df89f`의 B-025 RESULTS와 CONDITIONS를 원격에서 읽었다. 같은 source/text/noise에서 Lab/IG 참조 묶음을 바꾸자 외형이 참조 방향으로 달라졌지만 IG는 누운 자세를 유지했다. source-copy만 한다는 설명은 이 pair의 외형 차이를 설명하기에 부족하다. 그러나 개체·동작·장면을 동시에 유지하는 목표는 FAIL이고, 실제 개체 일치와 시간 품질은 미확인이다. 사진의 자세·mask·체형·촬영 조건이 함께 달라지므로 원인을 특정 encoder나 자세 하나로 확정하지 않는다.

이번 질문: 같은 IG의 실제 사족 기립 참조를 쓰면, 현재 누운 참조보다 source의 기립 및 머리 동작에 적합해지는가? 그리고 그 개선이 정적인 참조 복사에 그치지 않고 동적 driving의 사건을 따라가는가?

서 있는 사진을 요구하는 것은 쉬운 조건에서 작동 경계를 확인하는 진단이다. 최종 시스템을 '항상 원하는 자세의 사진을 사용자가 마련해야 하는 도구'로 축소하지 않는다. 성공해도 자세 불변 identity 표현을 학습했다거나 최종 문제가 해결됐다고 하지 않는다.

## 2. 실제 참조 availability — 짧게 확인하고 없으면 대기

현재 검토자는 같은 IG의 실제 서 있는 사진이 기존 자산에 있는지 확인하지 못했다. 존재한다고 가정하지 않는다. 실행자는 기존 manifest와 이미 승인된 asset root만 한 번 확인한다(탐색 상한 15분). 원본 사진 또는 이미 제공된 같은 IG 원본 영상의 frame에서, 네 발로 지지하는 자연스러운 자세·머리·몸통·주요 사지가 보이는 후보를 찾는다. 품종이 같다고 같은 개체로 취급하지 않는다.

후보가 있으면 사용자가 확인한 개체 정보/기존 계보와 실제 이미지 관측을 구분한다. source만 보고 선택하고 생성 결과에 따라 여러 후보를 골라 돌리지 않는다. 가능한 한 source 첫 상태와 비슷한 시점의 자연스러운 전신 사진을 택하고, 기존 누운 사진과 다른 조명·해상도·크기·촬영시점을 기록한다.

후보가 없다면 **REFERENCE_PENDING / GPU 0**으로 한 번만 상태를 남긴다. 필요한 것은 같은 IG가 자연스럽게 네 발로 서 있는 원본 사진 한 장(또는 기존 원본 영상의 해당 frame)이다. 재검토·새 학습·다른 모델 실험을 자동으로 추가하지 않는다. 개인 홈 전체 검색, 웹 이미지/다른 IG 사용, A/imagegen 사진, 생성 모델로 자세 변경, 비선형 warp로 세우기는 금지한다. 동물에게 부자연스러운 자세를 요구하지 않는다.

이미 허용된 사진의 사용 범위를 반복 확인하지 않는다. 새 자료라면 비공개 로컬 추론·평가 범위를 기록한다. 전체 자료·mask·개인 경로는 공개하지 않는다.

## 3. 비교 셀과 사전 고정

| 셀 | 참조 | driving RGB+mask | 생성 |
|---|---|---|---|
| REST_MOV | B-025 기존 누운 IG | 실제 source 17장 | 기존 결과 재사용 |
| STAND_MOV | 확정한 실제 기립 IG | 같은 source 17장 | 신규 최대 1회 |
| STAND_STILL | STAND_MOV와 같은 사진 | source 첫 RGB와 mask를 각각 17회 반복 | 신규 최대 1회 |

원본 source는 실제 Lab f126..142, W896/H512,17프레임30fps로 유지한다. 원본 선택·timebase·crop·padding을 바꾸지 않는다. Lab 참조 결과는 맥락 자료일 뿐 다시 만들지 않는다.

STAND_MOV와 REST_MOV는 같은 IG이지만 사진·support·가려진 부위·조명·촬영시점이 달라지는 **reference-bundle 비교**다. pose 하나의 순수 인과효과로 주장하지 않는다. STAND_MOV/STAND_STILL은 같은 reference/text/noise 아래 driving RGB+mask의 공동 시간 정보 비교다. mask도 정지시키며 branch-off라고 부르지 않는다. STILL 출력은 움직일 수 있다.

standing reference는 기존 aspect-fit/padding 규칙만 적용하고, resize 후 개체 support 내부 RGB를 보존한다. 밖/padding은 RGB128, reference semantic mask는 RED/BLACK이다. 필요한 mask는 기존 CPU/수동 도구로 국소 준비하고 새 학습 모델을 설치하지 않는다. 서로 다른 자세의 mask/bbox가 같아야 한다고 강제하거나 source 실루엣에 맞춰 왜곡하지 않는다.

B-025의 실제 중립 caption과 empty negative를 그대로 재사용한다. 새 '더 서라' 문구나 품종·털색 지시를 추가하지 않는다. 같은 noise/RNG, UniPC40/shift3/CFG5, seed20261022, 정식 replacement=True, history/additional_ref=None, adapter/ALG/manualRoPE OFF를 유지한다.

생성 전에 두 참조의 관측 가능한 개체 특징 약 3개와 source의 head-turn 사건 local0/8/16을 기록한다. '서 있다'와 'source의 변화를 따른다'를 별도 판정한다. source/ref의 가려진 관절과 접촉을 만들어 쓰지 않는다.

## 4. 조건 인코딩과 실행 범위

standing reference VAE/CLIP 각 1회, reference mask 공식 helper 준비를 두 새 case가 공유한다. 텍스트·negative·기존 MOV driving/noise/schedule은 재사용한다. source 첫 RGB17장을 실제 video VAE로 인코딩해 STILL driving을 만든다. MOV 첫 latent slice 복제로 대체하지 않는다. 기존 B-012/013 STILL cache는 다른 source이므로 재사용하지 않는다. 같은 현재 source의 byte-equivalent cache가 실제로 있으면 계보 확인 후 재사용 가능하다.

REST_MOV 대 STAND_MOV의 기대 변경 집합은 양 CFG ref_latents/clip_fea/ref_masks(최대6leaf), 나머지는 유지한다. STAND_MOV/STAND_STILL의 기대 변경은 양 CFG pose_latents/driving_masks(최대4leaf)이며 reference/text/noise/scheduler 등은 동일하다. 실제 우연한 동일값을 억지로 다르게 만들거나 과거 검사 식을 그대로 적용하지 않는다. 기존 캐시·모델·원본은 불변이다.

이미 검증된 단계 분리·tiny CUDA·loader·FA2·최종 latent 저장 경로를 사용한다. reference/driver 복원 감사, checkpoint 변환, 새로운 커널 검사, 전체 타입 정리는 반복하지 않는다. 파일·shape·mode·실제 cache 연결과 필요한 최소 회귀만 확인한다.

실제 입력 확보 후 총작업 상한4시간. 신규 full sampler는 실패 포함 최대2회, 두 case 각40step80forward·decode각1회. 자동 retry/다른seed/추가사진 탐색0. 인코딩은 위 필요한 새 조건에 한정하고 PROBE는case별최대1회. 학습·새가중치/패키지·외부생성0. 기존72GiB시작/24GiBheadroom·swap0·타서비스 보호 유지, GPU-heavy 작업 순차 실행. 안전 문제 외에 첫 영상 품질이 나쁘다는 이유만으로 두 번째 사전 대조군을 생략하지 않는다. 최종 latent를 decode 전에 저장하고 D실패로 S를 다시 실행하지 않는다.

## 5. 평가와 해석

SOURCE / 두 IG reference / REST_MOV / STAND_MOV / STAND_STILL의 전체17장을 같은 시간축으로 비교한다. 정적 사진 반복은 CPU 보조 표시로만 사용할 수 있고 STILL 생성과 구분한다. 원좌표와 30fps를 유지하고 좋은frame 선별·warp·얼굴복원·합성·SR·보간을 하지 않는다.

판정 축:
- POSTURE: source와 같은 사족 기립인가? reference를 복사해도 기립은 나올 수 있다.
- MOTION: source의 고개 변화 방향·순서·대략적 시각을 따르는가? STAND_MOV가 STAND_STILL보다 사전 사건에 가까운가? 움직임 양만 증가하면 성공이 아니다.
- APPEARANCE: 회갈색/흰가슴·주둥이·귀·가는사지 등 참조 특징과 원본 검은 Lab 누수를 나눠 본다. generic IG와 실제 개체 일치도 구분한다.
- PRESERVATION: 타일·가구·로프·카메라를 보존하는가? 로프가 새 개체에 실제로 가려진 경우와 보이는 영역에서 지워진 경우를 구분하며 애매하면 UNCERTAIN이다. target 실루엣 변화가 모든 pixel불변 요구와 충돌하지 않게 한다.
- TEMPORAL: 실제 연속 검수 주체/관측이 없으면 UNVERIFIED다. 단회재생과 loop 경계를 구분해 viewer를 제공한다.

기립 출력만 좋아지고 동작 대조가 구분되지 않으면 POSTURE_IMPROVED/MOTION_NOT_ESTABLISHED로 기록한다. MOV가 참조 외형과 source사건을 함께 따르면 해당 단일 pair의 유망한 task사례일 뿐 일반화가 아니다. 두 출력이 source의 검은 Lab로 돌아가면 target identity의 실패다. 어려운 누운-reference 사례는 계속 실패 사례로 남겨 쉬운 사진 선택으로 벤치마크에서 지우지 않는다.

메모리(OS/RSS/cgroup/CUDA)와 encoder·로드·sampler·decode·mask준비 시간, 실패·수작업을 분리한다. 이 비교는 새로운 효율화가 아니며 maskedRGB만으로FLOP절감을주장하지않는다.

## 6. 연구·기록·종료

이론 해설은 F(V,R,P)의 reference-pose sensitivity와 reference-bundle 교란, 외형 조건과 motion 조건의 역할, static-reference 복사의 함정에 집중한다. 설명용 운동표현 m으로 m(F(V,R_rest,P))와m(F(V,R_stand,P))가원본m(V)에가까워야한다는목표를쓸수있지만 m은현재학습된정답추정기가아니며정확한pose metric을이미확보했다고하지않는다.

앞으로의 방법 연구는 쉬운 자세의 사진을 요구하는 것으로 끝내지 않고, 같은 개체의 참조 자세가 바뀌어도 편집이 유지되는 표현·데이터·학습 개입으로 연결할 수 있다. 이번에는 그 방법을 만들거나 LoRA를 학습하지 않는다. 기존 SCAIL도 조건 분리와 여러 driving을 연구하므로 현상·방법의 독창성을 먼저 주장하지 않는다.

착수 전 최신 CHARTER/RESEARCH_V2/ROADMAP/HISTORY/B025를 읽고 입력·조건·평가·예산을 확정한다. B-026 PLAN/INPUT_AMENDMENT와 HISTORY/ROADMAP에 availability 상태, 진단과 최종 목표의 차이를 기록한다. 종료 후 실제 결과·수치·한국어 해설·재현을 commit/push하고 remote SHA 확인. main/forcepush/기존실패변경 금지. 개인미디어·mask·latent·weights·개인경로는 비공개, 공개에는 비민감 문서·코드·요약만 남긴다.

실행했다면 신규 두 결과·기존 누운 결과의 비교·최종 latent·재현을 단일 비공개 ZIP으로 Spark/Mac /tmp에 보존하고 CRC/해시/실제전송을 검증한다. 자료가 없어 대기한다면 무의미한 감사ZIP이나 새 experiment 번호를 만들지 않는다.

입력 availability 확인 또는 사전고정 두 case 완료 후 종료한다. 추가 reference·multi-reference·새source·긴영상·학습·색/CFG sweep은 자동실행하지 않는다. 다음은 결과를 보고 한 가지로 정한다.

## 검토 범위

이 계획 작성자는 B025 원격 RESULTS/CONDITIONS/HEAD를 읽었다. 제공 ZIP은 정확한 mounted path로 container와 Python을 각각 호출했으나 모두 ClientError가 발생했다. ZIP CRC/367파일·개인사진·실제영상·양호스트동일성을 독립검증하지 않았다. 보고 SHA `f3012e22bfc8385a921bd20592b639f636ba3e25087059b4c3fcf9b4daa40e4b`는 실행자 보고값이다. 이번 작성에서 새 GPU/학습/생성0, 실제 서 있는 IG 자료 availability는 미확인이다.

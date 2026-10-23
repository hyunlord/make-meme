# B-013 결과: Lab 전이는 전신 자세와 국소 반응이 갈렸다

**COMPLETED / 실행·조건 통제 PASS / 전신 직립 전이 FAIL / 국소 driving 반응 PARTIAL / temporal UNVERIFIED.**

실제 Lab의 LAB_MOV와 LAB_STILL을 각각 한 번 생성했다. 두 출력 모두 침대 위 착석과 내려놓은 앞발을 유지했다. LAB_MOV는 후반 머리 변화가 더 나타났지만 눈·주둥이·귀가 심하게 번졌고, 원본의 깨끗한 점진적 roll이나 직립 안무를 수용할 수 없다. 검은 Lab 외형·넓은 몸통의 유지와 실제 반려견의 안정적인 얼굴 일치는 별개다.

## 실행과 고정 조건

- 시작 원격: `28a8540172768481efad7013281a7ce649985245`. 사전 prompt·입력·코드·config 고정 및 원격 확인: `f02896f825703a321c84127d4ef8135720176811`. [PLAN](PLAN.md)과 [사전 평가](PREREG_EVALUATION.md)는 결과를 보고 바꾸지 않았다.
- B-012의 실제 processed source f7~23, MOV/STILL RGB와 mask를 byte 그대로 재사용했다. source/Lab 사이 crop·구간·mask 개선은 없다. 기존 B-012 결과도 재생성하지 않았다. 512×896은 앞선 512×288 자료에서 확대·crop된 입력이며 새 고해상도 원본이 아니다.
- 기존 실제 검은 Lab RGB와 B-009 RED 개체+WHITE 배경 reference mask를 사용했다. 사진 배경 삭제나 자세 편집은 없다. 두 Lab 조건의 [prompt](PROMPT.md)는 완전히 같다.
- seed20261022, UniPC40steps, shift3, CFG5, negative empty, history=None, replace_flag=False, 512×896·17프레임·24fps, LoRA/enhancer OFF. 가중치·mixed BF16/FP32 loader·FlashAttention·tiny CUDA 선행/64-byte anchor·P→PROBE→S→D fresh worker와 최종 latent 저장 경로를 유지했다.
- 각 case의 P/PROBE/S/D **각1회**, full sampler **2/2회·실패0·재시도0**. 두 S 모두 실제40step·80forward다. 모델 다운로드·학습·imagegen·외부 생성0. A와 이전 결과를 보존했다.

## 조건 비교와 계보

[Lab pair 실제 검사](CONDITION_COMPARISON.json)는 두 CFG의 `pose_latents`/`driving_masks` **4leaf만 변경**, 나머지 **12leaf bit-exact**를 확인했다. 동일 seed만으로 noise를 같다고 가정하지 않았고 실제 초기 noise, generator state, scheduler를 비교했다. STILL도 반복 RGB 비디오를 별도 VAE encode했으며 MOV latent slice를 복제하지 않았다.

[대응 B-012 검사](LINEAGE_COMPARISON.json)는 각각 reference/text 관련7leaf 변경과 driving·negative·noise·RNG·scheduler 등9leaf bit-exact 보존을 확인했다. Lab cache 전체를 source cache에서 복사하지 않았다. source와 Lab의 reference 자세·체형·장면·text가 함께 달라지므로 이 비교는 순수 identity 하나의 인과효과가 아니다. 주 통제는 LAB_MOV 대 LAB_STILL이다.

| 관측 tensor | 실제 shape / dtype | 의미 |
|---|---|---|
| initial noise / final latent | `[16,5,112,64]` FP32 | 같은 shape지만 서로 다른 실제 값; final은40step 뒤 보존 |
| reference latent | `[16,1,112,64]` FP32 | 실제 Lab 사진의 압축 표현 |
| reference mask | `[28,6,112,64]` FP32 | 색상7채널의 시간 패킹; prefix와 zero suffix 검사 유지 |
| driving latent | `[16,5,56,32]` FP32 | RGB 시간 정보를 VAE로 인코딩 |
| driving mask | `[28,5,56,32]` FP32 | 대응 RED support의 시간 정보 |
| positive / negative T5 | `[108,4096]` / `[1,4096]` BF16 | 두 Lab case 동일; B-012 positive91token과는 다름 |
| CLIP | `[1,257,1280]` FP16 | Lab reference 시각 조건 |
| RNG / timesteps / sigmas | `[16]` uint8 CPU / `[40]` int64 CUDA / `[41]` FP32 CPU | 기존 device와 scheduler 계약 유지 |

양 CFG는 시각 조건을 공유한다. 따라서 CFG5가 reference 자세의 영향을 단순히 제거한다는 보장은 없다. 실제 코드·수식은 [한국어 해설](../../lessons/B-013-cross-identity-driving.md)을 따른다.

## 전체17프레임 정적 관측

두 관측자는 source와 reference를 먼저 본 뒤 조건명을 가린 A/B의 전체17장을 각각 검토했다. 기록 저장 후 대응표를 열었다: **A=LAB_STILL, B=LAB_MOV**. 동일 에이전트 계열의 정적 관측이며 독립 인간 ground truth나 통계적 blind 실험으로 부르지 않는다. 이후 labelled 전체17장과 기존 B-012 결과를 함께 확인했다. 실패한 local12~16을 제외하지 않았다.

| 평가 | LAB_MOV | LAB_STILL |
|---|---|---|
| 전신 자세·앞발 | **FAIL**: 착석·침대 지지 앞발 유지. 원본의 뒷발 직립·가슴 앞에 든 앞발과 다름 | **FAIL**: 착석과 지지 앞발 유지 |
| 국소 머리 반응 | **PARTIAL**: 후반 변화가 더 큼. 몸통 대비 머리 변화와 대략적인 후반 시점 대응은 관측되지만 형태 붕괴로 깨끗한 방향·증가 순서 수용 불가 | 초기 정면 자세 부근. 원본의 강해지는 후반 roll 재현 근거 부족 |
| 검은 Lab 외형·체형 | 초반 짧은 검은 털·처진 귀·넓은 주둥이·가슴·굵은 앞다리 유지 | 실제 사진과 유사한 외형·착석 체형 유지 |
| 실제 개체 일치 | 후반 얼굴·귀 번짐으로 **UNCERTAIN**. 견종 유사성으로 대체하지 않음 | reference 유사성이 높으나 새로운 자세에서 개체 보존을 입증한 것은 아님 |
| source 외형 누수 | 옅은 털·가는 전신으로 바뀌는 뚜렷한 누수는 관측되지 않음; 국소 얼굴 변형의 원인은 특정 불가 | 뚜렷한 옅은 전신 털 누수는 관측되지 않음 |
| 형상·경계·접촉 | local12~16 눈·주둥이·귀 번짐이 큼. 발/꼬리/가림·접촉은 **UNCERTAIN** | 상대적으로 안정적인 정적 외형. 숨은 부위·접촉은 **UNCERTAIN** |
| 시간 품질 | **UNVERIFIED** | **UNVERIFIED** |

사전 사건 local0/12/14/16을 그대로 사용했다.

- **local0/source f7:** 두 출력은 실제 Lab의 정면 착석과 가깝다. source는 이미 직립한 자세이므로 이 차이는 처음부터 존재한다.
- **local1~11:** MOV의 입·혀·머리 변화가 나타나며 STILL은 대체로 초기 모습에 가깝다. 입 닫힘은 사전 필수조건이 아니며 이를 새 실패 기준으로 만들지 않았다.
- **local12/source f19:** MOV에서 큰 머리 변화와 얼굴 번짐이 뚜렷해진다. source의 후반 head-roll 구간과 시간적으로 겹치지만 정확한 각도는 판독하지 않았다.
- **local14/source f21, local16/source f23:** MOV의 머리는 몸통에 비해 더 기울고 위치가 달라지지만 눈·주둥이·귀가 훼손되어 충실한 점진적 roll로 수용하지 않는다. STILL에는 같은 수준의 후반 변화가 없다. 두 조건 모두 전신은 앉아 있다.

기존 B-012 MOV는 동일 개체에서 더 명료한 후반 머리-몸통 상대 변화가 있었고 STILL은 초기 자세 근처였다. 이번 Lab 과제에서는 **driving이 출력에 영향을 준다는 근거와 유용한 전신 전이 성공이 분리**된다. reference 자세가 원인이라는 가설과도 양립하지만, 이번 pair만으로 reference/text/모델 prior 각각의 원인을 분리할 수 없다. 큰 움직임이나 흐림 자체를 안무 성공으로 계산하지 않았다. 각도·관절·접촉의 정밀 값, gain, 유의성은 만들지 않았다.

침실·침대 유지 자체는 animation 설정의 실패가 아니다. reference mask의 얇은 발·꼬리·바닥 경계는 **PARTIAL_UNRESOLVED**이며 결과의 어느 결함을 얼마나 일으켰는지는 미식별이다. 배경·그림자·반사는 국소 동작과 별도 항목이다.

## 실행 산출물과 자원

두 final latent는 FP32 `[16,5,112,64]`로 finite·원자적 저장·재읽기를 통과했고 S 종료 후 D에서 decode했다. raw는 finite `[3,17,896,512]`, MP4는 **17장·24fps·0.708333초**다. 처음과 마지막 표본 사이 시간은16/24초다. 24fps는 source 시간축 보존이며 모델의 시간적 학습 prior를 바꾼 것이 아니다.

| case | S guard 초 | D guard 초 | 최소 시스템 가용 GiB | final latent 파일 SHA256 |
|---|---:|---:|---:|---|
| LAB_MOV | 1181.602 | 16.198 | 46.304 | `f36e76fe6066dd8a044e3a5d6d3048e16a60e765e1ef228f6e8cb08bd2757f98` |
| LAB_STILL | 1149.802 | 16.219 | 46.139 | `7a66819d2426bf8e9bef11611d6a32b00f3f6e10e77c77f82870b2b2bb6943a5` |

전체 phase wall-clock2921.784초, 최소 시스템 가용46.139GiB, swap/OOM0. 두 S의 CUDA peak allocated33.832GiB다. **cgroup high 이벤트는 각각4242/3670으로 존재**했고 OOM과 구분한다. 기존72GiB 시작·24GiB 실행 headroom 가드를 완화하지 않았다. 시스템 가용·RSS·cgroup·CUDA 값을 별도 물리 메모리처럼 합산하지 않는다. [전체 실측](MEASUREMENTS.md), [세부 JSON](MEASUREMENTS.json), [실제 호출·출력 장부](RUN_LEDGER.json)에 phase와 hash를 남겼다.

코드/config/input/upstream864개 종료 후 SHA 검사 PASS. 대형 가중치는 이전 full SHA와 이번 fresh size/mtime로 확인했으며65GB 전체를 이번에 재해시했다고 주장하지 않는다. CPU 계약9검사·syntax/critical lint PASS와 별도로 dynamic comparator의 typecheck86diagnostics는 **NOT_CLEAN**으로 남긴다. 런타임 통과가 정적 타입 검사 통과를 뜻하지 않는다. [CPU 기록](CPU_VALIDATION.json).

## 보기·재현·공개 범위

비공개 `reports/output-review/review.html`은 SOURCE/실제 Lab reference/B-012 MOV/STILL/LAB_MOV/STILL을 같은 시간축에 보여준다. 전체17장 PNG, grouped contact sheet, 사전4시점, 새 pair와 기존 pair 비교,3072×928·17장·24fps 비교 MP4를 보존했다. 기존34장 B-012 PNG는 해당 raw 양자화와 pixel 완전 일치(max_abs0)를 확인했다. 새 두 raw에만 동일 quantization을 사용했다. warp·얼굴복원·보간·retiming·프레임 선별은 없다.

브라우저의 이전/다음·slider·끝점·한 번 재생 종료·autoplay/loop OFF 및 desktop/mobile 표시를 실제 확인했다. 모바일6열은 세부 판독에 작으므로 desktop 또는 원본 PNG를 사용한다. 파일 재생 가능성과 사람의 연속 품질 관찰은 다르다. 이번 관측은 정적 전체 프레임 검토이며 **temporal=UNVERIFIED**를 유지한다.

[재현 방법](REPRODUCE.md), 실행 코드/config·입력 hash·수학은 공개한다. 개인 미디어·좌표·조건 cache·latent·weights·개인 절대 경로는 공개하지 않는다. private ZIP에는 두 실제 raw/MP4/최종 latent·조건·재현·실패/불확실성 기록과 비교 자료를 포함하며 weights는 제외한다. [전달 검증](DELIVERY.md)에 양 호스트 CRC·551개 payload SHA·전송 동일성을 기록했다.

[codegraph 경고](TOOLING_WARNING.md)는 TOOLING_WARNING이다. 이번8개 worker의 정상 종료와 무관하며 hook 삭제·전역 해제·GPU 재설치나 완료 결과 재생성을 하지 않았다. 과거 경고의 정확한 원인은 UNKNOWN으로 유지한다.

## 다음 연구 하나 — 실행하지 않음

**SCAIL reference conditioning에 ALG의 시간별 참조 완화 원리를 적용할 수 있는지 검토하고, 전신 자세 전환 대 개체 보존을 비교할 단일 통제 실험을 설계한다.** 움직임 조건을 바꿔도 착석이 남았으므로 같은 mask/seed 탐색을 반복하기보다 reference/task 측 제약을 직접 다루는 가설이다.

[ALG 논문](https://arxiv.org/html/2506.08456v2)과 [고정 공식 구현](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py)은 사전 근거일 뿐 SCAIL 성공 증거가 아니다. 공식 경로는 원래/필터 참조와 text branch를 구분하며 단순히 양 CFG 입력 사진을 흐리는 방식과 다르다. 적용 구간의 forward가2→3개로 늘 수 있고, 저주파 착석 실루엣이 남거나 개체 세부가 약해져 개선되지 않을 수도 있다. SCAIL의 ref latent·CLIP·mask 계약과 guidance 식을 먼저 맞춰야 한다. **이번에는 이 수정·추론·학습을 모두 NOT_RUN으로 유지하고 종료한다.**

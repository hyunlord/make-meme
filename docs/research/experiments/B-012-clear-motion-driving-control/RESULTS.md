# B-012 결과 — 동적 driving의 추가 정보

**COMPLETED / 실행·조건 통제 PASS / 유용한 상대 머리 움직임의 탐색적 근거 / temporal UNVERIFIED.**

같은 reference·text·실제 initial noise에서 MOV는 원본 후반의 머리 기울임을 몸통과 구분되는 방향·순서로 재현했다. STILL은 초기 자세에 가까웠다. 따라서 이 한 구간·한 seed pair에서는 동적 RGB+mask가 유용한 시간 정보를 추가했다는 근거가 있다. 정밀한 앞발 안무, 정확한 회전각·접촉, Lab cross-identity 전이 또는 일반화 성공은 입증하지 않았다.

## 실행 전 고정한 비교

시작 원격 HEAD는 `aea64a71baf75db31a4aa4b9240ae4de8ad44545`다. 실제 source-only 후보 `[0,17)`, `[7,24)`, `[120,137)`를 검토해 가장 이른 적합 구간 **[7,24)**를 고정했다. 기존 원본은 1916×1078·24fps·361프레임이며 SHA256은 `da33bb95d4e05c49c537f3fdb27b2189fafec2b4f8d1a27e6b14efe034071f6b`다. source/mask 준비는 13:19~13:31 UTC 사이에 끝나 45분/30분 상한 안이었다. 큰 끝 자세의 난도는 제외하거나 숨기지 않았다.

원본→INTER_AREA 512×288→BICUBIC 1592×896→고정 crop의 같은 전처리를 사용했다. 512×896은 새 고해상도 원본이 아니다. 현재 decoded RGB와 과거 B-006 PNG 사이 최대 9 gray-level 차이를 기록했으며 이번 두 조건은 같은 실제 입력으로 비교했다. source7~16의 기존 mask와 source17~23의 기록된 수동 seed/CPU GrabCut을 사용했다. 사전 f19 seed 결함 수정과 이전 버전은 비공개 자료에 보존했고, 얇은 발·꼬리·귀·반사 경계는 PARTIAL이다. [선정](SOURCE_SELECTION.md), [입력](INPUT_PREPARATION.json), [사전 평가](PREREG_EVALUATION.md).

| 조건 | RGB driving | driving mask | 결과 성격 |
|---|---|---|---|
| MOV | 실제17장 | 대응17장 | 모델 생성 |
| STILL | 첫 RGB17회 | 첫 mask17회 | 모델 생성 |
| STATIC COPY | 첫 RGB17회 출력 | 해당 없음 | CPU 반복, 생성 아님 |

reference는 선택 첫 RGB, reference mask는 RED 개체+WHITE 배경으로 동일하다. 같은 source 개체·관측 동작을 서술한 prompt를 사전 고정했다. seed20261022, UniPC40, shift3, CFG5, negative empty, replace_flag=False, history=None, 512×896·17f24fps, LoRA/enhancer OFF를 유지했다. 코드·설정·입력·평가 사건을 **`8e80bdcfb9351bde5960cea4655f95ffaf22e98b`로 commit/push하고 원격 일치를 확인한 뒤** 첫 P를 실행했다. 결과 후 구간·prompt·기준 변경은 없다.

## 실제 조건과 사용량

MOV와 STILL 각각 실제17장 비디오를 독립적으로 VAE encode했다. MOV의 첫 latent slice를 복제하지 않았다. 양 CFG의 `pose_latents`와 `driving_masks` **4leaf만 변경**, 나머지 **12leaf 모두 bit-exact**였다. reference latent/mask, CLIP, positive/negative text, noise, RNG, scheduler를 보존했다. mask는 RGB alpha가 아닌 semantic 조건이다.

- driving latent `[16,5,56,32]` FP32, 최대 차이 4.467950105667114.
- driving mask `[28,5,56,32]` FP32, 최대 차이 1.
- noise `[16,5,112,64]` FP32, 실제 값 SHA256 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`로 동일.
- 12개 보존 leaf의 최대 차이 0. 사전 floating 허용값을 완화하지 않았으며 관측값은 tolerance 없이도 같았다.

[CONDITION_COMPARISON](CONDITION_COMPARISON.json)에 전체 shape/hash, [RUN_LEDGER](RUN_LEDGER.json)에 실제 파일·attempt·종료 증거가 있다. 같은 seed만으로 noise 동일성을 가정하지 않았다.

| 실제 결과 | MOV | STILL |
|---|---:|---:|
| P / PROBE / S / D 시도 | 각1회 | 각1회 |
| 완료 step / forward | 40 / 80 | 40 / 80 |
| S guard wall-clock | 1102.221초 | 1055.610초 |
| D guard wall-clock | 16.189초 | 15.171초 |
| S CUDA peak allocated | 33.832GiB | 33.832GiB |
| S 최소 시스템 가용 메모리 | 52.095GiB | 53.007GiB |
| final latent | finite FP32 `[16,5,112,64]` | 동일 shape/dtype·finite |
| decoded raw | finite `[3,17,896,512]` | 동일 shape·finite |
| MP4 | 17프레임·24fps·0.708333초 | 동일 시간축 |

sampler **2/2 소진**, 실패·재시도0, 신규 모델·다운로드·학습·LoRA·imagegen·외부 생성0. B-010 사용0/B-011 사용1 이력은 보존했다. 첫 P부터 마지막 D까지 2676.856초였고 swap/OOM0이었다. cgroup high MOV3630/STILL2959는 회수/스로틀 이벤트로 OOM이 아니다. 시스템/cgroup/CUDA 회계는 더하지 않는다. [상세 실측](MEASUREMENTS.md).

final latent는 마지막 scheduler/history 처리 이후 실제 decode 입력을 원자 저장하고 값·finite·lossless readback을 확인했다. 초기 noise를 final로 사용하지 않았다. S 종료·자원 회복 뒤 D를 실행했다. 자체 unit은 inactive/MainPID0이고 기존 서비스는 종료하지 않았다.

## 전체17장과 사전 사건의 실제 관찰

동일 canvas의 SOURCE / STATIC COPY / MOV / STILL 네 열을 전체17장 검토했다. local0/12/14/16은 생성 전 지정한 사건이다. 출력별 정렬·warp·zoom·시간 이동·보간·좋은 프레임 선별은 없다.

| local / source | 사전 원본 사건 | MOV 관찰 | STILL 관찰 |
|---|---|---|---|
| 0 / 7 | 약한 머리 기울임, 전면 몸통 | 초기 배치가 대응 | 초기 배치가 대응 |
| 12 / 19 | 끝보다 작은 roll, 전면 몸통 | 끝 이전의 작은 roll 순서가 대응 | 초기 배치 부근 유지 |
| 14 / 21 | 몸통보다 머리 roll 증가 | 같은 방향의 상대 회전이 뚜렷해짐 | 대응하는 증가가 없음 |
| 16 / 23 | 가파른 눈 연결선, 전면으로 기운 몸통 | 큰 머리 roll이 나타남; 세부 각도·얼굴은 다름 | 초기의 약한 기울임 부근 |

중간 f15도 포함해 후반 f14→15→16의 진행을 확인했다. MOV의 전체 이동·크기 변화는 원본과 대응하는 부분이 있지만, 이것만을 상대 동작 성공으로 세지 않았다. 주 근거는 전면 몸통에 대한 머리의 추가 회전이다. STILL을 픽셀 동일·완전 정지라고 주장하지 않는다.

두 결과 모두 검토한17/17장에서 전신과 뒷발이 보였고 피사체 전체 소실이나 큰 붕괴는 관측하지 않았다. 이것은 모든 세부가 정상이라는 판정이 아니다. MOV 후반 눈·주둥이·귀가 흐려지거나 원본과 달라진다. 양쪽 앞발이 주둥이 아래에 있다는 공통 배치만으로 정밀 앞발 제어를 입증할 수 없다. 발끝·얇은 경계·바닥 반사·그림자·접촉은 UNCERTAIN/PARTIAL이며 숨은 관절·3D 각도는 UNKNOWN이다.

coverage와 프레임별 관찰은 비공개 `output-evaluation.json`에 전부 남겼다. 좌표 오차를 보정하지 않아 gain·개선율·통계적 유의성은 계산하지 않았다. 관측자는 source와 조건 라벨을 알고 있었고, 복수 에이전트 검토를 독립 인간 ground truth로 취급하지 않는다.

**시간 품질 UNVERIFIED.** 정적 전체 프레임 관찰과 브라우저 기능 검사는 수행했지만 실제 연속 재생의 시각 품질 검수는 하지 않았다. 재생 파일·버튼이 작동한다는 사실은 temporal PASS가 아니다. 17/24초 파일 길이와 첫·끝 sample 간16/24초를 구분한다.

## 구현·검증 및 한계

기존 B-011 phase 분리·tiny CUDA/anchor·mixed loader·FlashAttention·scheduler·72GiB 시작/24GiB 실행 headroom·swap0 가드를 유지했다. 최소 변경은 두 case 경로/ID/deadline, RGB+mask 4변경/12보존 comparator와 입력 계약이다. 새 모델·범용 framework·추가 알고리즘은 없다. CPU 검토 도구는 frozen runtime 밖 [review_tools](review_tools/output_review.py)에 별도로 보존했다.

CPU 계약 회귀8개, critical lint/문법 검증은 통과했다. strict typecheck는 동적 scientific script와 미해결 import/type의 **92개 진단으로 NOT_CLEAN**이며 이를 실행 성공과 혼동하지 않는다. 실행 전1080개·실행 후848개 코드/입력/설정 대조를 통과했다. 대형4가중치는 이전 검증SHA와 이번 size/stat/mtime 일치로 재사용했으며 이번에 전체 bytes를 새로 해시했다고 주장하지 않는다. tokenizer4개는 새 SHA로 확인했다.

이 결과는 RGB와 mask의 시간 정보를 **함께** 바꾼 한 same-identity pair다. RGB 단독 기여, 모든 동물·seed·구간의 효과, Lab 정체성/체형 전이는 식별하지 못한다. 모델 학습을 수행하지 않았고, VACE/Kling 우월성·전체15초 성공·논문 성능으로 확대하지 않는다.

## 검토 자료와 다음 하나

비공개 자료에는 양쪽 raw/MP4/final latent/조건과 실제 입력, 전체17장·4열 native24fps 영상, 프레임 이동/단회 재생 페이지, mask 수정 이력, 실패·불확실성·자원 trace·재현 코드를 보존했다. 공개에는 개인 미디어·좌표·조건·latent·weights·개인 경로를 포함하지 않는다. [재현과 검토 명령](REPRODUCE.md), [수학·코드·질문과 해설](../../lessons/B-012-driving-information.md).

다음 연구 제안은 **같은 [7,24) 구간에 실제 Lab reference를 적용하는 제한된 cross-identity 전이 비교 하나**다. 먼저 이번 머리 roll의 제어 근거가 개체·체형을 바꿔도 유지되는지를 묻는다. 이번에는 NOT_RUN이며 추가 생성·학습·모델 변경을 시작하지 않았다.

# B-010 — 동물 자기 재현과 첫 프레임 복사 대조군

작성: 2026-10-23 · parent: B-008/B-009 · 상태: **PLANNED / NOT_RUN**

이 문서는 계획 공개이며 GPU 실행이나 새 예산 사용을 뜻하지 않는다. 사용자가 실행 담당자에게 이 계획의 수행을 지시하면 아래 한정 범위를 적용한다. 기존 미사용 슬롯을 자동으로 재사용하지 않는다.

## 0. 관측, 방향 전환, 검토 범위

B-009 원격 기준 commit: `173beb8be21997d789b64b5b9c67bf74c07ac341`.

검토자는 RESULTS.md, CONDITION_COMPARISON.json, RUNTIME_DIFF.diff를 직접 조회했다. 공개 기록상 두 CFG branch의 ref_masks만 바뀌고 나머지 14개 tensor는 exact였다. 원본 직립·앞발 동작 전달은 B-008/B-009 모두 실패했다. 이것은 **해당 입력·seed에서 reference 배경 BLACK→WHITE만으로 충분하지 않았다**는 결론이다. mask가 항상 무관하거나 SCAIL이 모든 동물을 처리하지 못한다는 증거가 아니다.

이번 검토에서 업로드 ZIP은 container와 Python 모두 ClientError로 읽지 못했고 Files 검색에서도 내용이 반환되지 않았다. ZIP CRC/268개 해시·Mac/Spark 일치·영상 시각 검토를 독립 수행했다고 주장하지 않는다. 제출된 ZIP SHA는 실행 담당자 보고값 `1ff9694f119798e2723efd9aa46cda612604aaba698b886c291e055a673e6440`다.

**결정:** WHITE/BLACK·회색 참조 실험을 반복하지 않는다. 다음은 원본 동물의 첫 RGB 프레임을 reference로 주는 동일 개체 자기 재현 진단이다. 이미지·영상 생성의 조건화 메커니즘을 이해하고 이후 모델 개입을 설계하는 것이 목적이며, 엔지니어링 통과 자체를 논문 기여라고 부르지 않는다.

## 1. 연구 질문

> 원본 개체·장면·초기 자세가 이미 맞는 reference를 주면, frozen SCAIL-2는 원본 RGB driving의 **시간에 따른 변화**를 첫 프레임 정지 복사보다 잘 재현하는가?

reference가 원본 첫 프레임이므로 직립 자체는 이미 주어진다. 직립 유지·낮은 flicker·선명한 정지 영상은 동작 전달 성공의 증거가 아니다. 자기 재현은 쉬운 진단 과제이며 실제 Lab로의 개체/체형 교체, unseen 일반화, 순수한 reference-pose 인과효과를 입증하지 않는다. reference RGB·reference mask·positive text가 함께 달라지므로 B-009와 단일요인 인과 비교라고 부르지 않는다.

## 2. 비교 구성

| 항목 | 구성 | 신규 생성 |
|---|---|---|
| 실제 목표/관측 기준 | 기존 처리된 source f0..f16 | 없음 |
| 정적 대조군 | source 첫 프레임을 17장 그대로 반복 | CPU 인코딩만, 생성 모델0회 |
| 자기 재현 출력 | source 첫 프레임 reference + 같은 RGB driving | full sampler 최대1회 |
| 맥락 비교 | B-009 Lab 출력 | 기존 결과 재사용, 통제 대조군 아님 |

첫 프레임 반복물은 일부러 정적인 대조군이다. 새 결과를 복제·보간해 평가하는 것과 구분하며 영상/시트에 STATIC COPY라고 표기한다. 원본17장 자체를 그대로 제출하고 생성 성공으로 보고하지 않는다.

## 3. GPU 실행 전 관측 가능성 점검

기존 source 17프레임을 먼저 확인하고, f0/4/8/12/16에서 보이는 코끝·머리 방향·앞발 끝 등 식별 가능한 소수의 표면점을 지정한다. B-006 주석이 동일 crop/시간축이면 재사용하고 좌표 변환과 실제 관측을 대조한다. 보이지 않는 관절·발 접촉은 null/UNKNOWN으로 둔다.

source 첫 프레임 반복 영상과 실제 source가 어떤 움직임에서 구분되는지 결과를 보기 전에 적는다. 전체17프레임에 가능한 경우 주석을 확장하되, 보간 좌표를 관측 정답으로 삼지 않는다. 좌표는 고정 canvas에서 정규화하고 필요하면 고정 source bbox 크기로 나눈다. 프레임마다 자동 정렬해 원래 움직임 오차를 지우지 않는다.

관측 변화가 측정 불확실성보다 작거나 가림 때문에 정적 복사와 구분 불가능하면 **DIAGNOSTIC_INSUFFICIENT**로 명시한다. 더 긴 구간이나 다른 seed를 자동 선택해 실행하지 않는다. 합리적인 관측 근거가 없는데 결과를 보고 나서 성공 기준을 낮추지 않는다. 관측 가능하면 질문을 기다리지 않고 아래 P→PROBE→S→D까지 수행한다. CPU 사전 검토는 최대30분.

## 4. 입력과 prompt

- reference RGB: B-009에서 실제 사용한 처리된 driving의 첫 RGB 프레임을 lossless PNG로 저장. 새 이미지 생성·보정·색 변경·업스케일 금지.
- reference mask: 같은 source f0의 RED 개체 support를 사용하고 배경 WHITE를 명시한다. 가능하면 기존 원본 lossless mask를 사용. mask에 palette 경계 픽셀이 있으면 pinned mask helper의 색 채널 판정으로 동일 RED support를 확인하고 결정론적 파생 규칙을 기록한다. 새로운 윤곽을 추정하거나 인간 silhouette를 만들지 않는다.
- driving RGB와 전체 driving mask는 B-009와 동일한 파일/픽셀/시간 순서. RED 대응, 동일 공간 transform, driver BLACK 배경 유지.
- input/output 512×896, 17프레임, 24fps, sample timestamps i/24. 파일 길이17/24초와 sample endpoint16/24초를 구분. 반복 재생 끝→처음 점프를 내부 동작 실패로 계산하지 않는다.
- positive prompt는 실제 source의 개체·외형·장면·관측 가능한 움직임을 서술하는 문장 하나를 실행 전에 고정한다. Lab/침실로 잘못 묘사하지 않는다. 품종·관절·킥을 보지 않고 지어내지 않는다. 공식 README의 generated-video-description 형식을 따르고 외부 prompt enhancer는 사용하지 않는다. 결과를 본 뒤 prompt 수정 금지.
- negative prompt는 기존 empty, animation replace_flag=False, seed20261022, UniPC40steps, shift3, CFG5, history=None, LoRA OFF 유지.

## 5. 조건 계약 — B-009 검사를 무조건 재사용하지 말 것

새 과제에서는 reference latent/CLIP/reference mask/positive text가 달라질 수 있다. B-009의 't4/t10만 변경' 검사나 Lab-specific 이름을 단순 삭제해 통과시키지 말고 **기대 변경 집합을 새 config로 명시**한다.

같아야 하는 것: 실제 RGB driving/driver mask와 공간·시간 처리, driving latent와 mask, negative text, initial noise의 값+shape+dtype, generator state, timesteps/sigmas, model revision/weights/precision/backend와 sampler 규약. GPU encoder의 작은 numerical 차이는 사전 tolerance로 보고하며 bit-exact가 아니면 그대로 기록한다. mask/noise/RNG/schedule은 exact 요구.

같아서는 안 되는 것도 확인한다: source-first-frame reference가 실제 P의 VAE/CLIP 입력에 사용됐는지, Lab cache나 침실 이미지가 남지 않았는지. condition tree의 16-leaf 가정과 경로·색상 채널·실제 입력 해시를 확인한다. 다른 reference의 cache를 새 이름으로 재사용하지 않는다.

## 6. 실행 범위

성공한 H/B-008/B-009의 P→PROBE→S→D 순차 fresh worker, 사전 tiny CUDA 실제 연산/64-byte anchor, mixed-BF16/FP32 staged loader, FlashAttention, final latent 원자 저장, VAE-only decode를 유지한다.

- 새로운 P·PROBE·S·D는 각각 최대1회. full sampler는 실패 포함 최대1회, 재시도0.
- 기존 공식/인간 예제·Lab baseline을 재생성하지 않는다. Lab·IG·다중개체·윙크·킥·15초 확대 없음.
- 학습/LoRA update0, 새 모델·대형 weight 다운로드0, SAT 재변환0, imagegen·외부 생성API0.
- 총 작업 상한3시간. 기존24GiB headroom·swap0·cgroup/타 서비스 보호 유지. 숫자를 낮추거나 drop_caches/sudo/드라이버/다른 프로세스 종료하지 않는다. 새로운 현재 deadline/unit을 사용.
- D 실패 시 S의 final latent를 보존하고 S를 다시 돌리지 않는다. 큰 framework·새 승인 상태 머신을 만들지 않는다.

## 7. 사전 평가 규칙과 수식

원본 p_src(t,j), 생성 p_gen(t,j), 반복물 p_copy(t,j)=p_src(0,j)를 같은 canvas 좌표에서 비교한다. q(t,j)=p(t,j)-p(0,j)로 변화를 분리한다.

설명/보고용 변화 오차:

`E_motion(Y) = sum_valid ||q_Y(t,j)-q_src(t,j)|| / (n_valid * s)`

여기서 s는 고정된 source의 기준 크기이고 t>0이며, 양쪽 t와0에서 관측 가능한 동일 표면점만 포함한다. 반복물 q_copy=0이므로 E_copy가 기준 오차다. 생성의 가시성을 평가 못하면 missing을 숨기지 말고 coverage와 invalid를 함께 기록한다. 포즈가 무너져 대응점을 못 찾는 것을 표본 제외만으로 유리하게 처리하지 않는다.

`gain = 1 - E_motion(Y)/E_copy`는 E_copy가 관측 오차보다 충분히 큰 경우에만 보조적으로 쓴다. 수치 gain만으로 성공 선언하지 않는다. 작은 분모에서는 UNDEFINED/INCONCLUSIVE이며 임의 epsilon으로 큰 개선율을 만들지 않는다.

함께 볼 것:
1. 초기 절대 자세와 모든 프레임의 형태/개체 유지.
2. 머리·앞발의 상대적 방향·크기·시간 단계. 전경 전체 평행 이동/zoom만으로 articulated motion 성공이라고 하지 않는다.
3. 생성과 source의 t=0 이후 변화. t0를 반복하는 것보다 움직임의 방향/크기/타이밍이 실제로 가까운가.
4. 과도한 흔들림·텍스처 flicker를 높은 motion score로 보상하지 않는다.
5. PSNR/SSIM은 self-reconstruction에서 보조로 쓸 수 있지만 배경/정적 프레임이 지배할 수 있어 주 성공 기준 아님.
6. 원본에 맞추기 위한 dynamic time warping, 최적 lag 사후 탐색, 프레임별 crop/warp/정렬·frame interpolation을 기본 평가에 사용하지 않는다. native time 결과를 우선한다.

판정: EXECUTION_PASS와 별도로 MOTION_FOLLOWING_OBSERVED / STATIC_COPY_LIKE / STRUCTURE_FAIL / INCONCLUSIVE 중 근거 있는 상태를 기록한다. direct realtime viewing이 없으면 temporal quality는 계속 UNVERIFIED. 정적 시트의 frame-indexed trajectory 검토와 실제 속도 재생을 혼동하지 않는다.

이 한 번의 결과는 RGB driving의 인과 기여를 독립 증명하지 않는다. 그 증명에는 추후 동일 reference/text에서 driving 시간 순서를 바꾸는 등의 별도 대조가 필요하다. 이번에 추가하지 않는다.

## 8. 결과 후 한 번의 결정

- 자기 재현이 정적 복사보다 원본의 비정적 움직임을 명확히 잘 따르면: 해당 동물/장면의 matched-reference 능력은 관측됐다. cross-identity와 reference pose/형상 충돌을 다음 연구 문제로 좁히되 원인이 확정됐다고 하지 않는다.
- 직립은 유지하지만 정적 복사 수준이면: self pose copy를 성공으로 포장하지 않는다. inference condition의 시간별 활용을 조사하는 메커니즘 가설을 선택한다.
- 자기 재현에서도 형태/동작이 실패하면: 해당 입력의 데이터/도메인/시간·공간 표현/전처리 가능성을 다시 비교한다. SCAIL 전체 동물 능력 실패로 확대하지 않는다.
- 작은 source 움직임 때문에 구분 불가면: INCONCLUSIVE. 다음에는 사전에 정한 더 식별 가능한 동작 구간을 제안하며 자동 실행하지 않는다.

어떤 경우에도 다음 실험 하나만 제안한다. 마스크 색깔 재탐색, prompt/seed sweep, 즉시 업스케일·LoRA·새 모델 설치로 확대하지 않는다.

## 9. 공부와 관련 연구

한국어 lessons/B-010-self-reenactment-and-static-shortcut.md:
- same-identity self-reenactment와 cross-identity retarget의 차이, reference 첫 프레임 제공의 지름길과 평가 누수.
- noise time tau와 video frame t의 구분, conditional vector field와 static appearance bias.
- CFG의 양 branch가 시각 조건을 공유할 때 CFG를 올린다고 motion conditioning만 독립 강화되는 것은 아님을 실제 code로 설명.
- 위 displacement error/정적 대조군/관측 불확실성과 causal limit.
- 직관→수식→actual tensor/code→관측→질문3개와 별도 해설.

검토할 관련 원 논문: Choi et al., Enhancing Motion Dynamics of Image-to-Video Models via Adaptive Low-Pass Guidance, arXiv:2506.08456 (https://arxiv.org/abs/2506.08456). 초기 고주파 reference 노출과 정적 appearance shortcut을 다루는 선행연구이며, 우리 SCAIL 실패 원인이 같다고 확인된 것은 아니다. I2V initial conditioning과 SCAIL의 reference VAE/CLIP/RGB-driving 경로 차이를 코드로 설명한다. 이번 실험에 low-pass나 새로운 loss를 적용하지 않는다. 문헌 수치·기여를 우리 개선으로 주장하지 않는다.

## 10. GitHub 기록·제출

작업 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL, B-008/009 RESULTS와 이 PLAN을 읽고 branch/HEAD/local dirty 상태 확인. 방향·학습·논문 목표를 잊지 말고, 이번은 진단 기준선임을 유지한다.

GPU 전 PLAN/config/실행코드/자원 정책 및 source의 평가할 움직임을 고정·commit/push. 기존 결과와 비공개 자산을 보존. 각 단계 주요 결과와 실패만 기록하며 모든 명령별 장문 기록은 하지 않는다.

종료 후 B-010 RESULTS.md, 학습 문서, 실제 입력·조건 변경표, 지표·재현, HISTORY/ROADMAP을 갱신하고 remote SHA 확인. 공개는 코드·비민감 설정·요약·hash·MD만. 개인 사진·원본/출력/마스크·표면점 좌표·latent·condition cache·가중치·private 경로·비밀값 공개 금지.

비공개 ZIP 하나에 source/STATIC COPY/self output/맥락용 B-009 비교(동일 표기), 전체17프레임, 보기 페이지, 관측점·coverage·평가 산출 과정, final latent·재사용 sidecar·재현 자료를 포함한다. 대형 weights 제외. 실제 호스트 /tmp/에 저장하고 Mac/Spark 전송 여부·파일 크기·SHA256·CRC·내부 manifest를 구분 보고한다.

최종 보고는 결과값, 판단 근거, 관측하지 않은 범위, 다음 한 연구 방향을 먼저 제시한다. 테스트 수나 ZIP 검증을 동작 품질 성공의 대용으로 쓰지 않는다. 이 계획 등록 시점 생성·학습은 NOT_RUN이다.

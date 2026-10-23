# B-014 — ALG 수식·코드 이식 검증과 제한된 SCAIL pilot

작성: 2026-10-24 · parent B-013 · 상태 **PLANNED / NOT_RUN**.

본 문서는 연구 제안/사전 기록이다. 등록만으로 GPU 실행이나 예산 사용을 승인한 것이 아니다. 사용자가 실행 담당자에게 본 계획 수행을 지시하면 아래 조건부 한정 범위를 적용한다. B-013 등 이전 사용 이력은 보존한다.

## 0. 방향·관측·검토 범위

B의 목표는 DGX Spark급 로컬 자원에서 이미지/영상 생성의 수학·아키텍처·조건화·학습을 이해하고 개선하는 것이다. 상용급 생성 품질과 검증 가능한 논문 기여가 장기 목표다. 서비스 구매나 설치 성공으로 대체하지 않는다. A의 native imagegen 전용 MCP와 B를 섞지 않는다.

B-013 기준 commit `676aecd494e7d3f4917e1e252a2dbb2f95079080`의 RESULTS와 실제 phase_sample.py를 읽었다. 원격 기록은 LAB_MOV의 후반 머리 변화/PARTIAL 및 심한 얼굴·귀 번짐, 두 조건의 착석 유지/직립 FAIL, LAB_STILL의 초기 자세 유지, 개체 UNCERTAIN/temporal UNVERIFIED를 보고한다. 이 결과는 reference/driving의 충돌 가설과 양립하지만 원인이나 고주파 책임을 확정하지 못한다.

이번 계획 작성에서는 제공 ZIP `/mnt/data/make-meme-B-013-20261023-final.zip`을 container와 Python으로 읽으려 했으나 모두 ClientError였다. 294,365,414bytes / SHA256 `28217356dd48d90766a99ae3ab72f42649b0c847d53dac18b96749a766700e15` / 551개 해시는 실행 담당자의 보고값이다. 영상 시청·CRC·tensor bytes를 독립 검증했다는 주장은 하지 않는다. 아래는 원격 소스·논문·실행 기록을 대조한 계획이다.

**주 질문:** 동적 driving/마스크/텍스트/초기 noise를 고정한 상태에서, 초기 샘플링의 reference-latent 기반 CFG 차분을 ALG 방식으로 변경하면 원본 동작 충실도가 개선되는가? 얼굴·귀의 형태와 실제 개체 보존을 추가로 훼손하지 않는가?

## 1. 선행 연구에서 확인한 중요한 구현

원 논문: https://arxiv.org/abs/2506.08456 (검토 v2, Improving Motion in Image-to-Video Models via Adaptive Low-Pass Guidance).
공식 구현: https://github.com/choi403/ALG, 검토 고정 commit `3657bfd0d408631db2443b491498c44e1cb2e5c6`.
직접 확인한 파일: `pipeline_wan_image2video_lowpass.py`(특히 830~955), `lp_utils.py`, `configs/wan_alg.yaml`.
SCAIL 고정 upstream: `78fe19576bb06be96c2375e088574a262a300edb`, `wan/scail.py`, `wan/modules/model_scail2.py`.

중요: 공식 Wan ALG는 초기 구간에서 원본 reference의 text-negative 예측을 유지하고, low-pass reference의 text-positive/negative 두 예측 차이를 guidance로 사용한다. 단순히 두 CFG branch의 reference를 흐린 값으로 바꾸는 것과 다르다. 원 논문 Eq.(2)와 실제 3-chunk 코드의 조합식을 우선한다. 이식은 SCAIL의 다른 조건 구조를 대상으로 하므로 원논문의 재현/공식 SCAIL 지원/새 알고리즘으로 부르지 않는다.

SCAIL은 reference latent를 생성 latent 앞의 token으로 구성하고, 별도의 CLIP·색상 mask·RGB driving 조건도 함께 받는다. reference는 반드시 출력 첫 프레임이어야 하는 것이 아니다. 원논문 부록의 first-frame overwrite를 이식하면 앉은 Lab reference를 출력에 강제할 수 있다. **이번에는 first-frame overwrite/clamp를 절대 넣지 않는다.** 코드 버전·논문 부록의 차이도 기록한다.

## 2. 이식할 정확한 식

R: 기존 reference latent; L(R): 공간 low-pass 처리된 R; D/M: 동일 driving/mask; c+/-: 기존 positive/negative text; CLIP은 원본 그대로.

기존 CFG:
`v_base = v(z,t,R,D,M,c-) + w * (v(z,t,R,D,M,c+) - v(z,t,R,D,M,c-))`

초기 ALG 구간:
`u_orig = v(z,t,R,D,M,c-)`
`u_low  = v(z,t,L(R),D,M,c-)`
`c_low  = v(z,t,L(R),D,M,c+)`
`v_alg  = u_orig + w * (c_low - u_low)`

후반에는 기존 두-branch CFG 경로를 그대로 실행한다. text-negative는 시각적 무조건/branch-off가 아니며 reference·driving·mask·CLIP를 그대로 받는다. 여기서의 low-pass는 reference VAE latent의 spatial axis에만 적용한다. latent 채널의 고주파를 RGB 털 고주파와 완전히 같은 의미로 주장하지 않는다.

보존해야 할 것: CLIP 특징, reference/driver mask, driving RGB latent, text, noise, RNG, scheduler timesteps/sigmas, reference 길이·token 위치·history, 해상도·fps·model dtype/weights. 원본 ref_latents를 in-place 수정하거나 cache 파일을 덮어쓰지 않는다.

## 3. 첫 pilot 설정 (사전 고정, 탐색 grid 없음)

공식 Wan YAML의 resize_factor=0.4, interval [0,0.20]을 가져온 최초 이식 설정이다. SCAIL의 최적값이라고 주장하지 않는다.

- `R.shape=[16,1,112,64]`, FP32. 실제 캐시 확인 후 시간축1을 batch로 옮긴 `[1,16,112,64]`에 bilinear down-up을 적용한다.
- `h1=max(1,round(112*0.4))=45`, `w1=max(1,round(64*0.4))=26`; 이후 원래112×64로 복원. `align_corners=False, antialias=True` 양쪽 적용. 각 채널·각 프레임 독립; 시간·채널 혼합 금지.
- 일반5D `[B,C,T,H,W]`는 단순 view로 `[B*T,C,H,W]`가 된다고 가정하지 마. permute가 필요한 구조를 명시하고 channel/frame isolation fixture로 확인한다. 이번은 T_ref=1이다.
- strength는 공식 `i/max(N-1,1)` 규칙. N=40이면 i=0..7의8스텝 active, i=8..39 비활성. active에서3회, 나머지2회, **총88개 DiT single-sample forward**. 기존40step80forward보다 NFE10% 증가이며 walltime10% 증가 보장은 아니다.
- 3branch를 batch3으로 묶지 않는다. 기존 sequential CPU-offload prediction 경로를 유지하고 새3번째 forward도 순차 실행하여 피크 활성값을 억제한다. scheduler.step은 여전히 전체40회, 동일 UniPC/shift3/CFG5.
- 첫/끝 생성 latent는 원래 scheduler output만 사용한다. reference로 x0 일부 교체, 자세 보정, warp, 보간, SR, 다른 필터나 CFG tuning은 금지한다.

## 4. 감사·CPU 계약 검증 — 결과만 준비하고 무기한 멈추지 않기

모델 설치/가중치 변환/새 framework 없이 기존 코드를 읽고 ALG→SCAIL 조건 매핑을 작성한다. 원문·공식 소스와 현 sampler·extractor·contracts·phase_decode의 차이를 최대60분 안에 정리한다. input/model/serialization 준비 감사를 재실행하는 것으로 시간을 채우지 않는다.

작은 CPU fixture에서 아래를 검증한다.

1. 비활성 옵션 또는 ratio1 no-op에서 기존2branch 경로/순서/계산과 동일. 원본조건 hash·RNG state 보존. 이는 CPU 계약 검증이지 14B bit-identical 재생성 증명은 아니다.
2. 세 branch 중 원본 negative만 R, 두 low branch만 L(R). 실제 kwargs에서 mask/CLIP/driving/text/RNG/scheduler 변경 집합을 검사. dict/list shallow copy alias로 원본을 바꾸지 마.
3. 결과 조합이 정확히 `u_orig+w*(c_low-u_low)`인지 의도적으로 다른 fixture 값으로 검사한다. naive low-low CFG와 구별한다.
4. i=0,7,8,39에서 schedule/call count 검증, expected88/40steps를 config로 유도한다. 80forward 하드코딩이 있는 sample/decode/contracts/manifest/검증 코드를 좁게 갱신하고 검증을 삭제하지 않는다.
5. 공간 필터가 channel·frame을 섞지 않고 shape/dtype/device를 보존함; 상수 입력·다른 채널 impulse·batch/frame isolation; 원본 storage 불변과 새 filtered hash 확인. signed latent clamp/추가 normalization은 하지 않는다.
6. sampler 추출 AST/patch 지점을 공식 소스 hash와 대조한다. ALG를 전체 diffusers pipeline으로 교체하지 않는다. 변경은 prediction 조합과 reference kwargs 선택으로 한정한다.

검사 실패/현재 구조에 올바른 연결 불가면 ADAPTATION_BLOCKED로 멈추고 사유를 보고한다. 새 global monkeypatch나 자동 새 backend/모델 교체를 시도하지 않는다.

## 5. 조건부 실행 범위

위 계약과 원본 자산 재사용 검사를 통과하면 **LAB_MOV_ALG 신규 full sampler 최대1회(실패포함, 재시도0)**와 해당 latent의 D 최대1회를 수행한다. 별도 원본 알고리즘 재생성0, STILL_ALG0이다. 이 범위는 사용자가 본 의뢰서를 실행 담당자에게 전달했을 때만 적용한다.

- 기존 B-013 LAB_MOV cache/initial noise/실제 processed source f7..23/RED+WHITE ref mask·Lab prompt·negative·model hash를 확인하고 읽기전용으로 재사용. P encoder 재실행0, 새 모델/weights/data 다운로드0, 학습/LoRA0, imagegen/외부 생성0.
- CPU로 기존 reference latent에서 filtered 파생 tensor·schedule sidecar만 새로 저장하고 부모 cache SHA를 연결한다. 이 sidecar는 원본 P cache 자체의 변경이 아니다.
- 전체3시간, 한 번에 heavy GPU1개. 기존 tiny CUDA→staged loader→cache restore→S→종료/자원회복→D 경로 유지. start72GiB/runtime24GiB headroom 및 기존 cgroup/swap0/타 서비스 보호를 완화하지 않는다. 기존 프로세스 종료·sudo/driver/swap/drop_caches 금지.
- expected forward=88·step=40를 실제 집계한다. active step에서 원본neg/lowneg/lowpos branch와 reference hash를 기록하고 후반 baseline 복귀 확인. 첫 샘플링 상태와 scheduler가 같음을 확인한다.
- prediction norm/차분 norm은 이미 계산한 값에서 작은 scalar로만 관측 가능. extra DiT forward나 hidden state 전체 보존 금지. attention map 시각화나 새 decoder 호출을 몰래 추가하지 않는다.
- 조건 입력은 baseline과 같아도 첫 개입 이후 latent trajectory는 달라지는 것이 정상이다. 후반 원래 reference 복귀는 baseline latent/output 복귀를 뜻하지 않는다.
- final latent를 먼저 원자 저장·finite/readback 검증한 뒤 S를 종료하고 VAE-only D를 수행한다. 출력은17f/512×896/24fps. P cache·latent·frame별 idx/sigma/norm·의도된 수식 계보를 보존한다.

## 6. 평가: motion 증가를 성공으로 세지 않기

SOURCE, 실제 Lab reference, 기존 B-013 LAB_MOV, LAB_STILL, 신규 LAB_MOV_ALG를 같은 시간축에서 비교한다. 기존 baseline을 재생성하지 않고 원본/모델/precision/입력/config 동등성의 범위를 적는다. 사전 local0/12/14/16 및 전체17장을 유지한다.

판정 축을 분리한다.
- 전신: 직립/앞발 들어올림 전달 여부. 새 모습만 나오고 실제 Lab가 사라지는 것은 성공 아님.
- 국소: source 후반 head-roll 방향·증가 순서/몸통 대비 변화. 단순 더 큰 흔들림·줌·카메라 이동은 성공 아님.
- 정체성/형태: 실제 얼굴·귀·눈·주둥이 안정성, local12~16 번짐/겹침, 가슴·사지 비율. 선명한 STILL보다 흐리다는 이유만으로 움직임을 억제한 결과가 유리하지 않게 source fidelity와 함께 해석한다.
- 시간: agent가 실제 연속재생을 관찰하지 못하면 UNVERIFIED. 기존 viewer로 raw/native-speed 재생과 정적17장 검토를 제공. 사람 피드백은 별도 근거.

가능한 결과: 의미 있는 motion+shape 개선, motion 증가/identity 악화, 전신은 착석/국소만 개선, 변화 미미, 붕괴 악화. 한 seed의 탐색이며 효과 크기/유의성/최고성능·논문기여를 주장하지 않는다. 추가88NFE 대 baseline80NFE 비용을 숨기지 않는다. 유망하면 이후 ALG_STILL·time-matched/compute-matched baseline·held-out 개체/seed 검증을 별도로 계획한다. 이번에 자동 실행하지 않는다.

**가설의 한계:** low-pass는 자세 제거기가 아니다. 앉은 실루엣·체형·배경의 저주파, 원본 CLIP·참조mask 정보가 남고, SCAIL은 source-driving을 별도로 받는 모델이다. 이 이식이 실패해도 ALG 전체 또는 모든 reference intervention이 무효라는 결론은 못 낸다. 성공해도 원본 실패 원인이 고주파 하나였다는 증명은 아니다.

## 7. 이론·로드맵·논문 원칙

한국어 lessons/B-014-alg-and-conditional-velocity.md:
- I2V motion suppression과 우리 cross-identity fidelity 문제의 차이.
- baseline CFG와 ALG3항 공식, 원본negative fidelity 기준항을 남기는 이유.
- 두 CFG의 시각 조건 공유와 text-negative가 진정한 시각 unconditional이 아닌 점.
- noise time sigma와 video frame t, 초기8 sampling step은 처음8 영상프레임이 아니라는 점.
- low-pass RGB vs latent 의미·정보 손실·체형 silhouette 유지; E(L(I))와 L(E(I))의 비동등성.
- SCAIL ref token/CLIP/mask/driving의 실제 shape·함수·변경 경계.
- cost88vs80와 batch3 memory 금지, trajectory 비선형성과 late reference 복귀의 한계.
직관→식→텐서→CPU fixture→실제 관측→실패 가설→질문/해설로 작성한다. 기존 방법을 올바르게 이식한 재현/탐색이며 새 논문 알고리즘이라고 부르지 않는다. 향후 독창성은 별도 선행 비교/새 방법/일반화 증거로 판단한다.

작업 전 연구 공통 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL를 읽고 실제 code/config/filter/schedule/예산을 커밋한다. 같은 생성 엔진을 유지하며 입력 ablation에서 sampling mechanism 개입으로 넘어가는 이유를 HISTORY/ROADMAP에 기록한다. 종료 후 RESULTS/ADAPTATION_AUDIT/REPRODUCE/조건계보/실측/lesson을 갱신·commit/push하고 remote SHA 확인한다. 과거 결과·gain/미검증 상태를 덮어쓰지 않는다.

개인 미디어·캐시·latent·weights·절대경로·secret은 GitHub 공개 금지. 비공개 ZIP에 실제 시도/실패, sidecar·final latent·영상·전체17장·원본/대조비교·재현·trace를 넣고 큰 weights는 제외한다. Mac/Spark의 실제 /tmp 경로·전송/CRC/manifest/SHA를 구분한다. 종료 후 자체 process 상태를 확인하고 추가 설정탐색·모델·학습으로 자동 확대하지 않는다.

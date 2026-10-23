# B-008 — 실제 Lab의 첫 RGB-driving 품질 기준선

작성: 2026-10-23 · parent: B-007H · 상태: **PLANNED / NOT_RUN**

이 문서는 다음 실행의 제안과 사전 기록이다. GitHub 문서 등록만으로 새 GPU 실행이나 예산 사용을 의미하지 않는다. 사용자가 이 의뢰서를 실행 담당자에게 전달할 때 아래 한정 실행 범위를 적용한다.

## 0. 방향·목표·현재 증거

B-007H 기준 커밋은 `a1164e4a10c48aecd6c05f5df7dbb8fc2944379e`다. 공식 인간 예제에서 CUDA probe → S → D가 완료됐고, 40 scheduler steps·80 DiT forward의 최종 latent와 896×512/17프레임/16fps/1.0625초 MP4가 보고됐다. G의 실패 원인은 UNKNOWN이고, 이 한 번의 성공은 상용급 품질·동물 일반화·학습 적합성의 증명이 아니다.

이번 계획 작성자는 원격 H RESULTS/RUNTIME_DIFF, G phase_prepare, H phase_decode 및 기존 E INPUT_AUDIT를 직접 읽었다. 업로드 H ZIP에 대한 container와 Python 접근은 ClientError로 실패했으므로 ZIP CRC/159개 해시/영상 시청을 독립 검증했다고 주장하지 않는다. 실제 Spark 실행을 재수행한 것도 아니다.

**단계 전환:** B-007의 실행 기반 진단에서 B-008의 실제 과제 품질 진단으로 이동한다. 이제 새로운 CUDA/직렬화 감사·MCP·대형 framework를 추가하지 않는다. 성공한 H의 실행 경로를 보존하고 실제 Lab 입력 한 건을 끝까지 생성·평가한다. 연구 목적은 이미지·영상 생성의 수학·아키텍처·조건화 메커니즘을 이해하고 이후 검증 가능한 방법 개선으로 이어가는 것이다. 이번 baseline 자체를 새 논문 기법이라고 부르지 않는다.

질문: **실제 앉은 Lab 사진의 얼굴·귀·털·체형을 유지하면서, 원본 f0~f16의 직립 자세와 관측 가능한 머리·앞발 동작을 RGB driving으로 전달할 수 있는가?**

## 1. 고정 범위와 예산

- A는 계속 동결. B에서 native imagegen/외부 이미지·영상 생성 API/유료 GPU를 사용하지 않는다. 원본 실제 사진·영상만 사용한다.
- 기존 SCAIL2 가중치, 고정 upstream commit, mixed BF16/FP32 정책, FlashAttention binary, staged loader와 H의 사전 CUDA copy/add/synchronize/readback·64-byte anchor 유지 경로를 재사용한다. 새 모델·weights 다운로드0, SAT 재변환0, 학습/LoRA update0.
- **Lab 신규 P 조건 준비 최대1회, 조건 probe 최대1회, S 모델 적재·full sampler 최대1회, 해당 final latent의 D decode 최대1회.** 실제 실패도 각 단계의 시도에 포함한다. 공식 예제를 다시 생성하지 않고, 실패 후 seed/prompt/resolution을 바꾼 재시도도 하지 않는다.
- 단계 순서는 P → PROBE → S → D. 각각 fresh worker, 직전 worker 종료와 자원 회복 확인. 성공한 H cache 검증을 반복할 필요는 없으며 Lab의 새 cache만 검증한다.
- 전체 작업 최대3시간, 무거운 GPU 작업1개, H와 동일한 시작·24GiB global headroom·swap0·cgroup·다른 서비스 보호 정책. deadline/unit 이름은 현재 작업에 맞게 설정하고 과거 종료시각을 복사하지 않는다.
- sudo/driver/OS/clock/swap 변경·drop_caches·타 프로세스 종료·가드 완화·무한 환경 탐색 금지. 대상이 아닌 서비스 queue가 바쁘면 작업을 중지한다.
- 예산/완료/실패 장부는 이전 E/F/G/H 이력과 분리 연결한다. 이전 잔여 슬롯을 초기화·재승인한 것으로 취급하지 않는다.

## 2. 입력·기존 코드의 중요한 차이

기존 E INPUT_AUDIT의 Lab 입력을 우선 재사용한다. 실제 파일의 존재/해시와 원본을 확인하고 추측한 경로나 대체 동물 사진을 쓰지 않는다.

| 항목 | 성공한 H 공식 예제 | 이번 Lab |
|---|---|---|
| 대상 | 공식 인간 | 실제 검은 Labrador 1마리 |
| instance color ID | BLUE | 기존 RED 대응 |
| 출력 W×H | 896×512 | 512×896 |
| source | 공식17f,16fps | 기존 f0~16,24fps |
| 파일 길이 | 17/16초 | 17/24초 |
| 참조/조건 cache | G/H 공식 cache | **새 Lab 전용 P cache** |

공식 cache에는 사람 예제의 text/CLIP/reference/driving/mask/noise 등이 들어 있으므로 Lab에 재사용하지 않는다. G의 `phase_prepare.py`는 `parent_official/run.json`과 초기 noise hash를 고정하고, H의 `cuda_probe.restore`, `run_phase`, `phase_sample`, `phase_decode`에도 공식 cache hash/가로형 shape/16fps가 하드코딩되어 있다. **이것을 삭제해서 검사 우회하지 말고 Lab의 명시적 config/manifest에서 기대값을 읽는 최소 변경**으로 바꾼다.

- 검증된 공식 코드·원본 출력은 그대로 남긴다. 새 B-008 코드가 지원할 case는 기존 official과 lab 두 계약으로 제한한다. 범용 job framework를 만들지 않는다.
- 실제 Lab 파일별 SHA, 전처리 tensor shape/dtype/value hash, RGB/mask 동일 crop/resize, reference/driver 색상 대응을 기록한다.
- mask의 얇은 앞발·꼬리·바닥 반사 경계는 기존 PARTIAL_UNRESOLVED를 유지한다. 모르는 관절이나 접촉을 정답으로 채우지 않는다. 새 segmentation 모델이나 결과를 본 뒤의 mask 수정은 이번에 하지 않는다.
- Lab prompt는 이전에 사전 등록한 Lab prompt를 그대로 사용하고 문자열을 실행 전에 명시한다. 기존 값이 없거나 충돌할 때만 원본 변경 없이 짧은 대체문을 amendment로 사전 고정하고, 출력 관찰 후 수정하지 않는다. 원본에서 보이지 않는 윙크·킥·추가 동물을 넣지 않는다.

## 3. 시간·shape·RNG 계약

- source f0~f16의 sample time은 t_i=i/24초다. 출력은17프레임/24fps, 파일 길이17/24=0.708333초, 양 끝 sample 간격16/24=0.666667초. 프레임 복제·보간·임의 duration stretching 금지.
- 24fps로 저장하는 것은 입력 시간축과 파일을 맞추는 일이지, 모델의 시간적 학습 분포를 바꾸는 것이 아니다. native16fps prior 차이는 품질 한계로 기록한다. 공식 인간16fps와 Lab24fps 결과 차이를 동물 도메인 하나의 인과효과라고 해석하지 않는다.
- shape는 config 및 실제 VAE stride/encode 결과에서 유도한다. 기존 `[16,5,64,112]`를 고정하거나 가로 tensor를 reshape해서 세로 조건을 만들지 않는다. Lab 예상 generated latent `[16,5,112,64]`, decoded `[3,17,896,512]`를 실제 결과와 대조한다. reference prefix와 generated latent의 시간축을 혼동하지 않는다.
- seed20261022, UniPC40steps, shift3, CFG5, history=None, segment17/overlap5, optional LoRA OFF, enhancer OFF를 사전 고정한다. negative prompt와 CFG2 branch는 고정 코드를 따른다.
- 공식 인간 예제와 동일 seed라고 Lab noise hash까지 같아야 하는 것은 아니다. Lab P에서 실제 생성한 noise와 RNG state를 보존하고 **Lab P→S 사이의 동일성**을 검증한다. 초기 noise를 최종 latent로 쓰지 않는다.
- CPU-only 작은 fixture에서 가로/세로 shape와16/24fps writer, case별 manifest validation, device 복원·dtype·RNG state 계약을 확인한 뒤 실제 P를 시작한다. 전체 타입 검사의 기존 부채를 모두 고치는 작업으로 확대하지 않는다.

## 4. 실제 실행과 보존

P: Lab text·reference·driving·mask와 초기 noise/RNG/scheduler 정보를 lossless 저장. P에는 DiT를 올리지 않는다. preprocessed 이미지와 tensor hash를 제공하고 새 cache provenance를 확인한다.

PROBE/S: 성공한 H와 동일한 비무작위 tiny CUDA 연산을 큰 CPU weight 적재 전에 수행하고 작은 anchor를 유지한다. condition leaf는 저장한 원래 device로 복원한다. CPU sigma/generator state를 전부 CUDA로 바꾸지 않는다. CPU loader와 후속 device 이동·sampler는 동일 수학적 경로를 유지한다. 새 CUDA 진단 API나 시스템 최적화를 동시에 넣지 않는다.

S: 40steps·CFG2 기준 실제80forward와40 scheduler step을 durable counter로 기록. final latent finite/shape/dtype·원자적 저장·값 hash·readback exact 확인 후 worker 종료. H 또는 G의 final latent를 Lab 결과처럼 사용하지 않는다.

D: S 종료·자원 회복 후 VAE만 로딩하고 Lab final latent를 원래 scaling 규약으로 복원한다. 결과 finite, 원본 RGB/raw17장, MP4 actual W/H/frame count/fps/decode를 검증한다. D 실패 시 final latent 보존, sampler 재시작 금지.

공식 H 실측 S약20분은 기준 관측이지 이번 소요시간 보장이 아니다. P/S/D/전체 작업, model load, sampler, decode, 자원 peak를 분리하고15초/두 동물 비용을 선형 외삽하지 않는다.

## 5. 사전 고정된 품질 검토 — baseline이지 성능 기여 증명이 아님

원본source/전처리source/참조/출력의 f0,4,8,12,16과 전체17장, native24fps 나란히 비교 MP4를 제공한다. framing을 다르게 확대해 체형·위치 변화를 숨기지 않는다. 첫 영상은 raw로 평가하며 업스케일·보간·face restore·warp·출력 선별을 넣지 않는다.

평가 축은 각각 PASS/FAIL/UNCERTAIN와 근거 프레임을 기록하고, 임의 총점/성공률/통계적 유의성을 만들지 않는다.

1. 실제 개체: 얼굴·주둥이·귀·검은 털의 질감·가슴/사지 비율. 검은 Lab 견종 유사성은 특정 반려견 identity 증명이 아니다. 한 참조에서 관측되지 않는 부위는 불확실로 남긴다.
2. 자세와 동작: 단순 직립/움직임 유무와 원본의 회전 방향·단계·앞발 이동·타이밍 추종을 분리한다. 체형이 다른데 source 픽셀 좌표와 똑같아야 한다고 강제하지 않는다.
3. reference/source 누수: 앉은 참조 포즈 고정, 원본의 가는 몸통/귀/얼굴/색 복사, 방/스튜디오 배경 영향을 개별 기록한다.
4. 형상/가림/경계: 머리·목·발·꼬리의 붕괴, mask 경계/바닥 반사/접촉. 보이지 않는 체중 분배를 추정해 판정하지 않는다.
5. 시간: 실제 연속 재생을 본 주체·관찰 여부를 적는다. 정적17장만 확인했다면 temporal=UNVERIFIED. 짧은 클립의 마지막→처음 loop 점프는 내부 불연속과 구분한다. 사람이 볼 수 있는 one-shot/프레임 이동용 로컬 HTML을 필요 시 제공하되 관찰을 대신했다고 하지 않는다.

과거 VACE 결과와 나란히 볼 수 있으나 해상도·조건 표현·모델·crop 등이 달라 **통제된 모델 우월성 실험이나 새 방법 ablation**이라고 부르지 않는다. 이번은 기존 모델의 실제 입력 한 건에 대한 탐색 기준선이다.

## 6. 학습·연구 연결

한국어 `lessons/B-008-reference-motion-generalization.md`를 작성한다. 직관 → 변수/가정 → 실제 tensor·코드 → 이번 관측 → 실패/반례 → 질문3개·별도해설 순서.

설명용 표현:
`c=E(R,D,M,prompt)`, `dz_t/dt=v_theta(z_t,t,c)`, `Y=Decode(z_final)`.
시간 방향/부호는 실제 scheduler와 연결한다. B-008은 theta를 학습하지 않고 입력 조건 c를 바꾸는 domain/instance baseline임을 분명히 한다. 두 사례 비교만으로 condition disentanglement의 원인을 증명하지 않는다.

필수 학습 항목: RGB driving과 image reference의 표현, 참조 pose leakage, morphology와 motion phase 분리, video VAE의 시간·공간 압축과16/24fps의 차이, dtype/device를 포함한 cache invalidation 조건. 조건 cache 재사용은 input과 encoder 계약이 같을 때만 허용됨을 실제 official→Lab 변경으로 설명한다.

논문 목표는 유지하되 이 결과를 신규 기여라고 부르지 않는다. 이후에는 실제로 관측된 반복 실패에 대해 선행 연구와 차이·학습 target·반증 가능한 가설을 정한다. 이번 상태에서 새 loss/adapter를 자동 학습하지 않는다.

## 7. GitHub 기록·종료

착수 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL/연구 범위 AGENTS 및 H RESULTS를 읽는다. 별도 연구 프로그램 문서 branch가 있더라도 GPU 실행 도중 자동 merge하지 않는다. 이번 계획·최소 case별 코드 변경·resolved config를 결과 관측 전에 commit한다.

HISTORY/ROADMAP에는 B-007H의 기술 baseline 확보와 B-008의 동물 품질 평가로의 전환을 짧게 기록한다. 기존 실패/미확인 결론은 보존한다. 결과 후 B-008 RESULTS, 실행 재현/실측, 한국어 학습 문서 및 HISTORY/ROADMAP을 갱신하고 연구 branch push·원격 SHA를 확인한다. 충돌 시 덮어쓰기/force push 대신 SYNC_PENDING으로 기록한다.

공개: 비민감 MD/코드/설정/집계/해시만. 비공개: 개인사진·source·mask·영상·latent·조건 cache·개인 경로·가중치·토큰. `git add .` 금지. 범용 타입-clean 주장은 실제 검사와 구분한다.

검토 ZIP은 실제 host /tmp/ 한 파일로 만들고 CRC/manifest/hash 및 Mac 전송 여부를 명시한다. 작은 MP4·시트·condition/final-latent sidecar·최종 latent·재현·실패 기록을 포함하고 weights/중복 대형 raw는 제외한다. Mac/Spark 절대 경로를 혼동하지 않는다. 영상·시트는 ZIP 밖에서도 바로 열 수 있게 남긴다.

실행이 끝나면 자기 worker 종료를 확인하고 다음 실험 **하나만 제안**한다. 새로운 CUDA 원인 감사·공식 예제 재생성·다른 모델·두 개체·15초·윙크·킥·학습으로 자동 확대하지 않는다. 생성 성공과 실제 Lab/안무/시간 품질 수용을 구분한다.

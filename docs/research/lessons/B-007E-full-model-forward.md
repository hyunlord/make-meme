# B-007E — 파일 변환에서 실제 모델 forward로

[입력 감사](../experiments/B-007E-scail-forward/INPUT_AUDIT.md) · [계획](../experiments/B-007E-scail-forward/PLAN.md). 현재 **LOAD_PASS·FIRST_FORWARD_PASS**이며 공식 예제의 token12992와 latent/attention shape는 실제 trace로 확인했다. sampler 로그40/40 뒤 post-sampler offload/decode 경계에서 시스템 메모리 guard로 중단됐다. 영상 출력은 없다. Lab shape는 소스 기반 예상으로 구분한다.

## 1. 가중치 파일과 실행 모델

B-007D의 65.58GB FP32 파일은 tensor 값의 저장물이다. Module은 architecture와 parameter/buffer를 가진 실행 객체다. 보통 architecture 초기화 후 checkpoint load와 state_dict copy를 수행하면 초기 parameter와 checkpoint tensor가 동시에 존재할 수 있다. meta-init은 초기 실제 storage를 생략하고 assign은 storage 소유를 넘길 수 있지만, key/shape·buffer·dtype·device가 완성돼야 forward할 수 있다.

FP32→BF16은 원소당 bytes를 4→2로 줄이지만 유효 자릿수도 달라진다. 원본 변환본의 byte-identical parity는 BF16 실행 모델의 수치 동일성으로 이어지지 않는다. parameter 메모리, temporary cast, activation, T5/CLIP/VAE, file page cache는 분리해 측정한다. unified memory를 CPU/GPU 두 용량으로 합산하지 않는다.

### 정밀도와 transient peak

FP32는 sign 1bit, exponent 8bit, fraction 23bit이고 BF16은 sign 1bit, exponent 8bit, fraction 7bit다. exponent 폭이 같아 비슷한 dynamic range를 갖지만 간격은 다르다. 정규화된 수를 round-to-nearest로 바꾸는 단순 모델에서는 BF16 상대 rounding 오차가 대략 `2^-8` 이하다. subnormal·overflow·연산 누적까지 이 식으로 보증하지 않는다. 값이 0에 가깝다면 상대오차만으로 판단하기 어렵다.

FP32 원본 P개 parameter의 storage는 `4P` bytes다. 실행 정책에서 P_b개를 BF16, P_f개를 FP32로 두면 최종 parameter bytes는 `2P_b+4P_f`다. 이것은 `peak=max_t M(t)`와 다르다. casting 중 source와 destination, 누적된 parameter, runtime·activation·page cache가 겹친다. 각 stage peak를 모두 더하는 것도 시간상 동시 상주를 과장한다. 실제 phase별 allocation/RSS/cgroup/시스템 메모리를 기록해야 한다.

이번 [staged_loader](../experiments/B-007E-scail-forward/code/staged_loader.py)는 CPU meta architecture와 정확한 checkpoint key/shape/F32 조건을 먼저 검사한다. `safe_open.get_tensor`로 하나씩 읽어 명시된 mixed dtype로 누적하며 time/head/norm/modulation 등 FP32 구간을 보존한다. `load_state_dict(strict=True,assign=True)`는 key 계약을 엄격히 검사하면서 이미 준비한 payload를 parameter로 연결한다. 기본 copy loading과 달라 초기 거대한 random parameter storage가 필요 없다. 단, assign 자체가 buffer·비등록 tensor·tied weight까지 모두 안전하게 해결하는 것은 아니다. 이 구현은 등록 buffer나 tied parameter를 발견하면 별도 정책 없이 통과시키지 않는다.

[공식 모델 635행](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L635)의 RoPE `freqs`는 dtype 변환을 피하려고 register_buffer를 사용하지 않은 tensor다. meta-init 뒤 state_dict만 채우면 이것이 meta에 남을 수 있다. loader는 공식 `rope_params`로 CPU에서 다시 만들고 직접 attribute까지 검사한다. 따라서 strict key PASS와 모든 실행 tensor materialization PASS는 다른 검사다.

## 2. 세 종류의 video token

H896W512 또는 H512W896은 같은 면적이다. 생성 대상17f의 VAE latent 예상은 C16,T5,H/8,W/8이다. 한 장 reference는 T1이며 공간 해상도는 동일하다. RGB driver는 pipeline에서 공간을 절반으로 줄여 encode하므로 예상 공간은 H/16,W/16이다. patch(1,2,2)라면 생성 token은 `5×(H/16)×(W/16)=8960`, reference는 `1×(H/16)×(W/16)=1792`, driver는 `5×(H/32)×(W/32)=2240`이다. 총12992 token이며 공식 예제의 실제 forward trace에서도 확인됐다.

[고정 pipeline](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L438)의 latent 준비와 [model](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py)의 token 결합을 실제 trace와 대조한다. mask는 개체 대응·배경 가시성 조건이다. mask color ID가 하나라고 video RGB의 pose나 identity가 자동 보장되는 것은 아니다.

[공식 forward 744행](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L744)은 reference와 generated latent를 시간축으로 붙여 patchify하고, RGB driving branch를 별도 patchify한 다음 token축으로 이어 붙인다. mask embedding은 각 branch feature에 더한다. text·CLIP context는 self-attention token 길이에 단순히 더하는 것이 아니라 별도 cross-attention context 경로로 들어간다.

예상 latent shape는 Lab 기준 generated `[16,5,112,64]`, reference `[16,1,112,64]`, driver `[16,5,56,32]`다. 공식 가로 예제는 H/W축만 서로 바뀐다. 모델 내부에는 i2v mask channel과 batch축이 추가되므로 이 VAE latent 표기와 patch embedding 입력 shape를 혼동하지 않는다.

40 heads, head dimension128이면 공식 예제에서 실제 관측한 self-attention Q/K/V shape는 `[1,12992,40,128]`이다. naive attention score는 head당 N² 요소를 가진다. naive score 요소 수는 `B×heads×N×N`이고 N=12992이면 약67.52억 개다. BF16 score 한 벌만 약13.50GB이며 이는 실제 FlashAttention allocation 예측이 아니다. FlashAttention은 IO와 중간 score materialization을 줄이지만 모델 parameter와 다른 activation을 없애지 않는다. 작은 kernel smoke 성공과 실제12992-token forward 성공은 다르다. wrapper에서 본 Q/K dtype와 kernel 직전 cast dtype도 구분한다.

## 3. Noise time과 물리적 video time

Flow path를 `zσ=(1−σ)x+σε`로 쓰면 `dzσ/dσ=ε−x`다. sampling은 높은σ에서0으로 간다. 고정 UniPC는 단순 Euler가 아니며 이전 model output을 재사용한다. shift3은 `σ′=3σ/(1+2σ)`의 schedule 재분배이며 물리적 fps 변경이 아니다. [scheduler의 flow prediction 변환](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L323)은 `x0_pred=sample−σ×model_output`이다. 위 경로에서 `zσ−σ(ε−x)=x`이므로 부호가 연결된다. 교육용 data-time t=1−σ 방향의 velocity x−ε와 부호가 반대다. 이를 epsilon prediction 또는 DDPM v-parameterization과 같은 이름으로 섞지 않는다.

CFG5에서는 `v=v_uncond+5(v_cond−v_uncond)`를 계산한다. [고정 두 forward 분기](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L391)에 따라 single17f segment40steps는 보통80 DiT 호출 예상이다. 실제 완료된 forward 수와 실패 위치는 hook trace로 확인한다.

Lab의 sample time은 `t_i=i/24`, 공식은 `i/16`이다. 출력17장의 파일 길이는 각각17/24와17/16초이고 첫~마지막 sample 간격은16/24와16/16초다. writer fps24는 입력 시간축을 보존하지만 model의16fps 설정·학습 motion prior가24fps에서도 올바른 동작을 재현한다는 증거가 아니다. loop 끝→처음 점프와 내부 불연속도 구분한다.

## 4. 무엇을 성공으로 부를 것인가

- LOAD_PASS: 실제 weights와 architecture 적재, key/buffer/dtype 계약 및 자원 확인.
- FIRST_FORWARD_PASS: 실제 조건과 token으로 한 DiT forward 완료.
- VIDEO_OUTPUT_PASS: sampler·VAE decode·17장 인코딩 완료.
- 개체·동작 수용: 실제 reference/source와 비교한 별도 시각 판단.

앞 단계만으로 뒤 단계를 인정하지 않는다. 연속 재생을 직접 확인하지 못하면 temporal=UNVERIFIED다. 전체 로딩은 14:06:15 UTC 시작되어 14:10:44 UTC에 LOAD_PASS를 확인했다. 공식 예제는 첫 forward 완료와 token/latent shape를 확인했다. sampler 로그40/40은 확인했지만 offload/decode 경계에서 중단되어 end-to-end 출력은 없다. LoRA 업데이트는0이다.

[질문](../experiments/B-007E-scail-forward/QUESTIONS_KO.md) · [해설](../experiments/B-007E-scail-forward/ANSWERS_KO.md)

## 5. 실제 로딩 관측 — forward와 구분

실제 전체 로딩 시간은 268.587초다. `loader.json`에서 tensor 1,307개(974 BF16,333 FP32), parameter **16,395,544,384개**, payload **33,166,820,096 bytes**를 확인했다. 이 parameter 수는 적재된 SCAIL DiT의 실제 합계이며 T5·CLIP·VAE를 모두 합친 전체 pipeline 수가 아니다. 이름의14B를 이 실측치 대신 사용하지 않는다. dtype별 숫자974/333은 tensor 개수이며 각 dtype의 parameter 개수가 아니므로 단순 비율로 메모리를 계산하지 않는다.

strict=True,assign=True 결과 missing/unexpected key는 모두 빈 목록이다. RoPE는 CPU 실물 `[8192,64]` complex128로 확인됐다. 여기까지는 architecture·weight 연결과 materialization의 증거다. 실제 condition으로 DiT를 계산하거나 VAE decode를 완료한 증거가 아니다.

공식 sampler 로그40/40 이후 offload/decode 경계에서 중단됐으며 첫 forward 완료는 확인됐다. token12992는 실제 확인했고 CFG80회는 전체40steps가 끝났을 때 확인할 예상 호출 수다. LOAD_PASS나 FIRST_FORWARD_PASS만으로 VIDEO_OUTPUT_PASS 또는 개체·안무 수용을 선언하지 않는다.

### 실제 공식 예제의 첫 forward 진입

14:12:05 UTC에 첫 DiT forward **진입**을 관측했다. 이 진입에 대응하는 첫 forward는 아래 시각에 완료됐다. 공식 가로 예제의 실제 generated latent는 `[16,5,64,112]` FP32, reference는 `[16,1,64,112]`, reference mask는 `[28,6,64,112]`, RGB pose latent는 `[16,5,32,56]`, driving mask는 `[28,5,32,56]`다. reference mask의 T6은 reference T1과 generated T5의 결합에 대응한다.

실제 text context는 `[5,4096]` BF16, CLIP context는 `[1,257,1280]` FP16이다. 이 text 길이5는 이번 prompt의 실제 encoding 결과이며 모든 prompt에서 고정된 수가 아니다.

attention wrapper에서 Q/K는 `[1,12992,40,128]` FP32, V는 같은 shape의 BF16으로 관측됐다. 예상 token12992는 이번 진입 trace에서 확인됐지만, 이 wrapper dtype를 최종 FlashAttention kernel dtype로 오인하지 않는다. upstream wrapper가 수행하는 kernel 직전 변환은 별도 단계다. 진입 시 GPU allocated는34,076,237,312 bytes였다. 이는 전체 peak·reserved·cgroup·시스템 메모리의 대체값이 아니다.

진입 시점의 증거는 올바른 shape의 입력을 받은 지점까지였다. 이후 첫 forward 완료와 finite 출력을 확인했다. 80회 forward 완료는 직접 계측하지 않았으며, decode·MP4·시각 품질과 구분한다.

### 첫 forward 완료

14:12:28.710 UTC에 **FIRST_FORWARD_PASS**를 확인했다. 입력 진입14:12:05.853에서22.856초이며 출력 finite=True다. 첫 sampling step40.30초와 한 forward22.856초는 측정 구간이 다르다. 이후 sampler 로그40/40을 확인했지만 offload/decode 경계에서 중단됐다.

실제 patch embedding은 `[1,5120,6,32,56]`, pose patch는 `[1,5120,5,16,28]`이다. 첫 branch token10752와 driver2240을 더하면12992다. 호출 kwarg `seq_len=1e10`은 sentinel이며 실제 token 수가 아니다. 앞의 wrapper shape를 실제 token 관측으로 쓴다. 이 full forward PASS는 작은 FA kernel smoke보다 강한 실행 증거지만 전체 sampler·영상 품질 성공을 대신하지 않는다.

### 실행 중 통합 메모리 회계의 한계

공식 sampler 5/40 시점에서 cgroup MemoryCurrent=16,060,981,248 bytes였지만 CUDA allocated는 약34GB, 프로세스 RSS는 약15GB, 시스템 MemAvailable은 약40GB로 관측됐다. 각 계측의 대상과 시점이 다르며 cgroup이 모든 CUDA 통합 메모리 allocation을 포괄한다고 볼 수 없다. 따라서 **64GiB cgroup cap이 전체 GPU 메모리까지 제한한다고 주장하지 않는다**. 시스템 MemAvailable watchdog과 CUDA allocator·cgroup 관측을 함께 유지해야 한다. 이들은 서로 더해서 총 사용량으로 계산하는 값도 아니다.

warm-up 이후 약24초/step이라는 중간 관측은 진행 중 표본이다. 전체 sampler 시간·최종 peak·남은 시간 보장을 뜻하지 않으며 최종 결과와 구분한다.

## 최종 결과: sampler 뒤 offload/decode 경계에서 안전 종료

14:30:22 UTC에 시스템 MemAvailable이23.898979GiB로24GiB guard 아래로 내려가 종료됐다. swap0·OOM0이며, CUDA OOM 예외나 kernel 오류로 판정하지 않는다. sampler 로그는40/40이지만 raw_output.pt·MP4는 만들어지지 않았다. 따라서 LOAD_PASS·FIRST_FORWARD_PASS는 유지하고 **VIDEO_OUTPUT_PASS는 아니다**. Lab는 NOT_RUN, review_outputs.py도 NOT_RUN이다.

최종 denoised latent는 현재 보존되지 않았다. 저장된 initial noise는 최종 latent의 대체물이 아니다. 첫 forward CUDA peak를 decode peak라고 재사용하지 않는다. decode allocator peak와 메모리의 객체별 원인 분해는 미측정이다. 정확한 소스 경로·가설·후속 한 실험은 [POSTMORTEM](../experiments/B-007E-scail-forward/POSTMORTEM.md)에 정리했다. 재시도·추가 생성은 하지 않는다.

정정된 세부 원인: model.cpu()→empty_cache()→vae.decode() 사이 hook이 없으므로 실제 decode 진입은 **UNOBSERVED**다. RssAnon 약13GB→33,101,068KiB 증가는 GPU→CPU offload의 순간 공존과 부합하지만 원인을 확정하지 않는다. 다음 한 실험은 최종 latent checkpoint와 해당 phase hook을 갖춘 제한적 post-sampler 메모리 전이 관측이다.

후속 실험의 단일 변경은 post-loop의 `self.model.cpu()`만 생략하여 DiT를 GPU에 둔 채 decode하는 것이다. 다른 offload 정책은 유지하고 최종 denoised latent checkpoint와 전이별 phase hook을 사전 등록한다. CPU copy와 GPU cached weight의 순간 공존을 피할 수 있다는 가설이며, GPU에 남은 DiT와 VAE가 같은24GiB headroom guard 아래 들어간다는 보장은 없다. 정확한 기존 종료 subphase는 계속 UNOBSERVED다. 새 tiling·프로세스 분리 등 다른 개입을 동시에 넣지 않으며 이번에 실행하지 않았다.

# B-007B — 가중치 변환부터 실제 모델 forward까지

[Gate1 합성 fixture](../experiments/B-007B-scail-baseline/GATE1_SUMMARY.json)는 통과했고 Gate2 선택 파일 다운로드·해시 검증도 완료했다. 그러나 실제 SAT checkpoint의 NumPy globals 사전 검사에서 metadata gate가 **BLOCKED**됐다. 실제 변환·모델 forward·영상 inference는 0/2회, LoRA와 optimizer update는 0회다. 아래 모델 shape·호출 수 예상값을 실측으로 읽지 않는다.

## 1. 이름을 바꾸는 것과 모델을 바꾸는 것

SAT와 Wan은 같은 의미의 parameter를 서로 다른 이름·묶음으로 저장한다. 입력 hidden dimension D, head 개수 H라 하면 한 self-attention의 packed projection weight는 `W_qkv ∈ R^(3D×D)`이고, dim0의 연속 세 구간을 `W_q,W_k,W_v ∈ R^(D×D)`로 나눈다. bias도 같은 순서로3D→D씩 나뉜다. cross-attention KV와 CLIP feature KV는2D→D씩 나눈다.

`[Wq;Wk;Wv] x = [Wq x;Wk x;Wv x]`

이므로 transpose·순서·dtype를 보존하면 분리 자체가 함수를 바꾸지 않는다. 반대로 q와 k를 바꾸면 shape가 맞아도 다른 모델이다. [공식 매핑](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L105)을 그대로 불러 쓰고, 작은 fixture에서 공식 전체 매핑/save_file 출력과 key·dtype·shape·contiguity·값·byte SHA를 비교했다. q/k/v 위치는 별도 수동 slice 기대값으로도 확인했다.

실제 Spark CPU torch2.14.0+cu130에서8개 검증이1.21초에 통과했다. BF16/F32/F16을 섞은 숫자 fixture이며 실제 SCAIL 가중치의 유효성이나 동작 품질 증거는 아니다. [구현·실행 경계](../experiments/B-007B-scail-baseline/CONVERSION_DESIGN.md).

## 2. mmap과 streaming이 없애는 복사, 없애지 못하는 비용

공식 `torch.load`는 저장된 device 복원을 포함할 수 있다. 이번 converter는 CPU/weights_only/mmap을 명시하고 FakeTensor metadata gate를 먼저 적용한다. unsafe globals나 mmap 불가 형식을 발견하면 실행을 멈춘다. 임의 allowlist나 unsafe pickle fallback은 없다.

safetensors는 dtype·shape·offset을 담은 header 뒤에 연속 tensor bytes를 둔다. 연속 tensor의 i번째 byte 위치는 `file_data_start + tensor_offset + i`다. 변환기는 전체 model의 bytes를 한꺼번에 만들지 않고8MiB 이하 view를 순서대로 쓴다. BF16을 FP32로 바꾸거나 큰 `.contiguous()` 복사를 하지 않는다. noncontiguous 입력은 거부한다.

mmap은 파일의 필요한 페이지를 가져오는 방식이지 메모리 사용0이라는 의미가 아니다. resident source pages·dirty output cache·metadata·runtime가 실제 통합 메모리를 사용한다. 그러므로 `8MiB chunk`는 RSS의 상한이 아니다. 외부 cgroup·MemAvailable·swap·deadline guard와 실제 peak 관측을 유지한다. 변환 종료와 모델 loading을 별도 프로세스로 나누면 변환의 mmap 수명을 끝낼 수 있다.

독립 verifier는 safetensors parser로 metadata를 읽고 source와 output bytes를 chunk별로 다시 hash한다. converter 자체 manifest만 재확인하는 순환 검증을 피한다. fixture의 output payload1byte를 바꾼 경우 검증 실패를 확인했다. 실제 대형 검증은 아직 NOT_RUN이다.

## 3. 저장 dtype 보존과 runtime mixed-BF16은 별개다

converter는 원본 dtype를 보존한다. 반면 [runtime_loader.py](../experiments/B-007B-scail-baseline/code/runtime_loader.py)의 실행 정책은 meta 모델을 만들고 parameter별로 읽어 BF16 또는 FP32로 배치한다. time embedding/projection, head, normalization, modulation, 지정된 CLIP projection LayerNorm은 FP32로 유지하고 나머지를 BF16으로 둔다. 이 정책은 공식 FP32 loading과 바이트·수치 동일하다는 주장이 아니다. 실제 로드 보고서의 source_dtype와 loaded_dtype를 각각 읽어야 한다.

meta tensor는 shape/dtype 정보를 갖지만 실제 weight storage가 없다. 작은 tensor를 하나씩 로딩하는 이유는 초기 거대한 random FP32 parameter와 checkpoint 전체를 동시에 materialize하는 peak를 줄이기 위해서다. 모든 key·shape·실제 storage 대입과 RoPE buffer 생성이 끝나야 forward 가능한 모델이다. 이 방식도 최종 parameter resident와 activation·VAE·T5·CLIP 비용을 없애지 않는다.

## 4. 작은 커널과 실제 token sequence

B007A의 kernel query는 `(1,64,40,128)`이었다. 실제 단일 reference,17프레임,H896/W512에서 코드 예상 latent는 생성 `(16,5,112,64)`, reference `(16,1,112,64)`, half-space driver `(16,5,56,32)`다. patch1×2×2라면 reference+생성10,752와 driver2,240, 총N12,992 tokens다. self QKV는 batch1 기준 `(1,12992,40,128)` 예상이며 실제 hook shape는 아직 미관측이다. [조건 결합 코드](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741).

attention은 `softmax(QKᵀ/√128)V`다. FlashAttention은 전체 score 행렬을 저장하지 않지만 dense pair 계산을 없애지는 않는다. tiny kernel이 통과해도 full sequence 메모리·시간·수치·다른 VAE/encoder가 성공하는지 따로 확인해야 한다.

## 5. UniPC Flow Matching의 시간 방향과 호출 수

물리 영상 시간 τ와 noise level σ를 구분한다. 실제 scheduler의 선형 경로는 `zσ=(1−σ)x+σε`이며, 학습 velocity target은 `v=ε−x`다. σ는 noise 쪽에서0쪽으로 감소한다. 직관용 Euler는 `z_next=z+(σ_next−σ)vθ`이며, 음수 Δσ가 noise→data 방향을 만든다. 첫날 toy의 t가 noise→data로 증가했다면 σ=1−t이므로 부호가 반대다.

실제 실행은 단순 Euler가 아니라 [FlowUniPCMultistepScheduler](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L281)다. default predict_x0 경로에서 `x0_pred=sample−σ*model_output`을 사용하고, 이전 model output을 활용하는 predictor/corrector로 다음 상태를 계산한다. schedule은 감소하는 σ에 `σ'=sσ/[1+(s−1)σ]` shift를 적용하고 끝에0을 붙인다. [실제 schedule](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/fm_solvers_unipc.py#L184). 변수명이 noise_pred여도 이 경로를 DDPM epsilon prediction으로 바꾸어 설명하면 안 된다.

[모델 루프](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L385)는 guidance g>1일 때 조건·비조건 prediction을 각각 계산한다.

`v_cfg = v_uncond + g(v_cond−v_uncond)`

따라서40 sampling steps,단일 segment,조건/비조건 각1회가 모두 완료되면80 DiT forward가 예상된다. 이것은40프레임이나80개 영상 생성이 아니다. UniPC corrector는 저장한 output을 활용하며 이 loop에 추가 모델 호출을 넣지 않는다. 중단·다중 segment·guidance≤1이면 실제 횟수가 달라지므로 최종 trace를 확인한다. 현재80회는 코드 예상이지 실행 완료 수가 아니다.

## 6. 24fps 저장과16fps 학습 prior

원본17장의 sample time은 τ_i=i/24초, 끝점 간격16/24초, 파일 표시 길이17/24초다. writer를24fps로 명시하는 것은 이 표시 시간을 지키기 위한 변경이다. 모델의 학습된16fps temporal prior를24fps에 맞게 재학습한 것은 아니다. 안무 phase·속도·접촉은 동일 원본 시각에서 별도 평가해야 한다. frame 복제·보간으로 조건 실패를 숨기지 않는다.

## 7. 실제로 어디까지 도달했는가

- 실제 SAT metadata: NumPy globals 사전 검사에서 BLOCKED. 원본 weight dtype/count·안전 mmap 지원은 아직 미관측.
- 대형 변환·독립 hash 검증·최대 메모리: NOT_RUN / NOT_MEASURED.
- 실제 DiT/VAE/text/reference shape·full sequence forward: NOT_RUN.
- output frames·fps·개체/안무·시간 품질: NOT_RUN. 실제 연속 재생을 관찰하지 못하면 시간 품질 UNVERIFIED로 남긴다.

[질문](../experiments/B-007B-scail-baseline/QUESTIONS_KO.md)과 [해설](../experiments/B-007B-scail-baseline/ANSWERS_KO.md)은 분리했다.


실제 차단된 이름은 `numpy.core.multiarray._reconstruct`, `numpy.ndarray`, `numpy.dtype`다. 우리 fail-closed guard가 `torch.load`를 부르기 전에 멈췄으므로 FlashAttention이나 모델 forward가 실패했다고 해석하면 안 된다. 추가 read-only opcode 문맥에서는 np_rng_state → MT19937 → NumPy 재구성·dtype u4·shape624가 이어져 RNG metadata라는 강한 단서를 얻었다. 이는 원본을 unpickle하거나 수정한 결과가 아니며 전체 참조 graph에서 model storage와 독립이라는 증명까지 수행한 것은 아니다. 파일 해시 검증은 provenance·완전성을 확인할 뿐 모든 pickle 재구성을 안전하게 허용한다는 뜻이 아니다.

다음에는 비텐서 metadata의 위치·참조 graph와 weight 보존을 안전하게 감사하는 한 경로만 검토한다. 실제 제거·호환 로더 구현·baseline 재개는 별도 승인과 검증 후의 작업이다. 이번에는 allowlist나 unsafe unpickle로 차단을 넘지 않았고, 원본·실패·미실행 기록을 그대로 보존했다.

실패한 metadata 프로세스의 sampler와 systemd가 각각 503,808 bytes와 331,776 bytes를 기록했지만, 프로세스 전체 RSS를 대표하는 신뢰할 수 있는 peak 측정으로 볼 수 없다. 따라서 이 단계의 실제 peak도 **NOT_MEASURED**이며, 이 수치를 대형 checkpoint 처리의 메모리 근거로 사용하지 않는다.

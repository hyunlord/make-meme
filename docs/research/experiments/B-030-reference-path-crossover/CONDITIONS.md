# B-030 조건과 계보

## 실제 파생

기존 B-027의 human/vehicle R1·R2 cache에서 각 행의 나머지 입력을 유지하고 양 CFG의 `clip_fea`만 반대 참조에서 복사했다. encoder·target·prefix 계산은 0회다. 기존 파일은 변경하지 않았으며 새 safetensors/metadata/receipt를 B-030에 별도로 저장했다.

| 과제 | 새 셀 | VAE + reference mask | CLIP | 기존 cache 대비 |
|---|---|---|---|---|
| human | Y12 (`cases/R1`) | B027 R1 | B027 R2 | t2/t8 변경,14leaf 보존 |
| human | Y21 (`cases/R2`) | B027 R2 | B027 R1 | t2/t8 변경,14leaf 보존 |
| vehicle | Y12 (`cases/R1`) | B027 R1 | B027 R2 | t2/t8 변경,14leaf 보존 |
| vehicle | Y21 (`cases/R2`) | B027 R2 | B027 R1 | t2/t8 변경,14leaf 보존 |

[PREREGISTRATION.json](PREREGISTRATION.json)에 원래 행·CLIP donor cache SHA256, 새 cache SHA256,16leaf별 shape/dtype/SHA256, 실제 noise 파일·tensor SHA256, 코드 및 private freeze manifest SHA256을 고정했다. 경로명만으로 계보를 판단하지 않는다.

## 보존 경계

`structure` 전체(dict/list/scalar 및 원래 device)가 부모 둘과 정확히 같다. t0 noise, t1/t7 text, t3/t9 reference VAE, t4/t10 reference mask, t5/t11 driving, t6/t12 driving mask, t13 generator state, t14 timestep, t15 sigma를 행의 값 그대로 유지한다. t2/t8만 donor의 CLIP과 같은 shape/dtype/값이다. `initial_noise.pt` 파일은 양 부모·파생 사이 byte-identical이다.

두 부모의 기존 B027 producer receipt·pair 계약을 먼저 확인한다. 새 consumer에서는2변경/14보존과 구조·provenance·noise·resolved config를 다시 확인한다. CPU cache copy 중 RNG는 변경되지 않았고 저장후 모든 tensor값이 exact readback으로 확인됐다. 이 검사는 독립 GPU 계산을 byte-identical하다고 요구하는 검사가 아니다.

## 실행 연결

기존 공식 sampler 추출·loader·decode는 유지한다. 새 worker에는 `phase_encode`가 없고 ENC stage도 허용하지 않는다. B029 gate 모듈을 포함하지 않으며 pinned upstream SHA와 공식 cross-attention method module을 검증한다. LoRA/ALG/manualRoPE OFF, replacement True, history/additional_ref None이다.

첫 실제 positive/negative forward에서 복원된 cache의 `ref_latents`, `ref_masks`, `clip_fea`, `pose_latents` object 연결을 확인하고 해당 hash·crossover parent를 남긴다. 관측용 추가 forward나 attention dump는 없다. 실제 final latent에는 새 condition SHA256과40step/80forward counter가 연결되고 decode가 이를 검사한다.

## 해석 범위

VAE와 reference mask는 하나의 행 묶음이다. 이 묶음의 차이를 VAE 단독 또는 순수 pose 효과라고 하지 않는다. CLIP도 자세·공간 정보를 담을 수 있다. 교차는 같은 target track의 두 사진이지만 학습에서 익숙하지 않은 조건 조합일 수 있다.

## 실제 실행 후 확인

네 교차 셀 모두 첫 positive/negative 두 호출의 실제 ref/CLIP/mask hash가 해당 파생 cache와 일치했다. 각40step·80forward 이후 새 condition SHA를 가진 final latent가 저장되고, 각각17프레임·896×512·preview24fps MP4가 생성됐다. 원본 cache 변경·encoder 호출·추가 관측 forward는 없다. 이 실행 확인은 경로의 의미를 pose/identity로 분리했다는 품질 판정이 아니다.

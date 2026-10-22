# B-007E 로더 분석 — 실행 전

현재 상태: **tiny actual architecture CPU fixture PASS / full load NOT_RUN**.

고정 upstream commit `78fe19576bb06be96c2375e088574a262a300edb`의 `wan/scail.py:113–115`는 `SCAIL2Model.from_config`로 기본 FP32 파라미터를 만든 뒤 `safetensors.load_file`과 기본 `load_state_dict` 복사를 수행한다. 공식 FP32 checkpoint payload는 65,582,313,560 bytes다. 초기 모델 파라미터와 checkpoint 쪽 mapping/page residency가 동시에 존재하여 약131.16GB의 두 FP32 논리 사본이 필요할 수 있다. 실제 resident peak는 mmap/pagecache/allocator에 따라 달라지며 이 수치는 측정치가 아니다. T5/CLIP/VAE와 activation은 별도다.

새 `staged_loader.py`는 기존 B007B 실험 로더의 meta-init/per-tensor 교체를 좁게 강화한다. 공식 architecture를 meta에서 생성하고 전체 checkpoint key, shape, F32 source dtype를 먼저 검사한다. 이후 한 tensor씩 CPU safe_open으로 읽고 지정 dtype으로 변환해 참조 dict에 모은 뒤 `model.load_state_dict(cast_state, strict=True, assign=True)`를 한 번 호출한다. missing/unexpected 결과가 실제로 빈 목록인지 검사·기록한다. dict와 모델은 동일한 cast payload를 참조하며 추가 parameter copy를 만들지 않는다. 전체 FP32 모델 allocation이나 전체 FP32 state_dict 복사를 추가하지 않는다. 단, 누적 BF16/FP32 모델과 mmap 원본 page cache, 최대 단일 tensor 변환 transient는 남으며 함수 자체가 OS 메모리 안전성을 보증하지 않는다.

정책은 time_embedding/time_projection/head, norm/modulation 및 image MLP의 정확한 LayerNorm 경로 `img_emb.proj.0/4`를 FP32로 유지하고 나머지를 BF16으로 읽는다. 공식 time forward는 명시적으로 FP32 계산과 결과 dtype을 요구한다. 모든 값을 BF16으로 변환하는 것은 아니다. FP32→BF16 반올림은 원본 값 동등성과 다른 실험 조건이며 B007D의 FP32 byte parity를 BF16 출력 품질 parity로 바꾸어 주장하지 않는다.

`model_scail2.py:635–648`의 `freqs`는 dtype 변환을 막기 위해 register_buffer를 사용하지 않는 complex128 tensor다. meta 생성 후 이 속성을 그대로 두면 실제 device 전송에서 실패한다. loader는 공식 `rope_params`를 CPU에서 다시 호출해 같은 complex128 값을 만든다. 파라미터·persistent/nonpersistent buffer·직접 tensor 속성에 남은 meta를 검사한다. 현재 공식 SCAIL에 등록 buffer가 없음을 작은 실제 architecture에서 확인했으며, 등록 buffer나 tied parameter가 생기면 자동 추정하지 않고 거부한다. 일반 모델용 범용 loader가 아니다. 임의 깊이의 Python container 안에 숨은 tensor를 탐색하는 기능은 없으며 고정 architecture에만 적용한다.

전체 key/shape 사전 검사 뒤 공식 PyTorch strict/assign 로딩 semantics와 hook 경로를 실제 사용한다. 같은 dtype fixture는 원본값과 정확히 일치하며 mixed fixture는 명시한 cast값과 정확히 일치한다. 원본 모델 전체 forward와 품질은 별도 미실행이다.

## 사전 검증

Ruff E4/E7/E9/F/I 검사 통과. Mac 기존 environment의 basedpyright standard 검사에서 코드 타입 문제는 정리했고 `safetensors`, `safetensors.torch` 미설치 import 진단2개가 남는다. 이를 type clean으로 보고하지 않는다. 신규 dependency는 설치하지 않았다. 실제 작은 fixture와 full model 로딩은 별도 기록한다.

API: `load_model(config_path, checkpoint_path, phase_hook=None)`는 CPU model만 반환한다. `B007E_LOADER_REPORT`는 새 private JSON 경로여야 한다. phase hook: dit_meta_init_start/done, dit_staged_weights_done, dit_loader_complete_cpu. GPU 이동/전체 forward/추론 budget 및 OS watchdog는 runner 책임이다.


## 실행된 CPU fixture
Spark 기존 B007B 격리 환경에서 tiny actual SCAIL i2v(dim128, ffn256, head1, layer1, freq32)를 생성했다. v1은 upstream package initializer가 T5 기본인자에서 CUDA 초기화를 시도해 CPU-only import에서 실패(6PASS/1FAIL). fixture에서만 namespace package를 설정해 해당 eager initializer를 건너뛰고 실제 model_scail2.py 및 attention.py는 그대로 import했다. v2는7PASS2.30초. strict/assign 경로 변경 후 v3도7PASS2.36초다. 초기 실패 로그를 보존했다.

검사: 전체key와 cast값 일치, 원본RoPE complex128 값 일치, missing/unexpected 빈목록, missing/unexpected/shape/source-dtype 거부, 등록nonpersistent buffer와unregisteredmeta 거부, FP32imageMLPnorm/time/projection/head 연산 finite. 전체 DiT/FlashAttention forward, pretrained weights, GPU·diffusion 실행은0회다. BF16반올림은 tensor.to(bfloat16)와 정확히 일치함을 확인했으며 원래FP32와 동일하다는 뜻이 아니다.

최종 타입 표현 정리 후7개 fixture 재확인2.30초. load_state_dict 결과는 Module 임의 속성 대신 TypedDict 반환으로 report에 기록한다. 최종 loader SHA `63db4df57de32a6c5316c20575bb5ed9b2c851af8aa2b2c8959814cbc3277cf8`.

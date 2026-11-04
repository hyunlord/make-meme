# VACE 14B BF16 변환 준비 (아직 실행하지 않음)

V-001 `code/e2_cast_bf16.py`(SHA256 76609f052e0d0301f9f60de4f3f4fe2e7a7203bd4632949ba428b607d1f12bd3)의 순차 shard 변환·원자 저장·readback bit 검증 구조를 재사용했다. 새 `code/convert_vace_bf16.py`는 VACE의 단일 7-shard index와 FP32/BF16 혼합 저장 형식에 맞춘다. 설치·모델 import·실제 변환·GPU 실행은 이 준비 단계에서 0회다.

## 실제 헤더

7개 shard, 1,331 tensor. 1–6번은 FP32 총 57,153,966,336 bytes, 7번은 이미 BF16 6,098,202,624 bytes다. 변환 payload는 34,675,185,792 bytes (32.293783 GiB). 기존 BF16 tensor도 `original.to(bfloat16)`과 모든 byte를 비교한다. 원본은 보존한다.

원본 index `metadata.total_size`는 69,350,371,584로 전체를 FP32로 계산한 값이며 실제 헤더 payload 63,252,168,960과 다르다. 원본 index는 수정하지 않고 이 차이를 receipt에 남긴다. 입력 key-map 및 확인한 원본 metadata 값을 검사한 뒤 변환 index에 실제 BF16 payload 값을 기록한다.

## 로더 확인

실제 설치된 DiffSynth의 `diffsynth/core/vram/disk_map.py:48–64`는 전달된 shard 경로의 safetensors를 열고 저장 dtype tensor를 얻은 후 필요한 dtype으로 변환한다. `diffsynth/core/vram/layers.py:132–143`은 `.to(dtype=torch_dtype, device=device)` 후 `load_state_dict(assign=True)`한다. 기존 V002 `vace_entry.py`의 14B 분기는 preparing/computation dtype 모두 bfloat16이다. 따라서 config.weights를 **변환이 COMPLETE_VERIFIED_CPU_CAST로 끝난 별도 폴더**로 지정하면 기존 로더가 BF16 파일을 사용한다. loader 코드를 바꾸지 않는다. fileglob는 7개 변환 shard만 선택해야 한다.

## 사전 메모리 계산 주의

사용자 예시 약67GiB는 BF16 파일 page cache를 제외한 합이다. 보수적으로 전체 BF16 파일 cache 32.294 + 전체 BF16 resident 32.294 + T5/VAE 약11.06 + 활성값24 = 99.648GiB이며 host/temporary 여유4GiB를 더하면 103.648GiB로 100GiB를 넘는다. 이 계산은 모델 불가능성의 증명이 아니라 보수적 상한 추정이다.

기존 disk-offload의 vram_limit=24는 현재 CUDA 사용량을 검사하는 soft 한도이며 module 단위 적재가 이를 넘을 수 있다. 단순히 resident를 24로 대체하여 엄격한 상한이라고 주장하면 안 된다. 변환 후 실제 선택된 실행 경로와 활성값 근거로 root가 peak를 재평가하고 100GiB 이하임을 뒷받침할 때만 실행한다. 페이지 cache가 자동으로 사라진다고 가정하지 않는다.

## 실행 계약과 준비 검증

기존 연구 Python에서 `convert_vace_bf16.py --config PRIVATE.json --cpu-only`는 header/schema/disk 여유만 검사한다. config 키는 source_root,target_root,receipt(모두 절대경로). target/receipt는 반드시 새 경로다. 실제 변환은 동일 명령에서 --cpu-only를 빼고, root가 후보 선택·외부 작업 관측 후 단일 흐름에서 실행한다. 내부에서 CUDA_VISIBLE_DEVICES 빈 문자열, nice +10, CPU threads2를 설정한다.

실제 Spark 원본 헤더를 stdin 실행으로 검사한 결과 HEADERS_PASS,7shard/1331tensor/target34675185792bytes,torch_imported=false였다. py_compile PASS. 실제 tensor bit 검증은 변환 실행 전이므로 NOT_RUN이다.

## 추가 정적 분석: 기존 offload의 실제 적재 단위

실제 `layers.py:65–75`의 `check_free_vram()`은 `cuda.mem_get_info`의 total-minus-free 사용량과 24GiB를 비교한다. torch allocated만 보는 것은 아니다. 다음 module의 크기를 먼저 더하지는 않는다. `AutoWrappedModule.forward:201–205`와 `AutoWrappedLinear.forward:472–477`은 아래일 때 preparing 상태로 적재·유지하고, 위일 때 computation 경로의 임시 module/tensor를 사용한다. `AutoWrappedModule.computation:185–197`에서 disk→computation은 `copy_module=True`; BF16 파일과 computation dtype이 같아 FP32→BF16 CUDA 중복은 없다. `load_state_dict(assign=True)`도 전체 두 번째 parameter copy를 만들지 않는다.

`vram_management_module_maps.py:144–153`에서 WanModel은 DiTBlock의 nonrecursive wrapper와 하위 Linear 등으로 분할한다. `:175–181`에서 VACE의 DiTBlock은 whole-block wrapper다. 실제 헤더를 BF16 bytes로 합산한 최대 단위는 `vace_blocks.0` 807,666,688 bytes = 0.7522GiB, 나머지 VACE block 755,227,648 bytes = 0.7034GiB이다. 최대 단일 Linear `time_projection.1` weight는 314,572,800 bytes = 0.2930GiB다.

따라서 이 실행 경로의 transformer resident 계획치는 24GiB + 최대 보존 overshoot 0.7522 + 동시에 실행되는 임시 block 0.7522 = 약25.505GiB, 반올림 26GiB로 둘 근거가 있다. 이는 순차 무gradient 실행, wrapper가 실제 해당 모듈에 적용됨, 임시 module 수명이 forward 내로 제한됨을 전제로 한 계획 추정이며 보장 상한이 아니다. memory allocator reserved/driver 공간과 활성값은 별도다.

이 가정에서 transformer 파일 cache32.295 + resident26 + T5/VAE11.06 + 활성값24 + host여유4 = 97.355GiB다. **단, 이 합에는 T5/VAE 원본 파일 cache가 resident tensor와 별도로 끝까지 남는 최악 경우의 약11.06GiB가 추가되지 않았다.** 그 별도 cache까지 모두 동시에 남으면108.415GiB다. helper의 적재 전 cache 비우기만으로 이후 새로 읽힌 파일 cache의 소실을 보장할 수 없다. 실제 계획은 이 두 경우와 reclaimable cache 가정을 명시해야 하며, 아래 추정을 택하려면 해당 가정의 근거를 기록해야 한다. 새로운 offload/cache framework나 정책 변경을 제안하거나 구현하지 않았다.

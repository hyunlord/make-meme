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

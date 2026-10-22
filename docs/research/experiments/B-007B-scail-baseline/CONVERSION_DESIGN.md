# Gate 1 — mmap CPU 변환 설계와 고정 비교

상태: `f1cbdff` 고정 후 Spark CPU의 작은 fixture 8/8 PASS. [실행 요약](GATE1_SUMMARY.json). 실제 대형 checkpoint 호환성·변환 peak는 UNKNOWN이다. 새 모델 다운로드·GPU·diffusion·학습 실행은 없다.

## 유지하는 것과 바꾸는 것

공식 Wan commit `78fe19576bb06be96c2375e088574a262a300edb`의 convert.py SHA256 `0519f688643b0a2c3f13660f196e34280704ddb3e2575aa226e2d2f8f2b4397f`를 확인한 뒤 그 파일의 `get_new_mappings`를 그대로 호출한다. 원본을 수정하지 않는다. QKV는 dim0의 q/k/v 순서, KV는 k/v 순서이며 dtype와 shape·연속값을 바꾸지 않는다. 공식 전체 mapping의 duplicate 덮어쓰기 대신 중복은 오류로 중단한다.

공식 기본 torch.load와 전체 save_file만 교체한다. `torch.load(map_location="cpu",weights_only=True,mmap=True)`를 사용하며, 먼저 FakeTensorMode metadata gate에서 전체 key mapping·layout·dtype를 검사한다. unsafe globals가 있으면 거부하고 allowlist나 weights_only=False fallback을 추가하지 않는다. legacy serialization/mmap 불가·비연속 tensor·미지원 dtype도 중단한다. weights_only는 임의 pickle 실행 위험을 줄이지만 악성 파일의 자원 고갈까지 막는 sandbox는 아니므로 고정 HF bytes/hash 확인 및 외부 resource guard가 별도로 필요하다. [PyTorch2.14 serialization](https://docs.pytorch.org/docs/2.14/notes/serialization.html), [torch.load](https://docs.pytorch.org/docs/2.14/generated/torch.load.html).

연속 CPU tensor를 uint8 view→NumPy view→memoryview로 노출하여 최대8MiB slice씩 출력한다. 전체 `.clone()`, `.contiguous()`, dtype cast, `.tobytes()`를 production converter에 쓰지 않는다. scalar는 reshape(-1) 후 byte view다. 공식 QKV split의 storage offset을 유지한 연속 view를 그대로 순차 직렬화한다. safetensors의8byte little-endian header length, JSON dtype/shape/offset,8byte header padding, 연속 데이터 영역을 쓴다. [공식 형식](https://github.com/safetensors/safetensors#format).

원본 파일은 읽기 전용이다. 출력은 `.partial`에 배타적으로 생성하며 실패·중단 시 partial을 보존한다. fsync 후 같은 filesystem의 no-overwrite hardlink로 최종 이름을 공개하고 partial 이름을 제거한다. 파일이 이미 있으면 덮어쓰지 않는다. 완료 표시는 WRITTEN_REQUIRES_INDEPENDENT_VERIFICATION이며 tensor별 hash/dtype/shape/bytes manifest를 남긴다. 최종 대형 output은 별도 bounded reader 검증과 resource 측정 후에만 사용할 수 있다.

## 작은 fixture의 판정 기준

27개 입력 key가 모든 공식 mapping 분기를 포함한다. BF16/F32/F16, QKV/KV weight와 bias를 섞는다. 공식 `get_new_state_dict`+`safetensors.save_file` 출력과 key 집합·dtype·shape·contiguity·각 tensor 값 및 byte SHA256을 비교한다. 파일 header 정렬이 다를 수 있어 전체 파일 byte 동일성을 요구하지 않는다. q/k/v의 위치는 별도의 수동 slice 기대값으로도 검사한다.

scalar/empty tensor와 shared-storage split을 추가 확인한다. 비연속 입력·변경된 공식 source·unsafe pickle global·legacy serialization·기존 출력 덮어쓰기는 모두 거부해야 한다. fixture는 합성 숫자이며 실제 모델 호환성·개체 품질·대형 peak 검증이 아니다.

## 메모리·운영 경계

mmap은 page fault로 파일 페이지를 읽는다. 명시적 전체 CPU/GPU 복사를 제거하지만 RSS/page cache가 계속 작다고 보장하지 않는다. 변환 프로세스가 종료되면 mapping을 해제하고 이후 모델 loader를 별도 프로세스로 실행한다. 입력 mmap resident pages, 출력 dirty cache, runtime·metadata·단일 tensor view가 공유 통합메모리를 사용한다. 코드의8MiB slice는 전체 RSS 상한이 아니다.

runtime 담당자의 독립 cgroup/메모리·swap·deadline guard 아래에서만 대형 작업을 실행한다. 실제 metadata gate가 통과하기 전 대형 변환을 강행하지 않는다. safetensors 출력 dtype는 원본 그대로이므로 이후 meta+assign 로더가 dtype를 임의로 BF16으로 바꾸었다고 가정하면 안 된다. 로더 경로와 모델 peak는 별도 소유·검증이다.

## 재현

기존 격리 Python에서 `SCAIL_CONVERT_SOURCE=<검증된 pinned convert.py> python -m pytest code/test_conversion.py -q`로 합성 검증한다. 변환은 외부 guard 아래 `python code/converter.py <checkpoint> <pinned convert.py> <output.safetensors>`다. 이 문서는 실제 다운로드/실행 승인이나 성공 기록을 대체하지 않는다.


## 실제 실행과 재현 증거

Spark CPU Python3.12.3, torch2.14.0+cu130, safetensors0.8.0, pytest8.4.2에서 8개 비교가1.21초에 통과했다. GPU를 숨기고120초 timeout을 적용했다. 앞선 pytest 미설치 시도는 fixture 실행 전 중단됐고, 독립 B007B 환경에 테스트 의존성을 설치한 뒤 실행했다. Mac CPU의 사전8개 비교도 통과했으나 Spark 결과를 대체하지 않는다.

`converter_verify.py`는 Rust safetensors parser로 key/dtype/shape/format을 확인한 뒤, source CPU mmap과 출력 파일을 tensor별 최대8MiB로 읽어 SHA256을 비교한다. `safetensors.load_file`로 전체 출력 state를 materialize하지 않는다. 실제 source metadata mapping과 값을 다시 대조하므로 converter가 작성한 manifest만 믿는 검사가 아니다. synthetic 출력의 payload1byte를 바꾸자 검증이 거부됐다.

대형 변환 뒤 별도 resource/deadline guard 아래 `python code/converter_verify.py <checkpoint> <pinned convert.py> <output.safetensors>`로 검증한다. 원본 mmap resident/file cache는 여전히 메모리에 포함되므로 검사 자체도 무제한 실행하지 않는다. 실제 checkpoint의 안전한 mmap 지원과 대형 변환·검증 peak는 아직 미측정이다.

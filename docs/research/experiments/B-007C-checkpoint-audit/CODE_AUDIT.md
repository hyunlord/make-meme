# B-007C 공식 배포와 serialization 코드 감사

확인일: 2026-10-22. 이 문서는 소스·소형 HTTP metadata·환경 import의 증거다. 실제 65GB checkpoint의 신규 `torch.load`나 변환을 실행한 기록이 아니다. 작은 fixture의 실제 결과는 [RESULTS](RESULTS.md)에 별도로 기록한다.

## 공식 tensor-only export

공식 HF API의 `main`과 기존 revision `150cc0ca4e98e50e60b9295dacde39442fdccab2`를 각각 조회했다. 같은 revision이며 파일 12개에 SCAIL 본체 safetensors는 없다. 본체는 `model/1/fsdp2_rank_0000_checkpoint.pt`; 나머지는 VAE·CLIP·T5·tokenizer·두 optional LoRA·문서다. 따라서 **조회한 공식 배포 범위에서는 ready-made tensor-only export를 찾지 못했다**. 인터넷 전체에 존재하지 않는다는 주장은 아니다. [공식 고정 tree](https://huggingface.co/zai-org/SCAIL-2/tree/150cc0ca4e98e50e60b9295dacde39442fdccab2).

GitHub 현재 branch head도 기존과 같았다: wan `78fe19576bb06be96c2375e088574a262a300edb`, sat `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`. [공식 README](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md)는 SAT checkpoint에서 로컬 변환을 요구한다. [convert.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py)의 mapping은 tensor 변환 규칙의 근거이며, 원본 전체 pickle을 안전하게 읽어도 된다는 인증은 아니다.

## 실제 버전과 제한된 unpickler

Spark 기존 격리 환경에서 CPU import만 실행했다. Torch `2.14.0+cu130`, git `08187d9e0fba026dc8217405802ab5381dc88d90`, NumPy `2.5.2`다. NumPy 소스 tag의 commit은 `48fecee5453aa1d31e6b79dcb3969dc1a6d1a891`이다.

- [get_unsafe_globals_in_checkpoint](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/torch/serialization.py#L343)는 pickle globals를 정적으로 모아 기본 및 사용자 허용 목록과 비교한다. 동적으로 만들어지는 class까지 완전히 예측하지 않는다.
- [restricted Unpickler](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/torch/_weights_only_unpickler.py#L307)는 GLOBAL을 제한한다. 그러나 허용된 REDUCE 함수는 `func(*args)`로 호출하며, 허용된 BUILD 객체는 `__setstate__` 등을 실행할 수 있다. `weights_only=True`는 비실행 파서가 아니다.
- [safe_globals 구현](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/torch/_weights_only_unpickler.py#L112)은 context 진입/종료에서 **프로세스 공용** 허용 집합을 추가/제거한다. thread-local 보안 경계가 아니다. 격리된 단일 작업 subprocess, 겹치는 context 없음, 진입/종료 허용 집합 대조가 필요하다. context 자체는 OS sandbox가 아니다.
- `mmap=True`는 storage 파일 페이지의 로딩 방법, `map_location='cpu'`는 위치, FakeTensorMode는 tensor storage materialization 억제다. 셋 모두 pickle의 허용된 함수 실행과 비텐서 객체 할당을 제거하지 않는다. [공식 serialization 문서](https://docs.pytorch.org/docs/2.14/notes/serialization.html), [torch.load](https://docs.pytorch.org/docs/2.14/generated/torch.load.html).

## NumPy 세 global과 동적 dtype

실제 환경의 `_reconstruct.__module__`은 `numpy._core.multiarray`; 기존 checkpoint 문자열은 `numpy.core.multiarray._reconstruct`다. future scoped mapping은 이 alias를 명시적으로 기록해야 한다. [NumPy _reconstruct](https://github.com/numpy/numpy/blob/48fecee5453aa1d31e6b79dcb3969dc1a6d1a891/numpy/_core/src/multiarray/multiarraymodule.c#L3162)는 ndarray subtype·shape·dtype를 받아 배열을 만든다. [array_setstate](https://github.com/numpy/numpy/blob/48fecee5453aa1d31e6b79dcb3969dc1a6d1a891/numpy/_core/src/multiarray/methods.c#L2031)는 shape·dtype·order·rawdata로 상태를 복원한다. 단순 텍스트 metadata 조회가 아니다.

CPU에서 `type(numpy.dtype(numpy.uint32))`는 `numpy.dtypes.UInt32DType`로 확인됐다. dtype factory가 생성하는 구체 class는 static GLOBAL 목록에 없을 수 있다. 따라서 세 이름만 허용했다고 완전한 동적 요구를 확인한 것은 아니다. dtype 종류를 임의 확대하지 말고 fixture에서 관측한 정확한 class와 alias만 별도로 검토한다. 안전성 검토는 이름뿐 아니라 subtype·shape·byte length·object dtype 여부와 allocation 상한까지 필요하다.

## 해법 비교와 현재 한계

| 경로 | 장점 | 필요한 증거 / 위험 |
|---|---|---|
| 공식 tensor-only 배포 | 로컬 NumPy 복원 의존성 회피 | 현재 조회한 공식 배포에는 없음. publisher provenance와 key/dtype/shape/value parity 필요 |
| 비실행 정적 분리 | reducer를 호출하지 않고 graph·storage 참조 분석 가능 | stack/memo alias/FRAME/protocol/persistent ref를 정확히 보존해야 함. 문자열 삭제는 불가. 범용 parser를 만들 정도면 이번 범위를 초과 |
| scoped safe_globals + weights_only | upstream 제한 unpickler와 tensor reconstruction 사용 | 허용 함수·BUILD가 실행됨. 동적 dtype, 프로세스 공용 허용 집합, allocation 위험. 이번에는 작은 fixture에 한정 |

B-007B opcode 근접성만으로 RNG와 model storage의 독립성을 입증하지 않는다. 이번 graph 감사가 독립성을 확인하더라도 실제 tensor 값을 읽고 검증한 것과 다르다. 작은 fixture PASS도 실제 checkpoint의 metadata load·변환·model peak를 승인하지 않는다. 후속 한 경로의 최종 선택은 이번 실제 감사 결과를 근거로 [RESULTS](RESULTS.md)에 정리한다. 실제 대형 allowlist 로딩은 후속 PLAN과 별도 결정 대상이다.

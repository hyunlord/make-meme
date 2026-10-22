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

### Fixture v1에서 관측한 ambient 허용 집합

실행 담당자가 보고한 첫 fixture는 FakeTensor의 lazy initialization 과정에서 framework globals 10개가 추가되어, 시작 시점과 종료 시점의 전체 허용 집합 동일성 검사를 통과하지 못했다. 실패는 보존한다. 이것을 NumPy context가 10개를 유출했다는 증거로 단정하지 않는다. 수정된 검증 설계는 별도 fresh process에서 FakeTensor를 먼저 준비하고 ambient 허용 집합을 기록한 뒤, 정확한 NumPy 항목 4개의 scoped context 진입·종료를 비교한다. 기존 ambient 항목을 지워 성공을 만들지 않는다. 이 수정만으로 최종 PASS가 확정된 것은 아니다. 이후 상태는 아래 실제 감사 결과에 기록한다. 이 prewarm은 권한 축소나 sandbox가 아니라 초기화와 context 복구 효과를 분리하는 측정 조건이다.

## 실제 비실행 graph 감사 결과

실행 담당자의 실제 전체 정적 감사는 151.633초에 완료됐으며 원본 SHA256은 전후 동일했다. data.pkl 163,821 bytes, opcode 31,271개, graph node 16,374개, storage 참조 989개, ZIP member 993개를 확인했다. member는 모두 STORED이며 storage bytes 합계는 65,582,182,608이다.

지원된 opcode를 대상으로 memo alias까지 추적한 결과, NumPy globals 세 개와 `_codecs.encode`의 도달 root는 `np_rng_state`뿐이었다. tensor rebuild와 OrderedDict global **기호**는 module 및 torch/cuda RNG root에서 공유되지만, root 사이에 공유되는 비리터럴 객체 node나 storage key는 관측되지 않았다. module은 FloatStorage 987개, torch/cuda RNG는 ByteStorage 합계 2개로 분리됐다. 이는 앞선 단순 opcode 인접성보다 강한 구조적 증거다. 다만 비실행 graph 분석의 지원 opcode·모델링 범위 안에서의 결과이며, 실제 tensor 값을 읽거나 큰 checkpoint를 역직렬화한 검증은 아니다.

최종 소형 fixture v3는 **PASS**이며, v1·v2 실패도 보존한다. 실제 wall time 1.85초, max RSS 593,476 KiB, swap 0이었다. strict 거부, 동적 dtype 요구, 예상하지 않은 global에 대한 negative 검사가 통과했다. materialized load의 mmap=False/True 양쪽에서 값·dtype·shape·stride·offset과 실제 공유 storage를 확인했다. 공식 mapping의 출력 5개 key와 760-byte safetensors roundtrip도 통과했다.

중요한 한계: FakeTensor 경로의 storage 객체 alias 동일성은 **NOT_PRESERVED**였다. 대신 tensor metadata와 실제 ZIP storage offset 4806의 대응을 확인했다. 이 관측을 FakeTensor의 물리적 storage 공유 성공으로 표현하지 않는다. ambient 허용 목록은 초기 73개에서 prewarm 후 83개로 늘었다. 이 10개 framework 항목은 초기화 효과로 기록하고 유지했으며, 그 기준에서 NumPy 4개 scoped 항목의 context 종료 복구를 검사했다. 두 초기 실패를 숨기거나 전체 허용 목록을 지워 성공시킨 것이 아니다.

이 PASS는 작은 fixture의 제한된 경로에만 해당한다. 실제 65GB checkpoint의 scoped load·metadata/FakeTensor 호환성·값 검증·변환·모델 peak는 **NOT_RUN/NOT_MEASURED**다.

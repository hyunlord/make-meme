# B-007C 결과 — RNG 의존성 감사 완료, 실제 변환은 미실행

2026-10-22 · **AUDIT_PASS (한정된 감사·후속 경로 선정)**. 실제 65GB checkpoint의 restricted loading·tensor-only 변환·모델 로드·영상 추론은 **NOT_RUN**이다. 작은 fixture 성공을 대형 파일의 안전성 또는 메모리 적합성 보장으로 확대하지 않는다.

시작 원격 HEAD `6e2594fea94a31340989e022339d2c4340d23e0d`. 계획과 코드는 실행 전에 연구 브랜치에 등록했고, 두 synthetic 검사 실패와 수정 이유를 [RUNNING](RUNNING.md)에 보존했다. B-007B의 unsupported globals gate와 원본은 변경하지 않았다.

## 실제 파일에서 확인한 것

| 항목 | 관측 |
|---|---|
| SAT 파일 | 65,582,563,395 bytes |
| 전후 SHA256 | `d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f`, 동일 |
| ZIP | 993 members, 전부 ZIP_STORED, format3/little endian |
| data.pkl | 163,821 bytes, protocol2, 31,271 opcodes |
| symbolic graph | 16,374 nodes, 7개 top-level root |
| storage 참조 | 989개: module FloatStorage987, torch/cuda RNG ByteStorage2 |
| storage ZIP bytes | 65,582,182,608 |
| NumPy globals | `_reconstruct`, `ndarray`, `dtype` 모두 `np_rng_state`에서만 도달 |
| root 간 공유 | nonliteral 객체0, storage key 공유0; 함수/class 심볼 공유는 존재 |
| 실제 역직렬화 | 0회, reducer/BUILD 실행0 |

최상위 root는 iteration, lr_scheduler, random_rng_state, np_rng_state, torch_rng_state, cuda_rng_state, module이다. memo alias와 BUILD 상태 연결을 포함해 분석했다. `_codecs.encode` 역시 이 파일에서는 NumPy RNG subtree에만 연결된다. tensor rebuild와 OrderedDict **심볼**이 여러 root에 공유되는 것과 실제 storage가 공유되는 것은 다르다.

NumPy subtree는 ndarray subtype, 초기 shape `[0]`, dtype `u4`, little endian, 최종 shape `[624]`, Fortran=false, MT19937 상태를 선언한다. raw 데이터 표현은 `_codecs.encode(unicode, 'latin1')`이며 문자열 2496개 codepoint가 모두 0~255여서 `624×4=2496 bytes`에 대응한다. NumPy RNG subtree의 persistent storage 참조는0이다. 실제 NumPy 배열을 만들거나 reducer를 호출해 얻은 결과가 아니다.

이것은 **고정 파일의 비실행 구문 의존성 감사**다. 임의 callable의 반환 alias, `__setstate__` 부작용까지 모델링한 일반 증명은 아니다. 선언된 FloatStorage 합계16,395,544,384 elements도 실행된 모델의 parameter count가 아니다. storage CRC는 기록된 ZIP 필드이며 전부 재계산하지 않았다. 전체 파일 SHA는 직접 전후 계산했고 기존 다운로드 장부 SHA도 보존됐다. [공개 요약](evidence_summary.json).

## 작은 fixture: 실제로 실행한 범위

실제 파일 대신 자체 생성한 작은 tensor3개와 NumPy RNG를 사용했다. noncontiguous view, offset, 공유 storage를 포함한다. 원본 tiny fixture를 보존하고 새 tiny ZIP의 GLOBAL 철자 한 곳만 `numpy._core`에서 실제 checkpoint의 `numpy.core`로 바꿨다. 다른 member bytes는 전부 같음을 확인했다. 이 fixture 준비 코드를 실제 파일에 적용하지 않았다.

| 검사 | 결과 |
|---|---|
| 기존 strict gate | NumPy 세 global 거부, 예상대로 |
| exact alias+ndarray+dtype만 허용 | 동적 UInt32DType 부재로 거부, 예상대로 |
| 네 항목 scoped + weights_only, mmap false/true | keys·값·dtype·shape·stride·offset·실제 storage 공유 PASS |
| 예상 밖 class | 거부 PASS |
| NumPy context 종료 | 초기화 후 ambient 허용 집합으로 복원 PASS |
| FakeTensor metadata | dtype·shape·stride·offset 및 실제 ZIP payload offset4806 일치 PASS |
| FakeTensor 객체 identity 공유 | **NOT_PRESERVED**, 실제 storage 공유 PASS로 해석하지 않음 |
| 공식 mapping + safetensors | 작은 Q/K/V split 포함5 keys, 값·dtype·shape roundtrip PASS |
| safetensors storage alias | 연속 독립 payload로 저장하므로 보존 대상 아님 |

실행한 NumPy 추가 허용은 legacy alias를 명시한 `_reconstruct`, `numpy.ndarray`, `numpy.dtype`, `numpy.dtypes.UInt32DType` 네 항목이다. 이는 전체 허용 집합이 아니다. 기존 환경 import 시 ambient73개, FakeTensor 초기화 후83개가 관측됐다. `safe_globals`는 프로세스 공용 집합을 변경하므로 dedicated subprocess가 필요하며 sandbox가 아니다.

첫 실행은 FakeTensor lazy import의 framework globals10개 추가 때문에 복원 검사가 실패했다. 원인만 분리한 두 번째 실행은 FakeTensor storage의 Python identity를 물리 alias로 가정한 검사에서 실패했다. 두 실패를 보존하고, 마지막 실행에서 실제 ZIP offset 근거와 원래 CPU storage 공유 검사를 분리했다. 검사 삭제로 정상 처리한 것이 아니라 **실패한 가정과 보존된 성질을 나눠 기록**했다. 세 실행 모두 synthetic이며 실제 checkpoint 로딩은0이다.

## 시간·자원·미실행

실제 읽기 전용 감사151.633초. 한 live sample의 VmRSS/VmHWM45,908KiB, cgroup anon37,502,976 bytes, file cache1,572,626,432 bytes였다. 최종 Python peak는 NOT_MEASURED이며 약1.5GiB cgroup charge를 모델 메모리로 부르지 않는다. CPU audit에는2GiB MemoryMax/1.5GiB MemoryHigh/swap0/1200초 guard를 적용했다.

최종 fixture wall1.85초, 내부 검사0.685초, maxRSS593,476KiB, swap0. 실제 대형 mmap/FakeTensor 메모리와 변환 peak는 NOT_MEASURED다. 신규 대형 다운로드0, 실제 checkpoint unpickle0, 대형 변환0, diffusion0, 학습0. A/VACE/ComfyUI를 수정하거나 다른 프로세스를 종료하지 않았다.

## 선택한 다음 한 경로

**공식 SHA에 고정한 별도 프로세스의 exact scoped safe_globals + weights_only=True + CPU mmap/FakeTensor metadata 검증을 먼저 수행하고, 그 결과가 통과할 때만 기존 bounded tensor-only 변환기로 연결하는 경로**를 선택한다. 이번에는 실행하지 않았다.

선정 이유: 공식 배포에서 tensor-only 본체 export를 찾지 못했고, 직접 pickle graph를 재작성하거나 일반 static extractor를 새로 만드는 것은 이번보다 넓은 검증 책임을 만든다. 현재 경로는 실제 NumPy 사용처·인자 형태를 정적으로 확인했고 legacy alias와 동적 dtype 및 tensor parity를 작은 fixture에서 검증했다. 단, 허용된 NumPy 함수/BUILD는 실제 실행되므로 무위험이라고 부르지 않는다.

후속 실행의 필수 순서와 중단 조건은 다음과 같다.

1. 동일 공식 파일 SHA·metadata 구조·고정 Torch/NumPy/변환 코드 hash만 허용한다. 사용자 임의 checkpoint에 재사용하지 않는다. 미지 global, 추가 dtype, 다른 RNG shape/byte length, graph 차이가 나오면 중단한다.
2. credential 없는 단일 subprocess와 읽기 전용 원본, 전용 출력, 네트워크/파일 접근 제한, cgroup 시간·메모리·swap 제한을 **실제로 검증**한다. 현재 CPU resource guard만으로 보안 sandbox가 완성됐다고 하지 않는다. 필요한 격리를 적용할 수 없으면 BLOCKED다.
3. FakeTensor 초기화 후 ambient allowlist를 동결·대조하고, 실제 graph에서 사용되는 정확한 global 집합을 별도 검사한다. 네 NumPy 항목 외 추가 신뢰 확장은 금지한다. framework 등록 항목이 많다는 사실을 숨기지 않는다.
4. metadata-only 최초 로드에서 module key·dtype·shape·stride·offset·storage 크기/ZIP 위치를 이번 static 결과와 대조한다. FakeTensor Python object identity에 기대지 않는다. unknown layout, 범위 초과, 메모리 압박은 차단한다.
5. 그다음에만 새 출력으로 bounded CPU mmap tensor 변환을 검토한다. 원본 불변 SHA, 공식 mapping, tensor별 논리 값/byte hash, dtype·shape·QKV 순서를 독립 검증하고 실패 출력도 보존한다. 작은 fixture parity는 이 실제 검증을 대체하지 않는다.

현재는 **후속 경로 선정 가능**, 실제 대형 변환의 안전 검증은 아직 미완료다. B-007B baseline은 여전히 미확보다. 전체 모델 로딩·영상 추론은 이 후속 변환 검증과도 별도 단계이며 자동 진행하지 않는다.

[재현](REPRODUCE.md) · [공식 코드 감사](CODE_AUDIT.md) · [한국어 이론](../../lessons/B-007C-serialization-and-metadata.md) · [질문](QUESTIONS_KO.md) · [해설](ANSWERS_KO.md)

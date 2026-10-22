# B-007C — 가중치와 RNG metadata는 어떻게 함께 저장되는가

실제 대형 checkpoint 신규 역직렬화·변환·모델 추론·학습은 수행하지 않는다. 아래 개념은 [고정 소스 감사](../experiments/B-007C-checkpoint-audit/CODE_AUDIT.md)와 연결한다. 실험 결과는 [RESULTS](../experiments/B-007C-checkpoint-audit/RESULTS.md)에 기록하며, 작은 fixture와 실제 checkpoint 증거를 구분한다.

## 1. 직관: 목차와 데이터 창고

PyTorch checkpoint는 tensor만 담는 파일일 필요가 없다. 학습기는 model state_dict와 함께 optimizer, step, Python/NumPy RNG state를 저장할 수 있다. ZIP의 `data.pkl`은 이 객체들의 관계와 tensor의 설명을, `data/<key>`는 실제 storage bytes를 담는다. pickle의 metadata가 작아도 전체 model은 클 수 있다. 반대로 tensor payload를 읽지 않았어도 pickle 객체를 복원하면서 코드를 실행할 수 있다.

B-007B에서 확인한 `np_rng_state → MT19937 → ndarray uint32 shape624`는 난수 상태라는 강한 구조적 단서였다. 그 근접성만으로 모든 memo 참조와 model storage가 독립이라고 단정할 수는 없다.

## 2. Tensor는 bytes와 view의 결합이다

일반적인 strided tensor를 다음처럼 생각한다.

`T = (storage S, dtype d, shape n, stride s, storage_offset o)`

유효한 index 벡터 `i`의 원소 위치는 element 단위로 `o + Σ i_k s_k`, byte 단위로 `itemsize(d) × (o + Σ i_k s_k)`다. shape만 같아도 stride나 offset이 다르면 다른 값이다. Q/K/V split처럼 여러 tensor가 같은 storage의 다른 영역을 가리킬 수도 있다. 따라서 storage 개수와 tensor 개수, 파일 bytes와 논리적 tensor bytes는 같다고 가정하지 않는다.

변환 동등성은 최소한 key·dtype·shape·값과 mapping 순서를 확인한다. safetensors로 연속 배열을 저장하면 원본 view의 stride나 공유 storage를 그대로 보존하지 않을 수 있지만, 각 논리 tensor의 값은 동일해야 한다. 원본 bytes hash와 변환 파일 hash가 서로 같아야 한다는 검사는 적절하지 않다. 각각의 provenance hash와 mapped tensor의 논리 byte hash를 구분한다.

## 3. 왜 단순한 pickle 문자열 삭제가 안 되는가

GLOBAL은 callable/class 식별자를, REDUCE는 callable과 인자의 조합을 표현한다. unpickler는 이를 실제 호출로 복원할 수 있다. memo는 이전 객체를 다시 가리키므로 graph의 alias를 만든다. BINPERSID는 torch storage 같은 외부 저장 단위를 연결한다.

`pickletools`로 opcode를 읽는 것은 reducer 호출과 다르다. 그러나 graph를 수정하려면 stack·memo·FRAME·protocol·persistent storage 참조를 모두 유지해야 한다. `np_rng_state`라는 문자열만 삭제하면 바로 뒤의 객체나 다른 곳에서 공유하는 참조가 안전하게 사라지는 것이 아니다. 이번 범위는 감사이며 범용 pickle 변환기 구현이 아니다.

## 4. RNG 상태와 추론 가중치의 역할

MT19937 state에는 624개의 uint32 값과 현재 위치 등이 들어간다. uint32 배열 부분만 `624 × 4 = 2496 bytes`이고 전체 pickle 크기는 별개다. 학습 재개에서 RNG를 잃으면 이후 dropout·sampling·augmentation 등의 난수열을 재현하지 못할 수 있다.

frozen inference용 tensor mapping은 보통 학습기의 RNG 객체 자체를 weight로 쓰지 않는다. 하지만 이것은 특정 checkpoint에서 RNG를 버려도 된다는 자동 증명이 아니다. 공식 convert.py가 읽는 module과 RNG 사이의 alias·storage 의존성을 감사하고, 값이 보존되는지 확인해야 한다. 새 추론 seed를 고정하는 일과 원래 학습 RNG를 보존하는 일도 구분한다.

## 5. 제한 unpickler와 메모리 기능의 경계

`weights_only=True`는 허용 객체만 복원하도록 제한한다. `safe_globals`에 넣은 함수는 REDUCE에서 호출될 수 있고 객체는 BUILD에서 상태 복원 함수를 실행할 수 있다. 따라서 scoped allowlist는 검토한 신뢰 범위를 확장하는 조치다. context를 쓰더라도 실제 구현의 허용 집합은 프로세스 공용이므로 겹치는 작업 없는 별도 subprocess가 필요하다.

Spark NumPy 2.5.2에서 dtype factory의 결과는 `numpy.dtypes.UInt32DType`다. 정적 GLOBAL 목록은 이처럼 동적으로 만들어지는 class를 빠뜨릴 수 있다. 현재 함수 module의 `_core`와 기존 파일의 `core` alias도 명시해야 한다.

`mmap`은 storage page를 필요할 때 가져온다. FakeTensorMode는 실제 tensor storage 대신 metadata를 다룬다. 이 기능들은 NumPy 복원 함수 실행·비텐서 할당·malformed metadata 위험을 없애지 않는다. CPU 배치·timeout·메모리 제한은 별도의 실행 정책이며 안전한 pickle이라는 증명은 아니다.

## 6. 작은 fixture가 답하는 질문

`{module: 작은 tensor dict, np_rng_state: 작은 실제 NumPy RNG state}` fixture는 기본 static guard가 왜 거부하는지, 최소 scoped 허용 후 동적 dtype가 요구되는지, context 종료 뒤 허용 집합이 복구되는지 확인할 수 있다. tensor key/dtype/shape/value parity는 비텐서 복원 경로가 이 fixture의 tensor 값을 바꾸지 않았다는 증거다.

그 결과를 65GB 실제 checkpoint의 전체 graph, storage 무결성, mmap 지원, peak 메모리로 확대하지 않는다. 실제 fixture 결과와 정적 파일 감사의 수치는 아래에 기록했다. 설계와 실제 확인한 범위를 구분한다.

[이해 질문](../experiments/B-007C-checkpoint-audit/QUESTIONS_KO.md) · [별도 해설](../experiments/B-007C-checkpoint-audit/ANSWERS_KO.md)

### Fixture v1에서 관측한 ambient 허용 집합

실행 담당자가 보고한 첫 fixture는 FakeTensor의 lazy initialization 과정에서 framework globals 10개가 추가되어, 시작 시점과 종료 시점의 전체 허용 집합 동일성 검사를 통과하지 못했다. 실패는 보존한다. 이것을 NumPy context가 10개를 유출했다는 증거로 단정하지 않는다. 수정된 검증 설계는 별도 fresh process에서 FakeTensor를 먼저 준비하고 ambient 허용 집합을 기록한 뒤, 정확한 NumPy 항목 4개의 scoped context 진입·종료를 비교한다. 기존 ambient 항목을 지워 성공을 만들지 않는다. 이 수정만으로 최종 PASS가 확정된 것은 아니다. 이후 상태는 아래 실제 감사 결과에 기록한다. 이 prewarm은 권한 축소나 sandbox가 아니라 초기화와 context 복구 효과를 분리하는 측정 조건이다.

## 실제 비실행 graph 감사 결과

실행 담당자의 실제 전체 정적 감사는 151.633초에 완료됐으며 원본 SHA256은 전후 동일했다. data.pkl 163,821 bytes, opcode 31,271개, graph node 16,374개, storage 참조 989개, ZIP member 993개를 확인했다. member는 모두 STORED이며 storage bytes 합계는 65,582,182,608이다.

지원된 opcode를 대상으로 memo alias까지 추적한 결과, NumPy globals 세 개와 `_codecs.encode`의 도달 root는 `np_rng_state`뿐이었다. tensor rebuild와 OrderedDict global **기호**는 module 및 torch/cuda RNG root에서 공유되지만, root 사이에 공유되는 비리터럴 객체 node나 storage key는 관측되지 않았다. module은 FloatStorage 987개, torch/cuda RNG는 ByteStorage 합계 2개로 분리됐다. 이는 앞선 단순 opcode 인접성보다 강한 구조적 증거다. 다만 비실행 graph 분석의 지원 opcode·모델링 범위 안에서의 결과이며, 실제 tensor 값을 읽거나 큰 checkpoint를 역직렬화한 검증은 아니다.

최종 소형 fixture v3는 **PASS**이며, v1·v2 실패도 보존한다. 실제 wall time 1.85초, max RSS 593,476 KiB, swap 0이었다. strict 거부, 동적 dtype 요구, 예상하지 않은 global에 대한 negative 검사가 통과했다. materialized load의 mmap=False/True 양쪽에서 값·dtype·shape·stride·offset과 실제 공유 storage를 확인했다. 공식 mapping의 출력 5개 key와 760-byte safetensors roundtrip도 통과했다.

중요한 한계: FakeTensor 경로의 storage 객체 alias 동일성은 **NOT_PRESERVED**였다. 대신 tensor metadata와 실제 ZIP storage offset 4806의 대응을 확인했다. 이 관측을 FakeTensor의 물리적 storage 공유 성공으로 표현하지 않는다. ambient 허용 목록은 초기 73개에서 prewarm 후 83개로 늘었다. 이 10개 framework 항목은 초기화 효과로 기록하고 유지했으며, 그 기준에서 NumPy 4개 scoped 항목의 context 종료 복구를 검사했다. 두 초기 실패를 숨기거나 전체 허용 목록을 지워 성공시킨 것이 아니다.

이 PASS는 작은 fixture의 제한된 경로에만 해당한다. 실제 65GB checkpoint의 scoped load·metadata/FakeTensor 호환성·값 검증·변환·모델 peak는 **NOT_RUN/NOT_MEASURED**다.

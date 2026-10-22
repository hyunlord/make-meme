# B-007C 사전 계획 — SCAIL SAT 체크포인트 RNG 메타데이터 직렬화 감사

작성: 2026-10-22 · 상태: **PLANNED / NOT_RUN** · parent: B-007B

## 목표와 현재 장애

B-007B는 필수 약80GB 자산 중 신규 68,111,049,006 bytes 다운로드 및 공식 파일 해시를 검증했다. 그러나 SAT 65,582,563,395-byte checkpoint의 PyTorch pickle metadata에서 NumPy globals 세 항목이 검출되어, 코드의 명시적 fail-closed 검사(실제 torch.load 이전)에서 BLOCKED. 변환·모델 로드·diffusion 추론·학습은 0회. 이것이 checkpoint 악성 판정이나 모델 성능 실패라는 주장은 없다.

관측 globals: numpy.core.multiarray._reconstruct, numpy.ndarray, numpy.dtype. 비실행 pickletools opcode에서는 np_rng_state / MT19937 / uint32 length624 부근에서 나타났다. **이 정적 인접 관계는 전역이 RNG 메타데이터에만 쓰였다는 완전한 증명은 아니다.**

**이번 질문:** 공식 checkpoint의 tensor state_dict와 비텐서 RNG 상태의 직렬화 의존성을 분리해, 안전한 tensor-only 변환을 진행할 수 있다는 증거를 확보할 수 있는가?

목표는 무단 역직렬화 보안 우회가 아니라, 공식 변환에 필요한 tensor를 안전하게 읽을 수 있도록 하는 것이다. 기존 68GB 다운로드와 해시 확인을 재사용한다.

## 범위/상한

- 연구 B만. A/기존 VACE/ComfyUI 및 기존 데이터는 손상·중단 금지.
- **신규 대형 파일 다운로드 0GB, 새 diffusion 추론 0회, full SCAIL 모델 로드 0회, optimizer update 0회.**
- 기존 SAT checkpoint는 **읽기 전용** 보존. 기존 convert.py, converter_mapping.py, 검증된 모델 hash 보존.
- 2시간 이내. CPU-first; read-only zip metadata/pickletools 정적 처리부터 진행. 명시된 테스트 외 신규 보조 파일/빌드/모델 설치 금지.
- 격리된 Python 실행 환경, CPU/GPU 제한과 cgroup/ulimit/timeouts, 메모리/디스크 guard를 기록. 안전한 static analysis만 수행하는 단계는 GPU 불필요.
- **torch.load(weights_only=False), pickle.load, 임의 exec/eval, 패키지 globals 대량 allowlist, 시스템-wide torch.serialization.add_safe_globals 금지.**
- pickletools.dis의 로그 출력을 그대로 공개하지 말고 private evidence에만 보존; 민감한 개인 경로나 원본 자산은 공개하지 않는다.
- 같은 오류를 피하기 위해 static global 검사 결과를 무조건 무시하거나, 실제 다운로드 모델의 tensor 내용을 조작하지 않는다.

## 1. 실제 ZIP/pickle 구조에 대한 비실행 감사

1. 기존 checkpoint 파일 경로/크기/hash, HF repo revision, B-007B 다운로드 장부를 현재 파일과 대조. 이미 확보된 원본을 새로 받지 않는다. 사전 기록 파일이 누락됐다면 BLOCKED.
2. Python zipfile로 archive members/CRC 및 PyTorch format version, data.pkl, storage 파일명/크기/position/zip compression을 점검. 전체 checkpoint 압축 해제 금지. 데이터 계층/스토리지 총계는 metadata로 계산.
3. pickletools.genops(data.pkl)로 GLOBAL/STACK_GLOBAL/REDUCE/BUILD/PERSID/BINPERSID, memo와 top-level dict keys/np_rng_state 인접 구조 조사. **opcode 출력은 실행이 아니며 pickle 구조의 동적 소유관계를 자동 증명하지 않는다.**
4. 포함한 numpy globals가 RNG subtree 밖에서 참조되는지 memo alias까지 찾아 구조적으로 감사하고, source tensor storage references와 RNG metadata 사이에 교차 공유가 없는지를 확인 가능한 범위에서 보고한다. 확실하지 않으면 UNKNOWN으로 기록.
5. 최신 PyTorch 공식 serialization 문서의 weights_only=True, safe_globals, mmap, FakeTensorMode 보안 특성을 구분한다. get_unsafe_globals_in_checkpoint()는 정적 검사라 동적으로 생기는 NumPy dtype 등의 추가 유형을 빠뜨릴 수 있다.

## 2. 안전한 해결 경로 비교 — 실행과 계획을 구분

A. 공식 출처의 tensor-only safetensors 또는 신뢰할 수 있는 publisher export가 있다면, 체크포인트 revision 및 required keys/shape 대조 가능성을 확인. 새 65GB 체크포인트를 자동 다운로드하지 않는다.

B. **비실행 정적 분리**가 가능한 기존 PyTorch ZIP/pickle 구조인지 검토한다. pickle opcode를 직접 편집하려면 stack/memo/FRAME/protocol/persistent storage ref 등이 불변임을 증명할 수 있어야 한다. 단순 replace/delete로 np_rng_state를 제거해 checkpoint를 변형하지 않는다. 범용 pickle 변환기 제작이 필요해지면 작업을 확대하지 않고 BLOCKED/연구 결과로 기록한다.

C. 차선책으로 PyTorch의 **국소적 torch.serialization.safe_globals context + weights_only=True** 후보를 검토한다. 이는 weights_only=False와 다르지만 allowlist의 함수·클래스는 재구성 중 호출/인스턴스화될 수 있으므로 무위험이 아니다. 공식 torch docs와 사용되는 정확한 NumPy 구현/version/function semantics, static globals 외 dynamic dtype 발생 가능성을 검토한다. 이번 단계에서는 **실제 65GB checkpoint를 신규 allowlist로 역직렬화하지 말고**, 별도의 작은 synthetic fixture로만 의미·출력·제한적 scope·메모리 안전성을 검증한다. 실제 checkpoint에 safe_globals를 적용하려면 정확한 격리 정책과 이유를 후속 PLAN에서 명시하고 별도 결정한다.

모든 해법에서 checkpoint provenance/hash를 고정하고, 원본 불변·tensor mapping 동등성 확인 방안이 없으면 PASS를 주지 않는다.

## 3. B-007B 실패 재현 및 검증 산출물

- 기존 fail-closed converter_metadata.py를 원형 그대로 실행하지 않고, B-007B 실패 로그·code commit/hash를 비교해 무엇이 검사 차단이었는지 재현성 검토.
- 소형 fixture로 **tensor module + NumPy RNG state** 같은 구조를 재현하고 (1) static globals 탐지, (2) strict gate 거부, (3) 제안한 안전한 경로의 metadata-only fixture 평가, (4) tensor keys/shape/dtype/value checks를 수행.
- fixture 테스트가 통과하더라도 65GB 실제 metadata/FakeTensor 경로, storage consistency, full conversion/14B 모델 메모리 적합성은 미검증.
- 논리적 종료 판정:
  * AUDIT_PASS: 실제 global이 어디 등장하는지 근거가 있고, 구현·보안 조건·원본 불변성을 포함한 **구체적 다음 한 경로**를 제시할 수 있음.
  * BLOCKED: 정적 정보만으로 tensor-only 안전 분리를 증명하기 어렵거나 추가 allowlist 위험을 수용하지 못함. 공식 tensor-only export 제공 요청/보안 격리된 후속 로딩 검토를 제안.
- 어떤 판정도 SCAIL model forward PASS 또는 diffusion inference 예산 사용으로 집계하지 않음.

## 4. 수학·학습 문서

한국어 lessons/B-007C-serialization-and-metadata.md:
- torch.save ZIP: pickle의 객체 graph vs 실제 tensor storage bytes, dtype/shape/stride/storage offset 관계.
- pickle opcode의 GLOBAL/REDUCE/memo가 왜 RCE 표면이며 pickletools 정적 inspection과 unpickling의 차이인지.
- RNG metadata(NumPy MT19937: state 624xuint32)의 재현 목적 vs 추론 가중치. 단순히 RNG를 버려도 학습 resume에는 영향이 있지만 frozen inference weight 변환에 어떤 부분을 요구하는지 분리.
- restricted unpickler(weights_only=True)의 범위와 safe_globals의 보안 tradeoff, PyTorch의 mmap/FakeTensorMode가 arbitrary pickle의 안전성을 대신하지 못하는 이유.
- 실제 파일의 evidence vs 추정, 안전한 checkpoint 변환의 tensor parity 검증 방법.
- 직관 → pickle/storage 실제 파일 구조 → 원리/간단한 자료구조식 → 작은 fixture → 미검증 → 이해 질문 3개 및 해설.

## 5. GitHub와 제출

사전 계획은 docs/research/experiments/B-007C-checkpoint-audit/PLAN.md로 고정. 시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL 및 B-007A/B-007B RESULTS를 읽고 사전 코드/fixture hash, 안전 예산을 커밋한다.

완료 후 RESULTS.md, CODE_AUDIT.md, 재현/실패 기록, lessons/B-007C-serialization-and-metadata.md, HISTORY.md, ROADMAP.md를 갱신·commit/push하고 실제 remote SHA 확인. 개인 원본 미디어·가중치/개인 절대 경로·SSH·토큰·raw pickle은 공개 저장소에 올리지 않음. 실제 단일 ZIP으로 Mac/Spark 복사 여부·CRC·files manifest·SHA256 확인.

**이번은 직렬화/메타데이터 감사까지만. 성공해도 65GB 전체 변환, 대형 모델 로드, 영상 생성 또는 학습은 자동 시작하지 않는다.** 후속 한 단계만 제안.

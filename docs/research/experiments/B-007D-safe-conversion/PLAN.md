# B-007D — 공식 SCAIL 체크포인트의 제한적 실제 로딩과 안전 변환

작성: 2026-10-22 · **PLANNED / NOT_RUN** · parent B-007C

## 목적과 근거
- B-007A: Spark GB10의 공식 SCAIL FA2/BF16 kernel tiny smoke 4/4 통과. 실제 대형 실행 NOT_RUN.
- B-007B: 필수 원본 약80GB 중 신규68.11GB 다운로드/해시 PASS; checkpoint의 NumPy pickle globals 세 개를 안전 검사에서 거부해 변환/추론 미실행.
- B-007C: 실제 data.pkl 비실행 graph 분석에서 3개 NumPy globals(및 codecs 관련 기호)는 np_rng_state root에서만 도달; 65,582,563,395-byte 원본 SHA d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f 보존. 소형 fixture에서 정확한 4개 scoped allowlist, restricted weights_only, mmap/FakeTensor, mapping/value/dtype/stride/offset/storage 검사 통과. **이것은 실제 대형 역직렬화의 안전 보증이 아니다.**

이번 실험은 해당 **고정 SHA의 공식 체크포인트 한 벌에 한해서**, 안전한 OS 격리로 actual metadata-only 제한 로딩이 가능한지 확인하고, 그 검증을 통과했을 때 메모리 한도가 있는 실제 tensor-only SAT→Wan 변환을 수행한다. 가중치 변환 성공과 모델 추론·영상 품질은 구분한다.

## 변경 금지 / 자원 허가
- A 트랙, 기존 VACE/ComfyUI, checkpoint 원본, B-007A/B/C 로그/결과, 시스템 환경은 변경하지 않음.
- 새로운 대용량 다운로드0, native imagegen/외부 생성 API0, **SCAIL 전체 모델 로딩0, diffusion 영상 추론0, optimizer update0**.
- 작업 최대 **3시간**. 기존 GPU-heavy job 중단·병렬 작업 금지. CPU 중심 처리. 저장 공간 안전 여유 300GB 이상/가용 통합메모리 fresh 확인. 시스템 드라이버/sudo/reboot/swap/clock/전역 torch 설치 금지.
- 별도 출력/격리된 subprocess/low-privilege container. 체크포인트 read-only mount, output 전용 writable, 네트워크 접근·host private files 접근 제한. **안전한 OS 격리가 구현·검증되지 않으면 allowlist를 실제 65GB에 실행하지 않고 BLOCKED.**
- 보안 경계는 safe_globals context 자체가 아니라 프로세스 격리/접근제어. credentials/token/env secret 접근 불가를 증명하고 범위 내 probe로 검증. sandbox 기능이 없는데 있다고 주장 금지.
- 최대 2회 bounded **실제** checkpoint load attempt: 최초 metadata-only FakeTensor, 성공했을 때 선택적 materialized CPU mmap 변환 1회. 실패도 장부에 포함. 실패 후 임의 allowlist 추가, weights_only=False, pickle.load, 다른 checkpoint 변경·부분 overwrite, 재시도 반복 금지.
- 동적 dtype은 **기존 4개** (NumPy legacy _reconstruct alias, ndarray, dtype, numpy.dtypes.UInt32DType)만 해당 고정 버전에서 검증. 현재 실제 Python/Torch/NumPy와 B-007C fixture/공식 SHA 일치 우선. 예상 밖 globals 또는 np_rng_state 구성 변경 시 정지.

## Gate0: 원본/코드/프로세스
- GitHub CHARTER, ROADMAP, HISTORY, RECORDING_PROTOCOL, B-007B/C RESULTS·CODE_AUDIT·실제 script를 읽고 HEAD, 사용 모델 revision, env·hash를 기록.
- 기존 다운받은 checkpoint의 길이, SHA, PyTorch ZIP data.pkl/storage 구조를 재확인. `weights_only=False` 금지.
- 실제 method: torch.serialization.safe_globals(정확히 4개, legacy alias 명시) 컨텍스트에서 weights_only=True, map_location=cpu, mmap=True, FakeTensorMode로 metadata-only 체크. context 이전의 FakeTensor lazy import 영향/ambient 등록, scope 전후 delta 확인. 같은 프로세스에서 다중 세션/thread 허용 목록 누적 금지.
- 수집하는 전체 딕셔너리의 tensor keys/metadata와 B-007C static graph의 일치 여부 확인, 예상 tensor storage ranges/offsets/stride 및 ZIP member 수치 검증. FakeTensor Python identity를 공유 storage의 물리적 입증으로 오인하지 않음.
- 실제 np_rng_state/객체 재구성의 부작용·추가형이 발생하면 오류를 남기고 즉시 STOP. 인스턴스 재구성을 실행하는 코드는 완전 무해함이 증명된 것이 아님. 파일/네트워크 격리를 먼저 실증해야 함.

## Gate1: 실제 metadata-only 제한 로딩 (첫 load)
- 거부 없이 metadata-only PASS이면 모델 tensor key set/shape/dtype/numel/storage mapping과 공식 convert.py의 예상 mapping을 대조. 987 module FloatStorage 등 B-007C static 자료와 비교하며 불일치는 별도 설명하고 STOP.
- CPU RSS, cgroup memory, OS MemAvailable, mmap file cache, elapsed, I/O 기록. 65GB 실제 tensor bytes를 읽지 않았다고 명시할 수 있는 근거를 검사. 모든 tensor data correctness는 metadata-only로 보증할 수 없음.
- 첫 로드가 실패하면 **이번 실험을 BLOCKED로 종료**하고 다음 요청 전 전체 변환 금지. 가드/실패 로그 보존.

## Gate2: memory-bounded SAT→Wan 변환 (두 번째 load, 조건부)
- Gate1 PASS 후에도 중단할 수 있다. 원본 SAT checkpoint를 통째로 torch.load/CPU mmap 한 뒤 공식 get_new_state_dict→safetensors.save_file을 바로 호출하기 전, 변환과 저장 중 **실제 peak 잠정 상한** 및 CPU/OS 가용자원 검토.
- 원본 checkpoint mmap과 동시에 발생할 수 있는 torch tensor materialization·serializer contiguous copy·QKV split, dictionary alias, pagecache, 출력 파일 쓰기를 메모리/디스크 계획에 반영. 낮은 메모리를 보증하지 못하면 Gate2 **NOT_RUN/BLOCKED**, 작은 fixture 성공을 이유로 강행하지 않는다.
- 변환 방법은 공식 get_new_mappings / get_new_state_dict semantics와 일치해야 함. 원본 dtype/value/shape/key map/QKV·KV split 보존. 안전한 shard/tensor 순차 출력이 실제 구현/검증됐을 때만 사용. 수동 pickle opcode 변형/일괄 bytes 교체 금지.
- 시작 시 cgroup memory.max는 실측 available/다른 작업 headroom을 감안해 예컨대 min(80GiB, MemAvailable−24GiB) 이하로 한정하고, 해당 값이 실행에 부적절하거나 24GiB 여유를 유지하기 어려우면 STOP. 숫자는 보안·OOM 무발생 보증이 아님. swap 증가/다른 서비스 영향/급격한 메모리 압박에서 자기 프로세스만 stop. 출력은 원자적 tmp→검증 완료 후 rename, 부분 파일을 완성 모델로 취급하지 않음.
- sharded safetensors 가능 시 실제 Wan 로더가 읽을 수 있는 방식인지 사전 확인. 호환되지 않는 분할 결과만 만들고 변환 PASS라고 주장 금지.
- 실제 결과 검증: 원본 불변 SHA, output keys/dtypes/shapes, tensor-by-tensor logical value hash와 공식 remapping parity, layer-count/QKV split ordering, 중복/누락 keys, output safetensors parse. 작은 fixture parity와 실제 tensor parity를 분리. 보존 가능한 실측 peak와 벽시계 시간 보고.
- 성공해도 **전체 SCAIL 모델 적재·실제 영상 17프레임 추론은 다음 별도 승인 단계**.

## 학습 기록/수식
한국어 `docs/research/lessons/B-007D-real-checkpoint-loading.md`: pickle object graph/실제 storage; FakeTensor와 metadata-only, mmap virtual vs resident, cgroup file cache; safe_globals의 실제 보안·격리; QKV chunk mapping과 storage alias vs safetensors; 통합 메모리 peak 추정과 측정 차이; OS page cache vs GPU allocator. 직관→실제 코드/실험→수학/텐서 shape→관측·한계→이해 질문 및 별도 해설.

## 종료·연구 기록
- 새 PLAN 실행 전 연구 브랜치에 실제 고정 실행 script/config/가드 해시와 사전 중지 기준 commit/push. 기록 전 실제 checkpoint restricted load 시작 금지.
- 종료 후 `docs/research/experiments/B-007D-safe-conversion/RESULTS.md`, 재현, 실제 보안/메모리 증거, lessons, HISTORY, ROADMAP commit/push, 원격 HEAD 확인. 개인 path/IP·비밀키·raw checkpoint/generator media·대형 가중치·전체 raw pickle 로그를 공개 repo에 올리지 않음.
- 비공개 ZIP 하나에 결과 요약, runner/config·hash, manifest, synthetic+실제 검사 증거 및 문제가 있으면 스택트레이스 일부(민감 경로 제거)를 보존; 원본 65GB 및 전체 변환 safetensors는 포함하지 않는다.
- 종료 때 자기 프로세스 상태 확인. 결과는 AUDIT_PASS/PARTIAL_CONVERSION_PASS/BLOCKED/CONVERSION_PASS처럼 **실제로 입증된 단계만** 표시. 다음 한 실험은 성공할 경우 모델 load + 공식 17f + Lab 17f 제한적 추론 하나이며 자동 시작하지 않는다.

# B-007D — metadata 로딩과 실제 가중치 변환의 차이

[계획](../experiments/B-007D-safe-conversion/PLAN.md) · [실제 코드 감사](../experiments/B-007D-safe-conversion/CODE_AUDIT.md). 코드 설명과 실제 metadata PASS를 함께 기록한다. 변환은 실제 값 검증까지 완료됐으며 아래에 결과와 한계를 기록한다.

## 1. 직관: 주소를 읽는 것과 모든 값을 읽는 것

metadata 단계는 tensor의 key, dtype, shape, stride, storage offset과 파일 내 저장 위치를 확인한다. 실제 값이 올바른지는 아직 모른다. 변환 단계는 모든 논리적 tensor 값을 읽어 새로운 이름·저장 형식으로 출력한다. 둘은 같은 checkpoint를 다뤄도 작업량과 증거 수준이 다르다.

FakeTensorMode의 tensor storage metadata가 일치해도 Python storage 객체가 같은 identity를 가질 필요는 없다. B-007C의 작은 fixture에서는 FakeTensor storage alias identity가 NOT_PRESERVED였지만 ZIP offset 대응은 확인됐다. 이를 실제 physical storage sharing의 증명으로 바꾸지 않는다.

### ZIP member 위치와 tensor view 위치

`data.pkl`은 객체 graph와 tensor 설명을 담고, `data/<storage_key>` member는 storage bytes를 담는다. B-007C 비실행 감사의 source contract는 module FloatStorage 987개와 torch/cuda RNG ByteStorage 2개, 전체 storage 참조 989개다. 이 숫자는 선행 정적 증거이며 이번 metadata load의 결과를 미리 대신하지 않는다.

압축하지 않은 STORED member에서 storage payload 시작의 절대 파일 byte offset을 `p`, dtype의 원소 크기를 `b` bytes, tensor storage offset을 `o` elements, stride를 `s_k` elements라 하면 index `i`의 위치는 다음과 같다.

`file_byte_position(i) = p + b × (o + Σ_k i_k s_k)`

여기서 `p`는 ZIP local header 시작이나 data.pkl 내 opcode 위치가 아니다. ZIP member의 실제 payload 시작 위치다. `_checkpoint_offset`과 ZIP parser가 얻은 payload offset을 대조할 때 이 좌표계를 맞춰야 한다. header 이름·extra field 길이·정렬 padding이 있으므로 단순히 모든 member가 같은 고정 header 크기를 가진다고 가정하지 않는다.

FakeTensor metadata로 shape·dtype·stride·offset과 범위를 검사할 수 있지만 그 위치의 값이 올바른지는 직접 읽지 않았다. 동일 storage를 가리키는 두 view는 위 식으로 같은 payload 범위를 참조할 수 있으며, FakeTensor의 Python 객체 identity가 같아야만 이를 표현할 수 있는 것은 아니다. 반대로 offset 일치만으로 전체 tensor 값의 hash 일치까지 입증되지 않는다.

## 2. QKV 분할 수식과 shape

입력 차원 D_in, 출력 차원 D_out인 packed weight를 `W ∈ R^(3D_out × D_in)`라 하자. 공식 dim=0 분할은 `Wq=W[0:D_out,:]`, `Wk=W[D_out:2D_out,:]`, `Wv=W[2D_out:3D_out,:]`다. bias도 같은 행 순서를 따른다. packed KV는 2D_out을 두 부분으로 나눈다. 실제 shape는 metadata 결과로 검증하며 수식의 균등 분할 가정을 무조건 적용하지 않는다.

연속적인 행 분할은 원본 storage를 공유하는 view가 될 수 있다. 요소 크기 b라면 QKV weight 전체의 논리 bytes는 `3 × D_out × D_in × b`다. 분할은 값을 새로 학습하거나 BF16으로 바꾸는 연산이 아니다. safetensors는 각 결과를 연속 bytes로 저장하므로 원본 공유 storage 구조 대신 tensor별 값 보존을 검증한다. 공식 구현 위치는 코드 감사의 고정 링크에 연결했다.

## 3. mmap의 가상 주소와 실제 resident memory

mmap은 파일 주소 공간을 매핑한다. 약65GB를 매핑했다고 바로65GB RSS가 생기는 것은 아니지만, 모든 값을 hashing·writing하면서 읽으면 source page가 resident가 된다. 출력은 dirty file cache를 만들고 이후 디스크로 writeback된다. memoryview와 8MiB chunk는 거대한 사용자 buffer를 피하지만 OS page cache까지 없애지 않는다.

개념적으로 관측 대상은 anonymous/runtime memory, source file pages, output file cache, kernel overhead다. 이는 정확한 상호 배타적 회계식이 아니다. RSS와 cgroup memory.current, memory.stat의 file/anon, 시스템 MemAvailable을 함께 봐야 한다. 공유 페이지의 귀속이나 reclaim 때문에 단순히 모두 더한 값도 맞지 않을 수 있다.

`memory.max`는 cgroup의 hard 제한이고 도달 시 reclaim·OOM이 가능하다. `memory.high`는 pressure와 throttling 경계다. 실행 guard는 실패를 제한할 뿐 성공을 보장하지 않는다. CPU와 GPU가 공유하는 Spark memory를 두 번 계산하지 않는다. 이 CPU 변환에서 CUDA allocator가 낮다는 이유로 통합 메모리 여유를 판정하지 않는다.

## 4. 안전성·동등성·자원은 각각 검증한다

정확한 source SHA와 NumPy 네 항목 scoped allowlist는 신뢰 범위를 좁힌다. 하지만 허용 함수는 실제 실행될 수 있다. 제한된 OS 환경과 파일 read-only mount, network/credentials 접근 차단이 별도로 필요하다. FakeTensor는 보안 sandbox가 아니다.

동등성은 key 누락·중복, dtype, shape, Q/K/V 순서, 각 tensor의 논리적 byte hash를 확인한다. safetensors 구조 parser만 통과하면 내용 오류까지 배제되는 것은 아니다. 작은 fixture parity, 실제 전체 tensor parity, 모델 forward 성공은 서로 다른 결과다.

이번 두 번 실제 load 상한에서는 metadata load 한 번, 조건부 materialized mmap load 한 번을 구분한다. 검증을 위해 몰래 추가 source load를 실행하지 않는다. 같은 살아 있는 source를 다시 읽어 검증했는지, 첫 쓰기에서 얻은 hash와 output을 대조했는지 명시한다. 후자는 독립 source reload 검증이 아니다.

## 5. 실제 관측과 한계

B-007C의 실제 원본 크기·storage 구조와 작은 fixture 결과는 선행 증거다. B-007D의 sandbox 및 metadata 결과는 아래 실제 관측에 기록했다. 실제 전체 값 parity와 시간은 아래에 기록하며 자원 peak는 별도로 구분한다. 이는 대형 model load·영상 생성·학습을 의미하지 않는다.

[이해 질문](../experiments/B-007D-safe-conversion/QUESTIONS_KO.md) · [해설](../experiments/B-007D-safe-conversion/ANSWERS_KO.md)

실제 OS probe는 **PASS**로 보고됐다. user namespace 기반 bwrap/unshare의 EPERM 실패는 보존하며, 대체 경로는 기존 non-root Docker container다. [실제 command](../experiments/B-007D-safe-conversion/code/sandbox_command.py)는 runc, network=none, read-only root, UID/GID 1000, cap-drop=ALL, no-new-privileges, pids limit 64, CPU 2개와 명시적 mount를 사용한다. 보안 판정은 container 명칭이 아니라 실제 접근 차단 probe에 근거한다.

후속 단계에 설정한 메모리 cap은 metadata **8GiB**, 변환 **32GiB**다. 앞서 PLAN의 예시 상한 80GiB를 실제 배정치로 읽지 않는다. `memory-swap=memory`로 추가 swap allowance를 두지 않는다. 이 cap은 peak 실측이나 OOM 무발생 보증이 아니다. 소형 코드 fixture는 12개 PASS로 보고됐다. ambient 허용 집합 재검증과 outer cleanup 검사는 PASS이며, 사전 고정 코드 `5e134fa`로 12:53:35 UTC에 첫 실제 metadata attempt를 시작했다. 이후 metadata PASS를 확인했으며 세부 수치는 아래에 기록한다. 변환의 최종 결과는 아래 실제 관측에 기록한다.

## B-007D 실제 metadata 결과

첫 metadata attempt는 **PASS**다. source tensor 987개에서 공식 mapping으로 1,307개 tensor, 논리 payload 65,582,177,536 bytes를 확인했다. static contract의 key·dtype·shape·stride·storage offset 및 실제 ZIP payload offset을 대조했다. scoped 종료 후 ambient 83개로 복구됐다. 실제 값 parity는 이 단계에서 **NOT_VERIFIED**다.

전체 metadata stage는 45.2086초였고, full-file SHA 검증이 44.3708초를 차지했다. SHA 단계는 65GB 파일 전체를 논리적으로 읽었으며 `/proc` read_bytes 증가는 10,668,929,024 bytes였다. page cache 때문에 논리적 읽기량과 backing-device I/O는 다를 수 있다. 이후 restricted load 자체는 0.167183초, rchar 증가 4,330,136 bytes, read_bytes 증가 2,928,640 bytes였다. 따라서 전체 stage를 payload I/O가 없는 metadata-only 작업이라고 표현하지 않는다. 제한 로딩 단계와 full-file hash 단계를 분리한다.

프로세스 max RSS는 573,196 KiB였다. 8GiB cgroup cap과 그에 가까운 file-cache charge는 이 RSS와 다른 측정 범위다. SHA scan으로 charge된 cache를 Python heap이나 tensor가 모두 복제된 증거로 해석하지 않는다. 반대로 낮은 RSS만으로 시스템 메모리 영향이 작다고 결론 내리지 않는다.

두 번째이자 마지막 허용 load인 변환은 12:55:50 UTC 시작됐고, 이후 검증 및 종료까지 PASS로 확인됐다. metadata PASS를 값 parity·변환 완료·모델 forward PASS로 확장하지 않는다.

metadata cgroup의 최고 current 표본은 8,589,799,424 bytes, peak는 8,589,934,592 bytes(설정한 8GiB cap)였다. 해당 표본의 anon은 305,696,768 bytes, file은 8,281,137,152 bytes였다. memory.events의 max=941, oom=0이므로 cap 접근과 reclaim 압력을 OOM 발생으로 쓰지 않는다. 이 peak는 제한 아래에서 관측한 값이며, 제한이 없을 때의 자연스러운 필요 메모리 peak를 측정한 것이 아니다. 비동기 표본·회계 범위 때문에 stat 합계를 RSS와 정확히 같게 맞추지 않는다.

### 실제 첫 layer QKV 예제

실제 metadata에서 layer 0의 packed QKV weight는 FP32 `[15360,5120]`, stride `[5120,1]`, storage bytes 314,572,800, ZIP payload offset 8,399,439,808, storage key 331이었다. 공식 분할 결과 `blocks.0.self_attn.{q,k,v}.weight`는 각각 `[5120,5120]`이며 storage offset은 element 단위로 0 / 26,214,400 / 52,428,800이다.

FP32는 b=4이므로 각 tensor는 104,857,600 bytes(100MiB)다. 첫 원소의 파일 위치는 Q=8,399,439,808, K=8,504,297,408, V=8,609,155,008 bytes다. 세 부분의 합은 원본 314,572,800 bytes와 같다. 이것은 실제 metadata의 분할 순서·범위 증거이며 실제 값 hash parity는 아래 완료된 변환 검증의 별도 증거다.

## 최종 실제 변환 결과

**CONVERSION_PASS_NOT_MODEL_FORWARD**. 실제 load attempt는 metadata 1회와 materialized CPU mmap 변환 1회, 총 2회다. mapped tensor 1,307개 전체에 대해 writer hash와 동일 source mmap에서 얻은 original mapped view의 hash, output에서 다시 읽은 hash가 일치했다. 이는 실제 전체 값 parity이며 별도 source 재로딩 검증은 아니다. 원본 SHA는 전후 불변이다.

논리 tensor payload는 65,582,177,536 bytes, 최종 safetensors 파일은 65,582,313,560 bytes다. 최종 SHA256은 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`이다. 검증을 마친 staging 파일만 최종 이름으로 발행했다. 종료 코드 0, 남은 container PID 0, OOMKilled=false로 확인됐다.

전체 guard 시간은 456.759초다. receipt의 `seconds=369.068`은 최종 output SHA 계산 **이전**에 평가된 값이므로 전체 작업 시간이라고 부르지 않는다. 실제 model 적재·attention/DiT forward·diffusion·영상 품질·학습은 모두 **NOT_RUN**이다. 순차 변환의 성공과 자원 관측을 실제 모델 추론의 메모리 적합성으로 확대하지 않는다.

### 실제 변환 메모리의 서로 다른 측정

cgroup peak는 34,359,738,368 bytes로 설정한 32GiB cap에 도달했다. 그러나 표본에서 읽은 프로세스 VmHWM은 **55,564,172 KiB(약53GiB)**였다. VmHWM은 그 시점까지의 누적 RSS 최고값이며 cgroup charged-memory와 동일한 회계가 아니다. 따라서 **32GiB를 전체 프로세스 RSS 상한으로 보고하면 안 된다**. mmap/shared file page와 cgroup charge 귀속 차이가 가능한 설명이지만, 이 실행에서 각 page의 소유·과거 charge까지 추적해 원인을 입증한 것은 아니다.

관측된 시스템 MemAvailable 최저치는 89,057,169,408 bytes(약82.94GiB)였다. 마지막 memory.events는 max=31,772, oom=0이었다. max는 cap 접근/회수 압력의 기록이지 OOM 횟수가 아니다. 이 수치들은 guard가 적용된 이번 실행의 관측이며, 무제한 peak나 향후 model forward의 필요 메모리를 예측하지 않는다.

두 번째 materialized mmap load 자체는 약0.090초, rchar 증가 4,330,136 bytes, read_bytes 증가 2,453,504 bytes였다. 선행 hash 단계는 62.763초였다. mmap 객체 구성이 빠른 것과 이후 모든 tensor page를 읽어 변환·검증하는 비용이 작은 것은 다르다.

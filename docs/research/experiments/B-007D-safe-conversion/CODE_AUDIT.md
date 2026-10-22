# B-007D 코드 감사 — tensor mapping과 저장 경계

상태: 소스 검토와 OS 사전 검증 완료, 실제 metadata PASS 및 CONVERSION_PASS_NOT_MODEL_FORWARD. 이 문서는 실행 담당자의 실제 격리 검증을 대신하지 않는다. [PLAN](PLAN.md), [이전 안전성 감사](../B-007C-checkpoint-audit/CODE_AUDIT.md).

## 공식 mapping

고정 SCAIL commit `78fe19576bb06be96c2375e088574a262a300edb`의 [convert.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L31)를 읽었다. source SHA256은 `0519f688643b0a2c3f13660f196e34280704ddb3e2575aa226e2d2f8f2b4397f`다.

- self-attention의 packed QKV는 [110행](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L110)에서 dim=0을 Q,K,V 순으로 3분할한다.
- text cross-attention KV는 [129행](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L129), image KV는 [73행](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/convert.py#L73)에서 K,V 순으로 분할한다. dtype cast나 learned 변환이 아니다.
- `get_new_state_dict`는 key 재배치와 view 참조를 모은다. 이를 checkpoint 전체 clone 두 벌이라고 단정할 수 없다. 반대로 원본 loader·serializer까지 무복사라는 보증도 아니다.

## 기존 순차 writer와 검증기

[B-007B writer](../B-007B-scail-baseline/code/converter_stream.py)는 CPU contiguous strided tensor만 허용한다. uint8 view의 memoryview를 최대 8MiB씩 쓰며 원본 dtype을 유지한다. dtype/shape/data_offsets JSON과 8-byte little-endian header length를 쓴다. 부분 파일은 배타적으로 생성하고 fsync 뒤 no-overwrite hardlink로 이름을 발행한다. [safetensors 공식 형식](https://github.com/safetensors/safetensors#format).

8MiB는 쓰기 chunk 상한이며 프로세스 RSS나 cgroup 메모리 상한이 아니다. source mmap resident page, 출력 dirty page cache, Python과 library metadata가 별도로 존재한다. 원본이 noncontiguous이면 강제 contiguous copy로 통과시키지 않고 거부한다.

[B-007B verifier](../B-007B-scail-baseline/code/converter_verify.py)는 safetensors parser의 key/dtype/shape 확인과 source/output per-tensor byte hash 비교를 수행한다. 다만 그대로 호출하면 metadata 및 materialized `torch.load`를 **추가로 두 번** 실행한다. B-007D의 전체 두 번 상한과 맞지 않으므로 실제 B-007D 검증은 두 번째 load의 살아 있는 source tensor를 재사용하거나 그때 기록한 source hash와 output을 대조해야 한다. 어느 독립성을 확보했는지 결과에 기록한다. 별도 source reload 검증으로 과장하지 않는다.

writer의 output 이름 발행 시점은 독립 검증보다 앞이다. B-007D에서는 후보 파일 이름과 검증 완료 파일을 구분하고, 최종 PASS 이전에 완성 모델로 취급하지 않아야 한다. 이 항목들은 실행 담당자에게 전달했으며 이 감사에서 기존 writer/API는 변경하지 않았다.

## 보안과 메모리의 서로 다른 gate

[고정 PyTorch restricted unpickler](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/torch/_weights_only_unpickler.py#L307)는 allowlisted REDUCE/BUILD를 실행할 수 있다. 정확한 네 NumPy 항목과 weights_only를 쓰더라도 OS 파일·네트워크·credentials 격리를 먼저 검증해야 한다. FakeTensor와 CPU mmap은 이 보안 경계를 제공하지 않는다. [공식 serialization 설명](https://docs.pytorch.org/docs/2.14/notes/serialization.html).

[Linux cgroup v2 문서](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory)는 anonymous와 file cache를 구분한다. memory.current/peak는 RSS와 다른 지표이고, memory.max 도달 시 reclaim이나 cgroup OOM이 가능하다. memory.high는 hard allocation 상한이 아니다. 입력/출력 page cache를 전부 GPU allocator 수치로 볼 수 없다. Spark의 통합 메모리를 CPU와 GPU의 독립 용량으로 합산하지 않는다.

원본 크기 65,582,563,395 bytes 및 B-007C storage 합계 65,582,182,608 bytes는 실제 파일의 구조 측정이다. 이는 변환 peak가 아니다. B-007D의 max=min(80GiB, fresh MemAvailable−24GiB) 같은 guard는 실행 정책이며 성공 보증이 아니다. 실제 peak·입출력·시간과 원본 불변·전체 tensor parity가 모이기 전 변환 PASS는 미확인이다.

실제 OS probe는 **PASS**로 보고됐다. user namespace 기반 bwrap/unshare의 EPERM 실패는 보존하며, 대체 경로는 기존 non-root Docker container다. [실제 command](../B-007D-safe-conversion/code/sandbox_command.py)는 runc, network=none, read-only root, UID/GID 1000, cap-drop=ALL, no-new-privileges, pids limit 64, CPU 2개와 명시적 mount를 사용한다. 보안 판정은 container 명칭이 아니라 실제 접근 차단 probe에 근거한다.

후속 단계에 설정한 메모리 cap은 metadata **8GiB**, 변환 **32GiB**다. 앞서 PLAN의 예시 상한 80GiB를 실제 배정치로 읽지 않는다. `memory-swap=memory`로 추가 swap allowance를 두지 않는다. 이 cap은 peak 실측이나 OOM 무발생 보증이 아니다. 소형 코드 fixture는 12개 PASS로 보고됐다. ambient 허용 집합 재검증과 outer cleanup 검사는 PASS이며, 사전 고정 코드 `5e134fa`로 12:53:35 UTC에 첫 실제 metadata attempt를 시작했다. 이후 metadata PASS를 확인했으며 세부 수치는 아래에 기록한다. 변환의 최종 결과는 아래 실제 관측에 기록한다.

## B-007D 실제 metadata 결과

첫 metadata attempt는 **PASS**다. source tensor 987개에서 공식 mapping으로 1,307개 tensor, 논리 payload 65,582,177,536 bytes를 확인했다. static contract의 key·dtype·shape·stride·storage offset 및 실제 ZIP payload offset을 대조했다. scoped 종료 후 ambient 83개로 복구됐다. 실제 값 parity는 이 단계에서 **NOT_VERIFIED**다.

전체 metadata stage는 45.2086초였고, full-file SHA 검증이 44.3708초를 차지했다. SHA 단계는 65GB 파일 전체를 논리적으로 읽었으며 `/proc` read_bytes 증가는 10,668,929,024 bytes였다. page cache 때문에 논리적 읽기량과 backing-device I/O는 다를 수 있다. 이후 restricted load 자체는 0.167183초, rchar 증가 4,330,136 bytes, read_bytes 증가 2,928,640 bytes였다. 따라서 전체 stage를 payload I/O가 없는 metadata-only 작업이라고 표현하지 않는다. 제한 로딩 단계와 full-file hash 단계를 분리한다.

프로세스 max RSS는 573,196 KiB였다. 8GiB cgroup cap과 그에 가까운 file-cache charge는 이 RSS와 다른 측정 범위다. SHA scan으로 charge된 cache를 Python heap이나 tensor가 모두 복제된 증거로 해석하지 않는다. 반대로 낮은 RSS만으로 시스템 메모리 영향이 작다고 결론 내리지 않는다.

두 번째이자 마지막 허용 load인 변환은 12:55:50 UTC 시작됐고, 이후 검증 및 종료까지 PASS로 확인됐다. metadata PASS를 값 parity·변환 완료·모델 forward PASS로 확장하지 않는다.

metadata cgroup의 최고 current 표본은 8,589,799,424 bytes, peak는 8,589,934,592 bytes(설정한 8GiB cap)였다. 해당 표본의 anon은 305,696,768 bytes, file은 8,281,137,152 bytes였다. memory.events의 max=941, oom=0이므로 cap 접근과 reclaim 압력을 OOM 발생으로 쓰지 않는다. 이 peak는 제한 아래에서 관측한 값이며, 제한이 없을 때의 자연스러운 필요 메모리 peak를 측정한 것이 아니다. 비동기 표본·회계 범위 때문에 stat 합계를 RSS와 정확히 같게 맞추지 않는다.

## 최종 실제 변환 결과

**CONVERSION_PASS_NOT_MODEL_FORWARD**. 실제 load attempt는 metadata 1회와 materialized CPU mmap 변환 1회, 총 2회다. mapped tensor 1,307개 전체에 대해 writer hash와 동일 source mmap에서 얻은 original mapped view의 hash, output에서 다시 읽은 hash가 일치했다. 이는 실제 전체 값 parity이며 별도 source 재로딩 검증은 아니다. 원본 SHA는 전후 불변이다.

논리 tensor payload는 65,582,177,536 bytes, 최종 safetensors 파일은 65,582,313,560 bytes다. 최종 SHA256은 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`이다. 검증을 마친 staging 파일만 최종 이름으로 발행했다. 종료 코드 0, 남은 container PID 0, OOMKilled=false로 확인됐다.

전체 guard 시간은 456.759초다. receipt의 `seconds=369.068`은 최종 output SHA 계산 **이전**에 평가된 값이므로 전체 작업 시간이라고 부르지 않는다. 실제 model 적재·attention/DiT forward·diffusion·영상 품질·학습은 모두 **NOT_RUN**이다. 순차 변환의 성공과 자원 관측을 실제 모델 추론의 메모리 적합성으로 확대하지 않는다.

### 실제 변환 메모리의 서로 다른 측정

cgroup peak는 34,359,738,368 bytes로 설정한 32GiB cap에 도달했다. 그러나 표본에서 읽은 프로세스 VmHWM은 **55,564,172 KiB(약53GiB)**였다. VmHWM은 그 시점까지의 누적 RSS 최고값이며 cgroup charged-memory와 동일한 회계가 아니다. 따라서 **32GiB를 전체 프로세스 RSS 상한으로 보고하면 안 된다**. mmap/shared file page와 cgroup charge 귀속 차이가 가능한 설명이지만, 이 실행에서 각 page의 소유·과거 charge까지 추적해 원인을 입증한 것은 아니다.

관측된 시스템 MemAvailable 최저치는 89,057,169,408 bytes(약82.94GiB)였다. 마지막 memory.events는 max=31,772, oom=0이었다. max는 cap 접근/회수 압력의 기록이지 OOM 횟수가 아니다. 이 수치들은 guard가 적용된 이번 실행의 관측이며, 무제한 peak나 향후 model forward의 필요 메모리를 예측하지 않는다.

두 번째 materialized mmap load 자체는 약0.090초, rchar 증가 4,330,136 bytes, read_bytes 증가 2,453,504 bytes였다. 선행 hash 단계는 62.763초였다. mmap 객체 구성이 빠른 것과 이후 모든 tensor page를 읽어 변환·검증하는 비용이 작은 것은 다르다.

# B-030 독립 연결 검토

검토 주체: 실행 담당과 별도의 읽기 전용 코드/장부 검토 agent. 영상 품질·사람 연속 시청을 대신하지 않는다. 기존 B028/B029 실패와 CONTROL 판정은 변경하지 않는다.

## 생성 전 확인

2026-10-26, 실제 Spark의 B027 부모와 B030 파생 safetensors를 CPU에서 읽었다. PyTorch/GPU 연산 없이 safetensors header의 dtype/shape/data_offsets와 해당 storage bytes의 SHA256을 독립 계산했다.

| 셀 | 실제 값이 바뀐 leaf | 나머지 실제 값·shape·dtype | container/device 구조 | donor CLIP 값 |
|---|---|---|---|---|
| human Y12 | t2,t8 | 14개 동일 | 동일 | R2와 동일 |
| human Y21 | t2,t8 | 14개 동일 | 동일 | R1과 동일 |
| vehicle Y12 | t2,t8 | 14개 동일 | 동일 | R2와 동일 |
| vehicle Y21 | t2,t8 | 14개 동일 | 동일 | R1과 동일 |

두 CLIP은 `[1,257,1280]`, FP16이다. 실제 storage 해시는 파생 metadata의 tensor 해시와도 일치했다. 보존14개에는 initial noise, positive/negative text, reference VAE/mask, driving VAE/mask, generator state, timesteps, sigmas가 포함된다. seed 문자열만 비교한 결과가 아니다. 원래 metadata의 tree를 유지하므로 tensor의 원래 CUDA/CPU 복원 위치와 list/dict/scalar 구조도 보존된다.

`crossover.py`는 부모를 읽고 별도 cache에 clone을 저장하며 부모 파일 해시와 CPU RNG 불변, 저장 후 값 동일성을 확인한다. `contracts.py`는 기존 B027 producer 검사를 유지하고 두 부모 receipt/조건/config를 검증한 뒤 파생의 정확한 2변경/14보존을 검사한다. 실제 복원은 기존 `load_tree`가 저장 파일과 각 tensor hash·shape·dtype를 다시 검증한다.

## 실행 코드의 변경 범위

B027 `phase_sample.py` 대비 sampling 수학 변경은 없다. 차이는 B029 gate OFF 및 공식 cross-attention 함수 module 확인, 첫 두 CFG의 교차 계보 기록, 최종 latent의 B030 consumer 표기다. `staged_loader.py`, sampler 추출 경로와 official upstream은 기존 기준선을 사용한다. 단순 `__module__` 이름 검사만으로 패치 부재를 증명하지 않으며 pinned upstream SHA·실제 import 경로·코드 명세와 함께 확인한다.

기존 sampler는 CPU scheduler 계산 위치·UniPC40/shift3/CFG5·80forward를 유지한다. 실제 양 CFG에 replacement=True와 동일 시각 조건 경로를 전달하고 additional_ref/history는 None이다. 실제 block kwargs로 공식 replacement 위치 규약을 관측하되 변경하지 않는다. Q/V가 일반 Linear이고 LoRA parameter가 없음을 검사한다. 추가 attention dump/관측 forward는 없다.

시작72GiB·실행24GiB headroom·swap0·기존 서비스 queue/PID 보호와 deadline을 유지한다. stage attempt와 watchdog record는 exclusive create이므로 같은 stage의 조용한 재실행을 막는다. 각 task의 고정 Y12/Y21을 PROBE→S→D로 순차 실행하고 앞 worker의 종료 및 결과를 확인한다. 새 encoder 경로는 실행 목록에 없다.

## 수용 범위

현재 이 문서의 판정은 **CPU 조건 계보 PASS / 코드 범위 검토 PASS**다. 실제 GPU의 네 셀 실행·40step80forward·final latent/decode 계보는 종료 장부를 확인한 뒤 아래에 별도로 기록한다. CPU fixture나 본 검토로 영상 품질·시간 품질·full14B 수치 동등성을 주장하지 않는다.

사전 고정 후 19개 공개 runner와 실제 로컬 runner의 bytes 동일성을 확인했다. `run_all.sh`는 human Y12→Y21, vehicle Y12→Y21의 고정 순서이며 각 PROBE/S/D를 직렬 호출하고 실제 완료 receipt와 MainPID=0을 확인한다. CPU 로그는6개 검사 통과(0.58초)이며 이는 대형 모델의 수치 동등성 검사가 아니다. 코드·4개 cache·부모 계보·deadline은 [PREREGISTRATION](PREREGISTRATION.json)에 고정됐다.

## 실행 종료 후 독립 검증

2026-10-26 종료 후 Spark의 실제 파일을 다시 읽었다. 다음은 CPU/stdlib·ffprobe 읽기 전용 검사이며 추가 모델 호출, Torch import, GPU 연산은 하지 않았다. 위의 실행 전 `GPU 장부 미확인` 상태는 당시 기록으로 보존하고, 아래 종료 증거를 추가한다.

| 셀 | 실제 steps/forward | S 프로세스 초 | D 프로세스 초 | 관측 최소 MemAvailable GiB | 관측 cgroup peak GiB | final/MP4 |
|---|---:|---:|---:|---:|---:|---|
| human Y12 | 40/80 | 1017.669 | 16.215 | 53.316 | 62.029 | PASS |
| human Y21 | 40/80 | 998.665 | 15.240 | 52.911 | 62.585 | PASS |
| vehicle Y12 | 40/80 | 1001.058 | 15.226 | 52.971 | 59.612 | PASS |
| vehicle Y21 | 40/80 | 997.819 | 15.229 | 53.382 | 62.007 | PASS |

시간은 supervisor의 프로세스 시작→종료 구간이며 sampler kernel만의 시간이 아니다. 최소 가용 메모리와 cgroup peak는 PROBE/S/D의 기록 표본에서 얻었으며 서로 다른 회계를 합산하지 않았다.

- 부모 receipt가 고정한 기존 16개 파일을 다시 SHA256 계산해 모두 불변임을 확인했다. 파생 cache·metadata·initial noise 파일도 receipt와 일치했다. 최초 CPU storage 검사의 2변경/14보존 계보가 유지된다.
- 네 최종 latent의 실제 safetensors bytes와 metadata SHA256이 일치했다. F32 `[16,5,64,112]` storage를 직접 읽어 전 원소 finite, tensor hash 일치, 초기 noise와 다른 값임을 확인했다. provenance의 해당 조건 cache hash, adapter OFF, 실제 counter 40step/80forward를 확인했다.
- 각 첫 실제 forward의 양 CFG 기록에서 reference/CLIP hash가 파생 cache와 일치하고 검증된 복원 cache와 같은 객체로 연결됐음을 확인했다. 추가 관측 forward는 0이다.
- D 코드가 검증된 final latent를 읽어 공식 VAE로 decode하는 경로와 실제 종료 장부를 확인했다. runtime raw finite 및 `[3,17,512,896]` 검사가 PASS다. 이번 독립 감사는 raw pickle을 다시 역직렬화하지 않았으며 raw 파일 hash를 계산했다.
- 네 MP4를 별도 ffprobe `count_frames`로 다시 검사했다. 모두 896×512, 실제 읽힌 17프레임, 24/1fps다. 원본 fps 확인을 대신하지 않으며 `source_fps=null`, `timebase_assumed=true`는 유지된다.
- stage attempt 파일은 PROBE/S/D 각 4개(합12), sampler-attempt는 4개다. 모든 stage는 `COMPLETED`, `service_exit`, returncode0, `MainPID=0`, inactive다. 12개 프로세스의 시작/종료 구간은 순차이며 겹치지 않는다.
- 모든 자원 기록 표본의 swap은 0, MemAvailable은 24GiB 이상, cgroup OOM/oom_kill은 0이었다. `memory.high`는 human Y12/Y21과 vehicle Y21에서 발생했다(각 stage 최대 누적값 6580/3217/340). 이는 high 제한의 reclaim/throttling 신호이며 `OOM 없음`을 `압박 없음`으로 바꾸어 해석하지 않는다.
- 종료 시 pipeline/watchdog 두 systemd unit 모두 inactive, MainPID0을 직접 확인했고 B030 자체 프로세스는 남아 있지 않았다.

최종 latent 파일 SHA256:

| 셀 | SHA256 |
|---|---|
| human Y12 | `96ac85f74c5187d234ededfb78ba28883c02536192e79b35658569f7e3d06499` |
| human Y21 | `8ce7459f1e76095a7be558ba363b8948e88c394bfa461f4d94206b99d976b31d` |
| vehicle Y12 | `31816becc0ce3ff366450cae81131711ec2480016bf0d5925da5e514040b9933` |
| vehicle Y21 | `08837e5ee2fefd3ceab95c21e493c3227fc39664d30f406a3ddcb8c9f8802cae` |

최종 **연결/예산/출력 기술 검증 PASS**. 실제 원시 영상의 외형·동작·장면 성공은 별도 MATRIX_REVIEW/RESULTS의 관측 판정이다. 이 감사는 영상 품질 개선이나 독립 사람 평가가 아니며 실제 연속 시청을 수행하지 않았으므로 temporal=UNVERIFIED다.

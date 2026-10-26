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

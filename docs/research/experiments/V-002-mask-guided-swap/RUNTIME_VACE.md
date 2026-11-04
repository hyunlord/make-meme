# V-002 VACE 실행 계약

V-002는 C-009/C-012의 검증된 DiffSynth VACE 진입 경로를 사용한다. 14B에는 C-005에서 작성한 native disk/offload 구성을 재사용한다. 이 파일은 실행 전 소스 확인이며 생성 성공 증거가 아니다.

## 실제 조건 전달

`vace_entry.py`는 `condition_dir/000.png`부터 73장(14B 축소 시49장), 같은 수의 RGB mask, 이미832×480 흰 canvas에 배치된 Lab/IG 참조 PNG2장을 받는다. PNG를 읽고 RGB mode·832×480·마스크0/255와 세 채널 exact를 검사한다. 정수 fill이 빨강으로 바뀌었던 C-008 오류를 허용하지 않는다. M3의 frame0 mask만 전체0이고 나머지는 부분 생성 영역이어야 한다.

기존 DiffSynth `WanVideoUnit_VACE.process`는 입력을 [-1,1]로 정규화하고 `inactive=RGB*(1-mask)`, `reactive=RGB*mask`를 각각 VAE encode한다. 따라서 M2의 depth는 reactive 조건에 실제로 들어가며, 생성 영역이라는 이유로 버리지 않는다. 두 참조는 각각 별도로 encode되어 시간축 앞에2칸 추가되고 decode 전에 제거된다.73프레임의 첫 model_fn context 기대 shape는 `[1,96,21,60,104]`이고49프레임은 `[1,96,15,60,104]`이다.

공식 VACE 역시 mask를64채널로 재배열한 뒤 `nearest-exact`로73→19 압축한다. 첫 표본은 frame1이므로 M3 frame0의 mask0이 압축 mask의 첫 칸에 그대로 남는다고 주장하지 않는다. 앵커 RGB는 inactive VAE 입력에 남지만 별도의 output frame0 덮어쓰기나 latent clamp는 하지 않는다. 마스크 밖 RGB도 조건이며 출력 픽셀 exact 보존을 보장하지 않는다. 실제 mask context temporal mean과 전체 context/noise/text hash를 첫 model_fn에서 추가 forward 없이 기록한다.

## 고정 숫자 설정과 구현 차이

공식 `vace_wan_inference.py` CLI 기본값을 확인하여 steps50, CFG5, shift16을 고정한다. 고정 positive prompt와 seed20261103을 사용하고 negative prompt는 Wan 공식 shared config의 기본값을 쓴다. 사용자 timebase24fps,832×480,73/49프레임을 유지한다.

**샘플러 구현 차이:** 공식 CLI는 UniPC를 기본으로 사용한다. 이번 승인된 기존 runner는 DiffSynth `FlowMatchScheduler`의 native Euler를 그대로 사용한다. 새 UniPC 구현을 이식하거나 서로 같은 샘플러라고 기록하지 않는다. CFG5에서50 scheduler step·100 model_fn call이 정상 계약이다. BF16 backbone, SDPA, 기존 tiled VAE를 유지하고 모든 모듈은 eval/grad-disabled다. optimizer와 backward는 없다.

14B 시간 측정은 실제50-step grid의 첫 positive/negative 쌍과 scheduler step1회 뒤 전용 예외로 종료한다. timestep 수를1로 바꿔 다른 grid를 측정하지 않으며 decode하지 않는다. 정상 생성은 마지막 scheduler 결과를 reference prefix 포함 상태로 원자 저장·readback한 후 native decode한다. raw tensor·전PNG·원MP4를 보존하고 후합성하지 않는다.

## 적재와 비용 근거

| 모델 | 저장 F32 payload bytes | 저장 BF16 payload bytes | BF16 transformer 계산 크기 bytes |
|---|---:|---:|---:|
| 1.3B | 5,675,987,200 | 1,469,950,464 | 4,307,944,064 |
| 14B | 57,153,966,336 | 6,098,202,624 | 34,675,185,792 |

공유 T5 파일은11,361,920,418bytes, VAE 파일은507,609,880bytes다. 저장 헤더와 실제 runtime tensor 크기를 구분한다. 1.3B는 기존 BF16 GPU 적재,14B는 diffusion disk offload·공유 모델BF16 CPU와 native `vram_limit=24` 경로다. 이는 worker100GiB cgroup 한도와 다른 내부 적재 한도다. Activation/page cache를 포함한 실제 시작 여부는 별도 사전 peak 추정·guard가 결정한다. 모든 heavy 진입에 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`를 요구한다.

### 14B disk offload의 peak 추정 한계

추가 정적 확인에서 `core/loader/model.py`의 disk 경로는 meta 초기화 후 `DiskMap`을 사용하므로 transformer 전체의 FP32 CPU 복사본을 만들지는 않는다. `core/vram/disk_map.py`는 safetensors를 CUDA device로 열어 tensor별로 읽고, `core/vram/layers.py`의 wrapped module이 BF16으로 변환한다. 이때 원 저장 dtype의 임시 CUDA tensor와 BF16 tensor가 겹칠 수 있다. 공유 T5/VAE의 binary loader는 전체 state dict를 읽는다.

그러나 파일 page cache의 퇴거를 보장하는 코드는 없다. `DiskMap.flush_files()`는 파일 handle을 재개방하며 cache 회수의 증거가 아니다. `vram_limit=24`도 hard peak 한도가 아니다. `check_free_vram()`은 현재 CUDA 사용량을 검사하고, 기준을 넘더라도 `computation()`은 계산용 임시 module을 적재한다. 따라서 파일 payload 63,252,168,960bytes(58.91GiB), BF16 transformer 32.29GiB, 공유 모델과 활성값의 동시 존속을 배제할 수 없다. 100GiB 이하라는 보수적 사전 추정을 입증할 수 없으므로 14B는 `ENGINE_BLOCKED_MEMORY_ESTIMATE`로 남길 것을 권고한다. 이는 실제 OOM이나 모델 실행 실패 관측이 아닌 실행 전 추정 한계다.

## 소스 계보

- 기존 DiffSynth `diffsynth/pipelines/wan_video.py` SHA256: `e3ab58df6db88987661813f92bca601de1397aa6a2986f2a9dda6e2771183bcc`.
- 기존 DiffSynth `diffsynth/diffusion/flow_match.py` SHA256: `43abe34773144e7f3ce660d40bf5f3ee25fe5538cbc7654c3992b9e40a761486`.
- 공식 VACE 확인 revision: `48eb44f1c4be87cc65a98bff985a26976841e9f3`.
- [공식 CLI 기본값](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/vace_wan_inference.py): `validate_args`, `get_parser`.
- [공식 입력·마스크·참조 처리](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/models/wan/wan_vace.py): `vace_encode_frames`, `vace_encode_masks`, `prepare_source`. 참조는 aspect-fit bilinear resize 후 white canvas 중앙 배치다.
- [Wan 기본 negative prompt](https://github.com/Wan-Video/Wan2.1/blob/main/wan/configs/shared_config.py).

실제 경로는 private config에만 보존한다. `--cpu-only`는 모델 import 없이 입력과 경로를 검사하며 CPU PASS를 추론 성공으로 계산하지 않는다.

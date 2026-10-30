# 적재 경로와 비교 범위

14B 공식 revision은 `539c162b1387eac9dc4c20bd3f74671309e76a4c`다. 기존 설치 DiffSynth 기록 revision `f39d731a3e318d25b725eb3389cfddb184619842`의 14B native registry와 모델 변환을 사용한다. 실제 설치 관련 파일의 hash를 freeze한다. 기존 소스 snapshot에는 .git이 없으므로 기록 revision을 현재 git HEAD로 검증한 것처럼 쓰지 않는다. MODEL_MANIFEST의 actual_git_head는 null이며 실제 파일 hash가 실행 근거다. 업그레이드·새 커널·양자화는 없다.

## 저장값과 모델 구조

공식 7개 shard의 합계는63,252,305,152bytes다. bounded HTTP206 header의 tensor storage 합계63,252,168,960bytes이며 1–6 shard는 F32(57,153,966,336bytes),7번은 BF16(6,098,202,624bytes)다. index1331keys가 header와 대응한다. index metadata.total_size=69,350,371,584는 실제 저장 bytes와 다르며 BF16 VACE 부분을 두 배로 센 값과 일치한다. 실제 파일 크기와 dtype/offset을 우선한다.

header 기준 DiT는14,288,491,584개, VACE는3,049,101,312개 tensor element이며 합계17,337,592,896개다. 모델명14B는 이 추가 조건 모듈과 T5/VAE까지 합친 전체 크기가 아니다. BF16 계산 가중치 총량은34,675,185,792bytes(32.294GiB)다. 이는 T5/VAE·activation·temporary·cache를 포함한 실행 메모리가 아니다. 14B DiT는5120차원40block/40head, VACE는96채널 입력의8block이다. 기존 registry hash `7a513e1f257a861512b1afd387a8ecd9` 경로로 DiT/VACE를 분리하며 vace 접두사 partition 외에 임의 tensor 변환을 하지 않는다.

## 로더와 고정 memory path

`core/loader/model.py`는 meta 초기화 후 native VRAM wrapper를 구성한다. diffusion은 offload/onload=`disk`, preparing/computation=`BF16,cuda`로 설정한다. onload=CPU 예제처럼32.294GiB 전 가중치를 CPU에 추가 유지하지 않는다. `DiskMap`의 safe_open은 필요한 tensor만 꺼내고 저장 F32 tensor의 일시 CUDA값을 BF16으로 바꾼다. source 전체 tensor dict를 먼저 materialize하지 않는다. disk 분기는 전역 strict load를 하지 않으므로 **별도 CPU/meta 예상 key/shape 전수 equality**를 heavy 전에 확인한다. 가중치 누락 허용이 아니다.

T5/VAE는 검증된 기존 파일을 쓰며 offload/onload=`BF16,cpu`, preparing/computation=`BF16,cuda`다. 기존 .pth는 weights_only=True로 읽는다. T5의 BF16 checkpoint 약10.58GiB와 CPU clone이 초기 적재 때 일시 공존할 수 있다. converter/assign 완료 후 loader 원본 dict가 해제되는 범위를 포함해 계산한다. 이를 FP32 파일로 잘못 부르지 않는다.

native `vram_limit=24.0` GiB를 두 사례에 동일 적용한다. 이는 check-before-layer cache 기준이며 hardcap이 아니다. global CUDA used memory를 읽으므로 실제 모델 캐시는24GiB보다 적을 수도 있다. largest-layer temporary·activation·CUDA reserved·CPU weights와 별도 측정해야 한다. 기존 supervisor MemoryMax64GiB/MemoryHigh62GiB 계산과 시작72GiB/실행24GiB headroom, swap0 worker, 전역 swap 증가/PSI 기준은 변경하지 않는다.

사전 예산은 cache24 + shared CPU 약11.1 + temporary/allocator/activation 여유12–16GiB = 약47–51GiB의 계산상 범위와 reclaimable file cache를 별도로 고려한다. 실제 peak 보장이 아니며 native layer 최대값/메모리 경로 감사와 fresh guard를 통과해야 한다. 전체58.91GiB 파일이 pinned RAM에 상주한다고 가정하지 않고, 반대로 file cache를 무료 메모리로도 보지 않는다. 부족하면 RESOURCE_INFEASIBLE_UNDER_CURRENT_POLICY로 종료하며 한도를 늘리거나 OOM trial을 하지 않는다.

## 관측과 해석

기존 최초 model_fn hook은 noise/context/mask를 읽기만 하며 추가 forward/RNG는 없다. 단계 비용 hook은 model load, text encode, condition VAE, denoising, decode, packaging 경계를 CUDA synchronize로 계측한다. process read_bytes는 전체 I/O이며 isolated offload bytes는 null로 둔다. cgroup current·host RSS·CUDA allocated/reserved·MemAvailable은 다른 지표다.

입력·noise·수학적 조건이 같더라도 1.3B는 기존 상주 경로,14B는 native offload이므로 비교는 QUALIFIED다. 두 checkpoint의 학습/구조/메모리 구현이 함께 다르므로 속도 차이를 파라미터 수 하나의 인과효과로 보고하지 않는다. 기존 worker elapsed는 전체 worker 범위여서 새 denoising-only와 직접 나누지 않는다.

공식 근거: [14B config](https://huggingface.co/Wan-AI/Wan2.1-VACE-14B/blob/539c162b1387eac9dc4c20bd3f74671309e76a4c/config.json), [native low-memory example](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/examples/wanvideo/model_inference_low_vram/Wan2.1-VACE-14B.py). 예제 totalGPU−2GiB 값은 사용하지 않는다.

## 실행 전 CPU/meta 확인 완료

실제 설치 registry/converter/class를 CPU/meta에서 구성하여 DiT1095+VACE236=1331 key와 shape가 공식 index/header와 전부 일치함을 확인했다. missing/unexpected/wrongshape0, CUDA 미초기화, full weight load0이다. 가장 큰 DiT tensor는 time_projection[30720,5120]으로 저장 F32 일시0.586GiB와 BF16 0.293GiB다. 보수적인 전체 VACE block 단위도 BF16 약0.752GiB다. 독립 감사에서 고정 disk/disk 경로의 전체 FP32 GPU dict 잔존이나 새 RNG/추가 forward는 확인되지 않았다. 실행 peak와 안전을 보장하는 검사는 아니며 기존 fresh guard가 필수다.

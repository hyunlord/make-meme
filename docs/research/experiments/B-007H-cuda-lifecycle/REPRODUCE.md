# B-007H 재현 계약

현재 실제 H 실행은 **PROBE PASS / SAMPLER_LATENT_PASS / VIDEO_OUTPUT_PASS**다. probe는6.062초, service_exit0·PID0으로 종료했으며 해당1회는 소진됐다. 재실행하지 않는다. [PLAN](PLAN.md)의 제한된 probe와 조건부 S→D만 대상이며, 이 문서 자체는 새로운 실행 승인이 아니다. 실행 사전 등록 commit은 `80f51ff`다. 실제 CLI는 아래와 같으며 이미 소진된 stage를 반복하는 명령이 아니다.

## 변경하지 않는 입력

- G의 실제 P 조건 캐시: 17,365,660 bytes, SHA256 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`.
- E와 동일한 initial noise SHA256 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`.
- pinned SCAIL `78fe19576bb06be96c2375e088574a262a300edb`, 기존 weights/mixed dtype/staged loader/attention.
- 공식17프레임·H512×W896·16fps, seed20261022, UniPC40 step, shift3, CFG5, history=None, adapter 없음.
- P 재실행0, Lab0, 신규 다운로드/학습/외부 생성0. 기존 E/F/G 기록과 실패를 보존한다.

## 조건부 실행 순서

1. 같은 서비스 환경의 fresh worker에서 CPU 캐시 무결성 확인→1MiB 이하의 RNG 비소비 CUDA copy/연산/synchronize/readback→leaf별 원래 device 복원과 값 검증을 최대 한 번 수행한다. 모델은 적재하지 않는다.
2. probe PASS와 PID0·자원 회복 확인 후, 별도 fresh worker에서 같은 tiny 연산을 먼저 수행하고 CPU DiT 적재를 최대 한 번 진행한다.
3. 조건 복원과 DiT device 이동을 통과한 경우에만 같은 worker에서 sampler를 최대 한 번 실행한다. 실패도 한정 슬롯에 기록하며 자동 재시도하지 않는다.
4. 실제 final latent 저장·readback과 S 종료·자원 회복 후에만 별도 VAE-only D를 한 번 실행한다. 초기 noise나 G cache를 final latent로 사용하지 않는다.

worker는 CUDA 초기화한 부모의 fork가 아닌 별도 exec다. 실제 absolute deadline과 unit은 H용 사전 등록값을 사용한다. 시작72GiB, 실행24GiB headroom, swap0과 기존 cgroup cap 산식을 유지하며 상위 제한은 읽기만 한다. 환경·driver·다른 프로세스·전역 cache를 변경하지 않는다.

## 필수 receipt

probe와 S에서 실제 API 순서, leaf 이름/byte 수/original device, phase start/end, readback hash, RNG 확인, runtime/context 상태를 구분한다. `mem_get_info`는 실제 CUDA 성공 이후에만 기록한다. CUDA initialized 또는 allocator0만으로 작은 연산을 통과시키지 않는다.

CPU load, restore, move, first forward, sampler step/call, final latent, decode, MP4의 실행 여부를 별도 기록한다. MemAvailable/RSS/cgroup anon·file·events/CUDA allocated·reserved는 겹치는 계정이므로 합산하지 않는다. 종료 상태와 PID0도 확인한다. 단순 service returncode0이나 파일 재생 가능 여부는 시각 품질 수용이 아니다.

## 고정된 launch 형식

실제 stage root는 `${RUN_ROOT}/stages/PROBE`, `S`, `D`다. probe는300초, S는7200초, D는3600초이며 runtime launcher가 절대 deadline인 2026-10-23 02:35 UTC의 남은 시간으로 제한한다. 각 stage의 실행 권한과 선행 성공을 확인한 뒤 개별 실행하며 무조건 반복하는 loop로 만들지 않는다.

```sh
# 이미 끝난 PROBE 명령의 재현 기록. 다시 실행하지 않는다.
STAGE=PROBE
SECONDS_CAP=300
STAGE_ROOT="${RUN_ROOT}/stages/${STAGE}"
"${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/runtime_launch.py" "${STAGE_ROOT}" "${SECONDS_CAP}" \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/run_phase.py" "${STAGE_ROOT}" "${STAGE}"
```

[run_phase.py](code/run_phase.py)는 stage별 exclusive attempt와 이전 stage의 완료·PID0을 검사한다. [cuda_probe.py](code/cuda_probe.py)의 실제 tiny 연산은16개 FP32 상수3을 copy하여2를 더하고 CPU에서5를 검증하는64-byte anchor다. tiny 전후 CPU RNG는 같았다. CUDA RNG는 tiny 성공 후 baseline과 cache 복원 뒤만 비교해 같음을 확인했으며 tiny 이전 CUDA 상태 측정은 하지 않았다.16개 leaf 원래 device/hash 복원 PASS, optional driver GetState는 NOT_CALLED다. S는80회 forward·40 step을 완료했고 D도 완료해 VIDEO_OUTPUT_PASS다. [학습 문서](../../lessons/B-007H-cuda-lifecycle.md)를 참고한다. 개인 경로·원본 media·조건/latent/가중치는 공개 문서에 포함하지 않는다.

### S 실제 관측

S는 약204초에 CPU 적재를 완료한 뒤 tiny 재검사와16개 original-device 조건 복원에 통과했다. DiT device 이동도 통과했고 stage 시작240.642초에 `first_forward_start`가 관측됐다. 해당 시점 CUDA allocated는33,268,072,448 bytes, 시스템 MemAvailable은59,302,164 KiB였다. G에서 실패한 복원 경계를 이번 실행에서는 넘었다는 증거이며, 초기화 순서가 유일한 원인이라는 증명은 아니다. 이후 S는80회 forward·40 step을 완료하여 stage_S_complete가1196.45초에 기록됐다. S의 전체 guard 시간은1199.009초이며, final latent 값 hash는 initial noise와 다르다. S 종료와 자원 회복 뒤 별도 D가 phase 기준13.262초에 완료해 VIDEO_OUTPUT_PASS를 기록했다. D 전체 guard 시간은15.228초이며 decode 구간은6.720초다. 단계 완료13.262초와 guard 전체 시간을 혼동하지 않는다. 실제 연속 재생 품질은 UNVERIFIED다. 실행 순서 변경이 관측된 실패 경계를 넘게 한 사실은 새 생성 방법이나 G 원인 확정의 근거가 아니다.

다음 제안은 기존 입력을 사용하는 Lab17프레임 고정 baseline 한 가지이며 이번에는 실행하지 않았다. 공식 사람 예제의 출력 확보는 Lab identity·안무 수용이나 초기화 순서의 유일한 인과 증명이 아니다. 추가 sampler·decode·실험은 실행하지 않는다.

## 최종 receipt 대조

[RUN_LEDGER](RUN_LEDGER.json), [MEASUREMENTS](MEASUREMENTS.json)를 확인했다. PROBE/S/D 모두 returncode0·MainPID0·inactive, retry0이다. guarded 시간은 각각6.062/1199.009/15.228초다. P는 재실행하지 않았고 model load1·sampler1·decode1을 사용했다. S80calls/40steps는 실제 persisted progress와 final sidecar로 확인됐다.

| 산출물 | bytes | 파일 SHA256 |
|---|---:|---|
| final_latent.safetensors |2293840|`d9014a440d1c5998d720310935b039a4bddde876f92567b28949ecd0773a9aec`|
| output.mp4 |1206562|`9f5b04d9c4e0798330423ed90a12b3cb3ae2b7c9e7f84200474b9af6ec4dac8f`|
| raw_output.pt |93587006|`bf91c20c230cb80683b5a9cfedc59687d6c8c9fbaad6861156738029ed024150`|

final latent 값 hash는 파일 hash와 별도로 `f129057bb2cbaca33cc0e494eb472c6ccf03a753fcf37afc48e0649ddf075bd6`이며 initial noise와 다르다. CPU-only readback은 exact/finite FP32 `[16,5,64,112]`를 확인했다. raw는 finite `[3,17,512,896]`, 영상은17프레임·16fps·1.0625초다. 재생 품질은 UNVERIFIED다. code/upstream/cache287개 보존 검사는 일치했지만 이번에 전체 가중치를 새로 해시 검사했다고 주장하지 않는다.

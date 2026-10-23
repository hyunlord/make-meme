# B-008 재현 계약

최종 기술 상태: **P/PROBE/S/D PASS**. 정적 검토에서 동작 전달 FAIL·실제 개체 UNCERTAIN이며 시간 품질은 UNVERIFIED다. [PLAN](PLAN.md)의 P→PROBE→S→D 각1회만 대상이다. 사전 고정 commit은 `e1424cb`다. 문서의 예상값을 실측으로 사용하지 않는다.

## 고정 조건

기존 실제 Lab reference, source f0~16, 대응 RED instance mask를 사용한다. H 사람 조건/latent를 Lab 산출물로 재사용하지 않는다. prior Lab prompt 원문과 입력 SHA는 실행 전 config/manifest로 고정한다. source와 mask는 같은 resize/crop을 적용하고 기존 얇은 앞발·꼬리·반사 경계의 PARTIAL_UNRESOLVED를 유지한다. 결과를 본 뒤 mask를 수정하지 않는다.

- pinned SCAIL `78fe19576bb06be96c2375e088574a262a300edb`, 기존 가중치·mixed dtype·FA·staged loader와 H의64-byte CUDA anchor 경로.
- Lab H896×W512,17프레임·24fps, seed20261022, UniPC40step, shift3, CFG5, history=None, segment17/overlap5, LoRA/enhancer OFF.
- 예상 generated latent `[16,5,112,64]`, raw `[3,17,896,512]`를 실제 encode/decode shape와 대조한다. 가로 tensor를 reshape하지 않는다.
- P/PROBE/S/D 각각 최대1회, 새 download/학습/공식 예제 재생성/다른 동물0. 실패 시 자동 재시도 없음.

## 실행 순서와 증거

1. P는 DiT 없이 Lab 조건·noise·RNG·schedule을 저장하고 hash/shape/dtype/device/container를 readback 검증한다. 공식 사람 cache hash 강제 대신 명시적 Lab manifest를 사용한다.
2. P 종료·PID0·자원 회복 뒤 PROBE는 Lab cache만 검증한다. H와 같은 비무작위 tiny 연산과 원래 leaf device 복원을 확인한다.
3. PROBE 종료·회복 뒤 S는 작은 CUDA 연산을 먼저 수행하고 동일 CPU loader/device 이동/sampler를 실행한다. Lab P noise와 S의 실제 입력을 비교한다.80 forward/40 step 및 finite final latent의 원자 저장·readback을 기록한다.
4. S 종료·회복 뒤 D는 VAE만 적재한다.17프레임·512×896·24fps·0.708333초, raw finite, MP4 decode/ffprobe를 확인한다. 최종 latent 없이 D를 시작하지 않는다.

각 worker는 fresh process다. 시작/24GiB headroom·swap0·cgroup 정책과 다른 서비스 보호를 유지한다. deadline과 unit은 B-008용 값을 사용한다. 새 CUDA 감사·allocator·tiling·모델 변경은 추가하지 않는다. 이미 예약된 attempt 파일을 삭제하거나 실패 횟수를 초기화하지 않는다.

## 검토 자료

raw17장, f0/4/8/12/16 시트, 원본/preprocessed/reference/output 비교와 native24fps 비교 MP4를 보존한다. 확대·warp·보간·프레임 복제로 불일치를 숨기지 않는다. 파일 길이0.708333초와 첫/끝 sample 간격0.666667초를 구분한다. 전체17장 정적 관찰은 연속 재생 검증이 아니며 temporal=UNVERIFIED를 유지한다.

개인 media·조건/latent·경로는 비공개이고 공개에는 코드·비민감 manifest/hash/요약만 둔다. 최종 receipt와 실제 launch 명령은 아래에 기록한다. [학습 문서](../../lessons/B-008-reference-motion-generalization.md).

## 사전 고정된 실제 launch 형식

stage root는 `${RUN_ROOT}/stages/P`, `PROBE`, `S`, `D`다. 요청 시간 상한은 각각1800/300/7200/1800초이고 전체 absolute deadline은2026-10-23 04:28 UTC다. launcher는 남은 deadline으로 시간을 제한한다. 아래는 실행 형식 기록이며 이미 예약한 stage를 반복하지 않는다.

```sh
STAGE=P
SECONDS_CAP=1800
STAGE_ROOT="${RUN_ROOT}/stages/${STAGE}"
"${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/runtime_launch.py" "${STAGE_ROOT}" "${SECONDS_CAP}" \
  /usr/bin/env PYTHONDONTWRITEBYTECODE=1 CUDA_MODULE_LOADING=LAZY \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg \
  "${STAGE_ROOT}/environment/bin/python" \
  "${STAGE_ROOT}/code/run_phase.py" "${STAGE_ROOT}" "${STAGE}"
```

[run_phase.py](code/run_phase.py)의 case/manifest 검사와 이전 stage 종료 검증을 유지한다. [phase_prepare.py](code/phase_prepare.py)의 독립 preprocessed hash 대조는 실제 Lab 입력 연결의 증거이며, 모델이 참조 개체와 동작을 의도대로 사용했다는 의미는 아니다. 그 구분은 raw 출력의 별도 품질 검토가 담당한다.

## 실제 P receipt

P118.06초 완료, 독립 전처리4개 tensor hash 일치. 새 Lab cache17,685,156 bytes의 SHA256은 `96164a2c54d38e86f006504824a85499f669eaca12f05ee3e6afe5a3858a0287`이다. noise FP32 `[16,5,112,64]`, reference `[16,1,112,64]`, reference mask `[28,6,112,64]`, driving `[16,5,56,32]`, driving mask `[28,5,56,32]`를 실제 관측했다. positive text는44×4096 BF16, negative1×4096 BF16, CLIP1×257×1280 FP16이다.

flattened noise hash는 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`으로 H와 같게 관측됐지만 seed와 element 수가 같은 결과다. H 일치를 강제하지 않았으며 H cache를 가져온 것이 아니다. shape는 다르므로 cache/shape/dtype/value hash를 함께 확인한다. 후속 S/D도 완료했으며 아래 최종 receipt를 따른다.

## 최종 실행 receipt

[RUN_LEDGER](RUN_LEDGER.json)의 P/PROBE/S/D guarded 시간은118.060/6.063/1066.317/15.219초다. 각1회·재시도0·returncode0·PID0/inactive를 확인했다.80 forward/40 step, finite FP32 final `[16,5,112,64]`, readback exact, Lab P→S noise exact다. raw finite `[3,17,896,512]`, MP4는17프레임·24fps·0.708333초다. 학습은 NOT_RUN이다.

| 파일 | bytes | SHA256 |
|---|---:|---|
| final_latent.safetensors |2293840|`480bacf8b868ad5f175196bf6345a2b5a17a2ad6415c5b8a0675649092a34394`|
| output.mp4 |605364|`774a637b48f82c3eba3120842b42f05e8653184f67c9ff606c5b04adf4fa00e6`|
| raw_output.pt |93587006|`eadad46956804f87356f57581d1e547842088125c1470283765187a719441bf4`|

final tensor 값 hash는 `24f40d5fd79571fdecd969f5e5ba1227c55a096c9a8770e2022469c270fe1813`이며 파일 hash와 다르다.424개 code/upstream/input 사후 검사는 일치했다. 기존 가중치 계보를 재사용했으며 새 전체 가중치 rehash를 수행했다고 주장하지 않는다. 정적 전체17장 검토에서 앉은 참조 자세·침대/커튼 배경이 유지돼 원본 직립 동작 전달은 FAIL이다. 실제 개체는 UNCERTAIN, 연속 재생 품질은 UNVERIFIED다. 추가 실험은 실행하지 않는다.

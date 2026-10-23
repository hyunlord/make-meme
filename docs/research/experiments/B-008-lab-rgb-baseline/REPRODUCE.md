# B-008 재현 계약

현재 Lab 실물 결과는 **NOT_RUN / 대기**다. [PLAN](PLAN.md)의 P→PROBE→S→D 각1회만 대상이다. 실행 코드와 실제 CLI가 고정되면 연결하며, 문서의 예상값을 실측으로 사용하지 않는다.

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

개인 media·조건/latent·경로는 비공개이고 공개에는 코드·비민감 manifest/hash/요약만 둔다. 최종 receipt와 실제 launch 명령은 실행 후 이 문서에 연결한다. [학습 문서](../../lessons/B-008-reference-motion-generalization.md).

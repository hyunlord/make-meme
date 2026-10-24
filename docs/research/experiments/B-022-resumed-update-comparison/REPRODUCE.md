# B-022 재현과 저장 상태 계약

이 실행은 B-020의 조건/Y/네prefix를 읽고 B-021의 restart20에서 재개하는 B-022 consumer다. 개인 입력·가중치·optimizer·cache 실물은 비공개이며 공개 코드만으로 복원할 수 없다.

## 출발점

- B-021 restart-020 SHA256: `5e43183e452b1f16736a37986839059082dc3601d0b2c0649bd597ae58ad3934`
- 별도 adapter-020 SHA256: `6d12c6a4e572addbe2b1e19ee6a269cd62b44b707fd2e25758eab29cf481a7a7`
- 순서: q.A,q.B,v.A,v.B. A `[4,5120]`, B `[5120,4]`, FP32. 실제 B는 학습된20회 값이며 Bzero가 아니다.
- AdamW moment와 step20, options, CPU/CUDA RNG, cursor2를 함께 복원한다. 다음update21은train_2다.

`consumer.json`의 역사 initial 정보는 B-020/B-021 producer 계보이며 새 B-022 초기화 지시가 아니다. 실제 출발점은 위 restart20이다. B-021의 엄격 replay FAIL·누락train row20·미도달base검사는 수정하지 않는다.

## 순서와 예산

CPU 검사→사전 코드/config 고정→TRAIN1(진단+재개80update)→자원회복→PROBE1→STEP20_S/D각1→자원회복→STEP100_S/D각1. TRAIN 기능/상태/안전 검사가 실패하면 후속을 실행하지 않는다. sampler·decode도 재시도하지 않는다.

비학습tail forward 계획33회(상한40), 진단backward3, 실제추가update80, 누적endpoint100이다. 같은checkpoint freshreload/OFF는 기존 atol=rtol1e-3와 실제오차를 함께 기록한다. 독립B-020과의 factor/velocity 차이는 별도관측이며새기능검사를 대신하지않는다.

각단계의 실제 argv·deadline·unit·guard·private 경로는 비공개 stages 보고서에 있다. stage명과 ledger를 바꾸어 예산을 초기화하지 않는다. 실험후 재현자료 제공은 추가실행 승인이 아니다.

## 무결성과 미디어

PREREGISTERED_CODE는 실제 실행code/config를 묶는다. producer의 코드hash는 B-020으로 유지하고 consumerhash는별도검사한다. P·prefix 전체forward는0이다. 두endpoint의 실제latent는 decode전에 저장한다. 미디어는896×512,17f,30fps이며 보간·warp·선별없다.

최종판정은 RESULTS와 실제receipt로확인한다. 준비된코드·CPU검사는 GPU학습·영상성공을뜻하지않는다.

## 저장 결과의 CPU 재현

아래는 이미 허가된 격리 Python과 비공개 B022_ROOT를 사용하는 분석 명령이다. 새 설치나 GPU 계산을 하지 않는다. 실제 전체 실행 argv는 ZIP의 stage별 pipeline-process/attempt 기록에 보존한다.

```sh
python analysis/build_loss_curves.py "$B022_ROOT"
python analysis/build_comparison.py \
  --target "$B022_ROOT/reports/comparison-inputs/source" \
  --trained20 "$B022_ROOT/reports/comparison-inputs/step020" \
  --trained100 "$B022_ROOT/reports/comparison-inputs/step100" \
  --reference "$B022_ROOT/reports/comparison-inputs/reference.png" \
  --output "$B022_ROOT/reports/comparison-review"
```

위 comparison은 실제 export된17개 PNG와 원래30fps를 사용한다. GPU phase의 entrypoint는 `code/run_phase.py STAGE_ROOT STAGE`이나, 반드시 기존 runtime_launch/runtime_guard의 service·메모리·deadline·1회 ledger 하에서만 호출했다. 이 entrypoint를 직접 재실행하거나 attempt 파일을 지워 제한을 초기화하는 것은 재현 명령에 포함되지 않는다.

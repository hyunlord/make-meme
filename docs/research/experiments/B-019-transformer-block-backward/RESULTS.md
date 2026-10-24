# B-019 결과: full block backward와 제한된 긴 입력 검사

**소형 SMALL_BLOCK_UPDATE_RELOAD_PASS, 긴 LONG_BLOCK_BACKWARD_PASS.** 공식 마지막 Transformer block만 실행했다. 실제 동물 데이터·전체 모델 학습·영상 품질·개체/자세 분리는 NOT_RUN이며 B-017 데이터/권한 부족은 유지한다.

## 실제 실행과 보존

사전 등록 `26c085635c41f77d26bd9f75a5c0976389b7ee3a`를 push하고 원격 일치 확인 후 GPU worker **1회**만 실행했다. `blocks.39.`32개 원본F32 tensor(403,838,464 parameter /1,615,353,856bytes)를 safe_open으로 선택했다. self/cross/norm/modulation/residual/FFN은 pinned 공식 연산 그대로다. Linear만BF16, norm/modulation은 원본FP32를 직접 보존했다.

B-018의 실제 x/target 및 Bzero 초기 adapter를 재사용했다. B-018 final adapter 이어학습은 하지 않았다. 새 context/e의 값·해시를 실행 전에 고정했다. 영상/사진/cache를 학습하지 않은 **SYNTHETIC_TENSOR_CONTRACT_TEST**다. 학습 대상81,920개FP32 parameter는 self_attn.q/v rank4·alpha4·dropout0 LoRA뿐이다. 전체 base는 동결·optimizer 제외·grad=None·값 불변을 확인했다.

| 단계 | 실제 block forward | backward | optimizer update | 판정 |
|---|---:|---:|---:|---|
| 소형36token, Bzero/baseline/훈련/reload/OFF 포함 | 8 | 3 | 3 | PASS |
| 긴12,992token, 같은 한 block | 1 | 1 | 0 | PASS |
| 합계, 동일worker | **9** | **4** | **3** | 재시도0 |

실제 FA2 wrapper를 사용하고 각 backward graph에서 self1+image cross1+text cross1의 FA backward node3개를 확인했다. SDPA fallback은 사용하지 않았다. 소형8forward와 FA8회는 같은 수가 아니다.

## 소형 결과

| update | synthetic 최종-output FP32 MSE | q.A grad norm | v.A grad norm | step seconds |
|---|---:|---:|---:|---:|
| 1 | 7.107974052 | 0.000000000 | 0.000000000 | 2.252 |
| 2 | 7.107662201 | 0.019015504 | 0.121488243 | 2.161 |
| 3 | 7.106311321 | 0.038024213 | 0.242827564 | 2.171 |

첫 A gradient0은 Bzero에 따른 정상 결과였다. 첫 B는 비영이고 이후 A/B 모두 비영·finite, 실제 adapter delta를 확인했다. 수치 loss가 조금 내려갔다는 것은 이 인공 과제의 배선 결과이며 FM/동물 학습 개선량이 아니다. loss를 낮추려 추가 update하지 않았다.

x gradient와 self/cross/FFN 입력 gradient가 finite·비영이었다. 첫 update의 cross 입력norm0.0219127, FFN입력0.329816, image context0.00454079/text0.0706191이다. residual만 통과해도 LoRA gradient가 남을 수 있으므로 실제 branch hook과 context partition을 별도로 검사했다. 개별 K/V hook이나 모든 개별 원소 비영까지 주장하지 않는다.

Bzero 대 baseline, fresh component reload 대 학습 후, adapter OFF 대 baseline의 **max absolute error는 모두0**이었다. 원래 고정 tolerance atol/rtol1e-3도 통과했다. fresh는 같은 worker의 새 component 객체이며 독립OS프로세스 재검증이라고 부르지 않는다. 초기/최종 adapter는 TEST_ONLY로 보존했고 실제 추론에 적용하지 않았다.

## 긴 입력 결과와 자원

`[1,12992,5120]`은 ref1792+generated8960+driving2240, T5/H56/W32의 공식 RoPE 계약이다. 실제 앞39층 출력/동물 activation이 아닌 fixed-seed synthetic tensor다. 작은 graph·optimizer·불필요한 source 사본을 해제하고 소형 결과를 원자적으로 저장한 후 실행했다.

긴 backward도 x·LoRA·self/cross/FFN·image/text 경로가 finite·비영이었고 base와 adapter 값은 불변이었다. **optimizer update0**이므로 full training 비용이 아니다. 실제 긴 tensor는 저장/ZIP하지 않고 recipe·hash만 기록했다.

| 관측 | 소형 단계 | 긴 단계 |
|---|---:|---:|
| 측정 구간 시간 | 24.290s | 6.803s |
| CUDA peak allocated | 976,793,088B (0.910GiB) | 6,244,993,024B (5.816GiB) |
| CUDA peak reserved | 1,004,535,808B (0.936GiB) | 7,249,854,464B (6.752GiB) |
| 완료 시 RSS | 3,579,699,200B | 2,099,101,696B |
| cgroup peak, 누적 | 2,018,435,072B | 2,115,108,864B |

소형 시간은 적재/해시/reload를 포함하고 긴 시간도 입력 준비·검증/hash가 포함된다. 순수 kernel benchmark나 warm steady-state latency로 해석하지 않는다. 긴 CUDA peak는 단계 직전 reset한 값이며 RSS/cgroup high-water는 프로세스 누적이다. 단위별 측정값을 더해 총메모리로 만들지 않는다. 통합메모리에서 cgroup charged bytes와 CUDA allocator는 서로 다른 회계다. 이번 cgroup peak약2.1GB와 CUDA peak약6.24GB의 차이 때문에 **cgroup16GiB를 전체 통합 GPU allocator의 검증된 hard cap으로 주장하지 않는다**. 별도 시스템 headroom 관측·가드를 함께 유지했다.

긴 사전 추정13,830,425,600B는 휴리스틱이며 상한 보장이 아니다. 16GiB cap/high14GiB·시작72GiB·실행24GiB headroom·swap0을 유지했다. guard wall36.351초, worker service35.640초, worker CPU time35.424초였다. sampled MemAvailable 최저86,151,704,576B, RSS 관측최대4,004,999,168B, swap0·cgroup high/max/OOM event0이다. 종료 후 두 owned unit은 inactive/PID0, 보호 서비스의 identity는 동일하고 queue idle을 확인했다. 전체 guard/시간/자원 회복 증거는 MEASUREMENTS와 private receipt에 보존한다. 한block peak×40로 전체모델 학습 가능성을 보증하지 않는다.

## 검사·코드 범위·한계

최종CPU18PASS, criticalRuffPASS. runner type0errors/145warnings로 **NOT_CLEAN**이다. 실제 tensor/경로/optimizer 연결 가능 오류를 우선 수정했고 동적 upstream/JSON/PyTorch 경계 경고를 suppression으로 숨기거나 무관한 타입 리팩터링을 하지 않았다. 공식 upstream·A·기존 환경은 수정하지 않았다.

변경은 별도 full-block runner·작은 계약 검사·기존 guard/LoRA helper 재사용·기록에 한정된다. 다른 backend/새framework/추가adapter/quantization/checkpointing은 넣지 않았다. 작은 fixture 성공도, 긴한block 성공도 전체 모델 학습 또는 실제 개체/동작 분리의 증거가 아니다.

## 다음 학습 목표 하나

**권한이 확인된 실제 Lab 자연동작 Y와 다른 시점 R을 이용하는 동일 개체 조건부 FM 소형 overfit**을 다음 목표로 둔다. 현재 R/Y·identity/session·사용권한이 부족하므로 DATA_PENDING이다. D=Y면 driving 복사 shortcut이 남으며 cross-ID 춤 학습/일반화라고 부르지 않는다. 이 실측을 참고하되 전체pipeline의 activation·encoder·optimizer 동시상주를 별도 예산으로 설계해야 한다. 이번 뒤 component 수 늘리기, 데이터 수집·생성·학습은 실행하지 않았다.

근거: [사전 계약](PREREG.md), [수치 실측](MEASUREMENTS.json), [재현](REPRODUCE.md), [공식 block 대응](BLOCK_CONTRACT.md).

# B-008 결과: Lab RGB-driving 기준선

**실행 PASS / 직립 동작 전달 FAIL / 특정 개체 UNCERTAIN / temporal UNVERIFIED.**

P·PROBE·S·D를 각각 한 번 실행해 실제 Lab 출력17프레임·512×896·24fps MP4와 재사용 가능한 최종 latent를 확보했다. 그러나 전체17장 정적 검토에서 출력은 참조의 착석 자세와 침대·커튼 배경을 유지했다. 원본의 뒷발 직립과 앞발 자세를 재현하지 못했다. 이번 baseline의 기술 완료를 반려견 동작 전이 성공으로 해석하지 않는다.

## 고정 조건과 실제 실행

시작 HEAD `c7d38938e51943576637611cdec9ae51902e0d65`, GPU 실행 전 코드/config 고정 `e1424cb088c745ef83ee1ce5d4f4ee05a1e22dec`. [PLAN](PLAN.md), [실행 장부](RUN_LEDGER.json), [입력 감사](INPUT_AUDIT.md), [재현](REPRODUCE.md).

H의 고정 SCAIL2·FlashAttention·mixed BF16/FP32 loader·tiny CUDA 선행 연산/64-byte anchor·phase separation을 보존했다. 공식 인간 입력을 재생성하거나 재사용하지 않고 기존 실제 Lab 사진·RED 대응 mask·RGB f0~16에서 새 P를 만들었다. seed20261022, UniPC40steps, shift3, CFG5, history=None, LoRA/enhancer OFF. 사전 Lab prompt를 변경하지 않았다.

| 단계 | 시도/상한 | guarded 시간(초) | 실제 완료 증거 |
|---|---:|---:|---|
| P | 1/1 | 118.060 | Lab cache·noise·RNG, 실제 전처리4tensor hash 일치 |
| PROBE | 1/1 | 6.063 | 실제 CUDA copy/add/sync/readback,16leaf 원래 device 복원 |
| S | 1/1 | 1066.317 | 실제40step·80forward, finite final latent·readback exact |
| D | 1/1 | 15.219 | finite raw `[3,17,896,512]`,17frame MP4 decode 검증 |

각 worker는 service_exit0·MainPID0으로 종료했다. 선행 종료·자원 회복 후 다음 worker를 실행했고 재시도0, 신규 학습/모델 다운로드/외부 생성0이다. 기존 ComfyUI 등 다른 작업을 종료하지 않았다. 기존 E/F/G/H의 실패 이력을 보존한다.

파일 시간은17/24=0.708333초, 첫·끝 sample 간격은16/24=0.666667초다. 24fps 저장은 원본 sample time 정합이며 모델의 기본16fps 시간 prior를 재학습한 것이 아니다.

## 조건·latent 계보

실제 P noise `[16,5,112,64]` FP32, reference `[16,1,112,64]`, half-resolution RGB driving `[16,5,56,32]`, text `[44,4096]`; 실제 VAE stride `(4,8,8)`를 확인했다. driving latent는 관절 좌표가 아니다. 원본 RGB/mask는 동일 공간 변환을 거쳤으며, reference/driver의 RED instance 대응과 독립 전처리4개 shape/dtype/hash가 실제 P와 일치했다.

- 새 Lab conditions SHA256: `96164a2c54d38e86f006504824a85499f669eaca12f05ee3e6afe5a3858a0287`
- final latent 파일 SHA256: `480bacf8b868ad5f175196bf6345a2b5a17a2ad6415c5b8a0675649092a34394`
- final tensor 값 SHA256: `24f40d5fd79571fdecd969f5e5ba1227c55a096c9a8770e2022469c270fe1813`
- actual initial noise 값 SHA256: `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`
- MP4 SHA256: `774a637b48f82c3eba3120842b42f05e8653184f67c9ff606c5b04adf4fa00e6`

Lab P→S noise 값·shape·RNG 계약을 검증했다. flattened noise bytes hash는 H와 같게 관측됐다. 같은 seed/dtype/원소 수이고 공간 shape는 다르다. hash 동일성을 요구하지 않았고 H cache/noise 파일을 가져오지 않았다. 따라서 값 hash 하나만으로 shape나 조건 계보를 판단하지 않는다. final latent는 initial noise와 다른 실제40step 결과이며 finite·원자적 저장·재로딩을 확인했다.

## 실제 시각 검토

주 에이전트가 실제 `selected.png`(사전 고정 f0/4/8/12/16)와 `all17.png`를 열어 원본 pre-crop, 실제 처리된 driving, 고정 Lab 참조, raw RGB 출력을 나란히 보았다. 별도 검토 에이전트도 착석 유지·직립 실패를 확인했다. 모든 프레임을 포함했고 피사체별 확대·좋은 프레임 선별·warp·보간·복원은 하지 않았다. 아래는 정적 시각 판정이며 실제 속도의 연속 관찰은 아니다.

| 축 | 판정 | 관측과 한계 |
|---|---|---|
| 검은 Lab 견종 외형 | PASS(정적 외형 한정) | f0~16의 검은 털·늘어진 귀·주둥이가 Lab처럼 보인다. |
| 실제 반려견 개체 | UNCERTAIN | 참조 얼굴·귀와 유사하지만 한 사진·한 출력으로 특정 개체 일치를 인증하지 않는다. |
| 넓은 가슴·몸통·굵은 사지 | UNCERTAIN | 착석 상태의 넓은 앞몸과 굵은 앞다리는 유지돼 보인다. 직립 체형과 가려진 뒷몸은 검증할 수 없다. |
| 원본의 뒷발 직립 | FAIL | 전체17장에서 앉은 자세가 남고 두 앞발은 침대 쪽을 지지한다. |
| 머리·앞발 동작 단계/타이밍 | FAIL(전체 동작 전달) | 약간의 머리·몸 위치 변화는 있으나 원본의 들어 올린 앞발/직립 단계가 전달되지 않는다. 미세한 머리 타이밍 대응은 UNCERTAIN. |
| 참조 자세·배경 누수 억제 | FAIL | 착석 자세와 침대·커튼·방 구도가 전체에 강하게 남는다. |
| source 개체 외형 누수 | UNCERTAIN | 흰 털·분홍 배 같은 명백한 색상 복사는 보이지 않는다. 체형/움직임의 잠재 누수는 이 비교로 분리 못 한다. |
| 머리·목·발·꼬리 형상 | UNCERTAIN | 정적 시트에서 머리·앞다리는 대체로 인식되지만 꼬리·뒷발·가림 부위의 정상성을 판정할 근거가 부족하다. |
| mask 경계·반사·접촉 | PARTIAL_UNRESOLVED | 기존 얇은 발/꼬리/바닥 mask 결함을 유지했다. 출력의 침대 접촉은 source 바닥 접촉 재현이 아니며 결함의 개별 기여도는 식별하지 못했다. |
| 프레임 간 외형 | UNCERTAIN | 전체 시트에서 큰 개체 교체는 보이지 않으나 소규모 얼굴·몸 위치 변화가 있다. 이를 정지 복제나 안정적 동작 성공으로 단정하지 않는다. |
| 실제 속도 시간 품질 | UNVERIFIED | MP4 decode/재생 제어 검증과 사람이 연속 재생 품질을 관찰한 것은 별개다. |

로컬 검토 페이지는 실제 브라우저에서 프레임0/16 경계·이전/다음·slider·1회 재생 종료·자동 반복 없음·모바일 overflow 없음 검사를 통과했다. 주 에이전트는 desktop 화면을 직접 확인했다. 이는 보기 도구 검증이고 연속 재생 품질 수용은 아니다.

원본 f0~16은 짧은 직립·소규모 머리/앞발 변화 구간이다. 강한 회전·윙크·킥·전체15초 안무를 평가한 것이 아니다. 두 개체/IG·윙크·킥·Kling 비교는 NOT_RUN이다. VACE와 입력·해상도·모델 조건이 달라 통제된 우월성 결론도 내리지 않는다.

## 자원과 검증의 범위

[MEASUREMENTS](MEASUREMENTS.json)와 [집계 CSV](resource_summary.csv)에 system/process/cgroup/CUDA를 구분했다. S 최소 MemAvailable51.978GiB, cgroup peak62.006GiB, 기록된 CUDA peak allocated33.831GiB다. S의 cgroup high3537, max/oom/oom_kill0, 모든 단계 swap0. high 사건은 숨기지 않으며 OOM과 동일시하지 않는다. RSS anon/file의 phase snapshot 최대는 각각31.068/31.364GiB이고 연속 관측 peak와 같다고 주장하지 않는다. 통합 메모리에서 이 회계들을 합산하면 중복 계산이다.

S CPU DiT load91.029초, device 이동7.370초, 첫 forward13.354초; D VAE load0.907초, decode6.782초, raw 저장0.696초. guarded 시간에는 준비/종료 등도 포함되며15초 비용으로 선형 외삽하지 않는다.

CPU fixture5개, critical Ruff·syntax PASS, 코드/upstream/input424개 보존 PASS. 전체 basedpyright는 NOT_CLEAN701errors/15files로 남겼다. 이를 모두 기존 오류라 주장하거나 타입 검증 완료로 포장하지 않는다. 전체 대형 weights 재해시는 이번에 반복하지 않았고 이전 검증 계보를 재사용했다.

Mac의 큰 전처리 tensor 전송은 중간에 중단돼 PARTIAL_TRANSFER로 보존했고 검토/ZIP에서 제외했다. Spark 원본은 완전하며, 검토 입력은 기존 CPU 전처리 재구성과 실제 P의4개 hash 일치로 연결했다. 실행·생성 실패는0이다.

## 해석과 다음 한 실험

현재 frozen baseline은 사진 속 외형·장면을 보존하는 데 비해 목표 직립 동작을 전달하지 못했다. 이것만으로 RGB condition이 무시됐거나 특정 mask/attention 한 곳이 원인이라고 확정할 수 없다. 체형 차이, 착석 reference, 짧은 motion, 동물 도메인·시간 prior가 함께 얽혀 있다. [한국어 수학·코드 설명](../../lessons/B-008-reference-motion-generalization.md).

다음 하나는 **원본 동물의 첫 프레임을 참조로 쓰는 RGB-driving 자기 재현 진단**이다. 같은17프레임 driving과 mask·seed·sampler를 고정하고 참조와 text를 자기 재현 과제에 맞춰 사전 등록한다. upright/앞발 단계조차 실패하면 기본 동물 motion 경로·표현의 한계를 우선 조사하고, 성공하면 cross-identity/체형 전이의 어려움을 별도 대상으로 좁힌다. 참조와 과제 text가 달라 순수 단일요인 인과효과나 Lab identity 성공을 증명하지 않는다. 이번에는 실행하지 않는다.

비공개 원본·출력·시트·최종 latent·sidecar·로그·재현은 로컬 검토 ZIP으로만 전달한다. 공개 저장소에는 개인 미디어/경로/cache/latent/weights를 올리지 않는다. 실행은 종료됐으며 추가 sampler·학습을 자동 시작하지 않는다.

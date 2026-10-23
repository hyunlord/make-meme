# B-014 결과 — 이식·실행 완료, 목표 품질 개선은 미입증

2026-10-24 KST. **ADAPTATION_PASS / SAMPLER_AND_DECODE_COMPLETED / 전신 FAIL / 국소 PARTIAL / 실제 개체 UNCERTAIN / temporal UNVERIFIED**.

공식 ALG의 세 항식을 SCAIL에 연결해 승인된 LAB_MOV_ALG 한 번을 실행했다. 40step·88forward와 최종 latent·17프레임24fps MP4를 확보했다. 그러나 전체17장 정적 검토에서 기존 LAB_MOV보다 원본 동작과 실제 개체 형태가 함께 좋아졌다는 명확한 근거는 없었다. 앉은 자세와 후기 얼굴·귀 번짐은 남았다. 일부 초기/중기 얼굴 경계가 더 읽히는 관측은 기록하되 전체 개선으로 올리지 않는다.

## 1. 고정 범위와 실제 사용량

- 시작 원격 HEAD: `152b6771397176ac0eb1860debc0902331c5d523`. 착수 기록 `0a4b25a619c3a9bdf47f57aab69e16432d994c85`, GPU 이전 코드·설정·평가 고정 `3cd90e196307fe1f663e8533124a0cbe42f8f41e`.
- 실행 manifest SHA: `71be87d69e5e10d6e7ac52219123413aa4582a3f5c4b8ec6b0816b96dc8965cb`. [설정](configs/alg.json), [코드 계보](PREREGISTERED_CODE.json), [원래 계획](PLAN.md), [사전 평가](PREREG_EVALUATION.md).
- P 재인코딩0, PROBE1/1, full sampler S1/1, D1/1. 실행 실패0·재시도0. B013 LAB_MOV/LAB_STILL은 재생성하지 않았다. 학습·LoRA·새 모델/가중치/데이터 다운로드·imagegen·외부 생성API0.
- 같은 source f7–23, 실제 Lab 사진·RED/WHITE ref mask, prompt·empty negative, seed20261022, UniPC40·shift3·CFG5, history=None, replace_flag=False,512×896·17f24fps. 모델/정밀도/attention/tinyCUDA/anchor/단계 분리/메모리 가드를 유지했다.

## 2. 수식·조건 계약은 실제로 연결됐는가

초기 i0..7은 `u_orig + 5*(c_low-u_low)`를 순차3회로 계산했다. i8..39는 원래 positive→negative 두 호출로 돌아왔다. 실제 trace는 활성24call+후반64call=88이며 scheduler update40이다. 모든 branch의 현재 noisy latent, driving·mask·CLIP는 같고 low branch의 reference VAE latent 공간축만 바뀐다. first-frame overwrite/clamp·후처리 warp는 없다. 기존 VAE/MP4의 정규화 규약은 유지했다.

공간 필터는 FP32 `[16,1,112,64]→[1,16,112,64]→45×26→112×64`, bilinear/AA=True/align_corners=False다. 원본 cache는 읽기 전용으로 남고 필터는 별도 sidecar다. [감사](ADAPTATION_AUDIT.md)는 공식 Eq.(2), 실제 Wan 구현, SCAIL 조건 결합의 차이까지 구분한다. 단순 low-low CFG로 대체하지 않았다.

CPU9개 PASS와 helper typecheck0error/0warning, 실제16leaf cache·원본/RNG 불변 검사를 마쳤다. 초기 미구현 fixture5실패와 static 진단은 수정 전 기록으로 남겼다. 기존 동적 runtime 전체 strict typing이나14B OFF/ratio1 bit-identical 재생성을 검증했다는 뜻은 아니다. [CPU 근거](CPU_VALIDATION.json).

| 값 | 실제 SHA256 |
|---|---|
| 원본 B013 조건 cache | `b7e5c62d8cb3a67e3cca0e104a536cf54c86937fa136f8554dbe55062ba9bf5d` |
| 초기 noise 값 | `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950` |
| 원본 reference 값 | `0ad957276e89e5692743ee9d8438044fe37daa48500c311746ccd949e93703c0` |
| filtered reference 값 | `40e6a0c2132cfc19f0a211a8cc654b21425e681b58cd45472656f3191454abda` |
| 최종 latent 파일 | `3d76cbc4f95e881346da2500c037d413e05e79e360f8b3ef3001d0ad2ee24594` |
| 최종 raw tensor | `542e41a1cf73afc0b9508ea8bd6abec6fb0add78811e3c0c2797bdef9e1cc3da` |
| MP4 | `5135eb5789cb245963f1cf9418805378554beb1e6c36437ed5bedad368a3b8b0` |

최종 latent는 실제 scheduler 결과 `[16,5,112,64]`, finite/readback PASS이며 initial noise와 다르다. S 종료·자원 회복 뒤 D만 적재해 finite raw `[3,17,896,512]`를 얻었다. 부모/입력/코드/sidecar426개 해시는 종료 후에도 일치했다. branch SHA는 device restore 때 실제 값을 검증하고 kwargs 선택에 맞춰 기록했으며 매 forward의 GPU tensor 전체를 다시 해시한 것은 아니다. 가중치는 이전 전체SHA와 이번 stat/mtime 대조다.

## 3. 전체17프레임 시각 관측

SOURCE/실제Lab/기존MOV/STILL/ALG 전체17장, local0/12/14/16을 보존했다. 두 agent가 A/B 라벨을 가린 시트를 먼저 보고 기록한 뒤 A=기존MOV, B=ALG를 공개했다. 같은 agent 계열이고 B013에 대한 사전 지식도 있으므로 독립 인간 blind 평가가 아니다. 보정된 관절 좌표·각도·gain·통계적 유의성은 만들지 않았다.

| 평가 축 | B013 LAB_MOV | B013 LAB_STILL | 신규 LAB_MOV_ALG |
|---|---|---|---|
| 원본 직립·든 앞발 | 착석·침대 지지, FAIL | 착석·침대 지지, FAIL | 착석·침대 지지, FAIL |
| 후기 상대 head roll | 방향·후반 순서 단서 PARTIAL | 대체로 초기 자세 유지 | 방향·후반 순서 단서 PARTIAL, 기존MOV보다 명확한 충실도 우위 미입증 |
| 얼굴·귀·주둥이 | local12–16 심한 번짐 | 비교적 안정된 초기 얼굴 | 일부 초중반 가독성 차이, local13–16 큰 번짐·재형성 지속 |
| 실제 개체·체형 | 검은Lab 인상, 후기 실제개체 UNCERTAIN | reference 닮음과 실제개체 수용 구분 | 검은Lab 인상은 남으나 실제개체 UNCERTAIN; 목/상체가 더 길고 좁게 보이는 차이를 체형 개선으로 세지 않음 |
| source 외형 누수 | 옅은 털·분홍 배의 명백한 전체 누수는 보이지 않음 | 같음 | 명백한 전체 누수는 보이지 않지만 개체 성공 증명은 아님 |
| 발·경계·접촉 | 든 앞발 전이 실패, 세부 UNCERTAIN | 세부 UNCERTAIN | 앞발 아래 지지 유지, 기존 mask PARTIAL_UNRESOLVED |
| 시간 품질 | UNVERIFIED | UNVERIFIED | UNVERIFIED |

- **local0:** 세 생성 모두 앉아 있다. ALG는 입 주변·목/머리 비율이 기존MOV와 다르다. 열린/닫힌 입을 새 필수조건으로 만들지 않았다.
- **local12:** 두 동적 결과에서 머리 반응과 얼굴 연화가 보인다. ALG 코/눈 경계가 상대적으로 더 읽힌다는 보조 관찰은 있지만 전신 자세는 그대로다.
- **local14·16:** source는 몸통 대비 오른쪽 head roll을 키운다. 두 동적 결과도 비슷한 거친 방향을 보이지만 눈·주둥이·귀가 심하게 번져 정확한 roll과 실제 얼굴 보존을 수용하지 못한다. 더 큰 움직임 자체를 성공으로 계산하지 않는다.
- **나머지0–11 및13·15:** 전부 시트에 포함해 확인했다. 입·눈·머리 높이 차이를 source의 정확한 안무로 간주하지 않았다. 좋은 프레임만 선별하지 않았다.

참조 침실을 유지하는 것은 animation 모드의 배경 의미이며 그 자체가 이번 실패 기준은 아니다. 그림자/침대 주름/접촉·원본 바닥 반사는 전경 움직임과 분리한다. 숨은 뒷다리나 물리적 접촉을 추정해 채우지 않았다. 연속 재생의 지각적 품질을 직접 관찰하지 못해 temporal=UNVERIFIED다. 브라우저 play/pause/seek/end·CJK·desktop/mobile 동작 확인은 viewer 기능 검증일 뿐 영상 품질 통과가 아니다.

## 4. 비용과 안전

| 동일 정의 | 기존 LAB_MOV | 신규 ALG |
|---|---:|---:|
| scheduler / forward | 40 / 80 | 40 / 88 |
| S guard wall seconds | 1181.602 | 1266.471 |
| S worker seconds | 1179.287 | 1262.838 |
| sampler loop seconds | 1020.890 | 1116.131 |

NFE는10% 늘었고 실제 walltime은 위와 같다. 파일 캐시·시스템 상태·관측 비용이 통제된 speed benchmark는 아니다. 새 D guard16.184초. 전체 단계의 최소 MemAvailable46.507GiB, S CUDA peak allocated33.847GiB, swap0·OOM0. cgroup high3518은 회수 압력이며 OOM과 구분한다. RSS·file charge·CUDA allocator·통합 메모리 가용량을 더해서 중복 계산하지 않는다. [실측](MEASUREMENTS.md), [실행 장부](RUN_LEDGER.md).

자체 두 unit은 inactive/PID0, 기존 Comfy 서비스와 환경은 보존했다. A는 변경하지 않았다.

## 5. 해석·제출·다음 하나

이번은 수식/코드 이식과 한 seed의 기술적 pilot 완료다. 전신 목표는 FAIL이며 유용한 motion+shape의 동시 개선은 **NOT_ESTABLISHED**다. 초기/중기 가독성 차이와 후기 손상 지속을 함께 보존한다. ALG 전체가 무효라거나 원래 실패가 고주파 하나 때문이라고 일반화하지 않는다. 이 실험은 새 알고리즘·논문 성능·상용급 품질·15초 제작 수용이 아니다.

비공개 검토물에는 raw/최종latent·재사용 규약/filtered sidecar/전체17장/native24fps 비교MP4/원본 입력·대조군/시도·실패·불확실성·trace·재현을 포함한다. 17프레임의 파일 길이17/24=0.708333초와 첫–끝 sample 간격16/24=0.666667초를 구분한다. 업스케일·보간·warp·추가생성은 없다. [재현](REPRODUCE.md), [한국어 수식·코드 해설](../../lessons/B-014-alg-and-conditional-velocity.md). ZIP 경로·CRC·SHA는 최종 DELIVERY에 별도 기록한다.

**다음 연구 하나만 제안:** 같은 고정 ALG를 LAB_STILL에 적용하는 대조군 한 번으로, 이미 있는 MOV/STILL/ALG_MOV와 함께 guidance×driving의 네 셀을 완성한다. 국소 반응/번짐 변화가 실제 동적 driving과 상호작용하는지 분리하는 진단이며 직립 개선을 약속하는 설정 탐색이 아니다. 이번에는 실행하지 않았고 별도 승인이 필요하다. 추가 seed·강도 탐색·학습·SR·모델 교체는 NOT_RUN이다.

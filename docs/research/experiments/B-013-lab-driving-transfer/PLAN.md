# B-013 — 같은 명확 동작 구간에서 실제 Lab의 MOV/STILL 전이 비교

작성: 2026-10-24 · parent: B-012 · 상태: **PLANNED / NOT_RUN**

이 문서 등록은 계획 공개이지 GPU 실행이나 예산 사용이 아니다. 사용자가 실행 담당자에게 이 의뢰서의 수행을 지시하면 아래 범위를 적용한다. B-012의 사용2/2 및 이전 실험 이력은 보존한다.

## 0. 목적과 판단 근거

장기 목표는 사용자의 DGX Spark에서 이미지·영상 생성의 모델·아키텍처·학습 메커니즘을 이해하고 개선해 높은 품질과 검증 가능한 연구 기여를 얻는 것이다. A(native imagegen-only MCP)는 별도 동결; B에는 native imagegen/유료 외부 생성/API fallback을 넣지 않는다.

검토 기준 B-012 commit `adcdd522f655802d92efc6da8927c38cd224a9b8`. RESULTS, CONDITION_COMPARISON, RUNTIME_DIFF를 직접 조회했다. 원격 기록상 source [7,24)에서 동일 reference/text/noise의 MOV는 후반 머리 roll 방향·순서에 대응하고 STILL은 초기 자세 근처였다. driving RGB latent와 mask의 양 CFG 4leaf만 바뀌고 나머지12leaf bit-exact. 이는 **해당 same-identity 한 쌍에서 동적 RGB+mask의 추가 기여**를 지지하나, 모든 동물·seed·개체 간 전이·정밀 접촉·시간 품질을 입증하지 않는다.

검토자는 업로드 ZIP을 container와 Python에서 각각 읽으려 했으나 ClientError로 실패했다. 제출 크기257,112,039bytes, SHA `215cbce3e87aa4111ce2673ea5d23d42edaece8b7b1c6bcb4173169e799d3a02` 및 CRC/525파일·Mac/Spark 동일성은 실행 담당자의 보고값이며 이번 검토의 독립 확인이 아니다. 실제 영상 시청·Spark 재실행은 하지 않았다.

**새 질문:** 동적 driving의 유용한 효과가 앉아 있는 실제 Lab 참조로 바꾼 과제에서도 남는가? 전체 직립 자세 전환과 국소 머리 roll은 따로 평가한다. Lab가 앉은 상태에서 MOV만 원본 방향으로 머리를 기울이면, 전체 목표는 실패지만 국소 조건 활용의 근거는 별도로 남긴다.

## 1. 비교 설계 — 기존2개 재사용 + 신규2개

| 참조/과제 묶음 | MOV: 실제 RGB+mask | STILL: f0 RGB+mask 반복 |
|---|---|---|
| 원본 개체의 선택 첫 프레임 | B-012 기존 결과 | B-012 기존 결과 |
| 실제 Lab 사진 + Lab용 고정 text | **신규 LAB_MOV 1회** | **신규 LAB_STILL 1회** |

주 통제 비교는 **LAB_MOV 대 LAB_STILL**이다. 두 출력의 Lab 사진·참조 마스크·positive/negative text·초기 noise·sampler·가중치는 동일해야 한다. source reference 행과 Lab 행은 reference 자세·체형·장면·CLIP/latent 및 필요한 text가 함께 바뀔 수 있다. 4셀 표를 만들더라도 순수 identity만의 2×2 요인 인과효과나 통계적 상호작용으로 주장하지 않는다.

기존 B-012 두 결과는 재생성하지 않고 same-identity 맥락 비교로 재사용한다. 이전 B-008/009의 다른 [0,17) 출력은 새 구간의 정합 대조군이 아니며, 맥락용으로만 링크한다. STATIC COPY는 필요하면 기존 B-012 파일을 그대로 사용하고 생성 모델의 STILL 출력과 구분한다.

## 2. 입력을 바꾸는 범위

- driving은 **B-012가 실제 사용한 processed source f7..23와 그때의 mask**를 해시 확인 후 그대로 가져온다. 새 구간 선정, 원본 재축소/고해상도 교체, 이전 B-006 PNG로 대체를 하지 않는다. B-012에는 기존 PNG와 최대9 gray-level 차이를 기록했으므로 비슷해 보인다는 이유로 다른 파일을 섞지 않는다.
- LAB_MOV RGB/mask17장은 B-012 MOV와 동일. LAB_STILL은 B-012 STILL과 동일한 source7 RGB와 mask를17회 반복한 영상이다. mask도 함께 정지시킨다. 같은 VAE로 실제 영상을 인코딩하며 latent 첫 slice 반복으로 만들지 않는다.
- reference는 기존 실제 검은 Lab 사진, reference mask는 B-009의 **RED foreground + WHITE background**를 읽기 전용 재사용한다. 새 사진 생성·포즈 보정·배경 삭제·새 mask edge 개선을 추가하지 않는다. RGB와 mask의 정합·해시·기존 경계 결함을 확인한다.
- animation `replace_flag=False`를 유지한다. 원본 스튜디오에 인물만 교체하는 replacement 결과라고 요구하지 않는다. 참조 침실이 유지되는 것 자체와 착석 유지 실패를 구분한다.
- positive text는 B-012의 관측된 동작·카메라 설명을 기반으로 Lab의 실제 검은 털/넓은 몸통·귀 등과 충돌하는 부분만 과제에 맞춰 **생성 전에** 고정한다. 필요하면 장면 설명도 수정 이유를 기록한다. 두 Lab 조건의 text는 완전히 동일. source 동물의 옅은 털·작은 체형 지시를 남기지 않으며 보이지 않는 킥·윙크·3D 회전을 추가하지 않는다. 기존/새 prompt diff와 T5 token length를 남긴다. 이 text 변화가 있어 source/Lab 간 차이를 순수 reference 효과로 부르지 않는다.
- 기존 processed W512/H896,17frames24fps, sample times local t/24와 source indices7..23 유지. frame duplication은 명시한 STILL 입력/STATIC COPY에만 사용하며 결과를 보간하지 않는다.

## 3. 고정 실행과 예산

정상 SCAIL2 upstream·checkpoint, FlashAttention binary, mixed BF16/FP32 staged loader, tiny CUDA copy/add/sync/readback·64-byte anchor, P→PROBE→S→D fresh-worker 분리와 latent 저장을 유지한다. 새 CUDA/직렬화 감사·전면 refactor·MCP/state machine은 만들지 않는다.

- seed20261022 / UniPC40steps / shift3 / CFG5 / negative empty / history=None / optional LoRA와 enhancer OFF.
- 신규 full sampler **최대2회(실패 포함)**, LAB_MOV1회·LAB_STILL1회. 각 조건의 P/PROBE/S/D 최대1회, 자동 재시도0. Lab용 새 P cache 필요; source reference cache 전체를 재사용하지 않는다.
- 첫 출력이 착석이거나 품질이 나빠도 기술·안전 문제가 없으면 STILL까지 수행해 비교를 완료한다. 실제 자원 가드 위반·조건 불일치·작업 충돌이면 다음 단계를 중지한다.
- 총 작업 상한4시간. 새 모델/대형 데이터 다운로드0, 학습·LoRA update0, imagegen/외부 생성API/유료GPU0, 업스케일·보간·얼굴복원·warp·새 seed·프롬프트 탐색0.
- 기존72GiB 시작/24GiB 실행 headroom·swap0·cgroup·타 서비스 보호를 유지한다. 다른 프로세스 종료, sudo/driver/reboot/swap/clock/drop_caches/가드완화 금지. GPU-heavy 작업 순차1개.

## 4. 조건 검증은 두 수준으로

### Lab pair 내부

B-012의 양 CFG `pose_latents` 및 `driving_masks` 4변경/나머지12보존 comparator를 가능한 그대로 사용한다. 두 Lab case에서 reference RGB latent/mask·CLIP·positive/negative text·noise/RNG/scheduler가 같아야 한다. noisy/mask/schedule exact, encoder float 허용오차는 사전 고정하고 실제 exact 여부를 함께 기록. runtime tree의 위치로 비교하고 key 번호만 믿지 않는다. 예기치 않은 차이를 검사 삭제로 우회하지 않는다.

### B-012 대비

각 Lab case의 driving RGB/mask 입력 해시는 대응하는 B-012 case와 exact. 기존 tensor가 실질적으로 같은 실행/encoder 계약이면 driving latent·mask, actual noise/shape·negative·RNG/schedule을 대조한다. source→Lab에서는 ref latent2·ref masks2·CLIP2·positive text1의 변경을 허용·예측하며, reference-mask shape가 같다는 이유로 값까지 같아야 한다고 검사하지 않는다. 단순히 model 전체를 다른 dtype/새 버전으로 올리지 않는다.

실제 기대 변경 집합·config·input SHA를 P와 S 사이에 검증한다. 동일 seed만으로 GPU byte-identical 결과를 보장하지 않는다. 최종 latent와 cache의 shape/dtype/finite·value hash·provenance를 원자 저장하고 재읽는다. D 실패 시 S 재실행 금지.

## 5. 사전 사건과 품질 평가

새로운 관측 구간을 찾지 않는다. B-012의 local0/12/14/16 (source7/19/21/23) 사건과 **전체17프레임**을 유지한다. 원본의 전면 몸통에 대한 후반 머리 roll 증가·방향·순서가 주 동작 단서다. source 복사와 Lab의 서로 다른 몸 형태 때문에 절대 pixel landmark 일치를 주 지표로 삼지 않는다.

평가를 다음으로 나눈다.
1. **전신 자세 전이:** source 뒷발 직립과 들어 올린 앞발 배치를 재현하는가, 아니면 Lab reference의 착석이 고정되는가.
2. **국소 동작 제어:** LAB_MOV에서 원본 후반의 머리 roll 증가·방향·순서가 LAB_STILL보다 대응하는가. 앉은 채로만 머리를 따라가도 이 항목의 부분 근거와1의 실패를 동시에 기록한다. 화면 전체 회전/zoom으로 생긴 변화와 구분한다.
3. **개체/체형:** 견종 유사성과 실제 반려견 일치를 구분. 검은 털·귀·얼굴·주둥이·넓은 가슴·굵은 사지, source의 옅은 색·가는 체형 누수, 머리 roll 때 얼굴 무너짐을 별도 기록. 개체 정체성 보존을 외모가 검다는 이유로 PASS하지 않는다.
4. **시간/세부:** 17장 모두 coverage·형상·가림·발·반사·경계 확인. 정밀 앞발/접촉·숨은 관절은 UNKNOWN일 수 있다. 움직임 크기/저flicker만으로 성공하지 않는다.

눈 중심선과 몸통 방향을 안정적으로 읽을 수 있을 때만 2D 상대 roll 및 f0 대비 변화를 보조로 표시한다. 부위를 source에 맞춰 사후 warp/scale/time-align하지 않는다. 점 위치가 불확실하면 방향·이벤트 순서를 주로 보고 각도·gain·통계적 유의성은 만들지 않는다. 같은 한 seed/17frames를 독립 표본으로 세지 않는다.

가능하면 두 Lab output을 A/B로 가린 동일 크기 패널에서 관측한 뒤 대응표를 확인한다. source를 본 동일 에이전트의 판독을 독립 인간 blind 평가로 부르지 않는다. 실제 연속 재생을 관찰하지 못하면 temporal=UNVERIFIED. HTML play 테스트·ffmpeg decode는 연속 품질 수용이 아니다.

제출 비교: SOURCE + Lab reference + LAB_MOV/LAB_STILL의 전체17장과24fps MP4, B-012 source MOV/STILL을 재사용한4셀 보기. 각 조건을 같은 canvas로 표시하고 좋은 프레임만 고르거나 미용 후처리하지 않는다.

## 6. 해석·수학·다음 가설

한국어 lessons/B-013-cross-identity-driving.md:
- v_theta(z_tau,tau;c_ref,c_drive,c_text,c_mask)에서 driving pair를 개입한 Lab 내부 비교와 reference/task 묶음이 달라진 source/Lab 맥락 비교를 구분한다. noise time tau와 frame time t를 구분.
- 같은 Lab 조건에서 Δ_drive는 '두 출력이 다르다'가 아니라 사전 source 사건을 어떤 쪽이 더 잘 재현하는가라는 질문이다.
- 조건 사용과 전체 목표 수용은 다르다. 국소 머리 동작 성공/전신 pose 전환 실패가 동시에 가능하다. 관절 retarget·latent conditioning의 어떤 연구 가설이 이어질 수 있는지 설명하되 이번 실험으로 attention 원인이나 정보 분리를 확정하지 않는다.
- 실제 P 텐서 shape와 양 CFG의 시각 조건 공유를 코드로 연결한다. CFG를 그냥 높이면 motion만 강화된다고 가정하지 않는다.
- 한 pair의 탐색 근거, 여러 seed/동작·개체에서 일반화, 새로운 방법의 학습 기여를 분리한다. 이번은 학습0인 baseline.

결과 후 다음 작업 하나만 제안한다. 전신 자세와 머리 roll이 모두 잘되면 새 seed/미사용 동작 검증을 우선. 앉은 채 머리만 대응하면 coarse pose 전환과 local control의 분리 가설을 검토. Lab 두 조건 모두 초기 자세에 고정되면 reference/task 의존성을 다룰 모델 조건화 개입 하나를 선행 연구와 비교한다. source/Lab prompt 차이를 무시해 identity 하나를 원인으로 확정하지 않는다. 다시 색상·seed·설치·구간선정만 무한 반복하지 않는다. 이번에 low-pass/adapter/LoRA/SR/해상도 변경을 적용하지 않는다.

## 7. 별도 hook 경고

B-012 최종 사용자 로그의 `unsupported plugin entry type: .../node_modules/.bin/codegraph`는 먼저 **TOOLING_WARNING**으로 분리한다. 문자열과 경로는 플러그인 로딩/파일 유형 검사 문제를 시사하지만 실제 entry가 symlink인지·검사 규칙·hook 종류는 미확인이다. 생성 런 실패나 CUDA OOM으로 재분류하지 않는다. 기존 artifacts/remote commit/exit receipt가 완료됐는지 확인하면 결과 보존 가능하다.

필요하면 CPU 읽기 전용 lstat/readlink와 플러그인 manifest·해당 hook 실행 로그를 제한적으로 기록한다. 개인 경로·계정 ID·secret은 공개하지 않는다. plugin 전체 삭제, broad security hook disable, 임의 symlink-follow 우회, GPU 환경 업데이트는 이번 범위가 아니다. 다음 실행을 실제 차단하면 미해결 도구 오류로 명시하고 필요한 최소 해결 하나를 별도 제안한다. hook 경고만으로 완료한 영상 실험을 재생성하지 않는다.

## 8. GitHub·보존·완료

시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL, B-012 결과/코드와 B-009 참조 provenance를 읽고 원격 HEAD와 git status를 확인. public 문서 branch와 local 실행 checkout이 같은 파일이라고 가정하지 않는다. 계획·기대 변경·Lab prompt·입력·코드/config를 생성 전에 커밋한다.

HISTORY.md/ROADMAP.md에 B-012의 한-pair 근거와 B-013의 목표·범위·상태를 연결하고 시작/중요 실패/종료를 기록한다. 종료 후 RESULTS, CONDITION_COMPARISON, SOURCE_LINEAGE, 실행·자원 장부, 재현, 한국어 해설을 비민감 코드와 함께 commit/push하고 remote SHA를 확인한다. 생성 성공과 lint/type-clean을 혼동하지 않으며 기존 정적 부채는 숨기지 않는다. 복잡한 CI/state machine을 새로 만들지 않는다.

개인 사진/영상/좌표/마스크/조건cache/latent/weights/개인절대경로/토큰을 공개하지 않는다. 비공개 ZIP은 기존 /tmp/ 전달 방식으로 Mac/Spark 위치·CRC/manifest/SHA·바이트 동일성을 확인하고 모든 실패도 포함한다. 대형weights는 제외한다. 실제 latent·raw·MP4와 필요한 비교·재현을 보존한다. 자체 process 종료를 확인하고 한 pair 후 멈춘다. 추가 생성·학습은 자동 시작하지 않는다.

# B-009 — 참조 마스크의 배경 가시성 조건을 분리하는 1회 비교

작성: 2026-10-23 · parent: B-008 · 상태: **PLANNED / NOT_RUN**
계획 공개 자체는 GPU 실행이 아니다. 사용자가 이 의뢰서의 수행을 실행 담당자에게 지시한 경우에만 아래 한정 예산을 적용한다.

## 0. 목표와 방향 변경의 근거

B-008@0113a12f89d17665d0c5a3577e69ab19ae5eb29f는 P→PROBE→S→D로 Lab 17프레임 영상을 만들었으나, 출력 전반에 참조의 착석 자세가 남고 원본의 직립·들어 올린 앞발을 재현하지 못했다. 시스템 실행 성공과 동작 전이 성공을 분리한다. A는 동결하고 B의 이미지·영상 생성 메커니즘 연구를 계속한다.

검토자는 업로드 ZIP 한 벌의 CRC·255개 파일 길이/SHA를 직접 확인하고, 전체17 출력 및 원본/참조 비교 시트를 보았다. Spark 재실행·Mac/Spark 직접 연결·실제 속도 연속 재생은 하지 않았다.

추가 확인:
- B-008의 generate 호출은 `replace_flag=False`(animation).
- 실제 reference mask는 RED 113,928 pixels + BLACK 344,824 pixels, WHITE 0이다.
- 저장된 조건의 양 CFG branch `ref_masks`는 [28,6,112,64]이고 white 채널은 모두0. 첫 reference plane의 red 평균은0.24834333147321427.
- 기존 H의 성공한 공식 animation_001은 reference WHITE background, driving BLACK background였다(B-007E INPUT_AUDIT).
- 고정 SCAIL README는 BLACK=해당 위치의 배경 비가시, WHITE=배경 가시, color=개체 대응이라고 명시한다. 이는 binary alpha mask가 아니라 의미 조건이다. official scail.py는 RGB reference를 mask로 곱해 제거하지 않고 VAE encode와 mask encode를 별도로 수행한다.

**이 차이가 착석 실패를 일으켰다는 것은 아직 가설이다.** Black reference background가 모든 상황에서 잘못됐다는 주장도 하지 않는다. 다만 새 개체/자세/배경/text를 함께 바꾸는 자기 재현보다, 관측된 입력 계약 차이를 한 번 분리하는 것을 우선한다.

질문: **reference RGB와 모든 조건을 고정하고 reference mask의 BLACK 배경만 WHITE로 바꾸면 원본 직립·앞발 동작의 전달이 달라지는가?**

## 1. 단일 개입과 대조군

- 기존 대조군: B-008의 Mref-black 결과를 재사용한다. 재생성하지 않는다.
- 신규: 같은 reference mask의 정확한 BLACK [0,0,0] 픽셀만 WHITE [255,255,255]로 바꾼 Mref-white.
- RED [255,0,0] 전경의 위치·면적·shape·픽셀을 모두 보존한다. reference RGB를 흰색으로 지우는 작업이 아니다.
- RGB reference/driver, driving mask의 BLACK 배경과 RED 전경, prompt/negative, 모드, seed, scheduler, 정밀도, 해상도, 프레임 수, FPS를 그대로 유지한다.
- 변경 마스크의 pixel count와 red 전경 equality를 CPU로 확인. 예상치와 다르거나 다른 palette가 나타나면 기존 자산을 덮어쓰지 말고 차이를 기록한다.
- 새 segmentation·새 동물 사진·crop 수정·전경 recolor·mask 경계 보정·replace_flag 전환을 함께 하지 않는다. 기존 얇은 발/꼬리/반사 결함은 PARTIAL로 보존한다.

## 2. 실행 상한과 성공 경로 보존

Lab P 1회 → PROBE 1회 → S full sampler 1회 → 해당 final latent D 1회. 실패 포함 각 최대1회, 재시도0. 최대3시간. 새 모델/가중치 다운로드0, 학습/LoRA0, imagegen/외부 생성 API0. 공식 인간 예제 재실행0.

기존 성공한 H/B-008의 단계 분리, tiny CUDA 선행 연산과64-byte anchor, mixed BF16/FP32 staged loader, 고정 checkpoint·upstream·FA를 재사용한다. CUDA/직렬화/전역 환경 감사를 반복하거나 새 framework/MCP를 만들지 않는다. 기존24GiB headroom, swap0, 단일 무거운 GPU 작업 및 타 서비스 보호 정책 유지. OS/driver/swap/clock·전역 cache 삭제·다른 프로세스 종료 금지.

설정: width512/height896,17frames,24fps, seed20261022,40steps UniPC,shift3,CFG5,history=None,replace_flag=False,LoRA/enhancer OFF. 기존 Lab prompt를 그대로 사용한다. 새 모델 다운로드·학습·prompt sweep·seed 탐색 없음.

원본의 source f0..16과 출력 시간축을 유지한다. 공식 README는 mixed resolutions/fps 학습을 명시하므로, writer 기본16fps를 고정된16fps 학습 분포로 해석하지 않는다. 이번 실험에서 FPS를 바꾸지 않는다.

## 3. 실제 조건 텐서의 통제 확인

기존 B-008 input/config/condition/final/output 계보를 보존하고 신규 폴더/experiment ID에 기록한다. 새 P는 변경된 참조 mask를 실제 encode해야 한다. 기존 조건 캐시에 사진을 바꾼 척하거나 receipt 검사를 제거하지 않는다.

검증 기대:
- 새 initial noise는 B-008의 실제 값·dtype·shape·RNG 계약과 동일.
- text/CLIP/reference RGB latent/driving RGB latent/driving mask/history/scheduler는 동일 설정에서 같은 의미와 형태를 유지.
- 양 CFG branch의 reference mask prefix에서 WHITE 가시성 channel만 바뀌고 RED 및 나머지 색상/영상 부분은 보존되는지 pinned `extract_and_compress_mask_to_latent`의 실제 출력과 대조.
- RGB reference는 바뀌지 않으므로 reference latent 자체가 달라지는 것이 실험 의도가 아니다.
- 같은 seed가 무조건 GPU bit-identical을 보장하지는 않는다. 비교 기준/허용오차는 결과를 보기 전에 등록한다. 예상 밖의 큰 텐서 변화가 있으면 대조 유효성을 먼저 판정하고 원인을 숨기지 않는다.

성공한 출력 보존 규약대로 final latent를 S 종료 전에 원자 저장·검증한다. D 실패에도 latent 보존; S 자동 재실행 없음. 기존 결과·weights의 전체 재해시를 매번 다시 강제하지 말고 불변 계보와 실제 변경 입력/코드를 우선 검사한다.

## 4. 평가 및 기각 기준

원본 processed driving / B-008 / B-009를 native24fps와 고정 f0/4/8/12/16 및 전체17프레임으로 비교한다. 업스케일·warp·보간·좋은 프레임만 선별·얼굴 복원 없음.

주 평가: 뒷발 직립, 앞발의 위치·들림, 머리/몸의 시간별 변화와 원본 단계의 대응. 검은 Lab 견종 유사성과 실제 개체 일치를 구분한다. 특정 개체 판정은 불확실하면 UNCERTAIN. 단순 motion magnitude나 몸이 흔들리는 것을 안무 성공으로 보지 않는다.

보조 평가: 얼굴/귀/주둥이/가슴·사지 체형, 원본 개체 외형 누수, 경계/반사, 참조 자세에 고정됨, 실제 속도 시간 품질. 미관찰 temporal=UNVERIFIED.

**배경 판정:** 이 실험은 animation이며 Mref-white는 참조 배경을 visible로 지시한다. 따라서 침실이 남는 것 자체를 이번 개입의 FAIL로 판정하지 않는다. 원본 스튜디오 배경에서 개체만 교체하는 최종 응용은 replacement라는 별도 계약이다. 이번에 replace_flag를 동시에 바꾸지 않는다.

해석:
- 자세 전달이 개선되면 이 특정 입력의 reference mask 가시성 조건이 결과에 영향을 준 근거. 전체 동물 일반화나 유일 원인 입증 아님.
- 여전히 착석이면 WHITE 조건만으로 충분하지 않음. reference-pose 분리/동물 motion/구도 차이 등은 아직 남는다. 이 결과를 모델 전체의 능력 부재로 일반화하지 않는다.
- 배경만 달라짐은 동작 성공이 아니다.

## 5. 자기 재현 진단을 나중에 할 경우의 함정

B-008 제안인 source 첫 프레임 reference 진단은 보류 후보로 보존한다. 이 프레임이 이미 직립이므로 그 자세의 복사만으로 upright PASS를 받을 수 있다. 이후 실행한다면 **first-frame-repeat 정적 대조군(새 생성 없음)**을 만들고, 출력의 움직임 방향·위상·시간을 source와 비교해야 한다. 원본17프레임 변화가 판별하기 작으면 INCONCLUSIVE로 남긴다. reference와 text를 바꾼 진단을 순수한 단일요인 또는 Lab identity 성공으로 주장하지 않는다. B-009 이후 자동 수행하지 않는다.

## 6. 이번 연구·수학 학습

한국어 `lessons/B-009-semantic-mask-conditioning.md`:
- RGB alpha masking과 semantic mask conditioning의 차이.
- pinned 함수의 threshold와 white/red/... 7개 channel, 시간 패킹4×7=28, area downsampling이 어떤 정보를 전달하는지.
- BLACK은 seven-channel zero, WHITE는 배경 channel 활성화이며, 이를 branch-off/무조건 생성과 혼동하면 안 되는 이유.
- v_theta(z_t,t,c_ref,c_drive,c_mask,c_text)에서 c_mask만 변경하는 비교의 의미와 한계.
- animation/replacement의 과제 차이 및 reference-copy 정적 대조군이 자기 재현 평가에 필요한 이유.
- 직관→식→실제 helper/텐서→관측→반례·질문/별도해설. 새 방법이나 논문 독창성은 아직 주장하지 않는다.

## 7. 기록·최종 제출

CHARTER/AGENTS/RECORDING_PROTOCOL와 현 HEAD·worktree 상태를 확인한다. 시작 전 PLAN·코드/config/mask 해시를 고정하고 HISTORY/ROADMAP에 이 우선순위 변경 이유를 기록한다. 종료 후 RESULTS·실측·학습문서·재현·HISTORY/ROADMAP commit/push, remote SHA 확인. 기존 기록은 append-only이며 연구 branch만 사용하고 force push/main 직접 변경 금지.

공개: 비민감 코드/문서/지표/해시. 비공개: 반려동물 RGB·mask·원본/출력·조건/latent·개인 경로·가중치·토큰. 비공개 ZIP에는 비교MP4·전프레임 시트·final latent·검증/재현을 넣고 weights 제외. Mac/Spark 경로·전송 여부·CRC/manifest/hash를 구분한다.

최종에는 actual execution/quality/temporal 상태, 사용한1회 sampler, 가장 중요한 한 관찰과 다음 한 실험만 제안하고 멈춘다.

## 고정 근거

- make-meme@0113a12f89d17665d0c5a3577e69ab19ae5eb29f: B-008 RESULTS/INPUT_AUDIT/phase_prepare/configs, B-007E INPUT_AUDIT.
- zai-org/SCAIL-2@78fe19576bb06be96c2375e088574a262a300edb: README Mask Semantics/Usage/Checkpoints, wan/utils/scail_utils.py, wan/scail.py.
- 업로드 B-008 ZIP SHA256: 53c3160a391dcfa7cdf9dfb3c4d722c55bffb99374c53ac78022a32f8c464c9d. 독립 검토는 해당 업로드 한 벌에 한정한다.

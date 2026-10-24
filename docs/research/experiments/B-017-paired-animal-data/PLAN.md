# B-017 — 동물 개체·자세 분리 학습을 위한 데이터 계약과 소형 실제 샘플

작성: 2026-10-24 · parent: B-016 · 상태: **PLANNED / NOT_RUN**

이 문서는 다음 작업의 제안이다. GitHub 등록은 데이터 수집·학습·GPU 실행이 아니며, 실행자가 사용자의 수행 지시를 받으면 아래 범위를 따른다.

## 0. 왜 이 단계로 전환하는가

B-012의 same-identity MOV/STILL에서는 후반 상대 머리 roll의 제한된 제어 근거가 있었다. B-013의 실제 Lab에서는 착석이 남고 MOV에서 후기 얼굴·귀 손상이 나타났다. B-014/015의 고정 ALG는 목표 품질 개선을 입증하지 못했고 종료됐다. B-016의 animation 유지+reference RoPE H0→120은 실제 연결·40step80forward를 통과했으나 착석·후기 손상을 해결하지 못했다.

검토 기준 commit은 `dd98d1f226b72e9701bcc12d530c032c3683e9cd`다. 원격 RESULTS와 MODEL_PATCH.diff를 확인했으며 Spark 재실행은 하지 않았다. 업로드 B-016 ZIP은 이번 검토자의 container와 Python 모두 ClientError로 열지 못했다. 크기150,796,636bytes, SHA `1fe40f6821cd04f76ee82389e107d2e41196578be7cb5f8e6384cfa37c88e3a7`, CRC/363payload/양호스트 동일성은 실행 담당자 보고값으로만 인용한다.

결론은 **현재의 두 inference 개입이 충분하지 않았다**는 것이며, 학습 데이터 부족이 유일한 원인·학습이 반드시 해결책·모델이 모든 동물에 불가능하다는 결론은 아니다. 무제한 ALG/offset sweep 대신 다음 학습 가설의 입력과 정답부터 확인한다.

연구 질문: reference의 개체 외형은 필요하지만 reference 자세나 driving의 외형을 그대로 복사하는 것으로는 loss를 낮출 수 없는 훈련 예제를, 현재 허용된 자료에서 만들 수 있는가?

이번 산출물은 문헌 목록만이 아니다. **실제 자산 목록·권한 상태, R/D/Y 예제 manifest, 가능한 경우 실제 최소 case, CPU loader 검증, 다음 학습 pilot의 정확한 범위**를 남긴다. 존재하지 않는 정답은 만들지 않는다.

## 1. 범위와 종료 기준

- A와 모든 과거 B 결과·환경·모델·캐시는 보존한다. ALG OFF·H0의 기존 baseline을 향후 학습 비교의 기본 후보로 둔다. B-016 파일을 수정하거나 활성 환경에 patch를 잔존시키지 않는다.
- 총 최대3시간. 기존 허용된 연구 자료 검토60분, 공식 문헌/입력 계약 검토45분, 소형 실물 구성·CPU 검증·기록75분을 기준으로 하되 전체 범위를 늘리지 않는다.
- **신규 diffusion/imagegen/외부 생성API0, optimizer update0, 전체 모델 로드0, 새 대형 모델·영상 데이터셋 다운로드0.** GPU 인코딩/LoRA backward는 다음 별도 실험이다. 기존 CPU 영상 decode·crop·타임스탬프 확인·manifest/fixture 작성만 허용한다.
- 외부 자료는 공개 README·논문·라이선스·소형 메타데이터만 읽는다. 접근 신청서 제출·이메일·계정 가입·유료 서비스·우회 수집은 하지 않는다.
- 데이터가 부족하면 필요한 자산 종류와 누락 필드를 정확히 보고한다. 무관한 자료를 모아 채우거나 근거 없는 합성 target을 만들지 않는다. 같은 실패 입력으로 새 샘플링을 추가하지 않는다.

## 2. R/D/Y 계약부터 정의

각 예제는 최소 `(R,D,Y,M_R,M_D,text,mode,provenance)`다.

- R: 목표 개체의 실제 reference image. 실제 identity와 pose/state evidence를 구분한다.
- D: 따라갈 motion을 제공하는 driving sequence. 개체ID·타임스탬프·motion event를 명시한다.
- Y: supervised target video. 실제로 존재하고 사용 범위가 확인된 영상이다. 학습 loss의 정답이다.
- M_R/M_D: 해당 입력에서 만들어진 correspondence/environment masks. target의 미래 실루엣·pose를 몰래 생성 조건으로 추가하지 않는다.
- text: **Y에 실제로 나타나는 개체·행동·장면**을 서술한다. Lab reference와 다른 개체 target을 Lab라고 적지 않는다.
- mode: animation의 reference environment 또는 replacement의 driving environment와 Y가 맞는지 확인한다. background/camera가 어긋나는데 aligned ground truth라 부르지 않는다.

구분할 세 수준:

1. `SELF_RECON_SMOKE`: R은 같은 개체의 다른 시점, D=Y 또는 거의 같은 영상. pipeline/gradient/작은 overfit 확인에는 사용할 수 있으나 clean driving에 target 외형과 pose가 이미 있으므로 reference를 무시하는 shortcut이 가능하다. cross-identity 분리 학습의 증거가 아니다.
2. `SAME_ID_POSE_VARIATION`: 같은 목표 개체의 서로 다른 자세 R_a/R_b와 같은 Y. reference가 target 첫 프레임과 같은지, target 구간 밖인지, camera/조명/배경의 잔여 차이를 기록한다. D=Y이면 첫 수준의 shortcut은 그대로 남는다.
3. `CROSS_ID_MOTION_PAIR`: R과 Y는 목표 개체A, D는 외형이 다른 개체B, D/Y는 같은 motion의 방향·event·타이밍을 갖는다. 체형이 다르면 픽셀/관절 절대좌표 동일성이 정답은 아니다. 반대로 모두 '걷기'라는 행동 label만 같은 임의 두 영상을 aligned pair로 보지 않는다.

사진 여러 장만 있으면 identity/image 학습 후보이지 target motion video가 있는 것이 아니다. 실패한 Lab 생성 영상을 positive target으로 승격하지 않는다. 기존 source 원본의 다른 강아지를 실제 Lab의 정답으로 부르지 않는다.

## 3. 실제 자산 inventory와 사용 범위

기존 manifest에 등록된 연구 root와 사용자가 제공한 자료부터 확인한다. 최대30개 관련 source를 우선 조사하며 개인 홈 전체·새 클라우드 계정을 검색하지 않는다. owner-provided media와 제3자 밈 원본을 구분하고, 사용자 제공 사실만으로 공개 재배포 권한이 있다고 간주하지 않는다.

private inventory 항목:
`asset_id, local_alias, source_hash, media_kind, width,height,frame_count,fps,timebase, identity_evidence, session_id, source_video_id, motion_coverage, rights_basis, permitted_use, redistribution, synthetic_origin, prior_experiments`.

rights는 private research/training/redistribution/commercial 여부를 독립적으로 기록한다. 미확인 범위는 UNKNOWN/PENDING이다. 연구 실험 입력으로 사용했던 영상이라고 dataset publication 권한까지 확인됐다고 쓰지 않는다. 권한이 명확하지 않은 자산은 학습-ready에서 제외하고 검토용 목록에 남긴다.

새 반려견 촬영이 필요하면 자연스러운 고개 움직임·걷기·앉기 등 필요한 coverage를 제시하되, 실제 반려견을 억지로 직립/춤추게 하라는 지시를 만들지 않는다. 현재 목표의 의인화된 춤과 자연 동작 데이터 사이의 domain gap을 명시한다.

## 4. 공개 후보는 세 갈래만 확인

공식 근거와 실제 접근 가능성/terms를 기록한다. 이 단계에서 대량 다운로드나 접근 신청을 대신 수행하지 않는다.

- **SCAIL MotionPair**: 공식 README가 access form과 terms 동의를 요구한다. repo 코드의 Apache 라이선스를 데이터 사용 허가로 대체하지 않는다. 동물 pair 비중·실제 이용 범위·동작/개체 메타데이터는 확인된 것만 기록한다.
- **APT-36K 또는 APTv2**: pose/tracking 후보. 공식 정의는 clip마다15개 선택 frame이며 연속17frame24fps와 동일하지 않을 수 있다. 개체 추적ID는 clip을 넘어 동일 생물학 개체를 보장하지 않는다. pose annotation만으로 cross-identity target이 존재하는 것으로 간주하지 않는다.
- **기존 소유/승인 자료**: reference와 target의 identity/scene를 직접 확인할 수 있는 우선 경로. Lab의 다른 자세 사진·영상이 실제 없으면 없다고 보고한다.

AP-10K 같은 정지 이미지 자료를 참고할 경우 motion video가 아닌 보조자료로만 분류한다. 후보 수나 clip 수를 과장하지 않는다.

## 5. 실제 작은 case를 구성한다 — 가능한 수준을 표시

현재 권한·실물이 확인된 자료에서 최대8개 case를 만든다. 8개가 필수 합격 숫자는 아니다. true paired case가 없으면 0으로 명시하고, 별도 smoke fixture와 구분한다. 가능한 최소1개 실제 SELF_RECON_SMOKE라도 실제 decode/타임스탬프/참조가 다른 시점인지 확인해 구성하되 이것을 전이 데이터 PASS로 승격하지 않는다.

reference는 가능하면 target 구간 밖의 다른 자세를 선택하고, 실제 관측 가능한 pose gap을 기록한다. 같은 Y에 R_a/R_b를 사용할 수 있는 경우 같은 source_group을 부여해 같은 split에 둔다. 서로 다른 R/D/Y 영상 사이의 event alignment가 불명확하면 weak_pair로 분류하며 임의 retiming/보간으로 GT를 만들지 않는다.

case 계약은 공식 SCAIL training README의 `GT.mp4`, `rendered_v2.mp4`, `rendered_mask_v2.mp4`, `ref.jpg`, `ref_mask.jpg`, `prompt.txt`에 대응시킨다. 기존 파일 copy/symlink/hash 방식으로 원본을 보존한다. 새 VAE cache나 모델 infer를 실행하지 않는다. 마스크가 없어 공식 case까지 완성할 수 없으면 missing_fields를 기록하고 CPU schema fixture까지만 수행한다.

**train/val/test를 프레임 무작위 분할하지 않는다.** identity/session/source-video와 모든 derivative parent를 그룹으로 묶는다. 같은 개체 unseen-motion 평가와 unseen-identity 평가를 구분한다. 개체 한 마리·clip 한 개뿐이면 independent test 없음으로 보고한다. 지금까지 반복 본 source f7~23과 Lab 결과는 development/regression set이며 새 held-out benchmark로 재명명하지 않는다.

## 6. shortcut·누수 검사와 CPU 테스트

검증기는 소형 스크립트면 충분하다. 새 데이터 플랫폼/상태관리체계를 만들지 않는다.

- ref/driver/target의 실제 파일 존재·decode, shape·fps·원본 sample times·길이를 검사한다. sparse15frames를17frames로 복제해 연속동작이라고 보고하지 않는다.
- pixel hash가 다른 것과 semantics가 다른 것은 별개다. D=Y hash/decoded equality, R=Y첫프레임, 시간중첩, source_group split교차를 표시한다.
- 같은 species/breed를 같은 identity로 취급하지 않는다. 서로 다른 개체의 reference와 target을 의도적으로 섞은 invalid fixture를 잡는다.
- seed나 mask ID가 같다는 것으로 R/Y identity 일치를 보장하지 않는다.
- RGB grayscale/blur/color-jitter로 D를 바꾸더라도 몸통형태·장면 단서는 남는다. 그런 pair는 약한 augmentation이지 true cross-ID ground truth가 아니다.
- target이나 미래 frame을 참조의 추가채널에 몰래 넣지 않는다. training label로 Y를 쓰는 것과 추론조건에 Y를 누출하는 것을 구분한다.
- 실제 frame 정밀 annotation이 어렵다는 이유로 같은17장 주석 감사만 반복하지 않는다. 누락은 누락대로 보고한다.

private manifest 필드:
`sample_id,pair_type,R,D,Y,identity_R,identity_D,identity_Y,identity_evidence,motion_id,event_times,reference_pose,target_pose,scene_id,mode,fps,timestamps,masks,caption,permission_id,origin_group,split,leakage_flags,readiness,missing_fields`.

## 7. 합성 pair 경로는 설계만 — 새 영상 생성0

SCAIL 논문의 reverse-driving은 합성된 다른 개체 영상을 D로 쓰고 실제 원본을 Y로 쓰는 구성이다. 본 방법을 새 아이디어라고 주장하지 않는다. 원논문의 외부 이미지/API pipeline을 우리 B에 자동 도입하지 않는다.

후속 선택 후보는 (a) 허가된 paired data, (b) local-only generator로 motion-preserving D를 만드는 역방향 pair, (c) 허가된 rig/asset으로 같은 event를 두 체형에 retarget한 render pair다. 생성 오류·motion mismatch·renderer domain gap·asset license와 비용을 각각 기록한다. 실패한 현재 모델로 만든 D가 motion을 잃었다면 pair로 채택하지 않는다. synthetic target은 REAL_GT와 분리하며 기존 생성 실패를 정답으로 재사용하지 않는다.

후속 하나를 고를 때 실제 data access·motion coverage·copyright/terms·Spark 비용·평가 split의 근거가 있어야 한다. 원본에 Lab의 직립 정답이 없다는 사실은 기록하지만 전체 연구 불가능으로 확대하지 않는다.

## 8. 학습 메커니즘과 실제 공식 인터페이스 연결

공식 Wan branch의 cache_scail2_wds.py와 SAT branch의 dataset/train/loss 경로를 읽기 전용으로 조사해 revision을 고정한다. 현재 inference branch를 checkout/upgrade하거나 학습 dependency를 설치하지 않는다. 공식 코드에 adapter/LoRA 경로가 없으면 있다고 가정하지 말고 추가 구현 범위를 기록한다.

공식 필드 `video_pth`(target), `smpl_render_downsample`(driver), `ref_frame_pth`, `first_frame_pth`, latent masks가 실제 train forward에 어디 들어가는지 표로 정리한다. 특히 `first_frame_pth`의 의미와 참조·history/dropout 규칙을 실제 코드에서 확인한다. 추론 cache16leaf를 그대로 supervised target dataset으로 쓸 수 있다고 가정하지 않는다.

한국어 lessons/B-017-paired-data-and-flow-training.md:
- p(Y|R,D,M,T)와 D=Y shortcut. loss가 작아도 R을 활용했다는 증거가 아닌 이유.
- 설명용 선형 noise 경로 z_sigma=(1-sigma)E(Y)+sigma*epsilon와 target u=epsilon-E(Y), conditional MSE. 실제 pinned train target·time 방향·loss weight·prediction parameterization을 코드와 대조한다.
- reference-pose 변화 pair, identity 변화 pair, motion 변화 pair가 각각 무엇을 식별하는지.
- 같은개체 복원/새자세/다른개체전이/일반화의 구분. 정답이 없는 cross-ID task에 reconstruction loss를 임의 정의하지 않음.
- 학습 update와40step 영상 sampling의 차이. LoRA 파라미터가 작아도 backward activation/optimizer/base weight residency가 필요함. 기존 no_grad 34GiB 추론치를 학습fit으로 대체하지 않는다.
- 원리→공식 입력/텐서→실제 case→shortcut 반례→질문3개와 별도 해설.

## 9. 최종 출력과 다음 한 단계

결과는 실제 case 수와 종류를 먼저 보고한다. 문헌 수·코드 테스트 수를 학습 성과로 포장하지 않는다.

- `DATA_MANIFEST`와 `RIGHTS_AND_PROVENANCE`(private 상세, 공개 익명 요약)
- 최대8case의 실제 R/D/Y 구성·contact sheet 또는 어떤 파일이 없어 구성하지 못했는지 목록
- `DATA_CONTRACT`와 CPU validator/fixtures 결과
- 그룹 기반 split과 기존 dev set 격리
- 고정 공식 training interface mapping 및 후속 최소 학습 pilot안

판정은 SMOKE_DATA_READY / POSE_VARIATION_AVAILABLE / CROSS_ID_PAIR_AVAILABLE / RIGHTS_PENDING / DATA_GAP을 각각 표시하며 하나의 PASS로 합치지 않는다. 실제 pair가 충분하면 다음은 **허용된1~수개 샘플의 단일 backward/LoRA 배선·overfit 가능성 확인**을 제안할 수 있다. 이때 baseline freeze, actual gradient·optimizer delta·base-weight 보존·reloading·reference sensitivity 평가와 peak memory 예산을 명시한다. pair가 없으면 필요한 자료를 한정한 수집/허가/합성 경로 하나만 제시한다. 이번 B-017에서는 실행하지 않는다.

## 10. 연구 히스토리·공개 범위

CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL와 B-016 결과를 읽고 시작한다. 별도 연구 프로그램 브랜치는 읽되 실행 branch에 무단 merge하지 않는다. 착수 때 PLAN·코드·데이터 선정 규칙을 고정하고 HISTORY/ROADMAP에 추론 개입에서 데이터/학습 준비로 전환하는 이유를 기록한다.

종료 후 RESULTS.md, DATA_CONTRACT.md, 허가·계보 요약, 실제 CPU검사·train interface mapping, 한국어 lesson, HISTORY/ROADMAP을 commit/push하고 원격 SHA 확인. 기존 이력을 수정·삭제하지 않는다. private media/coordinates/masks/cache/latent/weights/개인경로/token은 공개하지 않는다. ZIP은 작은 private 검토 묶음만 /tmp에 만들어 실제 Mac/Spark 복사 여부·CRC·payload SHA를 기록한다. 전체 원본 corpus/weights는 넣지 않는다. 자기 프로세스 종료와 GPU생성/학습0을 명시한다.

### 공식 근거

- SCAIL-2 paper §3.2 Reverse Driving, §3.3 Model Design: https://arxiv.org/html/2606.10804v1
- SCAIL official training format·MotionPair access: https://github.com/zai-org/SCAIL-2/blob/wan-scail2/README.md (2026-10-24 조회 README blob6432684bdfcc4102b8c751e83f1b6d8e5d39b61f; 실행자는 실제 train 코드 revision도 고정)
- APT-36K official paper: https://arxiv.org/abs/2206.05683 ; repository https://github.com/pandorgan/APT-36K
- Flow Matching: https://arxiv.org/abs/2210.02747

# B-021 — 동일한 실제 FM tuple에서 20 대 100 update 비교

작성: 2026-10-24 · parent B-020 · **PLANNED / NOT_RUN**.
이 계획 게시 자체는 학습·생성 실행이나 GPU 예약이 아니다. 사용자가 실행 담당자에게 이 계획을 수행하도록 지시한 경우에만 아래 범위를 적용한다.

## 0. 목표와 확인한 근거

기준 B-020 commit은 `13ac7727e501913ed7e765f44f1d8f6385a19178`. RESULTS, TRAINING_SUMMARY.json, INPUT_AMENDMENT.md, code/phase_train.py, phase_sample.py, fm_contract.py를 원격에서 읽었다. 실험/ZIP을 독립 재실행하지 않았다. 제공 ZIP은 이번 검토 세션에서 container/Python 모두 ClientError로 읽기 실패하여 CRC·payload·영상은 독립 미검증이다. 실행 담당자 보고 ZIP SHA는 `3a59de2c416aa5c5b37b75843251614b0f9dce672f0027af75c3c3135ef6f108`이다.

B-020은 실제 제공 Lab Y의 VAE latent로 FM velocity target을 만들고, frozen prefix의 실제 출력에서 마지막 block Q/V LoRA만 20update했다. 배선·base 불변·reload·OFF는 PASS지만 목표의 네 발로 선 자세 대신 착석·후기 머리 손상이 유지됐다. 이는 두 발 춤 학습이 아니다. 현재 목표는 동일 개체 자연동작 재구성이다.

현재 학습 데이터는 서로 다른 동영상3개가 아니라 **같은clip의 고정 sigma/noise3tuple**이다. train=(0.2,2026102401),(0.5,2026102402),(0.8,2026102403), same-clip diagnostic holdout=(0.65,2026102404). 다른 개체/영상/장면 test는 없다. 20update의 작은 개선만으로 학습 가능성·rank/학습층 한계·추론 실패 원인을 확정하지 않는다.

질문: **같은 학습 공간·tuple·초기 adapter·optimizer 설정에서 update 상한만100으로 늘리면, 고정점의 FM 예측과 동일noise 생성이 20update보다 달라지는가?** 이번은 유한한 회귀 문제의 최적화 예산 검사다. 일반적인 학습량 부족, 새 noise 분포의 학습, identity/pose 분리 또는 일반화를 증명하는 실험이 아니다.

## 1. 중요한 재시작 계약 — adapter만으로 연속 재개하지 않는다

B-020 공개 phase_train.py는 adapter 초기/최종/last-completed를 저장하지만 optimizer.state_dict를 저장하지 않는다. AdamW의 moment/step을 새로 초기화한 뒤 final20 adapter에80update를 더하는 것은 동일한100step 학습과 다르다.

이번 기본안은 **B-020 adapter-initial.safetensors의 실제 A/B값과 메타데이터를 검증해 로드한 뒤 fresh AdamW로0→100을 새로 수행**하는 것이다. 원본 initial의 Bzero, A shape/value·기반 모델·코드/정밀도·training seed20261024·tuple 순서를 보존한다. B-018/019 TEST_ONLY adapter나 B-020 final20을 시작점으로 사용하지 않는다.

실행 비용은 신규100update이며 추가80회라고 계산하지 않는다. 초기 adapter 실물이 없거나 계보 검증이 불가능하면 INITIAL_STATE_UNAVAILABLE로 종료하고 임의 재초기화로 동일 비교라고 보고하지 않는다. 기존 실행의 optimizer checkpoint가 별도로 발견돼도 이번에 로딩 방법을 자동 변경하지 말고 계획 amendment로 명시해야 한다.

PyTorch 공식 근거: https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html#saving-loading-a-general-checkpoint-for-inference-and-or-resuming-training

## 2. 고정 데이터·계산·범위

- B-020의 사용자 허용 자료를 그대로 사용한다. 새 촬영/권한 확인을 중복 요구하지 않는다. 제3자 원본의 미확인 권한과 사용자 제공자료의 허용 상태를 섞지 않는다.
- source f126..142, PTS4.2..4.733333s,17frames/30fps, W896/H512 letterbox와 같은 reference/마스크/positive/empty-negative, D=Y를 고정한다. 영상 길이17/30와 표본간격16/30를 구분한다. 과거 세로17f24fps/다른동물 캐시와 혼합 금지.
- 기존 Y/조건/4tuple frozen-prefix 캐시를 읽기 전용으로 재사용. **P0, prefix full forward0**, 새 모델·패키지·데이터 다운로드0. 기존 frozen prefix 출력은 같은 sigma/noise/조건·가중치·dtype에서만 유효하다.
- 마지막 blocks.39.self_attn.q/v만 rank4, alpha4, dropout0. 기반40block·head는 동결. 공식 head/unpatchify를 통과한 generated-region velocity MSE를 유지한다. trainpositive만 학습한 상태를 negative branch까지 supervised training했다고 하지 않는다.
- AdamW lr1e-4, weight_decay0 및 betas/eps/foreach/fused 등 실제 resolved 옵션을 B-020과 대조해 고정한다. tuple은 index%3 순환. 100회에서는34/33/33,20회에서는7/7/6 노출임을 기록한다. 한epoch나40step sampling과 update 수를 혼동하지 않는다.
- gradient가 필요한 tail/head를 no_grad/inference_mode/detach로 끊지 않는다. x_sigma=(1−sigma)z_Y+sigma*epsilon, target=epsilon−z_Y, model timestep=1000sigma 유지. loss 가중치/foreground 재정규화·augmentation·새noise·reference/dropout 변경을 추가하지 않는다.
- ALG OFF, animation H0/replace_flag=False, history/additional_ref=None. B-016 H120 patch 잔존 없음 확인.

## 3. 캐시 계보는 보존하면서 새 실행을 분리한다

B-020의 캐시는 parent PREREGISTERED_CODE/config hash에 묶여 있다. B-021 code hash와 다르다는 이유로 오래된 producer 문서를 덮어쓰거나 검사를 삭제하지 않는다. parent prefix receipt/캐시/target/조건/noise/geometry/model의 실제 hash를 그대로 검증하고, **producer=B-020 / consumer=B-021** 계보를 별도 명시한다. 새 실행 코드·update budget hash는 B-021의 manifest에 기록한다. sample/serializer의 실험명·허용scope만 좁게 교정하고 수치 helper는 고정한다.

B-020 serializer의 상속 TEST_ONLY label과 실제 private-overfit scope 혼재는 원본 기록으로 보존한다. B-021 새 산출물에는 PRIVATE_ONE_CLIP_FM_OVERFIT_NOT_PRODUCTION 범위를 일관되게 기록하되, 과거 adapter를 조용히 수정하지 않는다.

## 4. 실행과 관측 — 하나의 연속100update

- 학습 worker 최대1회, optimizer update 최대100, 자동재시도0. baseline/trained20 영상을 다시 생성하지 않는다.
- 고정 평가 시점은 **update0,20,50,100**. 각 시점에서 3train+1holdout의 같은 입력을 평가한다(16tail forward). 이후 fresh reload/OFF2회로 총18개 평가 forward, hard cap20. 학습100forward/backward와 구분한다. 예측값 비교를 위해 추가 full-model forward를 실행하지 않는다.
- update0에서는 기존 baseline_velocity와 split parity(기존atol/rtol1e-3)를 확인한다. update20에서는 같은초기값·같은순서의 replay 결과와 B-020 summary/adapter를 비교하고 max/relative차이를 공개한다. 해시 일치가 있으면 기록하되 같은seed가 언제나 byte-identical을 보장한다고 주장하지 않는다. 의미있는 불일치가 확인되면 21회 이후 증량 전에 원인을 보고하고 STOP; tolerance를 사후 확대해 비교를 맞추지 않는다. 작은 replay 오차도 원래20회 개선량과 함께 보여 인과 해석 한계를 남긴다.
- 매 update: tuple ID, loss, finite gradient·adapter parameter 변화·step 수. loss 곡선은 **서로 다른sigma의 연속 loss를 한 하강 곡선으로 해석하지 말고 tuple별**로 제시한다. 평가 스냅샷의 동일tuple 비교를 주로 사용한다.
- 같은 평가 forward에서 얻은 prediction으로 baseline 대비 RMS/maxabs·상대L2 변화량을 기록한다. weight가 바뀌었다는 사실과 실제 BF16 추론 예측에 변화가 나타났다는 사실을 분리한다. 해석을 위해 full Q/V delta matrix를 매번 만들지 않는다.
- 기반가중치 grad=None·optimizer 제외·runtime값 불변, adapter만유한변화, save/fresh-reload/OFF 검증을 유지한다. loss의 단조 감소나 모든tuple 개선을 PASS 요건으로 강제하지 않는다. NaN/Inf·잘못된parameter변경·cache불일치·자원위험이면 STOP한다.
- 0/20/50/100에서 adapter를 보존하고, 이후 재개에 필요한 optimizer moment/step, CPU/CUDA RNG, tuple cursor, options·code/parent hashes를 함께 보존한다. 저장은 안전한 tensor/primitive 스키마로 하고 외부pickle broad allowlist를 도입하지 않는다. optimizer checkpoint 생성 검사는 adapter reload 검사와 구분한다. 저장물을 현재계획 밖 학습에 자동 재개하지 않는다.

## 5. 사전 고정한100회 endpoint의 영상 한 번

학습이 유한하게 완료되고 checkpoint·계약 검증을 통과하면 loss가 가장 좋은 checkpoint를 골라 쓰지 말고 **update100 endpoint**만 실제 sampler로 평가한다. loss가 작게 바뀌거나 나빠져도 기술적으로 안전하면 사전 고정한 평가1회를 시행해 failure를 숨기지 않는다.

- 기존 B-020 baseline 및20update 결과를 그대로 재사용.
- 새100update full sampler 최대1회,40steps/80forward·UniPC shift3/CFG5·기존실제 초기noise와generator state·same W896/H512·17f30fps, decode최대1회. PROBE최대1회. 최종latent를D전 원자 저장; D실패로S재실행 금지.
- adapter선택/실제Q/V설치/sha/dtype/provenance를 로그로 확인한다. 100개update를100개samplingstep으로 바꾸지 않는다. 전체40block의 추론은 필요하며 cached prefix를 sampler의모든step에 재사용하지 않는다.
- 원본 / update0 / update20 / update100을 같은canvas·시간축·전체17장으로 비교. 사전local0/8/16 유지. source의 사족으로 선 자세, head turn 방향·순서, 얼굴/귀/목/주둥이·경계잘림, 실제개체와견종 유사성, reference letterbox/장면복사를 따로 기록.
- 현재target 복원에서는 목표장면과의 차이를 기록하되 일반animation모드에서 reference배경유지가 항상오류라고 일반화하지 않는다. standing target 실패가 우선이다.
- 후처리warp·crop변경·새mask·보간·SR·좋은프레임선별 없음. 실제연속시청주체·근거 없으면 temporal=UNVERIFIED. MP4 decode/viewerQA를 사람의품질수용으로 대체하지 않는다.

## 6. 자원·정지·해석

총작업상한3시간. 기존B-020의phase별 실제guard/cgroup상한, 시작72GiB·실행24GiB headroom·swap0·타서비스보호를 유지한다. 이 제안으로기존cap을자동확대하지않는다. 새deadline/unit은실제시작시각기준. 다른프로세스종료·driver/swap/clock변경·캐시강제삭제·추가worker없음. 자기프로세스만종료한다.

B-020의학습38.8초관측을미래소요보장으로쓰지않고동일단위로재계측한다. inference가training보다더비쌌다는기존관측을고려해여러중간MP4를생성하지않는다.

종료시판단:
1. train·sameclip holdout 예측과 영상이 개선: 이고정문제에서추가최적화의유용한근거. 일반화/identity분리주장금지.
2. train만개선·holdout정체/악화: 고정tuple적합과noise/time확장의차이. holdout은독립영상test가아님.
3. 고정loss는개선·영상은그대로: teacher-path예측과실제CFG/생성궤적사이차이,coverage/학습모듈/공간loss문제등이후보. 특정하나확정금지.
4. 모두작은변화: 100회범위와이optimizer/adapter/tuple에서유용한개선미확인. 수학적수렴·모델용량부재·전체LoRA불가능증명아님. 원래손실감소추세도함께보고.

**이한번후자동200/500/1000update확장금지.** 다음은곡선·예측변화·영상에근거해학습분포또는학습범위등가설하나만선택한다. 데이터추가·lr/rank/layer/CFG변경을이번비교와섞지않는다.

## 7. 공부·GitHub·제출

한국어 lessons/B-021-finite-fm-optimization.md: 실제FM기댓값과고정3tuple경험손실, frozenprefix가sigma/noise/c에의존하는이유, 학습positive와CFG rollout의차이, Adammoment를포함한resume와warmstart, tuple별loss곡선·개체/자세품질의차이를수식→실제코드→관측→한계→질문/답안순서로설명한다. 기존LoRA/FM이론을새기여로포장하지않는다.

시작전CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL·B020관련코드를읽고새100update예산·평가기준·입력·producer/consumer계보를사전commit한다. HISTORY/ROADMAP에이번결정과상태를연결한다. 종료후RESULTS·loss표/곡선·실제선택endpoint·재현·실측·학습문서를commit/push하고remoteSHA를확인한다. 기존결과·A·main은변경하지않고forcepush금지.

비공개ZIP에는새adapter/optimizer상태·scalar로그·입력계보·100회영상/latent·기존비교·실패/재현을보존하고대형weights·중복prefix특징은제외한다. 개인사진·영상·adapter·latent·feature·private경로·secret은공개하지않는다. Mac/Spark /tmp의실제경로·CRC/payloadhash/전송일치를확인하고자체작업종료상태를보고한다.

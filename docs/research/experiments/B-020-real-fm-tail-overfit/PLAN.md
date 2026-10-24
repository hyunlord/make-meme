# B-020 — 실제 영상 FM target을 이용한 마지막 block LoRA 소형 overfit

작성: 2026-10-24 · parent B-019 · **PLANNED / DATA_PENDING / GPU NOT_RUN**.

이 문서는 다음 연구의 조건부 계획이다. 게시만으로 자료 확보·개인 자료 학습 허가·GPU 실행 승인이 된 것은 아니다. 사용자가 자료를 제공하고 수행을 지시한 뒤, 아래 데이터·수치·자원 계약이 충족될 때만 실행한다. 현재 없는 Lab 영상이 있다고 가정하지 않는다.

## 0. 판단과 목표

B-019 고정 commit `65b0e7f53d53396d348c57c92486810c0fb0c666`: 실제 마지막 block의 synthetic36token 3update·reload/OFF, synthetic12992token backward1회·update0 통과. 긴 CUDA peak5.816GiB는 한 block의 실제 길이 검사값이며 전체 모델 학습 메모리나 동물 학습 성과가 아니다. 구성요소 수를 하나씩 늘리는 synthetic smoke는 여기서 일단 마무리한다.

다음 질문은 **실제 영상 Y의 VAE latent로 정의한 FM target을, 공식 출력 head를 거친 모델 예측에서 학습시킬 수 있는가?** 목표는 한 clip의 제한적 동일 개체 복원 overfit이며, cross-ID/직립 춤/새 개체 일반화/논문 기여가 아니다. D=Y인 경우 reference 무시·driving 복사 shortcut을 명시한다.

## 1. 데이터 게이트: 자료가 없으면 같은 감사 반복 금지

- 사용 범위가 확인된 실제 동일 Lab의 자연동작 영상 Y 하나, 가능하면 Y 밖 다른 시점의 실제 reference R 1~2장부터 시작한다. smoke용1clip으로 충분하며 여러 세션 확보를 첫 배선 검사의 필수 조건으로 만들지 않는다. 별도 세션이 있으면 독립 평가용으로 보존하되 같은 개체 평가를 새 개체 일반화라 하지 않는다.
- 예시 수집 범위는 자연 고개돌림·앉기/서기·짧은 걷기 5~10초 원본이다. 직립 춤을 강요하지 않는다. 사용자가 촬영/권한과 비공개 연구 학습 허용을 확인하면 그 근거를 기록한다. 불필요한 법률 서류를 요구하지 않으며, 업로드가 공개 재배포 허용이라는 뜻도 아니다.
- D=Y의 SELF_RECON_FM_SMOKE로 정의한다. 다른 동물의 원본이나 과거 실패 생성물을 Lab Y로 대체하지 않는다. 기존 제3자 영상의 RIGHTS_PENDING을 해제한 척하지 않는다. 새 외부 데이터·생성·신청·가입·다운로드는 하지 않는다.
- 현재 등록 자료에 해당 Y/R가 없으면 **DATA_PENDING**으로 누락자료 한 번만 기록하고 종료한다. 새 synthetic experiment·반복 권한 감사·임의 학습을 대체 실행하지 않는다.
- 자료 확보 후 source만 보고 최초 적합 연속17frame 구간을 선택한다. 원본 fps/PTS와 실제 처리 시각을 기록한다. 학습·추론·평가 시간축을 동일하게 고정하고 30fps 자료를16/24fps라고 relabel하지 않는다. 필요한 재표본화는 타임스탬프 대응과 처리 이유를 입력 확정 문서에 먼저 남긴다. 공간크기는 기존512p와32배수 규약을 우선하되 발/머리 crop 손실을 검사한다.
- 실제 R/D/Y와 reference/driving mask·caption 역할을 확인한다. mask가 없으면 기존 CPU 도구로 명확한 단일 개체 support를 제한적으로 준비하고 애매한 경계는 표시한다. 새 segmentation 모델 설치 금지. 확정 RGB/mask/target 해시·geometry·timebase와 학습허용 범위를 공개 가능한 요약/private manifest로 구분해 기록한다.

## 2. 모델·loss: 인공 hidden target에서 실제 velocity target으로

- ALG OFF, reference RoPE H0, animation, history=None, additional_ref=None. 기존 가중치/upstream/loader/FA2/mixed precision/프로세스 분리와 안전 가드를 보존한다.
- VAE·T5·CLIP 및 기반 모델 가중치를 동결한다. 학습 파라미터는 B-019와 같은 `blocks.39.self_attn.q/v`의 rank4·alpha4·dropout0 LoRA(81,920개)만이다. 기존 TEST_ONLY adapter를 이어 학습하지 않고 Bzero로 새로 시작한다. 이 위치의 효과가 최적이거나 자세를 고칠 것이라고 가정하지 않는다.
- Y를 정상 VAE 경로로 인코딩한 z_Y가 실제 정답이다. 설명/목표 규약은 z_sigma=(1−sigma)z_Y+sigma*epsilon, target=epsilon−z_Y, model timestep=1000*sigma다. 고정 SAT RFLoss/RFScaling과 Wan forward의 부호·scale·CTHW/BTCHW·head/unpatchify를 실제로 대조하고 다르면 샘플을 돌리지 않는다.
- 첫 smoke는 history/OCR mask를 zero로 명시하여 generated latent 전체의 FP32 mean-squared velocity error를 사용한다. 참조/driving token을 target으로 계산하지 않는다. RGB loss 또는 block hidden MSE로 대신하지 않는다. caption dropout/augmentation/history 정책을 임의로 섞지 않으며 공식 전체 학습 recipe를 재현했다고 주장하지 않는다.
- 학습은 positive 조건의 velocity 예측 하나를 사용한다. CFG80forward/40step 영상 샘플링을 한 optimizer update 안에서 역전파하는 방식이 아니다.

## 3. 자원 전략: 고정 prefix 특징 재사용, 제한된 실제 FM 목적

우선안은 **앞39개 block과 embeddings를 동결해 no_grad로 실행하고, 실제 block38 출력 + context/time/position metadata를 저장 → prefix를 종료 → 마지막 block39와 공식 head/unpatchify만 적재해 LoRA 학습**이다. 전체40block을 backward하는 실험은 아니다. 실제 전체 생성에서는 모든 block을 원래대로 통과시킨다.

- 출력 head는 동결하지만 그 연산을 no_grad로 끊지 않는다. head와 unpatchify를 통한 input derivative가 LoRA까지 전달되어야 한다. 앞39개 block에는 학습 대상이 없으므로 no_grad/출력 detach가 가능하다. inference_mode tensor를 그대로 학습에 섞지 않는다.
- 저장할 실제 값은 block39 입력 h38, post-projection context, block용 e0, head용 e, 길이/격자/offset, target과 sigma/epsilon/provenance다. e와 e0를 혼동하지 않는다. 원래 dtype를 lossless로 보존하고 추가 BF16반올림·latent normalization을 넣지 않는다.
- prefix 특징은 h38=F_frozen(z_sigma,sigma,R,D,M,text)다. **clip당 한 특징이 아니다.** sigma/noise/reference/driving/crop/dropout/가중치가 바뀌면 재계산이 필요하다. 새로운 sigma/noise를 뽑았다고 하면서 과거 특징을 재사용하지 않는다.
- 계산비를 제한하기 위해 이번은 유한한 FM 회귀 문제로 사전 고정한다. 같은 clip의 학습3tuple은 sigma=(0.2,0.5,0.8)와 각각 독립 fixed noise다. 평가1tuple은 sigma=0.65와 별도 noise다. 실제 seed·tensor hash는 생성 전에 고정한다. 평가 tuple은 동일 clip의 noise/time holdout일 뿐 영상·개체 일반화가 아니다. 공식 LogisticNormal sigma 학습분포의 충실한 재현도 아니다.
- frozen prefix 추출은 총4tuple, 각각1회만 수행한다. 동일 forward에서 Bzero 기준의 최종 velocity도 저장하여, 별도 tail+head 경로가 같은 입력에서 맞는지 GPU 이전에 정한 tolerance로 검증한다. 비교값에 맞춰 tolerance를 늘리거나 head를 교체하지 않는다. CPU 작은 계약 검사를 먼저 수행하고 실제 불일치는 SPLIT_PARITY_BLOCKED로 기록한다.
- 학습 tuple3개를 고정 순서로 순환해 최대20 AdamW update(lr1e-4,wd0)를 수행한다. 추가 시간·noise 샘플을 자동 만들지 않는다. gradient20회, 학습 전후/고정 holdout/reload/OFF 추가 tail 평가 합계최대12회. 단조 loss 감소를 강제하거나 결과에 맞춰 학습 횟수·rank·lr를 바꾸지 않는다.
- 20update 또는 마지막 실제 완료 update의 adapter를 보존한다. 기반 가중치 불변·optimizer 객체 집합·실제 finite gradient·adapter 변화·fresh reload/OFF를 확인한다. training loss가 줄어도 motion/identity 성공으로 보고하지 않는다.

## 4. 자원·안전·시도 예산

- 데이터가 없는 현재는 GPU0. 자료 제공·사용자의 실행 지시·입력 계약 통과 후 총 작업상한4시간이다. 자동재시도0, 새 모델·대형 데이터·패키지·외부API·imagegen0.
- 실제 조건/target encoding1회, frozen-prefix 추출4tuple, tail 학습 worker1회(max20update), 제한적 학습 전/후 sampler각1회(max2), 각 decode1회까지만 허용한다. 호환되는 동일입력 baseline이 실물·해시로 확인된 경우에만 재사용한다. 이전 밈/Lab clip의 결과는 새 자연동작의 동등 baseline이 아니다.
- prefix/영상 sampler는 이미 성공한 full-model load와 해당 guard를 재사용하고, tail 학습은 기존B019 cap16GiB/high14GiB를 우선한다. cgroup은 통합 CUDA 메모리의 검증된 hard cap이 아니다. fresh MemAvailable·CUDA allocator·RSS·cgroup을 별도 측정하며 시작72GiB/실행24GiB headroom·swap0·타서비스 보호를 유지한다. 사전 자원검토에서 fit 근거가 없으면 중지하고 임의cap 확대·다른 작업 종료·drop_caches/driver/swap 변경 금지.
- 기존 장비에서 full-prefix 적재가 성공했다는 것은 train tail까지 동시상주한다는 근거가 아니다. phase별로 종료하고 회복 확인. 두 영상을 만들면 각각최대40step80forward, 같은 초기noise·조건·CFG를 유지해 adapter 차이만 비교한다. 자원/시간 부족 시 결과를 보존하고 영상은 NOT_RUN; 자동 추가 실행 금지.
- decoder·후처리 실패 시 보존한 final latent를 삭제하거나 sampler를 다시 돌리지 않는다. 테스트 adapter를 일반 production 기본값에 적용하지 않는다.

## 5. 평가·학습 범위

- 3개고정 FM tuple loss의 전후, 동일clip heldout noise/time loss, trainable/base 변화, split parity, reload 결과를 각각 기록한다. 낮은수준 학습배선·한clip 적합·생성 품질·개체전이를 구분한다.
- 영상은 TARGET / BASELINE / TRAINED를 실제 시간축·전체17장으로 비교한다. 자연동작의 방향·타이밍·형상·참조개체를 본다. 손상·정지화·외형누수·실패를 숨기지 않는다. 실제 연속재생을 보지 못하면 temporal=UNVERIFIED다.
- D=Y라면 loss나 영상이 좋아져도 driving 복사만으로 가능한 과제다. cross-ID dance·pose/identity 분리·새동물 일반화·논문기여는 NOT_RUN/NOT_ESTABLISHED로 남긴다. 마지막 block LoRA로 개선이 없어도 전체모델 학습 불가능·데이터가 무효라는 결론은 내리지 않는다.
- 한국어 lessons: 실제Y latent→noise mixing→velocity target→head/unpatchify→loss→LoRA gradient를 텐서·공식소스·수식으로 연결한다. frozen prefix cache가 가능한 조건, 시간/noise를 바꾸면 캐시가 무효인 이유, frozen head를 통한 chain rule, training update와sampling step의 차이, overfit/noise holdout/generalization 차이를 설명하고 이해 질문·해설을 남긴다.

## 6. 기록과 종료

착수 시 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL와 B017/B019 결과를 읽는다. 데이터가 없으면 DATA_PENDING에 머물고 같은자료 재감사·합성component실험을 자동 생성하지 않는다. 자료가 확보되면 실제 clip/R/mask·시간축·sigma/noise·baseline·loss·정밀도·guard를 확정 amendment와 코드로 사전 commit한다.

종료 후 RESULTS/한국어해설/실측/재현/HISTORY/ROADMAP에 실제완료·미실행·해석을 기록하고 연구branch에 push·remote SHA 확인한다. 원본/미디어/특징·latent·adapter·개인경로·secret은 공개하지 않는다. 비공개ZIP에는 작은결과·adapter·필요한재현·해시·실패를 포함하고 대형weights와수GB prefix cache는 기본제외/실제경로·hash만 기록한다. Mac/Spark 전송·CRC·파일hash를 구분한다. 이 연구는 DATA_PENDING 해소 이후 실제 FM로 연결하는 한 단계이며, 종료 후 추가sample/epoch/adapter확장/개체전이는 자동 실행하지 않는다.

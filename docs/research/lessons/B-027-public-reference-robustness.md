# B-027 — 공개 참조 교체의 조건 불변성과 실패 판독

확인일: 2026-10-26 KST. 아래 문헌 조사는 공식 웹·논문·저장소의 읽기 전용 확인이며, 조사 대상 모델 설치·가중치 다운로드·GPU 실행은 하지 않았다. B-027의 기존 SCAIL 실행과는 별도 범위다. 아래 문헌의 논문 보고 결과를 이번 Spark 실측으로 사용하지 않는다. 실제 실행 결과는 B-027 RESULTS와 구분해 연결한다.

## 1. DAVIS: 이번에 사용할 수 있는 자료 경로

- 공식 [DAVIS 2017 다운로드 페이지](https://davischallenge.org/davis2017/code.html)는 Semi-supervised TrainVal의 Images and Annotations 480p archive를 제공한다.
- 직접 URL: `https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip`
- 이번 HEAD 응답: HTTP 200, `Content-Length=832766765`, `Content-Type=application/zip`, `Accept-Ranges=bytes`, Last-Modified `Wed, 05 Apr 2017 15:28:22 GMT`. 약 0.776 GiB로 5 GiB 상한 안이다. 이 HEAD 관측 이후 실행자는 실제 파일832766765bytes와 전체 ZIP CRC를 확인했다. [다운로드 기록](../experiments/B-027-public-reference-robustness/DOWNLOAD.json).
- 공식 사이트의 [고정 revision dataset metadata](https://github.com/davisvideochallenge/davisvideochallenge.github.io/blob/30be16ff9d289f6711328c950a19c6288306ade3/index.html#L33-L42)는 DAVIS 2017 Dataset에 CC BY-NC 4.0을 표기한다. 코드 저장소 LICENSE를 미디어 허가로 대신하지 않았다.
- [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)은 attribution·license 링크·변경 표시와 비상업 조건 아래 공유·변형을 허용한다. 제품 상용 사용 허가로 확대하지 않는다. 공개 GitHub에는 원천 미디어 대신 다운로드 명세·해시·처리 코드만 두고, 비공개 검토물에도 dataset 출처·이용 조건과 변경 내역을 포함하는 경로가 적합하다. 인물의 공개/초상권 등 다른 권리가 자동 해결된다는 뜻도 아니다.
- 공식 480p 프레임 archive 자체에 native FPS가 확인되지 않으면 `source_fps=null`, `preview_fps=24`, `timebase_assumed=true`를 유지한다. 데이터셋 이름이나 preview MP4의 FPS를 원본 PTS 근거로 쓰지 않는다.

## 2. 세 문헌: 기제와 실행 가능성 구분

### VideoSwap

[논문 v2](https://arxiv.org/abs/2312.02087v2)의 핵심은 조밀한 픽셀 대응을 강제하는 대신 적은 수의 의미점 대응으로 원본 궤적을 대상 형상에 연결하는 것이다. 포인트 삭제·드래그와 부분 대응도 다룬다. 체형이 다른 대상을 같은 픽셀 실루엣으로 고정하면 안 된다는 이번 평가 관점과 관련 있다. 이번에는 포인트 추적·학습을 추가하지 않는다.

[공식 저자 재구현 README](https://github.com/showlab/VideoSwap/blob/e0dd4eb985e99a4e9c7d5e465ffaed238eed8741/README.md)는 train/inference 코드 공개와 A100에서의 환경을 명시한다. [prepare_dataset_model.sh](https://github.com/showlab/VideoSwap/blob/e0dd4eb985e99a4e9c7d5e465ffaed238eed8741/scripts/prepare_dataset_model.sh)는 학습 모델/AnimateDiff 모듈 archive와 기반 모델 다운로드 위치를 제시한다. 링크·코드는 확인했지만 외부 checkpoint archive를 실제 내려받아 로딩하지 않았다. A100 안내를 Spark 호환성·메모리 실측으로 옮겨 쓰지 않는다.

### VideoAnydoor

[논문 v4](https://arxiv.org/abs/2501.01427v4)는 ID extractor, box sequence, reference keypoint와 trajectory를 받는 pixel warper를 나누어 설명한다. 외형 표현과 움직임 경로를 분리하는 구체적인 선행 설계다. 논문 abstract는 warped feature를 diffusion U-Net에 결합한다고 설명한다.

반면 확인한 [공식 저장소 revision](https://github.com/yuanpengtu/VideoAnydoor/tree/79c0301eecfeb1e611484111d0e5bdb4a29c9938)은 README와 framework 그림만 있고, README의 2025-12-05 소식은 코드 정리·공개 예정이라고 적는다. README에는 Wanx 기반이라는 설명도 있어, 공개 논문의 U-Net 기술과 미래 구현을 동일 코드로 단정할 수 없다. **논문 공개 / 실행 코드·weights 제공 확인 못함**으로 구분한다. 바로 설치 가능한 대안으로 추천하지 않는다.

### VideoPainter

[논문 v3](https://arxiv.org/abs/2503.05639v3)는 masked video를 받는 별도 context encoder와 생성 backbone의 dual-stream으로 배경 문맥 보존과 전경 생성을 나눈다. target-region ID resampling도 설명한다. 이것은 source context를 독립 경로로 주는 설계의 선행 예이며, 이번 raw SCAIL 결과에 사후 합성을 적용했다는 뜻은 아니다.

[고정 코드](https://github.com/TencentARC/VideoPainter/tree/bbab6cd5cd5cb89f0e2444305c32fd74a010ae0a)에는 train/infer 코드가 있고, [공식 HF revision](https://huggingface.co/TencentARC/VideoPainter/tree/52bc9fd04553ad177158b8bcf42590670339e226)에는 context-branch safetensors와 VideoPainterID LoRA 파일이 실제 목록에 있다. 제공 상태를 확인했을 뿐 모델 다운로드·Spark 실행·이번 사례 품질 검증은 하지 않았다. CogVideoX 기반 checkpoint를 SCAIL용 모듈처럼 즉시 교체할 수 있다고 가정하지 않는다.

## 3. 한국어 이론: 같은 대상, 다른 참조에서 무엇이 같아야 하는가

### 직관

참조 R1/R2는 같은 target track의 다른 사진이므로 외형 근거는 공유하지만 자세·가림·시점은 다르다. source V는 두 경우 모두 같은 동작을 제공한다. 목표는 출력의 모든 픽셀이 같은 것이 아니라, 외형이 target을 따르고 동작의 방향·순서가 source를 따르는 것이다. source를 그대로 복사하면 장면과 동작은 맞아도 교체 실패다. 참조 사진을 반복하면 외형은 맞아도 동작 실패다.

### 수식과 가정

과제 i의 조건 묶음을

`C_ij = {E_VAE(R_ij), E_CLIP(R_ij), M_ref,ij, E_VAE(V_i), M_drive,i, E_text(P_i), mode}`

로 쓰면 `Y_ij = Decode(Sample(epsilon_i, C_ij))`이다. j=1,2에서 source·caption·실제 초기 noise·scheduler는 고정하고 reference RGB/특징/mask만 바꾼다. 예시 FM 표기 `dz/dtau = v_theta(z,tau,C)`의 tau는 denoising 시간이며 영상 frame index와 다르다. 실제 scheduler의 시간 방향·sigma는 고정 구현을 따른다. 동일 noise라도 C가 바뀌면 예측 속도와 이후 z가 바뀌므로 두 실행의 중간 latent는 일반적으로 다르다.

이상적 목표를 설명하기 위해 외형 판독 a와 움직임 판독 m을 둔다면 `a(Y_i1)≈a(Y_i2)≈a(B_i)`와 `m(Y_i1)≈m(Y_i2)≈m(V_i)`다. 여기의 a,m은 검증된 자동 metric을 도입했다는 뜻이 아니다. 실제 평가는 사전 고정한 외형 특징·사건과 불확실성 표로 수행한다. 단순 pair 차이 `Y_i1-Y_i2`는 pose의 순수 인과효과가 아니다. reference mask·조명·시점도 함께 바뀐다.

### 실제 cache·코드와 연결

B-027 [`phase_encode.py`](../experiments/B-027-public-reference-robustness/code/phase_encode.py)의 `run`은 공식 `generate`의 첫 sampler 경계에서 `noise, arg_c, arg_null, generator_state, timesteps, sigmas`를 저장한다. R2는 같은 R1 tree를 CPU에서 읽고 양 CFG의 `ref_latents`, `clip_fea`, `ref_masks`만 바꾼다. [`pair_contract.py`](../experiments/B-027-public-reference-robustness/code/pair_contract.py)의 허용 key는 `t2/t3/t4/t8/t9/t10`이며, 모두 반드시 달라야 하는 것은 아니다. 나머지10leaf와 구조/device계약은 보존한다. [`phase_sample.py`](../experiments/B-027-public-reference-robustness/code/phase_sample.py)의 첫 실제 CFG hook은 reference/CLIP/mask가 복원된 cache 객체인지 확인하며 관측용 추가forward를 하지 않는다.

실제 완료한 실행에서 reference CTHW는 `[16,1,64,112]`, final latent는 `[16,5,64,112]`, raw decode는 `[3,17,512,896]`였다. driving VAE는 `[16,5,32,56]`이며 reference mask는 prefix와 generated 구간을 포함한 `[28,6,64,112]`다. CLIP `[1,257,1280]`은 FP16, reference/driving VAE는 FP32다. 이 값은 [CONDITIONS](../experiments/B-027-public-reference-robustness/CONDITIONS.md)의 실제 cache 관측이며 해상도만 보고 추정한 값이 아니다. reference mask는 RGB alpha가 아닌 별도 조건이다. RGB128은 encoder branch OFF가 아니며, 같은 foreground pixel도 주변 문맥 변화에 따라 VAE/CLIP 특징이 달라질 수 있다.

전처리 원본은854×480 공개프레임이다. 896×512 aspect-fit은 새로운 디테일을 만들지 않는다. 공개GT의가림을 그대로유지하므로 human R2의관목구멍이나 animal의작은support도 조건일부다. 형태의실패를 모델원인으로단정하기전에 이관측한계와구분한다.

### 실제 결과에서 수식을 읽는 법

동물 pair는 source의 접근·정면 변화가 남지만 어두운 target 외형 대신 옅은 source 외형이 유지됐다. 위 설명식에서 m의 큰 변화가 맞아 보이는 것과 a가 target에 맞는 것은 다른 조건이다. source-copy는 두 번째 조건을 위반하므로 교체 성공이 아니다.

사람 pair는 흰 상의·분홍 치마라는 target 특징이 나타났으나 팔/치마 배치는 source와 어긋나고 후반 형상이 무너졌다. 이는 참조 조건이 완전히 무시되지는 않았다는 근거이지, 외형과 공간 배치가 분리됐다는 근거가 아니다. reference가 같은 target track이라고 해도 E_VAE는 사진의 위치·자세·가림 정보를 담을 수 있다. 사람 R2의 넓게 펼친 옷과 팔, GT의 관목 가림이 함께 달라져 단독 원인을 분리할 수 없다.

차량 R1에서는 은색·옆 몰딩이 바뀌어도 source형 차체가 남고 비편집 영역에 큰 차량 그래픽이 생겼다. 조건의 영향이 있다는 사실은 지시 준수와 다르다. 특히 semantic mask를 전달한 것과 배경 픽셀을 하드하게 복사·보호하는 것은 같은 연산이 아니다. 본 실행은 RGB diffusion 출력이며 ROI 합성을 하지 않았다. 입력 연결이 맞았다는 runtime 확인만으로 배경 불변을 보장할 수 없다.

차량 R2는 큰 그래픽 없이 밝은 박스형 차체로 바뀌었지만 정확한 target 구조는 미입증이었다. 따라서 R1의 장면 실패가 필연적이라고도, R2의 비교적 깨끗한 장면이 교체 성공이라고도 하지 않는다.

각 pair의 외형/동작/장면/형상/비용은 [RESULTS](../experiments/B-027-public-reference-robustness/RESULTS.md)와 실제 전체17장 검토물에 연결한다. 세 과제의 차이는 모델 도메인과 reference 크기·가림 등이 섞인 결과이며 지원 범위의 일반 통계가 아니다. 실제 연속 검수가 없으므로 temporal=UNVERIFIED다. GT instance mask 사용은 mask-given이며 자동 선택·추적은 NOT_RUN이다.

## 이해 확인 질문

1. 같은 noise를 썼는데 R1/R2 출력이 다르면 왜 그것만으로 좋은 reference 활용을 입증하지 못하는가?
2. source와 출력의 전체 PSNR이 높으면 왜 객체 교체 성공을 뜻하지 않는가?
3. 6개 출력과 102개 프레임을 독립 표본으로 세면 왜 근거가 과장되는가?

## 별도 해설

1. 참조 배경·자세를 복사하거나 형상을 무너뜨려도 출력은 달라진다. target의 실제 특징과 source 사건을 함께 확인해야 한다.
2. 교체할 객체의 외형은 바뀌어야 한다. source-copy는 높은 유사도를 얻어도 identity-change FAIL이다. 보호 배경의 보조 오차와 객체 편집 평가는 나눠야 한다.
3. 같은 source/target/seed의 두 조건은 paired이고 인접 프레임은 시간적으로 의존한다. 독립 단위는 제한된 세 편집 과제이며 일반화·통계적 유의성을 추정할 규모가 아니다.

# B-030 — 같은 대상의 두 참조를 이용한 조건 경로 교차 비교

작성: 2026-10-26. 최초 상태: **PROPOSED / NOT_RUN**.

종료 상태: **COMPLETED**, 신규 sampler4/4·decode4/4·encoder0·재시도0. 마지막 decode UTC09:38:04. 사전 계획은 아래 그대로 보존하며 실제 관측·해석 한계는 [RESULTS](RESULTS.md)에 기록한다. 아래 PREPARING은 착수 당시 상태다.

실행 착수: 사용자 B-030 지시를 받아 2026-10-26 UTC08:19:50에 CPU 준비를 시작했다. 시작 원격 HEAD `230dad2ba9ffe5a02da3b408058e604e7dea757e`, 전체 deadline UTC11:19:50. 기존 활성 B030 프로세스는 발견되지 않았으며 실제 case 장부까지 확인한 뒤 생성한다. 아래 사전 계획과 기존 실패는 보존한다. 현재 **PREPARING / 신규 sampler 0**.
검토 기준 HEAD: `a60e258b9a6c25624b07423e4cd29838f3b1b195`.
문서 등록은 GPU 실행이나 예산 사용이 아니다. 사용자가 수행 지시를 전달할 때 아래 범위를 적용한다. 이미 실행 중인 다른 작업을 중단하거나 중복 실행하지 않는다.

## 1. 최종 목표와 B-029 종료 판단

공개·다중 사례의 원본 영상 V, 참조 이미지 R, 편집 지시 P를 받아 참조 대상의 외형을 반영하고 원본의 지정 동작·장면을 보존하는 방법을 단일 DGX Spark에서 연구한다. 특정 개인 사진 확보를 연구 진행의 조건으로 삼지 않는다. A imagegen 트랙은 독립 보존한다.

B-028의 전처리 정규화는 일부 외형 반응과 동작·장면 회귀를 함께 보였고, 공통 기준선으로 채택하지 않았다. B-029의 CLIP image cross-attention 출력 위치 재가중은 고정 METHOD6/CONTROL2 비교에서 결합 품질 개선을 입증하지 못했다. B-029는 NOT_ADOPTED를 유지하고 CONTROL을 사후 최적 방법으로 채택하지 않는다. 추가 lambda/layer/schedule/seed 탐색을 하지 않는다.

B-029가 reference VAE joint-attention을 그대로 두었다는 사실은 이 경로가 원인이라는 증거가 아니다. 다음에 가중치를 또 바꾸기 전에, 이미 존재하는 두 참조 경로를 교차해 관측되는 자세·외형·장면 변화가 어느 입력 묶음을 따라가는지 제한적으로 확인한다. 이것은 새로운 편집 알고리즘이 아니라 다음 방법의 표적을 고르는 메커니즘 실험이다.

## 2. 이번 질문과 한계

같은 대상 track의 R1/R2에서
- Z_i = (VAE(R_i), reference semantic mask_i)
- C_j = CLIP(R_j)
- Y_ij = F(V, Z_i, C_j, P; epsilon)
로 정의한다.

| VAE+mask 묶음 | CLIP R1 | CLIP R2 |
|---|---|---|
| R1 | Y11: 기존 B-027 | Y12: 신규 |
| R2 | Y21: 신규 | Y22: 기존 B-027 |

각 과제에서 같은 target의 사진을 교차한다. 서로 다른 정체성의 VAE/CLIP를 섞어 충돌시키는 실험은 아니다. reference mask는 반드시 해당 VAE 이미지와 함께 유지한다. 따라서 Z 효과를 'VAE만의 효과'나 '순수 위치 효과'라고 부르지 않는다.

VAE도 외형을 담고 CLIP도 공간·자세 정보를 가질 수 있다. VAE=pose, CLIP=identity라는 가정을 하지 않는다. Y12/Y21은 통상 같은 사진에서 함께 인코딩되는 두 경로를 다르게 연결한 입력이므로 학습분포 이탈과 경로 간 불일치가 가능하다. 교차 조건만 손상되면 경로 불일치 결과이지 어느 경로가 잘못됐다는 증명이 아니다.

한 seed·선택한 사례에서의 실행 개입 효과를 관찰할 수 있지만, 학습 원인·모든 객체·모든 layer/step의 기여를 일반화하지 않는다. 이 실험의 성공은 반드시 예쁜 영상이 아니라, 다음 방법을 겨냥할 수 있는 판별 가능한 결과다. 판별할 수 없으면 INCONCLUSIVE로 종료하고 겉보기 차이로 원인을 만들지 않는다.

## 3. 고정할 두 공개 과제

B-027의 human 및 vehicle 과제를 사용한다. 해당 두 R1/R2가 기존에 관측 가능한 자세·가림·문자/그래픽 차이를 보였기 때문에 선택한다. 새 결과를 보고 더 유리한 과제로 교체하지 않는다. animal은 이번 범위에 포함하지 않으며 성공/실패율 분모로 사용하지 않는다.

- human: source dance-twirl f0..16, target dance-jump track1 f0/f16.
- vehicle: source car-roundabout f30..46, target car-shadow track1 f0/f39.

공통 기준선은 B-027의 해당 네 출력·원래 cache다. B-028 정규화 입력이나 B-029 gate 출력으로 섞지 않는다. 원본 사진·마스크·crop·회색 배경 처리·caption을 바꾸지 않는다.

17프레임,896×512,source_fps=null,preview_fps=24,timebase_assumed=true를 유지한다. native 시간 보존을 주장하지 않는다. 기존 mask-given, 단일seed, 개발 패널, 데이터/학습 overlap UNKNOWN 조건을 유지한다.

## 4. 구현: 재인코딩 없이 기존 cache의 CLIP만 교차

기존 정상 baseline sampler/loader를 재사용한다. 새 attention 모듈, projection, RoPE 변경은 없다.

각 과제에서:
- Y12: R1 cache를 복사하고 양 CFG의 clip_fea만 R2에서 가져온다.
- Y21: R2 cache를 복사하고 양 CFG의 clip_fea만 R1에서 가져온다.

이 방법이면 reference VAE와 mask의 공간 정합을 그대로 보존한다. 원본 cache는 읽기 전용으로 두고 파생 cache를 별도로 만든다. 교차 출처를 경로명만이 아니라 각 tensor hash와 부모 metadata로 기록한다.

예상 변경은 행의 기준 cache에 대해 양 CFG clip_fea 2leaf다. 기존 16leaf 계약이 유지되는 경우 나머지14leaf는 같아야 한다. 특히 source driving/mask, positive/negative text, reference VAE/mask, 실제 noise, generator state, timesteps/sigmas, 모드·shape·dtype·device·container 구조를 보존한다. 현재 코드의 실제 tree를 확인하고 숫자만 맞추는 검사를 하지 않는다.

정식 replacement=True,history/additional_ref=None,LoRA/ALG/manualRoPE/B029 gate OFF다. 원래 upstream forward를 사용하고 소스 hash·활성 모듈 기록으로 확인한다. 이전 프로세스가 종료됐다는 이유만으로 OFF를 가정하지 않는다.

새 encoder·target 인코딩·prefix 추출·baseline 재생성은0회다. 첫 실제 forward의 두 CFG에서 선택한 ref/CLIP/mask가 연결되는지 작게 기록하고 관측용 추가 DiT forward를 실행하지 않는다.

## 5. 기존 결과를 먼저 보고 판별 항목을 고정

새 sampler 전에 기존 Y11/Y22, R1/R2, SOURCE를 열어 관측표를 고정한다. 알려진 보고서가 아니라 실제 보이는 항목을 우선한다.

human: 팔 배치, 치마 펼침/들림, 얼굴 가림, reference의 가림 실루엣, 하단 서명/추가 획, source 스텝의 순서.
vehicle: 차체 높이·창/루프 비율·방향·회전, source형 차체 잔존, 별도 차량 그래픽/문자, 도로·건물 보존.

R1/R2를 구분할 실제 시각 증거가 없다면 '경로가 무엇을 따른다'고 임의로 평가하지 않는다. 출력 관측 항목 3~5개와 불확실한 항목을 나누고 source/target의 실제 픽셀을 교체 정답으로 취급하지 않는다.

local0/8/16과 전체17장, 동일 preview24fps 영상을 제공한다. 새로운 보정·ROI합성·얼굴복원·문자제거·SR·보간·warp·출력별 시간정렬은 하지 않는다.

## 6. 실행 범위와 안전

- 신규 full sampler 최대4회: human Y12/Y21, vehicle Y12/Y21 각각1회. 실패/중단 포함, 자동재시도0.
- 각 UniPC40step,shift3,CFG5, 기존 seed20261022와 실제 동일 초기 noise, 80forward. 해당 final latent decode각1회.
- 신규 GPU encoder0,학습0,패키지/모델/데이터다운로드0,imagegen/외부생성0.
- 준비·CPU 검사 목표상한30분, 전체 작업상한3시간. 동일 작업의 실제 실행/완료 여부 확인 후 시작한다. 다른 작업 중단/병렬GPU 실행 금지.
- 기존 phase 분리·tiny CUDA·메모리 가드·swap0·다른 서비스 보호를 유지한다. 기존 guard 완화·새driver/커널 설치·다른 프로세스 종료는 하지 않는다.
- 첫 출력의 품질이 나쁘다는 이유만으로 남은 고정 셀을 생략하지 않는다. 입력 불일치·비유한값·자원 안전 문제는 중단한다.
- final latent를 decode 전에 저장하고, D 실패로 sampler를 다시 실행하지 않는다.

전체 14B OFF 수치 재현·변환 검증·커널 backward·사용권 반복 감사를 다시 하지 않는다. 이번 변경의 cache 출처·expected-diff·실제 연결만 확인한다.

## 7. 해석: 경로 효과와 상호작용을 구분

VAE+mask를 고정한 Y11 vs Y12, Y21 vs Y22는 CLIP 사진 조건 변경의 영향을 본다. CLIP를 고정한 Y11 vs Y21, Y12 vs Y22는 VAE+mask 묶음 변경의 영향을 본다. 서로 다른 행/열 비교로 identity/pose가 완전히 분리됐다고 주장하지 않는다.

사전에 정의된 scalar 관측 q가 실제로 있다면
I = q22 - q21 - q12 + q11
은 이 고정 예제의 기술적 상호작용 요약일 뿐이다. 신뢰할 q가 없으면 정성적 표로 충분하다. 임의 quality score·통계적 유의성·성공률을 만들지 않는다. 픽셀거리나 attention 크기를 실제 개체/동작 점수로 대체하지 않는다.

결정 분기:
1) 서로 다른 CLIP에서도 특정 자세·형태가 일관되게 VAE+mask 행을 따른다면, 이 범위에서 해당 묶음에 대한 조건부 의존 증거다. 다음 개입 표적 후보로 남기되 VAE 단독/공간 좌표 원인으로 확정하지 않는다.
2) 특정 외형/장식이 열을 일관되게 따른다면 CLIP 입력 정보와 출력 gate를 구분해 해석한다. B029 실패를 뒤집지 않는다.
3) 교차 셀만 크게 붕괴하거나 영향이 일관되지 않으면 경로 상호작용 또는 distribution mismatch로 INCONCLUSIVE. 무작정 VAE gate를 설치할 근거로 사용하지 않는다.
4) 양 경로를 바꿔도 source-copy가 지속되면 그 한계를 기록한다. 참조 zero-out/새scale/layer sweep을 자동 추가하지 않는다.

누락된 얼굴/차체의 실제 정체성은 UNCERTAIN, 실제속도 연속시청이 없으면 temporal=UNVERIFIED다. 이 패널은 개발에 사용했으며 미사용 일반화 자료가 아니다. 네 신규 output과 프레임을 독립 연구 반복으로 세지 않는다.

## 8. 다음 방법의 종료 기준

이번은 한번의 경로교차 진단이며 또 다른 가중치/마스크 숫자 sweep의 시작이 아니다. 결과가 뒷받침할 때만 VAE 토큰 전달 제어, 학습된 appearance adapter, 또는 명확한 reference-aware 편집 계약을 가진 다른 backend 중 다음 한 방법을 제안한다. 다음 kernel/adapter/모델을 자동 구현·실행하지 않는다.

'한 경로가 더 중요하다'는 진단 자체를 새 논문 방법으로 부르지 않는다. 이후 방법은 기존 모듈 대비 실제 외형·동작·보호 장면의 공동 개선과 비용을 검증해야 한다. 미지의 인과가 확인되지 않았다고 연구를 포기하지도 않고, 반대로 새 경로가 반드시 정답이라고 주장하지도 않는다.

## 9. 공부·기록·제출

한국어 해설은 VAE latent prefix+mask와 CLIP image context의 실제 코드 연결, 두 경로가 모두 자세·외형을 가질 수 있는 이유, 2x2의 조건부 비교와 상호작용, mixed-reference의 학습분포 이탈을 수식·코드·실제 출력에 연결한다.

착수 전 PLAN/입력/비교표/예산을 고정하고 HISTORY·ROADMAP에 B028/B029 NOT_ADOPTED와 이번 질문을 연결한다. 종료 후 RESULTS,CONDITIONS,MATRIX_REVIEW,COSTS,REPRODUCE,lessons를 작성하고 연구 브랜치에 commit/push·원격 SHA 확인. 과거 실패와 상태는 삭제하거나 소급 PASS하지 않는다.

코드·설정·평가 기준은 공개 가능 범위로만 기록한다. 개인자료·대형weight·cache·latent·secret은 GitHub에 올리지 않고 공개 데이터의 재배포 조건도 유지한다.

full과 compact를 분리한다. full에는 신규 raw/latent4쌍, compact에는 원본/참조/기존대각4출력/신규교차4출력·검토 HTML·보고서·재현 및 hash 명세를 넣는다. 기존 MP4 재인코딩은 하지 않는다. compact에서 빠진 duplicate PNG는 가벼운 프레임 추출 스크립트로 복원 가능하게 하고, raw/latent까지 독립 검증된 compact라고 하지 않는다. 대형weight/중복cache 제외. 단일 compact ZIP을 Mac/Spark /tmp에 보존하고 전송·CRC·manifest·실제 추출·바이트 동일성을 실제로 검사한다.

최종 보고는 (a)무엇이 어느 조건을 따랐나 (b)어느 비교가 불확실했나 (c)다음 방법 표적으로 쓸 근거가 있나 (d)실제 출력과 비용을 먼저 제시한다. 자체 프로세스만 종료하고 추가 실행·예약은 하지 않는다.

## 근거와 이번 검토 범위

- B029: ../B-029-spatial-image-conditioning/RESULTS.md, METHOD.md, NEXT_DECISION.md, code/spatial_image_gate.py
- B028: ../B-028-object-reference-normalization/RESULTS.md
- B027: ../B-027-public-reference-robustness/CASES.md 및 기존 cache manifest
- 공식 SCAIL 고정소스: https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py

이번 문서 작성자는 원격 보고서·실제 gate 코드·공식 입력 경로를 읽었다. 첨부 compact ZIP은 container와 Python이 ClientError를 반환해 읽지 못했으므로 실제 영상·ZIP CRC/hash를 독립 확인하지 않았다. 시각 판단은 B028/B029 보고서의 관측 범위이고, 이 문서로 새 품질 판단을 확정하지 않는다.

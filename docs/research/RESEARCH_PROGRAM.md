# 이미지·영상 생성 연구 프로그램 — 원리 이해에서 독립적인 논문 기여까지

작성: 2026-10-23. 상태: 연구 방향·운영 원칙 확정, 아래 가설은 미검증 후보. 이 문서는 새 GPU 실행·다운로드·학습 예산을 승인하지 않는다.

## 0. 사용자의 목표와 현재 실행의 경계

사용자는 실제 반려동물 영상이라는 응용을 해결하는 동시에, **이미지·영상 생성 모델의 수학, 아키텍처, 메커니즘을 이해하고 직접 실험·학습·개선하는 연구**를 원한다. 유망한 접근을 폭넓게 검토하고 독립적인 기여가 확보되면 CVPR/ICCV/ECCV 또는 NeurIPS/ICLR/ICML 등 연구 내용에 맞는 주요 학술대회의 본회의 논문 제출을 목표로 한다. 게재·성능·새로움을 미리 보장하지 않는다. 서비스 가치, 학습 성과, 논문 기여를 따로 평가한다.

반려동물 춤은 유용한 출발 사례이지 연구 범위의 영구적인 한계가 아니다. 영상 생성의 조건 분리, 시간적 일관성, 표현, 학습 목표, 샘플링과 효율성까지 다룬다. 특정 모델 실행 대행이나 한 밈의 프롬프트 최적화로 프로젝트를 축소하지 않는다.

현재 B-007F는 사용자가 실행 지시를 전달했다고 보고했다. 이 문서 작성은 해당 실행의 완료·진행 상태를 독립 확인한 것이 아니다. **B-007F의 코드·예산·실험 조건·연구 브랜치를 중간에 변경하지 않는다.** 이번 문서는 별도 문서 브랜치에만 추가하고 기존 실행이 종료된 후 문서 변경만 검토·반입한다.

A(native imagegen 전용 MCP)와 B(로컬 모델 연구)는 계속 독립이다. B의 시각 입력·학습 target에 A의 imagegen 산출물을 사용하지 않는다. 공개 사전학습 가중치의 제작 이력과 우리 로컬 실험에서 새로 만드는 데이터의 출처는 별도 기록한다.

## 1. 성과를 네 층으로 분리한다

| 층 | 질문 | 남길 증거 |
|---|---|---|
| 실행 기반 | 코드·가중치·커널·메모리·decode가 동작하는가? | 재현 명령, phase trace, 실제 출력/실패, 자원 수치 |
| 원리 학습 | 사용자가 수식과 코드로 동작을 설명할 수 있는가? | 유도·shape 추적·작은 실험·질문과 해설 |
| 연구 기여 | 기존 방법에 없는 지식/방법/평가를 검증했는가? | 선행 연구 차이, 반증 가능한 가설, 통제 실험, 일반화 |
| 응용 | 제한된 사용자 과제를 반복해서 해결하는가? | 개체·동작·시간 품질, 실패 포함 비용, 사용자 검토 |

모델을 Spark에서 실행하거나 CPU offload 한 줄을 바꾼 사실만으로 주요 학회 논문의 새로움을 주장하지 않는다. 반대로 작은 개입이어도 새로운 일반적 발견·명확한 분석·넓은 검증이 있으면 연구 후보로 검토한다. 재현·측정·실패 분석도 학습 자산이다.

## 2. 학습은 모든 실험에 결합한다

모든 주요 실험은 **질문/직관 → 수식과 가정 → 텐서 shape → 실제 고정 코드 → 작은 확인 실험 → 실제 결과 → 한계/반례 → 이해 질문/해설**의 연결을 갖춘다. 분량을 채우는 논문 요약이나 용어사전 대신 이번 실험과 관련된 개념 1~2개를 깊게 다룬다.

| 학습 축 | 깊이 이해할 내용 | 실제 연결 |
|---|---|---|
| 생성 수학 | DDPM, score/SDE와 probability-flow ODE, Flow Matching/rectified flow, 예측값 parameterization과 loss weighting | toy 분포, 실제 noise scheduler/target/solver |
| 압축 표현 | VAE/영상 VAE, KL·재구성, 시간·공간 압축, latent scaling, decoder receptive field/cache | encoder–decoder shape, 같은 latent decode 비교 |
| 생성 아키텍처 | U-Net 대 DiT, patch/token, self/cross attention, RoPE/위치, 시간축/공간축 결합 | Q/K/V 출처, 조건 token과 연산량 |
| 조건화 | reference, RGB driving, pose/flow/mask, CFG, context adapter, 외형 누수 | 실제 조건 교체와 내부 feature/출력 반응 |
| 시간 생성 | 전체 클립 비인과 attention, causal/AR 방식, history conditioning, 긴 구간 이음 | 짧은 클립과 컷/장기 생성의 차이 |
| 학습 개입 | paired target, LoRA·adapter·부분 layer 학습, overfit와 일반화, 증류·preference 학습 | gradient·optimizer·train/val 실험 |
| 추론/시스템 | ODE solver, step/CFG 비용, activation·weight, memory lifetime, 양자화·distillation | 같은 품질 조건에서 시간·메모리 비교 |
| 평가 | identity/motion/shape/timing, 불확실성·가림, 추정기 편향, 실패율 | 원본·참조·출력과 사람 평가 |

이 목록은 학습 지도이지 모두 설치·학습하라는 실행 지시가 아니다. B-007F의 경우 최종 latent와 픽셀 decode의 분리, 메모리 수명, CPU/GPU 통합 메모리를 우선 이해한다. sampler 실행 가능성이 영상 의미/품질 성공을 보장하지 않음을 유지한다.

## 3. 폭넓은 탐색과 집중의 균형

'좋아 보이는 것을 다 시도한다'는 것은 무제한 모델 다운로드나 seed 탐색이 아니다. 후보를 기록하고 다음 순서로 값싼 반증부터 진행한다.

**원 논문/공식 코드 확인 → 가장 가까운 선행 방법과 차이 → 작은 재현/반례 → 소규모 실제 과제 → 한 개입 비교 → 미사용 데이터 확장**.

동시에 깊게 진행하는 주력 가설은 하나, 비교 후보는 소수로 유지한다. 확인하지 않은 후보도 BACKLOG로 남겨 버리지 않는다. 임시 비율이나 고정 GPU 횟수를 모든 연구에 강제하지 않는다. 각 실험에서 필요한 실행 예산·고정 변수·최소 성공과 기각 조건을 미리 정한다.

입력 sensitivity를 확인하기 위한 회색/검정 대체 실험은 B-005에서 일단 종료했다. 현재의 커널/serialization/메모리 작업은 연구를 가능하게 하는 기반이며, 끝없이 검사 시스템을 확장하는 연구가 되어서는 안 된다. 이미 검증된 경로를 바꾸지 않았다면 동일한 큰 감사를 반복하지 않는다. 단순 문서·plot 수정마다 새 승인 상태 머신을 만들지 않는다.

## 4. 논문 후보를 고르는 기준

새 아이디어마다 다음 여섯 질문에 짧게 답한다.

1. 정확히 어떤 관측 가능한 실패를 해결하는가?
2. 가장 가까운 기존 논문/코드가 무엇이며, 이미 같은 해결을 제시했는가?
3. 우리가 바꾸는 모듈·데이터·학습 목표·추론 규칙은 정확히 무엇인가?
4. 왜 작동해야 하는가? 무엇이 나오면 가설을 기각할 것인가?
5. Spark에서 가장 작게 검증하려면 어떤 데이터/target/연산이 필요한가?
6. 한 영상을 넘어 미관측 개체·동작·체형 또는 다른 모델에서 성립하는가?

단순 모델 조합, LoRA 적용 자체, '동물에 사용했다', 새 loss 여러 개를 합친 사실만으로 새로움을 주장하지 않는다. 기술 기여가 방법이 아니라 benchmark/데이터/실증적 발견이면 그 기여 유형을 솔직히 명시한다.

## 5. 우선 검토할 가설 후보 — 전부 미검증

### H1. 참조의 자세 누수와 개체 정체성을 분리할 수 있는가?

동일 개체의 서로 다른 자세 사진 R^a,R^b, 동일 driving D와 초기 noise ε를 사용해 Y^a=G(ε,D,R^a), Y^b=G(ε,D,R^b)를 비교한다. 개체가 같은 상태에서 참조 자세가 달라지는 개입은 이전의 '사진 전체를 회색으로 교체'보다 질문에 직접적이다. 다만 사진의 카메라/조명/가림도 달라질 수 있으므로 paired 촬영·라벨·잔여 confound를 기록한다.

진단 지표 후보는 d(φ_motion(Y^a),φ_motion(Y^b))다. 이것만 줄이면 둘 다 정지해도 통과할 수 있으므로 **driving 추종, 실제 개체, 동작 크기와 타이밍**을 동시에 확인해야 한다. φ_motion을 어떤 관측/추정기로 정의할지와 동물 분포에서의 오차부터 검증한다. 서로 다른 체형에서 원본의 모든 픽셀/관절 위치를 그대로 복제하는 것을 정답으로 정의하지 않는다.

개입 후보: condition별 시간/층/공간 주입, appearance-conditioned adapter, counterfactual pair 학습. 구체적 선택은 baseline 출력과 literature gap에 근거한다. 새 논문 기법이라는 주장은 아직 하지 않는다.

### H2. 가림·표현 불확실성·체형 차이에 따라 동작 조건을 다르게 신뢰할 수 있는가?

확실히 보이는 표면점/영역과 관측 불가 영역을 구분하고, 원본 윤곽을 강제할 영역과 목표 체형의 생성 문맥에 맡길 영역을 다르게 처리하는 조건 주입을 검토한다. visibility, 측정 오차, 실제 3D 접촉은 다른 변수다. unknown을 좌표0이나 가짜 관절 정답으로 바꾸지 않는다.

원본의 얇은 몸을 더 큰 목표 체형에 맞출 때 'source 형태 복사'와 '동작 이벤트·방향·타이밍 보존'을 분리하는 평가가 필요하다. 같은 category에서도 변화가 큰 경우와 다른 category 사이를 구분한다. attention map의 상관만으로 원인을 증명하지 말고 통제된 intervention을 사용한다.

이 문제 범위는 SCAIL-2와 Motion Beyond Morphology 등과 겹친다. 특정 실패·데이터 조건·새 mechanism에서 검증 가능한 차이를 확보하기 전 독창성을 선언하지 않는다.

### H3. 제한된 통합 메모리에서 영상 생성의 품질을 유지하며 실행을 일반화할 수 있는가?

sampler/decoder 분리, phase별 memory lifetime, model offload·cache·tiling·batch의 장단점을 분석한다. 하나의 장비·모델에서 CPU 이동 한 줄 생략 성공은 엔지니어링 결과다. 연구 후보가 되려면 일반적인 정책/모델, 여러 구조·해상도·길이·장비 또는 조건, 강한 기존 memory manager와 비교, 실제 품질·시간·총 메모리 비용을 보여야 한다. 현재는 주력 생성 연구를 지원하는 보조 축이며 B-007F 결과만으로 논문 주제로 확정하지 않는다.

H1~H3를 동시에 구현하지 않는다. 최초 출력 확보 후 evidence·novelty·compute 기준으로 하나를 선택한다. 다른 생성 아키텍처나 학습 방법도 근거가 좋으면 후보로 추가할 수 있다.

## 6. 현재 확인한 선행 연구 지도와 겹침 경고

아래는 2026-10-23에 원문 페이지/공식 가이드를 확인한 출발점이다. 모든 논문의 실험 코드 재현이나 전수 문헌조사를 완료했다는 뜻이 아니다.

- **Latent Diffusion Models** — https://arxiv.org/abs/2112.10752 : 압축 공간 생성·조건화의 기초. 우리의 latent 사용 자체는 기여가 아님.
- **Scalable Diffusion Models with Transformers (DiT)** — https://arxiv.org/abs/2212.09748 : latent patch transformer와 규모의 관계. DiT에 LoRA를 붙인 사실만으로 새로움이 생기지 않음.
- **Flow Matching for Generative Modeling** — https://arxiv.org/abs/2210.02747 : 조건 확률 경로의 vector field 회귀. FM 사용 자체와 새로운 조건 학습/분석을 구분.
- **SCAIL-2, v3** — https://arxiv.org/abs/2606.10804v3 : end-to-end latent visual driving, MotionPair-60K, mask/RoPE 조건, Bias-Aware DPO. reference+driving 결합·여러 animation task는 이미 다루는 영역.
- **Motion Beyond Morphology (2026-08-03)** — https://arxiv.org/abs/2608.01628 : 형태·category 차이를 넘는 동작 전이, abstract motion views, 직접 video-conditioned 학습과 OpenVMT 평가를 제안. '체형이 다른 동작 전이'라는 큰 질문만으로 독창성을 주장하지 않는다. 공개 여부·수용 여부·재현 가능성은 별도로 확인하며 최신이라고 무조건 설치하지 않는다.
- **VBench** — https://arxiv.org/abs/2311.17982 : identity consistency, motion smoothness 등 분리 평가의 참고. generic 영상 지표를 실제 개체/동작 정답으로 취급하지 않는다.
- **CVPR 2026 Reviewer Guidelines** — https://cvpr.thecvf.com/Conferences/2026/ReviewerGuidelines : 기술적 타당성·새로움·영향과 성능을 함께 평가. 단순 SOTA 수치 하나만의 경쟁으로 축소하지 않는다.
- **NeurIPS Paper Checklist** — https://neurips.cc/public/guides/PaperChecklist : 주장 범위, 재현성, 불확실성, 계산 자원, 데이터 출처와 한계 기록의 기준. 제출 연도의 실제 규정을 다시 확인한다.

논문 표에는 향후 publication/date/version, problem/input, mechanism, training target/data, released code/weights/license, compute, reported failure, 우리와의 차이, 실제 읽은 범위를 기록한다. preprint와 peer-reviewed acceptance를 혼동하지 않는다. 인용·수식·수치는 원문 확인 없이 생성하지 않는다.

## 7. 평가·데이터 설계

한두 장의 사진, 한 밈, 두 seed는 디버깅과 가설 탐색이지 일반화 평가 세트가 아니다. 원본 FPS·길이·카메라 변화·가림·체형 격차가 드러나는 여러 독립 clip으로 확장하되 다음 구분을 지킨다.

- train/development/test는 scene·identity·motion 출처 단위로 분리한다. 인접 frame을 독립 표본 수로 세지 않는다. 같은 입력의 seed만 늘려 독립 개체가 늘었다고 주장하지 않는다.
- prototype에서는 작은 split으로 빠르게 반증하고, 주력 가설을 정한 뒤 별도의 holdout을 잠근다. 탐색 중 본 결과를 나중에 blind test처럼 표시하지 않는다.
- identity, morphology, motion direction/amplitude/event timing, occlusion recovery, anatomy, temporal artifacts, background, failed-run 비용을 분리한다.
- 정지 영상을 높은 temporal consistency로 보상하지 않는다. 발 미끄러짐/눈감기/킥 peak는 관측 가능한 경우에만 평가한다. 불확실한 contact를 가짜3D truth로 취급하지 않는다.
- cross-identity 전이에는 진짜 target video가 없을 수 있다. 이 경우 원본 RGB와의 PSNR을 품질 정답으로 사용하지 않는다. pair가 있는 synthetic 데이터의 결과와 실제 도메인의 결과를 따로 보고한다.
- generic embedding의 동물 개체 식별력·pose estimator의 unusual 직립 오차를 먼저 검증한다. 정적 시트·자동 지표만으로 실제 속도 재생을 관찰했다고 쓰지 않는다. 사람의 재생 검토와 가능하면 조건을 가린 쌍대 비교를 포함한다.
- 모든 시도·seed·실패·선별 기준·비용을 남긴다. 평균·분산/신뢰구간은 표본 단위와 의존성에 맞게 산출한다. 불충분한 n으로 유의성을 주장하지 않는다.
- 학습용 실제 Lab target가 없는데 다른 개의 driving을 Lab 정답으로 사용하지 않는다. 새 데이터의 촬영·수집·합성 출처, 권리·동의·개인정보·annotation uncertainty를 기록한다.

Spark는 주 실험 장비다. 작은 모델로 개입과 학습을 검증하고 실제 큰 모델에서 전이 가능성을 확인할 수 있으나, 큰 모델의 추론 성공을 동일 장비의 전체 학습 가능성으로 확대하지 않는다. 필요한 추가 계산 자원은 성과·측정치에 근거해 별도 제안하며 자동 대여하지 않는다.

## 8. 논문을 결과 마지막에 급히 만들지 않는다

가설이 정해지면 papers/<working-id>/에 다음을 최소한으로 관리한다. 지금 빈 파일 수십 개를 미리 만들지는 않는다.

- CLAIMS.md: 한 문장 주장, 가장 가까운 기존 방법, 지지 실험, 반증 실험, 현재 근거 수준.
- RELATED_WORK.md: 문헌 차이표와 확인한 source/version.
- EXPERIMENT_MATRIX.md: baseline/ours/ablation/data split/compute parity.
- DRAFT.md 또는 manuscript.tex: 문제·방법·필요한 증거의 뼈대. 미완료는 TODO/NOT_RUN. 결과 수치·가짜 인용 금지.

논문 수준으로 넘어가는 조건은 **중요한 실패의 재현 → 설명 가능한 한 개입 → 적합한 강한 baseline 대비 개선/새 발견 → 구성요소 제거 검증 → 미관측 조건에서 재현 → 한계 공개**다. 모든 경우에 모든 benchmark의 SOTA를 요구하는 것이 아니라 주장에 맞는 실증을 요구한다.

비전·조건부 생성 방법은 CVPR/ICCV/ECCV, 더 일반적인 학습/생성 원리는 NeurIPS/ICLR/ICML 등을 후보로 삼되 결과와 기여에 맞춰 선택한다. 지금 특정 연도 마감·게재를 약속하지 않는다. 본회의, Findings, workshop, technical report를 혼동하지 않는다.

공개 GitHub 이력은 연구 자산으로 계속 유지한다. 제출 시에는 해당 연도의 익명 심사·사전 공개·코드/영상 링크·AI 도구 사용 정책을 확인해 익명화된 제출물을 별도로 준비한다. 공개된 repo를 감추려고 과거 연구 기록을 파괴하지 않는다. 최종 주장·실험·인용·저자 책임은 사람 연구자가 검증한다.

## 9. 실행자 지속 지침과 다음 시점

현재 B-007F의 조건·예산은 그대로이며 본 문서로 확대하지 않는다. 완료 후 이 문서의 원칙을 연구 브랜치에 **문서 변경만** 반입하고 CHARTER/AGENTS 링크와 HISTORY/ROADMAP을 갱신한다. 로컬 dirty 파일/이전 연구 결과를 강제 덮어쓰지 않는다.

후속 작업부터 PLAN의 맨 앞에는 (1) 실제 응용 목표, (2) 이번에 배울 원리, (3) 검증할 가설과 기존 연구의 차이, (4) 반증·중지 기준을 짧게 적는다. RESULTS에는 실제 관측과 설명, 미확인, 다음 한 실험을 분리한다. 동일 사실을 여러 문서에 길게 복제하지 않는다.

새 실험마다 논문을 약속하지 않는다. 기반 작업이 길어지면 범위를 줄여 실행 가능한 baseline으로 돌아가며, 안전 가드를 우회하지 않는다. 중요한 것은 **볼 만한 결과, 이해한 메커니즘, 남에게 검증 가능한 새로운 주장**이 함께 축적되는 것이다.

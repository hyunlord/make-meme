# 2026-10-26 — B-028 결과 이후 실제 생성 경로 개입으로 전환하는 의뢰

## 상태와 사용자 목표

사용자는 공개·다중 사례에서 재현되는 로컬 객체 편집 방법을 연구하고, 개인 DGX Spark에서 품질과 비용을 개선하려 한다. 특정 반려견 사진의 추가 확보를 연구의 진행 조건으로 삼지 않는다. 이번 요청은 이 방향으로 진행할 통합 작업 의뢰서 작성이다.

현재 조회한 연구 HEAD는 `ebd728c4c48823f6d7f627174370455ec1736138`이고 B-028 PLAN은 PLANNED/NOT_RUN으로 표시된다. 이 원격 문서만으로 다른 worker의 현재 로컬 실행 여부를 단정하지 않는다. 작업자는 새 실행 전 실제 상태를 확인한다.

이번 기록 작성 중 GPU 생성·학습·설치·다운로드는 0회다. B-029의 최종 원인·방법·실행 계획은 아직 확정하지 않았다. 기존 B-028, 다른 실행 코드, 가중치, 결과는 수정하지 않는다.

## 전달 의뢰서

사용자에게 제공한 완전한 Markdown 의뢰서의 파일명은 `B028_TO_METHOD_RESEARCH_WORK_ORDER_KO.md`다.

SHA256: `43d6cfeada91b46ccdc01b3e88e1227506f7839e61cc912889bec1f5063457c1`

실행 담당자는 사용자가 전달한 이 문서 전체를 `docs/research/work_orders/`에 먼저 기록한 뒤 최신 상태에 맞춰 작업한다. 이 결정 문서는 그 요약이며, 더 상세한 입력·연산·자원 계약을 축약해 대체하는 문서가 아니다.

## 순서와 분기

1. 이미 실행 중인 B-028을 끊거나 중복 GPU 작업을 시작하지 않는다. 완료 결과는 재사용한다. 미착수라면 원래 B-028 6회 한도 내에서 먼저 수행하며 실패·완료 case를 재실행하지 않는다.
2. 전체 3과제×2참조의 외형·동작·형태·보호 장면을 검토한다. B-027 또는 B-028 중 하나를 패널 공통 기준선으로 고정하며 case별 best-of 조합을 만들지 않는다.
3. 문제가 남으면 생성 경로 개입 하나를 선택·구현하고 같은 패널에 적용한다. B-028 결과 전에 원인이나 효과를 확정하지 않는다.
4. 이미 세 과제의 두 참조 모두 관측 가능한 결합 목표를 충족했다면 불필요한 새 모듈 대신 미사용 공개 조합 2개에서 기준선만 검증한다. 방법 실험과 이 분기를 동시에 수행하지 않는다.
5. 구체적인 실행·입력 오류가 발견되면 그 영향을 먼저 구분하고, 버그 수정과 방법 변경의 효과를 섞지 않는다.

## 코드에 근거한 우선 후보 — 미검증 가설

고정 SCAIL `78fe19576bb06be96c2375e088574a262a300edb`의 `wan/modules/model_scail2.py`를 직접 읽었다. `WanI2VCrossAttention`은 이미지와 텍스트 attention 출력을 별도로 계산해 더한 뒤 `self.o`를 적용한다.

우선 후보는 기존 학습된 이미지 cross-attention 출력의 생성 query 위치별 재가중이다.

- 기준: `O = W_o(T + I) + b_o`
- 후보: `O = W_o(T + g * I) + b_o`
- `g = 1 + 0.5 * (E - mean_spatial(E))`, generated query에만 적용
- reference와 driving query의 계수는1, 양 CFG·모든 해당 block/step에 공통 규칙
- 기존 CLIP 가중치·VAE reference self-attention·RoPE·text·noise는 유지

E는 source 객체 mask에서 고정 팽창·경계 완화·token 시간/공간 대응을 통해 만든다. 정확한 VAE receptive field나 새 대상의 정답 alpha가 아니고, 체형 변화·가림에 대한 한계가 있다. 공간평균 계수가1이라는 것만 보존되며 feature norm·attention 확률·총 참조 영향이 보존되는 것은 아니다.

같은 계수 분포를 유지하면서 E를 고정 공간 이동한 음성 대조를 두 case에서 사용한다. lambda0/OFF 기능 검사와 이 대조는 서로 다른 설명을 검사한다. 임의의 random adapter를 붙이거나 새 학습 모듈을 훈련 없이 유효하다고 취급하지 않는다.

참조 외형 주입과 보호 문맥을 구분하는 데 이 경로가 적합한지 B-028 결과로 판단한다. 후보가 맞지 않으면 기존 모델·입력 안에서 가능한 대체 개입 하나를 사전 구체화한다. 이를 못 하면 METHOD_NOT_READY로 남기며 문서 작성만으로 방법 구현을 완료했다고 보고하지 않는다.

## 범위

- 방법 분기: METHOD6개 + 사전 고정 CONTROL2개, 새 full sampler 최대8회. 기준선은 재사용.
- 각40step/80forward, endpoint별decode1, 실패 포함, 자동재시도0.
- B-028까지 미착수라면 기존6회와 합쳐 최대14회. 이미 수행한 호출은 중복하지 않는다.
- B-028이 이미 모두 충분히 개선된 경우의 별도 분기: 미사용 공개 조합 최대2회만.
- 총 작업 상한8시간, 새 방법 설계·구현·소형 검사 최대2시간.
- 새 학습·대형모델·패키지·원격 생성·imagegen0. 기존 가중치를 이용한 추론 경로 실험.
- 기존 단일GPU 순차실행·메모리 가드·swap0·타서비스 보호와 final latent 선저장 유지.
- 새로운 본격 학습, 다른 backend, 비용 최적화, 두 개체/긴 영상은 이번에 자동 실행하지 않는다.

## 성과·기록 기준

동일 개발 패널에서 외형·동작·장면을 함께 개선했는지 먼저 보고한다. source-copy·참조 정지 복사를 성공으로 세지 않는다. 6출력/102프레임은 독립 반복이 아니고 공개 패널은 미사용 test가 아니다. 실제 연속 시청이 없으면 temporal=UNVERIFIED다.

공간 reference masking과 decoupled cross-attention은 기존 연구가 있으므로 이 후보 자체를 새 논문 방법이라고 주장하지 않는다. 개선이 생겨도 미사용 자료 검증과 선행 방법 비교가 필요하다. 여러 조건에서 이득이 없으면 lambda/layer/scale sweep을 이어가지 않고 가설의 한계와 다음 질문 하나를 기록한다.

실행자는 원본 의뢰서, 최종 선택 PLAN/DECISION, HISTORY/ROADMAP, METHOD/RESULTS/ABLATIONS/COSTS/REPRODUCE/한국어 lessons를 연결한다. 작업 전·후 remote SHA와 상태를 기록한다. full/review-lite ZIP을 분리하고 개인 미디어·latent·가중치는 공개하지 않는다.

## 참고한 1차 자료

- 고정 SCAIL 구현: https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py
- IP-Adapter: https://arxiv.org/abs/2308.06721
- Diffusers의 IP-Adapter 공간 mask 문서: https://huggingface.co/docs/diffusers/using-diffusers/ip_adapter
- VideoPainter: https://github.com/TencentARC/VideoPainter

이는 구현 가능한 후보와 선행 방식을 확인한 문헌·코드 검토이며, 새 방법의 품질·Spark 실제 효과를 확인한 실행 결과가 아니다.

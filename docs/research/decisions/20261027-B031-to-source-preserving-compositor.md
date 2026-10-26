# 2026-10-27 — B031의 단계별 실패와 원본 보존 합성 기준선

## 확인과 결정

B031 RESULTS/ANCHORS 및 연구 HEAD `3e669f0f5b284cc9ec178959b4f35e2129896788`를 원격에서 읽었다. Animal/human R1은 이미지 앵커부터 source 자세를 따르지 않아 영상 NOT_RUN이다. Vehicle R1은 target형 차체/원본 방향의 앵커를 만들고 영상에서도 외형/거친회전의 부분 근거를 얻었지만, 앵커에 없던 도로 그래픽으로 보호 장면을 실패했다. 결합 목표 FAIL, 정확 instance UNCERTAIN, temporal UNVERIFIED를 보존한다.

다음 제안인 생성 중 원본 문맥 보존은 미검증 가설이다. 곧바로 새로운 sampler 제약이나 backend를 설치하기보다, 이미 가진 source와 생성 raw를 결합하는 가장 싼 대조군을 먼저 만든다. 비용에 민감한 개인 Spark 목표에서 새로운 추론 비용이 필요한 이유를 그 결과로 판단한다.

실행 제안: [B-032 PLAN](../experiments/B-032-source-preserving-composite-baseline/PLAN.md).

- 기존 vehicle_R1 raw만 사용, 새 GPU/인코더/샘플러/학습/모델설치0.
- Source+앵커 support에서 정한 고정 envelope와, source+실제 출력target support를 사용하는 mask-assisted 합성의 두 수준.
- 출력target support 사용/수동 작업을 숨기지 않고, source mask만으로 큰 target을 잘라내거나 source 잔상을 남기는 문제를 점검한다.
- 그래픽이 edit support 안에 있거나 경계·접촉 문제가 남으면 그대로 실패로 남긴다. source 보호영역 복사가 모델 능력이나 새로운 알고리즘인 것처럼 주장하지 않는다.
- Animal/human의 앵커 자세 실패는 해결되지 않았으며 범주 전체 성공으로 확대하지 않는다. 차량 사례 선택은 기존 적합한 앵커의 가용성 때문이며 새로운 결과 선택은 아니다.

## 연구 방향

V/R/P로 원본의 지정 장면·동작을 보존하며 대상을 바꾸는 보편적 로컬 편집 목표는 유지한다. A imagegen-only와 B local-only는 분리한다. 개인 사진을 요구하지 않는다. 이번 cheap comparator는 장기 원본보존/합성 설계의 실제 작은 구현이며, 모델 연구를 포기하는 결정이 아니다.

생성 중 context 보존을 후속에 연구한다면 RAW뿐 아니라 B032 compositor보다 경계·그림자·편집 내부·자동화/노동비용에서 나은 근거를 요구한다. RePaint/Blended Latent Diffusion 등의 기존 알려진 영역 제약·blend와 차이를 구분한다. source outside-region 오차만으로 새로운 방법이 우수하다고 판정하지 않는다.

## 범위·상태

현재 B032는 PROPOSED/NOT_RUN. 이번 게시에서 변경한 것은 계획·결정 문서뿐이다. 기존 결과·실행코드·weights는 수정하지 않았고 생성·학습·설치0회다. 실행 담당자는 사용자 수행 지시를 받은 뒤 최대90분 CPU 작업, support 준비 최대30분, 끝15분 전달·정리 조건을 적용한다. 후속 in-sampler 실험은 이번 의뢰 범위가 아니다.

작성 중 첨부 compact ZIP은 container/Python 실행 오류로 열지 못했다. 원격 보고의 시각 판정과 비용을 읽은 것이지, 실제 미디어와 ZIP payload를 독립 검증한 것은 아니다. 존재하는 사용자 업로드를 없다고 하거나 잘못된 sandbox 경로를 만들지 않는다.

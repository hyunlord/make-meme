# 2026-10-25 — B-025의 외형 반응과 참조 자세 의존을 구분

## 확인 범위와 사실

기준 commit `eb0f86ad3654315f3c0bd2de206461104b6df89f`의 B-025 RESULTS/CONDITIONS와 연구 HEAD를 원격 조회했다. 중립 caption·source·noise를 고정한 Lab/IG pair에서 외형 특징이 참조 방향으로 바뀌었지만 IG는 누운 자세를 유지했고 원본의 사족 자세·동작을 따르지 못했다. 장면 보존 PARTIAL, 정확한 개체일치 UNCERTAIN, temporal UNVERIFIED를 보존한다.

양 CFG의 reference RGB 유래 latent/CLIP와 semantic mask가 함께 바뀌었다. 따라서 이 pair는 reference-bundle 효과의 근거이지 순수 identity 또는 reference pose 하나의 인과효과가 아니다. '참조를 전혀 사용하지 않는다'는 설명은 관측된 외형 차이에 맞지 않지만, '정체성과 동작을 분리했다'는 주장도 성립하지 않는다.

첨부 ZIP을 실제 제공 경로에서 container와 Python으로 각각 읽으려 했으나 ClientError로 실패했다. 실제 이미지·연속영상·CRC/367 payload·Mac/Spark 동일성을 독립 검증하지 않았다. 시각적 판단은 원격 실행자의 정적 관측 기록에 근거한다.

## 결정

다음은 [B-026](../experiments/B-026-reference-pose-sensitivity/PLAN.md)의 조건부 참조 자세 적합성 진단이다. 같은 IG의 실제 사족 기립 사진 availability를 먼저 기존 허용 asset에서 짧게 확인하고, 없으면 REFERENCE_PENDING으로 한 번만 기록한다. 가짜 standing 이미지나 다른 개체로 대체하지 않으며 아직 GPU ready라고 선언하지 않는다.

자료가 확보되고 사용자가 수행을 지시하면 기존 IG_REST_MOV를 재사용하고 STAND_MOV/STAND_STILL 각1회(새 sampler 최대2회)를 비교한다. 두 새 결과는 같은 standing reference/text/noise에서 실제 driving과 첫 RGB+mask 반복 driving만 다르다. 단순히 standing 사진을 복사해서 선 영상이 나오는 것을 동작 전달 성공으로 세지 않기 위한 대조군이다. REST와STAND는 사진·시점·조명·support도달라질수있어순수pose효과라고하지않는다.

이것은 최종 목표를 '원하는 자세 사진을 사용자가 반드시 제공해야 한다'로 바꾸는 결정이 아니다. 참조 자세가 맞는 쉬운 조건에서 실제 교체가 가능한지 확인하여 연구 병목을 좁히는 것이다. 어려운 누운 참조 실패는 계속 보존한다. 장기 목표는 참조에서 외형을 얻되 원본의 동작·장면을 따르는 로컬 객체 편집이다.

모델·프롬프트강도·LoRA·ALG·RoPE·회색값·추가참조·생성후합성은 이번에 동시에 바꾸지 않는다. 입력이 없다면 새로운 smoke·감사·학습으로 자동 우회하지 않는다. standing source가 있더라도 움직임·개체·장면을 함께 달성해야 task사례로 수용하며, 한 pair를 일반화·상용급·논문기여로 확대하지 않는다.

## 기록 상태

B-025 완료/실패 이력은 불변. B-026은 PLANNED / REFERENCE_AVAILABILITY_UNCONFIRMED / GPU NOT_RUN이다. 이번 원격 변경은 계획·결정 문서 추가뿐, 새 생성·학습·모델 다운로드0회다. 실제 착수/자료대기/종료 때 실행자는 HISTORY·ROADMAP에 이 결정을 연결한다. 존재하지 않는 실제 standing 사진이나 완료 결과를 문서로 만들어내지 않는다.

## 공식 참고의 역할

공식 SCAIL-2는 motion transfer와 조건 분리를 이미 연구한다. 이번 같은개체 참조사진비교 자체를 새기법으로 부르지 않는다. 최신 공식README의multi-reference는기능후보일뿐 이번에는추가하지않고 고정실행버전을유지한다.
- https://arxiv.org/abs/2606.10804
- https://github.com/zai-org/SCAIL-2

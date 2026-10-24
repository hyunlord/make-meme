# 2026-10-24 — 로컬 영상 객체 편집으로 문제를 명확히 하고 B-023 우선

## 사용자 목표와 결정

사용자는 '원본 영상+참조 이미지+프롬프트를 입력받아 원본 장면·동작·타이밍을 유지하며 해당 객체를 치환/합성하고, 개인 DGX Spark에서 높은 완성도를 내는 것'을 연구 목표로 명시했다. 이론·수학·아키텍처 학습과 주요 학회 논문 목표는 유지하고, imagegen-only A와 local-only B 경계도 유지한다.

새 상위 계획은 [RESEARCH_V2_SOURCE_PRESERVING_EDITING.md](../RESEARCH_V2_SOURCE_PRESERVING_EDITING.md), 첫 실행은 [B-023 PLAN](../experiments/B-023-task-aligned-replacement/PLAN.md)이다. 문서 등록만 수행했으며 GPU/학습/새모델다운로드0이다.

## 앞선 제안에서 바로잡은 부분

- subject-only RGBA생성이 언제나fullframe보다싸고쉽다는주장은검증되지않았다. mask만으로dense모델토큰이줄지않고현재RGB모델이alpha를자동출력하는것도아니다.
- pose/flow/depth/3D를전부필수선행조건으로두지않는다. 원본scenecontext와mask/track로첫baseline을실행하고실패에필요한보조표현만추가한다.
- 원본객체위에새foreground를덮는것만으로제거된영역·가림·그림자가해결되지않는다. edit support는source/target실루엣·드러난배경·필요한scene변화를포함할수있다.
- animation 실패를source-preserving replacement 전체의한계라고일반화하지않는다. H120단독변경은공식replacement가아니다. 고정공식모드의task-aligned baseline을먼저확보한다.

## 검토 근거와 범위

기준연구HEAD `9940848b59d52537194aa7118792efb15ad9a8e8`의CHARTER/ROADMAP을원격에서읽었다. CHARTER의초기VACE중심문구와ROADMAP상단의B017요약은과거상태여서새방향링크로혼동을줄인다. 실행기록은삭제하지않는다.

고정SCAIL `78fe19576bb06be96c2375e088574a262a300edb`의README·wan/scail.py를확인했다. replacement는공식입력모드로제공되고마스크/caption/모델위치계약을함께맞춰야한다. 실제생성결과와Spark효율은아직B023에서검증하지않았다.

VideoSwap/VideoAnydoor/AnyV2V/VideoPainter 및NVIDIA Spark공식자료를설계참고로검토했다. 기존videoediting기능과의차이를확인하기전논문독창성을주장하지않는다. 현재세션은기존비공개ZIP의영상품질재검토가아니며이문서가그검증을대체하지않는다.

## 기존 작업과의 관계

B001~021은기반·실패·학습증거로보존. B022는최신조회상PLANNED/NOT_RUN이고, 실행중이면중단시키지않으며동시GPU금지. 미착수라면새주력은B023, B022는후순위학습진단이다. 보류와실패를혼동하지않는다.

B023은공식SELF_REPLACE+LAB_REPLACE최대2sampler, 학습0,새다운로드0의실행제안이다. 두출력과동일LAB raw의사전ROI합성을비교한다. 원본copy는편집성공이아니고outside-ROI보존은생성모델성능/연산절감증거가아니다. 실행자가사용자의수행지시를받은후상세입력을고정하고HISTORY/ROADMAP에착수·종료를연결한다.

장기성과는한가지개입이동일비용에서개체/동작/장면보존을함께개선하거나같은품질에서비용을줄이는지로판단한다. 기능결합·MCP포장·한seed성공을논문기여로세지않는다.

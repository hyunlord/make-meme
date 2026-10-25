# 2026-10-26 — B-027 실물 검토와 다음 비교의 입력 계약

## 실제 검토 범위

연구 결과 기준 commit `86bcefa59e75256d432caf33c6c9f347ee4dc1ca`의 RESULTS/CASES를 원격 조회했다. 이번에는 첨부된 경량 ZIP을 실제로 열고 안전 경로 검사 후 추출했다. CRC와 MANIFEST의 payload615개 각각의 크기·SHA256이 모두 일치했다.

- review-lite bytes: 158,308,555
- review-lite SHA256: `e48f5face2630cdba337f196201e62eccc3cc5a70f2f08787bf763a103d0ae90`
- manifest 포함 ZIP member616개, payload615개
- full parent archive bytes/hash는 manifest의기록일뿐원본872,854,474bytes ZIP과Mac/Spark사본을이번에독립검증한것은아니다.

동물/사람/차량의 reference 시트와 local0/8/16 비교 시트, 동물 all17 시트를 직접 정적으로 확인했다. 옅은 source 개 잔존·큰 문자 장식, 사람 의상 변경과 팔/치마 손상, 차량의 혼합형상·별도그래픽 등 보고서의 핵심 실패와 부합한다. 사진 속 사람의 실제 신원은 식별하지 않았다. 이것은 agent의정적관측이지실제속도사람연속검수가아니다.경량ZIP에없는raw tensor/final latent의독립계보검사는수행하지않았다.

## 다음 판단에 필요한 두 가지

1. 동물 참조가 grey canvas에서 매우 작다. manifest 기준896×512에서R1 support4197(0.9149%),bbox152×46;R2 support10601(2.3108%)다. 이입력이모델의일반능력부족을증명하지않고,작은면적이유일원인이라는뜻도아니다. 기존사진을바꾸거나개인사진을추가하는대신,같은공개참조의크기·위치를공통규칙으로정규화하는전처리비교가가능하다. 확대는새정보복원이아니다.
2. VideoPainter는바로같은V/R/P계약의대체모델이라고확인되지않았다. 공식commit `bbab6cd5cd5cb89f0e2444305c32fd74a010ae0a`의infer/edit.py에서 편집caption의원격OpenAI호출,FLUX Fill로first frame생성,video[0]/masked_video[0]교체,그image와masked video로영상pipeline호출을직접읽었다. 해당entrypoint에SCAIL과같은별도target-reference입력이없다. ID-resampling명칭을reference-image IP encoder로가정하면안된다. Spark실행가능성도미검증이다.

공식근거:
- https://github.com/TencentARC/VideoPainter/blob/bbab6cd5cd5cb89f0e2444305c32fd74a010ae0a/infer/edit.py
- https://yxbian23.github.io/project/video-painter/

VideoPainter의원본문맥/시간일관성아이디어는유효한비교후보다. 그러나향후정확참조객체편집비교에는로컬reference-guided first-frame editor까지포함하거나,명시적인oracle first frame을주고downstream진단으로구분해야한다.보통텍스트로다른물체를만드는결과를특정참조객체교체성공으로보고하지않는다.기본script의외부LLM호출은B의로컬-only원칙과맞지않으며추후실행시완전히우회/제거해야한다.이번에호출·설치·가중치다운로드는없다.

## 결정 — B-028 한정 비교 제안

[PLAN](../experiments/B-028-object-reference-normalization/PLAN.md)에같은3과제×2사진의객체중심참조정규화한번을기록한다.고정bbox의중심·등방scale만바꾸고,동작/source/prompt/noise/모델은유지한다.출력·입력을유리한것으로재선정하지않는다.새sampler최대6·학습0·설치0의제안이며현재NOT_RUN이다.이문서게시만으로사용량이승인되거나작업이실행된것은아니다.

새로운사진을요구하지않고일반화가능한전처리규칙을시험한다.단순crop/정규화는기존기법의baseline이지논문독창성이아니다.결과가나오면이전처리계열은마무리하고,구조가다른backend/학습의실제기여를검토한다.파라미터를계속바꿔동일실패를반복하지않는다.

기존B027의6출력은그대로보존한다.표본은개발용3과제이며독립test/모델학습자료비중복/상용품질을입증하지않는다.추가자료감사·개인사진대기·GPU커널연구로돌아가지않는다.실행자는착수/종료시HISTORY·ROADMAP에이번결정을연결한다.이번변경은계획과결정두문서뿐이며기존실행코드·데이터·가중치는변경하지않았다.

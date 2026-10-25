# 2026-10-25 — B-024 개선 보존, 참조 교체 기여를 다음에 확인

## 검토와 근거

B024 결과 commit `f8dff4ac08d2393eeb4d90d7b29b7d7afe00fad5`의 RESULTS.md, CONDITIONS.md와 B020 INPUT_AMENDMENT의 실제 caption을 원격 조회했다. B024는 같은 객체 픽셀/support를 유지하고 비객체 RGB128을 양 encoder에 넣어 ref/CLIP4leaf만 변경했다. 정적 검토 보고에서는 침실·세로구획·후기 얼굴잘림이 줄고 원본의 사족자세·타일장면·고개돌림이 나타났다. 이를 중요한 task 관련 관측으로 보존한다.

검토자가 ZIP을 container와Python으로 직접 열려고 했으나 둘 다 ClientError였다. 미디어·334payload 해시·양호스트일치는 이번 검토에서 독립 확인하지 못했고 실제 프레임/연속재생을 봤다고 하지 않는다. 보고서의 시각관측과 코드/조건 기록을 읽은 범위다. temporal=UNVERIFIED 유지.

## 무엇을 결론내리지 않는가

같은 Lab source/reference와 black Labrador caption을 사용했기 때문에, 생성모델이 source의 개체를 따라갔다는 설명을 배제하지 못한다. raw에서PNG가나왔고source파일과byte가다르다는검사는파일대체검증이지model source-copy부정이아니다. background-only전처리를identity/pose완전분리나새알고리즘으로부르지않는다. RGB경계/padding과VAE/CLIP특징도함께바뀌었고두encoder기여는분리하지못했다. 학습량/ALG/RoPE가일반적으로무의미하다는결론도아니다.

## 다음 질문과 설계

상위 방향은 그대로다: 원본장면·동작을보존하면서reference와지시에맞게개체를교체하는단일Spark로컬시스템. 다음은 [B025 matched reference swap](../experiments/B-025-matched-reference-swap/PLAN.md)으로, source를현재Lab자연영상에고정하고사진에따라출력개체가바뀌는지확인한다. 새모델·학습·밈구간변경·합성·배경색sweep은하지않는다.

기존caption은검은Lab·넓은가슴·굵은사지를명시한다. 이를그대로IG사진에쓰면조건충돌이고,IGcaption으로바꾸면photo/text의공동효과다. 참조의기여를더명확하게보기위해외형을명시하지않는같은caption과actualnoise로 Lab/IG 두reference묶음을비교한다. 두ref는사용자가편집용으로제공한원본사진이며A생성물/새수집물은아니다. 전경RGB보존+밖128과RED/BLACKsemantic규약을둘다사용한다.

신규fullsampler최대2회,각40step/80forward·decode1회,학습/다운로드/retry0인제안이다. **두개seed나두방향성연구가아니라하나의질문을위한두조건**이다. B024는caption이다르므로새대조군으로조용히재사용하지않는다. 허용reference조건변경에는semanticmask도포함되므로RGB/identity단일요인이라고과장하지않는다.

표현색/체형반응,실제개체충실도,source동작·장면,시간적지각품질을각각판정한다. source-copy/참조무시를간접진단할수있지만참조필요성·일반화·동일품종개체구분능력까지입증하지않는다. 결과좋아보인다고15초·두개체로즉시확장하지않고관측결과후다음단계를정한다.

## 상태와 기록

B024는COMPLETED와정적개선관측을그대로보존한다. B025는 **PLANNED / NOT_RUN**이고문서등록만으로실행승인이아니다. 이번변경은새계획과결정문서추가이며기존코드/가중치/개인미디어/예산/과거실패를변경하지않았다. 새GPU·생성·학습0회다. 실제착수·종료시실행자가HISTORY/ROADMAP의현재상태를최신결과와연결해갱신한다.

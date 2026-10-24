# 2026-10-25 — B-023 결과 검토와 참조 RGB 분리 진단

## 유지하는 목표

영상+이미지+프롬프트로 원본의 장면·동작을 보존하며 지정 개체를 교체하고 단일 DGX Spark에서 품질/비용을 검증한다. [연구 v2](../RESEARCH_V2_SOURCE_PRESERVING_EDITING.md)는 유지한다. A/B를 섞지 않는다.

## 이번 검토의 근거와 한계

B-023 기준HEAD `9c3b84028c34b51e9af389d4a99a3f1b1454c54d`의 RESULTS/INDEPENDENT_REVIEW와 실제derive_cache/phase_sample/extract/phase_decode/media, B020 phase_prepare, 공식SCAIL `78fe19576bb06be96c2375e088574a262a300edb`의 scail.py/model_scail2.py를 읽었다. 작성자가 Spark에서 모델을 실행한 것은 아니다.

첨부ZIP는 제공된sandbox경로를container/Python으로 각각 시도했으나ClientError, Files읽기는텍스트없음으로끝났다. ZIP/290파일CRC·SHA·개인영상·Mac/Spark양호스트동일성은이번검토에서독립확인하지않았다. 실행자가보고한기술검증과정적시각관측을구분해인용한다.

결과는정식replacement가적용됐지만착석·중앙침실·후반얼굴잘림이지속된것이다. 확인한코드에서양CFG True·공식T/H/W전달·원래generated slice offset·final x0 decode경로는의도와맞고명백한입력/출력바꿔치기는찾지못했다. 이것이모든구현오류를배제하거나backbone의한계를증명하지는않는다.

## 다음 선택

BLACK semantic mask는reference RGB를지우는연산이아니다. 공식코드는RGB전체를VAE와CLIP에넣고maskembedding을별도로더한다. 따라서모드/마스크변경후에도침실정보는실제로encoder에들어간다. '모델이왜못하는가'로즉시일반화하기전에, 현재구현연결의짧은확인과비객체RGB의물리적중립화를묶어한번비교한다.

[B-024 PLAN](../experiments/B-024-reference-rgb-isolation/PLAN.md): source/reference 위치·크기·pose·semanticmask·모드·prompt/noise유지,reference비객체RGB만회색128로변경하고VAE/CLIP모두재계산한다. source/cacheVAE복원으로실제입력계보를확인하되새전체감사프로젝트로확대하지않는다. 특정구현결함이없으면원인UNKNOWN이어도단일통제실험을진행할수있다.

이번은 RGB배경/padding 전처리기준선이며pose제거·identity-only표현·새논문기여가아니다. 새sampler최대1회·학습0·다운로드0,본계획등록으로실행하지않음. foregroundmask는기존부분관측이라는한계를유지한다. 침실이없어져도원본장면·자세·개체가안맞으면전체성공이아니다.

B002의VACE배경제거실험과B024의SCAILreplacement를혼동하지않고,배경영향이없으면같은색/크기/offset튜닝을자동반복하지않는다. 실험완료후결과로다음병목하나를선택한다. HISTORY/ROADMAP은실행자가착수/종료때이결정과실제상태를연결한다.

이번원격변경은PLAN과이결정문서뿐이다. 기존코드·가중치·출력·실패이력은보존했고새GPU/학습/생성은0회다. 상태는PLANNED/NOT_RUN이다.

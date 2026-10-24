# B-024 — 참조 RGB 배경 분리와 조건 계보 확인

2026-10-25 · parent B-023 · **PLANNED / NOT_RUN**.
문서 등록은 GPU 실행이 아니다. 사용자가 실행 담당자에게 이 계획의 수행을 지시할 때 아래 범위를 적용한다. 이미 실행 중인 작업을 중단하거나 같은 실험을 중복 실행하지 않는다.

## 1. 상위 목표와 이번 결정

상위 목표는 [연구 v2](../../RESEARCH_V2_SOURCE_PRESERVING_EDITING.md)의 원본 영상+참조 이미지+편집 지시 기반 객체 치환이다. 원본 장면·카메라·시간·동작을 보존하면서 참조 개체를 반영하고 단일 DGX Spark에서 품질/비용을 함께 검증한다. A의 native imagegen과 B의 로컬 모델 연구는 독립이다.

B-023 commit `9c3b84028c34b51e9af389d4a99a3f1b1454c54d`의 RESULTS/INDEPENDENT_REVIEW/derive_cache/phase_sample/extract/phase_decode, B-020 phase_prepare, 고정 공식 scail.py/model_scail2.py를 읽었다. 정식 replacement와 semantic mask 변경은 반영됐지만 중앙 참조 침실·착석·후기 얼굴 잘림이 남았다는 실행자 관측이다. 모델 한계나 특정 encoder 결함을 확정하지 않는다.

검토자는 첨부 ZIP 경로를 container와 Python으로 각각 열려고 했으나 ClientError로 실패했고 Files에도 읽을 수 있는 내용이 없었다. 이번 세션에서 ZIP SHA/290개파일/미디어/양호스트 동일성을 독립 검증하지 않았다. 보고값 SHA `a790c9149fac18483c7a003bd8e8588a0102f14b53e28e443257033fccb6baec`를 실측으로 바꾸지 않는다.

중요한 코드 사실: 공식 파이프라인은 RGB reference 전체를 VAE와 CLIP에 각각 전달한다. semantic mask는 별도 feature로 전달되며 model의 patch_embedding_mask를 더한다. BLACK semantic mask가 RGB 배경을 지우거나 배경 토큰을 attention에서 강제 차단하는 연산은 아니다. model unpatchify는 additional_ref_length+ref_length를 건너뛰고 generated 구간만 반환하고, B023 D는 final x0를 직접 decode한다. 확인한 소스에서 명백한 reference/output 바꿔치기는 찾지 못했으나 실제 텐서 계보 전체를 독립 검증한 것은 아니다.

이번 질문은 **같은 개체 픽셀·크기·위치·자세와 semantic mask를 보존한 채 참조의 비객체 RGB(침실과 letterbox)를 중립화하면, VAE+CLIP를 통한 공간 배경 누수와 실제 편집 품질이 달라지는가?** 이 개입은 background/letterbox RGB의 공동 변경이다. 자세 제거, identity-only encoder, VAE/CLIP 개별 인과효과가 아니다. 단순 전처리 기준선이며 새 논문 방법이라고 하지 않는다. B-002의 VACE 배경 제거는 다른 모델/조건의 역사적 실험이지 이번 SCAIL replacement의 대조군이 아니다.

## 2. 범위와 예산

기존 정상 checkpoint·환경·분리 P/S/D·tiny CUDA·FlashAttention·mixed precision을 유지한다. 새 모델/패키지 다운로드0, 학습0, imagegen/외부생성/remote enhancer0, 새 원본/촬영/권한 재감사0.

- CPU 계보/코드 확인은 최대30분. 이전 메모리·변환·학습 감사를 재개하지 않는다.
- Reference 조건 worker 최대1회. 기존 VAE/CLIP만 순차 사용하며 T5/DiT는 이 worker에서 적재하지 않는다. 원본 reference 재인코딩 확인 최대1세트, 중립화 reference 인코딩 최대1세트(VAE+CLIP 각각)다.
- 기존 reference latent와 driving latent를 각각 최대1회 VAE decode하여 입력 계보를 시각 확인한다. 이는 새 diffusion 생성이 아니라 조건 표현의 복원이다. driving 복원은 원본의 절반 공간 해상도임을 기록한다. target 재인코딩·prefix 추출은0회다.
- 정상 입력 계약이면 신규 full sampler 실패포함 최대1회, UniPC40/CFG5의80forward. 해당 final latent의 D decode 최대1회. 필요 PROBE 최대1회, 자동retry/seed탐색0.
- 총 작업 상한3시간. 기존 시작72GiB·실행24GiB headroom·swap0·타 서비스 보호와 단계별 guard 유지. 타 프로세스 종료·driver/swap변경·전역cache삭제 금지. 서로 다른 메모리 회계를 합산하지 않는다.

## 3. 입력·상위 EditSpec 고정

B023의 같은 실제Lab source f126..142,17frame/30fps,896×512,원본 PTS와aspect-fit 변환,참조사진과support,positive/negative,seed20261022,실제noise/RNG/UniPC40/shift3/CFG5를 유지한다. 목표는 사족으로 서서 고개를 돌리는 자연동작이며 두발춤이 아니다.

replacement=True, history/additional_ref=None, 모든 학습adapter OFF,ALG OFF,수동RoPE OFF를 유지한다. semantic mask는 B023의 RED 개체/BLACK reference 배경, RED 개체/WHITE driving 배경 그대로다.

대조군은 B023 raw replacement 결과를 재사용한다. B020 animation이나 B022 학습출력은 역사맥락으로만 표시한다. 같은개체 source므로 source-copy로도 겉보기 성공할수있고 cross-ID/reference necessity는 미검증이다.

EditSpec에는 동일한객체·동작·시간·장면보존 목표와 이번 reference RGB 전처리만 바뀐다는 점을 기록한다. 모델/데이터/학습방향을 다시 정의하거나 별도parser/MCP를 만들지 않는다.

## 4. 짧은 연결 확인 — 불확실성을 이유로 끝없이 보류하지 않음

기존 실제input→tensor→cache→model arg→final latent→VAE→raw 경로를 확인한다. 변수명·해시만으로 입력 의미를 가정하지 않는다.

- 기존 reference RGB와mask의 같은 canvas/support를 눈으로 겹쳐 확인한다. source/driver 경로와RGB/mask 시간축을 확인한다.
- 기존 reference latent와pose_latent의 VAE복원으로 각각 침실의착석사진/원본의서있는동작이 들어있는지 확인한다. VAE손실복원은원본RGB와bit equality가필요한검사가아니다.
- ref/pose의 VAE scaling/CTHW, CLIP 입력사진, 실제model ref/pose 인자, unpatchify generated offset, D의x0계보를 좁게확인한다. 같은기존모듈source를읽는것과실제runtime trace의증거수준을구분한다.
- 원래 reference 재인코딩의shape/dtype/의미와기존cache를대조한다. 동일encoder를재실행한미세수치차이를독립학습byte재현gate처럼사용하지않는다. 기존허용기준이있으면재사용하고원시max/RMS·normalization을남긴다.
- source/ref뒤바뀜, 잘못된cache,중복normalization,출력offset오류 같은 구체적결함이확인되면 PIPELINE_DEFECT_FOUND로중단하고 신규sampler0으로남긴다. 결함수정과RGB개입을한번에섞지않고수정범위를보고한다.
- 구체적결함이없으면 원인UNKNOWN이어도그한계를기록하고 아래한번의통제실험으로진행한다. 모든잠재오류를배제하는것을생성의선행조건으로요구하지않는다.

## 5. RGB 개입 정의

R은 B023에서 실제모델에들어간 preprocessed reference RGB, M은그좌표의기존RED subject support다. uint8 RGB공간에서 다음을 만든다.

`R_fg[p] = R[p] if M[p] else (128,128,128)`

전체canvas·subject의위치·크기·pose·M안의RGB는보존한다. M밖의침실과흰letterbox를같은중립회색으로바꾼다. mask경계밖숨은털은기존support제약이며,alpha최적화나새분할을추가하지않는다. 배경과padding을함께바꾸므로침실만의효과라고부르지않는다. 회색은조건branch-off가아니다.

M안의pixel exact equality, M과bbox/면적불변, M밖constant, 변환전후전체시트를저장한다. crop/zoom/이동/좌우반전/리포즈/페더/생성inpaint/좋은사진선정은금지한다. grayscale변환으로개체색을바꾸는것도아니다.

R_fg를공식normalization으로VAE와CLIP양쪽에새로인코딩한다. 기존latent에M을곱하거나원래CLIP를그대로두지않는다. semantic BLACK 지시와실제RGB중립화의차이를명확히한다.

예상tensor변경은 양CFG의ref_latents+clip_fea,4leaf다. ref_masks/driving_masks/pose_latents/text/noise/RNG/scheduler등나머지12leaf는원본cache값을직접재사용하며불변을검사한다. 실제구조가다르면개수만믿지말고의미별계약을고정한다. ref/CLIP변경으로후속features가변하는것은의도한변화다. stale reference가남지않았음을실제sampler인자/첫forward내복사없는검사로확인하되추가DiT forward는없다.

## 6. 평가와 결론 규칙

SOURCE / 원래R / R_fg / B023 baseline / B024 raw를같은canvas·30fps·전체17frame으로비교한다. local0/8/16와연속변화를모두보존한다. 새생성을원본배경합성·SR·얼굴복원·warp·보간으로보정하지않는다.

따로기록할항목:
1. 참조침실·세로구획·흰padding·경계잘림이남는가? 중립회색을새로복사하는가?
2. 원본의바닥/가구/촬영구도가실제로보존되는가? 침실이사라지고임의배경이생기는것만으로성공아님.
3. 사족기립·고개방향/순서를따르는가? 착석유지와국소반응을분리.
4. 얼굴/귀/목·사지·개체/체형이보존되는가? '검은개'와실제개체일치를구분.
5. runtime/메모리/추가encoder비용은얼마인가?

목적에맞는개체+동작+장면의동시개선이주평가다. 배경누수감소만확인되면partial결과이고전체성공아님. posture는그대로인입력이므로실패가곧pose분리의불가능증거는아니다. 좋아져도mask-basedRGB전처리한case이며새아키텍처/상용품질/일반화아님.

actual native속도시청이없으면temporal=UNVERIFIED. 파일decode/뷰어기능과지각검토를구분한다. 실제사용자가볼수있는단회재생·전체frame뷰어를유지하고눈가림사람평가를했다고가정하지않는다.

한번비교후자동색상/크기/위치/CLIP강도/seed/schedule 탐색을하지않는다. 결과를검토한후에만다음연구하나를선택한다. 누수가줄어도자세가남으면background와pose문제를분리하고, 변화가없으면다음계층을무작정추가하기보다task baseline/모델적합성의가설을결정한다. 사전선택한기법을억지로성공시키려하지않는다.

## 7. 이론·기록·제출

한국어해설은 learned semantic mask와pixel gating/attention mask의차이, VAE/CLIP에동시에들어가는reference정보, 역할분리에서background제거와pose제거의차이를실제함수·텐서·결과에연결한다.

설명식: `c_ref=(E_VAE(R),E_CLIP(R),E_mask(M))`; 기존은M만바꿨고이번은R의비객체픽셀을바꾼다. 두encoder의효과를개별분리했다고하지않는다. encoder가nonlocal이므로M안의pixel이같아도M안의latent특징은달라질수있다.

시작전상위CHARTER/연구v2/ROADMAP/HISTORY/PLAN을읽고실제질문·변수·안전/예산을고정한다. 기존실패를수정하지않고HISTORY/ROADMAP에B023결론→B024가설을연결한다. 계획/코드/config를사전commit하고종료후RESULTS·재현·측정·해설·다음결정을push/remote확인한다. 새MCP/framework·전면타입리팩터링은없다.

개인영상/사진/mask/cache/latent/가중치/비밀경로는비공개다. 실제진행후단일ZIP를Spark와Mac /tmp에보존하여전송·크기·SHA·CRC·manifest·추출을확인한다. 포함은입력변경/조건복원/새결과/기존대조/최종latent/재현·실패근거이며대형weights·중복prefix는제외한다.

최종보고는품질결론→raw비교자료→실제사용량→한계→검증·기록→다음가설순으로한다. 테스트개수·ZIP검증만으로시각성과를대체하지않는다. 이번작성은계획문서이며실제추가연산0이다.

# B-034 제안 의뢰서 — clean-prediction 제약의 고정 방법 전이 검증

작성: 2026-10-27
상태: PROPOSED / NOT_RUN. 이 파일 작성으로 GPU 실행·데이터 수집·원격 저장소 변경을 수행한 것은 아니다.
저장소: hyunlord/make-meme
브랜치: docs/b-research-20261022
검토한 B-033 원격 기준: d401b0180168bd3db4b554ba127f1395c80c9c78

## 0. 목적과 기존 결과의 처리

최종 목표는 원본 영상 V, 대상 참조 R, 편집 지시 P로 객체를 바꾸되 원본의 지정 동작·장면을 보존하는 로컬 시스템이다. 개인 DGX Spark에서 전체 비용과 품질을 함께 평가한다. 개인 반려견 사진·새 촬영은 연구 진행 조건이 아니다. A/imagegen 트랙과 분리한다.

B-033은 차량 한 개발 사례·한 seed에서, 동일 RGB 후합성 후에도 생성 중 clean-prediction 제약이 최종 latent 혼합 및 RGB 후합성보다 접촉 부근 색상 조각을 줄이는 부분 개선을 보였다. 정체성의 완전한 보존, 실제 접촉·그림자, 시간 품질, 일반화와 자동화는 미입증이다. B-032는 저비용 기준선으로 유지한다. B-031의 비강체 앵커 실패 및 과거 실패 판정을 소급 변경하지 않는다.

이번에는 새 gate·마스크 튜닝·강도·스케줄을 만들지 않는다. 기존 규칙을 고정하고 다른 공개 사례에서 개선·회귀·무효를 확인한다. 새 작은 잔여 조각 하나를 지우기 위한 최적화는 하지 않는다.

핵심 질문:
“같은 제약을 다른 원본·대상에도 적용했을 때, 교체한 대상이 원본으로 되돌아가지 않으면서 편집 경계·주변의 오염을 줄이는가?”

이번은 최대 두 신규 공개 과제의 prospective 소형 검증이다. 전 범주 일반화·논문 성능을 입증하는 최종 benchmark가 아니다. 기존 모델의 사전학습 데이터와 중복 여부도 UNKNOWN이다.

## 1. 착수와 예산 확인

최신 HEAD, CHARTER, RESEARCH_V2, HISTORY, ROADMAP, B-031~033의 RESULTS/METHOD/CONTROL/COSTS를 읽는다. 동일 실험 번호가 이미 사용됐거나 실행 중이면 충돌·중복 실행을 피한다. 실제 실행 상태를 조회하며 원격 PLANNED만으로 로컬 프로세스 상태를 추정하지 않는다.

사용자가 이 의뢰서를 전달해 수행을 지시한 경우 아래 범위를 적용한다. 진행 중인 타 작업을 종료하지 않는다.

실행 전 이 의뢰서를 docs/research/work_orders/에 보존하고, 실제 선정 자료·코드·설정·평가·종료 조건을 PLAN/DECISION으로 기록한다. 결과를 보기 전에 선택과 허용 변경 범위를 고정한다. 사용자가 이번 단계만 원한 경우 이후 자동 후속은 없다.

## 2. 신규 공개 두 과제 — 생성 결과를 보고 재선정하지 않는다

기존에 확보한 공개 DAVIS/동등한 허가 자료에서 우선 선택한다. 사용한 source·target sequence/track/frame 이력과 대조해 B-027~033에서 생성하거나 방법 선택에 사용하지 않은 source와 target 조합 두 개를 확보한다. 같은 car-roundabout의 인접 프레임 또는 기존 target의 다른 사진만으로 미사용 검증이라고 하지 않는다.

목표 구성:
- 한 과제는 차량 등 강체, 원래의 차량 사례와 다른 장면·대상.
- 다른 과제는 동물 또는 사람 등 비강체.

각 과제는 같은 범주의 다른 source/target 인스턴스를 사용한다. 사람의 생체 신원을 식별·인증하지 않는다. source는 관측 가능한 이동·회전/몸 동작이 있는 연속 17프레임, target은 원본 사진 한 장이다. 원본의 시간 정보가 확인되지 않으면 source_fps=null, preview_fps=24, timebase_assumed=true로 유지한다. 17/24초를 원본의 실제 지속시간이라고 보고하지 않는다.

선정은 입력 관측만으로 하며 전체 후보 최대 12묶음·준비 최대 45분으로 제한한다. 대상이 식별 불가능할 만큼 작거나 마스크가 없는 등의 입력 부적합은 생성 전에 사유를 남긴다. 모델에 유리한 기립 사진만 요구하거나 사진을 생성해서 대체하지 않는다. 새 개인 자료를 요청하지 않는다.

기존 데이터에서 부족하면 공개·기존 이용조건 범위 안의 데이터만 누적 2GiB 이내 내려받을 수 있다. 모델·패키지 다운로드는 금지한다. 가입·신청·유료 API·접근 우회는 하지 않는다. 재배포/상업 사용 가능성을 별도로 기록하며 공개 데이터라는 이유로 용도를 확대하지 않는다.

두 과제를 첫 이미지 생성 전에 고정한다. 한 범주를 확보하지 못하면 확보한 범위만 실행하고 범위를 좁혀 보고한다. 출력이 나쁘다고 새 과제를 찾아 채우지 않는다. 이 두 입력을 결과 확인 후에는 개발 사례로 편입하고, 향후 최종 test로 재사용하지 않는다.

## 3. 변경하지 않을 것

B-031에서 확보한 Qwen과 SCAIL의 모델 revision·가중치·정밀도·정상 환경을 재사용한다. 현재 환경을 업그레이드하거나 새 backend·LoRA·attention·prompt enhancer를 설치하지 않는다.

공통 파이프라인:
1. 원본 첫 프레임 + 별도 target reference → 기존 Qwen 다중 이미지 편집.
2. 생성 앵커 A0의 target support를 기존 방식으로 추출하고, 밖 RGB128 / RED-BLACK reference semantic mask로 구성.
3. 동일한 source video·driving mask·text·initial noise로 BASE와 STEP을 비교.

원본 캔버스 896×512, 연속 17프레임을 사용한다. RGB와 mask는 같은 spatial transform을 적용한다. 기존 SCAIL replacement=True, UniPC 40step·shift3·CFG5, adapter/ALG/B029 gate/manual RoPE OFF, history/additional_ref=None이다.

과제별 caption은 대상 외형과 source 동작·장면을 정확히 기술하는 기존 규약으로 생성 전에 고정한다. 모든 영상 비교에서 같은 caption/negative를 사용한다. 사진의 서로 다른 외형을 부정하거나 모순되는 품종·의상을 지시하지 않는다. 결과 후 문구 변경·강조·negative 탐색은 금지한다.

과제별 seed는 사전 고정해 저장하고, BASE/STEP의 실제 초기 noise·RNG·sigmas·timesteps를 공유한다. 서로 다른 모델의 같은 숫자 seed가 같은 noise를 뜻한다고 하지 않는다.

## 4. 앵커 생성과 실패 기록

Qwen 이미지 생성은 과제별 1회, 합계 최대 2회, 실패 포함이다. B-031의 실제 다중 이미지 입력 순서와 공통 template·40 image step·guidance 설정을 그대로 사용한다. 원본 첫 프레임의 자세·방향·배치를 유지하고 target 외형을 반영하는 목적을 유지한다. 원본/참조/모델 입력/A0를 보존한다.

출력마다 개체 외형, source 자세·위치, 중복·형태, 보호 장면을 별도로 판정한다. 심한 자세 변경·이중 객체·target 미반영이면 ANCHOR_UNSUITABLE로 기록하고 해당 과제의 영상 단계는 NOT_RUN으로 남긴다. 재시도·다른 seed·다른 사진으로 교체하지 않는다. 탈락 자체가 전체 시스템의 실패이며 조건부 영상 단계의 성공률로 숨기지 않는다.

두 과제 모두 탈락하면 새로운 적합 사례를 찾지 않고 종료한다. 이때 clean 제약이 실패한 것이 아니라 영상 단계 미실행으로 보고하며, 앞단의 일반적 외형/자세 결합 문제를 다음 우선순위로 돌린다.

## 5. 각 적합 과제의 BASE와 support 확보

먼저 원래 SCAIL sampler로 BASE를 1회 생성·decode한다. 기존 B-031과 같은 과정이며 STEP과 동일한 앵커·문장·driving·noise를 사용한다. full-resolution source VAE encode도 과제당 최대 1회 수행한다. half-resolution driving latent 확대를 source latent 대용으로 사용하지 않는다.

BASE의 실제 target 영역 T_t를 기존 CPU/수동 도구로 표시한다. source 객체 영역 S_t는 공개 GT mask를 재사용한다. target 주석은 BASE 이후, STEP 생성 이전에 확정한다. STEP을 본 뒤 mask를 좁혀 불리한 결과를 자르지 않는다. 새 모델 기반 segmentation, 정교한 matte 연구, 사후 오염 pixel 지우기를 하지 않는다.

전체 두 과제의 target support 준비는 30분 이내로 제한한다. 불확실한 가림·얇은 구조·그림자는 표시한다. B-033과 동일하게 별도 shadow support H는 사용하지 않는다. 이 한계 때문에 그림자 생성이 충분히 허용되지 않을 가능성도 보고한다.

원본/target union으로 만드는 E 규칙은 그대로 재사용한다.
- clip 전체 source bbox 긴 변을 L이라 하면 r=max(2,ceil(0.02*L)). 기존 차량의 실현값 11px를 새 모든 사례에 무조건 고정하지 않는다.
- U_t=S_t ∪ T_t.
- U_t에서 Euclidean distance r 이내를 core로 두고, 그 밖 4px를 feather하는 B-032 구현 그대로.
- E=1은 생성 결과를 보존하고 E=0은 source를 복사한다.

시간 축 max 그룹 [0], [1..4], [5..8], [9..12], [13..16], 공간 8×8 max pooling 및 3×3 max pooling으로 latent M을 만든다. RGB support coverage와 latent mask 범위를 확인하되 정확한 VAE receptive field 대응이라고 주장하지 않는다.

입력·mask 정책은 전체 시작 전에 고정하되, 각 과제의 실제 E/M 값은 BASE에서 나온 주석에 의존한다. 그러므로 전체 파이프라인을 source-only 또는 1-pass automatic이라고 부르지 않는다. 그래픽 자체를 지우려는 의도로 mask를 만들지 않는다. 적절한 target 경계와 바깥 오염이 구분 불가능하면 MASK_PARTIAL/UNRESOLVED를 남기고 계산을 자동 확장하지 않는다.

## 6. 세 가지 비교 — 알고리즘은 고정한다

각 과제에서 같은 E/M을 사용하는 다음 결과를 만든다.

A. BASE + RGB_POST
원래 sampler 결과에 같은 E로 원본을 합성한다.

B. FINAL_LATENT_ONLY + RGB_POST
z_final = M*z_BASE + (1-M)*z_source.
DiT 새 호출 없이 decode 1회 후 같은 E 합성을 적용한다.

C. STEP_CONSTRAINED + RGB_POST
B-033 clean_constraint.py의 converter 개입을 그대로 사용해 신규 sampler 1회.
공식 converter의 x0 estimate를 한 번 얻은 뒤
  x0_constrained = M*x0_prediction + (1-M)*z_source
로 바꾸고 공식 corrector/history/predictor로 전달한다.
같은 E로 RGB 후합성을 적용한다.

모든 raw와 post 결과를 따로 보존한다. model weights·attention·CFG·sigma schedule·학습은 바꾸지 않는다. soft M의 블렌딩 의미와 hard endpoint를 유지한다. 다른 scheduler의 상태를 덮거나 noisy latent에 clean source를 직접 붙이는 구현으로 바꾸지 않는다.

이미 검증한 CPU 계약을 재사용한다. 이번 입력 shape·M/source coverage·same-noise·cache mapping·40회 converter 호출 확인만 추가한다. 새로운 kernel 감사·전체 가중치 재변환·타입체계 리팩터링을 하지 않는다.

STEP의 target이 BASE로 정한 E를 벗어나거나 source가 복사돼 형태를 잘라 내는 경우 MASK_INCOMPATIBLE/FAIL로 남긴다. 해당 문제를 후합성으로 감추지 않도록 raw와 E overlay를 함께 제시한다.

## 7. 평가 기준 — 좋은 결과만 모으지 않는다

생성 전에 입력 기준으로 다음을 고정한다.
- target/source를 구분하는 관측 외형 2~3개
- source 동작의 방향·순서·변화 1~2개
- 보호할 주변 객체·장면 요소

BASE를 얻은 뒤에는 STEP 전에 관측창·경계 띠·접촉 영역을 고정한다. 오염 없는 사례도 버리지 않고 non-regression control로 남긴다. STEP을 보고 유리한 crop을 바꾸지 않는다.

전체17프레임, 같은 local0/8/16, raw/post를 함께 비교한다. 주 질문은 같은 RGB 후합성 뒤에도 C가 A/B보다 추가 이득을 주는가다. 바깥 E=0의 source exact는 합성식의 성질이므로 모델 우월성 점수로 세지 않는다.

각 과제의 결과를 다음 중 하나로 요약한다.
- ADDITIONAL_BENEFIT: 두 대조군보다 편집 내부/경계 오염이 줄고, target 특징·source 동작·형태에 관측 가능한 큰 회귀 없음.
- NON_REGRESSION_ONLY: 오염이나 개선 여지가 원래 작고 방법이 큰 회귀를 보이지 않음. 개선 증거로 세지 않는다.
- TRADE_OFF: 오염 감소와 함께 target 희석, source 회귀, 잘림·접촉·동작 손상 등 발생.
- NO_BENEFIT 또는 WORSE.
- INCONCLUSIVE/NOT_RUN: 앵커·mask·가림·검토 근거가 부족함.

파편 색이 옅어졌다고 물리적으로 정확한 접촉·그림자가 됐다고 하지 않는다. source와 target의 체형이 다르므로 객체 영역의 source pixel MSE를 교체 정확도로 쓰지 않는다. source-copy와 target 유지, 단순 색상 변화와 실제 관측 특징을 구분한다.

두 새 사례는 일반화 성능이나 유의미한 성공률을 계산하기에 충분하지 않다. 한 사례만 좋아지거나 동종 강체에서만 좋아지면 그 범위를 좁혀 보고한다. 결과가 좋더라도 자동 기본 채택은 하지 않는다. 개선 없음/역효과면 현재 고정 방법의 확대를 중지한다.

## 8. 시간 품질 검토

원본 timebase가 불명확하면 preview 속도라고 표시한다. 영상은 loop를 기본 OFF로 하고, source/A/B/C를 동기화해 native preview 속도 및 frame-step으로 볼 수 있게 한다. 필요하면 방법 이름을 숨긴 고정 label과 mapping 파일을 제공하지만, label을 섞은 것 자체가 blind human evaluation은 아니다.

실제 연속 지각 검수자가 있다면 주체·검토한 클립·속도·횟수·판정을 남긴다. 도구가 재생 버튼을 눌렀다는 사실이나 프레임 확인을 실제 시청으로 바꾸어 쓰지 않는다. 실제 사람이 보지 않았다면 temporal=UNVERIFIED로 유지하고 전체 영상 품질의 기본 채택을 보류한다. 이 검토 부재 때문에 기술 실행·정적 관측 결과까지 폐기하지 않는다.

## 9. 비용 회계와 자원 상한

- Qwen 이미지: 최대2회, 각각 기존40step 설정. 실패 포함. 추가 image 후보0.
- 신규 SCAIL sampler: BASE2 + STEP2 = 최대4회. 각40step·80forward. 실패 포함, retry0.
- source VAE encode: 최대2회.
- 영상 VAE decode: BASE2 + SOURCE_RECON2 + FINAL_ONLY2 + STEP2 = 최대8회.
- 새 training/model/package/LoRA/imagegen/외부 inference: 모두0.
- GPU-heavy worker는 순차. Qwen 종료·회수 후 SCAIL 실행.
- 기존 72GiB 시작/24GiB 실행 headroom·swap0·타서비스 보호 유지. 새 가드나 driver 변경 금지.
- 전체 hard wall-clock 상한6시간. 마지막30분은 기록·보존·전달에 남긴다. 시간 안에 못 끝낸 과제는 NOT_RUN/부분 종료로 남기고 예산 초과를 숨기지 않는다.

세 비용을 구분한다.
1. 검증 캠페인의 전체 실제 비용: BASE·FINAL_ONLY·STEP·앵커·mask·source encode·decode·리뷰·패키징까지 모두.
2. 이미 BASE와 support가 있는 입력을 수정하는 증분 비용: 새 STEP sampler와 필요한 encode/decode 등.
3. 향후 제품의 가상 one-pass 비용: sampler 자체를 교체할 수 있는 가능성일 뿐, 이번 output-assisted support 때문에 아직 입증하지 않음.

B-033의 STEP 40step80forward는 BASE와 같은 NFE다. 따라서 “방법은 본질적으로17분을 추가한다”와 “무료다” 모두 부정확하다. 이번 pipeline은 BASE 이후 support를 만들고 STEP을 다시 수행하므로 실제 두-pass 비용과 주석을 반드시 포함한다. 한 번의 S worker 시간차를 isolated scheduler overhead나 속도 향상으로 주장하지 않는다.

GPU kernel, stage worker wall, 전체 wall, CUDA allocated/reserved, OS가용, cgroup, RSS를 구분한다. source·feature copies와 모델 로딩은 따로 기록하고 서로 다른 메모리 회계를 합산하지 않는다.

## 10. 학습·연구 해설

한국어 해설은 다음에 한정해 깊게 작성한다.
1. 마지막 합성과 반복 clean-prediction 제약이 다른 이유: 같은 혼합 연산이어도 후속 모델 평가가 달라진다.
2. latent의 위치와 RGB의 위치가 정확히 일대일이 아니며, 마스크·가림·VAE 재구성이 결과 해석을 제한하는 이유.
3. mask-given/출력보조 비교와 자동 end-to-end 편집의 차이.
4. 실험 증분 비용과 배포 one-pass 가상 비용의 구분.

RePaint/Blended Latent Diffusion 등 관련 방법과의 차이도 명시한다. 이번 구현을 그 방법의 정확한 재현이나 이론적 수렴 보장이라고 하지 않는다. 알려진 영역의 혼합만으로 새로운 알고리즘 기여를 주장하지 않는다.

## 11. 기록·산출물과 이후 결정

실행 전 PLAN·CASES·방법 버전·예산·평가를 고정하고, 종료 후 RESULTS·CASE_OUTCOMES·COSTS·REPRODUCE·lessons를 기록한다. HISTORY/ROADMAP에는 기존 B-033 PARTIAL, 두 새 입력의 적합성, 어떤 부분이 재현됐는지를 연결한다. 기존 결과를 소급 변경하거나 main/타 branch를 덮지 않는다. commit/push·원격 SHA를 실제 확인한다.

공개에는 비민감 코드·설명·검증 요약과 허가된 데이터 manifest만 남긴다. 개인 자료·가중치·cache·latent·비밀정보·비공개 절대경로는 공개하지 않는다. 데이터의 재배포 조건은 그대로 따른다.

compact/full 분리. compact는 원본·참조·실제 앵커·BASE/FINAL/STEP의 raw와post MP4·viewer·비교시트·보고서. full은 raw tensor·final latent·주석·조건 provenance를 추가하되 weights·중복 원본 archive는 제외한다. 생성되지 않은 항목은 NOT_RUN으로 표시한다.

새 비교용 MP4는 파생 인코딩, 기존MP4는 재인코딩0으로 구분한다. 압축은 SOURCE 생성 코드·이미 있던 검증기 재사용으로 최소화한다. 새 감사 framework·다중 reviewer loop를 만들지 않는다. 실제 CRC·payload hash·추출·Mac/Spark 전송 여부만 보고한다.

최종 답은 다음부터 시작한다.
- 같은 고정 규칙이 어떤 새 사례에서 추가 이득/회귀/무효를 보였는가?
- 원본을 복사해 target이 약해진 대가로 배경만 좋아진 것은 아닌가?
- 앵커/마스크 준비·생략까지 포함한 전체 시스템의 실패는 무엇인가?
- 자동화와 시간 품질에 아직 어떤 증거가 없는가?
- 그 결과를 근거로 이 모듈을 더 검증할 것인가, 사용 범위를 좁힐 것인가, 중단할 것인가?

이번 범위 이후 종료. 새 seed·mask·scheduler·강도·훈련·다른 backend·긴 영상 실험을 자동 시작하지 않는다. B-034가 좋아도 upstream 외형/자세 결합 문제를 해결했다고 하지 않는다. 그 미해결 연구 축과 다음 단계의 mask 자동화·단일패스 가능성은 결과를 본 뒤 별도로 선택한다.

## 참고 근거

- 사용자 연구 B-033 RESULTS/METHOD, commit d401b0180168bd3db4b554ba127f1395c80c9c78.
- RePaint (Lugmayr et al.), arXiv:2201.09865 — 알려진 영역 정보를 reverse diffusion에 활용하는 선행 연구.
- Blended Latent Diffusion (Avrahami et al.), arXiv:2206.02779 — latent 공간의 지역 편집 및 재구성/얇은 mask 문제.

이 문서는 다음 실험 제안이다. 현재 응답에서는 첨부 파일의 무결성·정적 이미지·코드 검토와 문서 작성만 수행했다. 사용자 Spark 접속, GPU 생성, 새 자료 다운로드, GitHub write는 수행하지 않았다.

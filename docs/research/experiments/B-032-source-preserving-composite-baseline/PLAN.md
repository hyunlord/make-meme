# B-032 — 기존 생성 결과의 원본 보존 합성 기준선

작성: 2026-10-27. **PROPOSED / NOT_RUN**. 기준 결과 commit: `3e669f0f5b284cc9ec178959b4f35e2129896788`. 문서 등록은 실행이 아니다. 수행 지시 후 아래 CPU 작업만 허용한다.

## 1. 상위 목표와 연구 판단

목표는 특정 반려견이나 모델에 종속되지 않는 로컬 V/R/P 객체 편집이다. 원본 장면·지정 동작을 보존하며 참조 대상을 반영하고, 개인 DGX Spark에서 전체 품질·비용을 검증한다. A imagegen-only 트랙은 독립 보존한다.

B031의 animal/human R1은 앵커의 source 자세부터 실패했고 영상은 NOT_RUN이다. Vehicle R1은 앵커에서 목표 차체와 우향을 함께 만들었으며 영상의 target형 차체·거친 회전도 관측됐지만, 생성 영상의 도로에 별도 차량 그래픽이 생겼다. B031 전체 FAIL과 temporal UNVERIFIED는 보존한다. 정확 개체·접촉·회전량이 입증됐다고 하지 않는다.

다음 후보인 생성 중 source context 고정은 타당한 연구 가설이지만, 새 sampling 전에 **같은 기존 raw의 비편집 영역을 source로 복원하는 가장 단순한 기준선**부터 만든다. 이것은 장기 합성 설계의 작은 실제 구현이며 새 커널 감사나 모델 준비가 아니다. 이후 모델 개입은 raw뿐 아니라 이 합성 기준선보다 좋아야 할 이유가 필요하다.

이번에는 경계와 보호 영역 문제를 한 사례에서 분리한다. Animal/human 앵커 실패는 별개의 미해결 축으로 남기고 개인 기립 사진을 요구하지 않는다. 차량 사례는 적합한 기존 출력이 있는 가용성 기준으로 선택된 진단이며, 보편 성능을 대표하지 않는다.

## 2. 실행 범위

- **GPU worker / imagegen / encoder / sampler / VAE decode / 학습 / 새 모델·패키지 설치: 모두 0회.**
- B031 vehicle_R1의 기존 source 17프레임, lossless decoded raw, source GT support, A0 및 A0 target support를 재사용한다. 필요 파일은 기존 로컬 full 산출물에 있으며 chat compact만으로 raw가 없다고 새 추론하지 않는다.
- 동일 896×512, 순서17장, source_fps=null, preview24fps, timebase_assumed=true. 기존 noise·latent·가중치는 읽거나 수정할 필요 없다.
- CPU 합성 결과 두 개만 만든다: `FIXED_ENVELOPE`, `MASK_ASSISTED`. 조건 sweep·추가 프롬프트·새 target·새 image generation은 없다.
- 전체 상한90분(문서·ZIP·전송 포함), mask 준비 최대30분. 마지막15분은 결과 보존에 사용한다. 출력 품질을 좋게 만들기 위해 한도를 자동 연장하지 않는다.
- 다른 작업을 종료하지 않고 기존 상태·파일을 덮어쓰지 않는다. 이미 B032가 실행 중/완료면 중복하지 않는다.

## 3. 합성의 의미

source V_t, 기존 생성 G_t, 편집 가중치 E_t에 대해:

`Y_t = (1-E_t) * V_t + E_t * G_t`.

E는 target 객체 alpha가 아니라 **편집 결과를 사용할 영역**이다. 원본 객체와 새 객체의 크기·위치가 다르므로 source support만 쓰지 않는다. source 객체가 제거돼야 하는 영역, 새 target, 경계와 필요한 접촉 그림자를 고려한다.

E=0에서는 raw source를 그대로 복사하고 E=1에서는 raw generated를 그대로 복사한다. 경계만 같은 색/수치 규약의 float로 blend한다. RGB/CHW, 좌표, 범위, 프레임 순서와 uint8 변환을 기록한다. source padding과 fullframe 좌표를 그대로 사용한다. 색 보정·프레임 정렬·warp·inpaint·복원은 없다.

원본 밖 영역의 pixel exact 보존은 이 식의 성질이며 생성 모델이 장면 보존을 배웠다는 증거가 아니다. Target 외형/동작이 좋아졌다는 주장도 별도다. 새 샘플링이 없다는 것은 추가 처리 비용이 작다는 의미이지, B031의 이미 지출한 생성 비용을 없애지 않는다.

## 4. 두 기준선

### A. FIXED_ENVELOPE — source와 생성 앵커로만 결정

source 17장 GT target support와 A0 target support를 같은 canvas에서 합친 최소 bbox를 구한다. 그 bbox의 폭·높이 각각10%를 각 방향으로 추가한 뒤 canvas에 clip한다. 동일한 정적 사각형을 전17장에 적용한다. 외곽 안쪽8pixel만0→1로 선형 전이시키고 나머지 안쪽은1, 바깥은0이다.

확대율·feather는 한 번만 적용한다. 기존 영상 raw의 그래픽을 보고 사각형을 줄이거나 옮겨 오류를 숨기지 않는다. Generated target이 ROI 밖으로 나가면 SUPPORT_UNDERSHOOT로 남기고 이 기준선은 수정하지 않는다. 이 방법도 source GT와 A0의 제공된 support를 사용하므로 end-to-end 자동 segmentation이라고 보고하지 않는다.

### B. MASK_ASSISTED — 출력 객체의 support를 명시하는 합성 참고선

동일 G_t의 실제 주행 대상만 T_t로 표시한다. 기존 도구 또는 CPU 수동 polygon을 사용하며 source track와 연속 경로에 대응하는 차량을 선택한다. 도로 위 별도 그래픽을 target으로 포함하지 않는다. Target의 보이지 않는 부위를 상상해 채우거나, 얼굴/차체 pixel을 고치지 않는다. 생성 후의 support를 쓰는 이 분기는 **output-mask-assisted**로 명시한다. Agent 주석은 독립 human GT가 아니다.

source 객체 support S_t와 생성 target support T_t를 합친다. 눈으로 확인 가능한 source/target의 직접 접촉 그림자에 필요한 영역 H_t는 선택적으로 별도 표시하되, 본체 mask와 구분하고 작업 시간·근거를 남긴다. 불명확한 그림자는 임의로 정답 처리하지 않는다. Source의 앞쪽 occluder를 보호하려면 실제 앞뒤 근거를 기록하고, 알 수 없으면 UNCERTAIN으로 남긴다.

`U_t = S_t union T_t union H_t`.

clip 전체 source bbox 긴 변 L에서 `r=max(2,ceil(0.02*L))`을 한 번 정하고 고정한다. U_t를 radius r만큼 dilation한 core에서 E=1, core 밖4pixel distance band에서1→0 전이, 더 밖은0이다. 전17장에 같은 규칙을 사용한다. Target/source core를 feather로 잘라내지 않는다. 정책과 mask를 고정한 뒤 composite를 만들고 결과를 보고 r/w를 조정하지 않는다.

이 분기는 해당 출력에서 좋은 support를 제공할 수 있을 때의 도움을 보는 참고선이다. 생성 결과를 보고 mask를 정했다는 사실, 수동/agent 작업시간과 support 불확실성을 공개 요약에 적는다. '자동 편집 완성'이나 엄밀한 품질 upper bound로 부르지 않는다.

30분 내 세밀한 mask를 완성할 수 없어도 새로운 GPU 분할·완벽한 matte 감사를 하지 않는다. 가능한 coarse support·uncertainty와 실제 만든 결과를 남기고 MASK_PARTIAL로 마친다. 없는 mask를 만들어졌다고 보고하지 않는다.

두 분기 모두 그래픽이 편집 core 안이나 target과 겹치면 남을 수 있다. 그때 오염 pixel만 자의적으로 지워 해결된 것처럼 하지 않는다. 편집 영역 내부 실패로 기록한다.

## 5. 관측과 수용 범위

SOURCE / B031 RAW / FIXED_ENVELOPE / MASK_ASSISTED를 동시간축으로 보여준다. A0와 target reference도 별도 표시한다. 전체17장, local0/8/16, 차량 경계·바퀴·그림자·그래픽 위치의 확대를 제공한다.

검사 항목:
- E=0 raw source exact, E=1 generated exact. 새로운 인코딩의 MP4를 다시 읽은 픽셀은 손실압축 차이를 구분한다.
- 차량의 큰 차체/방향·거친회전이 보존됐는가, crop/부유/이중 원본 차량이 생겼는가?
- 도로 그래픽이 실제로 사라졌는가, 편집 범위 안에 남는 부분은 얼마인가?
- source 객체가 target보다 넓던 곳에 원본 잔상이 있는가? G 내부가 원본 객체를 남겼다면 합성만으로 해결되지 않는다.
- 경계의 색/밝기 차이, 타이어 접지·그림자 이중화·반사 누락, 고정/움직이는 support의 흔들림.
- ROI/mask 면적, target coverage, 수동 mask 준비시간, CPU 합성·인코딩·검토·패키징 시간.

보호 영역 오차는 E=0 정의만으로 좋게 보일 수 있으므로 source가 그대로인 trivial baseline과 edit footprint·경계/객체 품질을 함께 보고한다. 원본 copy는 객체 교체 실패다. 유효한 새 silhouette/그림자가 원본과 달라지는 것을 무조건 background 오류로 세지 않는다.

연속 재생을 실제로 관측한 주체가 없으면 temporal=UNVERIFIED다. Viewer 재생 버튼 확인은 지각 검수가 아니다. 현재 FPS는 원본 native가 확인된 것이 아니다. 한 vehicle sequence 결과를 모든 객체의 성공이나 통계적 우월성으로 주장하지 않는다.

기술실행 PASS, 원거리 장면 보호, 경계/접촉 품질, target 외형/동작, mask 자동화 수준을 각각 보고한다. Static 결합 목표가 만족돼도 temporal UNVERIFIED와 정확 instance UNCERTAIN은 그대로 둔다. Animal/human 영상은 여전히 NOT_RUN이다.

## 6. 다음 결정 — 이번에는 추가 실행하지 않음

- FIXED_ENVELOPE만으로도 보호 장면·경계가 수용 가능하면 가장 싼 source-preserving baseline으로 보존한다. 곧바로 새 sampler를 돌리지 않는다.
- MASK_ASSISTED만 잘되면 병목은 target-aware support·경계 자동화다. mask 노동비용을 숨기지 않고 다음 방법이 자동화 또는 같은 조건의 품질 이득을 입증하도록 한다.
- mask 밖은 복원되지만 경계·그림자·편집 영역 내부 그래픽이 남으면, 그 실패를 겨냥해 생성 중 원본 문맥 유지/영상 inpainting을 후속에 비교한다. 새 방법의 비교군은 RAW뿐 아니라 이 저비용 compositor여야 한다.
- 차량까지 실패하면 support 불확실성과 generated 내부 실패를 구분하고, 임의 attention 파라미터 sweep으로 돌아가지 않는다.

RePaint와 Blended Latent Diffusion은 알려진 source 영역을 생성 과정에 반영하는 기존 연구다. 이를 SCAIL의 FM/UniPC에 적용하려면 동일 noise level의 source latent와 VAE 오차·시간 압축·solver state를 별도로 맞춰야 한다. 이번에는 이를 구현하지 않는다. 단순 혼합이나 compositing 자체를 신규 알고리즘으로 부르지 않는다.

## 7. 공부·기록·전달

실제 산출물은 새 합성 영상 두 개와 재사용 가능한 CPU composer다. 새 계획문서나 ZIP 검증만으로 완료하지 않는다. 이론은 semantic mask/alpha/edit-support 구분, source/target union, disocclusion·그림자·known-region pixel constraint, 추론 중 제약과 출력 합성의 차이를 실제 코드·관측에 연결해 설명한다.

실행 전 최신HEAD/중복여부를 확인하고 PLAN·mask 규칙·예산을 고정한다. HISTORY/ROADMAP에 B031의 앞단 비강체 실패와 차량 전파 context 실패를 나눠 기록하고 B032의 제한된 역할을 연결한다. 과거 실패를 소급 변경하지 않는다.

종료 후 RESULTS·SUPPORTS·COSTS·REPRODUCE·한국어 lessons·코드를 연구 브랜치에 commit/push하고 원격SHA를 확인한다. 코드·마스크 좌표 오류 등 실제 위험만 작은 CPU 검사로 확인하고 무관한 타입/가중치/커널 감사를 반복하지 않는다.

compact에는 SOURCE/기존RAW/새2합성, 입력 support 시각화·확대 시트·viewer·보고서·재현 코드를 담는다. 기존 영상은 변경하지 않고, 합성 영상은 새 파생물로 명시해 인코딩한다. 새로운 영상에까지 '재인코딩0'이라고 하지 않는다. 대형raw·latent·모델과 과거전체ZIP을 중복 포장하지 않는다.

실제 수행했으면 Spark/Mac /tmp에 단일 작은 ZIP를 보존하고 CRC·payload SHA·추출·전송 동일성을 확인한다. 공개 자료도 재배포 조건을 지킨다. 사용자 개인 미디어·비밀정보·가중치는 공개하지 않는다. 시간이 부족하면 안전하게 결과를 보존하고 전달 미완료 부분을 명시한다.

## 근거

- 프로젝트 B031 RESULTS/ANCHORS @3e669f0f5b284cc9ec178959b4f35e2129896788: 실제 품질·실행은 해당 agent 보고의 관측 범위.
- RePaint (CVPR2022), 공식 연구자 페이지: https://martin-danelljan.github.io/publication/repaint/
- Blended Latent Diffusion (SIGGRAPH2023), 공식 코드: https://github.com/omriav/blended-latent-diffusion

작성자는 이번 세션에서 원격 RESULTS/ANCHORS를 읽었고, 첨부ZIP는 container ClientError/Python InvalidArgumentError로 직접 열지 못했다. 영상·payload hash를 독립검증했다고 주장하지 않는다. 이번 게시 중 생성·모델실행·학습0회다.

# C-001 통합 의뢰서
## Codex Astra의 native imagegen + DGX Spark 로컬 모델로 만드는 양끝 앵커 영상 편집 기준선

작성: 2026-10-28 KST  
상태: **의뢰서 작성 완료 / 실행 전**  
대상 저장소: `hyunlord/make-meme`  
목표 산출물: **공개 두 사례의 원본·참조·편집 앵커·객체 분석·실제 생성 영상을 한 화면에서 비교할 수 있는 첫 기준선**

> 이 파일을 수행 지시로 전달하면 아래 범위의 native imagegen 호출, 로컬 모델 실행, 필요한 제한적 다운로드·격리 설치, 연구 브랜치 기록을 승인하는 의뢰로 사용한다. 현재 이 문서를 작성한 것만으로 모델 실행이나 설치가 이루어진 것은 아니다.
>
> 이번에는 준비·검사 보고서만 만드는 것이 목표가 아니다. 실행 가능한 입력에서는 **편집 앵커를 만들고, 그 사이의 실제 영상을 생성하는 데까지** 진행한다. 단, 접근 권한·도구 부재·실제 자원 충돌을 우회하거나 결과를 꾸미지 않는다.

---

## 1. 최종 연구 방향과 C-001의 제한된 질문

최종 목표는 원본 영상 V, 자연어 지시 P, 선택적 참조 이미지 R로부터, 지정 대상의 외형을 바꾸면서 원본의 지정 동작·배역·카메라·장면을 유지하는 영상 편집 방법이다. 개인 DGX Spark에서 품질·비용·반복 연구 가능성을 함께 평가한다.

장기 구성은 다음이다.

1. 편집 의도와 원본 전체의 객체·움직임 분석.
2. 서로 일관된 시작·종료 앵커 생성.
3. 원본 객체와 편집 객체의 배역·형태·동작 연결.
4. 로컬 모델의 중간 영상 생성.
5. 원인별 피드백·구간 수정.
6. 필요한 경우 고해상도 복원과 최종 합성.

**C-001은 이 가운데 작은 전체 경로를 처음 연결하는 실험**이다. 다음 질문에 답한다.

- native imagegen이 동일 대상의 외형과 해당 시점의 원본 자세를 함께 만족하는 양끝 편집 앵커를 만들 수 있는가?
- 시간축에 놓인 두 앵커를 로컬 영상 모델이 실제로 사용해 중간 프레임을 생성하는가?
- 앵커 일치와 별개로, 중간의 개체 외형·원본 동작·보호 장면이 어디에서 실패하는가?
- SAM 계열 분석으로 어떤 객체·시간 정보와 오류 증거를 확보할 수 있는가?

이번에 새로운 전파 알고리즘, 학습된 동작 전이 모듈, 자동 피드백, 업스케일러까지 모두 완성하려고 하지 않는다. **SAM 분석이 존재한다는 사실과, SAM 정보가 영상 생성 조건에 사용됐다는 사실을 구분한다.**

첫 결과가 좋지 않아도 그 실패를 분석할 수 있으면 기준선 확보에는 의미가 있다. 그러나 파일 생성 성공을 편집 품질 PASS로 보고하지 않는다.

---

## 2. 두 실행 환경의 역할

| 구성 | 책임 |
|---|---|
| Codex Astra 세션 | 실제 사용할 도구 확인, 입력 검토, 편집 명세, native imagegen 호출, 코드 작성·작업 조율·결과 판독 |
| Codex가 연결된 Mac/작업 호스트 | 원본 프레임과 참조를 imagegen이 실제로 볼 수 있게 로드, 생성 파일 보존, Spark로 전달, 검토 자료 수신 |
| DGX Spark | SAM 분석, 로컬 영상 추론, 필요한 VAE/text 처리, 미디어 생성·계측 |
| GitHub 연구 브랜치 | 목적·선택·코드·설정·결과·한계·수학 해설의 이력 |

여기서 ‘Codex Astra’는 사용자가 쓰는 에이전트 환경을 가리킨다. 실제 실행 모델과 이미지 도구의 표시 명칭·버전은 관측한 범위에서 기록한다. 특정 이미지 API 모델 ID나 숨은 내부 구조를 추정하지 않는다.

### 트랙 경계

- A: native imagegen만을 생성 엔진으로 쓰던 기존 MCP 연구. 동결·보존.
- B: 로컬 모델만 사용하던 연구. 결과와 실패를 보존하며 B-034 재개를 이번 전제나 작업으로 삼지 않는다.
- C: **native imagegen의 편집 앵커 + 로컬 영상 생성**. 외부 이미지 생성 의존성을 명시한다.

A/B의 호출 장부·원본·실험 상태를 변경하지 않는다. 이전 생성 이미지를 이번 신규 앵커인 것처럼 쓰지 않는다. 공통 비생성 코드·이미 내려받은 공개 자료·가중치·검증된 venv는 계보를 기록하고 재사용할 수 있다.

---

## 3. 착수·브랜치·실제 도구 확인

### 3.1 저장소와 진행 상태

최신 원격과 로컬 작업 상태를 읽는다. 작성 당시 확인한 B 연구 HEAD는 `4610bfbe77f6991b144281838be02b74c03559c3`이지만, 이를 강제 checkout하거나 이후 변경을 버리지 않는다.

먼저 다음만 읽고 현재 맥락을 확인한다.

- 연구 CHARTER 및 `RESEARCH_V2_SOURCE_PRESERVING_EDITING.md`.
- ROADMAP/HISTORY의 최신 요약.
- B-027의 공개 CASES와 데이터 계보.
- 사용할 기존 VACE 환경·checkpoint의 실제 설정/계보.
- 현재 활성 작업과 기존 사용자의 로컬 자산 위치.

이미 C-001 작업이 시작되었으면 그 기록을 이어가고 중복 실행하지 않는다. 없다면 현재 연구 이력을 포함하는 HEAD에서 별도 worktree/브랜치 `docs/c-research-20261028`을 만든다. 같은 이름이 이미 있으면 덮어쓰지 않는다. main 변경·force push·기존 worktree 정리·파일 삭제는 하지 않는다.

### 3.2 native imagegen 경로

Codex의 실제 세션에 설치된 imagegen skill/도구 설명을 읽고, **기본 내장 imagegen 편집 경로**를 사용한다. 이것은 이 채팅에서 새 이미지 생성 API나 유료 클라우드 영상 서비스를 쓰라는 지시가 아니다.

- 로컬 이미지 편집 전에 `view_image` 등 해당 환경이 제공하는 읽기 도구로 원본과 참조를 실제 시각 컨텍스트에 올린다.
- 이미지마다 역할을 명시한다: 편집 대상 source frame / 외형 reference / 일관성 기준 previous anchor.
- 파일명·경로 문자열만 전달하고 이미지가 입력됐다고 가정하지 않는다.
- 생성 결과는 도구가 실제로 반환하거나 저장한 경로에서 읽고, 전용 C 실험 폴더로 원본 그대로 복사한다.
- 파일 존재, decode, 크기, 출처, 시간, prompt, 호출·재편집 장부를 기록한다.
- 내장 도구가 없으면 `NATIVE_IMAGEGEN_UNAVAILABLE`로 정확히 보고한다. 프롬프트 문서를 이미지 산출물로 세거나 Qwen으로 조용히 대체하지 않는다.
- 별도 OPENAI_API_KEY, CLI/API fallback, Gemini/Kling 등 외부 유료 생성으로 전환하지 않는다. 이 의뢰는 그 전환을 승인하지 않는다.

내장 도구 접근이 불가능하면 가능한 데이터/코드는 보존하되 실제 앵커가 필요한 부분은 미실행으로 남긴다. 없는 이미지를 가정해 샘플링하지 않는다.

---

## 4. 모델 선택 — 한 분석 모델과 한 영상 모델로 제한

### 4.1 SAM 3: 분석 경로

공식 `facebookresearch/sam3`의 사용 가능한 고정 revision·checkpoint를 사용한다. 이미 정상 동작하는 SAM 3 또는 SAM 3.1이 있으면 그 버전을 그대로 고정하며, 이번에 두 버전의 성능을 비교하지 않는다.

SAM은 이번에 다음을 수행한다.

- source 전체 구간의 주 대상 분할·추적.
- 시작·종료 edited anchor의 주 대상 분할.
- 해당 결과의 bbox·중심·면적·가시 여부와 불확실 구간 기록.

SAM은 관절·물리적 접촉·개체의 정확한 정체성을 자동으로 알려 주는 모델로 취급하지 않는다. 원본과 각 앵커의 숫자 track ID가 같다고 배역 연결이 성립한 것으로 보지 않는다.

가중치 접근 동의나 인증이 필요한 경우 기존 적법한 접근을 사용한다. 사용자 대신 약관을 수락하거나 접근제어를 우회하지 않는다. 권한이 없거나 기존 환경과 빠르게 호환되지 않으면:

1. SAM 상태를 `ACCESS_BLOCKED` 또는 `ENV_BLOCKED`로 남긴다.
2. source는 기존 공개 GT instance mask를, 앵커는 제한된 수동 support를 사용할 수 있다.
3. `MASK_GIVEN/MANUAL`과 비용을 명시하고 **양끝 영상 기준선은 계속 진행**한다.
4. SAM 성공·자동 추적 성공으로 보고하지 않는다.

단일 구성요소 설치가 전체 영상 생성을 막는 반복 대기 조건이 되지 않게 한다. SAM 준비에 반복적인 compiler/kernel 개발을 하지 않는다.

### 4.2 영상 모델: 기존 Wan2.1-VACE-1.3B의 양끝 조건 경로 우선

첫 기준선은 품질 최종 후보 선정이 아니라 실행 가능한 작은 end-to-end 실험이다. **기존에 확보한 Wan2.1-VACE-1.3B 계열을 우선 재사용**하고, 공식 `firstlastframe` 전처리와 시간 마스크 조건으로 양끝 프레임을 넣는다.

공식 VACE UserGuide는 `src_video`, `src_mask`, `src_ref_images`를 구분하며, `frameref/firstlastframe`을 별도 task로 제공한다. 따라서 **두 이미지를 순서 없는 reference 목록에 넣는 것과, 양끝 시간에 배치하는 것은 다르다.**

기존 체크포인트가 초기 Preview인지 정식 릴리스인지, 로컬 구현과 어떤 조합으로 검증되었는지 확인한다. 이름이 비슷하다는 이유로 서로의 weight/config를 섞지 않는다. 공식 또는 이미 검증된 first-last 경로를 구현할 수 있는 한 조합을 선택하고 두 사례에서 고정한다.

- 기존 checkpoint와 실행 가능한 코드가 있으면 새 가중치를 받지 않는다.
- 필요한 경우 공식 Wan2.1-VACE-1.3B 한 종과 필요한 구성요소만 별도 경로로 확보할 수 있다.
- 예전 도시 LoRA·학습 adapter는 OFF다.
- SCAIL의 일반 참조 이미지 경로를 양끝 시간 조건이라고 바꿔 부르지 않는다.
- 이번 작업 중 VACE/FLF2V-14B/LTX/AVE를 여러 개 설치하거나 품질을 보고 backend를 바꾸지 않는다.
- VACE의 정확한 양끝 경로가 실제로 연결되지 않으면 구체적 계약 오류를 먼저 수정한다. 구조적으로 지원되지 않거나 예산 내 호환이 불가능하면 `BACKEND_CONTRACT_BLOCKED`로 보고하고 임의 대체 생성으로 성공을 꾸미지 않는다.

이전 B-002~005의 Canny+참조 실험과 다른 입력 계약이다. 과거의 실패를 이번 결과로 대신하지 않으며, 이번 결과도 다른 모델의 한계로 일반화하지 않는다. 이 1.3B 기준선의 품질 한계와 제안하는 희소 앵커 연구 자체의 가능성을 구분한다. 좋은 결과나 실패 모두 이 모델·설정·입력 범위의 결과이며, 작은 기준선 하나로 전체 연구 가설을 입증하거나 기각하지 않는다.

### 4.3 설치 범위

새 weight는 SAM 한 종과 필요한 영상 checkpoint 한 종으로 제한한다. 기존 파일을 우선 재사용한다. 두 모델과 구성요소의 **신규 다운로드 총량 상한은 40GiB**, 공개 미디어 추가 다운로드는 2GiB다. 넘으면 임의 확대하지 않는다.

기존 Torch·CUDA·driver·B 연구 venv를 덮어쓰지 않는다. 필요한 소규모 Python 의존성은 격리 환경에 설치하고 버전을 기록할 수 있다. 공식 요구환경이 Spark와 맞지 않으면 기존 host 환경을 바꾸지 말고 해당 구성요소의 한계를 보고한다. 시스템 전체 패키지 업그레이드나 새 CUDA kernel 작성은 하지 않는다.

---

## 5. 두 공개 사례를 생성 전에 고정

### 5.1 구성

- `case_rigid`: 이동 또는 방향 전환이 있는 단일 강체 대상. 차량을 우선한다.
- `case_nonrigid`: 걷기·고개 회전 등 내부 자세 변화가 보이는 단일 동물. 동물 자료가 부적합하면 사전에 고정한 인물 사례를 사용할 수 있으나 결과를 보고 교체하지 않는다.

기존 DAVIS 공개 자료·mask와 이미 확인한 원천을 우선한다. 모델 입력 크기에서 target이 지나치게 작아 특징을 확인할 수 없는 자료는 생성 전에 제외한다. source와 다른 target 인스턴스를 사용한다. 임의의 사유로 개인 반려견 사진이나 새 촬영을 필수화하지 않는다.

처음에는 두 사례 모두 reference image가 있는 교체 과제로 진행한다. `reference=null`을 명세에 허용하되 텍스트-only 디자인 생성 비교는 이번에 실행하지 않는다.

각 사례는 한 샷·한 주 대상·양끝에서 대상이 가시적인 구간이다. 기본적으로 약2초의 움직임을 목표로 하며, 장면 컷·극심한 가림·두 객체 동시 교체는 제외한다. 입력 후보 검토는 최대6개로 제한하고 두 사례를 이미지 생성 전에 고정한다.

### 5.2 시간·공간 명세

권장 첫 설정은 **33프레임, 480p급**이다. VACE의 `4n+1` 조건과 선택된 pipeline의 실제 지원 크기를 확인한다. 가로 영상의 예시는 832×480이며, portrait이면 비율을 보존하는 공식 허용 크기를 사용한다. 두 사례 모두 같은 면적대·같은 계산 설정을 사용한다.

- 실제 원본 FPS·PTS가 있으면 기록하고, 모델 시간축에 대한 단조 resampling mapping을 저장한다.
- raw frame 폴더만 있어 실제 FPS를 모르면 `source_fps=null`, `timebase_assumed=true`를 명시한다. 이때 16fps preview로 표시할 수 있으나 실제 원본의 초 단위 타이밍 보존을 주장하지 않는다.
- 33프레임/16fps의 파일 지속시간은 33/16초이고, 첫·마지막 표본 사이의 간격은 32/16초다. 둘을 구분한다.
- 이미 있는17프레임을 복제하거나 slow motion으로 늘려 2초 동작을 확보했다고 하지 않는다. 원본의 충분한 구간에서 시간축을 구성한다.
- RGB·마스크·객체 좌표에 동일한 공간 변환을 적용한다. 이미지마다 독립 crop이나 사후 정합으로 동작을 맞추지 않는다.

### 5.3 최소 EditSpec

각 사례에 다음을 기계적으로 읽을 수 있게 저장한다.

```yaml
case_id: case_rigid
operation: replace_subject
source:
  asset_id: <source-id>
  source_frames: <ordered-frame-indices>
  source_fps: <number-or-null>
  model_frame_count: 33
  preview_fps: 16
  timebase_assumed: <true-or-false>
target:
  reference_asset_id: <target-reference-id>
  role_id: edited_subject
preserve:
  - motion_direction_and_event_order
  - camera_and_scene_layout
  - unedited_objects
allow:
  - target_shape_and_silhouette_change
  - necessary_disocclusion_and_contact_adjustment
anchors:
  - {model_index: 0, role: start}
  - {model_index: 32, role: end}
```

원본과 같은 개체를 target으로 골라 source-copy도 성공처럼 보이는 구성은 피한다. 결과 기록과 설명은 한국어로 작성한다.

원본에는 motion pixel GT가 있고 target에는 외형 정보가 있지만, 완성된 교체 영상 GT가 있는 것은 아니다. 전체 픽셀 MSE를 객체 교체 정확도로 사용하지 않는다.

---

## 6. SAM 분석과 객체 연결 — 먼저 원본, 그다음 앵커

### 6.1 원본

짧은 원본 구간 전체를 SAM으로 분석한다. 텍스트 query는 실제 source에서 찾을 개념이며, 아직 존재하지 않는 target을 source에서 찾으라고 하지 않는다.

예: source query `dog` 또는 `car` → 해당 source instance 선택 → `edited_subject`라는 실험 배역 부여.

보이는 마스크, bbox, 중심, 면적, 추적 중 끊김/중복/가림 후보를 저장한다. source의 GT mask가 있으면 보조 비교에 사용하되 SAM 출력과 혼합한 사실을 숨기지 않는다. 수동 수정 전 원래 결과를 보존한다.

### 6.2 앵커

시작·종료 이미지가 만들어지면 각 이미지에서 새 대상을 분할한다. 모델의 숫자 ID를 그대로 배역으로 쓰지 말고, 편집 명세·해당 시점의 위치·target 특징을 보고 같은 `edited_subject`에 연결한다. 첫 단계의 역할 대응은 사람이 확인할 수 있으며 이를 자동 연결 성능이라고 부르지 않는다.

source와 anchor를 별도 동영상인 것처럼 단순 이어 붙여 SAM tracking을 실행하고, 그 결과만으로 cross-domain correspondence가 해결됐다고 주장하지 않는다.

### 6.3 분석과 생성의 경계를 반드시 표시

C-001의 기본 생성 경로에는 **두 전체 프레임 앵커 + caption만 시간 조건으로 전달**한다. SAM 마스크·track은 객체 선택, 앵커 검토, 평가·향후 조건 설계용이다.

결과에 다음 표를 남긴다.

| 정보 | 분석/평가 사용 | 영상 모델 입력 사용 |
|---|---|---|
| 시작·종료 앵커 RGB | 예 | 예, 지정 시점 |
| 원본 중간 RGB | 동작 비교 | 아니오, 기본 기준선 |
| SAM 객체 track·마스크 | 예 또는 fallback 명시 | 아니오, 기본 기준선 |
| 원본 동작의 텍스트 설명 | 예 | 공통 caption |

원본의 모든 중간 프레임을 넣지 않은 경우 source-grounded motion 제어 성공이나 SAM-guided 생성으로 표현하지 않는다. 이 제한이 다음 조건 모듈 연구의 출발점이다.

---

## 7. native imagegen으로 양끝 앵커 생성

### 7.1 시작 앵커

같은 사례의 source 첫 프레임 전체와 target reference를 실제로 보여 주고 편집한다. target reference가 작으면 원천 RGB의 target bbox+고정 margin crop을 추가 supporting input으로 만들 수 있다. crop·resize 규칙과 원본은 보존하며 없는 부위를 생성해 reference로 미리 넣지 않는다.

프롬프트의 골격은 다음이다. 실제 관측과 다른 동작·특징을 추가하지 않는다.

> Image 1 is the frame to edit. Image 2 specifies the replacement subject's appearance. Replace only the selected subject in Image 1 with the subject from Image 2. Keep Image 1's action phase, facing direction, placement, camera, and unedited scene. Preserve the replacement subject's natural proportions rather than stretching it to the original silhouette. Do not copy Image 2's pose or background. Produce one full-frame image, not a comparison sheet. Do not add text, logos, extra subjects, or decorative graphics. [Describe the actual selected subject and visible target traits.]

지시와 RGB·참조 역할을 함께 고정한다. 편집 마스크가 지원되면 공식 인터페이스만 사용하고, 지원되지 않는 파라미터를 만들어 넣지 않는다.

### 7.2 종료 앵커

원본 마지막 프레임 + 같은 target reference + 채택한 첫 앵커를 보여 준다.

> Image 1 is the final source frame to edit. Image 2 specifies the target subject. Image 3 is the accepted first edited frame and is an appearance consistency reference only. Use Image 1 for the final action phase, direction, position, camera, and scene. Keep the same subject/design as Images 2 and 3. Do not copy Image 3's first-frame pose. Produce one full-frame edited image with no new text, graphics, or extra subjects.

각 이미지의 역할을 도구 컨텍스트에서 명확히 한다. 모델이 이전 대화를 실제로 보았는지 불명확하면 자동 기억을 가정하지 말고 지원하는 이미지 입력 경로로 다시 제공한다.

### 7.3 앵커 판정과 한정 수정

기본 생성은 사례별2장, 총4장이다. target 특징, 각 시점의 source 자세·방향, 두 앵커의 개체 일관성, 보호 장면을 평가한다.

- 작은 형태 차이·세부 불확실성은 `ANCHOR_PARTIAL`로 기록하고 진단 영상 생성은 진행할 수 있다.
- 주 대상이 없거나, 배역이 잘못됐거나, source 행동 상태가 완전히 다른 경우는 targeted repair 대상이다.
- 전체에 추가 native imagegen 수정 최대2회, 사례별 최대1회다. 따라서 총 imagegen 최대6회, 한 호출당 출력1장이다.
- 마지막 편집 때 첫 앵커와 외형 충돌이 생기면 한 번의 수정 이유를 기록한다. 두 이미지를 계속 번갈아 다시 만드는 루프는 하지 않는다.
- 수정 후에도 핵심 조건이 성립하지 않으면 그 사례는 `ANCHOR_UNSUITABLE`로 보존한다. 다른 source/reference로 교체하지 않는다.
- 유효한 두 앵커가 있는 다른 사례는 계속 진행한다.

실패·수정 전 raw·prompt·호출 출처도 모두 보존한다. 인간 검토를 하지 않았다면 독립 인간 판정으로 쓰지 않는다.

---

## 8. 로컬 양끝 영상 생성 — 정확한 시간 조건을 사용

### 8.1 기본 입력 구성

선택된 VACE 공식 `firstlastframe` 경로를 사용한다. 개념적으로는 다음과 같다.

- 조건 영상 t=0에는 시작 앵커, t=N-1에는 종료 앵커.
- 사이 프레임은 공식 helper가 쓰는 missing-content 값/표현.
- 시간 마스크는 두 앵커 프레임을 known, 나머지를 generate로 표시.
- 공식 VACE 설명에서는 mask white=생성, black=보존이고 missing RGB=127이다. SCAIL의 RED/WHITE/BLACK semantic 규약과 혼동하지 않는다.
- `src_ref_images` 두 장만 넣는 것으로 위 시간 조건을 대체하지 않는다.

공식 helper의 실제 최종 frame 수와 endpoint 위치를 검사한다. `expand_num`이 총 프레임 수인지 삽입 수인지 추정해서 사용하지 않는다. 기본 예제가81프레임이라고 자동으로33프레임 요청을 덮어쓰지 않도록, **실제 inference 직전 tensor/영상에서 N과 두 endpoint 위치를 확인**한다.

압축 MP4를 통해 조건을 읽는 경우 decoding으로 색과 마스크가 변할 수 있으므로 lossless 프레임/인메모리 입력을 지원하면 우선한다. 파일 입력만 지원하면 실제 decode된 조건의 마스크 값·endpoint RGB·시간 정렬을 검사하고 사용 codec을 기록한다.

### 8.2 생성 설정

선택한 코드 revision의 공식·검증된 기본 sampling 설정을 첫 생성 전에 고정한다. VACE 공식 runner는 sample_steps/shift의 기본값이 다른 Wan 계열과 다를 수 있으므로, **B의 SCAIL 40step/shift3을 근거 없이 복사하지 않는다.**

두 사례에서 동일 solver, step 수, guidance, precision, resolution tier를 사용한다. 본 첫 작업에서는 최적화 sweep을 하지 않는다. 예산은 **run당 최대50 denoising steps**, seed는 고정한 `20261028`을 기본으로 하되 공식 generator의 실제 seed·noise 재현 범위를 기록한다.

CFG 때문에 forward 수가 step 수와 다를 수 있다. 도구가 관측할 수 있는 경우 실제 모델 call 수를 기록하고, 관측하지 않았다면 2배라고 단정하지 않는다.

### 8.3 출력 불변 규칙

- raw generation, 최종 latent가 쉽게 제공되면 그 값, 모든 출력 프레임과 MP4를 보존한다.
- 앵커 이미지를 출력 첫·끝 프레임에 뒤에서 덮어써 endpoint 보존 성능을 꾸미지 않는다.
- 새 프레임 생성 대신 단순 crossfade·정지 이미지 반복을 모델 결과로 제출하지 않는다.
- 오류가 보인다고 프레임을 제거·재배치·출력마다 warp하지 않는다.
- 얼굴 복원·보간·업스케일·색보정·SAM 후합성은 이번 기본 결과에 추가하지 않는다.
- 외형·동작이 틀려도 raw는 그대로 평가한다. 안전·무효 입력 외에는 두 번째 과제를 첫 결과의 품질 때문에 취소하지 않는다.

---

## 9. 실제 실행 운영 — 간단한 오류는 같은 작업에서 수정

### 9.1 새 관리 시스템을 만들지 않는다

기존에 정상적으로 동작했던 로컬 추론 호출을 최대한 재사용한다. C-001 때문에 또 다른 supervisor/worker/감사 하위 시스템을 계속 만들지 않는다. B-034의 역사적 실패를 C 시작의 predecessor 조건으로 가져오지 않는다.

모든 remote 명령은 다음을 명시한다.

- 검증된 Python의 절대경로.
- 존재하는 작업 디렉터리.
- script·config·입출력의 절대경로.
- 필요한 environment와 활성 checkpoint.

한 공통 경로 검사를 거친 값을 preflight와 실제 호출에 함께 쓴다. 상대 stage path가 worker까지 전달돼 다른 cwd에서 해석되지 않게 한다. 전용 실행기를 불가피하게 사용한다면 **그 실제 실행 경로로 CPU-only worker 진입부터 정상 종료까지 한 번 확인**하고 모델을 올린다. 별도 시험용 호출만 성공한 것을 본 호출의 검증으로 보지 않는다.

### 9.2 수정 가능한 오류와 비용 있는 재생성을 구분

| 상황 | 이번 작업 안의 처리 |
|---|---|
| 모델 로딩 전 경로·인자·import·데이터 shape 오류 | 원인을 고치고 CPU 검사 재수행. 같은 의뢰 안에서 이어갈 수 있음 |
| 이미 저장된 latent 이후 디코딩·파일명·인코딩 오류 | 저장물 재사용. sampler를 다시 돌리지 않음 |
| 실제 모델 로딩/생성 후 확인된 기계적 코드 오류 | 아래 공통 예비 GPU 시도1회 범위에서만 복구 가능 |
| 외부 작업 충돌·관측 불가·실제 자원 위험 | 중단. guard를 낮추거나 외부 작업을 종료하지 않음 |
| 단순히 영상 품질이 나쁨 | 결과로 보존. seed·prompt·모델을 바꾸어 재생성하지 않음 |

CPU 오류도 시간·내용·횟수는 기록한다. 하지만 경로 오타 하나를 새 연구 번호와 별도 승인 루프로 만들지 않는다. 무제한 수정은 아니며 전체 시간·설치·생성 예산 안에서 처리한다.

### 9.3 자원·서비스 보호

모델은 SAM/분석 → unload → 영상 모델 → unload 순서로 실행한다. unified memory에서 CPU offload가 별도 물리 메모리를 추가한다고 가정하지 않는다.

기존 승인된 메모리·외부 작업 보호 정책을 재사용한다. 시작 여유72GiB·실행 여유24GiB 등 기존 운영 값은 해당 장비의 보수적 예산이지 성능 보증값이 아니다. 작은 안정된 **system swap 잔량만으로 실패시키는 옛 swap=0 규칙을 재도입하지 않는다**. 작업별 swap 금지·실제 pressure·증가량을 분리하는 최신 정책을 있는 그대로 사용하고 새로 임계값을 바꾸지 않는다. 실제 heavy 상태에서의 검증 여부는 별도 기록한다.

8190이 선택적 보호 서비스인 경우, 이번에도 사용자 승인된 비가동 기대 정책과 실제 프로세스/listener/GPU 부재 관측을 적용할 수 있다. 관리자 인터페이스가 원래 없는 수동 서비스의 ‘정상 종료 증명’을 무한히 찾지 않는다. 서비스·allowlist·시스템 설정은 임의 변경하지 않는다.

관련 프로세스 또는 외부 GPU 작업이 나타나면 현재 이번 작업만 중지/정리한다. 다른 작업을 자동 종료하거나 공유 가능한 작업이라고 추정해 허용하지 않는다. 안전 관측 실패를 성공으로 만들지 않는다.

---

## 10. 승인 예산과 전체 작업 상한

| 항목 | 이번 상한 |
|---|---:|
| 공개 source/target 후보 검토 | 최대6개 후보, 최종2사례 |
| Native imagegen | 기본4회 + 원인 명시 수정2회 = 최대6회 |
| 생성 영상 | 사례별1회 = 기본2회 |
| 예비 heavy 복구 | 전체1회, 기계적 실행 오류에만 사용 |
| 전체 영상 sampler | 실패 포함 최대3회, run당 최대50step |
| SAM 분석 | 두 source clip·선택된 네 앵커의 필요한 분석만. 같은 RGB의 반복 sweep 금지 |
| 새 학습 | 0회 |
| 새 이미지 생성 모델 | 0종. native imagegen만 사용 |
| 새 segmentation checkpoint | 최대1종 |
| 새 로컬 영상 checkpoint | 필요 시 VACE-1.3B 한 종만 |
| 신규 weight 다운로드 | 총40GiB 이내 |
| 추가 공개 미디어 다운로드 | 총2GiB 이내 |
| 업스케일·SR·RIFE 등 | 0회 |
| 전체 wall-clock 상한 | 4시간, 마지막20분은 보존·전달용 |

모델 준비·데이터 확인에 전체를 쓰지 않는다. 필요 시 분석의 자동화 수준을 정직하게 낮추되, 준비된 사례의 앵커와 실제 영상을 먼저 확보한다. 설치 권한·imagegen 부재·실제 GPU 충돌처럼 진행 불가능한 조건은 구체적으로 보고한다. 안전한 결과를 얻었다고 과장하기 위해 상한을 넘기지 않는다.

예비 heavy는 무의미한 추가 예산이 아니라 명시적으로 허용한 **한 번의 기계적 복구**다. 첫 실패와 두 번째 시도를 각각 기록한다. 품질 선택·다른 seed를 위해 사용하지 않으며, 자원 위험이 있었던 경로를 자동 재시도하는 권한도 아니다.

---

## 11. 평가 — 실제 영상 결과를 먼저 보여 준다

### 11.1 생성 전에 고정할 관측

사례별로 다음을 짧게 기록한다.

- target을 구분하는 외형 특징2~3개.
- source의 변화 방향·순서·사건2개.
- 보호할 장면/객체2개.
- 양끝 앵커에 필요한 자세·방향·배치.

독립 실험이 아닌 한 사례의 여러 프레임을 반복 표본으로 세지 않는다. 생성 결과를 보고 유리한 항목만 고르지 않는다.

### 11.2 단계별 판정

| 축 | 판정 내용 |
|---|---|
| 앵커 적합성 | 각 시점의 target 외형·source 상태·보호 장면 |
| 앵커 쌍 일관성 | 두 이미지의 대상 특징과 역할이 연결되는가 |
| 앵커 충실도 | 실제 생성 첫·끝 프레임이 입력 앵커와 얼마나 다른가 |
| 중간 외형 | 비앵커 프레임에서 source 회귀·다른 디자인·중복 발생 |
| 원본 동작 | 방향·이벤트 순서·대략적 시간 관계를 따르는가 |
| 장면 보존 | 원본의 보호 배경·다른 객체가 유지되는가 |
| 시간 품질 | 실제 재생에서 깜빡임·형태 점프·속도·연결 |
| 자원·작업비용 | imagegen·수정·분석·모델 로딩·생성·수동 작업을 분리 |

source-copy는 객체 교체 FAIL이고, reference/anchor 정지 반복은 motion FAIL이다. 멋있게 움직여도 source 동작과 다르면 그 축은 FAIL이다. 시작·끝을 만족하지만 중간이 틀린 경우도 구분한다.

bbox 중심이나 mask IoU가 비슷하다는 이유만으로 관절 운동·동작 보존을 PASS하지 않는다. SAM의 한 track이 유지된다는 사실도 정확한 target 개체 일치의 증거가 아니다.

첫·끝 이미지의 L1/SSIM 등을 보조 수치로 기록할 수 있지만 전체 identity 품질 점수로 사용하지 않는다. shape 변화가 목적이면 source silhouette pixel 일치를 성공 조건으로 강제하지 않는다.

### 11.3 검토 페이지

각 사례를 다음 순서로 배치한다.

`SOURCE / TARGET REFERENCE / START ANCHOR / END ANCHOR / GENERATED VIDEO`

추가로 source-track overlay, 두 앵커의 mask·role 매핑, 전체 프레임 contact sheet, 비앵커 중간0.25/0.5/0.75 시점 확대를 제공한다. 이미지·영상은 실제 파일과 연결하며 placeholder나 다른 실험 결과를 사용하지 않는다.

native preview 속도의 나란한 영상과 프레임 슬라이더를 제공한다. 실제 연속 재생을 지각 검수하지 않았다면 `temporal=UNVERIFIED`를 유지한다. ffmpeg decode·브라우저 재생 가능성과 사람이 본 시간 품질을 혼동하지 않는다. 사용자가 확인할 항목을 viewer에 남기되 검토 전 정적 판단을 확정된 시간 품질로 만들지 않는다.

---

## 12. 수식·수학·로직 학습 문서

`LESSON_KO.md`는 이번 실제 변수·함수·tensor와 연결해 설명한다. 일반적인 생성모델 개론을 반복 복제하지 않는다.

### A. 첫 기준선의 정확한 정보 흐름

\[
A_0=G(V_0,R,P),\qquad A_{N-1}=G(V_{N-1},R,A_0,P)
\]

\[
\widehat V=H_\theta(A_0,A_{N-1},P;\epsilon)
\]

이 기본식에는 source의 모든 중간 RGB나 SAM track이 직접 들어가지 않는다. source에서 관측한 사건을 caption에 서술하는 것과, 시간별 원본 motion tensor를 입력하는 것은 다르다.

### B. VACE 시간 조건의 실제 구현

개념적 조건 영상 U와 생성 마스크 B는 다음처럼 놓는다.

\[
U_0=A_0,\quad U_{N-1}=A_{N-1},\quad U_t=\text{missing}\ (0<t<N-1)
\]

\[
B_0=B_{N-1}=0,\quad B_t=1\ (0<t<N-1)
\]

실제 helper·RGB scaling·VAE 시간 압축·mask tensor의 구현과 연결해 설명한다. 입력 known mask가 있다는 사실이 최종 RGB endpoint의 pixel-exact 보존을 보장하는지 여부는 실제 코드·출력으로 구분한다.

### C. 영상 시간 t와 생성 진행도 s

영상의 첫/끝 위치, 실제PTS, latent 시간 index, diffusion/flow step을 구분한다. `4n+1` 구조와 사용 모델의 시간 압축이 어떤 입력에서 확인됐는지 기록한다. 영상33프레임과 denoising50step을 혼동하지 않는다.

### D. 객체 연결의 범위

\[
O_t^j=(r_j,M_t^j,b_t^j,u_t^j)
\]

role, visible mask, bbox/center, uncertainty의 실제 저장 형태를 설명한다. 이것만으로 새 체형의 부위 대응·3D 가림·접촉이 해결되지 않는 이유를 이번 예시로 설명한다.

마지막에는 이해 확인 질문3개와 별도 답을 붙인다. 다음 가설은 실제 실패를 바탕으로 한 개만 제안하되, 새 방법의 구현·추가 실험은 자동 시작하지 않는다.

---

## 13. 간결한 GitHub 연구 기록

공개 기록은 기존 `docs/research` 안에서 C를 구분해 남긴다. 전체 과거 문서를 다시 작성하지 않는다.

```text
 docs/research/
   C_CHARTER.md
   C_ROADMAP.md
   HISTORY.md                       # C-001 착수·종료 append
   work_orders/C-001-work-order.md   # 이 의뢰서 원문
   experiments/C-001-hybrid-endpoint-baseline/
     PLAN.md
     INPUTS.json
     BACKEND_CONTRACT.md
     RESULTS.md
     COSTS.json
     REPRODUCE.md
     LESSON_KO.md
     code/                           # 실제 사용한 작은 실행·전처리 코드
```

실행 전: 방향·질문·모델 revision·두 case·입력 역할·생성 예산·평가 기준을 고정한다. 실제 설정이 기존 문서와 다르면 시작 전에 이유를 기록한다.

실행 후: 구현 완료와 품질 성과를 분리하고, 미실행·fallback·수정·추가 비용도 기록한다. commit/push와 remote SHA를 확인한다. 파일 수·hash 개수를 최종 보고의 첫 성과로 쓰지 않는다.

기존 B-034는 운영 보류 상태로 연결만 하고 복구하지 않는다. A/B 이력·정답·실패 상태를 덮어쓰지 않는다. C 결과를 완전 로컬 시스템 성과로 부르지 않는다.

공개 GitHub에는 허용되는 코드·문서·비민감 manifest만 올린다. 사진·영상·생성 이미지의 공개 가능 여부는 자료별 이용 조건을 확인하며, 가능하다는 이유 없이 재배포하지 않는다. API key, token, 개인 경로·PID, 조건 tensor·가중치는 공개하지 않는다.

---

## 14. 최종 산출물과 전달

### 필수

- 사례별 source 구간, target reference와 이용/입력 계보.
- 실제 imagegen 시작·종료 앵커와 모든 실패·수정 기록.
- source/anchor 객체 분석 결과, SAM 또는 fallback의 구분.
- 실제 generated MP4와 전체 프레임. 미생성 사례는 원인 명시.
- source/anchor/output 비교 viewer와 contact sheet.
- 실제 입력 조건·코드·설정·모델 revision·seed와 재현 방법.
- 단계별 품질 평가, 실제 시간·자원·호출·수동 작업비용.
- 수학·코드·관측을 연결한 한국어 해설.

### 보관

- **compact ZIP**: 영상·앵커·참조·작은 시트·HTML·보고서·재현. 가능한 한100MiB 이하를 목표로 하되 실제 영상이나 핵심 결과를 누락해 숫자만 맞추지 않는다.
- **full 산출물**: 실제 얻은 raw/최종 latent·필요 수치 자료. 가중치·중복 frame/zip은 제외하고 무조건 거대 ZIP을 만들지는 않는다.
- Spark와 Mac의 실제 `/tmp` 경로에 전달하되, 먼저 생성 파일의 절대경로가 존재하는지 확인한다. 사용 가능한 기존 전송 경로를 재사용한다.
- CRC·payload manifest·전송 파일 hash를 한 번 검증한다. 경량본에 없는 raw까지 검증했다고 하지 않는다.
- 기존 영상의 바이트 보존과 새 비교 영상 인코딩을 구분한다. 전체에 대해 일괄 ‘재인코딩0’이라고 쓰지 않는다.

### 최종 보고 순서

1. 두 사례의 source·앵커·영상은 실제로 어떻게 나왔는가?
2. 앵커 단계와 영상 단계 각각 어디에서 실패했는가?
3. SAM 분석이 실제로 수행됐는가? 모델 생성 입력으로 사용한 정보는 정확히 무엇인가?
4. 개체·동작·장면·시간 품질 각각의 판정은 무엇인가?
5. imagegen 호출, 로컬 생성, 수정·설치·fallback·수동비용은 얼마였는가?
6. 바로 볼 viewer/MP4/ZIP/GitHub 결과는 어디에 있는가?
7. 같은 앵커를 유지한 다음 비교에서 무엇 하나를 바꾸어야 하는가?

상태 예시:
`PIPELINE_COMPLETE / ANCHOR_PAIR_PARTIAL / IDENTITY_PARTIAL / MOTION_FAIL / SCENE_PARTIAL / SAM_ANALYSIS_PASS / SAM_CONDITIONING_NOT_RUN / TEMPORAL_UNVERIFIED`

모든 축을 하나의 PASS로 합치지 않는다. 결과가 좋더라도 한두 사례를 일반화·상용급·논문 기여로 확대하지 않는다.

---

## 15. 이번 다음에는 자동으로 하지 않을 것

- 세 번째 case나 다른 seed 추가.
- 새 video backend 설치·교체.
- 시간 앵커 개수 늘리기, imagegen 무제한 재편집.
- CoTracker·depth·3D·새 조건 adapter 학습을 한꺼번에 추가.
- 자동 피드백·구간 재생성·두 객체·15초·업스케일 실험.
- B-034 복구.

C-001 출력과 실패를 사용자와 검토한 뒤 C-002의 가설을 정한다. 다음 연구의 중심은 ‘같은 앵커와 source에서 원본 motion/객체 연결을 어떻게 실제 생성 조건에 넣을 것인가’다. 첫 기준선의 한계를 숨기기 위해 후속 모듈을 이번에 추가하지 않는다.

---

## 16. 실행자가 확인할 1차 자료

아래는 설계 근거다. 실제 사용할 revision과 로컬 환경을 고정해야 하며, 웹 문서가 Spark에서 실행됐다는 증거는 아니다.

1. OpenAI Codex의 imagegen skill: 기본 내장 도구와 명시적 API fallback 구분, 실제 이미지 컨텍스트와 출력 저장 절차.  
   https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/imagegen/SKILL.md
2. OpenAI Codex 소개: image generation skill 제공.  
   https://openai.com/index/introducing-the-codex-app/
3. SAM 3 공식 저장소: 이미지·영상 분할/추적, 환경 조건, checkpoint 접근 절차.  
   https://github.com/facebookresearch/sam3
4. VACE 공식 UserGuide: `firstlastframe`, `src_video/src_mask/src_ref_images`의 서로 다른 의미.  
   https://github.com/ali-vilab/VACE/blob/main/UserGuide.md
5. VACE 공식 inference runner: 모델/크기/프레임/solver·step·shift의 실제 지원 인자.  
   https://github.com/ali-vilab/VACE/blob/main/vace/vace_wan_inference.py
6. Wan2.1 공식 저장소: 지원 checkpoint와 task.  
   https://github.com/Wan-Video/Wan2.1
7. 기존 프로젝트 공개 입력 기록: source FPS 미확인 등 기존 한계를 새 실험에 조용히 숨기지 않기 위한 근거.  
   https://github.com/hyunlord/make-meme/blob/4610bfbe77f6991b144281838be02b74c03559c3/docs/research/experiments/B-027-public-reference-robustness/CASES.md

**첫 작업의 성공적인 마무리는 ‘환경 검사 완료’가 아니라, 실제로 편집한 양끝 앵커와 그 사이에서 생성된 영상을 보고 다음 가설을 토의할 수 있는 상태를 만드는 것이다.**

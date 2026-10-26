# B-031 입력 사전 고정

2026-10-26, 앵커 생성 전 작성. 입력6쌍은 B-027의 동일 공개 DAVIS track/frame에서 만들었다. A 생성물·개인 반려견 자료·B-028 정규화 결과를 사용하지 않는다. 입력 준비는 CPU만 사용했고 생성 호출은0이다.

## 실제 파일과 변환

Image1은 B-027 `inputs/source/000.png`의 **바이트 동일 복사본**이다. 원래854×480 RGB를 B-027에서896×504로 Lanczos resize한 뒤 위·아래4px BLACK padding을 둔896×512 전체 장면이다. B-031에서 다시 crop/resize하지 않는다. Source의 native JPEG도 함께 보존한다.

Image2는 target의 native854×480 JPEG와 같은 프레임의 indexed GT mask에서 track1을 선택한다. bbox는 오른쪽·아래 exclusive다. **10% margin은 bbox 폭의10%를 좌우 각각, 높이의10%를 상하 각각 더한다.** 왼쪽/위는 floor, 오른쪽/아래는 ceil, native image bounds에서 자른다. 잘라낸 support 내부 RGB는 native JPEG decode 값 그대로, 외부는RGB128이다. feather·생성·회전·warp·추가 resize는0이다. Qwen pipeline 내부의 VAE/VL resize는 별도 실제 실행 관측에 기록하며 이 작은 crop에 새 원본 디테일이 생긴다고 주장하지 않는다.

| Case | Source / target native frame | Image2 W×H | native support px | 실제 입력 한계 |
|---|---|---:|---:|---|
| animal_R1 | dog0 / dog-gooses0 | 175×54 | 3,762 | 낮게 엎드린 작은 개체, 다리·얼굴 세부 불명확 |
| animal_R2 | dog0 / dog-gooses85 | 211×115 | 9,619 | 좌향 이동, 어두운 털 세부·발 경계 흐림 |
| human_R1 | dance-twirl0 / dance-jump0 | 351×378 | 33,486 | 옆/후면 머리, 팔과 치마의 동작 blur |
| human_R2 | dance-twirl0 / dance-jump16 | 312×447 | 33,928 | 앞쪽 식물이 가린 하체가 GT에서 제외되어 회색 빈 영역이 존재 |
| vehicle_R1 | car-roundabout30 / car-shadow0 | 412×234 | 41,790 | 좌향 측면, source와 반대 방향 |
| vehicle_R2 | car-roundabout30 / car-shadow39 | 203×119 | 12,077 | 작은 후측면, 노출·시점·크기가R1과 다름 |

전체 원본 파일SHA는 B-027 `task_manifest.json`의 source/target 기록과 일치함을 검사했다. 파일별SHA·bbox·crop·크기·순서·프롬프트는 [INPUT_CONTRACT.json](INPUT_CONTRACT.json)에 있다. 모든 case에서 Image1→Image2 순서다. 같은 task의 R1/R2는 같은 지시문을 사용한다. 지원되는 실제 pipeline resize와 모델 입력 hash는 환경/실행 장부에서 보완한다.

## 결과를 보기 전 실제 정적 관측

입력 담당 agent가 원본 source 세 장과 target 두 장씩의 실제 crop을 직접 열어 확인했다. 아래는 기존 보고서의 문장을 정답 주석으로 복사한 것이 아닌 이번 입력 관측이다. 인간 독립 평가나 사람 신원 인증은 아니다.

| Task | Target 구분 특징 | Source 첫 자세·방향·장면 내 위치 | 보호할 장면 |
|---|---|---|---|
| animal | source의 옅은 털과 달리 긴 검은 털; R2의 옅은 주둥이/하부 다리와 가슴 일부; R1은 낮고 긴 실루엣으로 미세 얼굴·발은UNCERTAIN | 화면 중앙 왼쪽의 큰 개, 머리는 낮춰 화면오른쪽/카메라 쪽, 몸은 왼쪽으로 이어지고 꼬리는 위로, 앞발 하나가 앞으로 나옴 | 철망 울타리, 오른쪽 관목, 새 실루엣 밖 마른 풀 |
| human | 흰 소매 블라우스; 연분홍 넓은 치마와 진한 분홍 이중 테두리; 어두운 땋은 머리(신원 인증 아님) | 중앙 전경 댄서, 한 팔은 머리 뒤로 굽고 다른 팔은 허리 쪽, 다리는 교차되어 앞발이 화면왼쪽 아래로 뻗음 | 관객 전원과 우측 잘린 다른 댄서, 안뜰 포장면·벽·짚더미 |
| vehicle | 밝은 은색 높은 차체; 루프레일과 높은 창 비율; 세로 후미등 | 중앙 아래 큰 어두운 차, 앞부분이 오른쪽인 측면, 네바퀴 위치를 완벽히 확정하지 않음 | 다른 차량, 건물, 중앙 기념물·난간, 표지판·노면 |

공통 지시는 Image1의 해당 객체를 Image2 대상으로 교체하되 Image1의 자세·향하는 방향·장면 내 위치·카메라를 유지하고 자연스러운 target 비율을 허용한다. 참조 자세/배경 복사, 원래 선택 객체 잔존, 이중 객체, 새 문자·로고·장식을 원하지 않는다. target 특징을 구체적인 색/의상 프롬프트로 대신 지시하지 않는다. R1/R2의 target source track 동일성은 공개 track계보이며 생체 identity 인증이 아니다.

## 생성 전 평가와 영상 선택

여섯 A0에서 target 외형, source 자세/방향/위치, 큰 형태 손상·중복, 보호 장면 변화를 별도로 본다. 단순 recolor/source-copy는 target교체 성공이 아니다. 정지 편집 단계에서 시간 품질을 판단하지 않는다.

영상 후보는 **animal_R1 / human_R1 / vehicle_R1**로 사전 고정한다. R1이 부적합하면 해당 영상은 ANCHOR_UNSUITABLE이며 더 나은R2로 교체하지 않는다. A0는 GT가 아니며 영상 frame0 overwrite/hard clamp에 사용하지 않는다.

## CPU 검사와 재현

`code/prepare_inputs.py`는 기존 파일을 수정하지 않으며 출력 디렉터리가 이미 있으면 거절한다. `crop_target` 소형 fixture2개가 bbox margin/경계 clip, support 내부 exact equality, 외부RGB128을 검사했다. 실제6case에 같은 검사와 B027원본SHA 확인을 실행했다. pytest2PASS, py_compilePASS. 새 패키지는 설치하지 않았다. ruff/basedpyright 실행파일이 없어 타입·lint 전체clean은 주장하지 않는다.

```sh
python code/prepare_inputs.py "$B027_ROOT" "$B031_ROOT/inputs" INPUT_CONTRACT.json
python -m pytest code/test_prepare_inputs.py -q
```

코드는 생성 프롬프트·순서·입력 파일해시를 함께 고정한다. 원본과 신규 입력은 private archive에 보존하고 공개 GitHub에는 코드·해시·관측 요약만 둔다. DAVIS2017 mask-given 개발 패널, CC BY-NC4.0 기록과 미사용 일반화 미입증이라는 B027의 권한·해석 한계를 유지한다. Source FPS는확인되지않아null, preview24fps/timebase_assumed=true이며 실제초단위보존을 주장하지 않는다.

## Vehicle R1 생성 후 실제 support 준비

16:01:30UTC에 시작해16:05:18UTC에 최종 polygon rasterization을 마쳤다(228.29초; 후속 파일전송은 별도). 실제 `vehicle_R1/A0.png`만 보며 수동 polygon을 작성했다. 원본source 또는 target GT mask를 재사용하지 않았다. 초기 draft의 상단 roofline 일부 누락/포함은 실제A0 좌표 grid로 한 번 수정해 최종freeze했고 draft-v1을 비공개로 보존했다. 이는 생성 결과를 보정한 것이 아니라, 생성된 개체 영역을 읽는 수동 annotation이다. 자동mask성능으로 보고하지 않는다.

최종 support76,196px, bbox `[198,184,703,401]`(exclusive)이며 도로의 cast shadow는 제외했다. 창유리와 그 안에 보이는 사람은 차량 실루엣 내부로 유지했다. 얇은 roof rail·뒤 spoiler·차체 하단·타이어 접촉의 약1–3px 경계 불확실성은 남는다. feather·inpaint·새 segmentation·RGB수정은 없다.

`code/manual_anchor_mask.py`가 저장된 polygon을 읽어 내부A0 RGB exact/outside128과 RED/BLACK categorical mask를 만들고 PNG를 다시 읽어 검증했다. 실제mask/poly/preview·초기draft·영수증은 비공개 `video/vehicle/inputs`에 있으며,최종PNG3개의 Spark 전송 후SHA도 일치했다. 이 CPU 검증은 앵커의 편집품질 판정이나 Qwen 프로세스 종료 확인을 대신하지 않는다.

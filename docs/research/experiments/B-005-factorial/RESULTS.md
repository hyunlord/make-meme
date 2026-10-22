# B-005 결과 — 입력 조합의 영향과 동작 전이 실패를 분리함

**COMPLETED: 신규 2/2, 실패 0, 기존 6개 재사용, 학습 0, adapter=null.** 두 seed의 2×2를 완성했다. 네 조합의 8개 결과에서 **실제 Lab identity와 원본 춤을 동시에 수용한 결과는 없다**. 시간 품질은 **UNVERIFIED**다. 추가 제거 실험은 실행하지 않는다.

## 1. 같은 두 seed의 2×2 결과

### seed 20261022

|참조|C-real|C-null|
|---|---|---|
|R-bg|착석 / 기존 B003|사족 / 기존 B003|
|R-gray|착석, 만화적인 얼굴 / 기존 B004|사족, 과장된 광택과 후반 얼굴 흐림 / **신규 B005**|

### seed 20261023

|참조|C-real|C-null|
|---|---|---|
|R-bg|착석 / 기존 B003|사족 / 기존 B003|
|R-gray|뒷발 직립 실루엣 / 기존 B004|사족, 옆을 보며 앞발·꼬리 변화 / **신규 B005**|

범주는 각 run f0~16에서 유지된다. 사족은 네 다리를 쓰는 자세 범주이며 모든 프레임에서 4개 발이 동시에 바닥에 접촉한다는 뜻이 아니다. 가림·발 들림 때문에 정확한 접촉점 수는 미측정이다. [프레임별 정적 판정](frame_observations.csv)은 같은 범주를 기록하되 실제 3D 관절/접촉 추정과 구분한다.

## 2. 원본 동작·개체·전체 형태

원본은 정면에 가까운 시점에서 두 뒷발로 서고 앞발을 든 다른 개체의 17프레임 영상이다. 실제 Lab 정답 영상이나 학습 target이 아니다. 검토는 조건을 알고 수행한 정적 검토이며 블라인드 평가가 아니다.

|조합|seed22 관측|seed23 관측|동작·identity 판정|
|---|---|---|---|
|bg-real|착석, 앞발 바닥·옆으로 벌어진 뒷다리, 은빛 가슴 광택|착석 유지, 가는 몸통·작은 흉부 무늬|원본 직립과 다름, 실제 개체 미수용|
|bg-null|사족으로 방향/다리 변화, f13~16 주둥이·귀 흐림|사족, 머리·꼬리 변화, 길어진 몸통·불규칙한 흉부 윤곽|움직임은 있지만 원본 춤과 다름|
|gray-real|착석, 흰 둥근 눈·벌린 입의 만화적인 외형|직립 실루엣, 옆을 보는 머리·어둡고 가는 몸통, 마지막 발 잘림|직립 범주만 부분적으로 가까움; Lab/안무 성공 아님|
|gray-null|넓은 검은 몸통, 벌어진 앞다리; 정면에서 옆으로 방향 변화. 플라스틱 같은 청색 광택과 f15~16 얼굴 흐림|옆을 보는 사족, 앞발 들기·꼬리 변화. 청록색 경계, 몸통 크기와 발 위치 변화, 하단 발 잘림|원본의 뒷발 지지·들린 앞발·정면 머리 대응 실패, 실제 Lab 얼굴/털 유지 미수용|

새 gray-null 두 결과 모두 일반적인 검은 개는 생성했지만 실제 Lab의 얼굴·귀·체형과 동작을 함께 유지하지 못했다. gray22의 몸통이 넓다는 것 하나로 개체 성공으로 보지 않는다. 자세가 사족인 시점에서 이미 원본 춤 단계와 다르다. 발·목·주둥이 경계와 반사/그림자를 별도 문제로 남긴다.

배경도 바뀐다. seed22 real/bg는 왼쪽 문이 있는 밝은 방, real/gray는 과노출·반사, null/bg는 밝은 빈 배경, null/gray는 밝은 스튜디오 같은 배경이다. seed23 bg-real은 베이지 벽/흰 걸레받이, bg-null은 콘센트/나무 바닥, gray-real은 단순한 밝은 배경, gray-null은 벽과 나무 바닥·강한 색 번짐이다. reference를 회색으로 바꾸어도 배경 생성 경로가 꺼지지 않는다.

현재 원본+8조건 f0/4/8/12/16 시트와 2×2 대표 시트, 신규 2개 및 bg-null 2개 전체 17프레임을 직접 열어보았다. 나머지 4개의 전 프레임은 B004에서 직접 검토했고 이번 복사본 byte 동일성을 확인했으며 이번에도 대표 시트를 대조했다. 모든 8개 전체 시트와 원본 MP4를 ZIP에 포함한다. 실제 연속 재생은 관찰하지 못했으므로 떨림·정지감·전환 자연스러움은 UNVERIFIED다.

모든 run은 서로 다른 17 PNG이지만 이것이 자연스러운 움직임 증거는 아니다. 평균 인접 RGB MAE(0..255)는 bg-real22=1.673, bg-null22=4.436, gray-real22=1.671, gray-null22=6.766; seed23은 각각 1.302, 1.797, 1.738, 7.113이다. 전체 화면의 배경·조명 변화까지 포함하므로 크거나 작다고 원본 동작 추종/시간 품질이 좋다는 뜻이 아니다.

## 3. 실제 입력·코드·tensor 통제

시작 HEAD `582e67ca0b153b5d602b04587b9f57cd36ad3426`, 실행 고정 commit `ac0ecbec709ac72a36668ed22f2d09a42577f257`을 원격 확인한 뒤 두 run을 실행했다. [PLAN](PLAN.md)은 변경하지 않았다. [reuse_audit](reuse_audit.json), [입력 hash](fixed_input_hashes.json), [실행 코드 hash](execution_code_hashes.json).

모델 Wan2.1-VACE-1.3B revision `574e6a744642ce3bee319afc31496b88bde8aac4`, upstream `f39d731a3e318d25b725eb3389cfddb184619842`. 모델/토크나이저 9파일·핵심 upstream 5파일 fresh SHA 일치. 기존 6개의 실제 source/condition/reference/mask decode·전처리·고정 설정·등록 실행 코드·noise를 검증했다. 전체 upstream tree/모든 GPU weight 값 감사는 아니다.

공통 512×288, 17frames, 24fps, 20steps, CFG5, full-white video mask, reference 1장, BF16 SDPA, offload 없음, adapter=null. prompt/negative 동일. sigma_shift5/vace_scale1/tiled 및 기타 [resolved defaults](resolved_defaults.json)는 같은 pinned 소스/호출 경로 근거다. 모두 live scalar hook으로 채취했다고 주장하지 않는다. 실제 runtime 기록도 6개 재사용본과 동일하다.

[run_summary.json](run_summary.json)의 실제 8셀 tensor 검사:

|항목|실측 shape|두 seed 각각의 4셀 비교|
|---|---|---|
|noise|1×16×6×36×64|같은 seed의 4셀 완전 동일|
|positive/negative text|각 1×512×4096|동일|
|inactive video|1×16×5×36×64|동일|
|mask|1×64×6×36×64|동일|
|reference prefix|1×96×1×36×64|같은 R끼리 동일, R에 따라 2가지|
|reactive video|1×16×5×36×64|같은 C끼리 동일, C에 따라 2가지|
|전체 VACE context|1×96×6×36×64|4가지 조합의 서로 다른 hash|

전처리 RGB video 1×3×17×288×512는 코드 유도 shape이고 실제 sampler context는 hook 관측이다. RGB0 C-null은 정규화 −1을 VAE로 인코딩하며 latent0이 아니다. RGB128 reference는 기존 gray 한 장을 동일 pad로 사용하며 prefix를 유지한다. 따라서 두 null은 branch-off가 아니다. 이 조합이 학습 분포 밖일 가능성 및 reference photo를 요구하는 텍스트와 회색 참조의 충돌을 남긴다.

## 4. 상호작용을 어떻게 해석하는가

seed22에서는 두 참조 모두 real 착석→null 사족이다. seed23에서는 bg가 real 착석→null 사족인 반면 gray는 real 직립 형태→null 사족이다. 참조에 따라 구조 내용 교체의 출력 반응이 달라지는 정성적 상호작용이다. 자세 범주에 임의 숫자를 붙여 연속 품질 점수나 통계적 유의성을 만들지 않았다.

gray23에서 real만 직립이었다는 관측은 그 고정 조건의 Canny 내용이 직립 형태에 기여할 수 있다는 제한적 근거다. 그러나 원본 발/머리 궤적과 실제 Lab를 동시에 전달하지 못했으므로 유용한 춤 전이의 증거는 아니다. 외형·자세·배경을 함께 바꾼 대체 입력과 두 seed만으로 조건의 순수한 보편적 인과 효과나 reference 지배를 단정하지 않는다. [한국어 이론](../../lessons/B-005-conditioning-interaction.md), [질문](QUESTIONS_KO.md), [해설](ANSWERS_KO.md).

## 5. 자원·범위·검증

|신규 run|process 초|pipeline 초|peak allocated/reserved bytes|최저 MemAvailable bytes|실패|
|---|---:|---:|---|---:|---|
|gray-null22|52.058|38.176|17,056,366,080 /17,687,379,968|74,433,101,824|0|
|gray-null23|54.040|38.096|동일|74,433,343,488|0|

swap 0, 무거운 GPU 작업 순차, 다른 서비스 유지, 잔존 추론 process group 없음. Spark 통합 메모리를 CPU/GPU 두 배로 합산하지 않는다. 신규 학습/모델/imagegen/외부 API/재시도 0. A 기존 111파일 hash 불변, 기존 6개 복사 480파일 원본/복사본 동일. Python compile/AST 및 검증기 negative fixture 통과. lint/typecheck는 도구 미설치로 NOT_RUN이며 성능/품질 통과와 다르다. fixture는 검증 배선 검사이지 동물 품질 검사가 아니다.

2개 비교 MP4는 1536×576, 17frames 24fps 0.708333초. 왼쪽 source, 오른쪽 2×2 행 bg/gray·열 real/null. 원본 8개 출력도 보존. 보간·crossfade·frame 복제·속도 변경 없음. [재현](REPRODUCE.md), [진행](RUNNING.md), [자원](resource_summary.csv).

## 6. 다음 연구 하나 — 동물 움직임 표현의 적합성 검증

**동일 원본 17프레임에 동물 관절 궤적·가시성·발 접촉을 명시하는 표현을 만들고, 원본의 직립 지지와 머리/발 변화를 보존하는지 검증하는 연구**를 제안한다. 머리 방향, 어깨/골반, 네 사지 관절과 발에 동일 ID를 두고 가림/미관측은 명시하며 추정값으로 채우지 않는다. 먼저 수동 검토 가능한 작은 source overlay/trajectory를 기준으로 삼는다. unusual 직립 동물에서 자동 추정 모델의 일반화를 가정하지 않는다.

동물 영상 keypoint/trajectory를 별도 연구 대상으로 다루는 근거는 [APT-36K 논문](https://arxiv.org/abs/2206.05683)과 [공식 저장소](https://github.com/pandorgan/APT-36K)다. 이는 현재 VACE가 이 표현을 바로 지원하거나 생성 품질이 개선된다는 증거가 아니다. 다음 계획에서는 해당 동작 표현을 실제 받는 로컬 모델/주입 경로의 지원 여부를 먼저 확인한다. 사진 기반 identity 조건과 동작 조건을 독립적으로 점검하고, 연결 부재면 BLOCKED로 남긴다.

이번에는 이 표현 구축·모델 설치·학습·추론을 실행하지 않았다. 같은 Canny/reference 제거 실험을 더 늘리지 않는다. 전체 제작·IG·윙크·발차기·Kling 수용은 NOT_RUN, 자연스러운 Lab 춤은 NOT_ACCEPTED다.

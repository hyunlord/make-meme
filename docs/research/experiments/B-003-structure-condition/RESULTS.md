# B-003 결과 — 구조 입력은 영향을 주지만 직립 춤으로 이어지지 않았다

**통제 비교 COMPLETED. 신규4/4 완료, 실패0, 재사용0, 학습0, adapter=null.** 두 seed 모두 C-real은 착석, C-null은 사족 자세였다. 차이는 명확하지만 네 결과 모두 원본의 뒷발 직립 춤을 재현하지 못했다. **시간 품질은 UNVERIFIED**, 실제 Lab 개체·동작 전이 성공은 수용하지 않는다.

## 실행과 통제 근거

사전 계획 `7368c1f9ff70030ff6490b1ff4a0a88e9213ebe2`, 실행 코드 `49c41ecaec76acba5e785421d8a4a35be5ac7e8b`의 push와 원격 SHA 일치를 확인한 뒤 순서대로 네 번 실행했다. 결과를 보고 조건을 바꾸거나 재시도하지 않았다. 시작01:26:56 UTC, 추론 네 번을01:42 UTC 이전 완료했고2시간 deadline을 넘지 않았다.

- 기존 Wan2.1-VACE-1.3B revision `574e6a744642ce3bee319afc31496b88bde8aac4`, DiffSynth `f39d731a3e318d25b725eb3389cfddb184619842`. 모델·토크나이저9파일과 핵심 upstream5파일 fresh SHA256 일치. 전체 upstream tree 인증은 아니다. [기록](model_revalidation.json).
- 고정 R-bg, 동일 prompt/negative,source f0~16,white video mask,512×288,17frames,24fps,20steps,CFG5,sigma_shift5,vace_scale1,BF16,SDPA,offload없음. [설정](configs/C-real-20261022.json), [resolved defaults](resolved_defaults.json).
- C-real 원본 PNG는 L이지만 실제 VideoData 출력은 RGB uint8 `(288,512,3)`, 값0..255다. C-null도 같은 형식이며 모든 값0이다. null의 정규화 값은−1이고 VAE latent0이나 branch제거가 아니다. [decoded 입력 실측](decoded_input_audit.json).
- 실제 noise `(1,16,6,36,64)`,text `(1,512,4096)`,VACE context `(1,96,6,36,64)` 관측. 두 seed 각각 noise/positive/negative text/reference prefix/inactive/mask hash가 같고 reactive video/context hash만 달랐다. 같은 condition의 context는 seed를 바꿔도 같았다. [실행/해시/자원](run_summary.json).
- reference는 RGB pad 후 VAE encode; 영상 전처리 BCTHW `(1,3,17,288,512)`는 코드로 유도한 shape이고 이 값 자체에 새 runtime hook을 달았다고 주장하지 않는다. 실제 관측 context의 reference slice는 `(1,96,1,36,64)`, inactive/reactive는각 `(1,16,5,36,64)`,mask는 `(1,64,6,36,64)`다.
- source RGB는 비교/기록용이며 실제 모델 구조 입력은 Canny/null이다. source를 Lab 정답 학습 영상으로 사용하지 않았다. parameter_counts_unchanged는 개수 검사이며 GPU 가중치 값 전부를 비교한 것은 아니다. runner에는 optimizer/adapter load 경로가 없고 실행모드는 inference다.

## 2조건 × 2seed 정적 관측

원본+네 결과의 f0/4/8/12/16 시트, 각 결과의17프레임 전체 시트,대표 f8 및 null22 f15 원본512×288을 실제로 열어 보았다. 조건 이름을 알고 검토했으며 블라인드 평가가 아니다. **연속 재생은 직접 관찰하지 못했다.**

|조건|seed|자세·지지발·원본 대응|개체·형상|배경|
|---|---:|---|---|---|
|C-real|20261022|착석. 앞발 두 개가 바닥에 있고 한 뒷다리는 옆으로 벌어짐. 원본처럼 앞발을 들고 뒷발로 서지 않음|검은 개·늘어진 귀 유지. 목/가슴 강한 은빛 광택, 옆 다리와 몸통 비율 어색함. 정확한 Lab 개체 수용 불가|밝은 방과 왼쪽 문. 기존 사진의 침대/커튼 배치는 안 보임|
|C-null|20261022|사족 자세에서 다리·몸 방향 변화. 원본의 직립/발 위치와 다름|후반 f13~16 머리·발 경계 흐림, 특히 f15 주둥이/귀 형태가 뭉개짐. 체형과 얼굴 유지 미수용|밝은 빈 배경, 바닥 접촉 그림자 있음. 원본 반사 재현 수용 아님|
|C-real|20261023|착석과 바닥의 앞발 유지. 작은 머리 변화가 있으나 직립 춤 단계 아님|검은 개지만 가슴/몸통이 가늘고 밝은 가슴 무늬. 실제 사진의 묵직한 체형 부족|베이지 벽·흰 걸레받이·밝은 바닥|
|C-null|20261023|사족으로 서서 머리·꼬리 위치 변화. 뒤쪽 다리 겹침이 있어 매 프레임 실제 접촉발 수를 확정하지 않음|검은 개·늘어진 귀, 길어진 몸통과 가슴 밑 불규칙한 털/윤곽. 정확한 얼굴·사지 수용 불가|벽·콘센트·나무 바닥. 참조 침실의 구체적 복사는 아니지만 새 환경은 생성됨|

두 seed 모두 **주요 자세 범주가 착석→사족으로 달라졌다(2/2쌍)**. 네 전체 시트에서 원본의 뒷발 직립 자세로 성공한 run은0/4였다. 이는 수동 범주 관찰이며 프레임별3D접촉점·pose detector·정량적 동작 유사도를 측정한 결과가 아니다. 가림 때문에 모든 발의 정확한 접촉 수는 미확정이다.

source는 짧은 직립·머리/몸 흔들림 구간이다. null의 더 큰 이동이나 꼬리 변화가 '춤을 더 잘 따라갔다'는 뜻은 아니다. real의 작은 변화도 안정된 영상 품질 성공으로 해석하지 않았다. 보조적인 전프레임 RGB MAE 평균(0..255단위)은 real22=1.673,null22=4.436,real23=1.302,null23=1.797이다. 전경·배경을 함께 세는 픽셀 변화량일 뿐이며 작을수록 좋은 점수나 source motion 유사도 지표가 아니다.

## 해석

1. **구조 입력을 무시한다는 가설은 지지되지 않는다.** 실제 reactive context가 달라지고, 같은 noise/reference에서 두 seed 모두 출력 자세 범주도 달라졌다. 변화가 단순한 작은 픽셀 잡음에 그치지 않았다.
2. **원본 안무에 유용한 구조 전달은 입증하지 못했다.** real이 null보다 원본 뒷발 직립에 가깝다는 관측은 없으며 둘 다 실패했다. 이 frozen baseline의 Canny 표현·white mask·조건 결합·sampling 설정 한계를 우선 검토해야 한다.
3. **reference 자세가 단독으로 지배한다는 결론도 아직 불가하다.** 같은 착석 reference를 주어도 null에서는 사족이 나왔다. real조건의 착석은 reference/구조/prior의 상호작용일 수 있지만 이번 실험은 reference를 바꾸지 않아 원인을 분해하지 못한다. 'reference가 언제나 구조보다 강하다'는 일반화는 하지 않는다.
4. black 입력은 윤곽을 없애면서 조건 분포도 바꾼다. 순수한 motion channel 제거 또는 VACE off 실험이 아니다. 두 seed·한 장면·한 reference의 국소적 근거다.

## 자원·출력·검증 범위

|run|process초|pipeline초|40회 model forward 합계초|peak allocated GiB|
|---|---:|---:|---:|---:|
|real20261022|72.06|40.46|33.89|15.89|
|null20261022|88.06|40.43|33.84|15.89|
|real20261023|90.07|40.11|33.46|15.89|
|null20261023|94.07|40.18|33.48|15.89|

총 child process 약344.25초. peak allocated17,056,366,080bytes,reserved17,687,379,968bytes. 최소 MemAvailable63,704,711,168bytes(59.33GiB),swap0. Spark GB10 통합메모리를 CPU/GPU별 총량으로 중복 계산하지 않았다. loading·관측 I/O가 포함돼 성능 벤치마크로 일반화하지 않는다.

네 원본 output MP4와 seed별 source|real|null 비교 MP4 모두17frames/24fps/0.708333초다. 마지막 샘플시각은16/24초. ffprobe/실제 decode 프레임 수를 확인했으며 보간·복제·crossfade·warp·속도 변경 없음. loop 끝→처음 점프는 내부 동작이 아니다. 파일 검증과 시간 품질 관찰은 다르다.

입력/실제 tensor/코드hash/조건pairing/인코딩 검사는 통과했다. Python compile/AST는 통과했으나 Ruff/BasedPyright가 사용 가능한 경로에 없어 NOT_RUN이며 새 설치하지 않았다. 기존 연구 코드의 타입/스타일 문제를 제품 수준 품질 통과로 보고하지 않는다. [검사 범위](static_checks.json).

## 다음 실험 하나 (이번에는 미실행)

**C-real을 고정하고 R-bg 대 같은 크기의 균일 회색 reference 한 장을 비교**한다. 참조 장수·latent 시간 길이·초기 noise 배치를 유지하면서 reference의 개체/착석 시각 정보가 사라졌을 때 구조의 직립 전달이 나타나는지 묻는다. 회색은 'reference 경로 제거'가 아니고 개체 정보도 함께 사라지므로 identity 개선 실험이 아니다. 이 비교를 계획 고정 후 별도로 승인받아야 하며 자동 실행하지 않았다.

## 자료 및 상태

[한국어 이론](../../lessons/B-003-structure-conditioning.md),[질문](QUESTIONS_KO.md),[별도 해설](ANSWERS_KO.md),[재현](REPRODUCE.md),[입력해시](input_audit.json),[실행장부 요약](run_summary.json).

사진·개인 영상·생성출력·전체로그는 GitHub에 올리지 않고 private ZIP에 보존한다. 공개 문서·코드·해시만 연구 branch에 반영한다. A는 동결,전체제작·IG·윙크·발차기·Kling 수용은 NOT_RUN. 추가 추론/학습은 실행하지 않고 이 비교로 종료한다.

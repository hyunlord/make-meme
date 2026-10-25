# B-025 결과 — 참조 외형은 바뀌지만 IG의 누운 자세도 복사됨

**COMPLETED / 기술 실행 PASS / 참조 외형 반응 관측 / IG 원본 자세·동작 보존 FAIL / 전체 객체 편집 목표 FAIL / temporal UNVERIFIED.** B024의 개선과 source-copy 한계, 이전 실패 기록은 그대로 보존한다.

## 실제 두 출력에서 달라진 것

Root와 별도 검토 에이전트가 실제 raw에서 나온 전체17프레임 및 local0/8/16을 원본·두 참조와 정적으로 비교했다. 독립 사람 검수나 실제속도 연속시청으로 보고하지 않는다.

| 평가 | 새 REF_LAB | 새 REF_IG |
|---|---|---|
| 외형 반영 | 검은 털, 넓은 주둥이, 늘어진 귀와 상당한 몸통 | 회갈색 털, 흰 목가슴·발, 좁은 주둥이, 큰 눈·접힌 귀, 가는 사지. 단순 recolor보다 강한 참조 반응 |
| 전신 자세 | 원본처럼 사족으로 서 있음 | 참조 사진처럼 몸을 말고 누운 자세가 전체 구간에 남음. 원본 사족 기립 FAIL |
| 고개 방향·순서 | 앞을 보다가 후반 image-left로 돌아가는 큰 순서가 source와 대응 | 후반 왼쪽/아래·몸 쪽으로 고개를 돌리지만 원본의 서 있는 자세와 머리 궤적을 재현하지 않음. 국소 변화만으로 motion 성공 아님 |
| 형태 | 얼굴·눈·털이 원본보다 매끈하고 일부 비율/입 모양이 달라짐 | 사진과 닮은 얼굴·가는 사지지만 접힌 다리·접촉은 불확실. 심한 후기 얼굴 번짐이나 이중 검은 Lab는 정적 시트에서 보이지 않음 |
| 장면 | 타일·러그·로프·의자·창가·랙·전경 팬 구도를 대체로 유지 | 방·가구 구도는 대체로 남지만 바닥 로프가 사라지고 개체의 위치·점유영역이 달라짐. 장면 보존 PARTIAL |
| 배경·framing | 중앙 침실 구획이나 참조 letterbox 복사 없음 | 침실 침구는 없지만 누운 참조의 자세·구성이 강하게 남음. 전체 신체가 보인다고 편집 성공은 아님 |
| 실제 반려견 일치 | UNCERTAIN; 같은 개체 source-copy로도 설명 가능 | 여러 관측 특징이 참조 방향이지만 정확한 실제 개체 일치/숨은 부위는 UNCERTAIN |
| 시간 품질 | UNVERIFIED | UNVERIFIED |

따라서 '두 출력 모두 source의 검은 Lab만 유지한다'는 결과는 아니다. 참조 묶음이 외형을 바꾸는 근거는 얻었다. 그러나 **원하는 개체로 바꾸면서 원본의 동작·장면도 유지**하는 결합 목표는 IG에서 실패했다. IG가 더 가늘다는 이유로 source와 관절 pixel 완전일치를 요구한 것이 아니라, 서 있던 동물이 누워 버린 실제 자세 차이를 판정한 것이다.

이번 조건에서는 reference 외형과 reference 자세·공간 구성이 함께 반영됐다. 이를 VAE 또는 CLIP 한 경로의 원인으로 확정하지 않는다. RGB·semantic mask·사진의 pose/support가 함께 바뀌는 묶음 비교이며, 순수 identity 인과효과·새 개체/장면/seed 일반화·상용급 품질은 미입증이다.

## 입력·실행 통제와 원본 보존

사전 공개 고정 commit `61724a656105ac5365e603be12f250b195ae70f1`. 같은 실제 Lab source f126..142,17프레임·30fps·896×512, 동일 중립 caption/empty negative, 실제 initial noise/RNG/UniPC40shift3CFG5를 사용했다. 정식 replacement=True, history/additional_ref=None, adapter/ALG/manualRoPE OFF다. B024 출력은 다른 caption의 역사 맥락이며 새 REF_LAB 대조군을 대신하지 않았다.

두 참조는 첫 sampler 전에 고정했다. Lab은 B024 회색 RGB/RED-BLACK mask를 exact 재사용했다. IG는 기존 사용자 원본과 기존 support이며 원본·workpack derivative hash를 구분했다. resize 후 개체 RGB를 보존하고 밖/padding만128로 채웠다. 새로운 segmentation·pose/scale warp·외형 생성은 없다. 얇은 발·꼬리 support 한계는 PARTIAL_UNRESOLVED다.

공통 positive T5 1회, IG VAE/CLIP 각1회, Lab encoder 재실행0회. 실제 cache pair는 ref/CLIP/refmask 6leaf만 변경, 나머지10leaf와 device구조 동일이다. 별도 원시 safetensor 검토도 48 payload의 hash/shape/dtype를 확인했다. LAB-vsB024는 positive t1만 변경됐다. 첫 실제 forward의 양 CFG 참조 객체 연결을 기록했으며 관측용 추가 forward는0회다. [조건](CONDITIONS.md), [검증](evidence/condition-review.json).

두 raw는 finite FP32[3,17,512,896]이며 각각 최종 generated x0[16,5,64,112]에서 공식 VAE decode로 나왔다. 실제40step80forward 완료 후 최종 latent를 먼저 저장했다. raw→전체17PNG는 각각 기록된 uint8 변환과 exact 일치한다. 원본이나 참조를 후처리로 붙인 결과가 아니며 ROI 합성·얼굴복원·SR·보간·warp·프레임 선별은 없다. 모델이 참조 자세를 재현한 현상과 파일 합성을 혼동하지 않는다.

## 사용량과 검증 상태

신규 sampler2/2회, case별 PROBE/S/D 각1회, 재시도0. 공통 인코딩118.26초, S worker는 Lab1032.16초/IG1034.79초, D worker는13.24초/12.68초다. 각 S CUDA peak33.85GiB, cgroup peak약62.01GiB이며 시스템 최소 가용은 각각53.12/52.28GiB다. 서로 다른 회계를 합산하지 않는다. cgroup.high6216/6009는 기록하고 max/OOM/kill0·swap0·headroom 종료0을 확인했다. [실측](MEASUREMENTS.md).

새 학습·모델/패키지 설치·다운로드·imagegen·외부 생성0. 작업 worker/watchdog 종료 및 기존 서비스 보존을 확인했다. 기존 동적 runner 타입 진단은 NOT_CLEAN, 사용 불가 linter는 설치하지 않았다. CPU4계약/compile, 실제 encoder/sampler/decode 및 raw 계보 검증을 타입 청결이나 시각 과제 PASS와 혼동하지 않는다.

## 바로 볼 자료와 다음 병목 하나

비공개 `review.html`에서 source/두 참조/두 raw, 전체17장, local0/8/16 및 native30fps 비교를 제공한다. 17/30초 파일이며 루프 경계는 내부 움직임과 별도다. Chrome 파일 로딩·재생 조작 확인은 인간 시간 품질 검수와 다르다. 최종 ZIP에는 두 raw/MP4/final latent, 참조·선택 source, 조건 hash/재현/실패 근거를 포함하고 대형 weights·중복 prefix를 제외한다. 위치·CRC·전송 hash는 최종 전달 기록에 남긴다.

**다음 가설 하나:** 동일 IG 개체의 실제 사족 기립 reference를 확보할 수 있다면, 현재 누운 reference와 다른 조건을 고정해 비교하여 reference 자세와 목표 자세의 일치가 전신 동작 보존 병목인지 검증한다. 이번 결과만으로 이 가설이나 encoder 원인을 확정하지 않는다. 추가 촬영/수집·생성·학습·sweep을 이번에 실행하거나 예약하지 않는다.

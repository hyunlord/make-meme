# B-017 결과 — 실제 검토용 case 2개, 학습-ready 0개

**COMPLETED_CPU_AUDIT / RIGHTS_PENDING / DATA_GAP.** 실제 source 파일로 R/D/Y 구성이 완비된 검토 case2개와 Lab 정답이 없는 미완성 후보1개를 만들었다. 실제 cross-ID motion pair0, training-ready0, 신규 생성·전체 모델 적재·VAE encode·optimizer update·LoRA0이다. 이번에는 학습하지 않았다.

## 세 질문에 대한 답

| 질문 | 결과 | 근거·제한 |
|---|---|---|
| 학습 배선 확인용 자료가 있는가? | **파일 구조는 있음, 학습 실행 READY는 아님** | SELF_RECON_SMOKE 후보1개. D=Y이며 R=첫target. source 진위·학습 권한 UNKNOWN |
| 참조 자세 변화 자료가 있는가? | **다른 시점 후보1개, 충분한 자세 변화 NOT_ESTABLISHED** | f0는 target[7,24) 밖이지만 f0/f7은 비슷한 직립 자세. 작은 위치/크기 차이를 관절 변화로 승격하지 않음 |
| 실제 cross-ID motion pair가 있는가? | **0개** | Lab R은 있으나 실제 Lab Y 없음. 다른 강아지나 실패 생성물로 채우지 않음 |

case2개가 서로 다른 target2개라는 뜻은 아니다. 같은 기존 source f7..23 하나에 reference만 두 가지다. Lab 후보는 완성 pair 수에 포함하지 않는다. 모든 자료는 development이며 독립 train/validation/test0이다. 권한이 미확인인 제3자 source가 실제 촬영 동물인지도 확인하지 못했으므로 REAL_GT라고 부르지 않는다.

## 실제 구성과 검사

시작 원격은 `ffe0369682eb2b0c3a903c44a2f23d5ff91b2299`. 선정 규칙 commit `3898e4b`, 복사/시트 코드 `c6838be`, 실제 case 검사 전 validator freeze `16b1479`를 각각 원격 고정했다. 최대8개를 채우려고 자료를 늘리지 않았다. 등록root의12개 관련asset record만 조사했으며 홈 전체·새계정에 접근하지 않았다.

| case | 구조 | D=Y 파일/픽셀 | R=Y첫프레임 | R/Y 시간 중첩 | 누락/차단 |
|---|---|---|---|---|---|
| self_f7 | 완비 | true/true | decoded·원본계보 true | true | target origin UNKNOWN, training rights 미확인 |
| pose_f0 | 완비 | true/true | decoded·원본계보 false | false | pose variation 미확인, origin UNKNOWN, rights 미확인 |
| lab_missing_target | 미완성 | 판정 불가 | 판정 불가 | 판정 불가 | Y·target근거caption 없음, rights 미확인 |

case 파일19개(기존 media 복사16개와 새 caption2개·누락안내1개) 및 작은 시트2개를 만들었다. 14개 media 역할을 실제 CPU decode했다. RGB/mask shape512×896, 영상17frame·24fps·PTS0..16/24가 선언과 일치했다. 모든 역할의 파일 SHA는 기존inventory와일치했다. source 원본은361frame·24fps·timebase1/12288이며 기존처리구간의 sample시각은7/24..23/24초다. 시트는 모든17frame을 포함하며 마지막 빈tile은 프레임이 아니다. 기존 crop/확대/마스크결함을 개선하지 않았다.

[CPU 결과](CPU_RESULTS.json), [원본-복사 해시](COPY_HASH_CHECK.json), [자료 계약](DATA_CONTRACT.md), [권한·split](RIGHTS_AND_SPLITS.md), [asset 요약](ASSET_SUMMARY.json). 실제 경로·PTS·decoded frame hash·private manifest는 비공개 ZIP에 있다. CPU 검증기는 biological identity나 mask의 실제 발 경계를 판정하지 않으며, 해당 증거의 declared/UNKNOWN 상태를 유지한다.

11개 synthetic validator fixture는 잘못된 identity·target/mask/caption 누락·generated target·split leakage·시간축 오류 등을 검출했다. Ruff와 all-mode typing은0error/0warning. 이것은 실제 학습/동물품질검증이 아니다. source mask의 얇은 발·반사 경계는 PARTIAL_UNRESOLVED이고 연속 재생에 의한 품질 평가는 수행하지 않았다.

## 공식 training 경로에서 확인한 것

Wan revision `78fe19576bb06be96c2375e088574a262a300edb`, SAT revision `ac63f8eb369e2f4fac2ce273ead0ae7e602c3919`를 고정해 읽었다. 활성 inference checkout은 바꾸지 않았다. [TRAIN_INTERFACE](TRAIN_INTERFACE.md)에 실제 파일/함수/줄을 연결했다.

- Y, reference, RGB driving, semantic mask는 별도 cache 필드다. 기존 inference16leaf만으로 supervised Y가 갖춰지는 것은 아니다.
- `first_frame_pth`는 GT f0가 아니라 **R+뒤zero RGB를 VAE로 인코딩한 영상**이다. 실제 SAT는 해당 필드의 존재와 history mask를 별도로 사용한다.
- 공식 RFLoss target은 ε−E(Y), history/OCR 제외 후 전체 원소 평균이다. mask 유효면적 재정규화가 아니다.
- 17pixel-frame은 시간압축 후 latent5이며, 공개 예제 bucket17/21 및 reader의fps16을 그대로 적용하면 이번 데이터계약과 맞지 않는다. 새 인코딩/loader실행은 NOT_RUN이다.
- generic LoRAMixin과 lora_train 분기는 있지만, 공개 SCAIL 예제의 실제 mixin 주입·이름필터·frozen-base/optimizer 검증이 연결된 즉시실행 recipe는 확인되지 않았다. ‘LoRA전혀없음’도 ‘바로실행가능’도 주장하지 않는다.

## 공개 데이터·로컬 대안

[공식 후보 감사](PUBLIC_DATA_AUDIT.md): MotionPair는 요청/terms 기반이며 실제 확보0, APT계열은 sparse pose/tracking으로 연속17f24fps·정렬된cross-ID pair를 자동 제공하지 않는다. 코드 Apache/MIT가 영상data권한을 대신하지 않는다. 신청·가입·이메일·코퍼스다운로드0이다.

Reverse driving은 기존 SCAIL 연구의 방법이다. local-only 생성 D+원본Y도 motion 오류 검증·생성비용·source권한이 필요하고, 허가된 rig의 retarget render pair도 자산권리·도메인차이·제작비가 있다. 현재 실패생성의 motion을 정답처럼 취급할 수 없으며 두 경로 모두 이번에 실행하지 않았다.

## 다음 한 작업

**권한을 확인한 실제 Lab의 자연 동작 영상 Y와 다른 자세 reference R를 작은 촬영 세트로 확보하는 것**을 제안한다. private training 범위·동일 개체·session·시간축을 기록하고 독립평가는 별도session으로 분리한다. 억지 직립 춤은 요구하지 않는다. 자연동작과 의인화된춤의 domain gap, D=Y의 shortcut은 남는다.

현재는 권한·진위·실제LabY가 부족하므로 backward/LoRA를 바로 시작하지 않는다. 필요한자료가 확보된 뒤에만 배선/gradient/base보존/reload/메모리 검증을 별도 결정한다. 추가 생성·학습·ALG/Hoffset탐색은0으로 종료한다.

[한국어 수학·코드 해설](../../lessons/B-017-paired-data-and-flow-training.md), [재현](REPRODUCE.md). 양 호스트 ZIP·CRC·해시·추출 재현 검증은 [전달 기록](DELIVERY.md)에 남겼다.

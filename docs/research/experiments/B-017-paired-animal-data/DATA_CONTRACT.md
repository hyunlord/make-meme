# B-017 실제 R/D/Y 계약

## 자료 역할과 세 수준

R은 생성할 개체의 reference, D는 동작 조건, Y는 supervised target이다. 파일이 존재한다는 사실, 동일 source-track이라는 사실, 실제 생물학 개체/촬영 진위, 학습 허가는 별도다.

| 검토 case | R | D/Y | 수준·한계 |
|---|---|---|---|
| self_f7 | source f7 | 둘 다 기존 source f7..23 | SELF_RECON_SMOKE 구조. R도 첫 target frame이므로 쉬운 복사 shortcut |
| pose_f0 | source f0, target 범위 밖 | 둘 다 같은 source f7..23 | SAME_ID_POSE_VARIATION **후보**. f0/f7 자세는 가깝고 충분한 참조 자세 다양성은 UNCERTAIN |
| lab_missing_target | 기존 실제 Lab 사진 | D는 기존 source; Y 없음 | 미완성 후보. CROSS_ID_MOTION_PAIR 완성 건수에 포함하지 않음 |

자기 재구성과 자세 변화 후보는 별도 수준으로 분류하되 실제 target clip은 하나다. 두 record를 서로 독립 데이터나 서로 다른 동물 두 마리로 세지 않는다. Source는 사용자 제공 제3자 밈 자료이며 실제 촬영/합성 여부 UNKNOWN이다. 동일 opening track의 R/Y 연결은 확인했지만 REAL_GT·생물학적 동일 개체로 확장하지 않는다. Lab의 실제 사진과 source 개체는 다르다.

## 공식 raw 역할 매핑

| 공식 파일 역할 | 이번 private case | 처리 |
|---|---|---|
| GT.mp4 / video_pth target | GT.mp4 | 기존 처리 source MP4 바이트 복사; Lab 후보에는 없음 |
| rendered_v2.mp4 / driving | rendered_v2.mp4 | 같은 파일 복사, D=Y 명시 |
| rendered_mask_v2.mp4 | rendered_mask_v2.mp4 | 기존 RED driver mask 바이트 복사, 새 segmentation 없음 |
| ref.jpg | ref.png | 기존 lossless PNG 보존. 공식 cache 경로 값에 실제PNG를 지정할 후보이며 .jpg로 이름만 위장하지 않음 |
| ref_mask.jpg | ref_mask.png | 기존 RED/WHITE PNG 보존; JPEG 색 손상 방지 |
| prompt.txt | prompt.txt | source에 보이는 크림색·직립·후기 고개 기울임·장면만 서술; Lab Y가 없으면 caption도 missing |

이 raw 역할 매핑은 공식 cache writer/SAT loader 실행 성공이 아니다. 새 VAE encode·16leaf cache 작성·전체 모델 load·backward를 수행하지 않는다. first_frame_pth 등의 실제 의미는 [공식 학습 경로](TRAIN_INTERFACE.md)를 따른다.

## 시간·공간·split

기존 source는24fps이며 선택17frame은 f7..23이다. sample 시각은7/24..23/24초, 구간 support는[7/24,24/24)초다. clip의 encoded PTS는0부터 다시 시작한다. 파일 길이17/24초와 첫/마지막 sample 간격16/24초를 구분한다. f0 reference는 target구간 밖이고 f7은 첫frame과 계보가 같다. PNG와 MP4 decode의 바이트 차이는 코덱 차이와 원본frame 계보를 별도로 확인한다.

512×896 입력은 과거512×288 전처리에서 확대/crop된 기존 산출물이다. 신규 고해상도 촬영/개선이 아니다. RGB/mask는 기존 동일 시점·크기를 보존하며 얇은 발·반사·경계 결함은 PARTIAL_UNRESOLVED다.

모든 source 파생 case는 같은 source/identity-track/session 그룹의 DEVELOPMENT다. Lab 입력도 반복 사용한 development이며 독립 test로 재분류하지 않는다. TRAIN/VALIDATION/TEST 할당0, 독립 test0. 프레임 구간이 겹치지 않아도 같은source/session을 train/test로 나누면 누수다.

## 권한과 readiness

이번 사용자 지시는 제한된 private CPU 검토/자료 구성을 허용한다. 원작자의 학습·재배포·상업 권한을 대신하지 않는다. 실제 Lab target 부재 및 source 권한/진위 UNKNOWN을 무시해 training-ready로 만들지 않는다. 공개에는 익명 역할·해시·검사 코드만 포함하고 media/mask/개인경로/좌표는 포함하지 않는다.

완성된 **검토용** case2, 미완성 Lab후보1. 학습 허가 완료0, 확인된 실제 cross-ID motion pair0. 추가 사진만으로 target video와 motion pair가 생기지 않는다. 다음 학습 시 기존 추론 cache16leaf 외에 올바른 Y latent, train schema, gradient 경로와 메모리 실측이 필요하다.

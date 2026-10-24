# B-017 사전 데이터 선정·판정 규칙

기준 PLAN: 시작 HEAD ffe0369682eb2b0c3a903c44a2f23d5ff91b2299. 새 생성/학습/전체 모델 적재0, case최대8. 기존 연구 manifest가 가리키는 자료와 명시된 asset root만 조사하며 관련source최대30. 개인 홈 탐색·신규 계정·데이터 접근신청·대량 다운로드는 하지 않는다.

## 선정 순서

1. 기존 B-012 f7..23 처리 RGB·mask와 source 원본의 계보를 검증한다. 동일 source의 첫 프레임 reference 자기재구성은 `SELF_RECON_SMOKE`다.
2. 이미 준비한 동일 source의 f0/reference mask가 있으면 target f7..23 밖 reference로 `SAME_ID_POSE_VARIATION` 후보를 만든다. 실제 자세 차이는 이미지를 보고 제한적으로 기록한다. D=Y shortcut은 유지된다.
3. 실제 Lab 사진은 R 후보이며 같은 Lab의 실제 Y가 없으면 `missing_fields`로 남긴다. 다른 개체 source·생성실패를 Lab Y로 쓰지 않는다.
4. 실제 R/Y identity와 D/Y 사건 대응이 모두 입증된 경우에만 `CROSS_ID_MOTION_PAIR`로 센다. 단순 같은품종/걷기label/합성shape변환은 해당하지 않는다. 없으면0이다.

## 기술·권한·평가 분리

- private 검토용 구성과 training-ready를 분리한다. 사용자 자료 제공은 public redistribution 허가가 아니다. 제3자 원본의 training권한 UNKNOWN은 READY에서 제외한다.
- 실제 decode, frame count/shape/fps/PTS, RGB-mask 대응, D=Y 파일/decoded equality, R=Y첫frame, 원본frame시간중첩을 기록한다.
- 같은 source/identity/session 및 파생물은 모두 development로 묶는다. 기존 f7..23/Lab 실험은 독립test가 아니다. 독립validation/test가 없으면없음으로 쓴다.
- mask는 기존 것만 재사용한다. 없으면missing_fields. JPEG 공식이름 때문에 semantic색상을 손상시키는 변환을 하지 않으며 필드매핑·실제format을 명시한다.
- 실제 관절·접촉 주석이나 신체변형은 추가하지 않는다. 정밀pose차이는 UNCERTAIN이어도 자료 수준/누수 판단은 계속한다.

CPU fixtures는 identity mismatch·missingtarget/mask·synthetic target·split leakage·D=Y/R=first 등의 검출만 검증하며 실제 동물품질/학습업데이트를 의미하지 않는다. 실제 case 계약은 실행 전 코드 commit/hash와 함께 보존한다.

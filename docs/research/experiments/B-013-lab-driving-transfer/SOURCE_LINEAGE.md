# B-013 입력 계보

**PASS_CPU_INPUT_REUSE**. 새 영상 생성·원본 재디코딩/재축소·새 마스크 생성 없이 기존 실물 파일을 복사하고 SHA256을 대조했다.

- LAB_MOV: B-012 MOV의 processed source f7..23 RGB17장·mask17장·두24fps MP4와 정확히 같은 바이트.
- LAB_STILL: B-012 STILL의 source7 RGB+mask 반복17장·두 MP4와 정확히 같은 바이트. RGB와 mask 모두 정지한다.
- 공통 reference: B-008/009가 사용한 실제 검은 Lab의 processed512×896 RGB. SHA256 `703884c8e2a657d4294cf4e74efeb463c9cd6e05e1ad582f99d6546b954cfdce`. B007A가 기록한 실제 원사진 SHA256은 `54f8052c7264139a41d2818d5c881abd2442f462b5d02cc7908c1f360f00fadb`; 이번에는 원사진을 다시 crop하지 않았다.
- 공통 reference mask: B-009 RED+WHITE 파일 그대로. SHA256 `ea54f417f109793210c405d2452152b839fd57f81329811fb650958e830bab9f`. RED113928/WHITE344824, 다른색0. RGB와 동일512×896 좌표이며 양조건 공통.

실제 RGB와 마스크 이미지를 직접 열었다. 침대 위에 앉은 검은 Lab의 접힌 귀·넓은 주둥이/가슴·굵은 앞다리와 앞다리 사이의 배경 틈이 기존 실루엣에 대응한다. 얼굴/귀/털/발의 얇은 경계·바닥 경계는 PARTIAL이며 보정하지 않았다. 고양이·IG·A 생성자산은 사용하지 않았다. 이 정적 확인은 개체 생성 수용이나 분할정답 인증이 아니다.

B-012의 현재 processed RGB를 그대로 쓰므로 이전 B006와의 최대9레벨 decode 차이를 다시 만들거나 교체하지 않는다. 이전 원본·reference·mask·출력은 변경하지 않았다. 비공개 계보 장부는 두 case 각각38파일, 총76파일의 복사 전후 SHA 일치를 보존한다.

고정 upstream helper의 실제 이미지 함수 두 개를 AST 추출하여 CPU에서만 실행했고 네 전처리 tensor shape/dtype/value SHA를 기록했다. 각 case의 pose_video 및 driving_mask_video는 대응 B-012 tensor와 정확 일치한다. Lab reference img/ref_mask_img는 두 case에서 정확 일치한다. 자세한 safe 해시와 크기는 [INPUT_PREPARATION.json](INPUT_PREPARATION.json)을 참조한다. 실제 P cache/양 CFG 조건 비교는 runner의 별도 검사이며 이 CPU 감사로 대체하지 않는다.

WHITE는 배경 가시성 의미이므로 침실이 유지되는 것만으로 전신 자세 실패를 판정하지 않는다. 전체 직립/앞발 전이, 국소 머리 roll, 개체·체형 일치를 각각 평가한다.

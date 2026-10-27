# 고정 방법의 새 입력 이식

B-033 `clean_constraint.py`는 바이트 변경 없이 사용한다. SHA256은 `7c24c3c14d39e07ea77f01fd45ffe13c051e1c7ef14be77f8329348ed120aebb`다. BASE는 공식 UniPC, STEP은 같은 클래스의 clean-prediction 변환 후 corrector/history 진입 전 제약만 적용한다. sampler/정밀도/CFG 및 양 branch는 동일하다.

각 과제는 ENC → BASE_S → BASE_D → CONTROL_D → STEP_S → STEP_D를 별도 프로세스로 실행한다. ENC는 공식 조건 준비와 원본 full-resolution VAE 인코딩 한 번을 수행하며 DiT는 생성하지 않는다. CONTROL_D는 저장된 source latent 복원과 BASE final latent의 일회 혼합을 각각 디코딩한다. STEP은 같은 조건 캐시와 초기 noise를 사용한다. BASE와 STEP의 최종 latent는 디코딩 전에 원자적으로 보존한다.

BASE 이후 표시한 실제 target support와 기존 source support의 합집합으로 E를 고정한다. B-032의 `max(2,ceil(0.02*L))` dilation과 4px feather를 적용한다. 새 과제에 과거 사례의 숫자 11을 강제하지 않는다. source와 target core의 M=1 포함을 검사한다. H는 확인되지 않은 그림자를 정답으로 넣지 않고 비운다. E와 M은 세 비교에 동일하다.

PNG endpoint는 E=0에서 source uint8, E=1에서 generated raw의 기존 floor 양자화 값을 명시적으로 복사한다. 경계만 float blend한다. 이 규칙은 B-033 export 수정과 같으며 마스크 축소·오염 제거 후처리가 아니다.

이 문서는 실행 연결 설명이다. 코드 작성이나 compile 성공은 영상 또는 품질 PASS를 의미하지 않는다.

실제 첫 두 CFG 호출의 noise hash 검사는 작은 CPU 복사를 수행한다. ref/CLIP 연결 검사는 객체 동일성을 확인하며 별도 attention dump나 추가 DiT forward를 수행하지 않는다. 이를 모든 관측 hook의 복사가 0이라는 주장으로 확대하지 않는다.

source reconstruction 및 FINAL_ONLY는 BASE 결과에 대한 대조이며 sampler가 아니다. 새로운 source 조건은 새로운 ENC에서 계산하지만, 동일 과제의 BASE와 STEP 사이에는 파일 단위 동일한 cache/noise/RNG/scheduler를 공유한다. 원본 frame bundle의 원래 FPS는 미확인이고 preview24fps는 가정된 재생 시간축이다.

# B-027 고정 공개 편집 과제

GPU 생성 전 선정. 공통 seed20261022, replacement=True, 896×512,17frames, UniPC40/shift3/CFG5, adapter/ALG/manualRoPE OFF. 실제 원본 FPS/PTS를 확인하지 못했으므로 source_fps=null, preview_fps=24, timebase_assumed=true다. 프레임 순서만 보존하며 원본 초 단위 타이밍 보존을 주장하지 않는다.

| 과제 | source A, track1 | target B, track1 참조 | 사전 동작 사건 | target 외형 근거 |
|---|---|---|---|---|
| animal | dog f0..16 | dog-gooses f0 / f85 | 고개를 낮춘 채 번갈아 앞발을 디디며 카메라 방향으로 접근; 후반 더 정면이 됨 | 어두운 털, 흰 주둥이·가슴/발 일부, 옅은 source와 다른 실루엣 |
| human | dance-twirl f0..16 | dance-jump f0 / f16 | 교차 스텝에서 앞으로 진행; 후반 다리를 벌리고 팔을 내림 | 흰 블라우스, 분홍 테두리의 연분홍 치마, 어두운 땋은 머리 |
| vehicle | car-roundabout f30..46 | car-shadow f0 / f39 | 화면 오른쪽 주행; 측면에서 뒤쪽 면이 더 보이는 방향 전환 | 밝은 은색 높은 차체, 루프레일, 세로 후미등·높은 창 비율 |

각 target의 두 사진은 동일 공개 sequence의 track1이다. source와는 서로 다른 sequence 및 관측 외형이다. 사람의 생체 신원이나 데이터셋 외 개체 이력을 인증한 것은 아니다.

검토 범위는7sequence, 최종9입력묶음(3source구간+6reference)과 제외3묶음으로 최대12다. dog-agility f0/f16은 폴 가림·motion blur·경계 잘림 때문에 생성 전에 제외했다. car-roundabout f0..16 대신 회전 시점 변화가 더 드러나는 f30..46을 고정했다. 결과를 보고 선정하지 않는다. 참조의 중간/끝 thumbnail은 해당 track의 자세 차이를 확인하기 위한 열람이며 추가 생성 후보가 아니다.

## 입력 처리와 한계

공식 DAVIS instance label을 직접 사용한 **mask-given** 평가다. 자동 대상 선택·추적·segmentation은 NOT_RUN. RGB와 mask는 동일 aspect-fit 좌표로 옮기며 RGB Lanczos, label nearest, source padding BLACK이다. 이는 과거 개인 영상의 FFmpeg area 대신 새 공개 JPEG 입력에 고정한 공통 resize이며 같은 task 두 조건은 동일하다. reference support 밖과 padding은128, reference semantic RED/BLACK, driving semantic RED/WHITE다. 개체 warp·crop·mask 보정은 없다.

animal R1은 4197개의 support pixel, R2는10601pixel로 얼굴 세부가 작다. R1 낮게 웅크림과 R2 사족 이동 자세·시점·크기가 함께 다르다. 이를 identity-only 또는 pose 하나의 효과로 해석하지 않는다. human R2는 전경 관목이 가린 부분을 GT가 제외하여 아래 실루엣에 빈 부분이 있다. vehicle R2는 멀고 작으며 빛 조건도 다르다. 이 한계를 고치거나 선택적으로 숨기지 않는다.

보호 영역은 animal의 울타리·오른쪽 관목·잔디, human의 관객·돌담·포장면, vehicle의 건물·난간/기념물·표지판·다른 차다. 합당한 새 실루엣 가림과 먼 배경 소실을 구분한다. 원본 객체는 edited pixel GT가 아니다.

중립 caption과 자세한 사건·한계는 [selection.json](selection.json)에 사전 고정했다. reference별 외형을 text로 대신 지시하지 않는다. 3paired task, 단일 seed의 개발 패널이며102개 독립 표본 또는 일반 성공률이 아니다.

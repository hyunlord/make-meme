# B-022 사전 평가 계약

출력 전에 B-020의 보존된 source 전체17장과 과거 비교 시트를 다시 읽었다. 과거 생성은 이번 matched20의 대체물이 아니다. 실제 source는 사족으로 서 있고 후반 머리가 화면 왼쪽으로 돌아간다. 카메라 시점과 장면은 별도의 착석 reference와 다르다.

## 고정 비교

SOURCE / B-021 정확한 step20의 새 생성 / 그 checkpoint에서 재개한 step100의 새 생성. 896×512·17frame·30fps, 전체 프레임, 같은 초기 noise와 sampler. 역사 B-0200/20은 별도 맥락이다. 정량 보정되지 않은 관절 좌표·각도·유의성·임의 gain을 만들지 않는다.

- 전신: target의 사족 서기인가, reference 착석이 남는가.
- 머리: 초기→후반 방향·순서가 source와 대응하는가. 단순 움직임 증가를 성공으로 세지 않는다.
- 얼굴/귀/주둥이/목: 형태 손상과 경계 잘림을 구분한다.
- 개체/체형: 검은 Lab 견종 유사성과 실제 개체 충실도를 구분한다. 불명확하면 UNCERTAIN이다.
- 프레이밍/장면: reference portrait 영역·white padding·배경 복사를 따로 보고한다. animation 배경 유지와 target 장면 복원의 목표를 혼동하지 않는다.
- 시간 품질: 전체 정적 시트 관찰과 연속 재생 관찰을 구분한다. 실제 연속 시청을 하지 못하면 UNVERIFIED다.

## 수치/기능과 품질의 분리

B-02020/B-02120 velocity maxabs/RMS/relative L2, factor차이와 고정입력 BA작용, OFF대비 변화, 동일tail 반복backward는 각기 다른 관측이다. loss 감소가 자세·개체 성공을 보증하지 않는다. 기능 parity는 기존 atol=rtol1e-3이며 B-021의 독립 replay 허용오차를 변경하지 않는다.

동일clip 네tuple의20/50/100 평가를 tuple별로 표시한다. holdout은 같은clip 별도noise/time이며 독립영상test가 아니다. 좋은 중간 checkpoint 선택·후처리 warp·프레임 선별을 하지 않는다.

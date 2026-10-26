# B-032 실행 전 고정

상태 PREPARING. 최신 원격 a05b098c83be26639e23a05b4d0945c8c7850bf2에서 PLAN/결정을 읽고 Mac/Spark의 기존 B032 디렉터리·실행이 없음을 확인했다. A checkout과 과거 결과는 보존한다.

사용자 수행 지시가 실행 승인이다. 보수적 시간 예산 시작2026-10-26T17:24:00Z, CPU 신규 작업 마감18:39:00Z, 전체 종료18:54:00Z. 실제 단계 시각은 따로 기록한다. GPU worker/이미지/encoder/sampler/VAE decode/학습/설치 모두0. 기존 raw tensor를 CPU로 역직렬화하는 것은 VAE decode가 아니다.

## 고정 정책

- Source17개 GT support+A0 support bbox의 각 방향10% 확대, floor 좌상/ceil 우하·canvas clip, 바깥0·안쪽8px 선형 feather. 생성영상의 그래픽으로 ROI 조정 금지.
- MASK_ASSISTED는 생성된 실제 주행 차량의 출력 support를 제한된 agent polygon으로 표시한다. source와 target union, 관측 가능한 접촉 그림자를 넣는다면 별도 H와 근거를 보존한다. 모호한 그림자는 H 정답으로 만들지 않는다.
- Source clip bbox 긴변 L에서 r=max(2,ceil(.02L)), Euclidean 거리 기준 radius r dilation core는1, 바깥4px 선형 feather, 나머지0. 모든17장 동일 정책.
- RGB 같은 좌표/프레임 순서의 float 합성, E0 source exact/E1 generated exact를 인코딩 전에 검증. uint8/MP4 변환은 명시하고 손실 영상 픽셀과 구분.
- target core coverage·source 제거영역·그림자/경계·그래픽 잔존을 별도 평가. 출력mask는 독립 human GT가 아니며 coarse MASK_PARTIAL 허용.
- 전체17장/local0·8·16/경계·접촉·그래픽 확대를 고정. temporal UNVERIFIED. 원본FPS불명 preview24fps·17frame·896x512 유지.

코드·입력·mask 계보는 합성 실행 전 별도 freeze에 연결한다. 두 결과 이후 종료하고 생성 중 개입을 자동 실행하지 않는다.

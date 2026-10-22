# B-006 실행 기록

시작 기준 remote HEAD: `f6819d2a5e487516896e1169237d910bd98354fd`.
2026-10-22 UTC, 기존 PLAN·CHARTER·ROADMAP·HISTORY·RECORDING_PROTOCOL·B-005 RESULTS 확인.
공개 문서 worktree와 비공개 Mac/Spark 실행 디렉터리를 분리한다. A checkout 및 기존 실험은 수정하지 않는다.

## 실행 전 고정

- 작업 상한 3시간. 보수적 시작 05:25 UTC, 종료 상한 08:25 UTC.
- 신규 모델 다운로드·diffusion 추론·optimizer update 모두 0.
- 원본 RGB와 Canny 17프레임·24fps를 해시 대조한다. 기존 생성 결과를 동작 정답이나 annotation 입력으로 쓰지 않는다.
- 관측은 수동 검토이며 자동 pose 모델 성능이 아니다. 2D 관측 불가능한 관절은 null, 접촉은 실제 증거 수준을 명시한다.
- 학습된 조건 의미와 일반 3채널 입력 수용을 구분한다. SCAIL-2는 source-only 공식 branch 고정 조사이며 Spark 실행 가능성은 모델을 실행하지 않은 한 UNKNOWN이다.
- 원본 시점/동작을 재생성하지 않고 overlay·trajectory만 만든다. 결과를 보기 전에 code/schema를 커밋한다.

진행: 입력 검증 및 코드·schema 준비, 공식 모델 인터페이스 독립 조사 중.

## 관측·코드 보완 기록

- 사전 코드 commit `5a001865026f8a1a6000877a4133aed502a77fd2` 원격 확인 후 입력 복사·수동 주석을 실행했다.
- 주석 전에 validation을 보완했다: visible-null / hidden-coordinate 모순, 4발 contact 상태, possible/unknown의 touching=null 검사. 대표 확대 overlay에 ID 라벨을 추가했다. 표현 의미·상한은 바꾸지 않았다.
- 17장 모두 개별 관측. 실제 보이는 7개 표면점/프레임만 기록하고 나머지는 null로 유지했다. 원본 RGB/Canny34파일 해시 대조와 CPU 영상 인코딩 완료; 시각화가 모델 동작 전이 성공은 아니다.
- 교육용 PyTorch CPU heatmap 코드와 synthetic contract fixture를 추가했다. 실제 annotation 입력에 실행하기 전에 별도 code commit을 고정한다. 별도 velocity 계산기를 만들지 않고 기존 finite-difference 기록을 재사용한다. toy fixture는 동물 추정 성능이 아니다.

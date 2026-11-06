# V-006 결과: 원격 상태 확인 불가

**새 영상의 완료와 다리 개선 효과는 확인하지 못했다.** W1-a 생성 중 Spark SSH와 Tailscale ping이 응답하지 않았고, 이후 Tailscale peer가 offline으로 바뀌었다. 마지막 확인은 50 scheduler step 중 41, model_fn 호출 84회 시도·83회 완료다. 최종 latent·33프레임·MP4·정상 종료 receipt는 가져오지 못했다. 연결 상실만으로 전원 차단이나 모델 실패를 단정하지 않는다.

|변형|실행 상태|검토 가능한 새 영상|
|---|---|---|
|W1-a|UNKNOWN_REMOTE_UNREACHABLE: 생성 1회 시작, 완료 미확인|없음|
|W1-b|NOT_RUN: W1-a 중간 전달 선행 조건 미충족|없음|
|W2|NOT_SUPPORTED: 두 참조의 input/noise latent 시간축 불일치|없음|

첫 실제 CFG step은 44.27초, 적재 시간을 포함한 50 step 예상은 37.45분으로 60분 시작 기준을 통과했다. 이는 완료 시간 실측이 아니다. 마지막 가드 관측은 CLEAR, MemAvailable 약96.8GiB, PSI full 0이었다. 최종 peak 메모리·hw.csv 최고값·커널 로그는 미수집이다. 보존된 첫 모델 입력은 bf16 [1,16,9,80,144], 토큰 25,920이다.

## 강도와 준비 결과

CPU에서 시작 σ는 W1-a 0.7291666269302368, W1-b 0.859375로 다르며 둘 다 low expert 경계0.875 아래다. 실제 모델 입력에서 확인한 값은 W1-a뿐이다. 공식 low expert의 1,095개 tensor를 bf16으로 변환하고 원본 cast와 bit 단위 일치를 검증했다. 원본은 보존했다. W2는 CPU shape fixture에서 단일 참조10/10, 요청한 두 참조10/11을 확인했으며 모델을 적재하지 않았다.

## 전달과 제한

Downloads 폴더는 현재 기록과 빈 사용자 검토 양식을 담는 **상태 보고물**이다. 요청한 W1-a 합성본 두 종류와 확대 비교의 중간 전달은 미완료다. 실제 RAW 없이 대체 영상을 결과처럼 넣지 않았다. 출력 SAM·합성·지표·출력 SAMPLE은 NOT_RUN이다. HUMAN_REVIEW_PENDING, temporal=UNVERIFIED를 유지한다.

원격 worker는 Spark tmux와 사용자 systemd 가드에서 실행되며 다음 단계를 자동 시작하지 않는다. 설정된 RuntimeMaxSec 최대3,900초는 원격 정상 종료의 증거가 아니다. 연결 복구 전 종료 여부는 UNKNOWN이다. 재부팅·원격 작업 재시도·W1-b 시작·다른 작업 종료는 하지 않았다. 복구 시 완료 산출물과 부팅 로그를 먼저 확인해야 하며, 전원 차단이 확인되면 의뢰서대로 남은 실행을 중단한다.

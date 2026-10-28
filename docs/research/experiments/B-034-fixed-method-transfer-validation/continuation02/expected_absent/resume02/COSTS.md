# 이번 재개의 비용과 시도 장부

- 모델 적재·sampler 시도 각1회 사용. sampler-attempt receipt는 존재하지만 DiT device 이동 완료·첫 forward·scheduler step·clean conversion에 도달한 기록은 없다.
- decode0, 새 final latent0, 영상0. 자동 재시도·추가 encoder·BASE/CONTROL 재생성·학습·설치0.
- supervisor 관측 구간 41.427초. CPU staged loader 29.540초. 샘플링 완료 시간·decode 비용은 미실행이다.
- 관측 cgroup peak 62.036GiB, phase RSS 최대 61.698GiB. 시스템 MemAvailable 최소 62.125GiB. 서로 다른 회계이며 합산하지 않는다.
- 마지막 phase CUDA peak 기록 17,743,360bytes는 조건 복원까지의 값이다. 중단된 DiT 이동의 최종 CUDA peak를 뜻하지 않는다.
- 실제 guard trigger는 시스템 swap256KiB다. 해당 표본의 MemAvailable 63.872GiB는24GiB보다 컸다. 자기 cgroup의 pswpout0과 시스템 swap 발생을 구분하며 발생 프로세스는 UNKNOWN이다.
- systemd/launcher 반환0이지만 TERM 중단·normal_exit_recorded=false·NOT_CLEAN이다. 완료로 판정하지 않는다.

새 테스트·정책 설계는 없고 기존13/24검사는 반복하지 않았다. 전체 기록·전달 시간은 최종 전달 receipt와 구분한다.

# RECOVERY_01 실제 비용

새 sampler0·이미지0·encoder0·학습0·설치0·재시도0. WanVAE worker1, 저장된 BASE latent decode1회다. CONTROL/STEP과 source reconstruction0회.

| 관측 | 값 |
|---|---:|
| VAE load phase | 0.379s |
| 실제 decode phase | 6.645s |
| CPU raw/PNG 저장 구간 | 1.972s |
| MP4 인코딩+전체 decode/ffprobe 검증 | 0.430s |
| worker 계측 구간 | 13.450s |
| supervisor 시작~종료 | 14.962s |
| CUDA peak allocated | 8.908GiB |
| CUDA reserved 관측 peak | 11.562GiB |
| 시스템 MemAvailable 최소 관측 | 76.526GiB |
| cgroup peak | 1.769GiB |
| swap 사용 peak | 0B |

시스템·cgroup·CUDA 메모리는 서로 다른 회계이며 합산하지 않는다. 시작 MemAvailable 약90.00GiB,72GiB 기준을 통과했다. worker 단계 비용은 문서/검토/전송의 전체 벽시계와 다르다. 최종 전달 비용은 DELIVERY 기록을 따른다.

출력 decode PASS와 별개로 종료 guard는 UNKNOWN_GPU_PID / NOT_CLEAN이다. 유효 raw를 보존했고 재시도하지 않았다. [원시 수치 요약](MEASUREMENTS.json).

SOURCE/BASE 나란히 보기용 새 CPU 비교 MP4 인코딩은0.912초였다. 1792×512·17프레임·24fps, 각 원본 프레임을 resize/interpolation 없이 좌우로 배치한다. 기존 SOURCE/BASE MP4는 byte-copy로 보존하고 비교 영상만 새 파생물로 기록한다.

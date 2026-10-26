# B-028 실제 실행 상태

2026-10-26 01:47 UTC 착수. 원격 사전 고정 커밋 `119f79b3b813565dd5b907f01277b62c016e738c`.

| 과제 | ENC | R1 PROBE/S/D | R2 PROBE/S/D |
|---|---|---|---|
| animal | COMPLETED | PASS / COMPLETED / COMPLETED | PASS / COMPLETED / COMPLETED |
| human | COMPLETED | PASS / COMPLETED / COMPLETED | PASS / COMPLETED / COMPLETED |
| vehicle | COMPLETED | PASS / COMPLETED / COMPLETED | PASS / COMPLETED / COMPLETED |

03:31:53 UTC 전체 완료. sampler 실제 시도6/6, decode6/6, worker21/21 완료. 각40step80forward·final latent 저장·finite raw·17프레임 MP4를 확인했다. 재시도0. 소유 unit 두 개 inactive와 자원 회복을 확인했다. 더 이상의 B-028 GPU 실행은 하지 않는다. 실제 비용은 [COSTS.md](COSTS.md), 조건 계보는 [CONDITIONS.json](CONDITIONS.json)을 참조한다.

animal의 새 cache는 대응 B-027 cache 각각에 대해 허용6leaf만 변경, 나머지10leaf와 구조·dtype·초기noise 파일이 보존됐다. 새 VAE/CLIP reference 각2회, T5·driving·target·DiT 인코딩0. 기존 cache는 읽기 전용이다.

기존 watchdog의 종료 후 이미 사라진 소유 pipeline unit에 대한 `unit not loaded` 메시지는 실제 receipt의 `service_exit`, returncode0, MainPID0과 별도로 보존한다. 다른 서비스 종료나 guard 변경은 없다.

시각 검토는 별도 담당자가 전체17장으로 진행한다. 기술 실행 PASS를 품질 PASS로 쓰지 않는다. 원본 reference의 낮은 정보량과 GT 가림 누락은 확대 후에도 남으며 q정규화를 정보 복원으로 해석하지 않는다. 시간 품질은 UNVERIFIED다.

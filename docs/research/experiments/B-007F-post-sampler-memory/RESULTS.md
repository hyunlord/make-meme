# B-007F 결과 — 첫 forward 전 가드 종료, MP4·최종 latent 없음

**BLOCKED. 실제 MP4 확보라는 목표는 달성하지 못했다.** 전체 모델은 적재됐지만 공식 예제의 첫 DiT forward 이전 구간에서 시스템 가용 메모리 하한에 도달했다. 변경한 post-sampler CPU 이동 생략과 final latent 저장 경로에는 도달하지 않았다. 공식 실패 후 Lab와 자동 재시도는 실행하지 않았다.

## 실행·수용 상태

| 항목 | 결과 | 증거와 한계 |
|---|---|---|
| 전체 모델 적재 | PASS, 331.44초 | 실제 full_pipeline_load 완료 |
| 공식 sampler 시도 | 1/2, FAILED_RESOURCE_GUARD | 예약 후 generate에 진입; 실패도 사용량에 포함 |
| 첫 DiT forward | 완료/진입 관측 없음 | initial noise 저장 당시 forward counter0, 첫 forward phase 없음 |
| 완료 scheduler step | 완료 기록 없음 | sampler_progress.json 없음; 최종 counter 실측으로 대체하지 않음 |
| 최종 decode latent | NOT_CREATED | initial_noise.pt만 존재하며 final latent가 아님 |
| post-loop CPU 이동 생략 | NOT_REACHED | 효과를 입증하거나 반증한 실험 결과가 아님 |
| VAE decode / raw / MP4 | NOT_RUN / 없음 / 없음 | 공식 기술 출력 gate 미통과 |
| Lab | NOT_RUN | 별도 프로세스와 두 번째 sampler 미실행 |
| 개체·체형·안무·경계 품질 | NOT_RUN | 평가할 생성 영상 없음; 기존 입력 mask PARTIAL 유지 |
| 시간 품질 | UNVERIFIED | 연속 재생할 생성 결과 없음 |
| 다운로드·학습·LoRA·imagegen·외부 생성 API | 모두0 | 기존 자산·환경 재사용 |

B-007E의 기존 1/2 실패 이력은 보존했다. B-007F의 별도 한정 예산은1/2 사용이며 남은 슬롯을 임의 재시도에 쓰지 않았다. 서비스 returncode0은 SIGTERM 정리 결과이며 실험 성공이 아니다.

## 고정한 조건과 실제 변경

시작 원격 HEAD는 `fcd1fda723b3828d416fa4de7b14fa292f9e02a6`, 실행 전 공개 고정 commit은 `97189c029ac298b0aded73990d1858d5df9b93bf`다. [PLAN](PLAN.md), [코드/config 해시](PREREGISTERED_CODE.json), [입력·가중치 해시](PREREGISTERED_INPUTS.json), [실제 source diff](SOURCE_PATCH.diff).

변경한 메모리 정책은 지정된 post-loop `self.model.cpu()` 생략 하나다. 같은 위치의 `empty_cache()`, 앞선 T5/CLIP 이동, step별 prediction/latent CPU 계산, offload_model=True, mixed-BF16 loader는 유지했다. 추가 관측·원자적 저장 코드는 sampler 완료 뒤 실제 x0를 보존하도록 구현했지만 실제 run에서는 해당 지점에 도달하지 못했다.

가중치8개·의존성 증거168파일·원본 코드8파일·고정 config/input10항목·사전 입력8항목은 E와 해시가 일치했다. 전체 환경의 모든 파일을 검사한 것은 아니다. [재사용 감사](INPUT_REUSE_AUDIT.json). 공식 입력 전처리 및 초기 noise SHA `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`도 E와 일치했다.

## 실제 메모리·종료 범위

- 전체 guarded service:410.013초. 새 연구 시작15:50:53UTC, hard deadline18:50:53UTC를 넘기지 않았다.
- 가드 시작 MemAvailable93,910,204,416 bytes. 실제 cgroup cap68,140,400,640 bytes는 기존 `min(64GiB, available−24GiB)` 계산 결과다. 고정64GiB를 사용했다고 잘못 표기하지 않는다.
- 마지막/최소 MemAvailable25,676,087,296 bytes(23.912720GiB), 하한25,769,803,776 bytes(24GiB). 위반 표본을 무시하지 않고 이번 서비스만 종료했다.
- resource 표본404개, 관측 cgroup peak66,118,230,016 bytes. swap0; cgroup events high9396, max0, oom0, oom_kill0. high 이벤트는 reclaim/throttle 압박 신호이며 OOM 횟수가 아니다.
- 마지막 durable phase는 `pipeline_loaded`다. 그 뒤 scheduler 설정과 초기 noise 기록은 존재한다. **정확한 allocating operation은 UNOBSERVED**이며, 초기 noise 저장 이후 첫 model-forward hook 이전 구간으로 한정한다.
- 이 구간에는 argument 구성·기존 empty_cache·sample_func의 기존 `model.to(self.device)`가 있다. CPU→GPU 이동의 순간 중복이 후보이지만 그 지점에 별도 hook이 없어 원인으로 확정하지 않는다.
- 마지막 phase의 CUDA allocator 값은 중단 순간의 CUDA peak가 아니다. 시스템/RSS/cgroup/CUDA 숫자를 합산하지 않는다.

[실측](MEASUREMENTS.json), [실패 장부](FAILURE_LEDGER.json), [자원 CSV](resource_summary.csv). 실제 stop reason과 파일 부재를 함께 사용했으며 `Result=success`를 영상 성공으로 해석하지 않았다.

## 구현 검증과 실제 실행의 차이

CPU/mock transition4개와 기존 guard policy3개가 통과했다. 정확한 source anchor, 앞선 CPU 이동 보존, 선택한 post-loop 이동만 생략, cache 호출 유지, decode 실패 뒤 latent 값/readback 보존을 검사했다. 독립 검토와 Python syntax·critical Ruff 검사를 수행했다. 이는 full VAE decode나 실제 메모리 감소 검증이 아니다.

`final_latent.safetensors`와 sidecar는 이번에 만들어지지 않았다. 따라서 decode-only 재개 명령을 실행할 수 있는 상태가 아니다. ZIP의 initial_noise.pt를 final latent로 사용하면 안 된다. 저장 코드의 규약은 [재현 문서](REPRODUCE.md)와 [한국어 이론](../../lessons/B-007F-unified-memory-lifecycle.md)에 남겼다.

## 종료·보존

종료 후 가중치8/의존성 증거168/원본 코드8/고정 입력-config10 항목이 동일했고, B-007E의 model-load·sampler·process·run 기록4개도 보관된 Mac 사본과 Spark 실물이 바이트 일치했다. pipeline/watchdog은 모두 inactive/MainPID0이며 다른 작업은 유지했다. 입력 감사의 post-run 보존 항목에 근거를 남겼다.

## 해석과 다음 연구 하나

이번 실패는 **post-sampler 정책의 평가 불가**다. B-007E가 첫 forward 이후까지 도달했다는 과거 사실과, 이번 실행이 더 앞에서 자원 하한에 걸린 사실을 함께 보존한다. 초기 조건의 자원 snapshot·메모리 수명·페이지 charge·계측 timing을 완전히 같게 통제하지 않았으므로 원인을 단정하지 않는다.

다음 한 작업은 **기존 E/F trace와 고정 코드로 첫 forward 이전 device 이동·storage 수명·메모리 회계를 조사하는 CPU-only 감사**다. 새로운 sampler나 모델 로딩 없이 비교 근거를 먼저 좁힌다. 최종 latent가 없으므로 decode-only 실행은 제안하지 않는다. 추가 생성·학습·다른 모델은 자동 시작하지 않았다.

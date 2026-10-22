# B-007D — 실제 제한 로딩·tensor-only 변환 결과

상태: **CONVERSION_PASS / 모델 실행 NOT_RUN**. 실제 제한 로드 2회와 전체 tensor-only 변환·값 검증을 완료했다. 영상 baseline은 아직 없다.

## 범위와 실행 고정

원격 시작 HEAD `ee7ef695cd6f438779166dce71fdbea1507cc129`, 실제 실행 코드 사전 등록 `5e134fa3c8668bd9abe8b00067c01d84cd2580b3`. [계획](PLAN.md), [실행 config/hash](PREREGISTERED_CONFIG.json), [재현](REPRODUCE.md), [코드 감사](CODE_AUDIT.md).

고정 원본 65,582,563,395 bytes, SHA256 `d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f`. Torch `2.14.0+cu130`, NumPy `2.5.2`, SCAIL commit `78fe19576bb06be96c2375e088574a262a300edb`. 실제 로드는 metadata 1회 + 조건부 변환 1회만 허용했다. 모델 인스턴스 적재·diffusion·학습·새 checkpoint 다운로드는 0회다.

## 격리와 실패 보존

unshare/bwrap는 권한 제한 EPERM으로 실패했고 OS 보호 설정을 변경하지 않았다. 기존 로컬 container image를 재사용해 nonroot UID, capability0, no-new-privileges, network=none, read-only root/입력, output 전용 쓰기를 구성했다. 실제 환경 secret canary 부재, 외부/host-loopback 연결 실패, host file/socket 비노출, input 쓰기 실패를 확인했다. CUDA device는 노출하지 않았다. 이는 관측한 probe 범위의 격리 증거이며 safe_globals 자체의 완전한 보안 보장이 아니다.

정확한 ambient73/83 이름·심볼 identity와 추가 NumPy4종 scope를 고정했다. 실제 실행 전에 systemd RuntimeMax 종료 및 ExecStopPost가 자기 container를 종료하는 sentinel도 확인했다. 예상 밖 global을 추가하지 않았고 unsafe 역직렬화는 사용하지 않았다.

## 실제 metadata

- 원본 module tensor 987개: dtype·shape·stride·storage offset·ZIP payload offset이 정적 계약과 일치.
- 공식 mapping 후 F32 tensor 1,307개, 논리 payload 65,582,177,536 bytes. QKV/KV 순서·view 범위·키 중복/누락 검사 PASS.
- 전체 stage 45.209초. full SHA scan 44.371초와 restricted FakeTensor load 0.167초를 분리했다.
- 제한 로드 구간 rchar 4,330,136 bytes, read_bytes 2,928,640 bytes. 전체 프로세스는 SHA 계산을 위해65GB를 읽었으므로 전체 작업이 payload를 읽지 않았다고 말하지 않는다.
- load 종료 시 max RSS 573,196KiB. cgroup peak 8GiB는 제한에 닿은 값이며 대부분 file cache다. 높은 current 표본에서 file 8,281,137,152 bytes, anon 305,696,768 bytes. 해당 표본 max event 941, 전체 표본 최대1,092, OOM 0. 자연적 무제한 peak는 측정하지 않았다.
- globals scope 복원, exit 0, container PID 0. 이 단계만으로 값 정확성은 검증되지 않는다.

[기계 판독 실측](METADATA_MEASUREMENTS.json), [한국어 이론](../../lessons/B-007D-real-checkpoint-loading.md).

## 실제 변환

두 번째 CPU mmap 로드 후 공식 mapping을 적용해 단일 safetensors를 순차 저장했다. 원본을 다시 로드하지 않고 같은 살아 있는 mmap view와 출력 파일의 tensor별 bytes를 비교했다. Rust safetensors parser의 키·dtype·shape 검사와 전체 1,307개 값 hash가 모두 통과했다. 원본 SHA 재검증 후에만 미검증 이름을 최종 파일로 발행했다.

| 항목 | 실제 관측 |
|---|---:|
| 전체 guard 시간(최종 출력 SHA 포함) | 456.759초 |
| 내부 receipt 시간(최종 출력 SHA 이전) | 369.068초 |
| 사전 전체 원본 SHA 계산 | 62.763초 |
| materialized CPU mmap 제한 로드 | 0.090초 |
| 출력 파일 크기 | 65,582,313,560 bytes |
| 검증된 mapped tensor | 1,307 / 1,307 |
| cgroup charged memory peak | 32GiB, 설정 cap에 도달 |
| 표본 VmHWM / 최대 RSS | 55,564,172KiB, 약53GiB |
| 최소 시스템 MemAvailable | 89,057,169,408 bytes, 약82.94GiB |
| cgroup max / oom / oom_kill events | 31,772 / 0 / 0 |
| 실제 checkpoint load 총수 | 2 / 2, 재시도0 |

출력 SHA256: `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`.

RSS가 cgroup charge보다 컸다. 파일 mmap의 resident/shared page와 cgroup 귀속은 다른 회계이며, 개별 공유 페이지의 과거 소유 cgroup은 측정하지 않았다. 따라서 32GiB를 프로세스 RSS 상한 또는 전체 시스템 소비 상한이라고 주장하지 않는다. source/file cache의 실제 계측을 포함한 이 실행에서만 OOM0·swap 증가0·headroom 유지가 확인됐다. 무제한 환경의 자연 peak나 다른 실행의 안전을 보장하지 않는다.

저장과 값 검증 각각의 시간은 NOT_MEASURED다. [변환 상세 측정](CONVERSION_MEASUREMENTS.json), [단계 요약](MEASUREMENTS.json). 양쪽 container exit0·PID0, supervisor inactive를 확인했다. 남은 자기 작업 프로세스는 없다.

## 산출물과 다음 하나

대형 safetensors는 Spark의 비공개 B-007D output에만 보존한다. 공개 저장소와 검토 ZIP에는 넣지 않았다. 비공개 ZIP에는 코드·설정·제한 로드 장부·전체 tensor hash receipt·실측·보고서를 포함하고 파일별 SHA와 ZIP CRC를 검증한다. 구체적인 Spark/Mac 경로와 ZIP digest는 비공개 delivery 기록과 최종 응답에서 제공한다.

다음 한 작업은 **별도 승인된 SCAIL 모델 적재와 공식/Lab 단일17프레임 제한 baseline**이다. 변환본 사용 시 실제 모델 적재 peak를 먼저 측정하고, 통과할 때만 RGB driving을 실행한다. 이번에는 이를 시작하지 않았다. 신규 모델 다운로드·전체 모델 적재·diffusion·LoRA·학습은 모두 0회다.

## 검사 수준과 남은 한계

실제 실행 전 소형 회귀 12개가 통과했다. 이후 읽기 전용 정적 검사에서는 Ruff 지적 18개(주로 import 정렬과 명시적 subprocess 옵션), 경로를 맞춘 Mac 기반 type 검사 오류 18개(미설치 safetensors 1개, 타입 표현 부족 17개)가 남았다. 실행 코드의 실제 해시를 보존하기 위해 실행 중 코드는 변경하지 않았다. 따라서 lint/type-clean 또는 제품용 범용 변환기 완성으로 보고하지 않는다. 실제 checkpoint 값 검증과 정적 코드 품질은 별개의 증거다.

원래 모델의 parameter 전체를 인스턴스화하지 않았다. 65.58GB payload는 checkpoint module storage의 논리 bytes이며 모델 실행 시 activation/attention peak가 아니다. 다음 단계의 GPU model loading 안전성과 영상 품질은 이번 CPU 변환에서 입증할 수 없다. 기존 A, VACE, ComfyUI와 원본 checkpoint를 변경하지 않는다.

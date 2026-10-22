# B-007E 결과 — 전체 적재·첫 forward PASS, 영상 출력 BLOCKED

**실제 모델 로딩과 첫 RGB-driving DiT forward는 통과했지만, 영상 baseline은 확보하지 못했다.** 공식 예제 sampling 로그는40/40까지 완료됐고, 그 뒤 offload/decode 경계에서 시스템 가용 메모리 하한에 도달해 자기 프로세스를 종료했다. MP4·decoded raw output·최종 denoised latent는 없다. Lab는 실행하지 않았다.

## 실행과 판정

| 항목 | 실제 결과 | 근거/한계 |
|---|---|---|
| 전체 pipeline 적재 | PASS,268.587초 | T5/VAE/CLIP와 실제 DiT, loading1회 |
| DiT state 검사 | PASS |1,307 tensor, strict/assign missing·unexpected 모두0 |
| 실제 첫 DiT forward | PASS |22.856초, finite 출력; 실제12,992 token |
| 공식 sampler |1/2회 사용, FAILED_SYSTEM_HEADROOM_GUARD |40/40 progress log 후 generate 반환 전 종료 |
| 전체 영상·raw decode | BLOCKED | MP4와 raw_output.pt 없음 |
| Lab sampler | NOT_RUN,0회 | 공식 실패 뒤 자동 진행하지 않음 |
| Lab 얼굴·귀·털·체형/직립·타이밍/누수 | NOT_RUN | 평가할 생성 영상 없음 |
| 생성 경계·접촉·반사·가림 품질 | NOT_RUN | 기존 입력 mask 결함은 PARTIAL_UNRESOLVED 유지 |
| 시간 품질 | UNVERIFIED | 생성 영상과 연속 재생 관찰 없음 |
| 모델 다운로드/학습/LoRA |0/0/0 | 기존 가중치와 격리 환경 재사용 |

실행 시작 기준 원격 HEAD `260ab8cbe140c27d46575a63ddc83779239c05aa`. 실제 loader·guard·config·입력 SHA는 실행 전 `a9923357f38d106fec733ce0765fe93bf916f05b`에 고정했다. isolated upstream patch는 해당 코드로 생성했고 실제 source hash는 launch 전 private 기록 및 후속 공개 `008153f`에 남겼다. 첫 적재/forward 기록은 `69c0352`다. 기존 A와 B 기록을 덮어쓰지 않았다.

연구 시작13:49UTC, 전체 모델 실행14:06:15UTC, guard 종료14:30:22UTC. 모델 서비스 전체 wall-clock1,449.654초. 사전5시간 상한보다 일찍 중단했다. 실제 loading 경로1개/상한2, sampler1개/상한2이며 남은 슬롯으로 자동 재시도하지 않았다.

## 실제 메모리와 중단 위치

- DiT parameter16,395,544,384개, mixed payload33,166,820,096bytes(30.889GiB). BF16 tensor974개, FP32 tensor333개.14B라는 이름을 전체 pipeline parameter 수로 쓰지 않는다.
- FP32 원본65,582,313,560bytes/SHA `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`를 보존하고, meta initialization→tensor별cast→`load_state_dict(strict=True, assign=True)`로 적재했다. BF16 반올림은 원본 FP32의 byte parity와 다르다.
- cgroup 최고67,427,590,144bytes(62.797GiB), process VmHWM62.153GiB. 이는 서로 다른 회계이며 더하지 않는다. 실행 중 cgroup current 약16GB와 CUDA allocation 약34GB가 동시에 관측돼, cgroup만으로 전체 통합 메모리를 제한했다고 주장하지 않는다.
- 첫 forward 시점 CUDA allocator peak36,798,287,872bytes(34.271GiB). **전체 sampler/후속 decode의 CUDA peak는 NOT_MEASURED**다.
- 마지막 MemAvailable25,661,333,504bytes(23.898979GiB)가24GiB(25,769,803,776bytes) 하한을 밑돌았다. swap0, cgroup OOM/kill0. 사전 가드가 SIGTERM으로 이번 서비스만 종료했다.
- 시스템의 `returncode=0`, `Result=success`는 정상적인 서비스 종료 처리다. 실험 성공이 아니며 guard reason과 출력 부재를 우선해 FAILED로 판정한다.

정확한 세부 종료 위치는 **UNOBSERVED**다. pinned `scail.py`는40step 뒤 `model.cpu()`→`empty_cache()`→`vae.decode()`를 수행하지만 그 사이 관측점이 없다. RssAnon 증가(약13GB→33,101,068KiB)는 GPU→CPU 복사와 GPU cache의 순간 공존 가설에 부합한다. VAE decode에 진입했다고 단정하거나 FlashAttention/OOM 실패라고 바꾸어 쓰지 않는다. [원인 분석](POSTMORTEM.md).

## 내부 텐서·호출 관측

공식 예제 H512×W896: generated latent `[16,5,64,112]`, reference `[16,1,64,112]`, RGB driving `[16,5,32,56]`, reference mask `[28,6,64,112]`, driving mask `[28,5,32,56]`. text context `[5,4096]` BF16, CLIP `[1,257,1280]` FP16. attention wrapper Q/K `[1,12992,40,128]` FP32, V BF16이며 실제 kernel 전 cast는 고정 attention 구현을 따른다.

40/40 완료는 tqdm 로그 근거다. `run.json`은 첫 forward 뒤에만 저장되어 persisted counter가1이다.40steps×CFG2로80forward를 예상할 수 있지만 **80회를 최종 hook counter로 실측했다고 쓰지 않는다**. 최종 latent를 저장하기 전에 종료돼 initial_noise.pt로 decode만 즉시 재개할 수도 없다.

## 입력·코드·검증 범위

공식 BLUE/reference-driving 대응, Lab RED 대응을 확인하고 RGB/mask에 동일 crop을 적용했다. Lab17f24fps와 공식17f16fps를 별개로 고정했다. Lab의 계획된24fps writer는 원본 시간축 보존이며 모델16fps motion prior의 일반화 성공을 뜻하지 않는다. [입력 감사](INPUT_AUDIT.md), [고정 입력 해시](PREREGISTERED_INPUTS.json), [코드 해시](PREREGISTERED_CODE.json), [upstream 해시](SOURCE_HASHES.json).

작은 실제 architecture fixture7개, resource 정책 fixture3개, 실제 timeout cleanup sentinel은 통과했다. 초기 CPU import는 upstream T5의 import-time CUDA default 때문에 실패했고 test-only namespace/stub로 분리한 검증 기록을 보존했다. 실제 실행 소스의 CUDA 동작을 끄지 않았다. 소형 검증을 전체 영상 성공으로 대체하지 않는다.

[실측 JSON](MEASUREMENTS.json), [자원 CSV](resource_summary.csv), [적재 결과](LOAD_RESULT.json), [재현](REPRODUCE.md), [한국어 수학·코드 설명](../../lessons/B-007E-full-model-forward.md). 출력 비교 스크립트는 준비됐으나 출력이 없어 NOT_RUN이다. 입력 비교 sheet는 생성 결과가 아니다.

## 보존·종료 확인

실행 후 가중치/토크나이저8개, 의존성168파일, 원본source8파일을 다시 hash해 모두 동일했다. 두 실험 unit은 inactive/MainPID0이며 기존 ComfyUI만 유지되고 queue는 비어 있다. 종료 후 MemAvailable93,825,449,984bytes,swap0을 확인했다. [보존 결과](PRESERVATION.json).

## 다음 연구 작업 하나

별도 승인된 **post-sampler 메모리 전이 실험**을 제안한다. 최종 denoised latent 저장·명시적 phase hook을 고정하고, post-loop CPU offload만 생략해 DiT를 GPU에 유지한 채 decode하는 한 경로를 같은 headroom guard 아래 비교한다. CPU 복사/GPU cache 공존을 피한다는 가설이며 fit이나 품질 개선은 보장하지 않는다. 새 sampler 예산이 필요하고 이번에는 실행하지 않았다. 다른 모델·학습·대량 추론으로 확장하지 않는다.

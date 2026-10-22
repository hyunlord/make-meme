# B-007B — 실제 체크포인트 직렬화 검사에서 BLOCKED

2026-10-22. **SCAIL-2 영상 baseline은 확보하지 못했다.** 필수 파일의 다운로드·해시는 검증했지만, 실제 SAT checkpoint의 NumPy pickle globals를 사전 고정한 안전 로더가 거부했다. 전체 변환·모델 로딩·forward·영상 생성은 **NOT_RUN**, diffusion 시도 **0/2**, 학습·LoRA 업데이트 **0**이다. B-007A 커널 PASS를 모델 실행 PASS로 확대하지 않는다.

## 실제 진행과 중단 위치

| 단계 | 결과 | 관측한 근거 |
|---|---|---|
| Gate0 입력·환경 | PASS / 마스크 PARTIAL | 이전148artifact 검증, 입력80파일 Mac/Spark 동일. RGB/mask 같은 crop, 기존 얇은 경계 결함 유지 |
| Gate1 소형 변환 | PASS, 범위 제한 | Spark CPU 합성 fixture8개1.21초. 공식 mapping·dtype·값·독립 손상 거부 비교. 실제 모델 품질 증거 아님 |
| Gate2 선택 다운로드 | PASS | 신규68,111,049,006bytes, SAT/CLIP 공식 SHA 일치. VAE/T5/토크나이저6파일은 해시 확인 후 재사용 |
| Gate3 실제 metadata | BLOCKED | `checkpoint_tensors()`의 `get_unsafe_globals_in_checkpoint()` 결과를 보고 거부. `torch.load`·FakeTensor 실행보다 앞선 차단 |
| Gate3 대형 변환/검증/모델 | NOT_RUN | 변환 safetensors 없음, 전체 모델 key/shape 계약·memory peak·CUDA forward 미검증 |
| Gate4 영상 품질 | NOT_RUN | 생성 영상 없음. identity·안무·누수·접촉·형상·시간 품질 판정 불가 |

실제 오류:

```text
ConversionError: Checkpoint requires unsupported globals:
['numpy.core.multiarray._reconstruct', 'numpy.ndarray', 'numpy.dtype']
```

[검사 코드](code/converter_mapping.py)의 명시적 fail-closed 정책이다. 이 오류는 체크포인트가 악성이라는 판정, mmap 자체의 비호환 입증, GPU OOM 또는 FlashAttention 실패가 아니다. `weights_only=False`, 추가 globals allowlist, 새 pickle parser로 우회하지 않았다.

이어 수행한 읽기 전용 ZIP/pickle opcode 검토는 `data.pkl` 163,821bytes·31,271opcodes를 확인했다. `np_rng_state`(offset3975), `MT19937`(3995) 뒤에 `_reconstruct`(4009), `ndarray`(4047), `dtype`(4129), `u4`·길이624 문맥이 있다. NumPy RNG 상태 메타데이터에서 발생했다는 강한 근거지만, 역직렬화한 객체의 소유관계를 증명한 것은 아니다. NumPy 객체를 복원하거나 값을 실행하지 않았다.

## 고정했으나 실행하지 못한 두 baseline

| 조건 | 해상도 W×H | 시간축 | seed / sampling | 결과 |
|---|---|---|---|---|
| 공식 animation_001 | 896×512 |17장16fps,1.0625초 |20261022 /40steps,UniPC,shift3,CFG5 | NOT_RUN |
| 실제 Lab + RGB driving |512×896 |17장24fps,0.708333초 |동일,adapter=null | NOT_RUN |

공식 예제의 참조는 실제1920×1080 가로 이미지이며 Lab는 세로 crop이다. Lab 원본의 좌우 장면 전체를 보존했다고 주장하지 않는다. reference/driving 색상 대응과 마스크는 B-007A 자산을 재사용했으며 새 반려동물 또는 A 생성 자산을 추가하지 않았다. Lab 마스크의 초기 바닥 반사·얇은 경계는 **PARTIAL_UNRESOLVED**다.

실제 생성 결과의 Lab 얼굴·털·체형, 뒷발 직립과 머리/앞발 동작, source 외형 누수, 발 접촉·반사, 시간 안정성은 전부 **NOT_RUN**이다. 연속 재생 관찰도 없으며 시간 품질 검증은 **UNVERIFIED**다. 비공개 ZIP의 writer 영상은 원본 RGB를 저장한 CPU 계약 검사이지 모델 생성물이 아니다.

## 자원과 구현 증거의 한계

- 다운로드 단계1,670.862초, SAT 전송1,505.427초, CLIP63.382초. metadata 단계1.026초에 종료했다. 작업은6시간 상한 안에서 조기 종료하며 가중치·추론 재시도를 이어가지 않는다.
- 다운로드 중 관측된 최소 시스템 MemAvailable75,377,397,760bytes, 최대 swap0. 이 값은 다른 작업을 포함한 시스템 상태이며 모델 전용 메모리가 아니다.
- 종료 시 MemAvailable95,945,383,936bytes, 디스크1,181,553,397,760bytes 여유. 실제 대형 변환·모델 peak는 **NOT_MEASURED**다. metadata의 짧은 cgroup 표본503,808bytes와 종료값331,776bytes는 총 Torch RSS/모델 peak로 사용할 수 없어 원시 증거에만 보존했다.
- 새 작은 의존성 wheel26,031,848bytes. 별도 환경만 사용했다. 기존 환경138개 파일과 B-007A FA binary, 알려진 A111파일의 전후 해시 일치. 전체 filesystem 감사를 했다는 뜻은 아니다.
- 소유한 실행 프로세스는 모두 종료했다. 실패한 service 기록은 보존했고 기존 ComfyUI를 종료하지 않았다.
- mixed-BF16 meta 로더의 작은 fixture와 FP32 normalization/time/head 경로는 검사했으나, 전체 모델 수치 동등성·메모리 적합성은 미검증이다. 실제 dtype/parameter 수와 token shape를 실행 실측값처럼 보고하지 않는다.

[측정 요약](METRICS_SUMMARY.json), [입력 해시](INPUT_HASHES.json), [코드/config snapshot](EXECUTION_SNAPSHOT.json), [Gate1](GATE1_SUMMARY.json), [CPU writer](WRITER_INTEGRATION.json), [실행 기록](RUNNING.md), [재현](REPRODUCE.md), [한국어 이론](../../lessons/B-007B-conversion-and-model-forward.md).

## 다음 한 경로

**동일 공식 checkpoint의 비텐서 RNG 메타데이터를 안전하게 분리할 수 있는지 검증하는 직렬화 감사**를 다음 단계로 제안한다. 객체 실행 없이 실제 tensor 경계·storage 관계·공식 mapping 보존을 증명하거나, 공식 출처의 tensor-only export와 동등성을 확인해야 한다. 이번에는 그 추출기·allowlist를 새로 구현하지 않았다. 새로운 영상 모델·학습·추론을 시작하지 않으며, 이 선행 문제가 해결돼도 실제 baseline과 품질 수용은 별도 실행으로 남는다.

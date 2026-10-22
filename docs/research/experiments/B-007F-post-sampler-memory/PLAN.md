# B-007F — 최종 latent 보존과 post-sampler 메모리 전이 실험

작성: 2026-10-23 · parent: B-007E · 상태: **PLANNED / NOT_RUN**
이 문서는 검토·방향 결정·실행 의뢰서다. 문서 등록 자체로 GPU 작업이 실행되거나 예산이 소비된 것은 아니다. 사용자가 이 계획의 실행을 지시할 때 아래 한정 예산을 적용한다.

## 0. 현재 상태와 이번 검토의 근거

B-007E 기준 커밋은 `aae93748cb1eebc89d68670673c301d739ebe149`다. 원격 RESULTS, POSTMORTEM, code/runtime_infer.py, code/runtime_guard.py와 공식 SCAIL `wan/scail.py`의 sample_func를 직접 읽었다. 공식 SCAIL 고정 commit은 `78fe19576bb06be96c2375e088574a262a300edb`다.

보고된 실제 전체 pipeline 적재268.587초, 첫 DiT forward22.856초/finite, strict key1,307개 검증은 유효한 실행 증거다. 공식 예제40/40 progress log 후 MemAvailable23.898979GiB가24GiB guard 하한을 밑돌아 자기 프로세스를 종료했다. swap0/cgroup OOM0. CUDA OOM이나 FlashAttention 실패로 재분류하지 않는다. 정확한 offload/decode subphase는 UNOBSERVED다. 최종 latent·decoded output·MP4는 없다. initial_noise.pt만으로 decode를 재개할 수 없다. Lab는 NOT_RUN이다.

원격 runtime_infer.py는 최종 영상이 pipeline.generate에서 반환된 다음에 raw_output.pt를 저장한다. 따라서 decode 앞에서 종료되면 샘플링 결과가 남지 않는다. 최종 forward counter도 첫 forward 뒤에만 저장돼 로그40/40을 최종80회 hook 실측으로 부를 수 없다.

이번 검토 환경에서 업로드 ZIP의 파일 검색은 파싱 결과를 반환하지 않았고, 정확한 업로드 경로를 읽은 container/Python 호출은 ClientError로 끝났다. 따라서 업로드 ZIP의86파일/CRC/SHA, Mac/Spark 일치는 이번 검토자가 독립 검증한 것으로 기록하지 않는다. 위 판단은 원격 코드·보고서 대조이며 Spark 재실행이 아니다.

## 1. 목표·가설·로드맵

목표는 모델/체크포인트 감사를 다시 반복하는 것이 아니라 **실제 MP4 확보**, 또는 실패하더라도 **재사용 가능한 최종 sampler latent와 정확한 종료 단계 확보**다.

가설: sampler 직후 DiT를 CPU로 복사하는 순간, 새 CPU weight와 GPU의 기존 allocation/cache가 같은 Spark 통합메모리에 공존하여 pressure를 높일 수 있다. post-loop DiT CPU 이동만 생략하면 이 전이를 피할 가능성이 있다. 실제 원인은 아직 미확정이며, DiT를 GPU에 유지해도 VAE activation과 함께 메모리가 부족할 수 있다.

방향: B-007E(전체 계산 진입) → B-007F(최종 latent 보존·offload 변경·decode 확인) → MP4가 있으면 실제 개체/동작 연구, 없으면 저장된 latent의 decode만 별도 분석. 같은 샘플링을 저장 없이 반복하지 않는다. A는 계속 동결, imagegen과 로컬 B를 섞지 않는다.

## 2. 실행 범위·예산

- 기존 가중치·SCAIL 소스·FlashAttention·mixed-BF16 staged loader·T5 CPU 경로·입력/mask를 재사용한다. 새로운 모델/weights 다운로드0, 학습·LoRA0, native imagegen/외부 생성 API0.
- 작업 상한3시간, heavy GPU 작업1개. OS/드라이버/swap/클럭 변경, 타 작업 종료, 가드 완화 금지.
- **신규 full sampler 시도 최대2회, 각 경우 최대1회, 실패 포함:** (1) B-007E와 같은 공식 예제 재실행1회. (2) 공식 예제가 raw decode 및 MP4 저장까지 완료되고 자원 회복이 확인된 경우에만, B-007E에서 미실행한 Lab 구간1회. 이는 사용자 전달 지시의 한정 승인 제안이며 이전 예산을 조용히 초기화하는 것이 아니다.
- 기존 B-007E의1/2 사용·실패 기록을 보존하고 새 시도 ID·parent 연결로 합산 가능한 장부를 유지한다. 단계 실패 후 seed/해상도/정밀도/샘플링 설정을 바꾼 자동 재시도는 없다.
- 공식 run이 decode까지 실패하면 Lab는 NOT_RUN으로 멈춘다. 이번 범위에는 tiling, VAE-only 별도 프로세스, 해상도 축소, DiT 파괴/재적재, 캐시 정책 변경을 묶어 넣지 않는다. 다음 실험은 실제 저장된 final latent가 있으면 sampler 없이 decode를 검토할 수 있다.

## 3. 단 하나의 메모리 정책 변경

공식 sample_func는 sampler loop 이후 다음 순서다.

```python
if offload_model:
    self.model.cpu()
    torch.cuda.empty_cache()
if self.rank == 0:
    videos = self.vae.decode(x0)
```

이번 변경은 **이 위치의 self.model.cpu()만 선택적으로 생략**하는 것이다. `torch.cuda.empty_cache()`의 이 위치 호출은 유지한다. 그 전까지의 offload_model=True, text/CLIP 이동, step마다 noise_pred·latent를 CPU로 보내는 경로, solver 계산 위치는 그대로 둔다.

`offload_model=False`로 전역 설정을 바꾸면 sampler 계산 위치와 여러 offload가 동시에 바뀌므로 이번 실험이 아니다. 모든 Module.cpu를 monkey-patch하거나 다른 이동까지 제거하지 마라. isolated source copy에 명확한 post_sampler_offload 옵션 또는 좁은 패치를 적용하고 exact diff/hash를 기록한다. 기본 동작과 기존 B-007E source는 보존한다.

작은 CPU/mock 테스트로 (a) sampler 설정과 앞선 CPU 이동 보존 (b) 선택한 post-loop 이동만 생략 (c) final latent 저장이 decode 전에 발생 (d) decode 실패 시 저장물 보존을 확인한다. 이 테스트를 실제 메모리 감소 증거로 보고하지 않는다. 모델 가중치·구조·precision·VAE decoder 구현은 그대로다.

## 4. 샘플링 결과를 먼저 보존

마지막 scheduler.step과 clean-history 적용이 끝난 뒤, **post-loop CPU 이동 및 VAE.decode보다 앞서** 실제 decode 인자 x0의 generated latent를 보존한다. initial_noise, noise_pred, reference latent 또는 중간 step을 final로 잘못 저장하지 않는다.

1. sampler 종료 이벤트를 기록하고 필요한 CUDA 동기화를 완료한다. 여기서 발생한 오류도 별도 단계로 남긴다.
2. 완료된 scheduler step 수·실제 model forward count·마지막 timestep/sigma·latent shape/dtype/device를 기록하고 finite 여부를 확인한다. progress bar만으로 완료 선언하지 않는다.
3. 기존 tensor 값을 변경하지 않고 detach 및 bounded CPU copy로 저장한다. 작은 latent와 큰 모델 parameter를 함께 CPU로 보내지 않는다. 표준 safetensors 또는 제한적 읽기가 가능한 자체 tensor 파일과 JSON sidecar를 사용한다.
4. 임시 파일→flush/fsync→원자적 rename, SHA256·shape·dtype 및 값 보존을 검증한다. GPU 객체를 전역 hook/list에 저장하지 않는다. raw latent 자체는 비공개이다.
5. sidecar에는 model/config/input/noise hashes, VAE weight·코드·scale/mean/std 규약, target H/W/frame count, fps, mask/crop, history/segment index, reference 포함 여부를 기록한다. later decoder가 VAE scaling을 두 번 적용하거나 제거하지 않도록 한다.
6. 저장/검증이 실패하면 완료라고 하지 말고 decode를 무리하게 이어가지 않는다. 가드는 계속 활성화한다.

보고된 generated latent shape `(16,5,64,112)`의 원소 수는573,440개다. 단순 payload 계산은 BF16 1,146,880 bytes/FP32 2,293,760 bytes다. 이는 저장할 latent가 약1~2MiB라는 설계 근거이지 새 실제 측정값이 아니다. 실제 dtype·shape와 파일 overhead는 runtime에서 기록한다.

## 5. 정확한 단계 관측과 같은 가드

기존 B-007E runtime_guard의 시작 조건(72GiB MemAvailable, swap0, 타 작업 queue 비점유), 실행 중24GiB MemAvailable 하한·swap·타 작업 감시·cgroup 정책을 유지한다. 새 실행 deadline/unit/output만 적법하게 갱신한다. 이전 만료 deadline을 그대로 쓰거나, 하한을23GiB로 내리거나, 위반 표본을 무시하는 유예를 추가하지 않는다. systemd returncode0만으로 실험 성공을 판정하지 않는다.

다음 phase를 파일에 즉시 flush하는 작은 관측 코드를 둔다.

- full_pipeline_load start/end
- first_forward start/end
- 매 step의 completed count 및 최종 실제 model-call count(작은 JSON; 대형 tensor 보관 금지)
- sampler_loop_exit / CUDA completion
- final_latent_save start/end
- post_sampler_offload SKIPPED
- empty_cache start/end
- vae_decode start/end
- decoded_raw_save start/end
- video_encode start/end

각 경계의 wall/monotonic time, MemAvailable, swap, VmRSS/RssAnon/VmHWM, cgroup current/peak/events/anon/file, torch CUDA allocated/reserved/peak를 기록한다. CUDA 동기화 필요 여부와 관측 비용을 명시한다. cgroup·RSS·CUDA 수치를 서로 더하지 말고, cgroup이 GB10 전체 CUDA 사용을 제한한다고 주장하지 않는다. phase hooks 자체가 timing을 바꿀 수 있어 과거 B-007E와 완벽한 통제 성능 비교라고 부르지 않는다.

기존 과거 결과는 종료 subphase와 final latent가 없으므로 byte-identical generation 비교가 불가능하다. 같은 초기 noise/input/config hash와 sampler 정책을 대조해 의도하지 않은 변경을 배제하되 결과 동일성을 추정하지 않는다.

## 6. 공식 예제 → 조건부 Lab

공식 예제는 B-007E의 같은 reference/driver/mask/prompt, 512×896(H×W),17f,16fps,seed20261022,40steps,UniPC,shift3,CFG5,adapter=null이다. 고정 config가 실제로 이 값인지 실행 전 읽는다. 소스에 추가한 관측·post-loop 이동 외에는 변경하지 않는다.

공식 run의 raw decode finite/shape/frame count와 MP4 실제 decode/ffprobe가 통과하고 guard reason이 정상 완료여야 Lab 진행 조건을 충족한다. 공식 예제의 시각 품질 문제도 숨기지 않으며 기술적 완료와 분리한다. 공식 run 종료·메모리 회복 후 새로운 프로세스에서 같은 loader로 Lab1회를 수행해 이전 hook/cache의 run 간 잔류를 피한다. 이는 한 가지 메모리 정책을 두 사례에 적용하는 것이며 추가 방법 탐색이 아니다.

Lab는 기존H896×W512,17f24fps,RED 대응 mask,동일한 실제 사진·RGB driving·프롬프트·seed·sampler를 사용한다. 마스크 경계 PARTIAL을 숨기지 않는다. 모델16fps prior와 output24fps의 차이는 한계다. fps override만으로 동작 충실도를 입증하지 않는다.

이 작업에서는 긴 영상·두 개체·윙크·킥·학습으로 확대하지 않는다. Lab raw가 나오면 정체성/체형·동작·형태·배경/마스크·시간 품질을 따로 보고한다. 실제 연속 재생을 관찰하지 못하면 UNVERIFIED이며, generated frames를 단순 인코딩한 사실과 자연스러움을 구분한다.

## 7. 성공·실패 판정

- final latent 없음: 마지막 durable phase와 guard/exception을 보고, 샘플링 완료를 주장하지 않는다.
- FINAL_LATENT_SAVED + DECODE_BLOCKED: 중요한 중간 산출물 확보. MP4 성공 아님. Lab 실행 금지. 다음 단계에서 이 latent를 재사용하는 decode 실험만 제안한다.
- DECODE_PASS + ENCODE_BLOCKED: decoded raw가 유효하면 보존. sampling 재시도로 해결하지 않는다.
- VIDEO_OUTPUT_PASS: 실제 raw finite/17frames/예상 fps/MP4 decode와 종료 상태를 확인. 이것만으로 Lab 정체성·춤이나 Kling 품질 PASS를 선언하지 않는다.
- 새 run이 성공해도 과거 실패 원인이 CPU offload였다고 완전 증명된 것은 아니다. phase 관측, RssAnon/allocator 변화와 함께 가설의 지지 정도를 기록한다.

## 8. 이론과 연구 기록

한국어 `lessons/B-007F-unified-memory-lifecycle.md`: CPU offload·실제 release·CUDA allocator cache 차이, Spark 통합메모리와 GPU/CPU tensor copy의 일시적 공존, DiT/sample/VAE/encoder의 수명, 최종 latent와 pixel frame의 차이, observed peak와 이론적 크기, CUDA 비동기 실행과 phase 동기화. 수식/shape→고정 코드→실제 메모리 trace→한계→질문3개와 별도 답안을 남긴다. 이번은 모델 학습법이나 새 논문 방법의 제안이 아니라 실행 수명 관리 실험이다.

실행자는 시작 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL 및 이 PLAN을 읽고, **HISTORY와 ROADMAP에 B-007E 결과 검토·B-007F 착수 링크를 추가한 뒤 실행 코드/config를 commit/push**한다. 이 PLAN 등록 단계에서는 공통 문서 전체를 덮어쓰지 않았다. 실험 종료 후 RESULTS·이론·재현·HISTORY·ROADMAP을 갱신하고 원격 SHA를 확인한다. main/기존 실험 결과/A는 변경하지 않는다.

사용자 사진·원본/생성 영상·mask·latent·가중치·개인 경로·secret/raw log는 공개하지 않는다. MD·비민감 코드/config·집계/해시만 push한다. 비공개 검토 ZIP은 Mac/Spark 위치와 실제 전송 여부를 구분하고 CRC/manifest/SHA를 검증한다. 모델weights는 제외; 최종 latent가 있으면 크기·SHA·재사용 규약과 함께 비공개 보존한다. 모든 자체 작업 프로세스 종료 여부를 최종 보고한다.

## 근거

- B-007E RESULTS/POSTMORTEM 및 code/runtime_infer.py, code/runtime_guard.py: `aae93748cb1eebc89d68670673c301d739ebe149`.
- 공식 SCAIL sample_func: https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L375
- PyTorch CUDA memory: https://docs.pytorch.org/docs/stable/notes/cuda
- NVIDIA Spark memory architecture: https://docs.nvidia.com/dgx/dgx-spark-porting-guide/overview.html

# B-007G 실행 전 독립 코드 검토

판정: **제한된 코드 계약 검토 PASS**. 실제 P/S/D 실행·메모리 fit·영상 품질 판정이 아니다. 검토자는 모델 로드나 GPU 연산을 실행하지 않았다.

- P는 T5/CLIP/VAE만 생성한다. `model=None`이며 고정 generate의 `getattr(..., no_sync)`는 기본 context manager를 사용한다. nested sampler를 조건 저장 경계로 교체한 뒤 제어 예외로 종료하므로 DiT 생성/forward에 도달하지 않는다.
- 원형 generate 추출로 reference/driving encode, text/CLIP 조건, mask, list 구조와 autocast 경계를 보존한다. history/additional reference는 이번 단일 segment 계약에서 None이다.
- S는 원형 nested sampler의 CPU prediction/latent 및 UniPC 계산 위치를 유지한다. CUDA initial noise의 E 해시와 값, noise 생성 이후 generator state, scheduler timesteps/sigmas를 대조한다. 고정 UniPC step의 generator 인자는 본문에서 사용되지 않는다.
- 조건 직렬화는 dtype/값과 container 구조를 보존한다. 공유 alias는 독립적인 동일 값 복사본이 되므로 storage identity parity는 주장하지 않는다. 고정 모델의 해당 조건 경로는 입력 조건을 읽고 새 batch/feature를 구성하므로 이번 추론 계약에서 alias 복원은 필요하지 않다.
- VAE provenance의 mean/std와 실제 scale=[mean,1/std]를 별도로 기록하도록 수정된 것을 확인했다. D는 공식 wrapper와 clamp를 사용하며 VAE의 encode/decode 진입·종료 cache reset 때문에 P의 transient cache를 이어받지 않는다.
- stage별 exclusive reservation과 별도 exec, 이전 단계 정상 guard 종료·PID0·완료 receipt 검사, 새 단계의 기존 72/24GiB·swap0 가드를 유지한다. parent는 CUDA tensor를 공유하거나 CUDA 초기화 후 fork하지 않는다.
- 최종 latent는 sampler 완료 후 decode 이전에 finite/shape 확인 및 lossless readback·hash·원자적 sidecar 기록으로 보존한다. 실패한 단계 뒤 자동 재시도나 다음 단계 진행은 허용하지 않는다.

작은 CPU fixture는 추출 loop·직렬화·scheduler 계약 근거이며 전체 14B numerical parity가 아니다. 원격 코드/config 고정, 실제 파일 해시, 현재 타 작업 idle·자원 여유, 실제 stage 종료와 산출물 검증은 실행 담당자가 launch 및 각 경계에서 확인해야 한다. 관측되지 않은 실제 품질·성능을 이 검토로 통과시키지 않는다.

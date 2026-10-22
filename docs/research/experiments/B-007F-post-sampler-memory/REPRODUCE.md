# B-007F 재현 계약

현재 새 실행의 결과와 정확한 launch entry는 **NOT_RUN / 고정 대기**다. [PLAN](PLAN.md)이 우선이며, 문서만으로 과거 B-007E나 새 예산을 초기화하지 않는다. 최종 실행 코드가 사전 고정되면 해당 명령·commit을 여기에 연결한다.

## 고정할 입력과 유일한 변경

SCAIL source `78fe19576bb06be96c2375e088574a262a300edb`, B-007E parent `aae93748cb1eebc89d68670673c301d739ebe149`, 변환 checkpoint SHA256 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`을 보존한다. 실제 입력8개와 T5/CLIP/VAE/FA hash는 [B-007E 사전 목록](../B-007E-scail-forward/PREREGISTERED_INPUTS.json)에 연결한다.

공식 H512W896·17f16fps, Lab H896W512·17f24fps, seed20261022·40steps·UniPC·shift3·CFG5·LoRA OFF를 유지한다. post-loop model.cpu만 생략하고 그 위치의 empty_cache와 앞선 offload는 그대로 둔다. isolated source exact diff와 hash, sidecar/phase observer hash를 실제 실행 전에 고정한다.

## 실행 순서

1. 승인된 환경의 resource/queue/swap과 deadline을 확인한다. private `${RUN_ROOT}`·`${MODEL_ROOT}`·`${INPUT_ROOT}`를 매핑하며 실제 경로·secret을 공개하지 않는다.
2. 작은 mock에서 선택한 post-loop 이동만 생략되는지, final latent 저장이 decode보다 먼저인지, decode 실패 때 저장물이 남는지 확인한다. 이 PASS는 GPU 메모리 결과가 아니다.
3. 기존 A·B/ComfyUI와 원본을 변경하지 않는 새 run ID로 공식 sampler 최대1회를 실행한다. B-007E의 실패 장부는 유지한다. 전체 sampler 상한2회에는 실패도 포함한다.
4. 최종 decode 인자 latent와 sidecar의 원자적 완료/hash/값 검증, 실제 completed-step·forward count, phase trace를 확인한다.
5. 공식 raw finite/shape17f·MP4 decode/fps·정상 guard 종료와 자원 회복이 모두 확인된 경우에만 새 프로세스로 Lab 최대1회를 진행한다. 실패하면 Lab NOT_RUN으로 종료한다.

원래 실행 deadline이 만료됐거나 시도가 이미 소비됐다면 명령을 재실행하지 않는다. 새로운 허가 없이 ledger 삭제·새 root로 횟수 초기화·해상도/seed 변경 재시도는 하지 않는다.

## 결과 재사용

latent 파일만 열어 shape가 맞는 것으로 decode 완료를 주장하지 않는다. VAE code/weight/scale과 payload hash, sampler 종료 증거, segment metadata가 함께 있어야 재사용 가능한 final latent다. initial_noise는 대체물이 아니다. 이번에 final latent만 남았다면 다음 별도 실험에서 sampler를 다시 실행하지 않고 decode를 연구할 수 있지만, 이 문서는 그 후속 실행까지 승인하지 않는다.

영상·latent·사진·mask는 private 산출물이다. 공개 자료에는 alias·hash·집계와 재현 코드만 둔다. 실제 raw/MP4가 없다면 review 작업을 수행한 것으로 표시하지 않는다. 연속 재생 관찰이 없다면 temporal 품질은 UNVERIFIED다.

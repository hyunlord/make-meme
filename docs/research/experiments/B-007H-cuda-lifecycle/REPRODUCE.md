# B-007H 재현 계약

현재 실제 H 실행은 **NOT_RUN / 관측 대기**다. [PLAN](PLAN.md)의 제한된 probe와 조건부 S→D만 대상이며, 이 문서 자체는 새로운 실행 승인이 아니다. 실제 코드와 CLI가 고정되면 해당 경로·명령·실측을 연결한다. 추측한 명령으로 GPU 작업을 실행하지 않는다.

## 변경하지 않는 입력

- G의 실제 P 조건 캐시: 17,365,660 bytes, SHA256 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`.
- E와 동일한 initial noise SHA256 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`.
- pinned SCAIL `78fe19576bb06be96c2375e088574a262a300edb`, 기존 weights/mixed dtype/staged loader/attention.
- 공식17프레임·H512×W896·16fps, seed20261022, UniPC40 step, shift3, CFG5, history=None, adapter 없음.
- P 재실행0, Lab0, 신규 다운로드/학습/외부 생성0. 기존 E/F/G 기록과 실패를 보존한다.

## 조건부 실행 순서

1. 같은 서비스 환경의 fresh worker에서 CPU 캐시 무결성 확인→1MiB 이하의 RNG 비소비 CUDA copy/연산/synchronize/readback→leaf별 원래 device 복원과 값 검증을 최대 한 번 수행한다. 모델은 적재하지 않는다.
2. probe PASS와 PID0·자원 회복 확인 후, 별도 fresh worker에서 같은 tiny 연산을 먼저 수행하고 CPU DiT 적재를 최대 한 번 진행한다.
3. 조건 복원과 DiT device 이동을 통과한 경우에만 같은 worker에서 sampler를 최대 한 번 실행한다. 실패도 한정 슬롯에 기록하며 자동 재시도하지 않는다.
4. 실제 final latent 저장·readback과 S 종료·자원 회복 후에만 별도 VAE-only D를 한 번 실행한다. 초기 noise나 G cache를 final latent로 사용하지 않는다.

worker는 CUDA 초기화한 부모의 fork가 아닌 별도 exec다. 실제 absolute deadline과 unit은 H용 사전 등록값을 사용한다. 시작72GiB, 실행24GiB headroom, swap0과 기존 cgroup cap 산식을 유지하며 상위 제한은 읽기만 한다. 환경·driver·다른 프로세스·전역 cache를 변경하지 않는다.

## 필수 receipt

probe와 S에서 실제 API 순서, leaf 이름/byte 수/original device, phase start/end, readback hash, RNG 확인, runtime/context 상태를 구분한다. `mem_get_info`는 실제 CUDA 성공 이후에만 기록한다. CUDA initialized 또는 allocator0만으로 작은 연산을 통과시키지 않는다.

CPU load, restore, move, first forward, sampler step/call, final latent, decode, MP4의 실행 여부를 별도 기록한다. MemAvailable/RSS/cgroup anon·file·events/CUDA allocated·reserved는 겹치는 계정이므로 합산하지 않는다. 종료 상태와 PID0도 확인한다. 단순 service returncode0이나 파일 재생 가능 여부는 시각 품질 수용이 아니다.

실제 launch 명령·실측 결과는 아직 대기다. [학습 문서](../../lessons/B-007H-cuda-lifecycle.md)를 참고한다. 개인 경로·원본 media·조건/latent/가중치는 공개 문서에 포함하지 않는다.

# B-007G 결과: 조건 캐시 통과, S의 CUDA 복원 실패

**CONDITION_CACHE_PASS / S_FAILED / D_NOT_RUN.** 공식 MP4와 final latent는 확보하지 못했다. 조건 준비를 DiT와 분리한 실물 P는 성공했으나 S는 CPU DiT 적재 후 조건 텐서를 CUDA로 복원할 때 실패했다. 신규 S 승인 슬롯1/1을 사용했으며 재시도하지 않았다. Lab·학습·다운로드·imagegen·외부 생성 API는 실행하지 않았다.

## 실제 완료와 실패 경계

| 단계 | 결과 | guarded 시간 | 최소 MemAvailable | 관측 cgroup peak |
|---|---|---:|---:|---:|
| P: T5/CLIP/VAE 조건 준비, DiT 없음 | PASS |143.331초|66.106GiB|23.708GiB|
| S: DiT CPU 적재 후 조건 복원 | FAILED |121.054초|58.415GiB|62.001GiB|
| D: VAE decode | NOT_RUN |미실행|미측정|미측정|

S의 `dit_load_end`는 프로세스 시작115.742초, 실제 load 시작부터111.869초다. 이후 `artifacts.load_tree`가 캐시의 첫 CUDA 텐서를 복원하면서 `torch.AcceleratorError: CUDA error: out of memory; cuDevicePrimaryCtxRetain returned CUDA_ERROR_OUT_OF_MEMORY`를 발생시켰다. `dit_to_device_start`, `sampler_start`, 첫 forward, scheduler step, final latent 저장은 모두 NOT_REACHED다. counter 파일은 존재하지 않아 측정값0으로 꾸미지 않았다.

이번 종료는 **실제 CUDA 오류 / service_exit / returncode1**이다. E/F의 시스템24GiB headroom 종료와 다르다. S의 cgroup high2660, max/oom/oom_kill0, swap0을 관측했다. 마지막 phase에서 `cuda_initialized=true`, allocator allocated/reserved0이지만 드라이버 여유나 필요한 메모리가0이라는 뜻이 아니다. 오류 순간의 내부 할당과 cgroup/드라이버 상호작용의 정확한 원인은 UNKNOWN이다. 시스템·RSS·cgroup·CUDA 회계는 겹치므로 합산하지 않는다. [실측](MEASUREMENTS.json), [시도 장부](RUN_LEDGER.json).

## 보존된 재사용 자료

P는 정상 종료하고 PID0·메모리 회복을 확인한 뒤 S가 시작됐다. 조건 파일은17,365,660bytes, SHA256 `1f1e0b68495b2276a5b6d12eaf160897a16acb2bd2a089e616a55c40bf590308`이며16개 tensor와 별도 metadata를 lossless 저장·재로딩 검증했다. E의 실제 초기 noise 값과 SHA `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`가 일치한다. 단순 seed 일치를 근거로 삼지 않았다.

캐시는 text/CLIP/reference/driving/mask/noise/RNG/timesteps/sigmas를 포함한다. 공유 tensor의 값은 보존했지만 저장 시 별도 storage가 되므로 alias graph 동일성을 주장하지 않는다. **이 파일은 조건 캐시이며 denoised final latent가 아니다. decode-only 재개할 수 없다.** 실제 비공개 ZIP에 저장물과 규약을 포함한다.

공식17프레임·16fps·512×896·40step UniPC·shift3·CFG5·동일 입력과 mixed dtype를 고정했다. `history=None`, 조건/비조건 인자, RNG 소비, CPU scheduler 계산을 추출 코드와 fixture로 확인했다. 실제 S forward가 없으므로 전체 실제 sampler 수치 동등성은 미검증이다. D는 구현만 존재하고 실제 decode/인코딩 검증은 NOT_RUN이다.

## 근거와 한계

- 실행 사전 고정: `648bbe4a1cf9cb13ddf25a6c9b5ca111282b0d6b`. [코드](code/), [재현](REPRODUCE.md), [CPU 검증](CPU_VALIDATION.json).
- CPU 계약 fixture5/5 PASS, syntax·critical Ruff PASS. [전체 type 검사](STATIC_VALIDATION.json)는147errors/523warnings로 NOT_CLEAN이다. 동적 코드 추출·tree typing·upstream import 관련 잔존 진단을 숨기거나 전체 정적 통과로 표시하지 않았다.
- E/F CPU 비교는45분 내 완료했다. [동일 phase 비교](E_F_COMPARISON.md), [객체 수명](OBJECT_LIFETIME.md). 같은 storage의 참조를 두 payload로 계산하지 않았고 기록 없는 이동은 UNKNOWN으로 유지했다. F의 post-loop 정책은 여전히 NOT_REACHED다.
- 종료 뒤 가중치8·환경 증거168·공식 코드8·기존 입력/config10 및 E/F 장부8개 해시 보존을 확인했다. 자체 pipeline/watchdog MainPID0, 다른 Comfy 작업을 보존했다.
- MP4/raw/final latent 없음. 시간 품질 UNVERIFIED. Lab 개체·안무·IG·윙크·발차기·Kling 수용 NOT_RUN. 코드·조건 캐시 통과는 영상 성공이 아니다.

## 다음 작업 하나

**저장된 P 캐시를 재사용하는 S의 CUDA context/CPU weight 수명 사전 진단**을 제안한다. 기존 S trace의 높은 cgroup file/anon과 CUDA 복원 순서를 근거로, sampler 없이 격리된 작은 재현에서 context 확보 시점·mmap 참조 수명·cgroup 회계를 확인한다. 드라이버 원인을 확정한 제안은 아니며 가드 완화·캐시 전역 삭제·다른 프로세스 종료는 대안이 아니다. 이번 작업에서는 추가 로딩·샘플링을 실행하지 않았다.

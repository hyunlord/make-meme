# CONTINUATION_01 실제 비용

| 단계 | 실제 상태 | supervisor wall | min MemAvailable | cgroup peak | CUDA peak allocated | swap |
|---|---|---:|---:|---:|---:|---:|
| CONTROL_FINAL_ONLY | decode PASS, clean exit | 14.6405 s | 76.3385 GiB | 1.6497 GiB | 8.90835 GiB | 0 |
| STEP_S | loader report 경로 누락으로 FAILED | 40.4790 s | 58.9873 GiB | 62.0066 GiB | 512 B | 0 |
| STEP_D | NOT_RUN | — | — | — | — | — |

CONTROL VAE load 0.3573 s, VAE decode 6.6303 s, raw/PNG 저장 구간 1.7411 s, MP4 인코딩+검증 구간 0.3077 s. 이 구간은 phase timestamp 차이이며 순수 연산만 분리한 계측이 아니다.

STEP은 tiny CUDA와 CPU staged weights 적재까지 실행됐다. 34.765 s의 `dit_load_start→dit_staged_weights_done` 구간 뒤 loader 보고서 경로 조회가 실패했다. DiT device 이동·model forward·scheduler update는 미도달이다. 1회의 승인된 STEP 시도를 사용했으며 actual forward=0, scheduler step=0, 새 STEP final latent=0이다. 재시도하지 않았다.

새 VAE decode 1회, BASE/source decode 0회, encoder 0회, 새 이미지 0회, 학습 0회, 설치 0회. CUDA allocator·cgroup·RSS·MemAvailable은 중복/서로 다른 회계이므로 합산하지 않는다. cgroup의 file cache를 GPU tensor 메모리라고 해석하지 않는다.

원시 수치·출력 해시와 phase 목록은 [MEASUREMENTS.json](MEASUREMENTS.json)에 남긴다. CPU support/합성/전송 비용은 별도 산출물 기록과 합쳐 전체 비용으로 검토해야 한다. 실제 연속 재생 품질 검수는 수행하지 않았으며 temporal=UNVERIFIED다.

# B-032 CPU 비용

신규 GPU worker, 이미지 생성, encoder, sampler, VAE decode, 학습, 모델/패키지 설치는 모두 0이다. 기존 tensor 파일의 CPU weights-only 역직렬화는 VAE decode가 아니다.

| 항목 | 실측 |
|---|---:|
| 수동 agent polygon 준비 wall time | 345.005 s |
| FIXED 합성+17 PNG/support 저장 | 1.283 s |
| FIXED 새 MP4 encoding+probe | 0.304 s |
| MASK 합성+17 PNG/support 저장 | 1.630 s |
| MASK 새 MP4 encoding+probe | 0.252 s |
| runner 내부 전체(입력/hash 포함) | 3.900 s |
| `/usr/bin/time -l` process real | 4.15 s |
| process user / sys | 4.57 / 0.23 s |
| process 최대 RSS | 515,997,696 bytes |
| process peak memory footprint | 498,434,912 bytes |
| process swaps | 0 |

위 RSS와 footprint는 별도 회계이며 합산하지 않는다. 전체 연구/검토/전송 비용은 이 4.15초에 포함되지 않으며 최종 delivery 기록에서 따로 보고한다. 파일 I/O block counters는 macOS가 0으로 보고했으며 실제 읽고 쓴 bytes가 0이라는 뜻이 아니다.

새 합성 영상 두 개는 libx264 CRF18 yuv420p, 896×512, 17프레임, preview24fps로 인코딩했다. 원본 FPS는 미확인(`source_fps=null`, `timebase_assumed=true`)이다. 기존 영상 파일은 변경하지 않았다.

| 파생 영상 | bytes | SHA256 |
|---|---:|---|
| FIXED_ENVELOPE | 438946 | `13b8df53883051fedcfe855bf29bede741bcb6a2881c341cf89e994064e76273` |
| MASK_ASSISTED | 405116 | `6da4ebeb74bbd94b8c229dca8e3986ba711f33f4697f988452a5c107d57149cb` |

두 결과 전체 34프레임에서 float E0/E1 및 PNG uint8 E0/E1 검사가 모두 일치했다. 입력 파일 hash는 실행 전후 동일했다. raw 추출 및 polygon rasterization 별도 replay도 18개 파일의 byte/hash 동일성을 확인했다. 기술 계약 확인이며 시각 품질·시간 품질 PASS를 의미하지 않는다.

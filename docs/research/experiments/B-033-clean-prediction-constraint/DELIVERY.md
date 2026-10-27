# B-033 전달·검증 영수증

연구 결과와 실행 코드는 `af5be47a53ba4b1b2159424d684b6fb2cf51b6ea`에 고정한 뒤 압축했다. 아래 ZIP은 Spark에서 생성하고 Mac으로 전송했다. 두 호스트에서 ZIP CRC, 실제 임시 디렉터리 추출, manifest 파일 집합·파일별 크기·SHA256을 확인했다. 원격과 전송 후 ZIP bytes/SHA256은 일치한다. 실제 호스트별 경로는 비공개 `B033-delivery-receipt.json`에 기록했으며 두 ZIP 권한은 각각0600이다.

| 산출물 | 파일명 | bytes | MiB | payload 파일 수 |
|---|---|---:|---:|---:|
| compact | `make-meme-B033-compact-20261027.zip` | 27,596,086 | 26.32 | 60 |
| full | `make-meme-B033-full-20261027.zip` | 290,755,028 | 277.29 | 136 |

- compact SHA256: `91bb98af44b0896a5f815414f782be8a94e420b17734e199d98505b061623680`
- full SHA256: `a0466276fa8f4ba286657016e82968cb050f6e07d39b384339ceb0bcb14c061d`

파일 수는 각 `PAYLOAD_MANIFEST.json` 자체를 제외한다. compact에는 비교 MP4 8개, 전체17장과 고정 확대 시트, 변경하지 않은 B032 support 시각화, viewer, 전체 의뢰서·결과·한국어 해설·재현 코드가 있다. full은 신규 raw3개, source/final-only/step latent3개, 실제 E/M과 실행·재사용 근거를 추가한다. 큰 weights, 중복 조건/prefix cache, 과거 전체 ZIP은 제외했다. compact 검증을 포함되지 않은 raw/latent 검증으로 확장하지 않는다.

기존 SOURCE/B031/B032 영상은 SHA256까지 보존했으며 재인코딩하지 않았다. 새 decode·합성 영상5개는 새 파생 인코딩이다. MP4 8개 모두 896×512·17프레임·preview24fps·0.708333초 파일이다. 원본 FPS는 미확인이므로 실제 원본 초 단위 시간축 보존 주장은 하지 않는다.

기존 Chrome에서 SOURCE의 GBRP MP4가 녹색/자주색으로 표시되는 한계를 그대로 고지했다. 원본 RGB 판독은 프레임 시트 또는 호환 플레이어로 한다. 실제 브라우저 링크·재생 진행·프레임 조작·세 viewport 확인은 PASS지만 연속 시청 평가가 아니며 temporal=UNVERIFIED다. 상세 미디어 검증은 [VALIDATION](media_code/VALIDATION.md)에 있다.

## 전달 비용

| 단계 | 실측 wall time |
|---|---:|
| 검토 영상 복사·전체/확대 시트 생성 | 3.03s |
| Chrome 기능·레이아웃 검사 | 17.22s |
| Spark compact 압축+CRC+추출/hash | 0.64s |
| Spark full 압축+CRC+추출/hash | 10.37s |
| compact Spark→Mac 전송 | 4.42s |
| full Spark→Mac 전송 | 28.13s |

Mac에서 별도로 실제 추출과 payload hash 검사를 다시 수행했다. 위 시간에는 앞선 입력/결과 파일 동기화·agent 판독·문서 작성 시간이 모두 포함되지는 않는다. 23:23UTC 착수 기준으로 최종 비공개 영수증 작성은 00:03:19UTC, 약40.32분이었다. 전체 연구 비용은 [COSTS](COSTS.md)의 GPU/CPU 실행과 이 wall-clock 범위를 함께 보되 서로 다른 메모리 회계나 중복 wall time을 합산하지 않는다.

압축 안의 DELIVERY 문서는 self-hash 순환을 피하기 위해 외부 최종 영수증을 안내한다. packaged RESULTS의 lesson 상대 링크만 ZIP 내부 위치로 바꿨으며 연구 결론은 바꾸지 않았다. 이번 전달 이후 추가 실험은 시작하거나 예약하지 않았다.

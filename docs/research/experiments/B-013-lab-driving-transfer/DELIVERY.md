# B-013 비공개 전달 검증

실험 결과 commit `5e20086319e874e3d5b17711a7e9f1ca30b642a6`을 연구 브랜치에 push하고 원격 SHA 일치를 확인했다. 개인 미디어는 GitHub에 올리지 않았다.

| 항목 | 검증 결과 |
|---|---|
| 최종 파일 | `make-meme-B-013-20261023-final.zip` |
| 생성 호스트 | DGX Spark, 임시 출력 디렉터리 |
| Mac 전송 | 완료, 파일 bytes·SHA256 동일 |
| 크기 | 294,365,414 bytes, 300MB 미만 |
| SHA256 | `28217356dd48d90766a99ae3ab72f42649b0c847d53dac18b96749a766700e15` |
| CRC | 양 호스트 PASS |
| 내부 manifest | 551개 payload의 size·SHA256 양 호스트 전수 PASS |
| 주요 파일 | 두 raw/MP4/final latent/metadata/noise, 전체17장 primary 비교, reference/source/mask,8stage 기록 포함 |
| 제외 | 대형 weights·환경·중복 preprocessing tensor; raw/실패 프레임 삭제 없음 |

첫338,055,977-byte 압축본은 CRC·내부 SHA가 맞았지만300MiB 목표를 넘었다. 원본은 로컬에 보존하고, **중복 collage layout34개만** 최종 ZIP에서 제외했다. `pairs/`와 `four-cells/`의 전체17장씩이며 좋은/나쁜 프레임 선택이 아니다. 해당 파일은 기존 private 결과 폴더에 그대로 남아 있고 생략한 bytes·SHA·상대 경로를 manifest에 기록했다. manifest의 생략 항목은 중복 이미지34개와 대형 preprocessing tensor2개, 총36개다. raw, 실패 구간, 전체17장 primary, blind/group sheets, 영상, latent는 모두 유지한다. 크기 조정은 생성 재시도나 실험 실패가 아니다.

ZIP의 `private/reports/START_HERE_KO.md`와 `private/reports/output-review/review.html`부터 확인한다. `public/experiment/RESULTS.md`와 `public/lesson/B-013-cross-identity-driving.md`는 위 결과 commit의 스냅샷이다. 이 전달 receipt는 압축 후 작성했으므로 ZIP 자체에 포함됐다고 주장하지 않는다. 실제 Mac/Spark 개인 절대 경로는 비공개 전달 안내에만 기록한다.

sampler2/2 소진·실패/재시도/학습0, 후속 실행 없음. 실행 성공과 전신FAIL·국소PARTIAL·temporalUNVERIFIED 판정은 [RESULTS](RESULTS.md)를 따른다.

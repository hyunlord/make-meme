# B-014 비공개 검토 ZIP 전달 검증

2026-10-24 KST. **ARCHIVE_VERIFIED / TRANSFER_VERIFIED**. 실험·품질 판정은 [RESULTS](RESULTS.md)와 같으며 압축 검증으로 품질 수용을 바꾸지 않는다.

| 항목 | 검증 결과 |
|---|---|
| 파일 이름 | `make-meme-B-014-20261024-final.zip` |
| 실제 생성 호스트 | Spark, 임시 출력 디렉터리 |
| 사용자 접근 사본 | Mac, 임시 출력 디렉터리; 전송 완료 |
| 크기 | 182,189,796 bytes (173.750 MiB) |
| SHA256, 양 호스트 동일 | `d0ec1d69de03d695e5adf421cc43f7fc47b55e663fff3404c17a9fd116e8c589` |
| 항목 수 | payload 402개 + `MANIFEST.json` 1개 |
| 검증 | 양 호스트 CRC·payload SHA 확인, 전체 ZIP 바이트 동일성 PASS |
| 별도 확인 | Mac에서 전체 402개 payload SHA 재검증, viewer 자료 103개 실제 추출 |
| 문서 snapshot | 결과 커밋 `3701c40317645fd705dadf4ad30b1e498a3c54d5` |

이 전달 영수증은 ZIP 생성·검증 뒤 작성했으므로 ZIP 안의 문서 snapshot에는 포함되지 않는다. ZIP에 담긴 CURRENT_STATE의 포장 대기는 그 시점의 기록이며 현재 포장·전송은 완료했다. 실제 개인 경로와 원본 검증 로그는 비공개 자료 및 사용자 최종 응답에만 남긴다. ZIP 자체는 GitHub에 업로드하지 않았다.

포함: 신규 raw·MP4·최종 latent 및 decode 규약, filtered reference와 sidecar, 원본 입력·조건 cache의 검증된 실물 사본, 기존 MOV/STILL MP4, 각 조건 전체17장, 비교 MP4·viewer·시트, blind 관찰 및 공개 기록, 코드·설정·메모리 trace·실행 장부·재현 자료. 심볼릭 링크 대신 검증한 실제 파일을 보존했다.

제외: 대형 weights·환경·upstream 전체·중복 또는 일시 파일. 기존 B013의 대형 raw tensor 두 개는 경로·해시·제외 이유를 비공개 staging manifest에 기록하고, 해당 MP4와 전체 프레임은 포함했다. 누락·제외 목록은 ZIP manifest에 남겼으며 유리한 프레임만 고르지 않았다. cache 제외라는 포장 제한 문구는 불필요한 디렉터리·중복 링크를 뜻하며, 재사용한 실제 조건 텐서는 검토 자료에 포함된다.

종료 확인: 자체 worker/watchdog 모두 inactive·MainPID=0, swap0. 추가 sampler·decode·학습은 실행하지 않았다. 전신 FAIL, 국소 PARTIAL, 실제 개체 UNCERTAIN, temporal UNVERIFIED, motion과 형태의 동시 개선 NOT_ESTABLISHED를 유지한다.

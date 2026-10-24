# B-017 검증된 비공개 전달물

결과 snapshot `b62022e0e62b37c49e32196b78b1870543c82627`. 이 전달 문서는 ZIP 생성 후 기록이므로 ZIP 내부에는 해당 snapshot이 들어 있다.

- CPU 실제 case 검증은 Mac에서 실행했다. Spark의 등록 자료는 읽기 전용으로 확인했다.
- ZIP은 Spark에서 생성했고 Mac으로 전송 완료했다. 양 호스트 경로는 각각 `/tmp/make-meme-B-017-20261024-final.zip`이다.
- 크기 **15,275,471 bytes**. SHA256 **`760d9ef3881171c0ce8b33c2c1832f8a4292b8109ccf6e46ffecc1b37c54934e`**.
- 137 payload + MANIFEST.json = 138 entries. 양 호스트 CRC·전체파일SHA·whole-ZIP 동일성 PASS.
- 양 호스트 추출 위치 `/tmp/make-meme-B-017-20261024-final-extracted`.
- Root가 Mac의 모든 ZIP payload와 추출본 SHA를 다시 검사했다. 추출된 코드+portable manifest로 실제 CPU decode 검증을 실행했고, 원래 CPU_CASE_VALIDATION 보고서와 바이트 동일했다.

case19파일(기존media복사16·caption2·누락안내1), 정적시트2, private provenance/권한/PTS/해시/CPU실패·검사·원문감사, 공개 코드/수학/결과 snapshot을 포함한다. 전체corpus·weights·cache·latent·과거생성실패영상은 넣지 않았다. 공식소스원문은 작은코드/문서이며 모델/대형데이터 다운로드가 아니다.

원래 절대경로 manifest는 보존하고 별도 상대경로 portable manifest를 제공한다. 이 파일이 self/pose case를 training-ready로 승인하지는 않는다. 실제 source 진위·권한 UNKNOWN, 충분한referencepose변화 미입증, LabY부재·truecrossID0·training-ready0을 유지한다.

모든 작업은 CPU 자료검토 범위에서 종료됐다. 신규 생성·전체모델load·VAEencode·optimizer/LoRA0, 남긴 실행worker0. 다음 촬영/확보·학습은 자동으로 진행하지 않는다.

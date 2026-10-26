# B-031 전달 검증

아카이브 문서·코드 스냅샷: `c2af9c84cb7765fc54dbabb7947c52716d8014d6`. 이 전달 영수증의 후속 commit과 구분한다. ZIP은 Spark에서 생성하고 Mac으로 실제 전송했다.

| Archive (양 호스트 /tmp) | Bytes | MiB | Payload files | SHA256 |
|---|---:|---:|---:|---|
| `make-meme-B031-compact-20261026.zip` | 63952997 | 60.99 | 159 | `1d9724628620eef7bca56ce5d54a84f685002628b5194f771bc4cefc404c6c7d` |
| `make-meme-B031-full-20261026.zip` | 178810805 | 170.53 | 361 | `ee917521010b6d3641198584b08f4865063c4ecd295eb9bf5ca7563e44068477` |

양 호스트 각각 CRC·실제 추출·모든 payload size/SHA256 PASS이며 전송 후 archive bytes/SHA256도 동일하다. Compact159파일에는 입력·6A0·기존6영상·source3영상·새차량1영상·전체17프레임시트·viewer·보고서·코드가 있다. Full361파일에는 추가로 새 이미지 raw/packed latent6쌍, 새 영상 raw/final latent1쌍, 실제 encoder 입력 및 상세 근거가 있다. Compact에 없는 raw/latent를 compact 검증 범위로 주장하지 않는다. 대형 가중치·venv·중복 prefix cache는 제외했다.

10개 MP4는 재인코딩하지 않았다. 기존 source H.264 RGB(gbrp)는 Chrome에서 자주색/초록색 오표시가 관측돼 viewer에 경고하고 FFmpeg로 디코딩한 전체 프레임 시트를 제공한다. 파일 디코딩·controls 검증은 실제 사람의 연속 품질 시청이 아니며 temporal=UNVERIFIED다.

초기 staging rsync는 목적 디렉터리 부재로 실패했다. 자체 delivery 디렉터리를 만든 뒤 전송·검증을 완료했으며 생성 재시도는 없었다.

시작 UTC `2026-10-26T14:46:41+00:00`, 최종 검증 UTC `2026-10-26T16:37:25.346541+00:00`. 전체 wall 6644.35초 (110.74분),6시간 상한 이내다. 자체 GPU worker는 종료됐고 후속 실험은 예약하지 않았다. 상세 비공개 영수증은 양 호스트 `/tmp/make-meme-B031-delivery-verification-20261026.json`이다.

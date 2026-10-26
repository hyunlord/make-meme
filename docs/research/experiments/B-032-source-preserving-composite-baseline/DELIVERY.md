# B-032 검토 자료 전달 검증

- CPU 합성 실행 호스트: Mac. GPU 작업0. Spark는 기존 자료 제공 및 ZIP 생성/보존에 사용했다.
- Spark와 Mac의 실제 ZIP 위치: `/tmp/make-meme-B032-review-20261027.zip`.
- Spark에서 생성한 뒤 Mac으로 전송했다. 양 호스트 byte identity PASS.
- 크기: 25,658,695 bytes (24.47 MiB).
- SHA256: `8162e3acde3a0a666061507f94fe02738210718b6bcf7b837c239be58ca41ce3`.
- payload manifest SHA256: `a48367a340f4b0bc209d3b631f5c1a1bb5fcc2f5ae09b7005b32e2c2a16a5e61`.
- 143 payload files + manifest, 총144 ZIP entries.
- 양 호스트 CRC, 실제 임시 디렉터리 추출, payload별 크기/SHA 검증 PASS. Mac에서 부모도 ZIP SHA/CRC/member scope 재확인.
- archive 연구 snapshot: `ba3f244a516fa613929501c89f8d12f14c18edf2`. 이 전달 영수증은 archive 이후 별도 기록이다.

source/기존 raw MP4는 byte 그대로이며 새 합성2개는 새 파생 인코딩이다. 전체17 프레임 비교, local0/8/16 경계·접촉·그래픽 확대, support, viewer, 보고서와 재현 코드를 포함한다. 큰 raw tensor·latent·weights·이전 full ZIP은 제외했고, 제외 자료를 archive에서 검증했다고 주장하지 않는다. 공개 원천 DAVIS의 CC BY-NC 4.0 고지와 변경 내역은 비공개 payload에 유지했다. GitHub에는 미디어를 올리지 않았다.

보수적 연구 시간창은 2026-10-26 17:24:00 UTC부터 전달 완료17:43:12 UTC까지 약19분12초다. 이는 준비·수동 주석·검토·기록·전송을 포함하며 CPU runner4.15초와 다르다. 이후 공개 전달 영수증 동기화까지 포함한 종료 시각은 Git commit에서 확인한다. 90분 상한 안에서 종료했다.

뷰어의1280/768/375 폭, 링크, 조작,4영상 metadata와 자동 재생 진행을 확인했다. 처음 자동 play는 user activation 부재로 거절됐고, 명시적 CDP userGesture로 기능 검증했다. 이는 사람의 연속 품질 시청이 아니므로 temporal=UNVERIFIED다. 기존 SOURCE MP4의 Chrome 녹색/자홍색 표시 문제는 원본 영상 수정 없이 경고하고 정상 RGB 시트를 제공했다.

자체 브라우저·HTTP·CPU 패키징 프로세스 종료를 확인했다. 신규 생성·학습·후속 실험은 예약하지 않았다.

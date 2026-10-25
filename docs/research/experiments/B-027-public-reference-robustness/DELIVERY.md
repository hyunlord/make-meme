# B-027 검토 ZIP 전달 검증

실제 실행 호스트는 DGX Spark, 사용자 열람 호스트는 Mac이다. 양쪽 `/tmp`에 같은 이름의 단일 비공개 ZIP을 보존했고 Spark→Mac 전송을 실제 수행했다. 공개GitHub에는 ZIP/미디어를 올리지 않는다.

- 파일명: `make-meme-B-027-public-panel-20261026.zip`
- 크기: **872,854,474bytes**
- SHA256: `81e437aa8ee4e424bae0f32c6ed8eb5f4ce79cec5f0657c117bced7cf6bdff04`
- payload1,057파일 + MANIFEST.json. 양호스트 CRC·manifest coverage·개별파일크기/SHA256·실제 임시폴더 추출검증PASS.
- 두호스트 ZIP byte수/SHA동일. Mac의 `/tmp`는 실제 `/private/tmp`로 해석되며 Spark의 `/tmp`와 별도 저장물이다.
- 실제 raw6개, final latent6개, initial noise6개, 비교영상3개, source/reference/mask·전체17장·실패기록·재현·한국어해설 포함. weights·전체DAVIS archive·중복condition/prefix 제외. 실패출력을 삭제하거나 좋은프레임만 선별하지 않았다.

ZIP의 공개 문서/코드 snapshot은 원격 확인한 `37cb2eb9430e1276bc90e8da65e6ca37d74580b2`다. 현재 DELIVERY와 비용의 전달완료 추기는 ZIP 생성 뒤의 외부 검증기록이므로 그 snapshot 안에 없다. 자기 자신의 hash를 ZIP에 넣는 순환을 만들기 위해 재압축하지 않았다. 외부 `.zip.json`, `.mac-verification.json`, `.timing.json`, `.mac-timing.json` receipt를 양호스트에 보존했다.

Spark package+검증 UTC17:26:30.747831→17:26:56.257779, Mac전송17:27:05.026615→17:27:35.052189, Mac추출검증17:27:35.723520→17:27:39.425267. 시작15:11:00Z부터 전달검증까지8,199.425267초이며8시간상한안이다. GPU worker span/단계별시간과 혼동하지 않는다.

최종 runtime receipt에서 자체worker/unit 종료와 기존 Comfy서비스 유지를 확인했고, 전달 후에도 GPU process 목록은 기존 보호서비스뿐이며 B-027작업process가 없음을 다시 확인했다. media/package/transfer 작업도 종료됐다. 추가 실험/학습/예약은 없다.

브라우저17frame controls·링크·MP4metadata와 desktop/mobile배치를 확인했다. 이는 파일/뷰어검증이며 독립 사람 연속시청이 아니므로 temporal=UNVERIFIED를 유지한다. 사용자는 추출 후 `private/review/review.html`에서 전체 비교를 볼 수 있다.

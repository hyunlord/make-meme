# SERVICE_RESUME_02 전달

새 상태 감사·중복 실행 장부와 이번 문서만 작은 ZIP으로 보존했다. 이번 표본에서 외부 GPU 작업은 없지만 관리자 정상 중지 상태는 미확인이다. 기존 관측과 이번 차단 이유를 섞지 않았다. 새 GPU worker·sampler·decode·미디어는 모두 0회다.

| 항목 | 실제 결과 |
|---|---|
| Spark 생성 위치 | `/tmp/make-meme-B034-service-recheck02-evidence-20261027.zip` |
| Mac 전달 위치 | `/tmp/make-meme-B034-service-recheck02-evidence-20261027.zip` |
| 크기 | 양 호스트 11,431 bytes |
| SHA256 | `0648932e14a25d03fbd8797ee61122d4543abbba14fedc5784ed807c1fb290e3` |
| Payload / ZIP 항목 | 9개 / manifest 포함 10개 |
| Spark CRC·실제 추출·payload 크기/SHA256 | PASS |
| Mac CRC·실제 추출·payload 크기/SHA256 | PASS |
| Spark→Mac 전송·양 호스트 바이트 동일성 | PASS |
| full archive | NOT_CREATED — 새 raw/latent 없음 |

기준 결과 commit은 `156f232772548db4279643c78df228ea939b3fc9`다. 기존 media·raw·latent·cache·weights·ZIP은 포함하지 않았다. 비공개 감사의 실행 경로·PID·boot identity는 공개 문서에서 제외했다. 이 영수증은 ZIP 봉인 후 별도 Git 기록이다.

Staging 전송 1.137초, Spark 포장·CRC/실제 추출 검증 포함 원격 명령 0.310초, ZIP 전송 0.333초, Mac 검증 0.047초였다. 전달 검증 완료는 2026-10-27 14:37:19.283 UTC, 시작 14:34:04 UTC부터 195.283초다. 이후 영수증 Git 반영 시간은 제외한다.

전송·포장·검증 프로세스는 모두 정상 종료했다. 전달 작업에서 서비스 상태를 추가 조회하거나 변경하지 않았고 자체 연구/GPU worker를 시작하지 않았다. 이전 증거 ZIP과 연구 실패는 그대로 보존했다. 이번 전달 성공은 STEP 실행이나 방법 비교 성공이 아니다.

# EXPECTED_ABSENT_02 실행 증거 전달

실제 모델 CPU 적재 이후 첫 forward 전 가드 중단의 신규 증거를 보존했다. 새 final latent·decode·영상은 없으므로 미디어 compact/full을 만들거나 기존 BASE/CONTROL raw를 중복 포장하지 않았다.

| 항목 | 실제 결과 |
|---|---|
| Spark 생성 위치 | `/tmp/make-meme-B034-expected-absent02-evidence-20261028.zip` |
| Mac 전달 위치 | `/tmp/make-meme-B034-expected-absent02-evidence-20261028.zip` |
| 크기 | 양 호스트 106,983 bytes |
| SHA256 | `3babb0275eea3b897f11fa018117cf8a15020b1fcc076e3554ce483f23aee79e` |
| Payload / ZIP 항목 | 64개 / manifest 포함 65개 |
| Spark CRC·실제 추출·payload 크기/SHA256 | PASS |
| Mac CRC·실제 추출·payload 크기/SHA256 | PASS |
| Spark→Mac 전송·양 호스트 바이트 동일성 | PASS |
| full archive | NOT_CREATED — 새 raw/latent 없음 |

기준 결과 commit은 `76d1ef5e6f92333998a63b0e99faefe85a9e069c`다. 실제 고정 코드·설정·preflight·시작 및 종료 관측·단계별 메모리·loader·실행 장부·이전 점유 작업의 한 번 확인과 신원 요약·최종 문서를 담았다. 개인 경로·PID·boot identity는 비공개 원시 증거에만 보존했다. 기존 media·weights·cache·raw·latent·이전 ZIP은 포함하지 않았다.

Staging 전송 27.191초, Spark 포장·CRC/실제 추출 검증 포함 원격 명령 1.175초, ZIP 전송 2.200초, Mac 검증 0.061초였다. 전달 검증 완료는 2026-10-28 02:08:15.473 UTC다.

전송·포장·검증 프로세스는 정상 종료했다. 전달 lane에서 추가 safety/GPU 조회, 서비스 조작, 후합성·인코딩은 하지 않았다. 이 영수증은 봉인 후 별도 Git 기록이며 ZIP 내부에는 없다. 기존 실패와 운영 차단 기록을 유지하며 전달 검증 성공을 영상 생성 성공으로 보고하지 않는다.

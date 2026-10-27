# OPTIONAL_EXPECTED_ABSENT 증거 전달

새 정책·사전검사·실제 시작 거절과 비용을 작은 증거 ZIP으로 보존했다. 사전검사 뒤 외부 GPU 작업이 관측되어 연구 worker는 시작하지 않았다. 새 model load·sampler·decode·미디어는 0회이며 기존 BASE/CONTROL 비교는 재생성하지 않았다.

| 항목 | 실제 결과 |
|---|---|
| Spark 생성 위치 | `/tmp/make-meme-B034-expected-absent-evidence-20261027.zip` |
| Mac 전달 위치 | `/tmp/make-meme-B034-expected-absent-evidence-20261027.zip` |
| 크기 | 양 호스트 64,584 bytes |
| SHA256 | `151b2c09408872588f6dcf13e4aad7e0e4638c700f153838099539665a1dc9a2` |
| Payload / ZIP 항목 | 44개 / manifest 포함 45개 |
| Spark CRC·실제 추출·payload 크기/SHA256 | PASS |
| Mac CRC·실제 추출·payload 크기/SHA256 | PASS |
| Spark→Mac 전송·양 호스트 바이트 동일성 | PASS |
| full archive | NOT_CREATED — 새 raw/latent 없음 |

기준 결과 commit은 `ad90b7619b56db213d718441e77b46d0d88dd6d2`다. 실제 코드·정책/config/freeze·CPU 검사·preflight·시작 관측·거절 장부와 최종 공개 문서를 포함한다. 사전 설정 파일은 실행 성공 증거가 아니다. 기존 media·raw·latent·cache·weights·과거 ZIP은 중복 포함하지 않았다. 개인 경로·PID·boot identity는 비공개 원시 증거에만 있다.

Staging 전송 1.965초, Spark 포장·CRC/실제 추출 검증 포함 원격 명령 0.333초, ZIP 전송 0.347초, Mac 검증 0.052초였다. 전달 검증 완료는 2026-10-27 16:27:18.874 UTC이며 시작16:13:44UTC부터 814.874초(약13분35초)다. 이후 영수증 Git 반영 시간은 제외한다.

전송·포장·검증 프로세스는 모두 정상 종료했다. 전달 lane은 서비스/GPU 상태를 추가 조사하거나 변경하지 않았고 연구 worker를 시작하지 않았다. 새 후합성·인코딩·뷰어는 만들지 않았다. 기존 프레임 자료를 읽기 전용으로 재확인했으며 새 연속 영상 품질 평가로 취급하지 않았다.

이 영수증은 봉인 후 별도 Git 기록이다. 기존 모든 ZIP·실패 기록을 보존하며 이번 전달 검증 성공을 GPU 실행 또는 방법 품질 성공으로 보고하지 않는다.

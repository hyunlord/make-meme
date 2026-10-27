# CONTINUATION_02 전달 — Mac CPU 증거만

이번 실행은 `BLOCKED_SSH`이며 새로운 STEP latent·raw·영상은 없다. 아래 ZIP은 로컬 코드와 CPU 검증·실패 기록만 담는다. 과거 BASE/CONTROL 자료를 새 결과로 포장하지 않았다.

| 항목 | 실제 결과 |
|---|---|
| Mac ZIP | `/tmp/make-meme-B034-CONTINUATION02-cpu-evidence-20261027.zip` |
| 크기 | 33,029 bytes |
| SHA256 | `20afe71e85579316fda5b179f66e35ba225050742ad5ef22051a6df31b564406` |
| Payload | 22개 파일 + `PAYLOAD_MANIFEST.json`, ZIP 항목 23개 |
| Mac CRC | PASS |
| Mac 실제 추출·파일별 크기/SHA256 | PASS; 포장 후 별도 검증기로 재확인 |
| Spark 전송 | NOT_TRANSFERRED |
| Spark 저장·CRC·추출·해시 | NOT_VERIFIED |
| 양 호스트 바이트 동일성 | NOT_VERIFIED |
| Full ZIP | NOT_CREATED — 새로운 raw/latent 없음 |

내용은 PLAN·RESULTS·해설·실측·재현 문서, 실제 bootstrap/worker/guard 코드, CPU 검사 기록, 이전 archive 정보다. 미실행 media 코드·개인 미디어·가중치·cache·기존 대형 ZIP은 넣지 않았다.

결과 기준 커밋은 `6271fb3a5c4e6faec8a55e6e2d10ab1a7cb49129`다. 봉인 전 추가된 RESULTS의 검증 도구 한계 문단도 포함했으며, `RESEARCH_COMMIT.json`에 문서 snapshot 해시를 기록했다. 이 전달 영수증은 봉인 이후 별도 Git 기록이므로 ZIP 내부에는 없다.

CPU 포장·첫 CRC/추출 검증 0.052초, 별도 CRC/실제 추출·payload hash 검증 0.046초다. 새 미디어 처리·재인코딩·전송은 0회이며 전달 lane에서 SSH·browser·server·GPU 프로세스를 시작하지 않았다. Spark의 현재 프로세스 상태는 접속 실패로 이번에 검증하지 못했다.

기존 CONTINUATION_01 비교 자료는 [이전 전달 기록](../continuation/DELIVERY.md)에 보존돼 있다. 이전 compact(13,511,163 bytes)와 full(86,416,881 bytes)을 새 ZIP에 중복 포함하지 않았다. 이전 양호스트 검증은 그때의 기록이며 이번 원격 재검증으로 주장하지 않는다.

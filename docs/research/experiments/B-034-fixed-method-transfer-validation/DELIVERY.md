# B034 검토물 전달

연구 기준 SHA: `e3d8b9eddb95a031232930b6cdcf76dd3b461e91`.

| 검토물 | bytes | payload | SHA256 |
|---|---:|---:|---|
| make-meme-B034-compact-20261027.zip | 6,400,417 | 81 | `0fbc8c96c297b012027c56925f555e1fbba1b2946a0e1046777cf7c3e3aac5e5` |
| make-meme-B034-full-20261027.zip | 84,566,598 | 280 | `0cc6b94803c444dc2cf269eb36e1b12875d50a2a5b46c0c767afb628cd75ad3e` |

Spark에서 생성한 두 ZIP 모두 CRC·실제 추출·payload 크기/SHA 검증 PASS. Mac으로 전송 후 각각 실제 추출·CRC·manifest member set·payload hash 검증 PASS, 두 호스트의 ZIP 바이트 크기/SHA 동일. ZIP 권한0600. 공개 저장소에는 ZIP/미디어를 포함하지 않는다.

Compact에는 실제 source compatibility preview2개·입력/두 A0/R_star·원본17프레임 시트·뷰어·보고서·재현 코드·DAVIS 이용 조건이 있다. 생성된 영상은 없으며 BASE/FINAL/STEP은 명시적 NOT_RUN이다. Full은 실제 image raw/latent와 차량 BASE final latent, source latent, canonical condition cache·noise·주석·원본 driver MP4 및 실패/QA 증거를 추가한다. 큰 weights·이전 archive·cache symlink 중복은 제외했다. Compact에 없는 latent를 compact 검증으로 확인했다고 주장하지 않는다.

기존 GBRP source MP4는 Chrome에서 색상 오류가 확인되어 source PNG로 새 yuv420p preview2개를 만들었다. 원래 파일과 runtime 입력은 해시 불변이며 full에 보존한다. 이 CPU 인코딩은 0.379초,796,648bytes이고 모델 생성 횟수가 아니다. 실제 final browser의 재생 진행·controls·local links·375/768/1280 layout 검사와 agent 정적 화면 검수 PASS; 인간 연속 시청이 아니므로 temporal=UNVERIFIED.

최종 staging 전송·Spark 압축/추출·Mac 반환/추출검증의 합산 실측 wall time은 304.8초다. 개별 압축/네트워크 구간은 별도 계측하지 않았으며 중간 확인·협업 대기 포함이다. 자체 Chrome/server 잔여 프로세스는 관측되지 않았다. 외부 전달 receipt는 ZIP 자기 해시 순환을 피하려고 archive 밖에 보존한다.

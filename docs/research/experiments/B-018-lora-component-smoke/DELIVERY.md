# B-018 전달 검증

비공개 검토 ZIP은 실제 실행 호스트에서 생성한 뒤 Mac으로 전송했다. 두 호스트의 bytes 및 SHA256이 같고, 각각 CRC·payload hash·압축 해제 후91개 파일 hash를 검증했다. private 절대 경로는 공개하지 않으며 사용자 전달 응답과 비공개 receipt에서 구분한다.

- ZIP: `make-meme-B-018-20261024-final.zip`
- bytes: **1,588,140**
- SHA256: `dce2aebd3812922751c4c82d34b90fefcc6c1ec38149c707283fa186b7d650ee`
- payload91개 + manifest1개, 총92개 항목
- CRC / payload SHA / extracted SHA / Spark↔Mac byte identity: **PASS**
- 포함: synthetic fixture, TEST_ONLY initial/final adapter와 schema, 실제 runner·설정·CPU/GPU/타입진단·자원로그·검토·문서 snapshot
- 제외: 전체 기반 가중치, 개인 사진/영상, condition cache, 모델 다운로드, optimizer 전체 state

Archive의 공개 문서 snapshot은 최종 전달 receipt 작성 직전 상태다. snapshot/source manifest로 실제 내용 hash를 고정했다. 자기 자신의 ZIP hash를 archive 안에 넣는 순환 구조를 만들지 않았다. 최종 GitHub commit과 이 전달 receipt는 별도 후속 기록이다. ZIP을 공개 저장소에 업로드하지 않았다.

자체 worker와 watchdog은 모두 inactive·MainPID0이며 추가 모델 실행은 없다. 패키징 안전검사에서 pytest cache 경로를 처음 차단했고, 불필요한 cache를 명시적으로 제외한 뒤 최종 ZIP 하나를 만들었다. 실패/타입 진단 자료는 제외하지 않았다.

# B-019 비공개 제출 검증

결과·학습자료 commit: `1bb877c3183c6bbfdbf9c7c7d1f5c7d22cc0318d`. 사전등록 commit: `26c085635c41f77d26bd9f75a5c0976389b7ee3a`.

검토 ZIP은 실제 실행 Spark의 `/tmp`에서 만든 뒤 승인된 연결로 Mac의 `/tmp`에 전송했다. 두 호스트의 파일명은 `make-meme-B-019-20261024-final.zip`이다. ZIP 자체는 GitHub에 업로드하지 않았다.

- 크기: **8,113,024bytes**
- SHA256: `4d12802124db539b5f20f80bfca798c858bb54cb35f41a184b8ff6331fb1382f`
- 108payload/109members. CRC·모든payload SHA·실제추출본 SHA·두호스트 전체파일 byte동일성 PASS.
- 작은 synthetic x/target·context/e·TEST_ONLY 초기/최종 adapter, schema, runner/config, 실제gradient·memory·reload·typing·독립검토·재현 포함.
- 대형baseweights·긴synthetic tensor·개인미디어·영상·optimizer state 제외. 미실행/제한을 삭제하지 않았다.
- 마지막 확인에서 owned worker/watchdog 모두inactive/MainPID0. 기존 보호GPU서비스만 남았으며 새학습/생성/추가worker는 시작하지 않았다.

이 문서는 포장 후 작성되어 ZIP의 공개문서 snapshot은 위 결과commit까지다. 파일해시·전송 검증 receipt는 비공개 연구 폴더에도 별도 보존했다. 전체모델학습·영상품질·개체/자세분리는 NOT_RUN, 실데이터는 DATA_PENDING이다.

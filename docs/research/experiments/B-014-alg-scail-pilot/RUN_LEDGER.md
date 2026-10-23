# B-014 실행 장부

사전등록 `3cd90e196307fe1f663e8533124a0cbe42f8f41e`. P0회, PROBE1/1·S1/1·D1/1, 실패0·재시도0. 기존 B013 baseline을 다시 생성하지 않았다.

S40step·88forward와 active i0..7의24call, 후반32step의64call을 실제 trace/counter로 검증했다. 원본negative→lownegative→lowpositive 이후 원래positive→negative 순서로 복귀한다. 각 branch SHA는 실제 device restore 때 검증한 reference를 kwargs 선택에 따라 기록한 것이며 매 호출 GPU 전체 bytes 재해시는 아니다.

최종 latent 파일 SHA `3d76cbc4f95e881346da2500c037d413e05e79e360f8b3ef3001d0ad2ee24594`, value SHA `d99d52d2ef1ba3c84b26289f5d740fced484072d6f91fdc453dcac861b9c8bf8`; finite/readback PASS, 초기 noise와 다르다. D는 저장된 x0만 decode해 finite17f24fps와 ffmpeg 검사를 통과했다. 기술적 출력 완료이며 시각 품질/production 수용이 아니다.

종료 후 부모 cache/metadata/noise/receipt와 코드·입력·sidecar 총426개 해시 검증 PASS. owned 두 unit inactive/PID0, 기존 서비스 identity/idle 보존. 실제 단계시간·메모리·파일해시는 MEASUREMENTS.json과 RUN_LEDGER.json에 있다.

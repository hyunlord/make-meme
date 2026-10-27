# 보존 latent의 재사용 계약

BASE final latent SHA256: `687197642b668543d771a14ce8a78fcfa5e58dee91f526ffead26a92448f4d40`

크기: 2293840 bytes. rigid_R1의 실제 40 UniPC step / 80 official forward 완료 후 생성 구간 x0를 저장했다. reference prefix나 initial noise가 아니다. shape `[16,5,64,112]`, dtype FP32, tensor SHA256 `3a0d6aacca1fe4342ba28b3ea1a12a5a0a2c7d83221226ae896c5cd1f0d322ad`, official WanVAE model-space이며 저장 tree는 `x0`의 길이1 list이다. 인코딩/디코딩 scaling은 공식 WanVAE wrapper 내부 규약을 유지한다. 출력 계약은 `[3,17,512,896]`, preview24fps, 원본fps 미확인이다.

조건 cache, source latent, 실제 noise, 모델/코드/입력 계보의 파일 hash는 EXECUTION_COUNTS.json에 있다. exact tensor dtype와 tensor hash, condition provenance는 비공개 final_latent.json에 보존한다. BASE teardown guard는 other_service_work이며 이를 변경하지 않는다.

이번에 decode는 실행하지 않았다. 저장물의 존재는 영상 품질 PASS가 아니다. 후속 허가가 있더라도 sampler 재생성 대신 이 저장물을 사용한 제한된 decode를 검토할 수 있다. 이번 실행의 predecessor gate를 우회하는 명령은 제공하거나 실행하지 않았다.

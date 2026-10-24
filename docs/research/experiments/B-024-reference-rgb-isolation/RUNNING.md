# B-024 착수 기록

2026-10-24 18:07UTC 착수, 전체 deadline21:07UTC. 최신원격 eb9636fd42750e4b2fa350b2c09ce9268dc7f98c 확인 후 clean 문서worktree를 fast-forward했다. 원래 B023기록/원본/환경을 보존한다.

B023의 원본보존 과제FAIL을 유지하면서 비객체 reference RGB만128로바꾸는 1회 비교다. 동일support·개체픽셀·자세·위치·크기·semanticmask·replacement모드·text·noise·시간축을 유지한다. VAE/CLIP를 모두새로계산하고 4leaf만교체한다. 배경과padding공동개입이며pose제거나identity-only표현이아니다.

연결확인은18:37UTC까지로제한한다. 기존ref/driverlatent각decode1과원래refVAE/CLIP재인코딩확인1세트,새ref인코딩1세트를단일encoderworker에서수행한다. T5/DiT동시적재없음. 구체적pipeline결함발견시sampler0으로중단하며UNKNOWN만으로무한감사하지않는다.

전체예산: encoderworker1,PROBE최대1,sampler최대1(40/80),그finaldecode최대1. 학습/다운로드/외부생성/imagegen/재시도0. 기존72GiB시작·24GiB실행headroom·swap0·기존서비스보호유지. 사전코드/config고정push후실행한다.

평가고정: 전체17장+local0/8/16,896×512·30fps SOURCE/B023/B024 비교; 원래/회색reference 별도표시. 침실누수·임의배경·장면보존·사족자세·머리방향/순서·형태·실제개체/체형·encoder비용을분리한다. 연속실제시청없으면temporalUNVERIFIED다.

초기Spark상태: B024기존실행없음,이전worker종료,기존Comfy서비스만GPU사용,MemAvailable96,261,824,512bytes,swap0. 이것은시작관측이며전구간안전보장은아니다.

## Reference worker completed
Original reference and driving latent decoded once each. Root and independent reviewer viewed seated-bedroom reference and standing-natural-motion driving; no concrete pipeline defect identified. Original VAE/CLIP repeat max_abs and RMS were0, observed rather than required byte-equality. Derived cache changes only4reference leaves;12leaves and device/container contracts preserved. Encoder worker ended and resources recovered. Authorized single PROBE/S/D proceeds. Temporal quality remains UNVERIFIED.

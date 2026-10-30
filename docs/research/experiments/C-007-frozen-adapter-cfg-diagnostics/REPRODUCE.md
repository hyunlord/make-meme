# C-007 재현 경로

부모 c4aef32de21de4073bd4eb1861df4d35f2eda793, 실행 전 동결 e61ca14ace07cd78e221a08842c94b71cf5adad5. 기존 C 트랙의 1.3B 환경·DiffSynth 실제 파일과 C003 현행 guard를 재사용했다. 설치/다운로드/가드 변경은 없다. 개인 경로·체크포인트·입력 tensor는 공개하지 않는다.

1. INFERENCE_INPUT_MANIFEST.json의 기존 입력/checkpoint0·128·256 hash와 부모 cache 계보를 확인한다. 원본은 읽기 전용이다.
2. 기존 load_cache의 제외 규칙을 적용한 뒤 명시된9key만 inference sidecar로 복사한다. clean_latent/loss_mask를 생성기로 넘기지 않는다.
3. 별도1000-step training grid에서 고정5sigma를 찾고 영상별 CPU seed20261101/+1 noise를 한 번 만든다. `diagnose.py --config <absolute-config>`의 one-step phase로160 forward를 수행한다.
4. `generate_video.py --config <absolute-config>`를 BASE1→ON256/1→BASE5→ON256/5 순서로 각각 원 보호 경로의 CPU 검사와 heavy stage에서 실행했다. 각 단계의 source/anchor/layout/mask/sidecar/checkpoint 및 코드 hash는 private freeze receipt에 있다. CFG는 실제 pipeline 인자다.
5. 같은 runner의 replay phase는 BASE5/ON5의 실제 savedcontext와 pre-step0/25/40/47/49만 사용해40 forward를 수행했다. 새 sampler나 target loss를 만들지 않는다.
6. 사후 CPU 비교는 실제 context와 진단 cache의 차이를 보존한다. 이를 맞추기 위해 encoder를 다시 실행하거나 기존 결과를 덮어쓰지 않았다.
7. `build_review.py <private-root> <existing-elephant-data> <review-root>`는 비교 뷰어/시트만 만든다. 원 MP4는 byte copy이고 source/layout 미리보기·JPEG시트는 새 파생물이다.

공개 JSONL은 원 관측 스칼라/shape/hash를 포함하며 경로/PID/tensor는 포함하지 않는다. `PROBES/CFG_STATS/BLOCK_STATS`는 data-noised 상태, `ROLLOUT_PROBES/REPLAY_BLOCK_STATS/REPLAY_CHECKS`는 실제 생성 상태, `ROLLOUT_STATS`는 원 sampler 관측이다. 같은-state와 서로 다른 trajectory 차이를 섞지 않는다.

재현 설명은 추가 실행의 자동 승인이 아니다. 이번 예산은 완료했고 추가 학습·수리·probe·영상은 시작하지 않는다.

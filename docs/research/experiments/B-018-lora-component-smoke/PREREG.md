# B-018 실행 사전 계약

분류는 `SYNTHETIC_TENSOR_CONTRACT_TEST`다. B-017의 권한·실데이터 부족을 해결한 것으로 해석하지 않는다.

- seed20261024, x와 별도 pseudo target `[1,36,5120]`.
- 마지막 `blocks.39.self_attn.`의 실제10개 F32 tensor만 per-tensor 로딩: 419,553,280 bytes. 전체 모델·개인 미디어·inference cache 로딩0.
- 공식 dim5120, heads40, head_dim128, RMSNorm 및 RoPE 유지. ref16/generated16/driving4 token은 수치 fixture다.
- animation H0 / refT0, generatedT1, drivingT1·W120. 실제 영상17프레임을 뜻하지 않는다.
- Q/V rank4, alpha4, dropout0. 81,920개 FP32 adapter parameter만 AdamW 대상. lr1e-4, weight_decay0, 최대3update.
- projection BF16, norm parameter FP32, norm 내부 계산은 공식 코드 유지. 원본 checkpoint F32와 runtime cast 이후 hash를 구별한다.
- initial Bzero, fresh reload, adapter OFF의 GPU 출력 비교 tolerance는 **atol=rtol=1e-3**. max error와 exact 여부를 함께 남긴다. CPU FP32 검사는 exact 비교를 사용한다.
- 실제 공식 FlashAttention 경로와 autograd backward node를 확인한다. SDPA 대체·추가 backend 재시도0.
- GPU worker1회 안에 최대8attention forward: baseline/Bzero/3update/postupdate/reload/OFF. 전체 diffusion sampler0.
- 시작 MemAvailable72GiB 이상, 실행24GiB headroom·swap0. 자체 worker cgroup max8GiB/high6GiB, 최대1800초 및 절대10:00UTC. 타 서비스의 PID/queue를 관찰하고 해당 작업의 unit만 중단한다.
- FAIL/커널오류/비정상 gradient/메모리 위반은 그대로 보존하고 자동 재시도하지 않는다.
- adapter는 `TEST_ONLY/NOT_FOR_INFERENCE`. FULL_MODEL_TRAINING, VIDEO_QUALITY, IDENTITY_POSE_DISENTANGLEMENT는 NOT_RUN.

CPU fixture 검증은 공식 GPU 커널 지원 증거가 아니며, 한 모듈 smoke는 전체 SCAIL training recipe나 실제 FM 학습이 아니다. loss 단조감소는 수용 조건이 아니다.

# B-018 실행 기록

- 시작 계획 HEAD: `a8885357684904285014ee28ac568f568ee59762`.
- 시작 관측: 2026-10-24 08:06:35 UTC. hard deadline: 10:06:35 UTC.
- 현재: CPU 계약·선택키·공식 모듈 연결 확인. GPU worker0/1, optimizer0/3.
- `SYNTHETIC_TENSOR_CONTRACT_TEST`: 개인 사진·영상·조건 cache를 사용하지 않는다.
- Q/V rank4 alpha4 dropout0, AdamW lr1e-4 weight_decay0. 상세 실행 코드·fixture seed·수치 tolerance는 GPU 이전에 고정한다.
- 원본 inference 코드·checkpoint·A는 보존한다. B-017 RIGHTS_PENDING/DATA_GAP는 변경하지 않는다.
- 실제 전체 모델 학습·영상 품질·개체/자세 분리: NOT_RUN.

CPU fixture의 성공은 GB10 FlashAttention backward 성공을 대체하지 않는다. 실제 커널 오류가 발생하면 같은 worker에서 fallback/retry하지 않는다.

## CPU 사전 검토

Helper7검사 통과: Bzero/OFF/재로딩 exact, 첫A0·B비영 및 이후Agradient, adapter-only optimizer와 base 불변, 변조된 저장 스키마 거부. GPU 검사 전 norm을 BF16으로 cast했다가 FP32로 복귀하는 구현 문제를 발견해 직접 FP32 보존 경로로 수정했다. 해당 반올림 회귀 검사를 추가했다. 공식 helper AST만 추출한 CPU RoPE36token forward/gradient도 통과했지만 full package/FA GPU 검증은 아니다.

Helper Ruff 통과, basedpyright0errors/19warnings로 typing은 NOT_CLEAN이다. PyTorch/safetensors 동적 경계 경고를 숨기거나 전체 codebase 정리로 확대하지 않는다.

# B-007E 해설

1. FP32→BF16 casting은 정밀도를 바꾸며 이후 연산에도 rounding이 생긴다. 원본 tensor의 보존, 실행 precision 변경, 출력 품질은 별도 검증이다. BF16은 FP32와 exponent 8bit는 같지만 fraction은7bit로 짧다. 비등록 RoPE tensor는 state_dict key 검사 밖에 있으므로 공식 방식으로 별도 materialization하고 attribute 검사를 해야 한다.
2. 예상값은 reference1792, generated8960, driver2240, 합계12992다. 실제 trace로 확정해야 한다. FlashAttention은 큰 attention score의 materialization과 IO를 줄이지만 parameter와 모든 activation·VAE·T5 메모리를 없애지 않는다.
3. CFG5에서는 조건/비조건 두 branch로 single segment40steps에80 DiT 호출이 예상된다. 이는 noise-time 적분의 함수 평가 수다. video는17/24초이며 sample endpoint 간격은16/24초다. fps를 바꿔도 denoising steps나 model의 motion prior가 자동으로 바뀌지 않는다.

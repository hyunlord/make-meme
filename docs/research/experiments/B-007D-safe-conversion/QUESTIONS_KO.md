# B-007D 이해 질문

1. packed QKV weight가 (3D,D)이고 FP32라면 dim=0 분할 뒤 각 shape와 논리 bytes는 얼마인가? view 분할이 반드시 전체 데이터를 복사하는가?
2. writer가 8MiB chunk만 쓰는데 cgroup memory.current가 수십GiB가 될 수 있는 이유는 무엇인가?
3. metadata load와 safetensors 구조 parse가 모두 통과했다. 값 동등성·보안 격리·모델 실행 중 무엇까지 입증됐는가?

[해설](ANSWERS_KO.md)

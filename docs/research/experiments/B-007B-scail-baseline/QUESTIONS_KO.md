# B-007B 이해 질문

1. packed QKV를 나눈 뒤 shape가 모두 맞다. 이것만으로 동일 모델인가? dtype·순서·값·hash를 각각 확인하는 이유를 설명하라.
2.8MiB씩 mmap view를 쓰면 process RSS가8MiB 이하인가? 변환 dtype를 보존했는데 runtime BF16 policy를 별도로 기록해야 하는 이유는?
3. σ가 감소하는 Flow Matching과 noise→data t가 증가하는 toy의 부호를 연결하라.40 UniPC step에 CFG가2번 forward를 호출하면 이것이80프레임을 생성했다는 뜻인가?

[해설](ANSWERS_KO.md)

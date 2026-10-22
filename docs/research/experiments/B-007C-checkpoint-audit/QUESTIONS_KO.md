# B-007C 이해 질문

1. 같은 shape와 dtype를 가진 두 tensor가 왜 다른 값을 가질 수 있는가? storage offset과 stride를 포함해 설명하고, safetensors 변환에서 반드시 같아야 하는 것과 달라도 되는 것을 구분해 보자.
2. `get_unsafe_globals_in_checkpoint()` 결과가 비어 있고 FakeTensorMode를 썼다면 pickle 객체 복원에 코드 실행이나 메모리 할당이 없다고 결론 내릴 수 있는가?
3. 작은 NumPy RNG fixture의 scoped allowlist와 tensor parity가 통과했다. 이 증거만으로 실제 65GB checkpoint를 변환하거나 추론해도 되는가? 추가로 필요한 증거를 나열해 보자.

[해설](ANSWERS_KO.md)

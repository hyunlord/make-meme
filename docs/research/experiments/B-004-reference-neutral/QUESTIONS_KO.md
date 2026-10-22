# B-004 이해 확인 질문

[이론](../../lessons/B-004-reference-condition.md)을 읽은 뒤 먼저 생각해 보자. 실행을 중단시키는 승인 질문이 아니다. [별도 해설](ANSWERS_KO.md)은 이후에 확인한다.

1. RGB128 reference를 넣는 것, normalized tensor0을 넣는 것, reference 자체를 없애는 것, vace_scale0을 쓰는 것은 왜 서로 다른가? BF16 반올림과 reference prefix의 shape까지 설명해 보자.
2. U=ε−Z, Q=(Z_σ,σ,C)라 할 때 왜 MSE의 최적 예측은 E[U|Q]인가? reference만 달라진 paired comparison에서 초기 noise를 고정해도 출력은 왜 달라질 수 있는가?
3. 두 seed 모두 R-gray에서 직립하고 R-bg에서는 앉는다면 무엇을 지지하는가? 왜 실제 Lab 개체 전이 성공이나 '참조 자세만이 원인'이라고 결론내릴 수 없는가? 연속 재생을 못 보았다면 어떤 판정을 보류해야 하는가?

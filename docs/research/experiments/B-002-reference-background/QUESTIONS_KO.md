# B-002 이해 확인 질문

[이론](../../lessons/B-002-conditioning.md)을 읽고 [별도 해설](ANSWERS_KO.md)을 열기 전에 생각해 보자. 답변은 실행 승인 조건이 아니다.

1. 모델 가중치를 전혀 바꾸지 않았는데 R와 R-bg 출력이 달라질 수 있는 이유는 무엇인가? 조건부 velocity와 ODE 경로로 설명하라.
2. 같은 seed와 같은 initial noise는 언제 다른 의미가 되는가? 이번 구현의 reference 장수, noise shape, 전용 Generator, VAE encoding 순서를 연결하라.
3. 흰 배경 참조에서 침대가 사라져도 '춤을 배웠다'고 말할 수 없는 이유는 무엇인가? 자세 보존과 학습 update를 함께 고려하라.
4. 이번 VACE의 CFG negative branch에는 Lab reference와 Canny가 남아 있는가? CFG와 vace_scale의 차이는 무엇인가?
5. R-bg를 만드는 alpha와 생성 video mask M을 바꾸면 왜 같은 실험이 아니게 되는가?

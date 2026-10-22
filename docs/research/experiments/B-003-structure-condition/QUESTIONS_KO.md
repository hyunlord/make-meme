# B-003 이해 확인 질문

[이론](../../lessons/B-003-structure-conditioning.md)을 읽고 [해설](ANSWERS_KO.md)을 열기 전에 생각해 보자. 답변은 실행 승인 조건이 아니다.

1. RGB(0,0,0) 영상, 정규화 tensor0, VAE latent0, vace_video=None, vace_scale0은 왜 같은 조건이 아닌가?
2. 모든 흰 video mask를 유지하면서 Canny만 검게 바꾸면 VACE context의 어떤 부분이 같고 어떤 부분이 달라질 것으로 예상되는가? 이를 실제로 확인하려면 무엇을 기록해야 하는가?
3. black과 Canny 출력이 둘 다 앉아 있을 때 구조 입력이 무시됐다고 결론내릴 수 있는가?
4. 같은 seed의 paired 비교에서 왜 실제 noise hash와 reference 장수까지 확인하는가?
5. 두 seed 모두 Canny가 더 직립해도 시간 일관성·개체 유지·다른 안무 일반화가 증명되지 않는 이유는 무엇인가?

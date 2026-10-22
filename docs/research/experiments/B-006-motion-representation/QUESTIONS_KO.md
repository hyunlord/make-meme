# B-006 이해 확인 질문

[학습 문서](../../lessons/B-006-animal-motion-representation.md)를 읽고 생각해 보자. [별도 해설](ANSWERS_KO.md)을 뒤에 확인한다.

1. 원본에서 root가 가려지고 앞발만 보인다. root-relative 좌표와 발 속도를 계산할 때 무엇을 보류해야 하는가? 2D contact와 실제 체중 지지를 왜 구분하는가?
2. 작은 개의 skeleton을 넓은 Lab 크기로 일괄 scale하면 왜 retargeting이 완성되지 않는가? body shape·관절 회전·카메라 projection을 식으로 연결해 보자.
3. RGB이미지를 받는 VACE에 animal heatmap을 넣는 것과 SCAIL-2의 공식 RGB driving은 어떤 근거 차이가 있는가? SCAIL 코드에 SDPA fallback이 보여도 현재 Spark 실행 성공을 선언할 수 없는 이유와24fps 평가의 함정을 설명해 보자.

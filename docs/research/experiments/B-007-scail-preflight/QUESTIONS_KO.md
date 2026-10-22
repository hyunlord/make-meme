# B-007 이해 질문

1. QKV의 shape가 `(1,12992,40,128)`일 때 모든 score를 BF16으로 저장한 메모리와 QKV 세 tensor의 메모리를 각각 계산하라. FlashAttention이 전자를 실제로 전부 저장하지 않아도 비교 횟수가 선형이 되지 않는 이유는?
2. SAT checkpoint65.58GB와 변환 dictionary 두 개가 보인다. 왜 RAM을 정확히131.16GB라고 할 수도,28GB라고 할 수도 없는가? 어떤 실제 관측이 더 필요한가?
3. 24fps 원본17장의 마지막 sample time과 파일 길이를 구분하라. 같은17장을16fps로 저장했을 때 motion speed는 어떻게 바뀌는가? tiny SM121 kernel PASS가 이 시간축이나 개체 품질을 검증하는가?

[해설](ANSWERS_KO.md)

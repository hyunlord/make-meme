# B-007 해설

1. score는40×12992²×2=13,503,365,120 bytes, QKV는3×12992×40×128×2=399,114,240 bytes다. FlashAttention은 online softmax와 tile 재사용으로 전체 score materialization을 피한다. dense token pair 계산은 여전히 quadratic이며 FFN 등 다른 메모리도 있다. 이는 모델 실측 peak가 아니다.
2. chunk view와 단순 참조는 storage를 공유하므로 dictionary 수는 full copy 수가 아니다. 반면 checkpoint 부가 객체, 원래 dtype/device, serializer 작업공간, cache/allocator가 존재할 수 있다. 원본 storage/dtype, 변환 중 RSS·GPU allocated/reserved·MemAvailable, 출력 bytes와 실제 peak가 필요하다.14B×2는 제한된 가정의 weight 계산이다.
3. 마지막 sample time은16/24초, 파일 길이는17/24초다.16fps에서는 길이17/16초, 동작 속도2/3이 된다. tiny kernel은 해당 layout/dtype/flags의 연산 가능성과 수치 오차만 확인한다. 파일 시간축·mask 대응·대형 모델 fit·Lab identity와 choreography는 별도 증거가 필요하다.

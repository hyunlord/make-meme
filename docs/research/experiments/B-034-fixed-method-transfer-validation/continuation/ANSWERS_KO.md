# 이해 확인 해설

1. 원본 exact는 후합성 endpoint의 보장이다. E 내부의 target 외형·동작·형태와 경계 품질은 별도다. 원본 SUV를 그대로 남겨도 바깥 배경은 exact가 될 수 있다.
2. FINAL_ONLY는 이미 끝난 trajectory의 endpoint만 바꾼다. STEP은 clean prediction을 공식 solver history와 다음 상태에 반영하므로 뒤의 모델 입력 자체가 달라진다. 40개 단계의 입력 차이는 단순한 마지막 혼합 한 번으로 일반적으로 환원되지 않는다.
3. PID와 MainPID는 현재/과거 관측의 숫자일 뿐 starttime·boot·invocation 등과 결합한 신원 증거가 아니다. proc 부재는 확인 불가능 상태로 남기고 bounded 재관측 뒤 새 live safety가 확인돼야 다음 단계로 넘어갈 수 있다. queue/외부 PID/관측 오류는 별도 차단한다.

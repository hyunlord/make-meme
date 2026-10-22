# B-004 해설

[질문으로 돌아가기](QUESTIONS_KO.md). 실제 B-004 결과를 가정한 해설이 아니라 원리와 가상 결과의 해석이다.

1. RGB128은 이상적 정규화에서1/255이며, Spark CPU에서 실제 upstream 전처리로 확인한 BF16 값은0.0078125다. GPU tensor 관측은 아니다. normalized0과 같지 않다. 또한 VAE의 bias·비선형 때문에 E(0)도0이라고 보장할 수 없다. 회색 한 장은 reference latent와 prefix 시간1개를 유지한다. reference 제거는 시간 길이/noise layout을 바꿀 수 있다. vace_scale0은 reference뿐 아니라 구조를 포함한 전체 VACE hint 기여를 바꾼다. 회색은 reference branch off가 아니다.
2. m=E[U|Q]로 두면 E[||U−a||²|Q]=E[||U−m||²|Q]+||m−a||²이다. 교차항은 조건부 평균0이므로 사라져 a=m에서 최소다. reference 변경은 Q의 조건을 바꿔 학습된 velocity 예측을 바꿀 수 있다. 첫 step의 차이가 이후 latent 경로에 누적되므로 동일 초기 noise가 동일 출력을 뜻하지 않는다. 이 수학적 최적해는 실제 network의 완벽한 학습을 보증하지 않는다.
3. 호환성을 확인한 비교라면 이 장면·두 seed에서 참조 내용 교체가 자세 결과에 영향을 줬다는 국소적 근거다. 회색은 자세뿐 아니라 실제 개체·털·체형 정보도 제거했고, 텍스트의 'reference photo' 지시와도 충돌한다. 따라서 자세만의 독립 원인을 식별하지 못한다. 직립은 원본 대응의 한 항목이며 Lab identity·안무·영상 품질을 함께 통과시키지 않는다. 실제 연속 재생이 없으면 시간 품질은 UNVERIFIED다.

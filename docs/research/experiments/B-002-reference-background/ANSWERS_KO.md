# B-002 해설

1. 고정 함수도 입력이 바뀌면 출력이 달라진다. 생성 모델은 조건 c를 받아 `v_theta(z,t,c)`를 계산하므로 같은 noise에서 출발해도 방향장이 달라져 적분 경로가 갈라진다. 가중치 갱신 없이 조건 개입의 효과를 본 것이다.
2. seed는 난수열 초기화 값일 뿐 tensor 자체가 아니다. shape, reference 장수, 생성 device/dtype, 난수 생성 순서·구현이 다르면 값이나 배치가 달라질 수 있다. pinned 구현은 전용 CPU Generator로 FP32 noise를 만든 뒤 BF16으로 바꾸며 reference slice를 앞으로 이동한다. VAE는 posterior sampling 대신 mu를 반환한다. 이번에는 shape와 실제 noise hash를 함께 확인해야 한다.
3. reference의 방 정보가 줄었을 뿐 앉은 자세와 body arrangement는 남아 있다. B-002의 optimizer update는0이고 새 동작을 학습한 것이 아니다. 직립 동작과 시간 변화가 원본에 대응하는지 별도로 관측해야 한다. 덜 움직여 flicker가 줄어든 것은 춤 개선과 다르다.
4. 남는다. positive/negative text context는 다르지만 shared VACE context는 같다. CFG는 두 text-conditioned 예측 차이를 결합하고 vace_scale은 DiT에 더하는 VACE hint의 배율이다. 이번에는 각각5와1을 고정한다.
5. alpha는 reference RGB 배경만 바꾸는 전처리 도구다. M은 source video를 inactive/reactive 분기로 나누는 모델 조건이다. 둘 다 바꾸면 출력 차이를 reference 배경 변경 하나에 귀속할 수 없다. alpha 경계와 resize filtering의 부수 변화 역시 기록해야 한다.

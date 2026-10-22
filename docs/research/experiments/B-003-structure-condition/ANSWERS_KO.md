# B-003 별도 해설

1. RGB0은 정규화−1이다. 정규화0은 중간 회색 계열 값이다. VAE는 비선형·bias·latent 정규화를 포함하므로 둘의 latent가0이라고 할 수 없다. video=None은 upstream이 정규화 공간 zeros를 만들지만 reference/mask가 있으면 VACE 경로가 살아 있다. vace_scale0은 계산된 hint를 DiT에 더할 때0을 곱하는 별도 개입이다. 이번에는 실제 RGB 검정만 쓴다.
2. reference 한 장의 slice, mask64channel, inactive encoder 입력0은 같다. reactive video 입력은 실제 Canny 정규화에서−1 상수로 바뀐다. 따라서 reactive latent와 최종 context는 달라질 것으로 예상된다. 입력 픽셀·정규화 range·각 slice/branch shape와 hash 또는 수치 차이를 실제 forward 경로에서 기록해야 한다. 전체 context hash 하나만으로 어느 branch가 달랐는지 분리할 수는 없다.
3. 없다. 두 출력이 같은 '착석' 범주에 속해도 세부 형태나 velocity가 달라질 수 있다. reference 착석 자세와 text·모델 prior가 함께 작용하며 구조 정보가 약하게 반영되었을 수도 있다. 경로 실행, tensor 변화, 출력의 구체적 동작 대응은 서로 다른 증거다.
4. seed는 난수 초기화 값이다. shape/device/dtype/구현이 달라지거나 reference 장수가 바뀌어 시간 slice 배치가 변하면 같은 seed라도 같은 tensor가 아닐 수 있다. paired 비교는 실제 noise까지 같다는 근거가 필요하다.
5. 직립 여부는 안무 전체와 다른 항목이다. 같은 자세에서 정지할 수도 있고 얼굴·사지가 붕괴할 수도 있다. 두 seed와 한 개체·짧은 source는 탐색적이며 다른 영상에 대한 일반화 검증이 아니다. 실제 재생을 보지 않으면 시간 품질은 UNVERIFIED로 남긴다.

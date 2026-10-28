# 실제 조건 연결

C-001의 실행 코드를 C-002에 작은 사본으로 확장했다. `Config.condition_mode`는 endpoint/layout_mov/layout_still이며 기존 endpoint RGB127 검사를 유지한다. 두 새 모드는 이미 렌더링한 33장의 uint8 RGB layout을 검증하고 중간 31장만 교체한다. 양끝과 생성 마스크 G 및 reference=None은 불변이다. 모델·scheduler·기존 프롬프트는 C-001 그대로다.

[공식 layout](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/layout.py)의 external/simple contour, black 3px/white canvas 의미를 기존 OpenCV 5.0.0으로 재현한다. 기존 SAM selected mask를 읽으므로 공식 LayoutTrack의 검출/분할은 실행하지 않는다. SAM의 작은 분리 speckle도 원래대로 렌더링한다. S_t 영역/L_t RGB 윤곽/G_t 생성 마스크를 구분하며 source RGB overlay는 검토에만 사용한다.

설치된 DiffSynth base_pipeline.py의 전처리는 PIL→float32→실행 BF16/device→RGB×2/255−1 순서이며, 영상 축은 BCTHW다. WanVACE unit은 G를 0..1로 정규화한 뒤 inactive=X×(1−G), reactive=X×G를 별도 VAE 인코딩한다. 중립 0은 정규화된 domain의 0이며 uint8 검정 RGB0과 다르다. 두 RGB 잠재 16+16채널과 마스크 64채널을 결합한다. 마스크는 공간 8×8을 64채널로 정리하고 시간 33→9 nearest-exact로 압축한다. 예상 context [1,96,9,60,104], noise [1,16,9,60,104]는 실제로 첫 model_fn에서 확인한다. vace_scale의 기존 default 1.0을 기록하며 변경하지 않는다.

설치된 pipeline의 원래 model_fn 호출 직전 kwargs latents/vace_context를 detach→CPU contiguous→uint8 view로 해시한다. BF16을 float32로 바꿔 hash하지 않고, 유한값/범위/shape/dtype을 기록한다. 실제 context의 마지막 64개 마스크 채널도 hash/시간별 평균을 기록한다. 원 tensor·RNG·출력을 수정하지 않고 추가 forward도 없다. 해시 차이는 입력 전달의 증거이며 조건 활용/품질 향상의 증거가 아니다.

C-001에서 사용한 guard/adapter를 변경 없이 재사용한다. 새 stage/config는 절대경로와 기존 공통 lock을 쓰고 기존 파일 해시를 확인한다. 각 신규 cell은 같은 target entry의 CPU-only systemd 정상 종료 영수증 뒤 heavy를 한 번 실행한다. 네 cell 사이 baseline은 독립이며 한 cell의 sampler→decode는 같은 baseline이다. 과거 B-034와 C-001의 정상 종료 수정 이력은 그대로다.

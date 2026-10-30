# C-006 실제 구현 계약

데이터와 라이선스는 DATA_SPLIT/DATA_LICENSE, 고정 수치는 TRAIN_CONFIG에 둔다. 1.3B의 30개 block 중 26~29 직전에 공유 motion context를 투영한다. MLP 303→192→192와 bias 없는 4개 192→1536 projection은 총 1,275,072개 FP32 parameter다. projection만 0으로 초기화한다.

`point_features.py`는 독립 VAE endpoint [16,1,30,52]에서 3×3 patch를 bilinear sampling한다. full target latent의 끝을 잘라 appearance로 쓰지 않는다. normalized 좌표는 (x+.5)/416, (y+.5)/240이며 align_corners=False다. mask와 원본에는 동일한 aspect-fit 변환을 적용한다.

`point_adapter.py`의 feature는 두 144차원 patch, 두 anchor validity, 현재 xy, 유효한 인접 velocity, 두 anchor offset, frame t, visibility/validity, source_motion_available, sigma로 총 303차원이다. point ID embedding 없이 permutation-invariant sum을 사용한다. Gaussian 공간 weight를 max(1,sum weight)로 나누고 3σ 밖은 0으로 둔다. kernel 폭은 ON/NULL 모두 같은 endpoint bbox 선형보간 폭의 8%이며 각 축 최소 1 token이다. 33장의 spatial splat을 먼저 구한 뒤 명목 그룹 [0],[1..4],…별로 평균한다. 보이지 않는 좌표를 평균해 위치를 만들지 않는다.

NULL은 두 endpoint에서만 좌표·visibility/validity·속도·offset을 만든다. 한 endpoint만 유효하면 상수 fallback, 둘 다 없으면 gate 0이다. 중간 tracker 값은 읽지 않는다. 동적 outline은 세 조건 모두에 있으므로 NULL은 완전한 motion-off가 아니다. 수동 제외는 raw NPZ와 raw cache를 보존하고 별도 sidecar로 validity/anchor validity/patch만 gate한다.

`wan_adapter_forward.py`는 실제 설치된 Wan의 최소 경로를 따른다. text/timestep/patchify 후 VACE hints를 현재 noisy latent로 계산하고, 각 DiT block 뒤 원래 VACE hint를 더한다. encoded VACE context만 캐시한다. prefix 0~25와 hints는 no_grad이고, 26~29와 head는 학습 시 gradient를 유지한다. 동결 가중치도 입력에 대한 미분을 전달한다. 마지막 4개 block에는 non-reentrant checkpoint를 적용한다.

`train_adapter.py`는 현재 scheduler의 1000개 grid를 사용해 매 update 새로운 sigma/noise와 균형 shuffle clip을 선택한다. zσ=(1−σ)z0+σε, target=ε−z0다. object/background 각 영역 평균을 1:1로 합한다. text drop 10%는 positive caption을 실제 inference의 고정 negative caption embedding으로 대체하며 NULL 25%와 독립이다. 이를 빈 문자열 또는 zero embedding이라고 보고하지 않는다.

heldout cache에는 clean target latent가 없다. inference는 새 native pipeline으로 실제 condition RGB를 다시 인코딩하며 cache에서 point/endpoint feature만 읽는다. BASE는 원래 model_fn을 그대로 사용해 adapter를 완전히 우회하고, ON/NULL은 학습과 동일한 함수를 쓴다. 두 CFG branch에 동일한 point 조건을 전달한다. 기존 VACE의 33→9 mask 압축 한계는 유지한다.

메모리 계획은 tracker 단독 → T5/VAE cache 단독 → DiT/VACE 학습 단독 → 전체 추론의 순차 실행이다. 학습 시 T5/VAE를 적재하지 않고 동결 prefix의 graph를 저장하지 않는다. 작은 adapter parameter 수는 전체 forward/backward 메모리의 안전 보증이 아니며 기존 guard가 모든 실행을 감시한다.

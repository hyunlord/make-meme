# C-006 실제 구현 계약

데이터·라이선스는 DATA_SPLIT/DATA_LICENSE, 고정 수치는 TRAIN_CONFIG에 둔다. 1.3B의30개 block 중26~29 직전 shared motion context를 투영한다. MLP303→192→192와 bias없는4개192→1536 projection은1,275,072개 FP32 parameter다. projection만0초기화한다.

`point_features.py`는 독립 VAE endpoint16×1×30×52에서3×3patch를 bilinear sampling한다. full target latent 끝을 잘라 appearance로 쓰지 않는다. normalized 좌표는(x+.5)/416,(y+.5)/240, align_corners=False다. mask/원본은 동일aspect-fit 변환이다.

`point_adapter.py`의 feature는 두144차원patch,2anchorvalid,currentxy,valid인접velocity,두anchoroffset,frame t,visibility/valid,source_motion_available,sigma다. point ID embedding은 없고 permutation-invariant sum을 사용한다. Gaussian 공간 weight를max(1,sum weight)로나누고3σ밖은0이다. kernel 폭은ON/NULL 모두같은endpoint-derivedbbox의8%, 각축최소1token이다.33장의spatial splat을 먼저구한뒤명목그룹[0],[1..4]…별평균한다. invisible좌표평균으로위치를만들지않는다.

NULL은두endpoint에서만좌표·visibility/valid·속도·offset을만든다. 한endpoint만유효하면상수fallback,둘다없으면gate0. 중간tracker값을읽지않는다. 그러나동적outline은세조건모두에있으므로NULL은완전motion-off가아니다. 수동제외는rawNPZ와rawcache를보존하고별도sidecar로valid/anchorvalid/patch만gate한다.

`wan_adapter_forward.py`는실제설치Wan최소경로를따른다. text/timestep/patchify후VACEhints를현재noisylatent로계산하고,각DiTblock뒤원래VACEhint를더한다. encodedVACEcontext만캐시한다. prefix0~25와hints는no_grad이고26~29/head는학습시gradient를유지한다. frozen가중치도입력에대한미분은전달한다. 마지막4block은nonreentrant checkpoint한다.

`train_adapter.py`는현재scheduler의1000grid를써매update 새sigma/noise와균형shuffleclip을선택한다. zσ=(1−σ)z0+σε, target=ε−z0. object/background각영역평균을1:1로합한다. text10%는positivecaption을실제inference의negativecaption embedding으로대체하며, NULL25%와독립이다. 이구현을빈문자열/zeroembedding이라고보고하지않는다.

cache worker에는heldoutclean target latent가없다. inference는새native pipeline이실제conditionRGB를다시인코딩하며,cache에서point/endpointfeature만읽는다. BASE는원래model_fn완전우회,ON/NULL은학습과동일함수다. 두CFGbranch에동일point조건을전달한다. 기존VACE의33→9mask압축한계는유지한다.

메모리계획: tracker단독→T5/VAE캐시단독→DiT/VACE학습단독→전체추론순차다. 학습시T5/VAE를적재하지않고,동결prefix는graph를저장하지않는다. 작은adapter parameter수는전체forward/backward메모리보증이아니며기존가드가모든실행을감시한다.

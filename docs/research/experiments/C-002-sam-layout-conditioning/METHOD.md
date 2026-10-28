# 실제 조건 연결

C-001의 실행 코드를 C-002에 작은 사본으로 확장했다. `Config.condition_mode`는 endpoint/layout_mov/layout_still이며 기존 endpoint RGB127 검사를 유지한다. 두 새 모드는 이미 렌더링한33장의uint8RGB layout을 검증하고 중간31장만 교체한다. 양끝과생성마스크G 및reference=None은불변이다. 모델·scheduler·기존프롬프트는C-001그대로다.

[공식layout](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/layout.py)의external/simplecontour,black3px/whitecanvas의미를기존OpenCV5.0.0으로재현한다. 기존SAMselectedmask를읽으므로공식LayoutTrack의검출/분할은실행하지않는다. SAM의작은분리speckle도원래대로렌더링한다. S_t영역/L_tRGB윤곽/G_t생성마스크를구분하며sourceRGBoverlay는검토에만사용한다.

설치DiffSynth base_pipeline.py의전처리는PIL→float32→실행BF16/device→RGB×2/255−1 순서, 영상축BCTHW다. WanVACE unit은G를0..1로정규화한뒤 inactive=X×(1−G), reactive=X×G를별도VAE인코딩한다. 중립0은정규화된domain의0이며uint8검정RGB0과다르다. 두RGB잠재16+16채널과마스크64채널을결합한다. 마스크는공간8×8을64채널로정리하고시간33→9nearest-exact로압축한다. 예상context[1,96,9,60,104],noise[1,16,9,60,104]는실제로첫model_fn에서확인한다. vace_scale의기존default1.0을기록하며변경하지않는다.

설치pipeline의원래model_fn 호출직전 kwargs latents/vace_context를detach→CPU contiguous→uint8 view로해시한다. BF16을float32로바꿔hash하지않고,유한값/범위/shape/dtype을기록한다. 실제context의마지막64마스크채널도hash/시간별평균을기록한다. 원tensor·RNG·출력을수정하지않고추가forward없다. 해시차이는입력전달의증거이며조건활용/품질향상의증거가아니다.

C-001에서사용한guard/adapter를변경없이재사용한다. 새stage/config는절대경로와기존공통lock을쓰고기존파일해시를확인한다. 각신규cell은같은target entry의CPU-only systemd정상종료영수증뒤heavy를한번실행한다. 네cell사이baseline은독립이며한cell의sampler→decode는같은baseline이다. 과거B-034와C-001의정상종료수정이력은그대로다.

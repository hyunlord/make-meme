# 구현된 조건 변환과 실행 한계

이번 코드는 실행 전 구현됐지만 실제 source scribble 추출과 두 영상은 안전 가드로 NOT_RUN이다. 수식의 실행 품질이 검증됐다는 뜻이 아니다.

`scribble_model.py`는 고정 공식 VACE의 모델 클래스를 재사용한다. `scribble_extract.py`는33개 full-frame832×480 source PNG를 RGB/255 FP32로 처리하도록 구현했다. 실제 weight를 weights_only=True/strict=True로 load하고 eval/inference mode를 쓰며 sigmoid×255를 uint8로 저장한다. 모델 load 자체는 아직 미실행이다. raw PNG를 캐시하고 생성 전에 실제 polarity를 확인해야 한다.

`prepare_internal.py`의 S는 기존 SAM, L은 기존 C002외곽선, J는 grayscale구조다. I=(cv2 정확 Euclidean DIST_L2/DIST_MASK_PRECISE 거리>4)&(L_gray==255). d=I(1−J/255). SAM bbox는 [xmin,ymin,xmax+1,ymax+1)의 half-open pixel-edge 구간이며 pixel center는(x+0.5,y+0.5)다. 정규화 pixel j는 u=(j+0.5)/256−0.5이고 p=c+Du다.

DYNAMIC/HOLD 모두 bbox crop→256×256→현재 bbox에 OpenCV INTER_LINEAR를 적용한다. 범위 밖은0이며 4px 내부 선택 때문에 crop boundary의 선 강도도0이어서 resize의 edge replication이0이다. 영역 mask의 정규화는 INTER_NEAREST_EXACT로 저장한다. d 자체에 I가 곱해져 있어 정규화 mask를 추가 gate로 중복 곱하지 않는다. 역변환 후 현재 I로 clip한다. DYNAMIC은 d_t^N, HOLD는 d_0^N을 사용한다. K는 I 밖에서 L 그대로, 안에서 np.rint(255(1−D)) ties-to-even 후uint8 RGB동일3채널이다.

`video_generate.py`는 C002의 작은 사본에 internal_dynamic/internal_hold와 해당 directory 검사를 더했다. 기존 endpoint회색127/layoutbinary0·255 검사는 유지한다. 새 내부그레이는 uint8RGB동일채널·좌표·I밖L픽셀동일·중간실제변경을 확인한다. 양끝은 기존 anchors, G는0/32whole0·middlewhole255, reference=None이다. 중간 reactive만 바꾸도록 구성했다.

실제 기존 DiffSynth는 정규화 X=RGB×2/255−1의 BCTHW에서 U=Encoder((1−G)X),R=Encoder(GX)를 만들고16+16+64 context를 연결한다. 새 실행은 없으므로 예상shape [1,96,9,60,104]를 이번 실제 관측이라 부르지 않는다.33→9nearest-exact mask에서endpoint0이 빠지는 부모 한계는 변경하지 않았다. 실제hook도 그대로이며 추가forward/RNG변경0이다.

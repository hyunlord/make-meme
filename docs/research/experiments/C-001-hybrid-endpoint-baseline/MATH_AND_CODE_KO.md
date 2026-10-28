# C-001 수학과 코드 해설

이 실험은 완성된 객체 교체 정답 영상이 없는 두 사례에서, 두 앵커만으로 어떤 중간 영상을 만드는지 확인하는 첫 기준선이다. 원본의 중간 프레임은 평가 자료이며 생성 조건이 아니다. 따라서 원본 동작 제어 또는 SAM-guided 생성의 검증으로 해석하지 않는다.

## 1. 좌표와 시간

원본 프레임 크기를 $(W,H)$, 모델 크기를 $(832,480)$이라 하면 공통 배율은 $s=\min(832/W,480/H)$이다. RGB는 Lanczos, GT 마스크는 nearest로 변환하고 동일한 패딩 위치를 사용한다. 새 앵커 원본 네 장은 모두 1652×952이며 832×479로 축소한 뒤 아래 한 행을 패딩했다. 대상마다 독립 crop이나 사후 정합을 하지 않았다. 참조 crop은 외형을 보여 주는 supporting input으로만 사용한다.

모델 표본은 $t=0,\dots,32$이다. 16fps 미리보기의 파일 길이는 $33/16=2.0625$초, 양끝 표본 간격은 $32/16=2$초다. 원본 FPS 증거가 없으므로 `source_fps=null`, `timebase_assumed=true`다. 이 표시 속도가 실제 촬영 속도를 복구하지는 않는다.

## 2. 객체 분석과 배역

마스크 $M_t(x,y)\in\{0,1\}$에서 면적은 $A_t=\sum M_t$, 중심은 $c_t=(\sum xM_t,\sum yM_t)/A_t$다. 빈 마스크에서는 중심을 0으로 대체하지 않고 결측으로 기록한다. bbox는 관측된 마스크의 최소·최대 좌표다. 면적 급변이나 중심 이동은 추적 이상 후보이며 단독으로 실제 동작 실패를 판정하지 않는다.

SAM 숫자 ID와 `edited_subject` 배역은 다르다. 원본 첫 프레임 GT와의 겹침은 후보 선택 보조이며, 이 경우 그 사용 사실을 기록한다. GT가 SAM 출력으로 바뀌는 것은 아니다. 앵커는 별도 이미지로 분석한다. 원본과 앵커를 연결한 가짜 시간열을 만들지 않는다.

## 3. 앵커에서 VACE 조건으로

공식 `FrameRefExpandAnnotator`의 `firstlastframe`과 `expand_num=31`을 실행한다. 입력 RGB 열은 $X_0=I_{start}$, $X_{32}=I_{end}$이며 중간 31장은 값127이다. 이미지 공간 마스크는 $M_0=M_{32}=0$, $M_1,\dots,M_{31}=1$이다. `video_generate.condition()`은 길이33, 실제 양끝 RGB 바이트, 중간 RGB, 모든 마스크를 검증한다. `vace_reference_image=None`이다. 따라서 두 이미지를 reference 목록에만 넣은 경로가 아니다.

VACE는 활성/비활성 RGB와 마스크를 잠재 표현으로 바꿔 denoiser에 전달한다. 다만 이 기존 구현과 공식 구현의 temporal `nearest-exact` 마스크 축소(33→9)는 양끝의 0 표본을 선택하지 않아 9개 마스크 평균이 모두1이다. 앵커 RGB는 inactive VAE 경로에 남지만 픽셀 공간의 정확한 양끝 고정 또는 마지막 프레임 덮어쓰기는 없다. 실제 출력 양끝이 앵커와 얼마나 다른지는 별도로 평가해야 한다.

## 4. 잡음, CFG, 적분

고정 seed20261028로 CPU RNG에서 초기 잡음을 만든다. 기존 DiffSynth의 flow-matching 경로에서 예측 속도를 $v_\theta(z,\sigma,c)$라 하면 CFG는 $\hat v=v_{uncond}+5(v_{cond}-v_{uncond})$다. Euler 갱신은 scheduler가 정한 연속 시그마 사이에서 $z_{k+1}=z_k+(\sigma_{k+1}-\sigma_k)\hat v_k$ 형태다. 실제 기존 scheduler와 sigma_shift5를 사용하며 50회 갱신한다. 공식 runner의 UniPC/shift16과 같다고 주장하지 않는다.

`counted_model`은 실제 model_fn 진입 횟수를, `counted_step`은 실제 scheduler 갱신 횟수를 기록한다. 요청한50과 실제 수행50은 결과가 생긴 뒤 대조한다. 마지막 latent를 원자 저장하고 CPU readback으로 exact equality를 확인한 뒤 decode 결과를 보존한다. BF16, SDPA, tiled VAE는 실행 설정이다. 작은 기준선의 결과를 다른 모델·정밀도·해상도로 일반화하지 않는다.

## 5. 결과를 읽는 방법

앵커 적합성, 출력 양끝 충실도, 중간 target 외형, 동작 순서, 보호 배경, 경계·접촉·그림자, 시간적 안정성을 나눠 본다. 전체 영상 MSE는 객체 교체 정확도의 정답 점수가 아니다. 픽셀 차이는 생성 입력과 출력의 차이를 보여 주는 진단 자료일 뿐이다. 연속 재생 검수가 없으면 temporal은 `UNVERIFIED`다. 다음 연결 모듈은 이번 실제 출력의 실패를 함께 검토한 뒤 설계하며 이번 실행에서 자동으로 추가하지 않는다.

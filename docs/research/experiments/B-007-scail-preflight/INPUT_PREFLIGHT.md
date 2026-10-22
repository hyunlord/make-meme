# B-007A — 실제 입력·색상 mask·24fps CPU 사전검증

상태: **입력/공간/FPS 계약 검사 완료, mask 정밀 경계 PARTIAL/UNRESOLVED**. 새 diffusion inference·모델 다운로드·학습은 0회다. 실제 upstream diffusion writer와 생성 품질은 NOT_RUN이다.

## 근거와 실제 입력

코드는 결과 전 `a020b61f60d67630c10b9e89580cfd8f09a1b8df`에 고정했다. 국소 mask trim은 원본 v1 실패를 본 뒤 별도 amendment `ded0bb3`로 먼저 고정하고 적용했다. 실제 실행은 기존 CPU 환경에서 했다. 개인 사진·원본·좌표·preview는 private review 자료로만 보관한다.

- Lab 사진은 B002의 원본 JPEG를 그대로 읽었다. SHA256 `54f8052c7264139a41d2818d5c881abd2442f462b5d02cc7908c1f360f00fadb`, decoded RGB는1536×2048이며 EXIF transpose를 새롭게 적용하지 않았다.
- B002의 수동 polygon/비학습 GrabCut alpha SHA256 `29ea5d20bf6ee1bf85e263ba14ab1cc3063f4dd6670064a6f63f3184cc725a3a`. 이 alpha는 사진과 같은 decoded 좌표를 유지한다.
- 원본 source 17장(512×288)은 B006 파일별 SHA와 대조했다. A 생성물·타 개체·고양이 자료를 쓰지 않았다.

## 색상 의미와 배역 대응

고정 [공식 README의 mask 의미](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#mask-semantics)와 [실제7색 채널 추출](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106)을 확인했다. white는 배경 가시, black은 배경 비가시, color는 character/driving 대응이다. VACE의 full-white mask와 의미가 다르다.

이번 reference와 driver의 단일 개체 ID는 **동일 red(255,0,0)**, 관련 없는 배경은 black이다. white 배경 채널은 쓰지 않았다. animation `replace_flag=false` 계약이며 replacement 영역 mask로 설명하지 않는다. 이 설정이 새 배경의 외형을 정의하거나 방·반사를 복원한다는 의미는 아니다.

## 공간 geometry

[공식 generate.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/generate.py#L266)는 reference 방향과 target 방향이 다르면 H/W를 교환한다. 세로 Lab를 `target_h=512,target_w=896`에 넣으면 실제로 H896/W512가 된다. 이번 preflight는 최종 **H896/W512**를 명시했다.

| 입력 | 원본 W×H | resize W×H | crop xyxy | 결과 W×H |
|---|---:|---:|---|---:|
| Lab RGB/mask |1536×2048|672×896|[80,0,592,896]|512×896|
| driver RGB/mask |512×288|1592×896|[540,0,1052,896]|512×896|

RGB/mask는 동일 spatial geometry다. RGB는 PIL bicubic, categorical mask는 nearest를 썼다. 공식 torchvision bicubic과 RGB byte 동일성을 주장하지 않는다. 후속에는 준비된 목표 크기 pair를 loader에 전달하는 조건이며, 이번 검사는 실제 모델 loader 실행이 아니다. 공식 코드는 mask에도 bicubic을 쓰므로 원본 크기 mask를 그대로 넘기는 경로와 이 준비 경로를 구분해야 한다.

reference와 driver f0/8/16 정적 preview에서 보이는 머리·발의 crop 손실을 발견하지 않았다. 모든 프레임의119개 가시 표면점이 crop 안에 남는 것도 계산 확인했다. 사진에서 원래 가려진 뒷발을 복원했다는 의미는 아니다. 세로 center crop은 좌우 배경을 제거하므로 원래 가로 영상 전체 프레이밍 보존과 다르다. 단일 개체의 머리·발 보존에는 이번 구간에서 letterbox가 필수는 아니었다.

## mask v1 실패와 v2의 한계

reference는 이미 기록된 B002 수동 alpha다. driver v1은 매 프레임 독립적인 OpenCV GrabCut5이며, 고정한 거친 polygon과 B006에서 관측한 표면점 seed를 사용했다. 학습 분할·flow·좌표 보간을 쓰지 않았다. **v1은 발 아래 반사 일부를 전경으로 포함했다.** 실패 mask·영상·preview를 그대로 보존했다.

v2에서는 실제 RGB의 바닥 확대를 보고 프레임마다 image-left/right 발 아래 및 중앙 꼬리의 보이는 끝 아래에 국소 배경 제외 사각형3개를 기록했다. 전체 바닥을 하나의 선으로 자르지 않았고, 중앙 꼬리의 보이는 부분을 유지했다. RGB를 수정하거나 새 털·발을 그리지 않았다. 원본 좌표와2px 경계 불확실성은 비공개 annotation에 있다.

전체17장 overlay sheet 및 f0/8/16 상세를 실제 정적으로 확인했고, root의 독립 정적 검토도 큰 반사 영역 제거와 꼬리 유지에 동의했다. **f1의 가는 red 잔여선, f0 발/꼬리 주변 바닥 일부와 얇은 경계 모호성은 남았다.** 세 번째 보정을 하지 않았다. 이 잔여 경계는 후속 실제 입력 사용 전 검토 항목이다. mask 품질을 production READY로 표시하거나 수동 수정을 자동화 성능으로 보고하지 않는다.

## 시간과 실제 writer 검사

CPU 결과 MP4는17프레임·24fps·0.708333초다. 원본 sample time은 i/24, endpoint 차이는16/24=0.666667초다. 16fps로 쓰면17/16=1.0625초가 되어 속도가 달라진다. 프레임 복제·보간·시간축 변경은 하지 않았다.

v1/v2 lossless RGB mask MP4를 실제 decode하여 **각각17개 PNG 전체 픽셀이 동일**하고 palette가 black/red뿐인지 확인했다. 출력 metadata만으로 색 보존을 주장하지 않았다. 검증 코드는 [input_preflight_verify.py](code/input_preflight_verify.py)다.

[공식 writer](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/generate.py#L355)는 `fps=cfg.sample_fps`다. [future_fps_override.patch](code/future_fps_override.patch)의 한 줄 발췌와 [CPU mock](code/test_fps_override.py)은 explicit24가 default16보다 우선하고 None은16을 유지하는 제안 expression을 검사했다. 실제 upstream은 변경하지 않았다. 후속 통합에는 `--output_fps` parser·양수 검사와 실제 writer 실행 검증이 필요하다. **CPU mock PASS를 diffusion writer PASS로 확대하지 않는다.**

연속 재생은 직접 관찰하지 않았으므로 temporal quality는 UNVERIFIED다. 비디오 decode 가능·정적 프레임 관찰·실제 속도 관찰은 서로 다른 근거다.

## 실제 색상 tensor 추가 검증

`cac61a7`에 코드를 고정한 뒤 Mac CPU(PyTorch 2.14.1)에서 pinned 함수의 AST만 추출해 실행했다. 전체 모델 import·VAE·diffusion·GPU는 실행하지 않았다. [코드](code/input_mask_tensor.py), [실측 요약](MASK_TENSOR_CHECK.json). 파일 SHA와 정확한 함수 source SHA를 기록했다.

실제 driver 경로는 `additional_spatial_downsample=2` 호출이 아니다. 먼저 `F.interpolate(mask_cthw, scale_factor=0.5, mode="bilinear", align_corners=False)`한 뒤 helper에 `additional_spatial_downsample=1`을 전달한다. bilinear가 임계값보다 먼저 적용되므로, threshold 이후 area downsample과 임의로 동등하다고 볼 수 없다.

| 실제 입력 | 출력 shape C,T,H,W | 활성 red slot | 다른 색 nonzero | 0~1 사이 fractional cell 수 |
|---|---|---|---:|---:|
| 준비된 reference mask |[28,1,112,64]|[1,8,15,22]|0|1,052|
| driver v2 17장, bilinear half 후 |[28,5,56,32]|[1,8,15,22]|0|2,380|

두 출력 모두 CPU float32, finite이며 min0/max1이다. 함수 docstring은 binary라고 적지만 실제 area interpolation 결과에는 0.015625, 0.03125 등 점유율 값이 존재한다. 임의 후처리 threshold를 추가하지 않았다. bright 판정은 정규화된225 값보다 **엄격히 큰 경우**이며, 픽셀225를 포함하는 ≥ 조건이 아니다. 이번 입력은 정확한 red/black이므로 색상 혼합을 요구하지 않았다.

이 검사는 실제 입력이 기대한 색상 slot으로 packing됨을 확인한다. 남은 mask 경계 오염을 해결하거나 모델의 의미 해석·생성 품질까지 검증한 것은 아니다.

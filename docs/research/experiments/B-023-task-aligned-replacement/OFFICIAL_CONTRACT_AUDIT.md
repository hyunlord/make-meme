# B-023 공식 입력 계약 감사

2026-10-25. 소스 읽기와 B-020 cache metadata 확인 결과다. B-023 실행·영상 품질 PASS를 대신하지 않는다. 최신 개정 PLAN이 과거 2-case/ROI 계획보다 우선한다.

## 고정 근거와 범위

SCAIL-2 commit `78fe19576bb06be96c2375e088574a262a300edb`의 gitlink는 SCAIL-Pose `519c7f54cb972e7f92684213b7ef6c3e05a8f3b2`다. 실제 로컬 공식 코드와 GitHub API의 pinned Pose 파일을 읽었다. Pose 모델/패키지를 설치하거나 실행하지 않았다.

- [README mask semantics](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#mask-semantics): BLACK은 배경 비가시, WHITE는 배경 가시, 색은 개체 대응을 나타낸다.
- [animation 전처리](https://github.com/zai-org/SCAIL-Pose/blob/519c7f54cb972e7f92684213b7ef6c3e05a8f3b2/NLFPoseExtract/process_animation_aio.py#L79): reference WHITE 명시. driving writer 호출 L99에는 배경 인자가 없으므로 BLACK 기본값이다.
- [replacement 전처리](https://github.com/zai-org/SCAIL-Pose/blob/519c7f54cb972e7f92684213b7ef6c3e05a8f3b2/NLFPoseExtract/process_replacement.py): `process_one`은 ref mask BLACK, driver mask WHITE를 명시하고 driving RGB 파일은 `shutil.copyfile`한다. 일반 `test_mode=False` 경로에서 reference RGB 배경을 지우지 않는다. test_mode의 실제 픽셀+검정 배경 reference 생성은 별도 분기이므로 B-023에 가져오지 않는다.
- [v2_helper](https://github.com/zai-org/SCAIL-Pose/blob/519c7f54cb972e7f92684213b7ef6c3e05a8f3b2/NLFPoseExtract/v2_helper.py#L44): image writer의 colors/bg는 BGR; MP4 writer는 BGR→RGB로 변환한다. WHITE/BLACK만 보면 채널 뒤집힘을 발견할 수 없으므로 RED를 RGB로 실제 확인해야 한다.

| 경로 | replace | reference bg | driving bg |
|---|---:|---|---|
| B-020 cache 계약 | false | WHITE | WHITE |
| pinned animation e2e 전처리 | false | WHITE | BLACK |
| pinned replacement 전처리 | true | BLACK | WHITE |

이는 계약 차이이며 과거 실패의 원인 확정이나 WHITE/WHITE 입력의 보편적 금지 증거는 아니다. 이번 비교는 mode와 reference mask를 함께 바꾸는 과제 적합성 진단이다.

## 실제 mask → 조건 경로

[wan/scail.py](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L286)의 `generate`는 reference RGB를 VAE로 encode하고, reference mask는 별도로 `extract_and_compress_mask_to_latent`에 전달한다. RGB에 semantic mask를 곱하지 않는다. driving RGB와 mask는 각각 bilinear/align_corners=False로 공간 1/2 처리한 뒤 RGB는 VAE, mask는 helper로 보낸다(L435–452).

[helper](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106)는 [-1,1] RGB에서 실제 비교식 `> (225-127.5)/127.5`를 사용한다. 주석의 ≥225와 달리 연산은 strict `>`다. WHITE/RED/GREEN/BLUE/YELLOW/MAGENTA/CYAN 순의 7채널을 만든다. BLACK 전용 채널은 없고 7채널 모두0이다. 공간 area interpolation 이후 fractional coverage가 있으므로 helper docstring의 `{0,1}`만 보고 최종 latent를 binary라고 단정하지 않는다.

첫 프레임을 4번 앞에 배치하고 나머지 프레임을 붙여 4-frame group을 채널로 패킹한다. 17frame→5latent time, 7×4=28채널이다. reference 단일프레임은 4번 반복하므로 white index는 0/7/14/21, red는 1/8/15/22다. 생성 부분에는 all-zero mask suffix가 추가된다. 단순 `1-white`나 수동 채널 invert는 실제 helper와 같다고 가정하지 않는다.

## B-020 metadata에서 확인한 shape와 B-023 기대 차이

`B-020/artifacts/conditions.json` 실제 저장 metadata의 16leaf 기준. 아래는 B-023 새 cache 실측을 아직 대신하지 않는다.

| leaf | 역할 | shape | B-023 기대 |
|---|---|---|---|
| t0 | initial noise | [16,5,64,112] FP32 | 보존 |
| t1/t7 | positive/negative text | [77,4096]/[1,4096] BF16 | 보존 |
| t2/t8 | CLIP | [1,257,1280] FP16 | 보존 |
| t3/t9 | ref RGB latent | [16,1,64,112] FP32 | 보존 |
| t4/t10 | ref mask + generated zero suffix | [28,6,64,112] FP32 | helper로 재계산한 prefix만 변경 |
| t5/t11 | driving RGB latent | [16,5,32,56] FP32 | 보존 |
| t6/t12 | driving semantic mask | [28,5,32,56] FP32 | 보존 |
| t13 | generator state | [16] uint8 CPU | 보존 |
| t14/t15 | timesteps/sigmas | [40] int64/[41] FP32 | 보존 |

두 `replace_flag` scalar false→true는 tensor leaf 수에 포함되지 않는다. history/additional ref는 None. 실제 비교는 t4/t10 외14leaf hash, suffix·RED 영역, scalar 구조, parent provenance를 확인해야 한다. initial noise SHA는 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`다. 동일 seed만으로 보존을 대신하지 않는다.

## 전체 mode RoPE

[model_scail2.py L836–856](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L836), additional_ref_count=0일 때:

| stream | animation (T,H,W) offset | replacement (T,H,W) offset |
|---|---|---|
| reference | (0,0,0) | (0,120,0) |
| generated/video | (1,0,0) | (0,0,0) |
| driving/pose | (1,0,120) | (0,0,120) |

따라서 H120 단독 변경은 replacement가 아니다. Wpose120은 원래부터 있고 새 개입이 아니다. 120은 token 위치 인덱스이지 pixel 이동이 아니다. 실제 Q/K에 적용되는 함수는 `rope_apply_scail` 경로이며 frequency/token 순서/patch embedding은 유지한다.

`forward` L751–763은 RGB latent patch embedding에 mask embedding을 더하고 driving embedding을 별도 붙인다. semantic channel이 hard alpha로 source pixel을 복사하는 연산은 없다. 이번 mode를 실행했다고 배경 exact-preservation이 보장되지 않는다.

## 수용 범위

소스 계약 확인 COMPLETED. 신규 runtime scalar/hash/shape 검증 및 raw 영상 결과는 실행자가 별도로 채운다. 실제 Lab f126..142(17f/30fps), W896×H512 및 B-020 adapter-OFF가 이번 기준이다. 밈 f7..23·24fps와 섞지 않는다. 같은 개체 source/reference이므로 좋아져도 source-copy와 reference 사용을 식별하지 못한다. 신규 matting/ROI 합성은 이번 실행 범위가 아니다.

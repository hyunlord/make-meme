# B-009 재현 계약

현재 **CPU 사전 검증 PASS / P·조건 통제 PASS**. 실행 사전 등록은 `1936356`이다. [PLAN](PLAN.md)의 reference mask BLACK→WHITE 비교 한 번만 수행하며 B-008 대조군은 재생성하지 않는다. A 및 기존 결과를 보존한다.

## 고정과 변경

정확한 BLACK[0,0,0]만 WHITE[255,255,255]로 바꾸고 RED[255,0,0]의 픽셀·면적·위치는 그대로 둔다. reference RGB는 변경하지 않는다. driving RGB/mask, Lab prompt/negative, input crop/resize, weights/dtype/FA, seed20261022, UniPC40/shift3/CFG5, history=None, animation replace_flag=False를 유지한다.512×896·17프레임·24fps이며 추가 segmentation이나 경계 수정은 없다.

pinned SCAIL은 `78fe19576bb06be96c2375e088574a262a300edb`다. helper strict threshold,7색 순서, temporal pack은 [학습 문서](../../lessons/B-009-semantic-mask-conditioning.md)에 기록했다. README의 mixed resolutions/fps 명시를 따르며 writer16fps를 고정 학습 FPS로 해석하지 않는다.

## 실행 전과 단계별 증거

- CPU 변경 pixel count·palette·RED exact equality를 확인한다. helper 결과 WHITE0/7/14/21의 reference prefix 변화, RED 및 나머지 channel/generated plane 보존을 검증한다.
- 비마스크 tensor의 비교 기준/오차를 결과 관측 전에 등록한다. initial noise·RNG·shape·dtype와 mask 이외의 text/CLIP/reference/driving 조건을 parent B-008과 대조한다.
- P1→PROBE1→S1→D1, 각각 fresh worker와 종료·회복 확인. 실패 포함 각 최대1회, 재시도0이다. 성공한 tiny64-byte anchor 및 staged loader 경로를 사용하며 새 CUDA 감사/모델/환경 변경을 추가하지 않는다.
- S의 실제80forward/40step, final latent finite·hash·readback, D17장·24fps·raw/MP4를 구분한다. 최종 latent가 없으면 D를 실행하지 않는다.

실제 stage CLI·deadline·사전 고정 commit과 receipts는 담당 실행 코드가 고정된 뒤 기록한다. 과거 deadline을 복사하거나 추측한 명령을 실행하지 않는다. 개인 RGB/mask/조건/latent/경로는 공개하지 않는다.

## 판정

원본/B-008/B-009 전체17장과 f0/4/8/12/16, native24fps 비교를 유지한다. WHITE animation에서 참조 침실 유지 자체를 FAIL로 삼지 않는다. 직립·앞발·머리/몸 phase를 주 평가로 삼고 견종 유사성과 개체 일치를 구분한다. 직접 연속 재생이 없으면 temporal=UNVERIFIED다. 추가 자기 재현·학습·생성으로 자동 확대하지 않는다.

## 사전 고정 비교 정책

[CPU_VALIDATION](CPU_VALIDATION.json)은10개 검증 PASS/1.11초/GPU0을 기록한다. [compare_conditions.py](code/compare_conditions.py)의 비마스크 floating encoder 조건은 rtol1e-5/atol1e-6, noise/RNG/timesteps/sigmas와 모든 비개입 mask·비부동소수 tensor는 exact다. reference mask 양 branch는 pinned helper의 old/new prefix에 exact 일치하고 WHITE 외 channel 및 generated plane을 exact 보존해야 한다. driving mask1e-7 변화도 거부한다. 이 CPU fixture를 실제 P condition 통제 완료로 대체하지 않으며 실제 비교 receipt를 별도로 확인한다.

### 실제 P 조건 통제 결과

P114.974초 PASS, 새 cache SHA256은 `e151044c4939c751b551c839f878acedfa233485db72275594d75e619e518ae3`이다.16개 leaf 중 t4/t10(양 CFG branch의 reference mask)만 예상 WHITE prefix 변화가 있었고 max absolute delta는1이었다. 다른14개 leaf는 bit-identical, max delta0이었다. 따라서 사전 등록된 비마스크 float tolerance 범위에 기대어 통과한 사례가 아니라 실제 exact equality를 관측했다. non-WHITE/reference RED 및 generated plane도 통제 검사를 통과했다. 이는 실제 입력 조건 통제의 증거이며 생성 자세 개선이나 유일 원인 규명은 아직 아니다. 후속 생성·시각 품질은 대기다.

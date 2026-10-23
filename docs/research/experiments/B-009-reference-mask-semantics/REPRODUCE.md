# B-009 재현 계약

현재 실물 실행 **NOT_RUN / 대기**. [PLAN](PLAN.md)의 reference mask BLACK→WHITE 비교 한 번만 수행하며 B-008 대조군은 재생성하지 않는다. A 및 기존 결과를 보존한다.

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

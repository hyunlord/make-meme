# B-006 — 동작을 표현하는 것과 동작을 생성하는 것

B-005는 입력 조합이 결과에 영향을 준다는 것을 확인했지만 실제 Lab 외형과 원본 춤을 함께 수용한 결과는0/8이었다. 이제 Canny 제거 실험을 반복하지 않고, 원본에서 보존해야 할 움직임 정보와 그 정보를 실제 받는 모델 경로를 구분한다. [계획](../experiments/B-006-motion-representation/PLAN.md), [공식 코드 감사](../experiments/B-006-motion-representation/MODEL_AUDIT.md), [질문](../experiments/B-006-motion-representation/QUESTIONS_KO.md), [해설](../experiments/B-006-motion-representation/ANSWERS_KO.md).

## 1. 직관: 선이 있다고 관절의 의미가 있는 것은 아니다

Canny에는 털·바닥·그림자·몸 윤곽이 함께 들어 있다. 화면의 한 선이 오른쪽 앞다리인지 배경 경계인지, 가려진 동안 같은 관절이 어디로 갔는지는 별도 정보다. semantic keypoint는 해부학적 ID와 시간상의 instance ID를 명시하지만, 보이지 않는 깊이·털·조명은 잃는다. RGB driving은 더 많은 시각 정보를 유지하지만 source의 얼굴·체형·배경까지 전달하여 외형 누출을 일으킬 수 있다.

표현의 정보량이 많으면 무조건 더 좋은 것도, 단순하면 무조건 더 안정적인 것도 아니다. 모델이 그 표현으로 학습됐는지, 원하는 동작과 불필요한 외형을 분리할 수 있는지가 필요하다. 정보 엔트로피의 숫자를 측정하지 않았으므로 아래 설명을 정량적 정보이론 증명으로 읽지 않는다.

## 2. 좌표·가시성·접촉을 서로 다른 변수로 둔다

프레임 t의 관절 j에 대해 `p[t,j]=(x,y)`는 픽셀 좌표, `v[t,j]`는 visible/occluded/unobservable, `id[j]`는 동물 자신의 좌우를 기준으로 한 해부학적 점이다. 관측되지 않은 p는 null이다. occluded라도 좌표를 추정해 넣는다면 추정 필드와 관측 필드를 분리해야 하며 이번에는 관측 좌표를 지어내지 않는다.

영상 크기 W,H에서 `p_norm=(x/W,y/H)`는 화면 크기에 대한 좌표다. root-relative 표현은 `q[t,j]=(p[t,j]−p[t,root])/s[t]`다. root와 body scale s의 정의·가시성이 먼저 필요하다. root나 scale 양 끝점이 가려져 있거나 s≈0이면 q는 UNRESOLVED다. torso가 안 보인다고 코나 bbox 중심을 몰래 torso root로 바꾸면 변수 의미가 달라진다.

동물의 좌/우는 화면 좌/우가 아니다. 정면·후면·회전·가림에서 혼동을 note로 남긴다. contact는 visible evidence/possible/unknown으로 기록한다. 2D 발끝이 바닥선에 닿아 보이는 것만으로 실제3D 접촉·체중 분배·힘을 확정할 수 없다.

Tensor 예시는 P `(T,J,2)`, visibility `(T,J)`, observed-valid `(T,J)`, contact label `(T,J)`다. 좌표가 null인 원본 JSON은 tensor화할 때 NaN과 validity mask로 분리할 수 있지만, NaN을0으로 바꾼 뒤 실제 영상 원점 관측처럼 사용하면 안 된다.

## 3. Shape와 motion, 2D의 모호성

3D 관절 X와 카메라 projection π에 대해 관측은 `p=π(X)`다. 깊이가 다른 여러 X가 같은 p를 만들 수 있다. 2D에서 torso가 짧아진 것은 실제 몸통 축소가 아니라 카메라를 향한 회전일 수도 있다.

kinematic tree의 관절은 개념적으로 `X_j=X_parent+R_parent R_local,j b_j`로 쓸 수 있다. bone offset b_j의 길이·체형은 shape, 시간에 따른 회전 R과 root 이동은 motion의 일부다. 실제 관절계·skin deformation·접촉 제약까지 정의해야 완전한 retargeting이 된다. `q=(p−root)/s`는 화면 위치·scale 일부를 제거할 뿐, 작은 source 개의 동작을 넓은 가슴의 Lab에 물리적으로 옮기는 해법이 아니다.

눈 연결선의2D 각도와 실제 머리3D roll도 항상 같지 않다. yaw/pitch·원근·한쪽 눈 가림이 함께 작용한다. 개체 ID·관절 ID·visibility를 유지해야 변화의 원인을 설명할 수 있다.

## 4. 실제 시간과 유한 차분

원본24fps에서 `Δt=1/24 s`, `velocity[t,j]=(p[t+1,j]−p[t,j])/Δt`의 단위는 pixel/s다. 정규화 좌표를 쓰면 screen-fraction/s가 된다. 이는 카메라 움직임을 포함하는 화면 속도이며 world-space 속도가 아니다.

두 시점이 모두 관측되고 같은 점 ID라는 근거가 있어야 차분을 계산한다. 중간 프레임 없이 f0와 f4만 있으면 시간 간격은4/24초이며 frame-to-frame 미분으로 부르면 안 된다. 가린 구간의 선형 보간은 시각화용 추정이지 ground truth가 아니다.

smooth한 궤적은 노이즈를 줄이지만 발차기·머리 회전의 peak와 타이밍을 바꿀 수 있다. 이번 주석에서 누락을 줄이려고 관측되지 않은 점을 smoothing으로 생성하지 않는다. 17프레임의 재생 길이17/24초와 첫~마지막 sample 간격16/24초도 구분한다.

## 5. 작은 PyTorch heatmap 예제: 입력 의미를 먼저 고정한다

아래는 CPU에서 재실행할 수 있는 교육용 renderer다. 무작위 모델·가중치를 쓰지 않는다. `points_px`는 `(T,J,2)`, `observed`는 `(T,J)`다. σ는 원본 pixel 단위의 Gaussian 폭이다. 좌표는 renderer에서만 heatmap 격자로 환산한다.

```python
import torch

def heatmaps(points_px, observed, image_hw, output_hw=(36, 64), sigma_px=4.0):
    h, w = image_hw
    oh, ow = output_hw
    assert points_px.ndim == 3 and points_px.shape[-1] == 2
    assert observed.shape == points_px.shape[:2]
    assert sigma_px > 0 and min(h, w, oh, ow) > 0
    # Heatmap pixel centers mapped into original image coordinates.
    yy = (torch.arange(oh, dtype=torch.float32) + 0.5) * h / oh
    xx = (torch.arange(ow, dtype=torch.float32) + 0.5) * w / ow
    gy, gx = torch.meshgrid(yy, xx, indexing="ij")
    valid = observed.bool() & torch.isfinite(points_px).all(dim=-1)
    safe = torch.where(valid[..., None], points_px.float(), 0.0)
    dx = gx - safe[..., 0, None, None]
    dy = gy - safe[..., 1, None, None]
    fields = torch.exp(-(dx * dx + dy * dy) / (2 * sigma_px ** 2))
    return fields * valid[..., None, None], valid

points = torch.tensor([[[32., 24.], [float("nan"), float("nan")]]])
observed = torch.tensor([[True, False]])
fields, valid = heatmaps(points, observed, (288, 512))
assert fields.shape == (1, 2, 36, 64)
assert fields[0, 1].sum().item() == 0
```

0 heatmap만으로 missing과 화면 밖 관절을 구분할 수 없으므로 validity를 함께 보존한다. 이는 표현·shape 예제이며 반려견 주석 정확도나 생성 성능 실험이 아니다. 로컬 CPU PyTorch 2.11.0에서 위 예제를 실행했고 shape `(1,2,36,64)`와 미관측 채널 합0을 확인했다. 실제 반려견 자료를 쓴 검증은 아니다. 현재 VACE가 이 `(T,J,H,W)` heatmap을 직접 학습된 조건으로 받는다고 가정하지 않는다.

## 6. 모델의 조건 interface와 loss를 연결한다

기존 [VACE unit](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674)은 RGB control·mask·reference를 encode한다. API가 RGB이미지를 받는 것과 animal skeleton의 의미를 학습했다는 것은 다른 주장이다. 임의 관절 색·heatmap을 넣으려면 그 표현과 target video를 연결하는 pretrained evidence 또는 조건 encoder/adapter의 학습이 필요하다. 실제 Lab target 동영상이 없는 상황에서 다른 개의 source를 Lab 정답으로 쓰면 identity 목표가 잘못된다.

SCAIL-2는 [공식 RGB-driving 경로](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L435)를 갖는다. 이름이 `pose_video`여도 RGB가 들어갈 수 있으며, 공간 절반 해상도로 VAE encode한 driving tokens를 reference/생성 tokens와 결합한다. 추가 color masks는 VACE white mask와 의미가 다르다. [실제 mask packing](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/utils/scail_utils.py#L106).

H512,W896,T17의 코드 예상은 생성 latent `(16,5,64,112)`, reference `(16,1,64,112)`, driving `(16,5,32,56)`, driving mask `(28,5,32,56)`다. 4개의 known/history channel을 붙인20채널에 patch embedding을 하고, reference/생성 tokens10,752와 driving tokens2,240를 결합한다. 모두 이번 **코드 유도**이며 SCAIL runtime shape는 NOT_MEASURED다. [token 결합](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L724).

SAT의 [RFLoss](https://github.com/zai-org/SCAIL-2/blob/ac63f8eb369e2f4fac2ce273ead0ae7e602c3919/sgm/modules/diffusionmodules/loss.py#L653)는 σ에서 `zσ=(1−σ)z+σε`, target `ε−z`를 사용한다. history H는 깨끗하게 유지하므로 실제 network input은 `H*z+(1−H)*zσ`다. OCR mask O도 제외하여

`L = mean[(1−H)(1−O) * (vθ−(ε−z))²]`

를 계산한다. mean은 전체 tensor 원소 기준이고 유효 영역 수로 재정규화한 식이 아니다. σ는 LogisticNormal이며 설정에 따라 공간 token 수에 의존한 shift가 적용된다. 참고용 Flow Matching 선형 경로 식과 실제 history/mask 처리를 혼동하지 않는다. 이 loss는 학습 target/condition가 준비된 경우의 경로이며 이번 학습 실행은0회다.

## 7. 실제 확인과 남은 한계

소스·metadata 감사에서 RGB driving interface는 확인했다. 그러나 현재 Spark에는 SCAIL 직접 호출이 요구하는 FlashAttention2/3 import가 없어 공식 경로가 BLOCKED다. generic SDPA fallback이 파일에 있다고 실제 모델이 그것을 사용하는 것은 아니다. 모델 가중치·activation peak·ARM64 kernel·실제 동물 출력은 미측정이다.

공식 writer 기본16fps는 우리24fps와 다르다. 17프레임 그대로16fps로 저장하면 속도가 변한다. 미래 baseline에서는 원본 aspect·frame time과 모든 mask의 동일 변환을 기록해야 한다. 입력 표현의 정확성과 실제 영상 생성 성공은 별도다.

원본 17프레임의 수동 관측에서는 프레임마다 코·양눈·네 발 끝의 표면점 7개, 총 119개가 visible이었다. 발 끝은 손목·발목 관절 중심과 다르다. 내부 관절 중심 9개씩 총 153개는 unobservable, 꼬리 뿌리 17개는 occluded로 기록하고 좌표를 null로 유지했다. 접촉 관측 68개 중 앞발 34개는 공중에 보여 touching=false이며, 뒷발 34개는 접촉 가능성만 있어 touching=null이다. 수동 주석은 해부학적 정답이나 자동 추정 성능의 증거가 아니다. [관측 결과](../experiments/B-006-motion-representation/RESULTS.md).

실제 주석을 읽는 [joint_heatmaps.py](../experiments/B-006-motion-representation/code/joint_heatmaps.py)는 Spark CPU에서 실행됐다. float32 heatmap `(17,17,72,128)`과 validity·visibility `(17,17)`를 만들었고, 유효 채널은 119개이며 나머지 170개는 0 heatmap과 별도 missing 상태를 보존했다. [실행 결과와 tensor 해시](../experiments/B-006-motion-representation/heatmap_report.json)에 기록했다. 이 구현은 heatmap 격자에서 σ=2 cells를 사용한다. 앞 절의 작은 교육용 예제는 원본 픽셀 단위 σ=4와 더 작은 격자를 사용하므로 별도 예제다. 두 실행 모두 영상 생성 모델이나 학습 실행이 아니다.

B-006의 새 diffusion 생성·학습은 0회다. 17프레임·24fps 비교 영상은 0.708333초이며, 실제 연속 재생을 관찰하지 않아 시간 품질은 UNVERIFIED다. Lab 안무·개체 수용을 성공으로 표시하지 않는다.

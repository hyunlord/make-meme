# B-016 — animation에서 reference RoPE H만 변경하는 제한 pilot

작성: 2026-10-24 · parent: B-013/B-015 · 상태: **PLANNED / NOT_RUN**.
이 문서 게시 자체는 GPU 실행·새 예산 사용이 아니다. 사용자가 실행 담당자에게 수행을 지시하면 아래 범위를 적용한다.

## 1. 목표·결정 근거·검토 범위

B-015 기준 commit `ad213e8b97230b253ec9b797ce97c599762f6ecf`의 RESULTS를 확인했다. 기록상 CFG/ALG × MOV/STILL 네 셀 모두 전신 직립·앞발 전이는 실패했고, 심한 후기 얼굴 손상은 두 MOV에서 나타났다. 두 STILL의 정적 외형 보존을 동작 성공으로 올리지 않는다. 현재 ratio0.4/초기20% ALG pilot은 종료하며 기본 경로로 채택하지 않는다. 이번 B-016은 **ALG OFF, 기존 CFG**로 돌아간다.

다음 질문은 고정 Lab 참조와 같은 driving에서 **reference token의 RoPE 높이 좌표만0→120으로 바꾸면** 전신 자세 고정, 후반 국소 반응과 얼굴 손상이 어떻게 달라지는가다. 사진이나 latent 내용을 옮기거나 흐리는 실험이 아니다. 기존 frozen 모델의 위치 조건화 개입이며 신규 아키텍처·학습 방법의 독창성을 주장하지 않는다.

이번 검토에서 업로드 ZIP의 정확한 경로로 container와 Python을 각각 시도했으나 ClientError로 읽지 못했다. 보고된 199,344,328bytes/471payload/CRC/Mac·Spark 일치와 SHA `83b549bbed45f93156245bb7d1377df2ab377aa15d4e37916f7843b08b0c314b`는 독립 검증값이 아니다. 원격 코드·문헌은 읽었지만 영상 재생·실물 해시·GPU 실행은 하지 않았다.

## 2. 원논문·고정 코드와 가설의 한계

- RoFormer: https://arxiv.org/abs/2104.09864 — Q/K에 위치별 회전을 적용해 상대 위치를 attention logit에 반영.
- SCAIL-2 §3.3/Table1: https://arxiv.org/html/2606.10804v1 — mask의 environment switch와 mode-specific RoPE를 함께 사용. 참조 위치 변경은 이미 이 모델의 설계 요소다.
- 고정 SCAIL commit `78fe19576bb06be96c2375e088574a262a300edb`, `wan/modules/model_scail2.py`: `rope_apply_ref`, `rope_apply_scail`, `WanSelfAttention.forward`, 최종 `rope_T/H/W_shift` 구성.

additional_ref=None인 현 구성의 실제 baseline:
- animation (`replace_flag=False`): reference T=0,H=0,W=0; generated T=1,H=0,W=0; driving T=1,H=0,W=120.
- 공식 replacement: reference H=120뿐 아니라 generated/driving T=0이며 입력·배경 mask 계약도 별도다.
- 이번 hybrid: **animation의 모든 계약을 유지하고 reference H만120**. 공식 replacement 전체를 재현하지 않으며 이 조합의 학습분포 적합성은 UNKNOWN이다. 120을 선택하는 이유는 공식 위치 인덱스에 이미 있는 값이어서이지 최적값이거나 안전한 성능을 보장해서가 아니다.

H120은120픽셀 이동이 아니다. 생성 latent H112,W64와 patch(1,2,2)라면 RoPE grid H56,W32이고, reference h 범위가0..55에서120..175로 바뀐다. 실제 config/shape로 재확인한다. T/W/frequencies/theta/sequence order/patch embeddings/V/CLIP·text cross attention/input tensors는 직접 수정하지 않는다.

한 높이 평면에서 q'_i=R(h_i)q_i, k'_j=R(h_j)k_j라면 score=q_i^T R(h_j-h_i)k_j/sqrt(d). ref 위치를 같이 Δ만큼 옮기면 **고정 Q/K에서 ref-ref pre-softmax dot product는 보존**, ref↔video 및 ref↔driving의 상대 위치항은 바뀐다. 이것은 softmax 확률·후속 hidden state 불변을 뜻하지 않는다. 다른 key logits가 바뀌면 정규화 분모도 바뀌고 다음 층의 Q/K도 달라진다. 위치를 멀리 둔다고 참조 영향이 단조 감소하거나 pose만 제거되는 것은 아니다. driving의 pooled complex RoPE는 그대로 둔다.

## 3. 재사용·단일 개입

대조군: **B-013 LAB_MOV (CFG, ref_H0)** 그대로 재사용. B-013 LAB_STILL과 B-014/015 ALG 결과는 맥락용이며 새 대조군 재생성 없음.
신규: **LAB_MOV_REF_H120 (CFG)** 최대1회.

기존 B-013 LAB_MOV의 `conditions.safetensors`·메타데이터·initial noise를 읽기 전용 재사용한다. 원본 캐시 SHA `b7e5c62d8cb3a67e3cca0e104a536cf54c86937fa136f8554dbe55062ba9bf5d`는 실제 파일·부모 기록과 확인한다. 캐시 전체16leaf의 값·shape·dtype·device 계약은 동일해야 한다. 이번 개입은 kwargs의 위치 지정이지 인코딩 텐서의 교체가 아니므로 과거4changed/12equal 검사를 그대로 강요하지 않는다.

고정: source f7..23, 실제 Lab RGB·RED/WHITE ref mask, 원본 RGB+mask MOV, Lab positive prompt와 empty negative, seed20261022 및 실제 noise/RNG, UniPC40/shift3/CFG5, history=None, additional_ref=None, replace_flag=False, W512/H896·17frames24fps, mixed precision/weights/FA/loader/가드 유지. ALG·LoRA·enhancer OFF. P 재실행0, mask/crop/prompt/사진 수정0.

## 4. 최소 구현과 CPU 계약

최대45분의 고정 코드 검토+소형 fixture 후 실제 한정 실행으로 연결한다. 새 attention 엔진·후크 프레임워크·기존 환경 전면 리팩터링 금지.

- 격리된 실험 코드에서 reference H override를 명시한다. 기본 None은 원래 모드별 값을 그대로 유지하고, 이번에는120만 사용한다. `replace_flag=True`로 대체하지 않는다.
- 기존 upstream 파일/가중치는 수정하지 않는다. 런타임이 실제 patched module을 import했는지 파일 경로 별칭·SHA·resolved 값으로 확인한다. module attributes/config 등록 때문에 checkpoint key·parameter 수가 바뀌지 않게 한다.
- `rope_H_shift['ref']`만 override하고 additional_ref=None을 assert한다. T/W/pose/video, additional-ref 관련 기본값은 건드리지 않는다. 동일 개입을 두 CFG branch와 모든 원래 self-attention block·40step에 적용. Q만이 아니라 공식 함수가 호출되는 Q/K 양쪽에 반영한다.
- 작은 random tensor CPU fixture에서 OFF/0이 기존 helper와 일치하는지, ref 외 token의 RoPE 출력이 그대로인지, ref Q/K norm·내부 상대 logit 보존(사전 tolerance), ref↔video/drive logit 변화, reference H 범위가 frequency table 안인지 확인한다.
- 검사는 **고정 synthetic Q/K에서의 성질**이다. 실제 full model attention 확률이나 후속 layer 출력을 불변이라고 요구하지 않는다. 실패를 숨기려고 테스트 삭제·dtype 변경·허용치 사후 완화하지 않는다.
- 실제12992token의 N×N attention map을 저장하거나 FlashAttention을 dense attention으로 바꾸지 않는다. 작은 helper 검사로 충분하며 실제 trace는 첫/마지막 step과 block별 해석된 위치값·token range 정도만 남긴다. 관측용 추가 DiT forward 없음.
- ALG 코드에서 시작해88회 검증을 무조건 지우지 않는다. 기존 CFG 경로로 되돌아가 실제 기대40step·80forward 검증을 유지한다. baseline strict load keys/condition hashes 확인은 기존 검사 재사용.

## 5. 예산·실제 실행

총 작업 상한3시간. PROBE 최대1, 신규 full sampler S 실패 포함 최대1, 해당 final latent의 D 최대1, 자동 재시도0. P0, 모델·데이터 다운로드0, 학습/LoRA0, imagegen/외부API0. 기존 A와 B 결과·가중치·타 서비스 보존. 기존72GiB 시작/24GiB 실행 headroom·swap0·순차 worker·tinyCUDA/anchor 정책을 유지하고 driver/sudo/swap/clock/drop_caches/다른 프로세스 종료/가드 완화 금지.

CPU 계약·입력 불변 확인이 통과하면 모델을 적재하고 같은 CFG80forward로 실행한다. 비교를 위해 sample_steps/seed/shift/precision을 바꾸지 않는다. 최종 latent를 S 종료 전에 원자 저장·finite·재읽기 검증하고 자원 회복 후 D에서 decode한다. D 실패로 sampler 재실행 금지. frame duplication/보간/업스케일/warp/얼굴복원·first-frame clamp 없음.

## 6. 사전 평가와 중단 후 해석

SOURCE / 실제 Lab reference / B013 CFG_MOV_H0 / 신규 CFG_MOV_H120을 같은17장·24fps·canvas에서 비교한다. 기존 local0/12/14/16 사건과 전체17장을 사용하며 사후 정렬·좋은 프레임 선별 금지. 기존 STILL은 맥락으로만 보존한다.

분리 평가:
1. 전신 직립·들린 앞발 vs 착석·지지 앞발.
2. 후반 머리 roll의 원본 방향·순서·형상 충실도.
3. 눈·주둥이·귀·목·가슴·사지의 보존, 단순 검은 Lab 견종 유사성과 실제 개체 구분.
4. 원본의 가는 몸·옅은 털 누수, reference 배경/카메라 변화 및 mask 경계. 배경이 바뀌면 의도치 않은 task cue 영향으로 기록하고 모드가 바뀐 성공으로 해석하지 않는다.
5. 시간 품질은 실제 연속 시청 없으면 UNVERIFIED. 모든 정적 판정·불확실성·관측자 편향을 그대로 남긴다.

직립만 나오고 얼굴/체형이 원본 개체로 바뀌면 목표 성공이 아니다. 얼굴이 깨끗해졌지만 동작이 없어졌다면 동작 품질 개선이 아니다. 큰 변화나 반복 위치 이동만으로 spatial correspondence 가설이 증명됐다고 하지 않는다.

실패 시: 이 hybrid 설정이 충분하지 않다는 결론이며 공간 조건 무관/학습으로 불가능이라는 결론이 아니다. 성공 시: 이 입력에서 위치 개입의 유망한 pilot이며 새로운 방법·일반화·1티어 논문 성능이 아니다. 필요하면 다음에 matched STILL 또는 미사용 사례 중 정보가치 높은 **한 실험**만 제안한다. 이번에 offset sweep/새seed/ALG 결합·학습을 자동 시작하지 않는다. 효과가 없으면 무제한 scalar 탐색 대신 데이터·reference와 pose 분리·학습 개입 가설로 우선순위를 재평가한다.

## 7. 공부·GitHub·완료 산출물

한국어 `lessons/B-016-rope-and-spatial-conditioning.md`: RoPE rotation과 QK 상대 위치 유도,3D T/H/W 분할, latent/patch/pixel 좌표 차이, self-attention과 CLIP cross-attention 구분, score invariance와 softmax normalization 차이, mode-specific RoPE와 hybrid의 분포 위험. 직관→수식/가정→고정 코드/shape→CPU 확인→실제 관측→반례→질문3개와 별도 해설을 연결한다. 단순 h변경이 이미지 warp·pose retarget·학습된 disentanglement가 아님을 명시한다.

실행 전 CHARTER/ROADMAP/HISTORY/RECORDING_PROTOCOL과 B013/B015 결과를 읽고, 본 PLAN/실행 코드·config·budget을 고정한다. HISTORY/ROADMAP에는 ALG pilot 종료와 RoPE pilot 질문·실제 상태를 짧게 연결한다. 종료 후 RESULTS·재현·이론·비민감 코드·측정/실패를 명시 stage, commit/push·remote SHA 확인. main/force push/reset/clean/자동merge 금지. 기존 검증된 환경의 대형 감사를 반복하지 않는다.

개인 영상·사진·mask·coords·condition cache·latent·weights·private path/token은 공개하지 않는다. local /tmp/ 검토 ZIP에 실제 영상/raw/final latent(생성됐으면)·전체 비교·실측·재현·실패·원본 계보를 보존하고 거대 weights는 제외한다. Mac/Spark 전송 여부·CRC·manifest/hash·자체 process 종료를 실제 확인해 보고한다. 파일 생성/코드 검사 통과와 영상 품질 수용은 분리한다.

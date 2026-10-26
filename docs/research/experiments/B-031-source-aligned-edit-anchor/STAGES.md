# B-031 단계 분리와 영상 전이 계약

상태: **영상 실행 전 준비 / GPU 영상 0**. 이미지 앵커 성공과 영상 성공은 별도 판정이다. 이 문서는 생성 전 고정된 영상 경로이며 실제 실행 여부는 종료 RESULTS/실행 장부를 따른다.

## 단계와 수명

1. Qwen의 여섯 이미지 시도를 종료하고 모델 프로세스가 실제로 종료됐는지 확인한다.
2. 각 task의 사전 지정 R1만 검토한다. 적합하지 않으면 `ANCHOR_UNSUITABLE`; R2로 바꾸지 않는다.
3. A0의 실제 target support를 제한된 CPU/수동 polygon으로 확인한다. 원본 mask를 다른 체형에 그대로 적용하지 않는다. RGB 안쪽은 그대로 두고 밖을128, semantic mask는RED/BLACK으로 만든다.
4. `ENC`: 기존 B027 R1 CPU cache를 읽는다. 새 reference만 공식 VAE와 CLIP에 각각1회 넣는다. VAE를 해제한 뒤 CLIP을 올린다. 공식 mask helper로 reference prefix만 새로 만든다. T5·driving·학습 target·prefix·DiT는 인스턴스화/재계산하지 않는다.
5. ENC 종료·자원 회복 후 `R1_PROBE`: tiny CUDA와 원래 device별16leaf 복원을 확인한다.
6. PROBE 종료 후 `R1_S`: 기존 mixed loader, tiny CUDA/anchor, 공식 replacement forward, UniPC40/shift3/CFG5를 사용한다. 실제40step·80forward를 확인하고 최종 x0를 원자 저장한다.
7. S 종료·자원 회복 후 `R1_D`: VAE만 올려 최종 x0를 한 번 decode하고17프레임·896×512·preview24fps MP4를 저장한다. 실패하면 latent를 보존하고 재샘플링하지 않는다.

영상은 task별 최대1회이며 이미지 모델과 SCAIL은 동시에 상주하지 않는다. 자체 unit 이름은 B031 전용이며 기존 서비스는 관측만 한다. 기존72GiB 시작/24GiB 실행 headroom·swap0를 유지한다. GPU 단계 cutoff는 UTC20:16:41이고 전체 hard deadline UTC20:46:41 이전 마지막30분은 보존·검증·전송용이다.

## 바뀌는 조건과 고정 조건

| 항목 | 처리 |
|---|---|
| 양 CFG CLIP `t2/t8` | 같은 R_star RGB의 새 CLIP |
| 양 CFG reference VAE `t3/t9` | 같은 R_star RGB의 새 VAE |
| 양 CFG reference masks `t4/t10` | 새 support의 공식28채널 prefix; 나머지 time slice는 부모에서 유지 |
| noise `t0`, text `t1/t7`, driving `t5/t11`, driving mask `t6/t12`, RNG `t13`, timestep `t14`, sigma `t15` | B027 해당 R1과 실제값/hash 불변 |
|16leaf 구조·shape·dtype·원래 device | 그대로 유지 |
|replacement / history / additional reference |True / None / None |
|LoRA / ALG / B029 gate / 수동 RoPE |모두OFF |

여섯 reference leaf는 **허용 변경 집합**이다. support가 우연히 같을 때 마스크까지 반드시 달라야 한다고 요구하지 않는다. 반면 나머지10개는 정확히 유지한다. 원래 producer provenance를 보존하고 `anchor_derivation`에 새 reference·mask·builder·부모cache 해시를 추가한다.

영상 첫 프레임 overwrite/hard clamp/history 주입은 없다. 조건 참조 A0의 자세가 실제 생성frame0과 같아야 한다는 강제식도 없다. 공식 replacement의 RoPE는 모델이 선택하며 hybrid override를 넣지 않는다.

## 실제 준비 검증

- 원격 기존 B027 animal/human/vehicle R1 receipt와16leaf·noise를 CPU로 읽고 확인했다. 이 검사에서 `torch.cuda.is_initialized=False`였다.
- noise `[16,5,64,112]`, reference `[16,1,64,112]`, CLIP `[1,257,1280]`를 기존 metadata에서 확인했다. 새 encoder/forward의 실측이 아니다.
- CPU4검사: 허용6leaf, 우연히같은mask, 금지driving변경, 금지reference dtype변경. Mac와 기존 Spark Python에서 PASS.
- Python compile과 shell syntax PASS. ruff/basedpyright 실행파일이 로컬에 없어 타입/린트 전체는 `NOT_RUN/NOT_CLEAN`으로 남긴다. 검사 억제나 새 설치는 하지 않는다.
- 신규영상·조건인코딩·모델로딩은 이 문서 작성시0이다. fixture 통과는 실제영상 성공을 뜻하지 않는다.

## 실제 함수

`video_code/prepare_video.py`는 적합성/모델종료 receipt, RGB128/RED-BLACK, 기존 driving bytes와 부모계보를 고정한다. `phase_reference.py`는 한 reference를 VAE/CLIP/semantic mask에 넣는다. `anchor_contract.py`와 `contracts.py`가10leaf불변·부모receipt·구조/device를 확인한다. `phase_sample.py`의 첫 실제 두 CFG forward hook은 동일복원객체와조건hash만 기록하며 추가forward는0이다. `extract.py`/`staged_loader.py`/`phase_decode.py`는 B030의 기존 실행경로를 보존했다.

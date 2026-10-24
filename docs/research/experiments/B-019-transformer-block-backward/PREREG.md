# B-019 실행 사전 계약

분류: SYNTHETIC_BLOCK_CONTRACT_TEST. 실제 영상·FM target·동물 데이터를 사용하지 않는다.

- B-018 실제 x BF16/target FP32 `[1,36,5120]` 파일을 재사용하고 payload SHA를 확인한다. 초기 adapter A/B도 그대로 재사용하며 Bzero를 확인한다. final adapter를 읽어 이어학습하지 않는다.
- 별도 CPU generator seed20261025. context는 FP32 정규분포에서 BF16으로 cast한 `[1,769,5120]`, 앞257 image/뒤512 text다. e는 FP32 uniform[-0.05,0.05] `[1,6,5120]`이며 입력 gate 성분2·5를1로 고정한다. learned modulation은 변경하지 않는다. 생성한 작은 파일·hash를 GPU 전에 고정한다.
- x와 context의 gradient를 허용해 입력 gradient 및 image/text K/V 경로를 검사한다. 학습 parameter는 self_attn.q/v rank4·alpha4 LoRA81,920개뿐이다. context는 optimizer 대상이 아니다.
- 공식 전체 block·FP32 norm/modulation·BF16 Linear·RoPE animation H0를 유지한다. 소형 ref16/generated16/driving4, 긴 ref1792/generated8960/driving2240이며 driving W120은 기존 위치 규약이다.
- block 최종 출력의 FP32 MSE, AdamW lr1e-4/wd0, 최대3update. Bzero/reload/OFF tolerance atol=rtol1e-3. 실제 오차를 남기고 수용값을 결과 후 조정하지 않는다.
- 소형8block forward/3backward/3update. 소형 저장 성공 및 메모리 회복 뒤 조건부 긴1forward/1backward/update0. 내부 FA 호출 수와 block 호출 수를 구분한다.
- 긴 입력은 seed20261026의 synthetic tensor `[1,12992,5120]`, T5/H56/W32다. 앞39층 activation 또는 실제 영상 데이터가 아니다. 긴 tensor는 ZIP에 넣지 않는다.
- worker1회·재시도0, cap16GiB/high14GiB, 시작 MemAvailable72GiB·실행24GiB headroom·swap0·타 서비스 보호. 종료10:37:58UTC 이전. cap 확대·길이 탐색·다른 backend·checkpointing 추가0.
- 긴 단계는 optimizer/이전 graph/불필요한 출력·복사본을 해제한 상태로만 수행한다. 사전 메모리 산술은 보장 상한이 아니며 실제 가드와 allocator 관측을 함께 사용한다.
- 각 branch output의 hook은 finite/norm scalar만 보존하고 graph를 모으지 않는다. residual 우회만으로 frozen cross/FFN 경로가 검증됐다고 하지 않는다.

실제 선택키·입력·코드 hash는 실행 전 함께 고정한다. B-017 DATA_PENDING, FULL_MODEL_TRAINING/VIDEO_QUALITY/IDENTITY_POSE_DISENTANGLEMENT NOT_RUN은 유지한다.

## 실제 checkpoint header

`blocks.39.` 전체32개 tensor, 원본FP32 payload **1,615,353,856bytes**, 기반 parameter403,838,464개를 확인했다. affine norm3와 learned modulation도 포함된다. B-018 self-attention10개와 달리 실제 전체 block 범위이며, 전체 checkpoint를 로딩한 값이 아니다. runtime cast는 실제 Linear와 FP32 island를 구분한다.

## 실행 직전 검사

CPU combined18PASS, critical Ruff PASS. Runner type0errors/145warnings로 NOT_CLEAN이다. 동적 upstream/JSON/PyTorch 경계 경고를 숨기지 않았고 실제 tensor/optimizer 연결 오류는 수정했다. 정확한 파일 hash는 CODE_FREEZE.json, 입력 파일·payload hash는 configs/fixtures.json에 고정했다. 실제 worker deadline은 전체 한도보다 엄격한10:30UTC이며, worker runtime도1800초 이내다. GPU worker는 아직0회다.

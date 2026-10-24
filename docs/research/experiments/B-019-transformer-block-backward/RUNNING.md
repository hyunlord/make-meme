# B-019 실행 기록

- 시작 HEAD `a930e137e3301fa3b3f748e8e3942a54f492c290`.
- 시작 UTC08:37:58, 절대 종료10:37:58 (2026-10-24).
- 현재 CPU 계약·공식 전체 block·선택 tensor header 확인. GPU0/1.
- B-018 x/target 실제 payload와 initial Bzero adapter를 재사용한다. final adapter 이어학습0.
- 소형8forward/3backward/3update 후 conditional long1forward/1backward/update0. 실패/재시도 경계는 PLAN 그대로다.
- 실데이터·권한 DATA_PENDING과 FULL_MODEL_TRAINING/VIDEO_QUALITY/IDENTITY_POSE_DISENTANGLEMENT NOT_RUN을 유지한다.

공식 `WanAttentionBlock.forward`는 self-attention 뒤 gated residual, image/text cross-attention residual, modulated FFN gated residual 순서다. 최종 loss에서 각 내부 경로로 전달되는 scalar gradient 요약을 검사해 residual 우회와 구별한다. 실제 source를 바꾸거나 frozen 연산을 no_grad로 제거하지 않는다.

## 08:50–08:51UTC 실제 실행 종료

사전 등록26c0856 이후 worker1회. 소형8forward/3backward/3update와 긴1forward/1backward/update0 통과. 작은 결과/adapter를 먼저 저장하고 긴 단계로 진행했다. 재시도·추가worker0. owned unit inactive와 보호 서비스 보존 확인. 결과·실측·해설·포장을 마무리하며 추가 실험은 시작하지 않는다.

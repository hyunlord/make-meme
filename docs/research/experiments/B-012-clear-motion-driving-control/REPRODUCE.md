# B-012 재현 계약

현재 source 선정·실제 실행 근거를 기다리는 초안이다. 새 생성·품질 결과를 완료했다고 주장하지 않는다. [PLAN](PLAN.md)의 MOV/STILL 각각 1회, 실패 포함 full sampler 최대 2회·retry 0 경계를 유지한다. B-011 사용1회와 B-010 사용0회는 보존한다.

## 입력 고정

기존 원본에서 최대 3개의 연속 17프레임 후보를 source-only로 검토하고 최초 적합 구간을 고정한다. 선택 구간과 최소 세 시점의 관측 이벤트는 실제 선정 기록으로 채운다. 아직 특정 프레임이나 동작을 추정하지 않는다. 512×896·24fps·동일 crop을 유지하며, reference는 선택 구간 첫 processed RGB다.

MOV는 실제 17장 RGB+대응 mask, STILL은 RGB f0+mask f0의 17장 반복이다. STATIC COPY는 생성 없이 f0를 반복한 별도 출력이다. reference mask는 동일 f0 RED support+WHITE 배경이고 prompt도 두 조건에 동일하다. 같은 source 개체를 묘사하며 과거 Lab prompt/cache를 재사용하지 않는다.

## 조건·실행 검사

seed20261022·UniPC40·shift3·CFG5·negative empty·replace_flag=False·history=None·LoRA/enhancer OFF, 기존 pinned SCAIL/weights/FlashAttention/mixed loader/64-byte CUDA anchor 경로를 유지한다. 조건별 새 P가 실제 17장 영상을 encode한다. STILL latent를 MOV 첫 slice 반복으로 만들지 않는다.

양 CFG의 pose_latents/driving_masks 4leaf는 변경 기대, 나머지 12leaf는 보존 계약이다. 실제 noise bytes/shape·RNG·timesteps/sigmas를 비교한다. float tolerance와 exact 정책을 사전 고정하고 observed exact 여부도 기록한다. 조건 비교 실패는 sampler 전에 중단한다. 출력 품질이 나쁘다는 이유로 안전한 둘째 대조군을 생략하거나 추가 retry하지 않는다.

조건마다 P→조건 비교→PROBE→S→D의 기존 분리 경로를 사용하며 GPU-heavy 실행은 순차다. final latent 저장·재로딩 검증과 S 종료·자원 회복 뒤 D를 실행한다. D 실패가 S 재실행 권한이 되지 않는다. 구체적인 stage 경로·고정 코드·실제 명령·deadline은 runtime 기록이 준비된 뒤 연결한다. 현재 명령 실행 이력을 지어내지 않는다.

## 평가·종료

SOURCE / STATIC COPY / MOV / STILL의 17장 전체와 사전 이벤트를 같은 24fps로 비교한다. 움직임 양이 아닌 source 대응을 보고 부위 관측 불확실성·coverage를 유지한다. 출력별 warp·zoom 보정·시간 이동·보간은 없다. 실제 연속 시청이 없으면 temporal UNVERIFIED다.

실제 결과·hash·자원·소유 프로세스 종료는 완료 receipt로 확인한다. 공개에는 비민감 코드·집계·자산 별칭만 남기고 실제 원본·mask·조건cache·latent·개인 경로는 공개하지 않는다. [학습 문서](../../lessons/B-012-driving-information.md)는 STATIC COPY와 STILL, 시간 압축 및 공동 driving 개입의 의미를 설명한다. 이 문서는 추가 생성이나 다음 실험의 자동 실행 승인이 아니다.

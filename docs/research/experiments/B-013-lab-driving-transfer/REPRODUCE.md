# B-013 재현 계약

현재 신규 생성 결과는 **NOT_RUN**이다. [PLAN](PLAN.md)에 따라 LAB_MOV/LAB_STILL 각 sampler1회·실패 포함 총2회·retry0만 사용한다. B-012 MOV/STILL은 기존 결과 그대로 재사용하며 재생성하지 않는다.

## 입력과 실행 통제

B-012 실제 processed source index7~23 및 mask를 해시 검증 후 그대로 사용한다. LAB_STILL은 대응 B-012 STILL과 동일한 RGB/mask f0 반복 비디오다. 새 decode나 다른 고해상도 파일로 교체하지 않는다. reference는 기존 실제 Lab 사진, mask는 B-009 RED foreground+WHITE background다. 새 mask 개선·배경 삭제·시각 생성은 없다.

두 Lab 조건의 text/reference/noise/scheduler는 동일하다. source→Lab prompt 변화는 사전 diff와 실제 T5 길이로 남긴다. Lab 내부 4변경/12보존, B-012 대비 reference/task7변경 및 대응 control 검증을 구분한다. key 번호보다 실제 tree location을 따른다.

512×896·17장·24fps·seed20261022·UniPC40·shift3·CFG5·negative empty·replace_flag=False·history=None·LoRA/enhancer OFF다. 기존 mixed loader/FlashAttention/tiny64-byte anchor/P→PROBE→S→D 경로를 유지한다. STILL도 RGB를 실제 VAE encode하고 latent 첫 slice를 반복하지 않는다. 새 P cache가 필요하다. 각 S의 최종 latent 저장·finite·재읽기 검증과 종료 후 D에서 decode한다.

전체 deadline은 시작부터4시간, 이번 작업은19:43 UTC까지다. 정확한 worker deadline·명령·hash·실측은 고정 runtime 근거가 준비되면 기록한다. 실행하지 않은 단계를 수행 이력으로 쓰지 않는다.

## 읽기 전용 비교와 판정

SOURCE와 실제 Lab reference, 기존 B-012 MOV/STILL, 새 LAB_MOV/LAB_STILL을 같은 canvas로 표시한다. raw 전체17장 및 local0/12/14/16 이벤트를 보존하고 24fps 시간축을 바꾸지 않는다. 좋은 프레임 선별·피사체별 확대·warp·보간·얼굴 복원은 없다. 비교 도구는 기존 CPU review UI를 최소 재사용하며 frozen runtime과 분리한다.

전신 직립/앞발 배치와 몸통 대비 국소 머리 roll을 따로 평가한다. 착석 유지 중 국소 제어가 관측돼도 전체 목표 성공으로 승격하지 않는다. Lab 유사성과 실제 개체 일치를 구분하며 숨은 부위·접촉은 UNKNOWN일 수 있다. UI 기능/ffmpeg decode PASS가 시간 품질 수용은 아니고, 실제 연속 검토가 없으면 UNVERIFIED다.

실제 code/input/condition/output hash와 자체 프로세스 종료는 완료 receipt로 확인한다. 개인 영상·사진·mask·좌표·경로는 공개하지 않는다. 수학과 코드 연결은 [학습 문서](../../lessons/B-013-cross-identity-driving.md)에 있다.

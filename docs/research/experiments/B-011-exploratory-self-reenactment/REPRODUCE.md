# B-011 재현 계약

현재 GPU 실행과 생성 결과는 **NOT_RUN**이다. [PLAN](PLAN.md)과 [RUNNING](RUNNING.md)의 새 B-011 범위만 사용한다. B-010은 DIAGNOSTIC_INSUFFICIENT, P/PROBE/S/D 각 0회 상태로 보존한다. 아래는 실행 예정 계약이며 수행 이력이 아니다.

## 입력과 불변 조건

B-010에서 준비한 processed source f0 RGB, 동일 RED support+WHITE background reference mask를 사용한다. driving 17프레임과 mask는 B-009/B-010 그대로다. 512×896·24fps·seed 20261022·UniPC 40step·shift 3·CFG 5·empty negative·replace_flag=False·history=None·LoRA/enhancer OFF다. positive는 PLAN에 명시된 문장을 그대로 사용한다.

원본 512×288의 기존 확대·crop을 유지한다. 더 좋은 입력이나 seed를 찾지 않는다. STATIC COPY는 f0의 CPU 반복 대조군이며 생성물로 보고하지 않는다. 공개 설정은 자산 별칭과 해시만 사용하고 실제 경로·원본·mask·좌표는 비공개로 보관한다.

## 순서와 판정

1. 최대 30분 source-only 관측에서 실제 화면상 변화와 평가 가능한 항목을 고정한다. 보수적 반경과 반복 판독 차이는 별도다. 부위 상대 운동 불확실성만으로 탐색 A를 일괄 차단하지 않는다.
2. 실행 코드·입력·관측 계약을 사전 고정한다. 새 P에서 B-009 대비 7leaf 변경/9leaf 보존을 실제 비교한다. 기존 tolerance/exact 정책을 유지한다.
3. P 종료와 자원 회복 후 PROBE, S, D를 각각 최대 한 번 실행한다. full sampler 실패도 한 번이며 재시도는 없다. S의 최종 latent 저장·재로딩 검증과 종료 후에 D를 실행한다.
4. source / STATIC COPY / raw output 전체 17장을 같은 좌표·24fps에서 비교한다. 원본 위치 정합을 바꾸는 warp·시간 재정렬·보간을 넣지 않는다.

실제 launch 명령·실행 commit·stage receipt는 runtime 고정 후 이 문서에 연결한다. 현재 명령을 실행했다고 주장하지 않는다. 전체 deadline은 2026-10-23 09:21 UTC, worker는 보수적으로 09:15 UTC를 사용한다. 종료 후 재현 명령이 남아도 추가 실행 승인이 되지 않는다. 기존 headroom·swap0·다른 작업 보호를 유지한다.

## 제출 판정

실행 완료와 화면상 변화 A, 부위 상대 운동 B, 외형 및 관측 불확실성을 분리한다. 실제 출력이 없으면 품질 NOT_RUN, 연속 재생을 보지 못하면 temporal UNVERIFIED다. Lab·cross-identity·전체 춤·Kling 수용은 이번에 수행하지 않는다. 수식과 측정의 의미는 [학습 문서](../../lessons/B-011-measurement-and-generative-diagnostics.md)에 정리한다.

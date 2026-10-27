# 검사 범위

이번 변경은 한정 정책과 supervisor 연결이다. 기존 bootstrap은 byte-identical이며 모델·sampling·decode 계산은 바꾸지 않았다. 새 정책 CPU 검사는 부재 승인, 서비스/listener 존재, 외부 GPU, 관측 오류, 비ECONNREFUSED, null queue, 실행 중 재등장, 메모리 위반과 중복 worker를 다룬다. 정확한 최종 수와 코드 해시는 CPU_REPORT/CODE_FREEZE에 고정한다.

독립 읽기 전용 검토에서 preflight/supervisor의 공통 정책 사용, 기존 종료 신원 검증, 과거 allowlist 보존, 임의 PID 허용 없음, 사전3표본과 실행중감시를 확인했다. unit이 없는 CPU worker도 별도로 감지하고, 현재 supervisor를 worker로 오인하지 않는 좁은 검사다.

Spark의 실제 worker --preflight-only는 기존 Python으로 실행하며 torch/model을 import하지 않는다. loader.json/worker-attempt도 만들지 않는다. 이는 CPU 실행 계약 증거이며 모델 forward/영상 품질 성공과 다르다.

Mac py_compile 및 whitespace 검사는 통과했다. ruff/basedpyright는 설치되어 있지 않아 NOT_RUN이며 새 패키지를 설치하지 않는다. 저장소 전체 타입 정리나 경고 억제를 수행하지 않았다. 기존24 fixture는 보존하며 새 검사 수에 포함하지 않는다.

시간차 관측은 완전한 원자적 독점이 아니다. 비차단 연구 잠금은 이 실행 경로의 중복을 막는 범위이며 다른 프로그램을 통제하지 않는다. 서비스·외부GPU가 새로 나타나면 자체 worker를 중단하는 감시를 유지한다.

## 실제 시작 관측

최종 focused CPU13개와 Spark S/D preflight는 PASS했다. 실제 supervisor 첫 표본은 서비스 EXPECTED_ABSENT_OBSERVED였으나 외부GPU1개로 UNKNOWN_GPU_PID/반환2다. worker 미생성, own unit inactive/not-found. GPU 연산과 영상 품질은 NOT_RUN이며 runtime 서비스 재등장 검사는 fixture 범위다.

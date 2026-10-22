# B-007E 실행 기록

시작 2026-10-22 13:49 UTC, 전체 hard deadline18:49 UTC. 시작 원격 HEAD `260ab8cbe140c27d46575a63ddc83779239c05aa`. 기존 별도 문서 checkout을 fast-forward했고 A checkout과 모든 기존 결과는 보존했다.

실행 순서: 원본·환경·입력 확인 → 공식 로더의 중복 메모리 감사 → 소형 meta/BF16 loader fixture → 실제 코드·config·입력 hash 사전 등록 → guarded 실제 모델 로딩 → 가능한 공식17f/Lab17f 각1회 → 결과·수학·장부 → GitHub/비공개 ZIP 검증.

동시 무거운 GPU 작업1개, 실제 loading path 최대2, 전체 sampler 최대2(실패 포함), 모델 다운로드·학습0. 메모리 가드와 기존 서비스 비간섭을 우선한다. 모델 로딩·첫 forward·전체 MP4·개체/동작/시간 품질을 각각 구분한다.

원래 FP32 safetensors를 보존하며 streaming BF16 cast가 사용되면 rounding과 실제 변경점을 명시한다. 소형 fixture를 전체 모델 fit 증거로 취급하지 않는다. 공식 예제와 Lab 색상 ID는 각각 실제 입력의 대응 관계를 사용한다.

## 실행 전 고정

13:53 UTC 변환본·T5·CLIP·VAE fresh SHA 확인. 입력8개와 FA binary/환경은 PREREGISTERED_INPUTS.json에 고정. meta/strict assign loader tiny 실제 architecture7검사 통과, 초기 CPU import 실패도 보존. 64GiB cgroup/swap0와 durable watchdog의 실제 종료 sentinel은3.26초 후 childPID0을 확인했다. 이것은 전체 모델 적재 성공 증거가 아니다.

공식→Lab은 하나의 pipeline을 재사용하되 각 sampler는 별도 exclusive reservation을 남긴다. 공식 실행 실패 시 Lab를 자동 수행하지 않는다. 새/기존 미확인 GPU 작업 발견 시 자기 작업만 중단한다. declared mixed-BF16 경로1개만 실행하며 자동 fallback은 없다.

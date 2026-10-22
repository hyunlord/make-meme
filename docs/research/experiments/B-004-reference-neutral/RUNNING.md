# B-004 실행 기록

2026-10-22 02:28:07 UTC 시작, 04:28:07 UTC 종료 상한. 시작 원격 HEAD `b08f4a5a163bd0e8256a2c7491585dd9074cc2e9`. 사전 PLAN 유지.

## 생성 전

Spark 기존 격리 환경 재사용. MemAvailable 95,919,349,760 bytes, swap 0, GPU utilization 0%, 기존 ComfyUI queue empty. 다른 서비스 유지.

`reuse_audit.json`: 모델 9개와 upstream 5개 파일 재해시 일치. 두 seed의 source/Canny decoded pixels, mask, R-bg pad, 고정 설정, 실제 기존 noise와 CPU 재구성 noise 일치. 기존 VAE/text 실행 해시는 사후 새 실행과 비교하며 사전 재실행으로 가장하지 않는다.

R-gray 원본 1536×2048 RGB128, 동일 RGB decode/pad. 신규 전체 추론 2회 이내, seed별 1회, 실패도 소비. 학습 0, adapter null. 코드·설정·입력 해시를 이 커밋에 고정한 후 실행한다.

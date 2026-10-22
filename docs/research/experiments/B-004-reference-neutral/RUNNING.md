# B-004 실행 기록

2026-10-22 02:28:07 UTC 시작, 04:28:07 UTC 종료 상한. 시작 원격 HEAD `b08f4a5a163bd0e8256a2c7491585dd9074cc2e9`. 사전 PLAN 유지.

## 생성 전

Spark 기존 격리 환경 재사용. MemAvailable 95,919,349,760 bytes, swap 0, GPU utilization 0%, 기존 ComfyUI queue empty. 다른 서비스 유지.

`reuse_audit.json`: 모델 9개와 upstream 5개 파일 재해시 일치. 두 seed의 source/Canny decoded pixels, mask, R-bg pad, 고정 설정, 실제 기존 noise와 CPU 재구성 noise 일치. 기존 VAE/text 실행 해시는 사후 새 실행과 비교하며 사전 재실행으로 가장하지 않는다.

R-gray 원본 1536×2048 RGB128, 동일 RGB decode/pad. 신규 전체 추론 2회 이내, seed별 1회, 실패도 소비. 학습 0, adapter null. 코드·설정·입력 해시를 이 커밋에 고정한 후 실행한다.

## 첫 실행 완료

실행 고정 commit `eafa250e9d03818bf6b94e69f3d2ae657076ec98` 원격 확인 후 seed20261022 exit0. seed20261023 순차 실행. 첫 f8 정적 관찰은 착석 및 만화 같은 눈/입이지만 최종 판정은 전프레임 비교 뒤 기록한다. 추가 계획 변경 없음.

## 종료

신규2/2완료·실패0. pairednoise/text/inactive/reactive/mask 동일, reference prefix와 전체context 상이. 기존runtime동일. 전체17프레임 정적검토: gray22착석,gray23직립형태이나개체/안무미수용. 시간UNVERIFIED. 재시도/추가추론없음. 사후 validator의 scripts/ prefix 중복 경로만 호환 처리; 고정 실행코드불변.

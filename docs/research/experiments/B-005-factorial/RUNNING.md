# B-005 실행 기록

시작 2026-10-22 04:20:34 UTC, deadline 06:20:34 UTC. 문서 branch의 실제 시작 HEAD `582e67ca0b153b5d602b04587b9f57cd36ad3426`. 기존 worktree clean 확인 후 fast-forward만 수행했다. A와 기존 B 실행본은 보존한다.

## 사전 단계

CHARTER, ROADMAP, HISTORY, RECORDING_PROTOCOL, B-003/B-004 RESULTS와 B-005 PLAN을 읽었다. 기존6개 재사용의 실제 모델/입력/noise/실행 경로를 확인 중이다. 신규는 gray+null 두seed각1회,전체2회상한,학습0. 계획 변경 없음. 코드는 기존 실행/관측 경로를 최소 확장하며 새로운 생성 모델을 추가하지 않는다.

## 재사용 검사 완료 / 실행 고정

6개 기존결과 모두 fixed 설정·decoded source/condition/reference/mask·실제noise 및 등록script 무결성 일치. 모델9/upstream5파일재해시일치. MemAvailable약93.40GB,swap0,기존ComfyUIqueue0/0. 기존서비스중단없음. `reuse_audit.json` 참조. 코드/config/inputhash를 원격고정한 후 두run순차실행.

## 첫 신규 run 완료

실행 고정 `ac0ecbec709ac72a36668ed22f2d09a42577f257` 원격 확인 후 seed20261022를 실행해 exit0을 받았다. 첫 f8 정적 관찰은 검은 사족 개이며 원본의 직립 자세와 다르다. 이 한 프레임으로 전체 시간 품질을 판정하지 않는다. seed20261023을 순차 실행했다. 설정·예산 변경과 재시도 없음.

## 비교 종료

신규2/2완료,실패0,기존6재사용. 전체8셀factorial tensor통제통과. 새두결과는모든17프레임사족형태; 전체8개jointidentity+source춤미수용. 시간UNVERIFIED. 검증기fixture는noise/ref/reactive불일치를검출했다. 추가추론/학습없음. 연구방향은반복제거대신명시적동물움직임표현검증하나만제안.

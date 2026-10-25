# B-027 실행 고정

2026-10-26 KST. 입력 후보 검토와 공개3task/6reference를 생성 전에 고정했다. [CASES](CASES.md), [selection](selection.json), [입력·코드 해시](INPUT_MANIFEST.json), [다운로드](DOWNLOAD.json).

최대6sampler, case별1회, 각40step80forward·decode1; 자동재시도0. 최초시각2026-10-25T15:11Z 기준 deadline23:11Z(8h). 공개데이터832766765bytes, 새모델/패키지/학습0. 개인 입력/조건 cache를 사용하지 않는다.

세 task의 실제 CPU decode/resize/normalization검사와8개CPU계약검사를 통과했다. source/targetGT마스크 입력은 mask-given이다. 기존 P/PROBE/S/D 계산과 가드를 유지하며 P는 새 공개입력만 인코딩한다. 각pair R1공통조건을 한 번 준비하고 R2 VAE/CLIP/refmask만 재계산한다. 16leaf중 reference관련 최대6leaf만 변경 허용, 나머지와noise/RNG/scheduler는 고정한다. 실제firstCFG에서 새참조계보를 확인한다.

기존loader/extract/probe/decode/storage는 B025와 byte-identical이다. 동적기존코드의 strict typing은 NOT_CLEAN, ruff/basedpyright는 기존환경에 없어 NOT_RUN이며 새설치하지 않았다. CPU PASS를 실제GPU/영상품질 PASS로 해석하지 않는다.

현재GPU NOT_RUN; 이 코드·입력 기록의 commit/push 이후 순차 실행한다. 첫출력의 품질만으로 paired대조군을 생략하지 않으며 실제입력/안전오류에는 중단한다. 모든latent는decode전에보존한다.

## 실행 시작 관측

사전 고정 commit `9a93aa09ed2032aebea3905e5b698388b65243c4`의 원격 일치를 확인한 뒤 실행했다. 첫 systemd launcher가 상대 경로로 호출되어 기본 cwd에서 guard 파일을 찾지 못했고, 이어 남은 실패 unit 때문에 두 번째 launcher가 거절됐다. 두 경우 모두 worker/encoder/model/sampler가 시작되지 않았다. 실패 receipt를 별도 보존하고 이 작업의 failed watchdog만 reset한 뒤 절대경로로 첫 ENC worker를 시작했다. 이는 sampler 재시도가 아니며 경로 오류 비용은 최종 COSTS에 포함한다. 다른 서비스를 중단하지 않았다.

ENC는 실제 완료했고 R1 PROBE도 통과했다. 최초 R1_PROBE launcher에 `PROBE`만 전달한 호출은 stage assertion에서 worker attempt 예약·CUDA 전에 거절됐다. 이를 별도 pre-worker 오류로 보존한 뒤 올바른 `R1_PROBE` 인자로 실행했다. sampler나 실제 CUDA 연산의 재시도가 아니다. 실제 S의 사용량은 각 exclusive attempt 및 최종 counter로 별도 확인한다.

선정 기록 해석: 초기 다운로드 receipt의 `candidate_count` 값은 열람 중간 집계였으며 private6/public7로 남아 있다. 최종 생성 전 선정의 정의와 수는 [selection.json](selection.json) 및 CASES의 입력묶음 기준12(선정9+제외3), 열람sequence7이다. 다운로드 receipt의 과거 숫자를 최종 후보12개 집계로 사용하지 않는다. 원본 receipt와 hash는 보존한다.

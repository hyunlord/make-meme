# B-027 실행 고정

2026-10-26 KST. 입력 후보 검토와 공개3task/6reference를 생성 전에 고정했다. [CASES](CASES.md), [selection](selection.json), [입력·코드 해시](INPUT_MANIFEST.json), [다운로드](DOWNLOAD.json).

최대6sampler, case별1회, 각40step80forward·decode1; 자동재시도0. 최초시각2026-10-25T15:11Z 기준 deadline23:11Z(8h). 공개데이터832766765bytes, 새모델/패키지/학습0. 개인 입력/조건 cache를 사용하지 않는다.

세 task의 실제 CPU decode/resize/normalization검사와8개CPU계약검사를 통과했다. source/targetGT마스크 입력은 mask-given이다. 기존 P/PROBE/S/D 계산과 가드를 유지하며 P는 새 공개입력만 인코딩한다. 각pair R1공통조건을 한 번 준비하고 R2 VAE/CLIP/refmask만 재계산한다. 16leaf중 reference관련 최대6leaf만 변경 허용, 나머지와noise/RNG/scheduler는 고정한다. 실제firstCFG에서 새참조계보를 확인한다.

기존loader/extract/probe/decode/storage는 B025와 byte-identical이다. 동적기존코드의 strict typing은 NOT_CLEAN, ruff/basedpyright는 기존환경에 없어 NOT_RUN이며 새설치하지 않았다. CPU PASS를 실제GPU/영상품질 PASS로 해석하지 않는다.

현재GPU NOT_RUN; 이 코드·입력 기록의 commit/push 이후 순차 실행한다. 첫출력의 품질만으로 paired대조군을 생략하지 않으며 실제입력/안전오류에는 중단한다. 모든latent는decode전에보존한다.

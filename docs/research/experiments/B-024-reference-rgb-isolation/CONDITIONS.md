# 조건 변경과 근거 수준

## 실제 관측

원래 전처리 reference PNG는 기존 normalized `img` tensor와 정확히 대응했다. 기존 RED support37,209pixel 내부 RGB는 pixel-exact 보존하며 나머지421,543pixel은 RGB128이다. semantic mask 파일은 B023과 동일하다. 따라서 bbox/면적/위치 변화가 없으며 새 분할이나 RGB warp는 없다.

원본 reference를 한 번 재인코딩한 VAE/CLIP는 이번 실행에서 각각 cached 값과 max_abs0/RMS0이었다. 이는 실측 결과이며 GPU재실행의보편적byte동일성을 요구하는 gate가 아니다. 기존ref와driverlatent를 각각 한 번 복원한 정적 시트에서 침실착석참조와 타일방사족driving을 구분했다. driving복원은448×256이다. source/ref교환·중복normalization·generatedoffset의 구체적결함은 발견하지못했으며 원인전부규명은아니다.

## 양 CFG cache

| 경로 | 변경 | 검증 |
|---|---|---|
| arg_c/arg_null clip_fea | 새 회색 RGB의CLIP | t2/t8 변경 |
| arg_c/arg_null ref_latents | 새 회색 RGB의VAE | t3/t9 변경 |
| context,ref_masks,pose_latents,driving_masks,noise,RNG,timesteps,sigmas | B023 재사용 | 나머지12leaf exact |
| device/container metadata | 보존 | 전체structure 동일 |
| mode | replacement=True | 양CFG 유지 |
| adapter/ALG/manualRoPE | OFF | 변경없음 |

새cacheSHA256 `1c8fc00620527f1fcddb7f380cd35ed70865ec4218420a85b7f6c21797496080`. 실제 leaf별 dtype/shape/hash는 비공개 `conditions.json`, 공개요약은[reference-encoding.json](reference-encoding.json)과[conditions-receipt.json](conditions-receipt.json)에 있다. 최초실제forward의객체동일성검사는verifiedrestoredcache의새ref/CLIP전달을확인하며관측용추가forward는없다.

## 소스에서 확인한 부분

공식VAE는CTHW입력과내부mean/std scaling을사용한다. 공식model은reference prefix1792token뒤generated8960token만unpatchify하고뒤drivingtoken을출력으로선택하지않는다. D는저장된finalx0를공식VAE에직접전달한다. 전체중간연산을runtime관측한것처럼주장하지않으며[CONNECTION_AUDIT](CONNECTION_AUDIT.md)의소스/실물근거를구분한다.

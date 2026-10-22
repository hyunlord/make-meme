# B-004 결과 — 회색 참조에서 직립은 한 seed에만 나타남

**COMPLETED: 신규 2/2, 실패 0, 기존 2개 재사용, 학습 0, adapter=null.** 통제 비교는 완료했지만 실제 Lab 동작 전이는 수용하지 않는다. 시간 품질은 **UNVERIFIED**다.

## 1. 조건별 관측

같은 C-real, prompt/negative, 512×288, 17프레임, 24fps, BF16 SDPA, 20 steps, CFG5를 유지했다. 기존 [PLAN](PLAN.md)은 수정하지 않았다. 17/24초(0.708333초) 영상이며 첫~끝 샘플 간격은16/24초다.

|seed|참조 / 실행|f0..16 자세|개체·형태·배경|원본 동작 수용|
|---|---|---|---|---|
|20261022|R-bg / B-003 재사용|착석 지속; 앞발 바닥, 뒷다리 벌어짐|검은 늘어진 귀, 강한 은색 흉부 하이라이트; 밝은 방과 왼쪽 문|FAIL: 직립 없음|
|20261022|R-gray / 신규1|착석 지속; 앞발 두 개 바닥, 뒷부분 낮음|흰 둥근 눈·벌린 입이 만화적, 털 디테일 감소; 과노출 방과 반사|FAIL: 직립 없음, 실제 Lab 외형 미수용|
|20261023|R-bg / B-003 재사용|착석 지속; 앞발 바닥|검은 개, 베이지 벽·흰 걸레받이; 비교적 좁은 몸통|FAIL: 직립 없음|
|20261023|R-gray / 신규2|뒷발 직립 형태 지속; 앞발 가슴 앞|어두운 실루엣, 옆을 보는 머리·가느다란 몸통·불명확한 앞발; 균일한 밝은 배경|미수용: 자세 범주는 가까워졌지만 개체·안무 일치 아님|

직접 정적으로 확인한 자료는 원본과 네 결과의 f0/4/8/12/16 비교, 네 결과 각각 모든17프레임 시트, gray23 f16 원본 해상도 및 실제 reference다. 원본은 두 뒷발로 선 다른 개체이며 Lab 정답 영상이 아니다.

R-gray23의 머리는 원본의 정면에 가까운 시점과 다르게 옆을 본다. 머리·몸통·발의 작은 변화는 보이지만 원본 춤 단계에 대응한다고 입증하지 못했다. 뒤로 갈수록 피사체가 커지고 아래로 내려와 마지막 프레임 발 일부가 하단에서 잘린다. 앞발과 어두운 몸통 내부의 구분도 부족하다. R-gray22는 귀·코·눈·입의 비사실적 모양이 두드러진다. 두 gray 결과 모두 실제 Lab의 넓은 가슴·얼굴·털 유지 성공으로 판정하지 않는다.

시트상 네 결과 모두 큰 자세 범주 변화가 없고 변화량이 작다. 모든 run의17 PNG는 서로 다르지만 이것은 자연스러운 움직임의 증거가 아니다. 평균 인접 RGB MAE(0..255)는 bg22=1.673, gray22=1.671, bg23=1.302, gray23=1.738이다. gray23의 최대8.308은f0→f1에서 발생한다. 배경·조명 변화도 포함하는 기술량이며 작은 점수가 좋은 시간 품질을 뜻하지 않는다. 실제 연속 재생은 관찰하지 못했으므로 떨림·정지감·전환 자연스러움은 **UNVERIFIED**다.

## 2. 재사용 및 실제 내부 조건

[reuse_audit.json](reuse_audit.json)에서 모델9파일·핵심upstream5파일의 fresh SHA, 두 기존 영상의 source/Canny decoded pixels, white mask, R-bg preprocessing, 설정 및 실제 초기 noise 일치를 확인한 뒤 실행했다. 모델 revision `574e6a744642ce3bee319afc31496b88bde8aac4`, upstream `f39d731a3e318d25b725eb3389cfddb184619842`. 전체 upstream tree 독립 해시 감사는 아니다.

실행 코드 고정·원격 확인 commit: `eafa250e9d03818bf6b94e69f3d2ae657076ec98`. [실제 실행 요약](run_summary.json)과 [runtime 비교](runtime_comparison.json):

|항목|실측 shape|R-bg 대 R-gray, 두 seed 각각|
|---|---|---|
|초기 noise|1×16×6×36×64|동일|
|positive/negative text|각1×512×4096|동일|
|inactive video latent|1×16×5×36×64|동일|
|reactive Canny latent|1×16×5×36×64|동일|
|mask 전체|1×64×6×36×64|동일|
|reference prefix|1×96×1×36×64|상이|
|DiT/VACE에 전달되는 전체 context|1×96×6×36×64|상이|

reference의16채널 latent는 prefix의 앞16채널이며 나머지는 zero padding이다. 코드상 RGB video는1×3×17×288×512, reference는1×3×1×288×512; gray reference 전처리는 Spark CPU에서 실제 같은 upstream 함수로 후속 확인했다. BF16 값은0.0078125였으며 GPU 전처리 tensor 직접 hook 실측이라고 주장하지 않는다. VAE latent와 sampler context는 실제 추론에서 관측했다.

R-gray raw PNG SHA `74fad0f371d7a3705a8653af44f6a0e6ef0bac4e4248353eb0f45f91a323119a`; 같은1536×2048 RGB decode 뒤512×288 pad, 한 장 reference 유지. ref=None으로 바꾸지 않았다. 전체 context SHA는 R-bg `48724efe2aee2ee9d0615cf8de0b83809e884b9b9895b0cbc1e2233c1f7bb735`, gray `6ec68d2ca166a874d8e2460a91bb0267687f7e20380e92083a6ed659209c032d`. 두 seed에서 각각 같은 reference context다. 전체 noise·slice 해시는 연결된JSON과 비공개 장부에 보존했다. source/Canny 및 R-bg 원본 파일 해시는 실행 이전부터 등록된 [B-003 input audit](../B-003-structure-condition/input_audit.json)에 있고, 이번 재사용 감사에서 실제 decode/전처리를 다시 대조했다. [회색 전처리 실측](gray_preprocessing.json)도 별도로 남겼다.

scheduler는 pinned 코드와 동일 호출 경로로 FlowMatchScheduler의 sigma_shift5, vace_scale1을 유지했다. tiled=True, tile_size(30,52), stride(15,26), cfg_merge=False, denoising_strength1 및 그 밖의 signature defaults는 [resolved_defaults.json](resolved_defaults.json) 참조. 이 기본값은 소스/호출 증거이며 모든 scalar를 live hook으로 따로 채취했다는 뜻이 아니다. 실제 runtime BF16/SDPA/offload 없음/adapter null은 두 baseline과 완전히 일치했다.

## 3. 무엇을 알았고 무엇을 모르는가

Lab 시각내용을 회색으로 교체하자 한 seed에서 착석→직립 범주 변화가 나타났고 두 seed 모두 외형·배경이 달라졌다. reference 내용이 출력에 영향을 주며 착석에 기여할 수 있다는 제한적 근거다. 다만 또 다른 seed는 계속 착석했다. 참조 자세만 제거한 것이 아니라 개체·털·체형·배경 정보를 동시에 없앴으므로 자세 정보의 독립 효과는 식별하지 못한다.

Canny를 고정한 실험이므로 gray23 직립이 Canny 덕분인지, 'hind legs' 텍스트와 모델 prior 덕분인지는 이번만으로 분리할 수 없다. prompt는 검은 Labrador와 reference photo를 요구하지만 회색에는 개체정보가 없다는 의미 충돌도 유지했다. 회색 reference는 branch 제거와 다르며 분포 밖 입력일 가능성이 있다. 두 seed·한 짧은 구간의 진단을 Kling 수준·일반화·개체 교체 성공으로 확대하지 않는다.

## 4. 실행·자원·실패

|신규 run|프로세스초|pipeline초|GPU peak allocated / reserved|최저 시스템 MemAvailable|실패|
|---|---:|---:|---|---:|---|
|gray20261022|58.058|38.010|17,056,366,080 /17,687,379,968 bytes|75,384,848,384 bytes|0|
|gray20261023|56.041|38.139|동일|75,395,874,816 bytes|0|

Spark 통합 메모리를 CPU/GPU별 독립 용량으로 더하지 않는다. swap 증가0. 새 모델/학습/imagegen/외부 생성API0, 자동재시도0. 무거운 작업 순차 실행, 기존서비스 유지. A baseline111파일 hash unchanged. 코드 compile/AST 통과, lint/typechecker 미설치로 NOT_RUN; 성능·품질 검증과 구분한다. 사후 검증기의 hash key prefix 해석만 수정했고 실행 코드와 결과에는 영향이 없다. [실행 기록](RUNNING.md), [재현](REPRODUCE.md).

## 5. 다음 연구 하나 — 제안만, NOT_RUN

**R-gray를 고정하고 C-real 대 C-null을 같은 두 seed로 비교**한다. 이번 두 gray+C-real은 실제 설정/noise 호환성을 다시 확인한 경우에만 재사용한다. C-null에서도 직립이면 현재 직립을 Canny 전달의 증거로 보기 어렵고, C-real에서만 원본 자세 대응이 강화되면 구조 기여의 근거가 늘어난다. 이 제안은 새 추론 승인이나 자동실행이 아니다. 이번 비교로 종료한다.

전체 제작·IG·윙크·발차기·Kling 수용은 NOT_RUN이다. 비공개 ZIP에는 네 결과와 두 비교MP4·전프레임 시트·입력/관측 장부를 포함하며 공개 GitHub에는 사진·영상·개인 경로를 넣지 않는다.

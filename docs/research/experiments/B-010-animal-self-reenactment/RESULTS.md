# B-010 결과 — 생성 전 진단력 부족으로 중단

**DIAGNOSTIC_INSUFFICIENT / GPU 및 생성 NOT_RUN.** 실제 source와 STATIC COPY는 일부 머리 위치에서 다르지만, 현재 관측점의 불확실성과 전체 피사체 이동·크기 변화를 고려하면 목표한 관절 동작 전달을 엄격히 구별할 근거가 부족했다. PLAN의 사전 중단 조건을 적용해 P·PROBE·S·D를 시작하지 않았다. 이는 모델 추론 실패도, source에 움직임이 없다는 판정도 아니다.

## 실제로 수행한 비교

시작 연구 HEAD는 `646ba5415b9af9b5b2469a4a0455c06d143366d4`. [PLAN](PLAN.md), [결정](../../decisions/20261023-B-009-to-B-010.md)을 확인하고 기존 격리 연구 checkout 및 A/H/B-008/B-009를 보존했다. 먼저 CPU로 기존 processed source f0를17장 반복한 **STATIC COPY**를 만들었다. source f0..16은 변경하지 않았으며 두 영상 모두512×896/17프레임/24fps다. 파일 길이는17/24초, 첫·끝 sample 간격은16/24초다.

주 에이전트가 source/STATIC COPY의 f0/4/8/12/16 시트 및 실제 표면점 overlay를 열어 비교했고, 독립 검토자도 source/static 시트와 머리 확대를 확인했다. source-only B-006 관측은 동일17장 RGB와 고정 resize/crop 대응을 확인한 뒤 재사용했다. 관측점은 코 중심·양눈·양앞발 끝의 보이는 표면 proxy이며 숨은 관절·접촉을 생성하지 않았다. 전체17프레임 자료를 보존하되 정량 관측점은 사전에 선택한5시점에 한정한다.

| 사전 검사 | 실제 결과 |
|---|---|
| source에서 관측 가능한 t>0 표면점 |20/20; 생성 coverage는 NOT_RUN|
| STATIC COPY 대비 source 변화 오차 평균 |15.5106717544px|
| 전파된 관측 오차 반경의 평균 |19.4222222222px|
| 앞발의 두시점 변위 오차 경계 |26.8888888889px; 관측 앞발 변화는 경계 미만|
| 일부 눈·코 절대 위치 변화 |오차보다 큰 항목 존재; 원본 무동작으로 판단하지 않음|
| 머리–앞발 상대 거리/앞발 간격 |오차 전파 구간이 모든 선택 시점에서 f0와 겹침|
| gain |UNDEFINED; 작은 분모에 epsilon이나 유리한 부분집합 적용 안 함|
| 최종 사전 판정 |DIAGNOSTIC_INSUFFICIENT|

[사전 평가 규칙·근거](PREREG_EVALUATION.md)에 오차 계산과 한계를 기록했다. 기존 낮은 해상도 주석의2px/4px 오차가896/288배로 전파됐고1px 여유가 추가됐다. 이것은 통계적 신뢰구간이 아닌 보수적 반경이다. **이 주석 정밀도에서의 진단력 부족이며, 해당17프레임 자체가 원리적으로 평가 불가능하다는 증거는 아니다.** 영상별 정렬·zoom·warp·동적 시간 맞춤으로 차이를 줄이지 않았다.

## 준비된 입력·코드와 미실행의 구분

reference는 실제 processed source f0 RGB, mask는 기존 f0 RED support와 WHITE 배경으로 준비했다. driving RGB/mask는 B-009와 같은 입력이다. 새 segmentation·체형 수정·색 변경은 하지 않았다. prompt는 실행 전에 다음 한 문장으로 고정했다.

> A small light-colored short-haired dog stands upright indoors, making subtle head and front-paw movements.

새 과제는 reference와 positive text가 함께 바뀌므로 B-009 대비 단일요인 인과 비교가 아니다. B-009 영상은 맥락용이며 정적 복사의 대체 대조군이 아니다.

준비한 comparator는 positive text1개, 양 CFG reference RGB latent2개·CLIP2개·reference mask2개, 합계7개 기대 변경 위치를 명시한다. 나머지9개는 driving latent/mask·negative text·initial noise·RNG·scheduler 계약을 유지한다. mask/noise/RNG/scheduler는 exact, 비마스크 encoder float만 사전 tolerance를 사용한다. Lab 조건 재사용을 거부하는 소형 fixture도 포함했다. **실제 P를 실행하지 않았으므로 새 조건 텐서의 shape/hash/equality를 실제 관측했다고 주장하지 않는다.**

H/B-009의 단계 분리·tiny CUDA/anchor·mixed loader·attention·sampler·final latent 저장 경로는 준비 코드에서 보존했다. 새 엔진이나 low-pass guidance는 적용하지 않았다. CPU8fixture0.91초·syntax·critical Ruff는 PASS지만 targeted typecheck81errors는 NOT_CLEAN이다. 540개 코드/upstream/input 보존 검사PASS는 영상 생성 성공과 다르다. [장부](RUN_LEDGER.json), [정적 검사](STATIC_VALIDATION.json), [코드 차이](RUNTIME_DIFF.diff), [재현](REPRODUCE.md).

## 실제 실행 예산·품질 상태

| 항목 | 실제 사용 |
|---|---:|
| P / PROBE / S / D |각0/1, 전부 NOT_RUN|
| 신규 full sampler / 재시도 / 생성 실패 |0 / 0 / 0|
| 학습·LoRA·새 모델·다운로드·imagegen·외부 생성 |모두0|
| 새 최종 latent·조건 cache·생성 MP4 |없음|
| GPU 시간·메모리 측정 |NOT_RUN; 과거 측정값을 이번 값으로 쓰지 않음|
| 생성 motion / identity / shape 품질 |NOT_RUN|
| 실제 속도 시간 품질 |UNVERIFIED|

현재 단계를 멈추는 데 production 승인이나 예산 부족을 이유로 쓰지 않았다. 사용자 지정 사전 관측성 조건이 충족되지 않았기 때문이다. 더 긴 구간·다른 seed·추가 마스크·모델로 변경하지 않았고 owned worker는 시작하지 않았다.

## 공부와 다음 연구 하나

[한국어 수학·코드 해설](../../lessons/B-010-self-reenactment-and-static-shortcut.md)은 같은 개체 자기 재현, 정적 reference 복사 함정, 변화량/coverage/오차, 조건부 속도장과 영상 시간, CFG의 공유 시각 조건을 연결한다. arXiv2506.08456 adaptive low-pass guidance는 선행 연구로만 검토했으며 이번 코드나 이미지에 적용하지 않았다.

다음 하나는 **같은17프레임의 실제512×896 해상도에서 보이는 표면점을 직접 재주석하는 CPU 관측 정밀도 감사**다. 현재의 저해상도 주석 확대에 따른 오차를 줄일 수 있는지 먼저 확인하고, 그 결과로 자기 재현 진단의 식별력을 다시 판단한다. 새 구간이나 sampler를 바로 실행하는 제안이 아니다. 이번 작업에서는 추가 재주석·GPU 실행을 하지 않고 종료했다.

비공개 ZIP은 source/STATIC COPY/맥락 B-009·전체17프레임·실제 주석과 불확실성·재현·미실행 근거를 포함한다. 존재하지 않는 새 latent나 생성 결과를 채워 넣지 않는다. 공개 문서에는 개인 미디어·표면점 좌표·절대 경로를 포함하지 않는다. 전달 무결성과 양호스트 위치는 별도 DELIVERY 기록으로 마무리한다.

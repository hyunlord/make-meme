# 2026-10-24 — B021 재현 중단과 B022 같은checkpoint 학습량 비교

## 검토한 근거

B021 원격 commit `e4b860bdac827027c7e5092cd398350971b39303`에서 RESULTS, phase_train.py, budget_contract.py 및 연구branch HEAD를 조회했다. 검토자는 Spark 실행을 하지 않았다. 업로드 ZIP은 제공된 정확 경로로 container와 Python을 시도했지만 두 도구 모두 ClientError로 실패했으므로 CRC/257payload/양호스트 동일성을 독립 검증하지 않았다.

기록상 actual initial A/B·입력·noise·optimizer 옵션과 update0 parity는 일치했고, 실제20update 뒤 네 scalar loss가 기존 replay검사를 통과했다. 네 A/B tensor는 사전atol1e-7/rtol1e-5를 초과했다. 최대loss차2.831221e-7, parameter maxabs약9.79e-7~5.24e-6. B021은 원래 계약에 따라 올바르게 정지했으며 그 상태는 유지한다. 근본원인은UNKNOWN이다.

공식 PyTorch는 seed 통제와 연산결정론을 구분한다. 공식 FA2 interface는 별도의 deterministic backward 인자를 제공한다. 이사실과원격코드의deterministic=False는가능한수치변동경로이지현재오차의원인을확정하는실험증거는아니다. 이번원격검토에선새반복backward/커널테스트를하지않았다.

## 판단

이전 계획은 동일한학습문제의20/100효과를비교하려는목적에비해, 독립실행된LoRA각원소의엄격한재현을진행gate로너무강하게사용했을가능성이있다. 그렇다고B021의허용오차를사후완화해PASS로바꾸거나, 비슷한scalarloss를영상동등성증거로삼지않는다.

문제를둘로나눈다: (1) 저장상태/입력/optimizer의정확한복원, (2) 서로다른학습실행사이의수치차이. 첫번째는엄격히검증한다. 두번째는A/B·BA의차이와같은입력에서의velocity차이로보고하고한정반복성검사를수행한다. LoRA factor분해의비유일성은단순A/B검사만으로함수동등성을판정할수없다는수학적근거이지이번차이의실제원인은아니다.

## 다음한작업

[B022 PLAN](../experiments/B-022-resumed-update-comparison/PLAN.md)을등록한다. 짧은동일tail반복backward최대3회와같은checkpoint복원·기능검사를묶고, 통과하면B021 restart20에서optimizer/RNG/cursor까지복원해80update만더한다. 같은B021step20과새100을각1회생성해matched영상비교를확보한다. B020step20은다른반복실행이라는맥락으로만표시한다.

기존B021실패는영구보존하며새실험은B020과동일100경로를재현했다는주장이아니다. root causeUNKNOWN을유지한채동일checkpoint의추가학습질문을검증할수있다. 파일/state/함수parity·finite·gradient·기반불변·자원오류는여전히중단사유다. 안전가드완화와FA2backend변경은없다.

최대3시간,학습80update·신규sampler2회·추가P/prefix0·다운로드/새자료0. 이등록은실행승인이아니며사용자가수행지시를전달할때계획범위를적용한다. 상태PLANNED/NOT_RUN. 실행전후공통HISTORY/ROADMAP을갱신한다. 이변경은계획/결정문서추가만이며기존실행코드·데이터·weights·기록은수정하지않았다.

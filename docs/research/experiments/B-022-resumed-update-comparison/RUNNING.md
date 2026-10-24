# B-022 실행 기록

## 2026-10-24 착수

사용자가 PLAN 실행을 승인했다. 시작 원격 HEAD는 `9940848b59d52537194aa7118792efb15ad9a8e8`이다. B-021의 STOPPED_AT_REPLAY_20과 네 adapter FAIL은 그대로 보존한다. 이번에는 같은 저장 checkpoint의 optimizer/RNG/cursor를 포함해20→100으로 재개한다.

현재 CPU 코드/복원 계약 검증 중이며 GPU NOT_RUN이다. 실제 실행 전에 코드·config·입력 상태 hash와 평가 forward 배분을 고정한다. 진단은30분 이내, 총3시간, 추가80update/진단backward3/비학습tail forward40/새sampler2/decode2가 상한이다. 재시도·P·prefix 재계산은0이다.

B-020과 다른 parameter라는 사실을 새 기능 복원 실패와 혼동하지 않는다. 반대로 새 실험 PASS를 B-021의 미도달 base 검사에 소급 적용하지 않는다.

## 실행 전 고정 완료

원격 commit `76bf4d0a159ca6bd06c1e7dbb810b2b4bfc8b96e` 일치를 확인했다. consumer manifest SHA256 `8a00f0aae8b442afb877d9eff1a8ad4c007f778ab4b11beab8491a4aa9ce3112`. 실제 checkpoint CPU 검증·7계약 검사·6stage 입력/cache 계약·critical lint와 독립 소스 검토를 통과해 TRAIN1 실행을 시작한다. 정적 typing NOT_CLEAN은 별도 보존한다. 현재 단계가 실제 학습/영상 결과를 보증하지 않는다.

## TRAIN 완료

B-021 restart20의18개 tensor와 payload hash를 그대로 복원했다. update21=`train_2`부터100까지80행을 저장했고, 비학습tail forward33회·진단backward3회였다. restart50/100의optimizer step·cursor와 adapter값을 독립 CPU 검증했다. 새 module reload/OFF max_abs=0, 이번 실행의 frozen base/source hash PASS다. B-021 과거 미도달 검사는 바뀌지 않는다.

네 고정tuple의 평가loss는20→100에서 모두 감소했다. 이는 동일clip·고정tuple의 FM 경험손실이며 영상품질 개선을 뜻하지 않는다. 같은checkpoint 반복3회의 prediction은 같았으나 gradient에는 최대2.28e-10 차이가 있었다. FA2만의 원인으로 확정하지 않는다. 이제 승인된 matched20/100 영상 각1회를 순차 실행한다.

## matched20 영상 확보

STEP20_S의40step/80forward·FP32 final latent `[16,5,64,112]` 저장/readback을 확인했다. STEP20_D는 finite raw `[3,17,512,896]`와17frame/30fps MP4를 저장했다. 두worker는각각종료·자원회복후다음단계로넘어갔다. 정적17장검토에서는착석/침실/padding이남고후반얼굴번짐·머리잘림이보였다.100회와의품질비교는아직대기다.

실행 중 원격에 추가된 B 연구v2·B023계획은9fe722a6deeaf024c947ea909251f233200759b3에병합보존했다. 새문서도이미실행중인B022의완료를유지한다고명시한다. B023 GPU는실행하지않는다.

## 종료

TRAIN/PROBE/두S/두D가각한번으로완료했다. sampler총2회·추가update80·진단backward3·비학습tailforward33이며모든자체worker종료·자원회복을확인했다. 양쪽조건16leaf/noise/RNG/scheduler동일성,다른endpointadapter값,raw유한값을검증했다. 전체17장정적비교에서품질개선은입증되지않았으며temporalUNVERIFIED다. 상세RESULTS·MEASUREMENTS·한국어해설을갱신하고최종비공개ZIP검증으로종료한다.

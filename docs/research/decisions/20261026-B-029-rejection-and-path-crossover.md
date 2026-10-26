# 2026-10-26 — B-029 기각 보존과 다음 조건 경로 비교

## 검토 범위

기준 연구 HEAD `a60e258b9a6c25624b07423e4cd29838f3b1b195`에서 B028 RESULTS, B029 RESULTS/METHOD/NEXT_DECISION과 실제 `spatial_image_gate.py`를 읽고 공식 SCAIL `78fe19576bb06be96c2375e088574a262a300edb`의 참조 latent·mask·CLIP 연결과 대조했다. 첨부 compact ZIP은 container와 Python ClientError로 열지 못했다. 실제 영상 재생·CRC·hash를 독립 검증했다고 하지 않는다.

## 결과에서 유지할 결론

B-028은 일부 외형 반영과 동작·형태·장면 회귀가 함께 있어 전 패널 기준선으로 채택하지 않는다. B-029도 고정 CLIP 이미지 출력 위치 재가중에서 공동 품질 개선 및 shifted CONTROL 대비 일관된 우위를 입증하지 못했다. B027을 공통 비교 기준선으로 유지하고 B029의 NOT_ADOPTED, temporal UNVERIFIED, 타입 NOT_CLEAN을 보존한다. 더 깨끗한 CONTROL을 사후 기본 방법으로 올리지 않는다.

B029가 reference VAE joint 경로를 바꾸지 않았다는 사실은 그 경로가 실패 원인이라는 증거가 아니다. 다음에는 새 gate 강도나 layer를 고르기보다 같은 공개 대상의 두 참조에서 VAE+mask 묶음과 CLIP 경로의 조건부 효과 및 상호작용을 확인하는 한정 비교를 제안한다.

## 다음 계획

[B-030 계획](../experiments/B-030-reference-path-crossover/PLAN.md).

공개 human·vehicle 각 과제에서 B027의 R1/R1 및 R2/R2 결과를 대각 기준선으로 재사용하고, VAE+mask R1/CLIP R2 및 VAE+mask R2/CLIP R1의 두 교차 결과만 생성하는 제안이다. 최대4신규 sampler,각40step80forward,학습/encoder/설치/다운로드0. 기존 사진·source·caption·noise·모드 유지, B029 gate OFF. 개인 추가 사진은 필요하지 않다.

VAE는 pose만, CLIP은 identity만 담는다는 해석을 하지 않는다. mask가 VAE와 함께 바뀌고 mixed-reference는 학습분포 이탈일 수 있다. 교차 조건에서만 손상이 커지면 입력 불일치 또는 상호작용으로 남기고 특정 encoder 탓으로 결론내리지 않는다. 결과가 불분명해도 또 다른 임의 gate sweep을 자동 시작하지 않는다.

이것은 다음 생성 방법을 정하기 위한 메커니즘 실험이며 새 편집 방법의 성과가 아니다. 이후 성과 기준은 동일 과제의 실제 외형·동작·장면 보존과 전체 비용이고, 개인 사례 성공이나 실행 PASS만으로 논문·상용 성능을 주장하지 않는다.

## 현재 상태

이번 변경은 계획·결정 문서 두 개뿐이다. 코드·과거 결과·가중치·HISTORY 완료 상태는 변경하지 않았다. B030은 **PROPOSED / NOT_RUN**이고 GPU/학습/생성/설치0이다. 사용자가 실행 지시를 전달하면 담당자가 실제 최신 상태를 확인해 HISTORY/ROADMAP에 착수·종료를 연결한다. 문서 생성만으로 예산 집행이나 GPU 실행 승인이 된 것으로 취급하지 않는다.

# B-027 공개 다중 사례 편집 비교

상태: **COMPLETED / 기술 실행 PASS / 결합 편집 품질 미입증**. 공개3과제×2참조의 실제 raw6개·최종 latent6개·17프레임 MP46개를 확보했다. 신규 sampler6/6, 각40step80forward, 재시도0. 외형·동작·장면·형태를 동시에 충족하는 일반적 편집 능력은 이번 결과로 입증되지 않았다.

## 시각 결과

| 과제/참조 | target 외형 | source 동작 | 장면 보존 | 형태·가림 |
|---|---|---|---|---|
| animal R1 | FAIL: 어두운 target 대신 옅은 source 외형 | PARTIAL: 접근/정면 변화, 발 세부 불확실 | FAIL: 좌하단 큰 문자·장식 추가 | PARTIAL/UNCERTAIN: 얼굴·털·사지 세부 흐림 |
| animal R2 | FAIL: 옅은 source 외형 잔존 | PARTIAL: 큰 접근 순서 | PARTIAL: 큰 배치 유지, R1 장식 없음 | PARTIAL/UNCERTAIN |
| human R1 | PARTIAL: 흰 상의·분홍 치마·어두운 머리 반영; 실제 인물 일치 불명 | PARTIAL: 다리 큰 순서는 대응, 팔 배치 다름 | PARTIAL/FAIL: 관객/배치 유지, 서명 모양 추가 | FAIL 항목: 얼굴·팔 번짐 |
| human R2 | PARTIAL: target 의상/머리 특징 | PARTIAL/FAIL: 큰 스텝은 대응, 참조의 펼친 팔·치마 영향 | PARTIAL/FAIL: 서명/문자 추가 | FAIL: 후반 치마가 상체를 가리며 연결 손상 |
| vehicle R1 | PARTIAL 색/몰딩, 실제 target 교체 FAIL | PARTIAL: 오른쪽/뒤쪽 회전 순서 | FAIL: 좌하단 큰 스포츠카 그래픽 추가 | PARTIAL: source/target 차체 혼합 |
| vehicle R2 | PARTIAL: 밝은 박스형 인상, 정확한 target 미입증 | PARTIAL: 오른쪽/후면 변화 순서 | PARTIAL: 큰 배치 유지, R1 그래픽 없음 | PARTIAL: 혼합 차체·세부 충실도 부족 |

전체17장과 local0/8/16의 agent 정적 관측이다. 독립 사람 평가나 실제 속도 연속 시청은 수행하지 않았고 **temporal=UNVERIFIED**다. 정지 참조 복사·source-copy·참조 특징 반영을 분리했다. 세부 근거와 사전 명칭 오인 정정은 [VISUAL_REVIEW](VISUAL_REVIEW.md)에 있다.

## 고정 비교와 해석 경계

[CASES](CASES.md)의 source3개, 각 다른 target track의 R1/R2를 생성 전에 고정했다. 실제 source native FPS를 확인하지 못해17프레임 순서만 보존하며 preview24fps로 표시한다. GT instance mask를 입력으로 제공한 **mask-given**이다. 개인 반려견 자료·A 생성물은 사용하지 않았다. B-026은 선택적 대기로 보존했다.

각pair는 같은 source/caption/noise/RNG/scheduler에서 ref VAE/CLIP/mask만 바꾼다. target 두 사진의 자세뿐 아니라 조명·시점·크기·가림·mask가 함께 다르므로 순수 pose 인과효과가 아니다. 작은 animal reference나 human R2의 실제 GT 관목 가림을 숨기지 않는다. source 객체의 픽셀은 교체 후 정답 영상이 아니며, 높은 원본 유사도만으로 성공이라고 하지 않는다.

3paired task와 단일 seed의 탐색 결과다. 6출력·102프레임을 독립 반복으로 세지 않으며 일반 성공률·benchmark·상용급·논문 기여를 주장하지 않는다. 범주별 차이는 모델 지원 범위와 참조 크기/가림 등이 섞여 있으므로 도메인 하나의 확정 효과도 아니다.

## 기록

- 사전 실행 고정 및 원격 확인: `9a93aa09ed2032aebea3905e5b698388b65243c4`.
- [조건 연결](CONDITIONS.md), [계약 코드 검토](CONTRACT_REVIEW.md), [비용](COSTS.md), [재현](REPRODUCE.md).
- [입력·코드 manifest](INPUT_MANIFEST.json), [데이터 출처/조건](DATA_LICENSE.md), [학습 해설·문헌](../../lessons/B-027-public-reference-robustness.md).
- 실행 전 launcher 오류3건은 실제 sampler 시도와 분리해 보존했다. 실패 기록·원본 cache·과거 결과를 소급 변경하지 않는다.

## 실제 실행·비용·수용 범위

- ENC3회, PROBE6회, S6회, D6회:21worker 완료.240step·480forward, 학습/추가 모델·패키지/외부 생성/imagegen0. 각S 최종 latent를 D 전에 원자 저장하고 shape·finite·readback을 확인했다.
- 실행 구간은 UTC15:22:44.266–17:20:27.322. 단계별 service elapsed 합계6,478.622초(약108분)이며 GPU kernel 시간은 아니다. 전체 준비·검토·패키징은 별도 wall-clock이다.
- 최소 시스템 가용52.635GiB, 최대 CUDA peak allocated33.847GiB, cgroup peak62.586GiB, RSS83.138GiB를 별개로 계측했다. swap0, OOM0이며 서로 합산하지 않는다.
- 실제 sampler/runtime 실패0, pre-worker CLI/launcher 오류3은 실패 장부에 보존한다. 보호 서비스 유지와 자체worker 종료를 확인했다.
- CPU 계약/미디어/패키지/요약 검사15개PASS, 실제 입력 decode·조건 hash·first-CFG 연결·final 저장·MP4 파일 검증PASS. strict typing NOT_CLEAN과 미설치 lint 도구 NOT_RUN은 남긴다. 이 결과가 시각 품질 PASS를 대신하지 않는다.
- 원본 배경·source 객체를 그대로 복사하면 겉보기 motion이 맞아도 교체 실패다. 작은 reference와 가림, 단일seed,3paired task, 미확인nativeFPS, 독립 사람 검수 부재를 한계로 유지한다. 기반모델 학습자료와 DAVIS의 중복은 UNKNOWN이다.

전체 비교는 비공개 `review/review.html`, task별 `all17.png`, `local0-8-16.png`, `comparison-preview24.mp4`에서 확인한다. raw후처리 보정은 없다. 최종 양호스트 전달·CRC·해시·추출 검증은 [DELIVERY](DELIVERY.md)에 남겼다. 다음 제안은 [NEXT_DECISION](NEXT_DECISION.md)의 한 가설뿐이며 설치·추론·학습을 시작하지 않았다.

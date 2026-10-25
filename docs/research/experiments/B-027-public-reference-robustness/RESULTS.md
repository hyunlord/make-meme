# B-027 공개 다중 사례 편집 비교

상태: **실행 중**. 아래 판정은 실제 도착한 raw만 대상으로 하며 미도착 결과를 채우지 않는다. 최종 사용량·종료 상태는 모든 승인 worker 종료 후 확정한다.

## 시각 결과

| 과제/참조 | target 외형 | source 동작 | 장면 보존 | 형태·가림 |
|---|---|---|---|---|
| animal R1 | FAIL: 어두운 target 대신 옅은 source 외형 | PARTIAL: 접근/정면 변화, 발 세부 불확실 | FAIL: 좌하단 큰 문자·장식 추가 | PARTIAL/UNCERTAIN: 얼굴·털·사지 세부 흐림 |
| animal R2 | FAIL: 옅은 source 외형 잔존 | PARTIAL: 큰 접근 순서 | PARTIAL: 큰 배치 유지, R1 장식 없음 | PARTIAL/UNCERTAIN |
| human R1 | PARTIAL: 흰 상의·분홍 치마·어두운 머리 반영; 실제 인물 일치 불명 | PARTIAL: 다리 큰 순서는 대응, 팔 배치 다름 | PARTIAL/FAIL: 관객/배치 유지, 서명 모양 추가 | FAIL 항목: 얼굴·팔 번짐 |
| human R2 | PARTIAL: target 의상/머리 특징 | PARTIAL/FAIL: 큰 스텝은 대응, 참조의 펼친 팔·치마 영향 | PARTIAL/FAIL: 서명/문자 추가 | FAIL: 후반 치마가 상체를 가리며 연결 손상 |
| vehicle R1 | PARTIAL 색/몰딩, 실제 target 교체 FAIL | PARTIAL: 오른쪽/뒤쪽 회전 순서 | FAIL: 좌하단 큰 스포츠카 그래픽 추가 | PARTIAL: source/target 차체 혼합 |
| vehicle R2 | 미도착 | 미도착 | 미도착 | 미도착 |

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

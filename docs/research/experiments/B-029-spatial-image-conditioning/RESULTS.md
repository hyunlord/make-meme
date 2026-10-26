# B-029 결과 — 위치별 이미지 조건 재가중

상태: **진행 중, 2026-10-26 UTC05:45 기준**. 완료된 출력의 정적 관측을 먼저 남긴다. 차량 METHOD/CONTROL과 전체 종료 검증 전에는 최종 채택 판정을 만들지 않는다. 기준선은 사전에 선택한 **B-027 전6case**이며 B-028의 좋은 출력을 섞지 않았다.

## 바꾼 것과 관측

기존 image cross-attention 출력에 generated query 위치별 계수 `g=1+0.5*(E-mean_HW(E))`를 곱했다. text 항과 더하기 전의 이미지 출력만 바뀌며, reference VAE·CLIP 입력·가중치·noise·sampler는 그대로다. 자세 제거·identity-only 모듈·객체만 생성하는 연산은 아니다. [방법](METHOD.md), [조건/대조](ABLATIONS.md), [전체 정적 관측](VISUAL_OBSERVATIONS.md).

| 과제/참조 | 외형 반영 | 원본 동작·형태 | 보호 장면 | 현재 해석 |
|---|---|---|---|---|
| animal R1 | 어두운 target 대신 밝은 source 계열 지속 | 큰 접근/정면 변화 유지, 세부 얼굴·발 불명확 | 큰 장식이 작은 원형 배지로 바뀌나 전17장 잔존 | 교체 FAIL, 장식의 제한된 감소 |
| animal R2 | 어두운 target 미반영, source 털/하네스에 더 가까움 | source 큰 배치에 더 가까워 보임; 관절 수치 미측정 | 새 대형 장식 없음 | source-copy를 교체 성공으로 세지 않음 |
| human R1 | 흰 블라우스/분홍 치마 반영은 기존에도 있음 | 치마 윤곽/테두리 일부 정돈, 팔·스텝 대응 미해결 | 하단 서명 지속 | 형태 PARTIAL, 결합 개선 미입증 |
| human R2 | 의상 반응 있으나 정확 인물 미확인 | 크게 들린 치마와 후기 얼굴 가림, 잘못된 팔 배치 지속 | 서명/추가 획 지속 | R1 개선이 두 참조에 이어지지 않음 |
| vehicle R1 | 은색 반응, target의 높은 차체보다 source Mini형 유지 | 큰 오른쪽 진행/후면 변화 유지, 세부 형태 미해결 | 별도 큰 차량 후면 그래픽이 전17장 도로를 가림 | 결합 목표 미충족, CONTROL 대기 |
| vehicle R2 | PENDING | PENDING | PENDING | 실제 출력 후 작성 |

animal R1의 shifted CONTROL은 큰 빨강/흰 배지, METHOD는 작은 원형 배지를 남겼다. 공간 배정에 따라 장면 오염 양상은 달라지지만 양쪽 모두 target 교체를 실패했다. 이를 외형·동작·장면의 공동 성공이나 참조 자세 분리로 확대하지 않는다. vehicle CONTROL은 미완료다.

## 기술과 품질의 경계

완료된6case는 각각40step·80forward·40block×80 gate 적용, 유한17프레임 decode를 기록했다. 실제 generated token은 start1792/length8960/suffix2240, grid[5,32,56]이며 image output FP32를 보존했다. B02716leaf와 실제noise/RNG/scheduler의 계보를 확인했다. CPU6개+기존4개 계약은 전체14B OFF 수치 parity나 영상 품질 검증이 아니다. LSP transport unavailable은 NOT_CLEAN으로 남긴다.

주체는 실행 agent의 실제 이미지 관측이다. 전체17장과 local0/8/16을 확인하지만 실제 속도 연속 재생을 시청한 것은 아니므로 **temporal=UNVERIFIED**다. 이 공개3과제는 방법 선택에 사용한 개발 패널이며 단일seed 탐색 결과다. 프레임을 독립 반복으로 세거나 임의 성공률·유의성을 만들지 않는다. source FPS 미확인, preview24fps/timebase_assumed=true를 유지한다.

## 종료 후 확정할 항목

- 차량2 METHOD와 CONTROL의 전체17장 비교 및 공동 목표 판정.
- 최종 실제 사용량·matched 기준선 비용·자원 회복·자체 프로세스 종료.
- 방법의 다음 검증 승격/보류/기각과 다음 가설 하나.
- 전체 결과/실패를 포함한 full 및 review-lite의 양 호스트 CRC·해시·실제 추출 검증.

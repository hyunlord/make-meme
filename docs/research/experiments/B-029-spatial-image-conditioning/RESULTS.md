# B-029 결과 — 위치별 이미지 조건 재가중

상태: **COMPLETED / 기술 실행 PASS / 고정 방법 NOT_ADOPTED / 결합 품질 개선 NOT_ESTABLISHED**. 2026-10-26 UTC06:15:19에 METHOD6+CONTROL2를 모두 종료했다. 공통 기준선은 사전에 선택한 **B-027 전6case**이며 B-028의 좋은 출력을 섞지 않았다. 효과가 없거나 나빠진 결과도 모두 보존한다.

## 바꾼 것과 관측

기존 image cross-attention 출력에 generated query 위치별 계수 `g=1+0.5*(E-mean_HW(E))`를 곱했다. text 항과 더하기 전의 이미지 출력만 바뀌며, reference VAE·CLIP 입력·가중치·noise·sampler는 그대로다. 자세 제거·identity-only 모듈·객체만 생성하는 연산은 아니다. [방법](METHOD.md), [조건/대조](ABLATIONS.md), [전체 정적 관측](VISUAL_OBSERVATIONS.md).

| 과제/참조 | 외형 반영 | 원본 동작·형태 | 보호 장면 | 정적 해석 |
|---|---|---|---|---|
| animal R1 | 어두운 target 대신 밝은 source 계열 지속 | 큰 접근/정면 변화 유지, 세부 얼굴·발 불명확 | 큰 장식이 작은 원형 배지로 바뀌나 전17장 잔존 | 교체 FAIL, 장식의 제한된 감소 |
| animal R2 | 어두운 target 미반영, source 털/하네스에 더 가까움 | source 큰 배치에 더 가까워 보임; 관절 수치 미측정 | 새 대형 장식 없음 | source-copy를 교체 성공으로 세지 않음 |
| human R1 | 흰 블라우스/분홍 치마 반영은 기존에도 있음 | 치마 윤곽/테두리 일부 정돈, 팔·스텝 대응 미해결 | 하단 서명 지속 | 형태 PARTIAL, 결합 개선 미입증 |
| human R2 | 의상 반응 있으나 정확 인물 미확인 | 크게 들린 치마와 후기 얼굴 가림, 잘못된 팔 배치 지속 | 서명/추가 획 지속 | R1 개선이 두 참조에 이어지지 않음 |
| vehicle R1 | 은색 반응, target의 높은 차체보다 source Mini형 유지 | 큰 오른쪽 진행/후면 변화 유지, 세부 형태 미해결 | 별도 큰 차량 후면 그래픽이 전17장 도로를 가림 | 결합 목표 미충족; CONTROL의 보호 장면이 더 깨끗함 |
| vehicle R2 | 밝은 색 반응, source Mini형 혼합 외형 지속 | 큰 이동/후면 변화 유지, 정확 target 차체 미확인 | BASE에 없던 큰 차량/빨간 문자 장식이 전17장 추가 | 보호 장면 회귀 |

animal R1의 shifted CONTROL은 큰 빨강/흰 배지, METHOD는 작은 원형 배지를 남겼다. 공간 배정에 따라 장면 오염 양상은 달라지지만 양쪽 모두 target 교체를 실패했다. 이를 외형·동작·장면의 공동 성공이나 참조 자세 분리로 확대하지 않는다. vehicle R1 CONTROL은 반대로 큰 장식이 없어 METHOD보다 보호 장면이 깨끗했다. 대상 위치에 맞춘 METHOD의 우월성은 입증되지 않았다. CONTROL도 target 차체 교체가 미입증이며 이를 새 기본 방법으로 채택하지 않는다.

## 기술과 품질의 경계

완료된8case는 각각40step·80forward·40block×80 gate 적용, 유한17프레임 decode를 기록했다. 실제 generated token은 start1792/length8960/suffix2240, grid[5,32,56]이며 image output FP32를 보존했다. B02716leaf와 실제noise/RNG/scheduler의 계보를 확인했다. CPU6개+기존4개 계약은 전체14B OFF 수치 parity나 영상 품질 검증이 아니다. LSP transport unavailable은 NOT_CLEAN으로 남긴다.

주체는 실행 agent의 실제 이미지 관측이다. 전체17장과 local0/8/16을 확인하지만 실제 속도 연속 재생을 시청한 것은 아니므로 **temporal=UNVERIFIED**다. 이 공개3과제는 방법 선택에 사용한 개발 패널이며 단일seed 탐색 결과다. 프레임을 독립 반복으로 세거나 임의 성공률·유의성을 만들지 않는다. source FPS 미확인, preview24fps/timebase_assumed=true를 유지한다.

## 판정과 비용

사전 채택 기준인 두 과제의 결합 개선과 다른 과제의 큰 회귀 부재를 충족하지 못했다. animal의 source-copy, human R2의 형상 손상, vehicle R2의 새 보호 영역 그래픽 때문에 **이번 고정 설정은 채택하지 않는다**. 일부 장식 축소나 치마 윤곽 개선을 모든 목표의 PASS로 합치지 않는다. 자세한 다음 가설 하나는 [종료 결정](NEXT_DECISION.md)에 남기며 추가 실험은 시작하지 않는다.

새 sampler는 METHOD6+CONTROL2, 총8/8이며 모두40step·80forward, decode8/8, 재시도0이다. B-028의 미착수6회까지 합쳐 이번 통합 의뢰에서14/14를 사용했다. B027 기준선은 재생성하지 않았다. B029 encoder0·학습0·설치0·외부 생성0·추가 관측forward0이다. NFE가 같다는 것을 같은 실행 시간이나 비용 절감으로 해석하지 않는다. B029 첫 PROBE~마지막 D는139.48분, CUDA peak allocated33.848GiB, 시스템 MemAvailable 최저52.983GiB였다. 같은 B027 case 대비 S worker는+1.858~21.509초였으나 CPU 비교/전송이 중첩되어 순수 gate 오버헤드나 효율 향상으로 해석하지 않는다. matched B027 비교와 CPU/CUDA/cgroup의 분리 실측은 [COSTS](COSTS.md), [MEASUREMENTS](MEASUREMENTS.json)에 있다.

독립 읽기 전용 실행 장부 대조에서8case의 조건16leaf·noise/RNG/scheduler·고정 코드·실제gate구간·최종latent/decode 계보와24stage 각1회 종료를 확인했다. 대형 가중치를 새로 적재/재해시하지 않고 기존 manifest·파일 동일성·loader 명세를 확인한 범위다. 자체 GPU unit은 inactive, 자체 코드 프로세스0이며 보호 서비스를 유지했다. [검토 범위](SOURCE_REVIEW.md).

## 바로 볼 자료와 재현

- [순차 시각 관측](VISUAL_OBSERVATIONS.md): 전체17장/local0/8/16과 실제 참조를 확인한 근거; 사건 시트와 전체 시트의 확인을 구분한다.
- [재현](REPRODUCE.md), [수학·코드 해설과 질문/답안](../../lessons/B-029-spatial-image-conditioning.md).
- 비공개 full/review-lite에는 B028 및 B029의 모든 새 출력, 원래 B027 비교, 실제 입력, 전체 프레임 뷰어와 실패 근거를 넣는다. raw tensor/최종latent는full에 보존하고 lite에는 영상·입력·전체 비교를 유지한다. 대형weights·중복cache는 제외한다.
- 최종 ZIP 자체 SHA와 양 호스트 경로는 ZIP 외부 전달 영수증에 둔다. payload manifest·CRC·실제 추출 해시와 원본 MP4 불변을 검증한 범위만 최종 보고한다.

공개에는 비민감 문서·코드·요약만 남긴다. 이번 패널의 mask는 공개 GT로 주어진 것으로, 자동 객체 선택/추적 성공을 뜻하지 않는다. 개인 사례·미사용 일반화·긴 영상·다중 객체·상용 품질은 이번에 검증하지 않았다.

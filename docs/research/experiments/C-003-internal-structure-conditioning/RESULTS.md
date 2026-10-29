# C-003 결과 — 내부 구조 전달 성공, 동작 이득 미입증

**NO_ESTABLISHED_GAIN. DYNAMIC은 OUTLINE_ONLY와 HOLD보다 원본 머리·다리 진행을 명확하게 더 잘 따른다고 판단할 수 없다.** 실제 두 영상은 정상 완료했지만 기본 채택하지 않는다. 검정/흰 외형과 거친 접근은 유지되고 얼굴 세부가 달라졌다. 내부 동작 이득보다 세부 외형 변화와 국소 배경 손상이 더 분명하다. 연속 지각 검수가 없으므로 **temporal=UNVERIFIED**다.

| 평가 축 | 실제 같은 인덱스 비교 |
|---|---|
| 전체 이동·크기 | 세 조건 모두 정면 접근을 보인다. DYNAMIC의 추가 이득은 뚜렷하지 않다. |
| 머리·내부 구조 | 코 각도·주둥이 무늬가 달라지지만 source 사건 진행을 두 대조군보다 정확히 따랐다는 근거는 부족하다. 낮은 머리가 남는다. |
| 보이는 앞발 | local8의 화면 왼쪽,16의 화면 오른쪽,28의 화면 왼쪽 앞발이 더 앞으로 보이는 거친 패턴이 세 출력에서 비슷하다. 관절·교대 보행·실제 접촉 성공은 미입증이다. |
| target 외형 | 검정/흰 얼굴·가슴·발이 남고 크림색 source로의 명확한 회귀는 없다. 세부 무늬 차이를 정확한 개체 일치 PASS로 보지 않는다. |
| 보호 장면 | 새 조건에서 풀·울타리 질감이 더 뒤틀리거나 패치처럼 보이는 구간이 있다. HOLD16 왼쪽 가장자리의 황갈색 객체 같은 패치는 source/OUTLINE/DYNAMIC에 없는 국소 손상이다. |
| 형태·종료부 | 낮은 머리·다리 겹침의 불확실성이 남는다.29–32는 source보다 낮게 웅크린 종료 앵커와 충돌하는 구간으로 별도 해석한다. |
| 연속 품질 | 모든33장 정적 검토와 MP4 decode/브라우저 동작 검사는 수행했다. 실제 연속 지각 검수는 아니므로 UNVERIFIED다. |

## 실제 실행과 전달 근거

사용자가 명시적으로 승인한 시작 정책 amendment와 코드 `fd1d7343eee6dce7a2f085acd1b07d1bfc2d9513`, 실제 조건·평가 freeze `1adcd2e7a6ed74c25553790e2da2d066a9bd6637`를 push/원격 확인한 뒤 실행했다. 수정은 시작10초 중 swap-out이0보다 크면 즉시 막던 추가 분기만 제거했다.64MiB 증가/최근 swap-out, PSI10%, headroom, 자체swap0/OOM, 서비스·외부GPU·신원·관측 가드는 유지했다. 현재 guard의 실제 import 경로·파일 hash와 공통 MemoryBudget identity를 확인했다.

공식 scribble 추출은 FP32 strict weights_only load로33장 한 pass를 완료했다. J에는 눈·코·귀와 일부 앞다리 경계가 있지만 몸통·얇은 발 내부 정보는 드물다. I밖 배경선과 경계대는 조건에 들어가지 않았다. DYNAMIC/HOLD는256 bbox 왕복과 같은 I를 거치며 중간31장의 총487,891픽셀이 다르다. HOLD의 초기 얼굴 패턴이 좁아지는 bbox에서 옆으로 밀리고 clip되는 현상은 의미 대응 없는 대조군의 한계다. 조건을 보고 선 강도·margin·seed를 조절하지 않았다.

각 영상은50 Euler step·100 model_fn call·33프레임을 완료했다. 최초 noisy latent와 mask64 hash는 두 신규 실행 및 C-002와 같고, VACE context는 두 조건에서 서로 다르며 finite다. 양끝 RGB·G·inactive 논리 입력은 동일하고 reactive의 허용 내부만 달라진 것을 실제 저장 조건으로 확인했다. Hash 차이는 전달 증거일 뿐 활용이나 품질 증거가 아니다. 원자 저장 final latent readback exact, raw와66개 무손실 출력 프레임을 보존했다. 양끝 덮어쓰기·후합성은 없다.

두 guard는 COMPLETE, worker0, 정상 종료, cleanup오류0, 최종 CLEAR/REMOVED다. 시스템 swap1,806,336B는 안정적이며 GLOBAL_SWAP_WARNING을 보존했다. 자체swap/OOM/high 증가0, 관측 최소 MemAvailable 약88.45GiB다. 자체 활성 unit와 GPU process가 종료 후0임을 확인했다. 다른 작업을 시작·종료하지 않았다. 세부 hash·실행 수치는 [NUMERICS](NUMERICS.json), [비용](COSTS.json), [전달](DELIVERY.json)에 있다.

## 비용과 해석

구조 추출2.7168초, 조건 변환1.9356초, 영상 DYNAMIC307.5222초/HOLD294.1902초로 총601.7124초였다. 영상 heavy2회,100step/200call, 예비·VAE복구·품질재시도0이다. 공식17,173,511B 가중치 한 파일은 초기 작업에서 확보했고 resume 다운로드0이다. imagegen/SAM재추론/학습/패키지 설치/유료생성API0이다. 따로 재지 않은 준비·검토 시간과 전기·구독 비용은 null로 남겼다.

OUTLINE↔DYNAMIC에서는 추가 내부 정보의 결합 이득이 미입증이다. OUTLINE↔HOLD는 초기 내부 패턴도 출력 세부와 배경을 바꿀 수 있음을 보인다. DYNAMIC↔HOLD에서 시점별 내부 구조가 뚜렷한 우위를 보인다고 하기 어렵다. 선 밀도·질감·가림·bbox 보간·clipping·앵커 충돌·낯선 혼합 표현이 함께 다르므로 하나의 원인을 확정하지 않는다. 한 개발 사례·한 seed이며33프레임은33독립 실험이 아니다.

다음 후보 하나는 **가시성·신뢰도를 포함한 시간별 객체 내부 대응**이다. 구조선이 표현하지 못한 부위와 전달된 선을 모델이 어떻게 사용하는지를 이번 결과만으로 분리할 수 없다. 후보를 기록할 뿐 점 추적기·pose·새 학습·추가 생성은 시작하지 않는다. 사용자와 이 두 출력 및 기존 기준선을 검토한 뒤 다음 개입을 정한다.

## 이전 중단 기록은 불변

초기 첫 CPU는 sibling import 오류이며 원래 NOT_CLEAN / OBSERVATION_FAILED / REMOVED:exit_not_verified, return1 기록을 유지한다. 다음 시작10.238937초의 pswpout127→128(실제4096B page), swap 최종+258,048B/최대+262,144B 때문에 당시 정책이 START_SWAPOUT_OBSERVED로 worker 전에 중단했다. 발생 주체 UNKNOWN이며 OOM/CUDA 결함이 아니다. 당시 완료 영상/추출0과 보류 commit `4e546e1971c2545d07883890287838b3a064e669`, 기존 blocked ZIP을 보존한다. 이번은 명시적 사용자 amendment 이후의 새 실행이며 과거를 PASS로 바꾸지 않는다. C-001 PARTIAL, C-002 차량 TRADE_OFF/개 COARSE_CONTROL_ONLY와 A/B 이력도 불변이다.

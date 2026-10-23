# B-011 — 제한된 동물 자기 재현 결과

**실행 PASS: 실제 17프레임 MP4와 final latent를 확보했다. 수준 A는 원본의 화면상 변화와 대응하는 탐색적 근거가 있으며, 수준 B의 정확한 부위 상대 운동은 INCONCLUSIVE다.** P·PROBE·S·D는 각각1회, full sampler1회·재시도0회다. B-010의 DIAGNOSTIC_INSUFFICIENT와 사용0 기록을 보존한다. 불확실성을 반영한 정적 복사 대비 우월성은 입증하지 않았고 통합 gain은 **UNDEFINED**, 시간 품질은 **UNVERIFIED**다.

## 무엇을 실제로 실행했는가

시작 원격 HEAD `dfa23d6ffeb49a8471eb3487085739f35e82d646`에서 계획·공통 기록을 읽었다. source-only 관측과 평가 수준을 생성 전에 고정한 commit은 `ee730af08a29ecfce3d0b6a243e18f04a2c64584`다. 입력·prompt·model·loader·sampler를 보존하고 B-011 ID·deadline·parent 사용 기록만 최소 변경했다. [정확한 diff](RUNTIME_DIFF.diff), [코드 해시](PREREGISTERED_CODE.json), [입력 해시](PREREGISTERED_INPUTS.json), [평가 계약](PREREG_EVALUATION.md)을 연결한다.

원본 f0 RGB와 기존 RED support+WHITE 배경 mask가 reference다. 같은 source f0~16과 driver mask,512×896·24fps, seed20261022,UniPC40steps·shift3·CFG5,negative empty,replace_flag=False,history=None,LoRA/enhancer OFF를 사용했다. positive prompt는 B-010의 사전 문장을 유지했다. 512×896은512×288의 확대·crop이며 새 고해상도 촬영 입력이 아니다.

새 P에서 B-009 대비 reference/text 관련7leaf가 바뀌고 driving·driver mask·negative·noise·RNG·scheduler9leaf가 비트 동일했다. reference/text를 함께 바꾼 자기 재현 진단이며 B-009와의 단일요인 인과 비교가 아니다. [실제 조건 비교](CONDITION_COMPARISON.json).

| 단계 | 실제 시도/상한 | guard wall time | 완료 근거 |
|---|---:|---:|---|
| P | 1/1 | 121.123초 | 새 자기 재현 조건 저장·검증,7변경/9보존 |
| PROBE | 1/1 | 6.055초 | tiny CUDA 실제 연산·조건 복원 |
| S | 1/1 | 1062.421초 | 실제40step·80forward,finite final latent,원자적 저장·readback |
| D | 1/1 | 15.219초 | finite raw·17프레임 MP4·전체 decode |

각 fresh worker가 종료하고 자원이 회복된 뒤 다음 단계로 진행했다. 최종 latent는 FP32 `[16,5,112,64]`, raw는 `[3,17,896,512]`다. MP4는512×896·17프레임·24fps·0.708333초이며 첫·끝 표본 간격은16/24초다. 기존 code의 seed만 믿지 않고 P→S 실제 initial noise 동일성을 확인했다. 최종 latent는 initial noise와 다른 실제40step 결과다. [장부 및 전체 해시](RUN_LEDGER.json).

- final latent 파일 SHA256: `269034da7059f9aef955491de829d2fa399c34b8b705a492dba8593a1c8626b3`
- MP4 SHA256: `3dbad6c70ed39636c9bfb47b7865c84b806600815a017d7742009148101ab11c`
- 신규 모델·다운로드·학습·LoRA·imagegen·외부 생성0. 추가 구간·seed·low-pass·업스케일·보간0.

## 관측과 품질 판정

생성 전 source-only 검토는 최대342.052초로30분 제한 안에 끝냈다. 같은 에이전트가 f0/4/8/12/16의 코·양눈·양앞발 표면점을 실제 이미지에서 읽고 텍스트로 기록했다. 마우스 클릭·인간 독립 ground truth·숨은 관절 추정은 하지 않았다. 기존19.4222px 평균 반경합은 보수적 전파 가정이며 실측 tracker RMSE·표준편차·신뢰구간이 아니다. 반경은 낮추지 않았고 체계적 편향은 UNKNOWN이다.

원본/STATIC COPY/출력의 전체17장과 고정 그룹 시트를 직접 열어 검토했다. 출력은 연한색 원본 개체의 직립 실루엣·귀·머리·앞발 배치와 장면을 대체로 유지했다. 정적 시트에서 큰 신체 붕괴는 보이지 않았고 후반부를 포함한 작은 위치·크기·머리 변화가 있다. 따라서 픽셀을 반복한 정지 영상이라고 단정하지 않는다. 직립은 reference에 이미 있으므로 그것만으로 새 동작 성공을 선언하지 않는다.

고정된5시점×5점의25위치를 모두 기록했다. 머리15위치는 VISIBLE, 앞발10위치는 흐린 발가락 묶음 말단 때문에 UNCERTAIN이다. 가려진 해부학 관절이나 발 접촉을 추정하지 않았다. 모든20변위에 불확실한 앞발8개를 포함했고 좋은 점만 제외·선택하지 않았다. 출력 위치의 오차는 **NOT_CALIBRATED**다. 같은 에이전트가 source를 이미 본 뒤 판독했으므로 관측자 편향 가능성도 남는다.

`q(t)=p(t)-p(0)`로 계산한다. E_copy는 원본 변위 길이, E_gen은 원본 변위와 생성 변위 차이의 길이다. 아래 값은 좌표 읽기의 기술적 요약이며 pixel RGB RMSE·관절 정답 오차·통계적 성능이 아니다. [전체 집계](OUTPUT_EVALUATION.json), 실제 좌표·20항목·판독 패널·재현 코드는 비공개 ZIP에 있다.

| 사전 고정 집계 | 변위 수 | STATIC COPY 잔차 평균 | 생성 잔차 평균 | 생성 변위 평균 |
|---|---:|---:|---:|---:|
| 전체 | 20 | 16.5407px | 3.5212px | 17.0948px |
| 코·양눈 | 12 | 18.0420px | 2.2804px | 16.2836px |
| 양앞발, UNCERTAIN 포함 | 8 | 14.2887px | 5.3823px | 18.3117px |

원본과 출력의 머리는 초반에서 중간까지 위·왼쪽으로 이동하고 후반에는 오른쪽으로 돌아오는 순서가 대응했다. 확대 패널과 이 raw 측정은 **단순 f0 정지 복사보다 원본의 화면 변화에 대응한다는 기술적 근거**를 제공한다. 작은 시트만으로는 이 대응이 명확하지 않았으며 확대 관찰을 통해 확인했다. 다만 source의 기존 반경합 평균19.4222px와 출력의 미보정 오차 때문에 개선율·유의성·정밀한 우월성은 선언하지 않는다. 생성 잔차의 원자료 범위는0~7.0711px, 정적 복사는1~28.4605px다. 이 min/max는 신뢰구간이 아니다.

몸 전체 크기와 위치도 달라지므로 화면 변화의 대응을 관절 안무 성공으로 올리지 않는다. 앞발의 상대 동작·정확한 타이밍, 목·발끝의 세밀한 형상과 접촉·반사 물리는 불확실하다. 큰 붕괴가 없다는 정적 관찰은 미세 형태나 시간 안정성 수용이 아니다. 같은17프레임에서 driving을 정적 입력으로 바꾼 생성 대조군이 없으므로, 조건 경로의 인과적 활용량도 식별하지 못한다. B-009는 참조·text가 다른 맥락 자료일 뿐이다.

| 평가 수준 | 판정 |
|---|---|
| A: 원본의 화면상 시간 변화 | 대응 근거 있음, 탐색적·서술적이며 불확실성 보정 우월성 미입증 |
| B: 전체 이동·scale과 분리한 부위 운동 | INCONCLUSIVE |
| 외형·형상 | 원본과 닮은 외형·큰 실루엣 유지, 큰 붕괴 미관측; 발끝 등 세부 UNCERTAIN |
| 통합 gain | UNDEFINED, 생성 전 규칙 유지 |
| 실제 속도 연속 재생 품질 | UNVERIFIED |
| C: Lab 전이·일반화·물리 접촉·전체 춤 | NOT_RUN |

연속 재생을 직접 시청하지 않았으므로 파일 전체 decode와 사람이 시간 품질을 검수한 사실을 혼동하지 않는다. 전체17장 고정 그룹·원본/정적 복사/생성/B-009 맥락용24fps 비교MP4·프레임별 로컬 검토 자료를 제공한다. 영상 반복의 끝→처음 경계는 내부 동작 평가와 구분한다.

## 자원·보존·검증의 한계

S의 최소 시스템 MemAvailable은52.86GiB, cgroup peak62.01GiB, 관측된 CUDA allocator peak33.83GiB였다. 서로 다른 회계이므로 더해서 총 메모리로 쓰지 않는다. swap0,oom/oom_kill0, cgroup high3357이며 high 이벤트를 숨기거나 OOM으로 잘못 세지 않는다. 기존24GiB runtime headroom·swap0·타 서비스 보호 조건을 유지했다. [단계별 실측](MEASUREMENTS.json).

종료 후 보존 해시540개와 자기 unit inactive/MainPID0를 확인했다. A·기존 환경·다른 서비스는 변경하지 않았다. CPU fixture8개와 syntax/핵심 lint는 통과했다. 상속된 B-010 기반 코드의 targeted typecheck81오류는 **NOT_CLEAN**으로 남겼고 이번 범위 밖의 리팩터링이나 무시 주석으로 숨기지 않았다. [검증 범위](STATIC_VALIDATION.json).

동일 개체 자기 재현은 Lab로 바꾸는 cross-identity 전이의 증거가 아니다. Lab/IG 개체·체형/전체 춤/접촉 물리/일반화/Kling 수용은 NOT_RUN이다. [한국어 수학·코드 설명](../../lessons/B-011-measurement-and-generative-diagnostics.md), [재현 명령](REPRODUCE.md)을 함께 제공한다.

비공개 ZIP은 Spark에서 만들고 Mac으로 전송한 뒤 CRC·290개 payload·전체 ZIP SHA256을 검증했다. [전달 영수증](DELIVERY.md). 공개 저장소에는 개인 미디어·좌표·cache·latent·가중치를 포함하지 않는다.

## 다음 한 작업

기존 원본에서 머리·앞발의 상대 움직임이 더 명확한 짧은 구간을 **source-only로 검토**한다. 같은17장 재주석을 반복하거나 그 새 구간을 이번에 생성하지 않는다. 추가 sampler·seed·학습·모델 변경은 실행하지 않았다.

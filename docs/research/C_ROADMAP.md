# C 연구 현재 상태

C-002의 실제 네 신규 영상이 완료됐다. 기존 C-001의 두 ENDPOINT와 같은 앵커를 비교했으며, 차량은 **TRADE_OFF**, 개는 **COARSE_CONTROL_ONLY**다. 개의 정면 접근과 거친 진행은 개선됐지만 내부 자세·접촉은 미해결이다. 차량은 일부 진행 이득과 보호 장면 손상이 동반됐다. 기본 채택하지 않으며 temporal=UNVERIFIED다. [결과](experiments/C-002-sam-layout-conditioning/RESULTS.md) · [해설](experiments/C-002-sam-layout-conditioning/LESSON_KO.md) · [비용](experiments/C-002-sam-layout-conditioning/COSTS.json).

운영: 기존 C-001 보호 경로를 변경 없이 재사용했다. 네 실제 CPU 경로와 네 heavy가 완료됐고, 새 영상마다50step/100call/33frames다. 추가 imagegen/SAM/학습/다운로드/품질 재시도/복구는0이다. 실제 noise가 MOV/STILL에서 같고, context는 다르며 mask64는 같음을 확인했다.

C-001의 PIPELINE_COMPLETE와 차량 MOTION_PARTIAL / 개 MOTION_FAIL / IDENTITY_PARTIAL / SCENE_PARTIAL / temporal UNVERIFIED는 당시 결과로 보존한다. A/B의 실패·UNKNOWN·운영상 보류는 수정하지 않았다. [C-001 결과](experiments/C-001-hybrid-endpoint-baseline/RESULTS.md).

다음 논의 후보는 머리·팔다리의 시간별 객체 내부 대응 하나다. 새 모듈·추가 seed·학습·backend·업스케일·장영상·GPU 실행은 시작하지 않았다. 이번 네 결과와 두 기준선을 함께 검토한 뒤 다음 개입을 정한다.

## C-003 운영상 보류

사용자 승인으로 개 한 사례의 공식 scribble 내부 시간정보 DYNAMIC/HOLD 두 조건을 구현했다. 실제 시작 guard가 START_SWAPOUT_OBSERVED로 차단하여 추출/영상0으로 종료했다. **INCONCLUSIVE/BLOCKED_SAFETY**, 내부 동작 효과·외형 손해 미평가다. 전역 발생 주체UNKNOWN이며 가드정책을 바꾸거나 자동재시도하지 않았다. 다음 구조 선택을 뒷받침할 새 생성 근거는 없다. 기존 C-002 두 판정과 C-001/A/B 이력은 그대로다. [C-003 결과](experiments/C-003-internal-structure-conditioning/RESULTS.md).

## C-003 명시적 amendment 이후 완료 (2026-10-29)

기존 시작 swap-out>0 추가 분기만 승인대로 제거하고 나머지 보호를 유지했다. 공식 FP32 scribble33장1pass와 DYNAMIC/HOLD 영상2개(각50step/100call)를 실제 완료했다. 동일 noise/G와 실제 context 전달을 확인했지만 내부 진행 이득은 NO_ESTABLISHED_GAIN, 국소 배경 손상이 관측되어 기본 채택하지 않는다. temporal=UNVERIFIED. 이전 안전 보류와 A/B·C001/C002 판정은 보존한다. 다음 후보는 가시성·신뢰도를 포함한 시간별 내부 대응이며 추가 실행은 사용자 검토 뒤 결정한다. [실제 결과](experiments/C-003-internal-structure-conditioning/RESULTS.md).

## C-004 종료 앵커 진단 완료 (2026-10-30)

Native1회로 끝 앵커를 부분 교정(PARTIAL_BUT_USABLE)하고, C002 동적 윤곽·시작·모델을 유지한 새 영상1개(50step/100call)를 완료했다. 실제 RGB32만 변경·noise/G 동일을 확인했으나 영상은 NO_ESTABLISHED_GAIN이다. 얼굴 방향/높이 변화와 국소 배경 손상은 있으나 중간 머리·발 진행이나29–31 종료 전환 개선은 미입증이다. 약한 앵커 교정으로 원인을 단정하지 않으며 temporal=UNVERIFIED, 기본 채택하지 않는다. 기존 이력은 보존하고 추가 앵커 튜닝을 종료한다. 다음 논의는 부위 ID·시간 대응·가시성·신뢰도의 실제 생성 연결이며 자동 실행하지 않는다. [결과](experiments/C-004-end-anchor-consistency/RESULTS.md).

## C-005 공식14B 비교 — 첫 적재 안전 중단 (2026-10-30)

동일 C-002 앵커/동적 윤곽으로 공식 VACE14B 차량→개 비교를 사전 고정했다. 공식7shards/hash와 CPU/meta1331key/shape, 동일 X/G/텍스트 및 두 CPU route를 확인했으나 차량 첫 적재에서 시스템 PSI full10초비율14.08681%로 기존 가드가 중단했다. Heavy1소진, forward/step/새영상0, 개/예비/설정변경 미실행이다. Raw NOT_CLEAN 및 종료 cgroup 관측 실패를 보존하며 원인UNKNOWN, OOM 재분류 없음이다. 품질 INCONCLUSIVE/비교미완료,14B 채택 근거 없음, 기존1.3B는 실행 가능한 기준선으로 유지한다. 과거 판정을 바꾸거나 자동재개하지 않는다. [실제 결과](experiments/C-005-vace-backbone-comparison/RESULTS.md).

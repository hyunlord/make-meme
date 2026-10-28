# C 연구 현재 상태

C-002의 실제 네 신규 영상이 완료됐다. 기존 C-001의 두 ENDPOINT와 같은 앵커를 비교했으며, 차량은 **TRADE_OFF**, 개는 **COARSE_CONTROL_ONLY**다. 개의 정면 접근과 거친 진행은 개선됐지만 내부 자세·접촉은 미해결이다. 차량은 일부 진행 이득과 보호 장면 손상이 동반됐다. 기본 채택하지 않으며 temporal=UNVERIFIED다. [결과](experiments/C-002-sam-layout-conditioning/RESULTS.md) · [해설](experiments/C-002-sam-layout-conditioning/LESSON_KO.md) · [비용](experiments/C-002-sam-layout-conditioning/COSTS.json).

운영: 기존 C-001 보호 경로를 변경 없이 재사용했다. 네 실제 CPU 경로와 네 heavy가 완료됐고, 새 영상마다50step/100call/33frames다. 추가 imagegen/SAM/학습/다운로드/품질 재시도/복구는0이다. 실제 noise가 MOV/STILL에서 같고, context는 다르며 mask64는 같음을 확인했다.

C-001의 PIPELINE_COMPLETE와 차량 MOTION_PARTIAL / 개 MOTION_FAIL / IDENTITY_PARTIAL / SCENE_PARTIAL / temporal UNVERIFIED는 당시 결과로 보존한다. A/B의 실패·UNKNOWN·운영상 보류는 수정하지 않았다. [C-001 결과](experiments/C-001-hybrid-endpoint-baseline/RESULTS.md).

다음 논의 후보는 머리·팔다리의 시간별 객체 내부 대응 하나다. 새 모듈·추가 seed·학습·backend·업스케일·장영상·GPU 실행은 시작하지 않았다. 이번 네 결과와 두 기준선을 함께 검토한 뒤 다음 개입을 정한다.

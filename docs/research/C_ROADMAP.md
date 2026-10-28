# C 연구 현재 상태

C-001 **PIPELINE_COMPLETE**: 실제 native imagegen 앵커4장, SAM source66프레임+4앵커 분석, VACE1.3B firstlastframe 영상2개를 확보했다. 각 영상33프레임·50step·100 model_fn call이며 heavy 복구0이다. [결과](experiments/C-001-hybrid-endpoint-baseline/RESULTS.md) · [수학/코드 해설](experiments/C-001-hybrid-endpoint-baseline/LESSON_KO.md) · [비용](experiments/C-001-hybrid-endpoint-baseline/COSTS.json).

운영: C 전용 사본의 정상 종료 관측 순서만 수정했고 실패 CPU 영수증을 보존했다. 실제 SAM/영상 heavy 보호 실행과 자원 회수는 완료했다. B-034 운영 보류와 A/B 이력은 변경하지 않았다.

과학적 결과: 두 사례 모두 ANCHOR_PAIR_PARTIAL / IDENTITY_PARTIAL / SCENE_PARTIAL. 차량 MOTION_PARTIAL, 개 MOTION_FAIL, temporal=UNVERIFIED. SAM 분석은 수행했으나 생성 입력으로 쓰지 않았다. 외형 교체가 보이는 첫 hybrid 기준선이며 원본 동작·장면 보존을 충족한 기본 시스템으로 채택하지 않는다.

다음은 같은 앵커를 유지한 객체 운동 조건 연결 대조를 사용자와 설계하는 단계다. C-002 구현·추가 seed·학습·다른 backend·업스케일·장영상은 시작하지 않았다.

C-002 사전고정: C-001의두ENDPOINT와동일앵커를재사용해차량MOV/STILL→개MOV/STILL4셀을실행한다. 중간RGB만SAM윤곽으로바꾸고동일G/모델/seed/caption을유지한다. 실제노이즈일치/조건전달과품질효과를분리해검토한다. [C-002계획](experiments/C-002-sam-layout-conditioning/PLAN.md). 추가imagegen/SAM/학습/패키지0.

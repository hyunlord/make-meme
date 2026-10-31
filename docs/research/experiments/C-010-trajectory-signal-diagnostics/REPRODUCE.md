# C-010 재현 경로

공개 저장소에는 경로·tensor·영상을 넣지 않는다. Spark의 C-010 디렉터리(비공개 config, stage 로그, METRICS 원본)가 보존 자료다.

1. 단계 A (CPU): `code/input_contrast.py <config>`. C-009 white cache와 C-006 point exclusion, C-006 source 프레임을 쓴다. 출력은 `INPUT_CONTRAST.json`, `tracks-*.jpg`, 사전 FD track 선택이다.
2. PLAN 커밋(`91287fe`) 뒤, `code/make_stage.py`(`C010_STAGE_SETTINGS`)로 cpu/heavy stage를 만든다. 기존 C-001 `run_guarded.py`와 C-003 guard로 실행한다.
3. `code/diagnose_signal.py <config>`: config는 C-009 runtime(cache_root=cache-white, phase=train), C-009 checkpoint 000/128/256 sha, C-007 probe_grid, 단계 A 결과, C-009 NEW_ON_5 trace, C-007 elephant sidecar를 가리킨다.
   - 단계 B: `adapter_trace` 사본으로 72회 계산하고, 매번 원본 출력과 equal인지 확인한다.
   - 단계 C: 84 forward. `observed_forward` 사본을 쓰며, 원본과 4회 bit-exact 대조, 반복 2회.
   - 단계 D: 16 forward + 16 VJP. optimizer 없음, parameter 불변 확인.
   - 단계 E: FD 12회.
   - rollout: 9회.
4. 뷰어: Spark에서 `review/` 그래프를 METRICS로 그리고, C-009 review의 MP4를 byte copy한다.

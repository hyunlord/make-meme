# C-011 재현 경로

공개 저장소에는 경로·tensor·영상을 넣지 않는다. Spark C-011 디렉터리(비공개 config, stage 로그, cache, checkpoint, 생성물)가 보존 자료다.

1. `code/make_stage.py`(`C011_STAGE_SETTINGS`)로 stage를 만든다. 모두 기존 C-001 `run_guarded.py`와 C-003 guard로 cpu→heavy 순서로 실행한다.
2. `rebuild`: `code/rebuild_endpoint_cache.py`로 C-009 cache-white 10개에서 vace_context만 E로 바꾼다. 결과는 `cache-endpoint/` + `CACHE_MANIFEST.json`.
3. `live-parity`: `code/live_parity_endpoint.py`. C-009 `gen/generate_video.py`의 `condition()`과 C-008 `encode_probe.run_g_prepare`를 쓴다.
4. `train`: `code/train_endpoint.py <C-009 train_white.py> <C-006 train_adapter.py> <config>`. 끝나면 C-009 `code/train_replay_check.py <C-009 train-white> <C-011 train-endpoint> <out>`.
5. `probes`: `code/probe_families.py`. C-010 `signal_common`(decompose·seed)과 C-007 probe_grid를 쓴다.
6. 영상 8개: C-009 `gen/generate_video.py`(수정 없음). config는 C-009 `NEW_ON_5.json`에서 output·anchor·prompt·condition_mode·layout_dir·cache_file·adapter_mode·checkpoint만 바꾼 것이다. 순서: E elephant BASE→ON→NULL, E goat BASE→ON→NULL, L goat BASE→ON.
7. 사후 CPU: 첫 model_fn context sha 대조, 블라인드 시트(A–E, key seed 20261101), source 객체 ROI 보조 지표.

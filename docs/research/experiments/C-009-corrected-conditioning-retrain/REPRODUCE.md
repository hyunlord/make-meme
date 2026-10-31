# C-009 재현 경로

공개 저장소에는 tensor·미디어·경로를 넣지 않는다. Spark의 C-009 실행 디렉터리, 비공개 config(`configs/*.json`, `stage-settings.json`), stage 로그는 로컬 보존 자료다.

1. `code/make_stage.py`(`C009_STAGE_SETTINGS`=비공개 경로 설정)로 C-007과 같은 cpu→heavy stage를 만든다. 실행은 기존 C-001 `run_guarded.py`와 C-003 guard를 변경 없이 쓴다.
2. `rebuild`: `code/rebuild_cache.py` → `cache-white/`(12), `cross-cache-white/`(1), 각 위치의 `CACHE_MANIFEST.json`(white_v1, 새 sha와 legacy sha).
3. `live-parity`: C-008 `code/encode_probe.py`를 G 모드로 elephant·goat에 실행한다. `tensors.pt`를 새 cache와 CPU에서 비교한다.
4. `train`: `code/train_white.py <C-006 train_adapter.py> <config>`. config는 C-006 `train-v2.json`에서 `cache_root/output/deadline_epoch`만 바꾼 것이다(resume 원본: C-006 `outputs/train/checkpoint-000.pt`).
   이어서 `code/train_replay_check.py <train-v2> <train-white> <out>`(CPU)를 실행한다.
5. `probes`: `code/probe_white.py`. C-007 code(metrics, forward)와 INFERENCE_INPUT_MANIFEST의 probe_grid를 쓰며, runtime cache_root=`cache-white`.
6. 영상: `code/gen/generate_video.py`(C-007 사본 + NULL 2줄)로 `NEW_ON_1`, `NEW_ON_5`, `NEW_NULL_5`를 만든다. config는 C-007 `ON_1/ON_5`에서 output/adapter_checkpoint/adapter_mode/guidance만 바꾼 것이다. sidecar는 C-007 `sidecars/elephant.pt`(clean_latent 없음).
7. 비교: 각 출력의 `first-model-input.json`, `trace/contexts.pt`, `condition.json`을 C-007 BASE/ON과 대조하고(`PARITY.json` generation_first_model_input), 프레임 픽셀 차이를 계산한다(`PARITY.json` video_pixel_differences).
8. `code/test_mask_contract.py`: 흰 마스크는 통과하고, legacy 빨강은 3채널 검사에서 실패하지만 채널0 비교로는 통과함을 확인한다.

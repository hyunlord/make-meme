# C-006 재현 경로

이 문서는 실제 사용한 함수와 순서를 설명한다. 공개 저장소에는 미디어·모델·개인 경로·checkpoint를 포함하지 않는다. 원본 입력과 출력, 비공개 절대경로 config/freeze는 검토 패키지의 manifest 및 로컬 full 보존 자료로 연결한다. 같은 입력이 없으면 아래 순서만으로 결과를 재현했다고 주장할 수 없다.

1. DATA_SPLIT에 고정한 12개 DAVIS 원본의 첫 33프레임과 선택 객체 mask를 `data_prepare.py`로 416×240 aspect-fit한다. RGB는 Lanczos, mask는 nearest다. source FPS는 알 수 없으며 preview만 16fps다.
2. 공식 CoTracker3 offline의 고정 code/checkpoint를 `track_points.py`로 호출한다. 최초 객체 영역에서 선택한 최대 16개 표면점을 한 번 추적하고 raw tracks를 보존한다. TRACK_REVIEW의 명백한 이탈은 별도 exclusion sidecar에 기록한다. 재추적이나 새 점 보충은 하지 않는다.
3. `cache_conditions.py`에서 두 anchor를 각각 독립 VAE 인코딩한다. T5, encoded VACE context, endpoint patch, tracks를 저장한다. 학습/검증의 clean latent는 target으로만 저장하고 heldout cache에는 넣지 않는다.
4. TRAIN_CONFIG대로 `train_adapter.py`를 실행한다. 첫 정상 update에 native/bypass/zero 일치와 late block/head gradient를 확인한다. 동일한 FP32 adapter만 최적화하고 256 updates 후 마지막 checkpoint를 사용한다. validation은 고정된 6개 noise/timestep probe이며 최종 checkpoint 선택 탐색에 쓰지 않는다.
5. `generate_video.py`에서 각 heldout의 BASE → ON → NULL을 생성한다. BASE는 native model_fn, ON/NULL은 동일한 학습 함수와 checkpoint를 사용한다. 실제 condition RGB, generation mask, noisy latent hash를 비교한다. 양끝 프레임을 덮어쓰지 않고 저장된 final latent의 readback, raw tensor, 33개 PNG와 MP4를 보존한다.
6. 선택적 기존 개 진단에서는 `cross_track.py`의 수동 대응된 얼굴 3점을 추적하고 `cross_cache.py`의 bbox 비율 기반 endpoint retarget를 적용한다. 이는 HEAD_ONLY 탐색이며 다리·관절 제어 실험이 아니다. 기존 C-001 두 anchor만 사용한다.
7. `build_review.py`는 위 실제 출력으로 검토 뷰어와 시트를 만든다. 원본 생성 MP4는 바이트 그대로 복사하고 비교 MP4/thumbnail은 새 파생물로 표시한다. 파일 재생 가능성은 temporal 품질 검수와 다르다.

모든 GPU 단계는 기존 `run_guarded.py`와 C-003의 현행 guard를 통해 순차 실행했다. CPU 경로, config, 입력, 코드, guard를 각 stage freeze로 고정한다. 과거 실패 stage는 삭제하거나 정상 결과로 바꾸지 않는다. 실제 resource/external guard 중단 시 자동 재시도하지 않는다.

기계적 복구 두 건은 cache endpoint patch의 CPU/CUDA grid 불일치와 사용되지 않는 native y branch에 관한 과도한 assert였다. 전자는 device만 수정했고, 후자는 native y=None 동작과 맞추어 assert를 제거했다. 학습은 저장된 step 0 상태에서 재개했으며 학습 완료 후 중간 trained checkpoint부터의 연속 재개는 실행하지 않았다.

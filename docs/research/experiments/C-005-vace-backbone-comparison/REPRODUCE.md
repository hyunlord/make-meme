# 재현 범위

전체 계약과 입력 고정은 [PLAN](PLAN.md), 정확한 공식 파일은 [MODEL_MANIFEST](MODEL_MANIFEST.json), 메모리 경로는 [BACKEND_COMPARISON](BACKEND_COMPARISON.md)에 있다. C-002의 원래 case_rigid/case_nonrigid layout_mov 설정에서 weights/model_index/shared_weights/output/native offload만 바꾸고, C-001 원래 양끝과 C-002 layout33장을 재사용한다.

1. 공식 pinned revision의 config/index와 정확한7shards를 확보하고 byte size/SHA256·header key/shape·native CPU/meta 대응을 검증한다. downloader는 이미 받은 파일을 다시 복사하지 않는다.
2. 기존 절대경로 계약으로 각 case config를 해석한다. `video_generate.py CONFIG --cpu-only`는 실제 조건과 compressed G를 검사하고 CUDA 초기화/모델 적재 없이 종료해야 한다.
3. 기존 C-001 run_guarded.py 및 현재 C-003 guard 사본을 그대로 쓰고 각 stage에 기존 adapter의 worker.py, configs/service-policy.json, reports, config/freeze를 준비한다. 공통 lock·external allowlist 비어 있음·현재 boot identity·기존 memory 보호를 유지한다.
4. CPU route COMPLETE 영수증과 같은 경로의 실제 heavy를 차량→개 순서로 각각 한 번 실행한다. 새 launcher나 예제 full sampler는 없다. Heavy 시작과 실패는 장부에 보존한다.
5. 각 원래 model_fn 첫 호출에서 noise/context/mask를 기록하고 scheduler50 종료 latent를 decode 전에 저장/readback한다. raw/PNG33/MP4와 stage-cost를 보존한다. 추가 forward/재생성은 없다.
6. `build_review.py C001_PRIVATE C002_PRIVATE C005_PRIVATE REVIEW_ROOT`로 private 미디어를 모으고 실제 생성 MP4 byte를 보존한다. 새 비교 MP4·JPEG 시트는 파생물로 표시한다. 양 host에서 ZIP CRC·manifest hash·실제 추출·전송 SHA를 검증한다.

실제 경로·PID·raw log·가중치·미디어는 공개 저장소에 포함하지 않는다. 공개 코드만으로 접근 권한 없는 원본 미디어가 자동 확보된다고 주장하지 않는다. source_fps=null이며16fps는 검토 timebase다. 한 seed의 두 개발 사례를 일반 성능으로 확대하지 않는다.

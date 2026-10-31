# C-012 재현 경로

공개 저장소에는 코드·문서·hash만 있다. task 프레임·cache·checkpoint·생성물·외부 가중치는 Spark C-012 디렉터리에 비공개로 보존한다.

1. `code/render_task.py <task>` (CPU): 공·배경·A/B 경로·mask·layout·9점 tracks를 만든다. `TASK_MANIFEST.json`은 파일 sha다.
   `code/evaluate.py <task>` (CPU): fixture → `FIXTURES.json`.
2. 모든 GPU 단계는 기존 C-001 `run_guarded.py` + C-003 guard를 쓴다(cpu → heavy). stage는 `code/make_stage.py`(`C012_STAGE_SETTINGS`)로 만든다.
3. `build`: `code/build_cache.py`
   - endpoint VACE context는 A/B 공유
   - 양끝은 독립 encode
   - A/B target encode, 재구성 decode 2
4. 생성: `code/gen/generate_video.py`(C-009 사본, seed literal만 20261029까지 허용). CFG1, Euler50, shift5, 416×240×33.
   - BASE: endpoint, adapter OFF
   - LAYOUT_A/B: `layout_mov`, `task/{A,B}/layout`
   - ON{256,1024,2048}_{A,B}: endpoint, adapter ON, sidecar `path_{A,B}.sidecar.pt`
   - ON2048_S2_{A,B}: seed 20261029
5. 학습: `code/train_capability.py`, segment config `stop_at` 256 → 1024 → 2048.
   - segment 1은 C-006 `outputs/train/checkpoint-000.pt`의 adapter 값만 쓴다(train seed 20261104).
   - 이후 segment는 이전 checkpoint에서 전체 상태를 이어받는다.
6. DragAnything
   - 코드: showlab/DragAnything @ `79355363218a7eb9b3437a31b8604b6d436d9337`
   - 가중치(fp16 파일, fp32로 실행):
     - SVD img2vid @ `9cf024d5bfa8f56622af86c884f26a52f6676f2e`
     - weijiawu/DragAnything @ `f66fb7cc44da731feae9393c7ba4959bd1daf37d`
     - windwhinny/chilloutmix @ `e0bf5daebbfb76e757baaf4ce88e0c1cc4df7525`
   - 격리 venv 패키지: transformers 4.36.2, huggingface_hub 0.20.3, accelerate 0.25.0, tokenizers 0.15.2, peft 0.7.1. Torch는 기존 2.14+cu130을 `.pth`로 공유한다.
   - wrapper: `code/run_draganything.py`(config의 `isolated_site_packages`, `repo`).
7. 판독: `code/score.py <task> pair <A> <B> <N> <out>` (DragAnything은 N=20, `eval416_*` 역 letterbox 사본).
   검토: `code/build_review.py <root> <out>` + `code/viewer.html`, `code/sheet.py`.

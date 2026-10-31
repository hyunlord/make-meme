# C-008 재현 경로

공개 저장소에는 tensor·경로·가중치를 넣지 않는다. Spark 실행 디렉터리, 비공개 config, 원본 report는 로컬 보존 자료와 DELIVERY의 manifest로 연결한다.

1. `code/encode_probe.py`는 기존 research Python과 기존 DiffSynth 사본으로 실행한다 (`wan_video_vae.py` sha256 17ad9aa4…, `wan_video.py` e3ab58df…, torch 2.14.0+cu130).
2. `code/make_stage.py <exp_root> <name> <script> <probe-config>`는 C-007과 같은 cpu/heavy stage(config, freeze, service-policy, worker copy)를 만든다. guard 코드·한도는 바꾸지 않는다.
3. 각 stage는 `<python> C-001/code/run_guarded.py <stage-cpu>`, 이어서 `<stage-heavy>` 순으로 실행했다. 실행 순서:
   - `c-elephant` (path=C, legacy mask): C_new vs cache-v2 저장물, vs C-007 G 저장 context, 반복, endpoint/patch/target.
   - `g-elephant` (path=G): C-007 `condition()`+`pipe(...)`를 `progress_bar_cmd`에서 denoise 직전에 중단. 같은 프로세스에서 C식 직접 호출도 한다.
   - `c-fixed` (path=C, mask_fill=white, elephant+goat): 수정 C, causal 의미 검사, 수정 validation cache 2개 저장 (`vace_context`만 교체).
   - `g-goat` (path=G, goat): 독립 G와 legacy C 대조.
4. 교차 프로세스 비교는 각 stage의 `tensors.pt`를 CPU에서 읽어 `compare()`로 한다. 결과는 `PARITY.json`의 `cross_process`.
5. 공개 `make_stage.py`는 실행본(sha256 c18eb5d9848c6ef9bfc64dc3050b6bd72d7e451f8060c863695c298e6bf0c238)에서 경로 상수만 비공개 settings JSON으로 옮긴 형태다. 로직은 같다.
6. `code/test_generation_mask.py`는 PIL int fill(빨강)과 수정 fill(흰색)을 확인하는 CPU 회귀 테스트다.

hook은 입력·cache·RNG·출력을 바꾸지 않는다. 관측을 켠 G 결과는 C-007이 관측 없이 저장한 context와 exact로 같았다.

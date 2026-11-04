# V-002 재현 기록

개인 자료·절대경로는 private config에만 둔다. 공개 입력 hash는 INPUTS_PUBLIC/MASK_CHECK를 사용한다. 부모 코드를 제자리 수정하지 않고 V002 code와guard사본을 사용한다. 설치·다운로드·새 모델 재학습은 이 경로에 없다.

## CPU 입력

기존 연구Python에서 실제 실행:

```sh
${RESEARCH_PYTHON} ${V002}/code/prepare_inputs.py ${V002}/configs/prepare-inputs.json --cpu-only
nice -n 10 ${RESEARCH_PYTHON} ${V002}/code/prepare_inputs.py ${V002}/configs/prepare-inputs.json
```

첫 검사는369입력,73프레임,torch미수입을 확인했다. 실제 제작은새prepared폴더에원자저장하고MASK_CHECK readback을남겼다. 기존 E1원본MP4는ffmpeg -vsync 0 -start_number 0으로nativePNG73장씩디코드했다.

## 기존 guarded stage

기존C012 make_stage.py build()와C001 run_guarded.py를재사용한다. private stage-settings의python/guard/adapter/policy_template/vae는인수한절대경로다. CPU/heavy config모두allocator환경변수를동일하게넣고,heavy에는MEMORY_PREFLIGHT의estimate와basis를넣는다. policy attempt_id는C001_V002_APPROVED_01. workermax는남은시간을넘지않으며deadline은2026-11-04T12:46:38Z다. freeze는config/policy/worker/script와모든동작Python코드,guard/uma.py 및실제입력파일hash를포함한다. stage생성뒤내용을바꾸지않는다.

```sh
${RESEARCH_PYTHON} ${C001}/code/run_guarded.py ${V002}/stages/v002-sam-baseline-e1-20261103-cpu
```

위 최초CPU시작관측은외부GPU프로세스로UNKNOWN_GPU_PID 거절됐다. 모델적재0/SAM0. 이를CPU_PASS나엔진실행으로표현하지않는다. rawstart-samples와거절stage는보존한다. 후속명령·완료내역은실행뒤RUNS에추가한다.

## 준비된 모델 설정

M1/M2/M3 privateconfigs는vace_entry.py에입력한다. 50step/100modelcalls,CFG5,shift16,기존Euler,seed20261103. 모델·환경import와GPU작업은동시에실행하지않는다.14B는128GiB사전추정으로차단되어probe/생성명령을실행하지않는다. LTXcanny는부모official_args에서조건영상과출력경로만교체하고새앵커·seed·strength를추가하지않는다.

SAM은동일기존ComfyUI SAM3.1,dog,threshold0.5,maxobjects4,detect_interval1을재사용한다. 출력마다native좌표로mask를저장한후metrics.py에서canonical역변환한다. `metrics.py CONFIG OUTPUT`, `selection.py CANDIDATES OUTPUT`, `metrics_sheet.py CONFIG SHEET`은모델을실행하지않는CPU단계다.

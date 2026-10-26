# B-031 재현 범위

공개코드·설정은 연구용이며 원본모델·DAVIS 입력·조건cache는 별도 로컬 자료다. 재현 명령을 적는 것은 추가 생성 허가가 아니다. 이미 생성/실패한case를 다시 실행하면 사용량이 증가하므로 이번 장부에서는 자동재시도하지 않는다.

## 이미지 단계

Qwen 모델revision·pipeline·격리환경·lock과 실행 명령은 [ENVIRONMENT](ENVIRONMENT.md) 및 이미지 실행코드를 따른다. 영상 모델과 동시에 적재하지 않는다. 실제 입력순서/이미지hash는 [INPUTS](INPUTS.md)를 따른다. 생성앵커가 미실행/실패이면 영상준비를 건너뛴다.

## 조건부 영상 준비

환경변수는 비공개 실제 경로의 별칭이며 공개 문서에는 개인 절대경로를 넣지 않는다.

```bash
# 기존 고정 SCAIL Python을 재사용한다. 신규 설치/환경 upgrade 없음.
"$SCAIL_PYTHON" -m pytest "$B031_CODE/video_code/test_anchor_contract.py" -q
"$SCAIL_PYTHON" "$B031_CODE/video_code/prepare_video.py" \
  "$B031_RUN/video/tasks/$TASK" "$B027_RUN/tasks/$TASK" \
  "$B031_RUN/anchors/$TASK/R1" "$B031_CODE/video_code"
"$SCAIL_PYTHON" "$B031_CODE/video_code/freeze_run.py" \
  "$B031_RUN/video/tasks/$TASK"
```

`TASK`는 animal/human/vehicle 중 사전 R1 적합 판정을 받은 task만이다. 앵커 폴더에는 `reference.png`, `reference-mask.png`, `anchor_suitability.json`이 필요하다. 마지막 파일은 task_id/reference_id=R1, suitable=true, qwen_process_exited=true, 두입력hash를 기록한다. 기록된 종료를 실제 process/resource관측과 확인한 뒤 실행한다. 적합성값을 임의로true로 만들거나 R2로 바꾸지 않는다.

`prepare_video.py`는 기존 root가 있으면 거부한다. source RGB/mask·prompt·negative·seed·noise 계보를 B027 R1에서 가져오며 reference 두경로만 새파일로 바꾼다. 부모캐시는 읽기전용이고 새조건은 별도artifacts에 기록한다. `freeze_run.py`는 코드·config·upstream hash를 실행전에 고정한다. 이 고정 자료를 연구브랜치에 기록한 뒤 GPU를 시작한다.

## 조건부 영상 실행

```bash
bash "$B031_CODE/video_code/run_video.sh" \
  "$B031_RUN/video/tasks/$TASK" "$SCAIL_PYTHON"
```

ENC→PROBE→S→D는 각각 fresh worker다. 각 worker의 exclusive attempt 파일로 중복 실행을 막고, predecessor의 실제 정상종료·MainPID0·result를 확인한다. 어떤 단계든 실패하면 뒤단계를 실행하지 않는다. sampler40step80forward·final latent·finite·17frameMP4를 별도로 확인한다. systemdreturncode0만으로성공판정하지 않는다.

현재코드는 이번 harddeadline에 고정돼 있다. 이 문서의 명령은 만료후 그대로 실행되지 않으며, 미래 새실험은 별도예산과 기록이 필요하다. guard를 임의로완화하거나 만료값만바꿔 재생성하지 않는다.

## 출력과 검증 범위

raw x0/final latent는 CPU lossless tensor tree와 metadata로 남기며 VAE mean/std를 decode wrapper가 적용한다. noise/reference latent를 final로 사용하지 않는다. `raw_output.pt`는 decodedfloat이고 MP4는 공식cache_video로17프레임24fps를 저장한다. source_fps=null/timebase_assumed=true이며 실제원본물리시간을 확인했다는 뜻이 아니다.

ZIP은 별도 전달 단계에서 payload manifest·CRC·실제추출·Mac/Spark동일hash를 검증한다. compact에는 큰raw/latent를 넣지 않으며 compact검증으로그파일까지검증했다고하지 않는다. 영상재인코딩·보정·좋은프레임선별은없다.

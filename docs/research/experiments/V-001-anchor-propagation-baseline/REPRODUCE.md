# V-001 실제 실행 경로

기준c55ff976,사전8ad08a9,배역/해상도개정32e2371,SAM/가드185e769. 실제경로는 private manifest/settings에만 보존한다.

```sh
# 입력 원본에서 각 고정73프레임을1280×720으로 추출
ffmpeg -i "$SOURCE_VIDEO" -vf 'select=between(n\,96\,168),scale=1280:720' -fps_mode passthrough -start_number 0 "$PRIMARY/%03d.png"
ffmpeg -i "$SOURCE_VIDEO" -vf 'select=between(n\,240\,312),scale=1280:720' -fps_mode passthrough -start_number 0 "$FALLBACK/%03d.png"
# 기존 C012make_stage.py를 V private settings로 사용, 새 launcher 없음
C012_STAGE_SETTINGS="$V_SETTINGS" "$PYTHON" "$C012_CODE/make_stage.py" "$RUN_ROOT" sam-primary "$V_CODE/sam_analysis.py" "$PRIMARY_CONFIG"
# 각 stage의 policy attempt_id=C001_V001_APPROVED_01,authorization갱신 후 freeze hash갱신
"$PYTHON" "$C001_CODE/run_guarded.py" "$RUN_ROOT/stages/sam-primary-cpu"
"$PYTHON" "$C001_CODE/run_guarded.py" "$RUN_ROOT/stages/sam-primary-heavy"
# primary미달 후 같은절차로 sam-fallback CPU/heavy 각1회
```

동일 V가드사본이CPU/heavy에 적용되고 실제파일sha가freeze에 포함됐다. 과거 memory state를 덮어쓰지 않았다.
SAM3.1 기존 Comfy commit5cc4b870094c89090db54bd8d12649dcaf89f2ba,querydog,threshold.5,maxobjects4,detectinterval1.
전트랙을 보존했다. 이번에는 source tracking만 실행했으며 image mode와 생성 출력 평가 경로는 NOT_RUN.
표준연구Python torch2.14.0+cu130,추가설치0. 생성 seed는미사용. 구간미달 뒤 자동재시도나신규구간 탐색 없음.

뷰어 검증: 설치된Chrome headless의실제미디어4개metadata와재생/정지/프레임이동/0.5배속/구간전환을CDP로확인했다. 스크린샷을직접확인했다. 연속지각품질은UNVERIFIED. 추가browser패키지설치0.

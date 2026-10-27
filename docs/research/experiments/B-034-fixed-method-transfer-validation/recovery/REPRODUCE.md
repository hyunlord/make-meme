# RECOVERY_01 재현과 비재시도 계약

공개 `CODE_FREEZE.json`은 실행 모듈과 재사용 helper/VAE 소스를 고정한다. private config에는 부모 root·기존 upstream/models 경로·기존 허용 GPU PID identity·VAE SHA가 있으며 공개하지 않는다. 실행 환경은 기존 B007E 격리 Python이다. 새 패키지 설치는 없다.

```sh
"${EXISTING_PYTHON}" "${RECOVERY_ROOT}/code/test_safety.py"
"${EXISTING_PYTHON}" "${RECOVERY_ROOT}/code/artifact.py" "${RECOVERY_ROOT}"
"${EXISTING_PYTHON}" "${RECOVERY_ROOT}/code/launch.py" "${RECOVERY_ROOT}"
```

마지막 명령은 RECOVERY_01 최초 허용 시도에만 사용한다. attempt 파일은 exclusive-create이며 완료·실패 후 삭제하거나 재실행하지 않는다. 과거 deadline이 지났다면 이 명령으로 새 실행을 시작하지 않는다. 신규 sampling/encoder/CONTROL/STEP 경로는 없다.

`launch.py`는 복구 전용 watchdog을 만들며 ExecStopPost는 이 복구 VAE unit만 가리킨다. `supervisor.py`는 hash·artifact receipt·새 queue/GPU PID identity·72GiB 시작/swap0를 확인하고 최대600초 worker를 실행한다. 실행중24GiB/swap0 가드는 유지된다. 관측 실패는 fail-closed다. 과거 `run_phase.py`와 predecessor는 변경하지 않는다.

`worker.py`는 parent exact latent를 재검증하고 WanVAE만 로딩한다. 공식 BF16 autocast 경계와 `vae.decode([latent.to('cuda')])[0]`를 유지한다. model-space scaling은 wrapper 내부에만 있다. raw 저장 후 PNG의 uint8 변환은 `floor((clamp(x,-1,1)+1)*127.5)`다. MP4는 새 파생물로 fullRGB→limitedBT709/yuv420p, libx264 CRF18,24fps를 사용한다. 원본 source bytes는 변경하지 않는다.

출력 계약은 `[3,17,512,896]` finite다. ffprobe와 전체 ffmpeg decode로 포맷을 확인하지만 시간적 미관을 판정하지 않는다. 실제 결과·종료감시는 RECOVERY_RESULTS를 따른다.

실제 재사용 환경 확인: Torch `2.14.0+cu130`, `SCAIL_CONFIGS['SCAIL-14B'].param_dtype=torch.bfloat16`. upstream은 기존 `78fe19576bb06be96c2375e088574a262a300edb` 계보이며 사용 파일의 실제 SHA는 CODE_FREEZE에 고정했다. WanVAE checkpoint SHA256은 `38071ab59bd94681c686fa51d75a1968f64e470262043be31f7a094e442fd981`다. 체크포인트는 worker에서 재해시한 뒤 적재했다. upstream autocast deprecation 경고는 보존하며 새 backend로 바꾸지 않았다.

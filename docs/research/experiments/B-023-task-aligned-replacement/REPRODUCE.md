# B-023 재현 단위와 제한

실행 전 공개 고정 commit: `9bdae0b665beca1b78b07022626bc526770ff7b5`.
환경·기반 가중치는 B020/B022의 기존 격리 환경을 그대로 쓴다. 새 설치 명령은 없다. 개인 미디어와 tensor 저장물은 비공개이며 공개 코드만으로 같은 출력을 만들 수 있다고 주장하지 않는다.

## 필요한 비공개 자산

- `${B020_ROOT}`: 실제 f126..142 입력, reference RGB/마스크, 조건/initial-noise 저장물, producer 코드/receipt.
- `${RUN_ROOT}`: 이번 별도 B023 디렉터리, `producer`는 위 B020을 읽기 전용 참조한다.
- `${PYTHON}`: 검증된 기존 Torch/FA2 격리 Python.
- `${UPSTREAM_ROOT}`: pinned SCAIL-2 `78fe19576bb06be96c2375e088574a262a300edb`, 수정하지 않은 공식 model.
- 기존 Wan safetensors SHA256 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`. 이번에65GB전체를 새로 rehash한 것이 아니라 기존 변환 검증과 로컬 실행 계보를 재사용한다.

## 실제 실행 순서

CPU 단계에서 기존 config와 input receipt를 가져오고 `prepare_layout.py`로 별도 단계 디렉터리를 만든다. `derive_cache.py`는 같은 pinned helper를 직접 import해 기존 마스크 prefix와 exact parity를 확인한 뒤 파생 cache를 저장한다. 부모 저장물을 수정하지 않는다. `freeze_run.py`는 코드·config·upstream·cache receipt를 연결한다. 실제 실행값은 `PREREGISTERED_CODE.json`과 `configs/`에 있다.

```sh
CUDA_VISIBLE_DEVICES='' B023_ROOT="$RUN_ROOT" "$PYTHON" -m pytest "$RUN_ROOT/code/test_replacement.py" -q
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/PROBE" 600 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/PROBE" PROBE
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/S" 3600 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/S" S
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/D" 900 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/D" D
```

단계는 직전 worker가 성공·종료하고 자원이 회복된 경우에만 순차로 실행한다. 명령을 동시에 실행하지 않는다. frozen deadline은 이번 실행을 위한 것이며 무기한 재실행 명령이 아니다. 시도 파일을 삭제하거나 기존 run을 덮어 재시도하지 않는다. 이후 재현에는 별도 사용자 범위·새 실행 기록이 필요하다.

P·target encoding·prefix·optimizer는0이다. S는 양 CFG `replace_flag=True`, vanilla Q/V projection·activeLoRA0, 공식 T/H/W mode kwargs를 확인한다. 실제40step/80forward·유한 final latent를 저장한 뒤 S를 종료한다. D는 해당 저장물만 사용한다. decode 실패로 S를 다시 돌리지 않는다.

## 검증과 해석

입력/캐시 hash는 정확히 비교한다. 이 사실만으로 독립GPU 실행의 byte-identical 출력이나 시각 성공을 요구/주장하지 않는다. 기술 실행은 step/forward/finite/shape/시간축/저장 receipt로, 시각 과제는 raw 전체17장과 local0/8/16으로 별도 판단한다. 같은개체·sourcecopy 한계와 temporal UNVERIFIED는 남긴다.

private ZIP에는 실제 guard/phase 기록·실패·raw/MP4·최종latent·비교자료·runtime/config가 포함된다. 대형 weights와 중복 prefix는 제외한다. 공개 manifest의 `allowed_gpu_processes.json`은 개인 프로세스 정보라 실물은 비공개이고 hash만 남긴다.

비생성 CPU 검토 스크립트와 명령: [review_code/REPRODUCE_MEDIA.md](review_code/REPRODUCE_MEDIA.md). 이 사후 검토 코드는 sampler 사전 고정 코드와 구분한다.

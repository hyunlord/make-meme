# B-024 재현과 입력 계약

실행 전 공개 코드/config commit: `460a5d212548552d304fff63f66e320a4014cbc2`. 기존 환경과 pinned SCAIL-2를 재사용한다. 새 설치는 없다. 개인 입력과 조건 캐시는 비공개이며 공개 코드만으로 동일 출력 재현이 가능한 것은 아니다.

## 부모와 변경점

`${RUN_ROOT}/producer`는 B-023의 읽기 전용 계보다. 실제 reference PNG는 B-020의 전처리 입력과 exact equality를 별도로 확인했다. B-023 conditions SHA256은 `6c531c132c359777d5a12fb535189e857321c44fad85b532126570c969eb3dad`다. 기존 mask/support·RGB driving·text·noise·RNG·scheduler를 보존하고 reference RGB 밖만128로 바꾼다.

`prepare_rgb.py`는 정확한 RED support를 사용한다. `phase_reference.py`는 VAE로 기존 ref/driver latent를 각각 한 번 복원하고 원본/중립 reference를 각각 한 번 encode한다. VAE를 해제한 뒤 CLIP으로 같은 두 reference를 각각 한 번 encode한다. T5/DiT는 이 worker에 없다. 이후 파생 cache의4변경/12보존과 device/container 계약을 확인한다. original reencode max/RMS와 손실 복원의 의미 검토는 별개다.

## 실제 명령 형태

`${PYTHON}`은 기존 검증된 격리 환경이며 `${RUN_ROOT}`는 별도 B-024 경로다. 아래는 실행 기록의 재현 형식이며 추가 호출 승인이 아니다. 기존 attempt 파일을 삭제하거나 deadline을 갱신해 재시도하지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' B024_ROOT="$RUN_ROOT" "$PYTHON" -m pytest "$RUN_ROOT/code/test_reference.py" -q
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/REF" 900 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/REF" REF
# 기존 조건 복원과 새 cache 검토 후, 종료와 자원 회복을 확인한다.
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/PROBE" 600 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/PROBE" PROBE
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/S" 2400 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/S" S
"$PYTHON" "$RUN_ROOT/code/runtime_launch.py" "$RUN_ROOT/stages/D" 600 "$PYTHON" "$RUN_ROOT/code/run_phase.py" "$RUN_ROOT/stages/D" D
```

단계는 병렬 실행하지 않는다. 이전 worker 성공·종료와 자원 회복이 다음 단계의 전제다.72GiB 시작조건/24GiB headroom/swap0와 타 서비스 보호를 유지한다. S의 실제40step/80forward와 finite final latent를 확인한 뒤 D가 그 저장물을 decode한다. D 실패에 따른 sampler 재실행은 없다.

첫 실제 두 CFG forward에서 새 reference/CLIP 객체가 검증된 cache에서 전달됐는지 확인한다. 이 hook은 추가 forward나 attention map 저장을 하지 않는다. replace=True와 공식 replacement 위치 계약을 유지하며 adapter/ALG/manualRoPE는 OFF다.

## 검토의 한계

기술 실행과 원본 장면·동작·실제 개체 품질은 별도다. 배경과 padding, VAE와 CLIP를 함께 바꿨으므로 개별 원인의 효과로 분해하지 않는다. 같은 개체 source이므로 source-copy와 실제 reference 교체를 구별할 수 없다. 실제 연속 관찰이 없으면 temporal=UNVERIFIED다.

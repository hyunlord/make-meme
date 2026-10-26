# B-033 재현

기존 B-031 vehicle R1의 source/conditions/final latent와 B-032 target support가 필요하다. 원천 미디어·cache·latent·개인 절대경로는 공개 저장소에 포함하지 않는다. 새 실행 승인 없이 반복 sampler를 실행하지 않는다.

1. 기존 고정 SCAIL Python에서 `prepare.py B033_ROOT B031_R1_WORKER`를 CPU로 한 번 실행한다. 준비된 입력 폴더는 source/source-mask/target-mask이고 source는 17장896×512다.
2. `test_contract.py`의 네 소형 CPU 계약 확인과 immutable parent receipt 확인을 수행한다. `EXECUTION_FREEZE.json`은 실제 실행 파일·입력·upstream 해시다.
3. 코드/설정/입력 고정 후 VAE → S → D를 fresh guarded worker로 순차 실행한다. 각 이전 서비스가 종료되고 자원이 회복돼야 한다.

```sh
$PINNED_PYTHON $B033_ROOT/code/runtime_launch.py $B033_ROOT/stages/VAE 600 $PINNED_PYTHON $B033_ROOT/code/run_phase.py $B033_ROOT/stages/VAE VAE
$PINNED_PYTHON $B033_ROOT/code/runtime_launch.py $B033_ROOT/stages/S 2400 $PINNED_PYTHON $B033_ROOT/code/run_phase.py $B033_ROOT/stages/S S
$PINNED_PYTHON $B033_ROOT/code/runtime_launch.py $B033_ROOT/stages/D 600 $PINNED_PYTHON $B033_ROOT/code/run_phase.py $B033_ROOT/stages/D D
```

이 명령은 같은 run의 재시도를 허용하지 않는다. attempt 파일은 exclusive 생성이다. 공개 스크립트의 날짜 deadline은 이번 승인 실행 전용이며 이를 자동 연장하지 않는다. source encode1/decode1, final-only decode1, sampler1(40step80forward), step decode1이 최대다. 마지막 latent는 decode 이전 lossless CPU 저장물로 보존한다.

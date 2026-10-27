# CONTINUATION_02 재현 경계

```sh
# 이미 수행한 Mac CPU 검사: 설치/모델 import 없음
python3 -m unittest discover -s continuation02/code -p 'test_*.py'
# 실제 Spark stage가 준비된 후 필요한 동일 entrypoint 검사(이번에는 NOT_RUN)
"$B007E_PYTHON" "$CONT02_ROOT/code/worker.py" "$CONT02_ROOT/stages/STEP_S" --preflight-only
```

`bootstrap(root)`가 실제 worker와 preflight 양쪽의 첫 실행 경로다. 현재 root의 stage/config/freeze를 읽고 HF_HUB_OFFLINE·TRANSFORMERS_OFFLINE·절대 B007E_LOADER_REPORT를 명시 대입한다. reports/loader.json이 없어야 하며, 고유 임시 파일의 쓰기·fsync·삭제만 확인한다. 실제 loader 보고서는 만들지 않는다. 잘못된 stage·경로·충돌·쓰기 불가·frozen 파일 불일치는 모델 import 전에 실패한다.

기존 staged_loader의 유일한 직접 필수 환경 조회는 B007E_LOADER_REPORT다. 선택 loader의 계산·dtype·RoPE·checkpoint 읽기는 바꾸지 않았고, 새 bootstrap이 그보다 먼저 실행된다. 기존 CONT01 guard/supervisor는 byte-identical 복사다.

실제 Spark 연결 2회가 timeout이어서 원격 stage layout·code/config freeze·동일 Python preflight·현재 duplicate/live safety 확인을 수행하지 못했다. 따라서 이번 산출물에 없는 runtime 경로나 해시를 실제 준비됐다고 간주하지 않는다. 기존 CONT01 코드는 수정하지 않았으며 누락 실패는 보존된다.

연결이 복구되면 새 승인/현재 예산 상태를 먼저 확인하고 원격 preflight와 fresh safety를 검증해야 한다. 모델 로딩 전에 env 계약을 검사해야 하며, 이번 로컬 CPU 결과만으로 GPU 실행을 시작하지 않는다. BASE/CONTROL 재실행은 금지된 상태 그대로다.

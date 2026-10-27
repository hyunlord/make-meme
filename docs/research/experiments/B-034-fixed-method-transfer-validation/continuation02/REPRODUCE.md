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

## RESUME_01 실제 Spark CPU 검증 (과거 SSH 차단 기록 보존)

연결 복구 후 별도 CONTINUATION_02/RESUME_01 stage를 `code/prepare_resume.py`로 만들었다. 기존 guard와 bootstrap/worker는 변경하지 않았다. stage deadline만 새 승인 시각으로 설정했으며 부모 artifact와 B033 수식 파일은 그대로 해시 고정했다. 실제 동일 Python의 STEP_S/STEP_D preflight 4회 및 CPU24개 PASS는 RESUME_CPU_REPORT.json에 기록했다.

하지만 보호 queue 접속 실패와 기존 허용 서비스 신원 부재로 live guard가 OBSERVATION_FAILED를 반환했다. supervisor와 GPU worker는 시작하지 않았다. 준비된 stage와 CPU PASS를 실행 승인으로 해석하지 않는다. 서비스 복구/운영 계약 확인은 별도 판단이며, 현재 allowlist를 조용히 바꾸거나 보호 검사를 건너뛰지 않는다.

재개 실행 시간의 활성 계약은 새 config의 `deadline_epoch`와 `configs/execution.json`의 `deadline`(13:18:47Z)이다. 부모 config에서 물려온 과거 설명용 시각이 있더라도 이전 실행의 metadata이며 이번 deadline을 연장하거나 대체하지 않는다. 전체 hard deadline은13:33:47Z로 별도 기록한다.

# 재현과 실행 계보

`prepare_resume.py`는 기존 CONTINUATION_01 입력을 읽기 전용으로 연결하고 새 EXPECTED_ABSENT_01 root에만 config·정책·freeze를 쓴다. 인자는 기존 연구 root, 새 코드 directory, 이미 확인한 서비스 배포 root이다. 실제 경로는 비공개 설정에 있다.

```sh
"$EXISTING_PYTHON" prepare_resume.py "$EXPERIMENT_ROOT" "$CODE_ROOT" "$KNOWN_SERVICE_ROOT"
"$EXISTING_PYTHON" worker.py "$STEP_S_ROOT" --preflight-only
"$EXISTING_PYTHON" worker.py "$STEP_D_ROOT" --preflight-only
"$EXISTING_PYTHON" supervisor.py "$STEP_S_ROOT"
```

위 supervisor 호출은 이미1회 실행되어 첫 live 표본 UNKNOWN_GPU_PID로 반환2였다. 같은 root를 다시 실행하는 지시가 아니다. STEP_D는 호출하지 않았다.

preflight/실제 worker와 supervisor는 같은 stage별 service-policy.json을 읽는다. bootstrap의 offline 환경·절대 loader-report 경로 검사는 유지한다. 알려진 서비스 프로세스/자식/cwd·listener·실제 ECONNREFUSED만 새 정책에서 제한적으로 허용하며, 외부 GPU·메모리·swap·관측 실패는 차단한다. 과거 allowed snapshot 파일은 보존하고 새 정책에서 그것을 현재 허용 PID로 재등록하지 않는다.

연구용 공유 비차단 lock과 기존 orphan worker argv 검사, 기존 자체 worker 생애주기 검사를 유지한다. 이번에는 model worker가 생성되지 않아 lock은 supervisor 종료로 해제됐고 해당unit은 inactive/not-found였다. 외부 GPU 작업은 그대로 두었다.

사전 고정 SHA와 입력 hash는 CODE_FREEZE.json, 실제 시작 거절은 MEASUREMENTS.json과 비공개 원시 receipt에 있다. 타입/lint 도구는 설치되지 않아 NOT_RUN이며, syntax와 focused CPU 계약 결과를 전체 타입-clean으로 주장하지 않는다.

# B-007D 재현 경계와 명령

이 문서는 기존 실행의 재현 방법을 설명하며 추가 실제 load를 승인하지 않는다. 원래 상한은 metadata 1회와 조건부 변환 1회다. 이미 사용한 ledger를 삭제하거나 새 폴더로 횟수를 초기화하지 않는다. 원래 supervisor deadline은 **2026-10-22 14:34 UTC**이며 만료 후 그대로 실행하면 중단되어야 한다. 이후 재현은 새로 승인된 예산·deadline·PLAN에서 수행한다.

## 필요한 고정 입력

- 원본 SAT SHA256: `d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f`.
- SCAIL 공식 converter source SHA256: `0519f688643b0a2c3f13660f196e34280704ddb3e2575aa226e2d2f8f2b4397f`.
- 실행 사전 고정 commit: `5e134fa`. 후속 수정이 있다면 실제 최종 RESULTS의 실행 hash와 함께 대조한다.
- B-007B mapping/writer와 B-007C graph 분석 코드, 정확한 ambient contract, 실제 OS probe receipt, shared ledger.
- 기존 검증 환경의 Torch/NumPy 및 동일한 Docker image digest·mount 구성. 일반 host Python 실행은 격리 재현이 아니다.

`${RUN_ROOT}`는 비공개 실행 디렉터리의 절대 경로로 매핑한다. 해당 디렉터리의 runtime 구성과 OS proof를 먼저 검증한다. public 저장소에는 개인 경로·원본·weights가 없다.

## 원래 실행 entry

다음은 실제 supervisor 형태의 명령이며 자동으로 두 단계를 연속 실행하는 스크립트가 아니다. metadata 결과와 자원 검토가 통과한 경우에만 두 번째 명령이 허용됐다.

```sh
python3 "${RUN_ROOT}/code/sandbox_launch.py" "${RUN_ROOT}" metadata
```

```sh
python3 "${RUN_ROOT}/code/sandbox_launch.py" "${RUN_ROOT}" conversion
```

supervisor는 systemd user unit에서 해당 실험의 container만 추적·정리한다. Docker entry는 runc, network=none, read-only root, 비root UID, cap-drop=ALL, no-new-privileges와 제한 bind를 사용한다. stage cap은 metadata 8GiB, conversion 32GiB다. host의 convert_stage.py 직접 호출로 probe나 lifecycle guard를 생략하지 않는다.

## 완료 증거

metadata-pass receipt의 source contract와 mapping을 확인한다. 변환이 끝나면 output parser·source/output per-tensor hash·원본 불변·최종 발행 receipt를 확인한다. 두 번째 load의 같은 mmap state로 검증하며 B-007B 독립 verifier CLI를 추가 호출하지 않는다. 그것은 source를 두 번 더 로드한다.

부분 파일이나 `unverified` 파일은 최종 모델이 아니다. load attempt·실패·guard 종료도 보존한다. metadata와 변환 성공이 확인돼도 모델 적재·영상 생성 명령은 이 재현 범위에 없다.

## 이번 실행의 완료 판정

metadata 및 변환 두 번의 실제 load를 모두 사용했고 최종 변환은 PASS다. 최종 파일 SHA256은 `8b844f026510f0b94d3209d66444b403a089ec179dc149d85513c13b2fa37118`, 크기는 65,582,313,560 bytes다. 1,307개 tensor 전체의 값 hash를 원본 mapped view 및 출력과 대조했다. 새 실행을 위해 ledger를 초기화하지 않는다. 기존 결과의 파일·receipt 검토와 새로운 역직렬화 실행을 구분한다. 전체 model forward와 영상 생성은 이번에 실행하지 않았다.

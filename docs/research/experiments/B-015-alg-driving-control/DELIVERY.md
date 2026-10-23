# B-015 전달 및 무결성

결과 snapshot commit: `7fd5d7a570e9714701ba960715a6ad6216f24a0d` (원격 일치 확인). 이번 전달 문서는 압축 후 검증 기록이며 ZIP 내부 snapshot을 소급 변경하지 않는다.

- 비공개 파일명: `make-meme-B-015-20261024-final.zip`.
- 실행 호스트 Spark의 `/tmp/`에 생성한 뒤 사용자 Mac의 `/tmp/`로 실제 전송했다. 두 위치는 서로 다른 호스트다.
- 크기: **199,344,328 bytes** (약190.11MiB).
- SHA256: `83b549bbed45f93156245bb7d1377df2ab377aa15d4e37916f7843b08b0c314b`.
- 두 호스트 CRC·471 payload SHA·전체 ZIP 바이트 동일성 PASS. 총472개 고유 member(471 payload+MANIFEST).
- Mac 실제 추출 후471개 payload 해시를 다시 대조했다. 4개 생성군 각17PNG, source17장, 새 raw·최종 latent·필터·parent 캐시·viewer 의존 경로를 확인했다.
- 뷰어 상대 위치: `private/reports/output-review/review.html`. 새 MP4와6열 native24fps 비교 및 전체17장·사전 사건 시트를 포함한다.

실제 신규 raw·MP4·final latent·filtered tensor/sidecar·STILL parent cache·실제 입력·실행/실패/타입한계 기록·재현 코드·수학·기존 세 결과의 MP4/전체PNG를 보존한다. 기존 세 raw 대형 tensor는 로컬 원본 경로/해시/크기/사유를 비공개 STAGING_MANIFEST에 남기고 제외했으며, 결과 프레임을 선별하지 않았다. pycache·부모 symlink 등 제외 항목도 manifest에 기록했다. 대형 weights·전체 환경·비밀키·토큰은 포함하지 않았다. 검토 ZIP은 GitHub에 올리지 않았다.

포장 검증과 별개로 시간 품질은 UNVERIFIED다. 실험 자체는 PROBE/S/D각1,40step88forward·17f24fps이며 자체 watchdog/pipeline은 최종 확인에서 inactive/MainPID0였다. 추가 sampler·학습·후속 가설 실행은 없다.

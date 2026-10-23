# B-008 검토 자료 전달 확인

상태: **양 호스트 CRC / 255개 payload 해시 / ZIP 바이트 동일성 PASS**.

- 비공개 ZIP: `make-meme-B-008-lab-rgb-baseline-20261023.zip`
- 실제 실행 호스트 Spark의 임시 디렉터리에서 작성 후 사용자 Mac의 임시 디렉터리로 전송했다. 호스트별 실제 경로는 비공개 receipt와 최종 응답에서 구분한다.
- 크기:133,652,595bytes (127.46MiB).
- SHA256:`53c3160a391dcfa7cdf9dfb3c4d722c55bffb99374c53ac78022a32f8c464c9d`.
- 양쪽에서 ZIP 재열기·CRC와 MANIFEST.json의255개 파일 bytes/SHA를 검증했다. manifest 포함256entries.
- ZIP 안의 공개 결과/코드 snapshot:`01fd87ca254ab0fb151789c6ed3b7c3a89937ccc`. 이 전달 확인 문서는 패키징 후 작성한 별도 기록으로, ZIP에 들어 있다고 주장하지 않는다.

실제 raw output,17PNG,final latent·sidecar,조건/입력 계보,원본/처리본/참조/출력 비교,전체17장시트,24fps비교MP4,프레임 이동/1회 재생 페이지,재현코드,실패·실측 기록을 포함한다. 큰 모델 가중치·중복198MB 전처리 tensor·불완전 전송본은 제외했으며 제외 이유와 원본 위치/해시는 private manifest/receipt에 남겼다. 이 ZIP과 개인 미디어는 GitHub에 올리지 않았다.

브라우저 제어 검증 PASS와 temporal UNVERIFIED를 구분한다. 주 에이전트가 로컬 ZIP 전체를 다시 읽어255개 해시를 독립 검증했다. 자체 worker/unit은 모두종료/PID0이고 브라우저·HTTP서버·전송 프로세스를 남기지 않았다. 기존 ComfyUI 서비스만 유지했다. 새 학습/추가생성은 실행하지 않는다.

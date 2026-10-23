# B-012 비공개 전달 검증

Spark에서 `make-meme-B-012-20261023-1436.zip`을 실제 생성한 뒤 기존 SSH 연결로 Mac에 전송했다. 양쪽 호스트의 `/tmp`에 각각 존재하며 개인 절대 경로는 공개하지 않는다. ZIP은 공개 저장소에 올리지 않았다.

- 크기: 257112039 bytes (245.201MiB), 300MiB 이하.
- SHA256: `215cbce3e87aa4111ce2673ea5d23d42edaece8b7b1c6bcb4173169e799d3a02`.
- payload525개. 양 호스트 CRC 및 모든 payload의 길이·SHA256 검증 PASS, ZIP byte 동일.
- 두 raw·MP4·final latent·조건·noise, 실제 source/17장 입력·mask, 전체17장 비교와 native24fps4열 영상·검토 페이지, 평가/불확실성, 실제8단계 로그·메모리 trace, 코드·설정·한국어 해설 포함.
- 중복 `preprocessed_inputs.pt` 두 파일만 실제 Spark 원본 경로/파일hash로 연결해 제외했다. 원본 입력과 전처리 코드, 실제 조건·raw출력·final latent는 포함했다. 모델 weights/환경/optimizer는 제외했다.
- 첫 패키징은 stage 코드의 fixture 테스트 파일이 실제 출력 선택 범위에 들어 있어 쓰기 전에 거부됐다. 규칙을 유지하고 실제 각 stage reports만 명시해 다시 패키징했다. 이는 생성 시도나 GPU 실패가 아니다. 해당 기록도 포함했다.

ZIP의 공개 문서 snapshot은 결과 commit `cce466d19afde6d19e79a2d748eb541a768bf79e`다. 이 전달 receipt는 ZIP 생성 후 별도 기록이므로 ZIP 안에 자기 SHA나 이 receipt를 소급 삽입하지 않는다. 자체 GPU unit은 inactive/MainPID0이며 추가 생성/학습은 없다.

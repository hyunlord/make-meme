# B-011 비공개 전달 검증

실험 결과·실측·한국어 해설 snapshot은 `d9b3753576376764829bda406e9ccf01f0cdb68c`다. 해당 commit을 연구 브랜치에 push하고 원격 SHA 일치를 확인한 뒤 Spark에서 비공개 ZIP을 만들었다. 이 문서는 압축 후의 전달 영수증이므로 ZIP 안에 자기 자신을 포함시키기 위한 재포장은 하지 않는다.

- 파일명: `make-meme-B-011-exploratory-self-reenactment-20261023.zip`
- 크기: **141,729,164 bytes** (약135.16MiB)
- SHA256: `95da41abe97f069d345c914b317325014d8cdbfce514cda7db96b3fac60e97b0`
- payload290개 + MANIFEST1개. Spark와 Mac에서 CRC·전체 payload 크기/SHA256검증 PASS.
- Spark에서 실제 생성한 ZIP을 Mac으로 전송했고 두 실물의 ZIP SHA256 일치를 확인했다. 실제 절대 경로는 비공개 최종 전달문에만 기재한다.

포함: 실제 raw·17f24fps MP4·final latent와 규약·initial noise·새 조건 cache, source/STATIC COPY/생성/B-009맥락 비교, 전체17프레임·고정 관측 패널·불확실한 좌표·코드·config·실측·실패/보존 장부·독립 검토. 모델 가중치·환경·upstream 전체·비밀정보는 제외했다. 중복 전처리 대형 tensor 제외 범위는 manifest에 기록한다. 개인 미디어·좌표·cache·latent 및 ZIP은 GitHub에 올리지 않았다.

ZIP을 풀고 `private/reports/output-review/review.html`을 열면 비교 MP4 한 번 재생과17프레임 PNG 탐색이 가능하다. UI 동작 검사와 실제 연속 재생 품질 검수는 별개이며 temporal은 UNVERIFIED다. 공개 문서 snapshot은 `public/experiment/docs/research/`에 있다.

최종 확인에서 B-011 자체 systemd unit·GPU 프로세스는 남지 않았고 기존 ComfyUI 서비스는 유지됐다. P/PROBE/S/D 각각1회·sampler1회·재시도0회를 끝으로 종료한다. B-010 사용0과 이전 결과는 보존한다. 압축 snapshot의 RUNNING 마지막 항목은 포장 당시 진행 상태이며, 현재 완료 상태는 이 영수증과 최신 RUNNING을 따른다.

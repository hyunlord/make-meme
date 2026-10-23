# B-014 입력 계보 — 읽기 전용 확인

Spark의 실제 부모 파일을 확인했다. 부모 캐시·metadata·noise 파일은 기존 receipt와 일치하고, safetensors의 16개 leaf 데이터 바이트를 표준 라이브러리로 직접 해시하여 metadata와 모두 대조했다. 모델 적재, GPU 사용, P 재인코딩, 입력 수정은 하지 않았다. 세부 해시는 [INPUT_LINEAGE.json](INPUT_LINEAGE.json)에 있다.

| 항목 | 확인 |
|---|---|
| B-013 LAB_MOV 조건 캐시 | `b7e5c62d8cb3a67e3cca0e104a536cf54c86937fa136f8554dbe55062ba9bf5d` |
| 조건 metadata | `7dbcddd695c7148f59a5790ae74c0569e0517d491cc1c26550c828ca995d68aa` |
| initial noise 파일 | `456ea2333ea5633c98e842d6ff2cca8e440def39fc1abd750882fc75ab2b78fc` |
| noise tensor 값 | `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950` |
| 참조 latent | FP32 `[16,1,112,64]`; positive/negative leaf의 원본 값 동일 |
| 입력 파일 | 부모 두 case의 76개 파일 모두 기존 receipt와 일치; driving RGB/mask PNG·MP4 72개는 B-012 실물과도 일치 |
| 원본 시점 | B-012 고정 선택 original `[7,24)`, local `[0,17)`; 17프레임·24fps·512×896 |
| prompt/config | 캐시 metadata config와 LAB_MOV config JSON이 동일; prompt UTF-8 SHA `51e64354e9d456ab3d12c0eaee3df6d70e8ffe5ca61d53f4880b58cf6ef8f8e2` |
| 대조군 준비 | B-013 LAB_MOV/LAB_STILL 각각 raw tensor·MP4·17 PNG 존재 및 SHA 기록 |
| 가중치 | 8개 파일의 새 size/mtime가 부모 기록과 일치. SHA는 이전 검증값이며 이번 전체 재해시는 아님 |

실제 Lab RGB와 B-009 RED/WHITE reference mask를 그대로 재사용한다. 사진·원본 driving 외 A 생성물, IG, 고양이 자산은 추가하지 않는다. 경계·발·얇은 부위의 기존 mask **PARTIAL**은 유지한다. source crop·색상·좌표 및 사진 내용은 수정하지 않았다. 원본 전체 영상의 SHA는 B-012 기록을 인용하며, 이번에는 선택된 PNG·MP4 실물을 다시 검증했다.

이 확인은 부모 입력의 재사용 준비 상태다. 새 B-014 symlink/filtered sidecar 및 실제 sampler 검사와 별개이며 ALG 결과는 이 작성 시점 **NOT_RUN**이다. 기존 대조군의 전신 전이 FAIL, 개체 UNCERTAIN, 시간 품질 UNVERIFIED를 수용으로 바꾸지 않는다. 새 결과가 생기기 전에 비교 영상을 만들지 않았다.

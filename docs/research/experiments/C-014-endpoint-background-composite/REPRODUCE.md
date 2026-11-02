# C-014 재현 계보

연구 branch docs/c-research-20261028. 사전 계획97a5d4f, 실제 합성/평가기 코드be64d7d,뷰어12f15d8. COMPOSITE_CONFIG.execution의 full SHA와 원본 정책 hash 참조. PREDECLARED_CONFIG는 동봉 JSON byte 그대로다. PATHS의 I50/S는 C-013 frozen JSON, A는 부모 pixel-index 공식 x=104+208t/32,y=120−48sin²(pi t/32),양끝offset0이다.

실제 runtime 절대경로는 Spark의 private-inputs manifest와 기존 stage-settings에만 둔다. 입력: C-012 원 start/end anchors, C-013 I50/S PNG33장 및 MP4, C-012 ON2048_S2_A PNG33장 및 MP4. C-013 ORIGINAL_MEDIA_SHA256와 C-012 TASK_MANIFEST 기대hash를 실제 파일과 대조했다. 공개 INPUTS_AND_PLATE는 역할/hash만 남긴다. 인수 당시 Spark 부모 manifest 파일이 루트에 없어 기존 Git 문서 사본을 현재 private root로 옮겨 대조했으며 부모는 수정하지 않았다.

기존 연구 Python과 NumPy/Pillow/OpenCV, /usr/bin의 기존 ffmpeg/ffprobe 사용. 설치0. 기존 C-012 make_stage.build로 cpu만 만들고 C-001 run_guarded로 실행했다. guard_code는 C-013 resume1 사본 그대로다. 현재 stage/승인/deadline 및 thread environment만 바인딩했다. 구 guard 전체swap 차단으로 되돌리지 않았고 새로운 예외도 없다. CUDA_VISIBLE_DEVICES 빈 값; torch import 없음. 기존 adapter의 checkpoint 필드는 경로 존재만 확인하는 원래 계약이며 VAE를 적재하지 않는다.

1. `RESEARCH_PYTHON code/run_composite.py PRIVATE_MANIFEST ROOT --cpu-only`: fixtures → plate/source_map/U0/UT freeze →99PNG/alpha float64→3POSTMP4→입력hash 재검증.
2. 별도 guarded CPU `code/evaluate.py PRIVATE_MANIFEST ROOT C012_ROOT C013_ROOT --cpu-only`: full-frame Reader 재사용, zone 및 위치, METRICS. 평가기만 부모 background를 읽으며 합성에 역전달하지 않는다. plate-vs-oracle audit은 NOT_RUN.
3. 별도 guarded CPU `code/build_review.py PRIVATE_MANIFEST ROOT REVIEW_ROOT --cpu-only`: 기존RAW와POST copy/hash,overlay/crop/sheets/index. 세 stage 정상 종료와 freeze를 확인했다. 각 stage의 상태/메모리/시작 관측은 GUARD_RUNS에 있다.

compose의 freeze는 당시 디렉터리 내 미사용 WIP build_review.py도 포함했다. compose 완료 후 수치표시를 추가한 최종 builder를 전달했으므로 이 미사용 파일 하나의 현재 hash는 최초 freeze와 다르다. 과거 freeze를 덮어쓰지 않았고 차이를 GUARD_RUNS에 보존했다. 실제 compose 코드/사용입력은 불변이며 evaluator/review stage freeze는 최종 파일과 모두 일치한다.

자료 출력은 overwrite를 거부한다. 완료99PNG를 더 좋은 품질을 위해 재계산하지 않는다. alpha NPY는 Spark 비공개 보존,공식/좌표/hash로 재생성 가능. alpha PNG/overlay는 표시 전용이고 합성에 재사용하지 않았다. fixture/exact는 품질 지표가 아니며 위치와 clipping/seam을 분리한다. SOURCE_MAP 값0 unknown/1anchor0/2anchor32.

전체33축소 RAW/POST 시트 및9시점 동일배율crop을 같은 Codex 세션에서 관측했다. temporal=UNVERIFIED. 브라우저 QA는 BROWSER_QA,패키지 CRC/실제추출/payload/호스트동일성은 DELIVERY 참조. PNG만 exact 기준이며 MP4는 손실 미리보기다. 공개Git에 미디어/weights/latent/private로그를 올리지 않는다.

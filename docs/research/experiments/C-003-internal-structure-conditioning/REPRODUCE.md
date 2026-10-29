# 재현과 보존

이 문서는 추가 실행 권한이 아니다. 최초 C-003 안전 중단 기록은 보존했으며 별도 [amendment](../../work_orders/C003_START_POLICY_AMENDMENT_AND_RESUME_KO.md)가 기존 미사용 범위만 재개했다. 품질재시도·자동예약·추가 사례는 없다.

1. C001 INPUTS/ANCHORS와 C002 CONDITIONS의 dog source33·selected SAM33·실제 layout33 및 앵커를 같은 무손실파일로 확인한다. 참조·caption·negative·frameindex·crop을 바꾸지 않는다. 공식 scribble weight는 ANNOTATOR.md의 immutable revision/hash가 일치하는 기존 파일을 재사용한다.
2. 기존 research Python과 run_guarded.py를 그대로 쓰고 guard_code만 C003/code/guard의 사전동결 버전으로 연결한다. C001의 과거 guard 파일은 수정하지 않는다. memory.py의 두 줄 제거 이외 세 guard 모듈은 byte-identical이다. fresh boot/deadline/stage와 절대경로/freeze를 만들며 actual memory.__file__/SHA와 safety/supervisor의 동일 MemoryBudget 객체를 확인한다. 실행경로 매핑과 원본 freeze는 private에 보존한다.
3. `test_start_amendment.py ABS_PRIVATE_OLD_START_SAMPLES`는 synthetic 중요한차단과 실제6표본의 새정책 replay를 구분한다. old START_SWAPOUT_OBSERVED는 그대로다. 실제 CPU systemd 경로가 완료된 뒤 matching heavy가 허용된다. 처음 import 오류를 막는 script 절대디렉터리 bootstrap을 유지한다. 추출 CPU receipt는 model_imported=false/cuda_initialized=false다.
4. `scribble_extract.py ABS_CONFIG [--cpu-only]`의 config: source_dir,weights,output,device. Full-frameRGB/255 FP32,strict weights_only,evaluate/inference로33장을 한 번 처리한다. 종료/자원회수 후 rawcache를 사용한다. 같은 source 재추출은 하지 않는다.
5. `prepare_internal.py ABS_CONFIG`의 config: source,masks,layouts,scribble,output. Hash/완료receipt를 대조하고 I/256bbox왕복/DYNAMIC/HOLD를 만든다. 실제 J와 K를 보고 polarity·좌표·배경제거·선유효성을 확인했다. 결과를 보고 threshold/margin/강도를 바꾸지 않는다. 모든actualK/hash는 CONDITIONS에 있다.
6. 부모 video config를 유지하고 condition_mode/internal_dir/interior_dir/output만 추가·변경한다. layout_dir은 C002의 원래 directory다. `video_generate.py ABS_CONFIG --cpu-only`로 실제X33/G33/anchors와compressmask를 검사한다. 실제 CPU경로 COMPLETE 뒤 DYNAMIC→HOLD 각 한 번, 이전 셀 정상종료/회수 뒤 다음셀로 간다. 첫model_fn noise/context/mask64를 원래hook으로 기록한다. 추가forward없음이다.
7. 50번째schedulerlatent를atomic/readback저장한 뒤 decode/raw/PNG33/MP4를 보존한다. Decode실패는 sampler재실행 사유가 아니다. Sourceoverlay/MP4를 모델입력으로 쓰지 않고 양끝출력을 덮어쓰지 않는다.
8. `build_review.py ABS_C001_PRIVATE ABS_C002_PRIVATE ABS_C003_PRIVATE ABS_NEW_DIR`로 실제6패널과 조건/J/I를 비교한다. 고정crop/동일index,33장/16fps,고정9장과29–32를 접근한다. 원생성MP4는원바이트, JPEG/sheet/나란한comparison/conditionpreview는 명시적파생본이다. 이전blockedviewer는 --blocked 경로로 보존됐다.

공개에는 source코드/비민감해시·요약만 있다. Full은 새raw/latent/무손실프레임/구조선·조건/guard근거를 별도로 보존하고 C001/C002full/weights를 중복 포장하지 않는다. 원본 dataset/license 조건은 C001에 따라 private검토만 사용한다. Compact의 CRC/추출/size/hash 및Spark/Mac원바이트일치는 DELIVERY에 있으며 자체해시순환을 피하려 delivery/publicationreceipt는archive외부에 둔다.

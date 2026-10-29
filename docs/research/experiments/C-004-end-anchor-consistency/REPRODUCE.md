# 재현 경로와 보존

추가 실행 권한이 아니다. C004는 native1call/1candidate와 적합한 앵커에 대한 영상1회로 종료한다.

1. C001 private native-call-records에서 실제 target crop와 raw start를 확인한다. source local32 무손실832×480, reference crop, start-original 순서로 native tool의 실제 referenced_image_paths3개에 전달한다. oldend는 입력하지 않는다. 정확한 prompt/입력hash는 IMAGEGEN_REQUEST.json, 실제원출력/정규화는 ANCHOR.json에 있다. 원출력은 보존하고 C001 aspect-fit LANCZOS/blackcanvas만 적용한다.
2. C002 원래 case_nonrigid-layout_mov config를 복사해 end_anchor/output만 새 절대경로로 바꾼다. 모델설정 기본값을 확장한 effective config에서도 이 두 값 이외 변경이 없다. C002 code/video_generate.py와 C001 run_guarded.py를 수정하지 않는다. C003 정상완료 current code/guard를 직접 연결한다. 실제 memory.__file__/SHA와 safety/supervisor의 같은 MemoryBudget identity를 확인한다.
3. 기존 stage 구조의 configs/reports/code를 만들고 worker.py는 원래 run_guarded.py의 byte-exact복사다. deadline/boot/stage/unit을 이번 실행에 바인딩하며 policy·외부allowlist·임계값을 바꾸지 않는다. config/입력/실행코드/guard를freeze하고 CPU와heavy는 같은 route를 사용한다. 처음 reports/worker 누락과 자체실패unit 이름충돌은 premodel기계적오류로 기록하고 이전 rawreceipt를 별도 보존했다. 고유 CPU unit명으로 정상확인했으며 다른 서비스 상태를 조작하지 않았다.
4. 기존 Python에서 `run_guarded.py ABS_CPU_STAGE`를 실행한다. 실제 condition RGB hash0..31 동일/32 변경, G33과 압축9 mask 동일을 C002와 비교한다. COMPLETE CPU receipt가 같은 route임을 기존 adapter가 검사한 뒤 `run_guarded.py ABS_HEAVY_STAGE`를 한 번 실행한다.
5. 기존 first-model_fn hook의 noise/context/mask64/scale를 읽는다. 추가 forward와 RNG 변경은 없다. final latent 원자 저장/readback 후 decode/raw/PNG33/MP4를 보존하며 출력 끝을 앵커로 덮지 않는다. source_fps=null, preview16fps, timebase_assumed=true이며 파일2.0625초와 끝 표본 간격2초를 구분한다.
6. C004 build_review.py에 기존 C001/C002 private와 새 C004 private 및 새 출력 directory를 전달한다. 원생성 MP4는 바이트 복사, 나란한 MP4·조건 미리보기·JPEG 시트는 파생물이다. 같은 인덱스 전체33장/고정9장/29–32/고정 머리·다리 확대로 검토한다. ZIP의 manifest·CRC·실제 추출·Spark/Mac 동일성을 검사한다.

원본/생성 미디어와 개인 경로/weights/latent는 공개하지 않는다. 기존 공개 데이터의 재배포 조건은 C001 기록대로 private 검토 범위로 제한한다. Full은 새 앵커/raw/latent/PNG/실제 조건/원본 실행 근거만 별도 보존하며 이전 full과 가중치를 중복 포장하지 않는다.

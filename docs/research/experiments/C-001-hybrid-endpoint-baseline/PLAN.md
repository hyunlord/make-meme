# C001 — 양끝 앵커 영상 기준선

시작2026-10-28T11:13:32Z, heavy cutoff14:53:32Z, 전체종료15:13:32Z. 기준연구commit4610bfbe77f6991b144281838be02b74c03559c3에서 독립 C branch/worktree를 만들었다. 의뢰서 전체를 따른다.

질문: native 앵커가 각 시점 source 상태와 target 외형을 함께 만족하는가, 시간조건으로 넣은 양끝 사이에서 VACE가 어떤 동작/개체/배경 실패를 보이는가? 분석 성공과 편집 품질은 분리한다.

예산: 후보≤6, 최종2. native imagegen 기본4+수정2(사례별수정≤1), 영상기본2+기계복구1/전체sampler≤3/각≤50step, seed20261028. 새학습/업스케일/보간/후합성/추가backend0. 신규weights≤40GiB, 공개media≤2GiB. 가능한 기존자료/모델만사용한다.

입력후보는DAVIS car-roundabout30..62/source→car-shadow0/reference 및 dog0..32/source→dog-gooses85/reference다. 원본33개서로다른프레임과target가시성을확인하고INPUTS.json으로생성전에고정한다. source_fps=null, timebase_assumed=true, preview16fps; 지속33/16초와표본간격32/16초구분. 공통aspectfit832×480변환을RGB/GT좌표에적용한다.

평가사전축: 차량의은색높은차체/루프레일/창비율, 강아지의검은털/흰주둥이·가슴/사족체형. 차량은주행방향·회전순서,개는접근·발디딤과고개상태. 보호영역은각각건물/난간과울타리/관목·잔디다. 앵커각시점상태,쌍일관성,실제출력endpoint충실도,중간외형,동작,장면,시간을각각판정한다. temporal은실제연속지각검수없으면UNVERIFIED.

SAM3.1 기존가중치/환경을확인하고source33장·네앵커만분석한다. 접근/환경차단시GT/MANUAL로명시하고영상은진행한다. SAM/원본중간RGB는생성입력에사용하지않는다. VACE모델은기존1.3B고정,checkpoint/runtime계보와공식firstlastframe helper를BACKEND_CONTRACT에고정한뒤실행한다. 두anchor만src_ref_images에넣는것은허용하지않는다.

절대python/script/config/input/output경로와존재cwd를공통검사하고실제호출경로에서CPU진입/종료를먼저검증한다. 경로/import/shape오류는예산안에서고치고이어간다. 최신메모리정책72/24GiB,worker swap0,전역S0/증가64MiB/10초swapout64MiB/PSIfull10%및관측/외부GPU·서비스보호를재사용한다. 외부작업종료/가드완화없음. 위험은종료하고품질실패는재생성하지않는다.

실행전입력·코드·조건commit,실행후실제영상·한계·비용·한국어수학코드해설·검토viewer·compactZIP을남긴다. 공개Git에개인경로/PID/weights/조건tensor/이미지실물은올리지않는다. Spark/Mac /tmp CRC·추출·payloadhash·전송검증과remoteSHA확인으로종료한다.


검토완료: 차량 마지막에도주대상가시적이며우측빨간전경차는보호객체. 개33프레임에서코를낮추고접근하며끝에서도전신가시적,부분motionblur유지. 네sequence선정확정. 영상설정은이미검증된DiffSynth Wan FlowMatch Euler50/sigma_shift5/CFG5/BF16/SDPA/seed20261028,공식helperexpand_num31→33frame,src_ref=None. 공식UniPC와다름을명시하고체크포인트revision574e6a744642ce3bee319afc31496b88bde8aac4·DiffSynth계보f39d731a3e318d25b725eb3389cfddb184619842로고정한다.

# C-014 사전 계획

작성 시각: 2026-11-02T19:31:05.869121+00:00

부모 C-013 11b4313c8d9c1b1c17ccdff70b9b75216cce3868, C-012 6fba3a00d587bc0f130420e0f5b8c264b5e7a548. Mac 연구 worktree의 docs/c-research-20261028에서 기존 HEAD/변경 없음 확인. 일반 checkout의 feature/swap-mcp와 .omx는 건드리지 않는다. 기존 SSH로 Spark 접속·실제 앵커와 부모 무손실 프레임 위치·ffmpeg/ffprobe 확인. 기존 C-014 실행 디렉터리 없음. 절대경로는 private manifest로 분리한다.

I50_S1/S_S1/ON2048_S2_A만 CPU 합성한다. 양끝 원 입력 앵커의52px 바깥 관측 영역을 사용하고 start 우선 같은 좌표 복사. 공통 관측 RGB exact/unknown0이 아니면 PLATE_NOT_ESTABLISHED. renderer background/sprite/중간RGB는 합성에 전달하지 않는다. 선택적 oracle audit은 plate freeze 뒤 평가 전용으로만 허용하나 필수는 아니다.

요청 경로 중심, core44/outer52/cosine8px feather, float64 RGB code값 혼합/np.rint/clip/uint8, core/outside 명시적 byte 복사를 고정한다. 결과로 mask를 조정하지 않는다. 모든99 PNG 저장/readback exact 및 부모 hash 전후 검증. 기존 B-032 blend 끝값 보존 원리 재사용; 옛 해상도/정규화/마스크 규칙은 이식하지 않는다.

생성 전 작은 CPU fixture로 plate provenance/관측 불일치/unknown/형식/alpha/rounding/덮어쓰기 거부/늘어진 support 잘림 한계를 확인한다. 부모 Reader 전체화면 검출·기존 임계값과 경로 scorer를 RAW/POST 전33프레임에 사용한다. I50/S 새경로, A 학습경로 구분. 주요9시점 center shift>2px 또는 POST 핵심 검출 실패는 회귀 조사. object<=28,collar32<d<=44,ring44<d<52,outside>=52 각각 MAE/p95/>25비율/픽셀수. core exact는 전체 객체 support 보존 증명이 아니다.

세 RAW/POST 영상과33프레임·alpha overlay·경계 crop·앵커/plate 출처 뷰어 제공. 실제 본 정적 범위만 clipping/seam 평가, temporal=UNVERIFIED 유지. 배경 복사 MAE0을 생성 능력이나 독립 개선 증거로 해석하지 않는다. 남은 객체 무늬 손상·주변 오염을 분리한다.

기존 C-012 make_stage/C-001 guarded CPU route 재사용. C-013 resume1 승인 guard 사본을 C-014 CPU에 승계하며 같은 freeze를 확인한다. 새 예외/가드 변경 없음.72GiB 시작/24GiB 실행,swap 증가64MiB/10초 swapout64MiB/PSI10%/worker swap0/OOM/외부 서비스·GPU/관측 오류 보호 유지. 실제 압박이면 중단, 자동 재시도 없음. 최대2threads, 순차 프레임, RSS목표2GiB 초과 중단. 총90분 중 마지막15분 전달. sampler/model/VAE/학습/GPU/다운로드/설치0. 품질 재시도0.

사전 commit 뒤 plate1/고정정책1/99PNG/파생MP4 3개 수행, 결과·한국어 해설·HISTORY/ROADMAP, Spark/Mac ZIP CRC/실제추출/hash/원본보존을 검증한다. 기존 판정/중단 이력 보존. 추가 학습·생성·mask 탐색을 시작하지 않는다.

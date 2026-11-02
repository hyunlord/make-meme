# C-013 승인된 재개 계획 — 2026-11-02

사용자가 이번 재개에서 명시적으로 승인한 예외: global swap 총량>64MiB만으로 START_SWAP_BUDGET을 내리는 시작 분기 제거. C-013 전용 guard 사본에만 적용. 부모 공통 memory/supervisor/safety/policy는 그대로 보존한다. code/resume-memory.patch가 전체 의미 변경이다. 기존 GLOBAL_SWAP_WARNING과 원래 swap 총량 로그를 유지한다.

기존 충분한 시작 관측(최소10초), 시작72GiB/런타임24GiB, baseline 대비64MiB 증가,10초 swapout64MiB, PSI full10%, worker swap0/max0, 메모리 한도/OOM, 외부 GPU/서비스/관측 오류/정상 종료 보호 모두 유지. 새로운 baseline은 실제 재개 첫 관측에서 얻고 작업 도중 재설정하지 않는다. 이전 stage/예산 state/8a5cc37 BLOCKED_SAFETY 보존. swapoff/swapon/재부팅/swappiness/다른 프로세스 종료 금지.

CPU/heavy 모두 같은 C-013 private guard 디렉터리로 설정하고 freeze에 실제 네 파일을 포함. 기존 make_stage 및 run_guarded를 재사용하며 새 launcher/supervisor/framework 없음. stage 이름은 resume1을 포함하여 과거 실패를 덮어쓰지 않는다. 기존 stage 생성기의 deadline은 이번 재개 시작+100분으로 제한해 마지막20분 전달을 남긴다.

1. 작은 정책 synthetic 검사 완료: 높은 안정 swap은 충분한 관측 후 CLEAR; 관측부족/성장/swapout/PSI/headroom/worker swap/OOM/외부 GPU/서비스 오류 차단. 결과 RESUME_POLICY_CHECKS.json.
2. 본 승인·patch·계획 commit/push 후 Spark 새 실제 관측10초 이상. 실제 압박이 발견되면 중단, 자동 반복 없음.
3. Spark 기존 연구 Python에서 기존 evaluator fixture 확인 및 필요한 기계적 수정. 검증된 fixture 없이 생성물 능력 판정 금지.
4. 기존 checkpoint/sidecar/PATHS 재사용, BASE_S2→I25_S1→I50_S1→I75_S1→S_S1 직렬. sampler5+기계예비1 미사용. 신규 학습/설치/다운로드/탐색0.
5. 실제 입력 parity/전33프레임/공통 ROI/정적 시트, 실제영상 우선 viewer/검토ZIP/Spark·Mac hash/CRC/추출, 결과·해설·HISTORY/ROADMAP commit/push/종료 확인. temporal UNVERIFIED unless continuous perceptual review.

새 정책을 검사했다고 연구 완료로 보고하지 않는다. 실제 압박 재중단이면 해당 관측 구간과 지표를 보고하고 더 완화하지 않는다.

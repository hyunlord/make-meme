# 승인된 한정 재개

사용자가 전달한 [amendment](../../work_orders/C003_START_POLICY_AMENDMENT_AND_RESUME_KO.md)에 따라 기존 미사용 추출1/영상2 범위를 재개한다. 과거 START_SWAPOUT_OBSERVED·CPU import 실패·NOT_CLEAN·UNKNOWN과 당시 heavy0는 불변이다.

C003/code/guard는 C001 동결 guard의 새 실행 사본이다. memory.py의 `elif start and swapout > 0` 두 줄만 제거했고 나머지 supervisor/safety/policy는 byte-exact다. 과거 C001/C002/C003 동결 파일·freeze·receipt는 수정하지 않는다. 같은 기존 run_guarded.py가 새 guard_code 한 경로를 CPU/preflight/supervisor/worker에 전달한다. 실제 import 경로와 SHA는 실행 전 비공개 route receipt, 공개SHA 요약으로 확인한다.

시작72GiB/10초/전역swap64MiB상한, runtime24GiB, 증가64MiB/10초swapout64MiB/PSIfull10%, worker swap0/OOM/identity/external/service/observation 보호와 MemoryMax/High 계산은 불변이다. 작은 변화는 GLOBAL_SWAP_WARNING이며 CLEAR 강제덮어쓰기는 없다. 수치는 연구 예산이지 vendor보증이 아니다.

실제 private6표본 재생은 새정책하 CLEAR+warning이며 과거 기록의 PASS 변경이 아니다. [CPU근거](START_AMENDMENT_CPU.json)는 synthetic 중요한차단13개와 실제replay를 구분한다. 현재 자원은 새10초 live관측으로 판단한다.

연구방법/조건/관측표는 불변, 기존weight재사용/재다운로드0. 완료추출1pass→프로세스회수→조건검사→DYNAMIC→HOLD순이다. 영상heavy2+기계적예비1, latent이후VAE복구1한도와 품질재시도0을 유지한다. 첫 작업소요약20분을 포함해 총3시간을 넘기지 않도록 이번 GPU 실행deadline을 재개시각+2시간으로 보수적으로 잡고 그 뒤20분을 전달에 남긴다. 자원/외부작업 중단은 자동재시도하지 않는다.

CPU extraction 경로는 sibling 절대 import bootstrap을 유지하면서 모델 클래스 import를 cpu_only return 뒤로 옮겼다. CPU receipt에서 model_imported=false와 cuda_initialized=false를 확인한다. 이는 모델 연산 변경이 아니다.

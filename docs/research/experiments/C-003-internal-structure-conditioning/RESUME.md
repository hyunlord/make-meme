# 승인된 한정 재개

사용자가 전달한 [amendment](../../work_orders/C003_START_POLICY_AMENDMENT_AND_RESUME_KO.md)에 따라 기존 미사용 추출1/영상2 범위를 재개한다. 과거 START_SWAPOUT_OBSERVED·CPU import 실패·NOT_CLEAN·UNKNOWN과 당시 heavy0는 불변이다.

C003/code/guard는 C001 동결 guard의 새 실행 사본이다. memory.py의 `elif start and swapout > 0` 두 줄만 제거했고 나머지 supervisor/safety/policy는 byte-exact다. 과거 C001/C002/C003 동결 파일·freeze·receipt는 수정하지 않는다. 같은 기존 run_guarded.py가 새 guard_code 한 경로를 CPU/preflight/supervisor/worker에 전달한다. 실제 import 경로와 SHA는 실행 전 비공개 route receipt, 공개SHA 요약으로 확인한다.

시작72GiB/10초/전역swap64MiB상한, runtime24GiB, 증가64MiB/10초swapout64MiB/PSIfull10%, worker swap0/OOM/identity/external/service/observation 보호와 MemoryMax/High 계산은 불변이다. 작은 변화는 GLOBAL_SWAP_WARNING이며 CLEAR 강제덮어쓰기는 없다. 수치는 연구 예산이지 vendor보증이 아니다.

실제 private6표본 재생은 새정책하 CLEAR+warning이며 과거 기록의 PASS 변경이 아니다. [CPU근거](START_AMENDMENT_CPU.json)는 synthetic 중요한차단13개와 실제replay를 구분한다. 현재 자원은 새10초 live관측으로 판단한다.

연구방법/조건/관측표는 불변, 기존weight재사용/재다운로드0. 완료추출1pass→프로세스회수→조건검사→DYNAMIC→HOLD순이다. 영상heavy2+기계적예비1, latent이후VAE복구1한도와 품질재시도0을 유지한다. 첫 작업소요약20분을 포함해 총3시간을 넘기지 않도록 이번 GPU 실행deadline을 재개시각+2시간으로 보수적으로 잡고 그 뒤20분을 전달에 남긴다. 자원/외부작업 중단은 자동재시도하지 않는다.

CPU extraction 경로는 sibling 절대 import bootstrap을 유지하면서 모델 클래스 import를 cpu_only return 뒤로 옮겼다. CPU receipt에서 model_imported=false와 cuda_initialized=false를 확인한다. 이는 모델 연산 변경이 아니다.

## 실제 추출과 입력 동결

재개 CPU 경로는 COMPLETE/CLEAR, cuda_initialized=false/model_imported=false였다. 그 뒤 한 번의 공식 FP32 extraction이33장/2.716827969초로 완료됐고 strict load/weights_only/keyshape를 기록했다. guard COMPLETE/CLEAR와 프로세스 종료 후 CPU 조건 변환을1.935635780초 수행했다. 재다운로드0이다.

실제 J16과 조건8/16 관측에서 검정/회색 선·밝은 배경을 확인해 공식 출력 무반전을 고정했다. 얼굴 눈/주둥이/귀·목 경계는 보이며 몸통/발 내부는 희박하고 얇은 부분은 제외된다. 구조선은 관절GT가 아니다. I밖은33장 모두 기존L과pixel-exact, 중간31장의 D/H차이는487,891pixels다. 이 유효성은 품질이득 증거가 아니다. 실제 입력계보/hash는 CONDITIONS.json에 동결한다.

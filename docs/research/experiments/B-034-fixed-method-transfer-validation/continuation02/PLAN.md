# B-034 CONTINUATION_02 — loader 환경 계약 복구

상태: 착수, GPU 미실행. 시작 기준 원격/로컬 HEAD `62df7de8c748c7498c56f751b3e5bfc9aa0f49d8`. 같은 실행 중복 여부를 로컬/Spark에서 확인한다. 과거 결과·실패·코드는 보존한다.

2026-10-27T09:39:00Z 시작, 새 heavy 시작/종료 관리 cutoff10:54Z, 전체 hard deadline11:09Z. 마지막15분은 보존·전달. CPU 수정 목표20분. 최초 현재 시각 확인09:40Z보다 이른 보수적 시작을 사용한다.

## 목적과 기존 판정

최종 목표는 target 외형과 source 동작·장면을 함께 보존하는 로컬 객체 편집이다. 이번은 새 연구 번호가 아니라 기존 차량 A BASE+RGB_POST / B FINAL_LATENT_ONLY+같은POST / C STEP+같은POST의 남은 C 복구다. A/B를 재생성하거나 재decode하지 않는다.

CONT01 BASE target 외형 FAIL, FINAL_ONLY 추가 이득 미관찰, STEP FAILED_BEFORE_FIRST_FORWARD(시도1/forward0/step0/latent0)를 유지한다. 원인은 새 worker의 `B007E_LOADER_REPORT` 전달 누락이며 CUDA/모델/메모리 원인으로 확대하지 않는다. 과거 guard/recovery, 비강체 ANCHOR_UNSUITABLE/영상 NOT_RUN, B033 단일 사례 PARTIAL도 그대로다.

## 최소 코드 변경

검증된 CONT01 safety/supervisor는 byte-preserving 복사한다. 새 private CONTINUATION_02와 공개 continuation02에 필요한 wrapper만 분리한다. 새 framework·backend 변경 없음.

실제 worker와 CPU `--preflight-only`가 같은 bootstrap/validator를 사용한다. 모델 import·torch/CUDA 초기화·weights 접근 전에 다음을 명시 대입한다(setdefault 금지).

- HF_HUB_OFFLINE=1
- TRANSFORMERS_OFFLINE=1
- B007E_LOADER_REPORT=이번 STEP_S root의 절대 reports/loader.json

이번 STEP_S인지, config/입력 경로, 보고서 허용 범위, reports 존재/쓰기 가능, loader.json 부재를 확인한다. 고유 임시 파일로 쓰기 검사 후 그 파일만 정리한다. loader.json은 생성하지 않는다. 기존 loader의 다른 필수 환경 계약도 선택 경로에 한정해 확인한다. 가능하면 isolated staged_loader의 환경/출력 경로 확인만 checkpoint 접근 전으로 옮기며 dtype/key/RoPE/적재 연산은 변경하지 않는다. 보고서 삭제/KeyError 무시는 금지한다.

## CPU acceptance

같은 Python executable과 worker entrypoint로 검증한다.
1. 부모 변수 없음 → 현재 절대 경로 설정.
2. 부모 과거 값 → 현재 절대 경로로 덮어씀.
3. bootstrap 미실행/필수 값 없음 → 모델 로딩 전 validator 실패.
4. 충돌/쓰기 불가/범위 밖 경로 거부.
5. 실제 loader.json/생성 산출물 없음, torch/CUDA/model import 전 종료.
6. 실제 STEP도 같은 bootstrap 경로, 검사 전용 우회 없음.

통과하면 CPU 보고서만 내고 멈추지 않고 fresh safety→STEP→decode를 승인 범위에서 수행한다. 사전 코드/설정/입력 freeze commit 후 GO. 미통과는 heavy 미실행으로 보고한다.

## 고정 artifact와 계산

BASE/CONTROL raw·latent·PNG·MP4, source latent,16leaf 조건, 실제 noise/RNG/timesteps/sigmas,E/M, 기존 crop을 읽기 전용 재사용. encoder/prefix0. B033 clean_constraint와 혼합 규칙 동일. 기존 fullweights 장시간 재해시 없음.

896×512,17frame,source_fps=null,preview24fps,timebase_assumed=true; UniPC40/shift3/CFG5,기존seed/noise/양CFG. LoRA/ALG/B029gate/manualRoPE OFF. E/M은 잘못된 BASE SUV를 포함한 output-assisted support이며 원하는 클래식 target GT가 아니다. Hempty/r4/feather4와 기존시간group/8×8max/3×3guard 유지.

## 예산과 안전

새 STEP heavy/model loading attempt1, fullsampler1(40step/80forward/40constraint), 해당 final latent D1. 첫 forward 전 실패도 사용. BASE/CONTROL 재생성·재decode0, source/refencoder0, 이미지/학습/설치/download0, retry/seed/설정탐색0.

CONT01 종료신원 처리·fresh safety·72GiB시작/24GiBheadroom/swap0·보호서비스identity/queue/외부GPU 검사 그대로. 다른프로세스종료/가드완화0. STEP 종료와 자원회복 확인 뒤 VAE worker를 실행한다. final latent decode전 원자저장/readback. 실패하면 단계·예외·모델forward/step/constraint/보존artifact를 기록; guardCOMPLETE나위험PID부재로 workerexit!=0을 PASS 처리하지 않는다.

## 평가 고정

SOURCE/TARGET/A0/BASE/FINAL_ONLY/STEP raw 및 같은E RGB_POST, 전체17/local0/8/16/기존crop/전체화면을 본다. 클래식 긴차체·노출바퀴·열린상부, 닫힌SUV/왜건,접근방향·크기변화,도로·산·울타리·타객체,경계·하부조각·접촉·그림자를 별도 판정한다.

STEP이 E밖으로 나가도 확장하지 않는다. 색보정/합성규칙변경/문자제거/SR/보간/warp0. 배경만 개선되고 target없으면 장면PARTIAL+결합FAIL. 기존SUV유지를 targetnonregressionPASS로 부르지 않는다. 새 외형은 실제target특징으로 판정하며 기대효과로 추정하지 않는다. 연속시청 없으면 temporalUNVERIFIED. 프레임을 독립 반복으로 세지 않는다.

방법판정 ADDITIONAL_BENEFIT/NON_REGRESSION_ONLY/TRADE_OFF/NO_BENEFIT/WORSE/INCONCLUSIVE. 핵심은 두 대조군보다 동일POST 후 내부/경계 추가이득, targetFAIL 해소, 기본채택 근거다.

## 기록·전달·종료

HISTORY/ROADMAP/RESULTS/COSTS/REPRODUCE와 짧은 실행계약 한국어 해설을 남기고 연구branch commit/push/remoteSHA 확인. 개인정보/weights/conditiontensor는 공개하지 않는다.

compact: 비교MP4/입력/viewer/작은시트/보고서/재현. full: 신규STEPraw/latent/필요수치근거. 기존93.6MBraw 중복금지. Spark/Mac/tmp에 CRC/payloadhash/실제추출/전송byte동일성 확인. 하지 않은 검증PASS금지.

한 번 이후 종료; 추가사례/seed/학습/모델/mask/강도0. 같은환경/경로오류 재발도 예산확대없이 증거를 보존한다.

# V-002 r1 실행 연결 기록

이 기록은 r1의 실제 인수·admission과 완료된 부분을 설명한다. 첫 실행 `9f78153`의 `BLOCKED_EXTERNAL_GPU`, 영상 0/5, 당시 입력과 가드 기록은 보존한다. 후속 실행의 성공을 과거 판정에 소급하지 않는다. 현재 전체 실행은 완료되지 않았으며 단계별 최신 상태는 `RUNS.json`을 따른다.

## 입력과 운영 인수

1183개 hash 비교(준비 입력 808, 부모 자산 369, 역할 파일 6)가 모두 일치했고 재제작하지 않았다. 원본·앵커·SAM·depth 및 canny 조건을 재사용한다. imagegen·새 depth 추론·학습·Bernini 실행은 0회다.

cache helper는 존재 여부만 확인한 것이 아니라 허용된 단일 명령의 실제 호출이 `APPLIED`로 기록됐다. heavy 적재 직전마다 다시 적용한다. helper가 이후 실패하면 SAM·1.3B는 진행할 수 있지만 14B·LTX는 `SKIPPED_NO_CACHE_HELPER`다. 다른 sudo 명령·서비스 변경·타 프로세스 종료는 없다.

`fls-slot-keeper`는 읽기 전용으로 확인했다. 인터페이스가 FLS 디렉터리·세션·스크립트 구조에 결합되어 있고 문서화된 범용 사용 계약이 없어 `NOT_USED_FLS_SCOPED_INTERFACE`로 남겼다. 임의 슬롯 요청이나 서비스 변경은 하지 않았다.

GPU 실행은 root 실행 담당 하나만 수행한다. 다른 작업 담당은 CPU 문서·정적 검사에 한정하며 모델 작업과 환경 import 시험을 병렬 실행하지 않는다. 외부 GPU compute 프로세스와 알려진 배치 부모를 함께 관측해 자식 사이 공백을 종료로 오인하지 않는다. CPU 상시 서비스는 외부 GPU 작업으로 세지 않는다. 첫 SAM admission은 18:13:49–18:16:49 UTC의 4표본에서 모두 비어 있었다. 이후에도 60초 간격·최소 180초·마지막 3표본 연속 부재를 요구한다. 전체/단계 대기 상한과 관측 오류 중단은 유지한다.

## 상속된 시작 조건의 계약 연결 수정

baseline 두 번째 SAM heavy와 이전 M3 CPU stage는 모델 적재 전에 `START_HEADROOM_NOT_MET`로 거절됐다. 첫 거절의 MemAvailable은 119789596672 bytes, swap 0, PSI 0이었다. 원인은 V-001 E2 개정 3에만 있던 시작 112GiB 조건과 `min(100, available-12)` worker cap이 r1에 상속된 것이었다.

r1이 유지하도록 지정한 V-001 §7에는 그 E2 전용 시작 조건이 없고 r1은 `MemoryHigh=MemoryMax=100GiB`를 명시한다. 따라서 기존 guard와 거절 stage를 보존한 채 `code/guard-r1-contract` 별도 사본에서 해당 시작 검사와 cap 연결만 바로잡았다. 새로운 `v002-r1c-` stage와 admission을 사용한다. `R1_CONTRACT.diff`, `PRECHANGE_SNAPSHOT.json`, `CONTRACT_ALIGNMENT.json`에 연결 근거를 기록하고 CPU 검사 38개를 통과했다. 이는 결과를 본 품질 재시도나 과거 중단의 PASS 변경이 아니다.

OOM, 첫 `NV_ERR_NO_MEMORY`, MemAvailable 12GiB 미만 30초, PSI full 25% 초과 60초, 관측 실패, 100GiB 사전 peak 상한은 그대로다. 실행 중 새 외부 GPU 작업을 발견하면 생성 단계만 `CONCURRENT_EXTERNAL_GPU`를 기록하고 현재 생성을 마친다. 다음 단계는 다시 기다린다. CPU/SAM/probe에는 그 생성 완료 예외를 적용하지 않는다.

## 현재 실측과 아직 없는 결과

baseline E1 두 출력의 SAM·CPU 측정과 진단 시트는 완료됐다. 개 2마리 검출은 각각 73/73프레임이고 전체 프레임 Lab/IG 평균 IoU는 seed 20261103에서 약 0.548758, seed 20261104에서 약 0.532575다. 이 기하 측정은 사용자의 기존 판정인 “개가 움직이지만 원본과 전혀 다른 동작을 한다”를 바꾸지 않는다. 뒤바뀜 수치는 기하 대응 proxy이며 시각적 정체성 유지의 증명이 아니다.

M1은 976.877초에 73프레임을 생성했다. 50 scheduler step, 100 model_fn call이며 peak RSS 13114093568 bytes, CUDA peak allocated 20036397568 bytes, reserved 21728591872 bytes다. 가드 정상 완료이며 endpoint 덮어쓰기·후합성·학습은 없다. MP4, 73 PNG, 최종 latent 및 raw를 보존했다. M2는 2026-11-04T19:02Z Spark SSH timeout 및 Tailscale offline 이후 UNKNOWN이다. 마지막 확인은 21/50 scheduler step, 44 model_fn call이며 완료 결과는 없다. 마지막 관측 가드는 CLEAR였고 관측된 MemAvailable 최저값은 95239196672 bytes, NVRM 이벤트는 없었다. 그 이후 관측이 끊겼으므로 OOM·재부팅·worker 종료 또는 정상 진행을 단정하지 않는다. M1 출력 SAM은 CPU 검증만 끝났으므로 새 출력의 자동 품질 측정 완료로 표시하지 않는다.

14B는 header·변환기·기존 BF16 로더 경로까지 정적으로 확인했으며 실제 변환은 아직 없다. 32.294GiB 변환 파일 자체만으로 전체 메모리 기준을 통과했다고 선언하지 않는다. T5/VAE 및 파일 cache, resident, 활성값을 포함한 추정과 그 가정을 기록하고 100GiB 이하일 때만 진행한다. 전체 cache 동시 잔류 가정은 기준을 넘을 수 있다. 자세한 계산은 `BF16_PREPARATION.md`에 보존한다.

## 해석과 전달의 경계

마스크 밖 원본 RGB는 VACE 입력 조건이다. 모델 출력의 마스크 밖 픽셀이 원본과 같다는 보장은 없고 실제 MAE로 평가한다. M3 첫 프레임 mask 0도 시간 압축 후 latent의 엄격한 고정을 보장하지 않는다. 출력 앵커 덮어쓰기나 배경 후합성은 하지 않는다.

M1–M3가 끝나면 14B 전에 검토 페이지·compact ZIP을 먼저 갱신한다. 아직 실행되지 않은 단계는 NOT_RUN과 이유를 표시한다. 최종 품질은 `HUMAN_REVIEW_PENDING`, 연속 지각 품질은 `temporal=UNVERIFIED`다. 자동 수치·프레임 decode·브라우저 재생 여부를 사용자 검토 대신 사용하지 않는다. 후속 실험·학습·생성은 예약하지 않는다.

## 관측 상실 이후의 한계

실행 담당은 제한된 연결 재확인을 진행 중이다. M3·14B·LTX 및 새 출력 SAM은 NOT_RUN이다. M1 원 MP4는 Spark에서 생성됐지만 아직 Mac에 복사되지 않았다. 따라서 Mac 전달과 ZIP 무결성 확인, 자체 worker 종료를 완료로 보고하지 않는다. M2의 실행 여부를 알 수 없는 동안 중복 생성이나 자동 재시도를 시작하지 않는다. 기존 가드·중단 기록은 그대로 보존하며 이 기록을 최종 종료 판정으로 사용하지 않는다.


최종 실행 상태: BLOCKED_HOST_UNREACHABLE. 기존 감독 SSH 연결도 timeout/broken pipe로 끝났으며 이는 원격 worker 종료 증거가 아니다. 추가 heavy 호출·재부팅·프로세스 종료는 하지 않았다.

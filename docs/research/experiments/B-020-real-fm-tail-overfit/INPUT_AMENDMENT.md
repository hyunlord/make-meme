# B-020 실제 자료 제공에 따른 실행 계약 확정

2026-10-24 · 시작 HEAD `64a66452561544fbb2d8c2bf6113a01db7710fe6`.

사용자는 새 자연동작 영상이 기존 앉은 Lab 참조 사진과 같은 실제 강아지임을 확인하고, 두 자료를 비공개 로컬 연구 학습·평가에 사용하는 것을 명시적으로 허용했다. 공개 GitHub 업로드/공개 재배포는 금지했다. B-020의 해당 자료 게이트를 해소하며, 기존 제3자 source의 권한 미확인 기록은 변경하지 않는다. 동일 개체는 사용자 진술에 근거하며 독립 생체 식별 검사라고 하지 않는다.

## 생성 결과 전에 선택한 source와 관측

원본은 1920×1080, 30/1fps, 369frame, video duration12.3초, timebase1/90000이다. SHA256은 `d286f6e25990080fe87b6903cdbcf8e30f89b0f367bd066f8e346d959fff31b0`. 미디어·이름·개인 경로는 비공개로 보존한다.

사용자가 우선 지정한4.2~5.0초의 원본 f126~150을 source-only 시트로 검토했다. 최초 적합17장 **f126~142 inclusive**, source PTS4.200000~4.733333초를 선택한다. 몸통과 발을 포함한 전신이 화면 안에 있고 후반에 머리를 화면 왼쪽으로 돌리는 변화가 보인다. 뒤쪽 발의 가림과 꼬리/발 경계는 정밀 관절/접촉 정답으로 채우지 않는다. 구간이나 성공 기준을 생성 결과 후 바꾸지 않는다.

D=Y는 같은 처리 RGB17장이다. 30fps를 유지하며 첫/끝 표본 간격16/30초, 출력 지속시간17/30초다. 프레임 보간/복제/속도변경은 없다. 음성은 모델 학습 입력에 넣지 않는다.

공간변환은 전신 보존을 위해 가로896×512를 사용한다. source1920×1080을896×504로 비율 유지 축소한 뒤 위/아래4px을 padding한다. 참조는 기존 앉은 Lab 사진과 RED/WHITE support를 같은 aspect-fit 변환으로 가로canvas에 넣어 center crop으로 머리/발을 없애지 않는다. 사진 내부 배경은 제거하지 않고 추가 여백만 명시한다. 정확한 pixel/파일 hash와 변환 계보는 private manifest에 기록한다.

새 driving mask는 기존 비학습 CPU 처리와 제한된 수동 관측으로 준비한다. 새 모델은 설치하지 않는다. RED는 Lab, WHITE는 배경이며 그림자를 개체로 처리하지 않는다. 얇은 꼬리·발·반사·가림 경계의 불확실성을 보존하고 자동 segmentation 성능으로 보고하지 않는다. 실제 입력 visual/CPU 확인 뒤 P를 시작한다. f0/8/16 확대와 전체17장 입력을 검토했으며, 안쪽 뒷다리 support의 일부 과대 영역과 얇은 경계는 PARTIAL로 남긴다. 원본 RGB/마스크 decode34/34와 D=Y byte 동일을 확인했다.

## 사전 고정 텍스트와 수치

Positive:

> A black Labrador retriever with a broad chest, sturdy body and thick legs, matching the reference dog, stands naturally on all four legs on a light tiled floor in a sunlit room. It gently turns its head toward the left side of the image while its body stays mostly in place and its tail moves. Natural realistic motion and a stable viewpoint.

Negative는 empty. baseline/trained/positive FM 조건에 동일한 문장을 사용한다. reference와 Y의 자세·장면은 다르며 D=Y 복사 shortcut은 남는다.

계획의 train sigma0.2/0.5/0.8, 같은clip holdout sigma0.65를 유지한다. 각 CPU noise seed는2026102401/2026102402/2026102403/2026102404로 사전 고정하고 실제 noise tensor hash를 prefix 전에 기록한다. sampler seed20261022·UniPC40step·shift3·CFG5, animation H0/ALG OFF/history=None/additional_ref=None, adapter 초기Bzero·rank4/alpha4/dropout0·AdamW lr1e-4/wd0를 유지한다. parity/reload/OFF tolerance는 atol=rtol1e-3으로 실행 전에 고정하며 결과 후 늘리지 않는다.

## 순서·상한

P(actual conditions+Y VAE)1회 → frozen prefix4tuple 각1회 → baseline sampler/decode 각1회 → tail worker1회(max20update, 총추가tail평가12회 이내) → trained sampler/decode 각1회. 각 phase 종료와 자원 회복을 확인한다. 코드·입력hash·실제config를 사전 commit한 뒤 실행한다. 추가 모델/패키지/데이터 다운로드·튜닝·재시도0.

전체 기한은10:58~14:58UTC. 기존72GiB 시작/24GiB 실행 headroom·swap0·타서비스 보호를 유지한다. cgroup과CUDA·RSS·시스템 가용메모리는 구분한다. 불일치/안전문제는 중단하고 실제 저장물을 보존한다. 최종latent를 decode보다 먼저 저장하고 decode 실패로 sampling을 반복하지 않는다.

이 문서는 기존 DATA_PENDING 기록을 삭제하지 않고 새로운 사용자 제공 사실과 실행 계약을 추가한다. 아직 실제FM 학습/영상 품질 PASS를 뜻하지 않는다.

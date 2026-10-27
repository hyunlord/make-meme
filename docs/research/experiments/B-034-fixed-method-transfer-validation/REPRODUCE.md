# B-034 재현과 현재 재사용 경계

실제 시작 입력/코드는 `94c33413d86c71f28f0069c2b604c53db6ae559e`, 차량 영상 freeze는 `9b821a7633c26b9f372917058f0c0c40bbd4692c`다. [전체 의뢰서](../../work_orders/20261027-B034-fixed-method-transfer-validation.md), [입력 계약](INPUT_CONTRACT.json), [영상 freeze](VIDEO_FREEZE_RIGID.json), [실행 연결](RUNTIME_REPRODUCE.md)을 함께 읽는다. 기존 Qwen/SCAIL 환경·가중치를 재사용하며 설치 명령은 없다.

이번 승인 예산 중 실제 사용은 이미지2, 차량 ENC1, 차량 BASE sampler1이다. 아래 경로 설명은 재시도나 추가 실행 허가가 아니다. 인물은 앵커 부적합, 차량은 BASE 종료 가드 때문에 downstream 미실행이다.

## 실행된 경로

1. `data_code/prepare_inputs.py`로 이미 확보된 DAVIS 자료를 고정 selection에 따라 준비했다. source PNG와 lossless driver decode의 값 일치, GT support 및 target crop 내부 RGB 보존을 검사했다.
2. 기존 Qwen 환경에서 `code/qwen_launch.py ROOT 7200 PYTHON code/qwen_runner.py ROOT`로 두 고정 입력을 각각 한 번 실행했다. 실제 입력 순서와 effective encoder shape는 private receipt에 남겼다.
3. 적합 차량 A0만 `manual_anchor_mask.py A0.png INPUTS_DIR`로 실제 수동 polygon을 rasterize했다. 원본 GT는 target mask로 복사하지 않았다.
4. `video_code/prepare_config.py TASK`와 `prepare_layout.py TASK CODE UPSTREAM MODELS`로 CPU freeze를 만들었다. 공식 normalization을 통과한 입력 hash와 각 stage config를 기록했다.
5. 기존 환경의 `runtime_launch.py STAGE_ROOT SECONDS PYTHON run_phase.py STAGE_ROOT STAGE`로 `ENC`, 이어 `BASE_S`만 실행했다. BASE_S는40/80 final latent를 저장했지만 supervisor reason은 `other_service_work`다.

실제 절대 경로·명령·프로세스 ID·각 파일 hash는 비공개 full 자료에 있다. 공개 문서에는 개인 경로와 모델 파일을 넣지 않는다.

## CPU 검증

기존 고정 scheduler import가 가능한 같은 환경에서 B033과 byte-identical한 `tests/test_contract.py`를 실행했다. OFF/M=1 경로, M=0 history, mask 축/shape, final endpoint 및 원본 tensor 불변의 소형 검사4개 PASS다. 전체14B 수치 동등성이나 영상 품질 증거가 아니다. [STATIC_CHECKS](STATIC_CHECKS.md)는 문법 검사와 미사용 lint/type 도구를 구분한다.

## 저장 latent를 재사용할 때

실제 저장된 것은 차량 BASE의 최종 generated-only model-space x0이며 reference prefix가 아니다. 공식 WanVAE wrapper의 mean/std 처리를 그대로 사용해야 한다. 이번에는 decode를 실행하지 않았으므로 RGB 내용은 미관측이다. private final metadata의 조건 hash·initial noise·40/80 counter·finite·shape·dtype·모델/코드 계보와 파일 SHA를 함께 검증한다.

기존 `BASE_D` downstream gate는 이전 stage의 clean `service_exit`를 요구한다. 현재 receipt를 수정하거나 해당 assertion을 삭제해 실행하지 않는다. 다음 작업에서는 저장물을 보존한 채 종료 이유·자원/타 서비스 상태를 별도로 해결한 후 허가된 VAE-only 범위를 정해야 한다. sampler 재생성은 필요하지 않으며 이번에는 자동 실행하지 않는다.

## 검토 매체

source의 원래 RGB MP4는 Chrome 색상 오류가 실제 확인됐다. 원본은 보존하고 source PNG에서 yuv420p preview를 새로 만들었다. 기존 MP4 재인코딩/덮어쓰기0, 새 preview 파생 인코딩2다. anchor/source 검토 HTML은 모든 미생성 영상 method를 NOT_RUN으로 표시한다. CRC·payload hash·실제 ZIP 추출·호스트 간 바이트 동일성은 별도 delivery receipt에서 확인한다.

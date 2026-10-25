# B-025 재현 계약

공개 코드만으로 개인 입력을 다운로드할 수 없다. 비공개 run manifest의 별칭을 권한 있는 source/reference/model 경로에 연결해야 한다. 현재 설치된 고정 SCAIL 환경을 재사용하며 새 패키지·모델 설치는 포함하지 않는다.

1. B024 parent의 conditions receipt, 원본 f126..142/17f30fps/896×512, 실제 initial noise와 frozen upstream/model hash를 확인한다.
2. Lab은 B024의 회색 RGB/RED-BLACK mask와 VAE/CLIP를 그대로 사용한다. IG는 사용자 원본과 기존 support의 좌표 계보를 확인하고 aspect-fit 후 support 내부 RGB를 보존, 외부/padding을128로 만든다. 개인 파일 경로는 비공개 manifest에만 있다.
3. `code/prepare_layout.py`로 ENC→LAB_PROBE→LAB_S→LAB_D→IG_PROBE→IG_S→IG_D의 기존 worker layout을 준비하고 `code/freeze_run.py`로 코드·입력·config·parent를 고정한다. 준비 스크립트의 인자는 파일 내 CLI를 따른다. 공개 configs는 역할별 값이며 실제 경로 매핑/보호 서비스 PID는 비공개다.
4. CPU 계약 검사를 실행한다. actual parent-cache 검사는 권한 있는 B024 cache가 필요하다. 소형 fixture 통과는 실제 모델/품질 통과가 아니다.
5. 기존 Python으로 `code/runtime_launch.py STAGE_ROOT TIME_LIMIT python code/run_phase.py STAGE_ROOT STAGE`를 실행한다. 시간과 메모리 가드는 고정한다. ENC 한 번에서 common positive T5 한 번과 IG VAE/CLIP 각 한 번만 계산한다. Lab-vsB024는 positive t1만, pair는 참조 최대6leaf만 변경돼야 한다.
6. 이전 worker 종료·자원 회복·조건 계약을 확인한 뒤 각 case의 PROBE/S/D를 순차 한 번씩 수행한다. S는40step80forward 후 finite final x0를 원자적으로 저장한다. D는 해당 final latent만 공식 VAE로 복원한다. 실패해도 자동 재실행하지 않는다.
7. raw-derived 전체17 PNG, native30fps MP4, source/참조/두 raw 비교와 local0/8/16을 보존한다. 보간·ROI 합성·warp·복원·선별은 없다. 재생 가능성과 실제 연속 품질 검토를 구분한다.

이번 승인 예산은 실험 당시 한 pair에 한정된다. 이 문서는 추가 sampler 자동 실행 승인이 아니다. 모델 파일·미디어·cache·latent는 공개 저장소에 넣지 않는다. 최종 비공개 ZIP의 manifest와 코드/config/출력 hash가 실행 증거이며, 기존 기준선을 재생성하지 않는다.

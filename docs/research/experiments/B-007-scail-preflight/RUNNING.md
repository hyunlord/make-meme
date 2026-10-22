# B-007A 실행 기록

## 실행 전 고정 — 2026-10-22 06:06 UTC

시작 원격 HEAD `6ca9271b8d565cf88db22bbfe61bbedecf7b915c`. 시작 06:01:33 UTC, 종료 상한 08:01:33 UTC. 기존 PLAN과 A/VACE 환경을 보존한다.

- 공식 SCAIL Wan commit `78fe19576bb06be96c2375e088574a262a300edb`의 attention wrapper를 그대로 읽어 실행한다. 모델 forward가 아닌 작은 BF16 attention만 허용한다.
- 최대 두 설치 방법과 다운로드2GB 상한은 `code/kernel_methods.json`에 고정한다. 첫 실패가 근거와 함께 기록된 경우에만 두 번째 방법을 검토한다.
- CPU mask/crop/FPS 코드는 `code/input_preflight.py` 및 JSON에 고정한다. 수동 관측과 비학습 GrabCut을 활용하며 자동 분할 정확도를 주장하지 않는다.
- 세로 reference로 인한 공식 H/W 자동 교환을 반영한다. RGB bicubic과 categorical mask nearest는 동일 geometry를 사용하나 upstream과 픽셀 동일하다고 주장하지 않는다.
- 가중치 다운로드0, 전체 영상 diffusion 추론0, 학습0. 커널 성공과 SCAIL 전체 실행/생성 품질은 별도다.

## 방법1 실패 및 방법2 선택 — 2026-10-22 06:12 UTC

릴리스 flash-attn 2.8.3.post2 source 8,453,127 bytes를 hash 확인 후 격리 prefix에 빌드했다. 실제 컴파일은 C++17 대 Torch2.14 ATen의 C++20 요구 충돌로 실패했다. import/커널 성공으로 처리하지 않는다. 공식 고정 main의 torch>=2.13 C++20 분기와 SM121 분기가 해당 오류에 대한 근거이므로 사전 등록한 두 번째 방법만 시도한다. 임의 source patch/세 번째 버전 탐색은 하지 않는다.

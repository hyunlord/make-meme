# B-007A 실행 기록

## 실행 전 고정 — 2026-10-22 06:06 UTC

시작 원격 HEAD `6ca9271b8d565cf88db22bbfe61bbedecf7b915c`. 시작 06:01:33 UTC, 종료 상한 08:01:33 UTC. 기존 PLAN과 A/VACE 환경을 보존한다.

- 공식 SCAIL Wan commit `78fe19576bb06be96c2375e088574a262a300edb`의 attention wrapper를 그대로 읽어 실행한다. 모델 forward가 아닌 작은 BF16 attention만 허용한다.
- 최대 두 설치 방법과 다운로드2GB 상한은 `code/kernel_methods.json`에 고정한다. 첫 실패가 근거와 함께 기록된 경우에만 두 번째 방법을 검토한다.
- CPU mask/crop/FPS 코드는 `code/input_preflight.py` 및 JSON에 고정한다. 수동 관측과 비학습 GrabCut을 활용하며 자동 분할 정확도를 주장하지 않는다.
- 세로 reference로 인한 공식 H/W 자동 교환을 반영한다. RGB bicubic과 categorical mask nearest는 동일 geometry를 사용하나 upstream과 픽셀 동일하다고 주장하지 않는다.
- 가중치 다운로드0, 전체 영상 diffusion 추론0, 학습0. 커널 성공과 SCAIL 전체 실행/생성 품질은 별도다.

## 방법1 실패 및 방법2 선택 — 2026-10-22 06:10 UTC

릴리스 flash-attn 2.8.3.post2 source 8,453,127 bytes를 hash 확인 후 격리 prefix에 빌드했다. 실제 컴파일은 C++17 대 Torch2.14 ATen의 C++20 요구 충돌로 실패했다. import/커널 성공으로 처리하지 않는다. 공식 고정 main의 torch>=2.13 C++20 분기와 SM121 분기가 해당 오류에 대한 근거이므로 사전 등록한 두 번째 방법만 시도한다. 임의 source patch/세 번째 버전 탐색은 하지 않는다.

## 동일 방법2 실행기 경로 수정 — 2026-10-22 06:14 UTC

`ninja.BIN_DIR`가 빈 문자열이어서 기존 실제 Ninja 실행 파일을 PATH에 넣지 못하고 serial distutils로 내려갔다. 기존 실행 파일의 `--version`을 확인하고 owned build process group만 중단했다. 로그와 object를 보존하고, 같은 source/arch/compiler를 실제 Ninja 경로로 재개한다. 새로운 설치 방법이나 다운로드가 아니며 원래 방법2 deadline 06:45:33 UTC를 명시적으로 유지한다.

## 실제 색상 압축 함수 CPU 검사 추가 고정

생성 없이 pinned helper 자체를 실행해 실제 준비 mask의28채널/시간축/색상 슬롯을 확인한다. driver 실제 순서는 bilinear 절반 resize 뒤 helper(additional_spatial_downsample=1)이며, helper2와 같다고 가정하지 않는다. 함수 AST만 추출해 CPU 실행하고 전체 pipeline/model import는 하지 않는다. area 보간의 fractional occupancy도 기록한다. 이는 기존 mask/FPS 사전검증 범위의 세부 검증이며 새로운 모델 실험이 아니다.

## 빌드 진행률과 시간 상한 — 2026-10-22 06:20 UTC

교정된 실행기는 CUDA compiler4개를 실제 병렬 실행한다. 06:19:20 기준97개 object 중11개 완료, MemAvailable 약79.63GB, swap0이었다. 진행률을 근거로35분에서65분으로 늘리는 방안을 검토했으나 live supervisor는 deadline을 시작 때 고정한다. 안전한 live 변경이 없어 **연장은 적용하지 않았다**. 같은 빌드를 감시 밖으로 떼거나 재시작하지 않고 기존 방법2 종료 상한06:45:33 UTC를 유지한다. timeout은 SM121 kernel 비호환 판정이 아니라 BUILD_TIME_BUDGET_EXCEEDED이며 실제 kernel은 그때까지 설치가 끝나야만 실행한다.

## 시간 예산 재검토: 감시 종료 후 동일 빌드 한 번만 이어가기 — 2026-10-22 06:36 UTC

앞선 live deadline 연장 거절은 그대로다. 사용자 상한은 총2시간/최대2가지 설치 방법이며35분은 실행자가 보수적으로 정한 한 프로세스의 내부 상한이다. 56/97 object까지 오류 없이 진행되는 증거를 근거로, 단순 내부 timeout 때문에 실제 연산 검증을 미리 포기하지 않도록 **원래 감시가 완전히 종료된 뒤 동일 방법2를 한 번만 이어가는 것**을 사전 등록한다.

조건: 원래 guard 종료와 owned group 부재 확인, TIMEOUT 기록 보존, 동일 pinned source/compiler/arch/Ninja와 기존 object 사용, 추가 다운로드/설치방법/환경 수정 없음. `kernel_method2_resume.py`를 동일하게 사용하며 KERNEL_METHOD_DEADLINE=1792653333.3034995(07:15:33 UTC, 방법2 원래 시작+65분)로 제한한다. 새 guard도 자체35분/global reserve보다 늘어나지 않는다. continuation의 시작·종료·object 재사용 여부를 별도로 기록한다. 이것이 마지막 continuation이며 실패하거나 누적 상한에 도달하면 중단한다. 사용자 전체2시간 deadline08:01:33은 바뀌지 않는다.
